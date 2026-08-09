"""
Blocklist for phone-agent vocabulary learning (English + Spanish).

Learned terms are fed to the speech recogniser as keyterms and appear in a
merchant-facing list. Neither is a place for slurs or profanity, and callers
swear — so a term matching this list is dropped at extraction and never
counted, stored, or shown.

Matching is EXACT on a normalised form, never substring. Substring matching is
what produces the classic "Scunthorpe problem": it would blacklist `bass`,
`class`, `cocktail`, `assortment` and `Assam` (a tea) via `ass`, quietly
deleting real menu words. A false positive here is not cosmetic — it silently
removes a term the agent needed to hear.

Food collisions were checked deliberately, because this runs on restaurant
menus. Terms left OUT for that reason:
  - `concha`   — vulgar in the Southern Cone, but a Mexican sweet bread that
                 absolutely will be ordered by name.
  - `cracker`  — a slur in one sense and a cracker in the other.
  - `redskin`  — a slur, and also a potato variety.
  - `güey`     — ubiquitous Mexican filler ("dude"), not a slur; blocking it
                 would be moralising at customers, and it is stopworded anyway.
"""
import re
import unicodedata

# Profanity — English. Includes the inflections callers actually say, because
# matching is exact and `fucking` will not be caught by `fuck`.
_EN_PROFANITY = {
    "fuck", "fucks", "fucked", "fucking", "fucker", "fuckers", "motherfucker",
    "motherfuckers", "motherfucking", "fuckin",
    "shit", "shits", "shitty", "shitting", "bullshit", "shithead",
    "bitch", "bitches", "bitching", "bitchy",
    "cunt", "cunts", "twat", "twats",
    "dick", "dicks", "dickhead", "cock", "cocks", "prick", "pricks",
    "pussy", "pussies",
    "asshole", "assholes", "arsehole", "jackass", "dumbass", "dipshit",
    "bastard", "bastards", "wanker", "wankers", "bollocks",
    "whore", "whores", "slut", "sluts", "skank",
    "douche", "douchebag", "douchebags",
    "piss", "pissed", "pissing",
}

# Profanity — Spanish, including the accented and unaccented spellings that
# both arrive from a transcriber.
_ES_PROFANITY = {
    "mierda", "mierdas",
    "joder", "jodido", "jodida", "jodete",
    "puta", "putas", "puto", "putos", "putada",
    "pendejo", "pendejos", "pendeja", "pendejas",
    "cabron", "cabrón", "cabrones", "cabrona",
    "chinga", "chingar", "chingada", "chingado", "chingadera", "chingon",
    "verga", "vergas",
    "culero", "culeros", "culiao", "culiado",
    "carajo",
    "gilipollas", "capullo",
    "hijoputa", "hijueputa", "hijodeputa",
    "boludo", "boludos", "pelotudo", "pelotudos",
    "mamon", "mamón", "mamada", "mamadas",
    "pinche", "pinches",
    "chucha", "huevon", "huevón",
}

# Slurs — racial, ethnic, religious, sexual-orientation, gender identity, and
# disability. Blocked regardless of who says them or how often.
_SLURS = {
    # racial / ethnic — English
    "nigger", "niggers", "nigga", "niggas", "coon", "coons",
    "chink", "chinks", "gook", "gooks", "jap", "japs",
    "spic", "spics", "beaner", "beaners", "wetback", "wetbacks",
    "kike", "kikes", "yid",
    "paki", "pakis", "raghead", "ragheads", "towelhead", "towelheads",
    # `guinea` is a slur in one sense but also guinea fowl and Guinea pepper,
    # both of which appear on menus — left out rather than risk deleting them.
    "wop", "wops", "dago", "dagos",
    "injun", "squaw", "gyppo", "gypo",
    # sexual orientation / gender identity
    "fag", "fags", "faggot", "faggots", "faggy", "dyke", "dykes",
    "tranny", "trannies", "shemale",
    # disability
    "retard", "retards", "retarded", "spastic", "mongoloid",
    # racial / ethnic — Spanish
    "sudaca", "sudacas", "negrata", "negratas", "panchito",
    "maricon", "maricón", "maricones", "marica", "maricas",
    "joto", "jotos", "puñal",
}

_BLOCKED = frozenset(_EN_PROFANITY | _ES_PROFANITY | _SLURS)

# Terms whose accent is the ONLY thing separating them from an ordinary word,
# so they must match with the accent intact. General matching folds accents (so
# `cabrón` and `cabron` both hit), but that same fold turns `coño` into `cono`
# — which is simply "cone", and blocking it would delete a real ice-cream word.
_ACCENT_SENSITIVE = frozenset({"coño", "coños"})

_REPEAT = re.compile(r"(.)\1{2,}")
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def _fold_keep_accents(term: str) -> str:
    """Lowercase and undo leetspeak/stretching, but KEEP accents — the form the
    accent-sensitive entries are matched against."""
    t = (term or "").strip().lower().translate(_LEET)
    t = _REPEAT.sub(r"\1", t)
    return re.sub(r"[^a-záéíóúüñç]", "", t)


def _normalize(term: str) -> str:
    """Fold a term to the form the blocklist is written in.

    Handles what a transcriber and a determined caller actually produce:
    accents (`cabrón`/`cabron`), stretched vowels (`shiiiit`), and leetspeak
    (`sh1t`). Accents are stripped for MATCHING only — the stored term keeps
    them, since `jalapeño` must survive intact elsewhere.
    """
    t = (term or "").strip().lower().translate(_LEET)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = _REPEAT.sub(r"\1", t)          # shiiiit -> shit
    return re.sub(r"[^a-z]", "", t)     # drop hyphens/apostrophes: f-ing -> fing


# The blocklist itself, normalised once at import so lookups are a set hit.
_BLOCKED_NORMALIZED = frozenset(_normalize(t) for t in _BLOCKED if _normalize(t))


def is_blocked(term: str) -> bool:
    """True when a term must never be learned, stored, or shown.

    Exact match on the normalised form — see the module docstring for why this
    is deliberately not a substring test.
    """
    if _fold_keep_accents(term) in _ACCENT_SENSITIVE:
        return True
    n = _normalize(term)
    if not n:
        return False
    if n in _BLOCKED_NORMALIZED:
        return True
    # Regular plural of a blocked singular ("pendejoss" is not a word, but
    # "cabrones" is already listed; this catches the simple -s case).
    if n.endswith("s") and n[:-1] in _BLOCKED_NORMALIZED:
        return True
    return False
