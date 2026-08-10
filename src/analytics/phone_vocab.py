"""
Phone agent vocabulary learning.

Distils the words a given store's callers actually use out of stored call
transcripts, so the transcriber can be primed with them. The point is proper
nouns: menu items pronounced unlike their menu spelling, street and
neighbourhood names, the shorthand regulars use.

Deliberately NOT a prompt change. Learned terms are fed to Deepgram as
keyterms, which improves what the agent *hears*; the script it speaks is
untouched. Prompt rewrites have regressed this agent before.

Approval is automatic but narrow. A term goes live only if it is the
merchant's own vocabulary (menu item, business name) or is not ordinary English
and several separate callers used it. Everything else stays a candidate,
because keyterms BIAS the recogniser — boosting a common word creates errors
rather than fixing them. Profanity and slurs are dropped outright and never
counted, stored, or shown (see vocab_blocklist).

A human can still approve or reject by hand; mining never overrules a status a
person set, in either direction.
"""
import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .vocab_blocklist import is_blocked

logger = logging.getLogger("meridian.analytics.phone_vocab")

# Words that carry no local flavour. Kept deliberately small: the goal is to
# strip filler, not to guess what a neighbourhood sounds like. Anything a
# specific store's callers repeat is worth surfacing, even if it looks generic.
_STOPWORDS = {
    "the", "and", "for", "you", "your", "yeah", "yes", "no", "not", "with",
    "have", "has", "had", "was", "were", "are", "can", "could", "would",
    "please", "thanks", "thank", "hello", "hi", "hey", "okay", "ok", "um",
    "uh", "like", "just", "get", "got", "want", "need", "one", "two", "three",
    "that", "this", "there", "here", "what", "when", "where", "how", "who",
    "all", "any", "some", "from", "them", "they", "she", "him", "her", "his",
    "our", "out", "about", "order", "orders", "ordering", "phone", "call",
    "know", "think", "going", "gonna", "wanna", "sorry", "right", "sure",
    "let", "see", "take", "put", "make", "give", "does", "did", "will",
}

# Any letter, not just ASCII: the merchants this serves have consomé, crème,
# jalapeño and piñata on the menu, and an [A-Za-z] class silently truncates
# them mid-word ("consomé" -> "consom"), which would then never match the
# spoken term. Digits and underscores are excluded.
_WORD = re.compile(r"[^\W\d_][^\W\d_'\-]{2,}", re.UNICODE)

# Ordinary English, plus the vocabulary every restaurant call contains. These
# are the words auto-approval must NOT boost: the recogniser already handles
# them, and biasing toward them actively creates errors — boost "pickup" and it
# starts hearing it in "pick her up" and in the surname "Pickford".
#
# This list only gates AUTOMATIC approval. A word in here can still be approved
# by hand, and is still mined and surfaced as a candidate.
_ORDINARY = {
    # days / times
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "today", "tomorrow", "tonight", "morning", "afternoon",
    "evening", "night", "minutes", "minute", "hour", "hours", "clock",
    "noon", "lunch", "dinner", "breakfast", "brunch", "week", "weekend",
    # ordering / service
    "pickup", "pick", "delivery", "deliver", "takeout", "dine", "table",
    "reservation", "book", "booking", "cancel", "change", "confirm",
    "address", "street", "avenue", "road", "apartment", "name", "number",
    "phone", "cash", "card", "credit", "debit", "pay", "paying", "payment",
    "total", "price", "cost", "much", "many", "extra", "side", "sides",
    "size", "small", "medium", "large", "regular", "special", "menu",
    "special", "combo", "meal", "plate", "bag", "box", "cup", "hot", "cold",
    "fresh", "spicy", "mild", "sauce", "cheese", "meat", "chicken", "beef",
    "pork", "fish", "veggie", "vegetarian", "vegan", "gluten", "allergy",
    "allergic", "nuts", "onions", "tomato", "lettuce", "drink", "drinks",
    "water", "soda", "coffee", "tea", "beer", "wine",
    # conversation
    "good", "great", "nice", "fine", "well", "bad", "wait", "waiting",
    "ready", "still", "again", "back", "come", "coming", "over", "under",
    "before", "after", "then", "now", "soon", "late", "early", "open",
    "closed", "close", "today's", "everything", "something", "anything",
    "nothing", "people", "person", "friend", "family", "guys", "guy",
    "man", "woman", "kids", "half", "double", "triple", "first", "second",
    "last", "next", "other", "another", "same", "different", "little",
    "big", "more", "less", "very", "really", "actually", "maybe", "probably",
    "definitely", "perfect", "awesome", "cool", "alright", "hold", "hang",
    "listen", "look", "talk", "speak", "say", "said", "tell", "told", "ask",
    "asked", "help", "sorry", "excuse", "mean", "means", "work", "works",
    "home", "house", "place", "time", "times", "day", "days", "money",
}

# A term must clear this many DISTINCT calls to be auto-approved on evidence
# alone. Higher than MIN_CALLS: appearing is enough to be worth showing a human,
# but not enough to change what a live call hears without anyone looking.
AUTO_APPROVE_MIN_CALLS = 5


def _menu_vocabulary(config) -> set[str]:
    """Words drawn from the merchant's own menu and business name.

    These are provably safe to boost: the merchant told us these are the things
    they sell, so telling the recogniser to expect them cannot be wrong.
    """
    vocab: set[str] = set()
    for item in (getattr(config, "menu_items", None) or []):
        name = (item.get("name") or "") if isinstance(item, dict) else ""
        vocab.update(w.lower() for w in _WORD.findall(name))
        for mod in (item.get("modifications") or []) if isinstance(item, dict) else []:
            vocab.update(w.lower() for w in _WORD.findall(str(mod)))
    vocab.update(w.lower() for w in _WORD.findall(getattr(config, "business_name", "") or ""))
    return {w for w in vocab if w not in _STOPWORDS}


def auto_status(term: str, calls: int, menu_vocab: set[str]) -> str:
    """Decide whether a mined term can be approved without a human.

    Two ways in, and only two:
      1. It is the merchant's own vocabulary (menu item, business name).
      2. It is not ordinary English and multiple separate callers used it —
         which is where local proper nouns live (neighbourhoods, regulars'
         shorthand, dish names the menu spells differently).

    Anything else stays a candidate. That is the safety property: a common
    English word is never auto-boosted, so automation cannot degrade
    recognition the way an unfiltered list would.
    """
    t = term.lower()
    # Defence in depth: extraction already drops these, so reaching here means
    # a term predates the blocklist or was inserted by hand. Never approve it.
    if is_blocked(t):
        return "blocked"
    if t in menu_vocab:
        return "approved"
    if t not in _ORDINARY and calls >= AUTO_APPROVE_MIN_CALLS:
        return "approved"
    return "candidate"

# A term must show up in at least this many DISTINCT calls to count. Frequency
# within a single rambling call says nothing about the store's vocabulary — one
# caller repeating "burrito" eight times is one data point, not eight.
MIN_CALLS = 3
MAX_TERMS_PER_MERCHANT = 60


def extract_terms(caller_texts: list[str]) -> Counter:
    """Count terms by how many DISTINCT calls contain them.

    Returns a Counter of term -> number of calls it appeared in.
    """
    counts: Counter = Counter()
    for text in caller_texts:
        seen_in_this_call = {
            w.lower() for w in _WORD.findall(text or "")
            if w.lower() not in _STOPWORDS and not is_blocked(w)
        }
        counts.update(seen_in_this_call)
    return counts


class _MenuSource:
    """The only two fields the menu vocabulary needs, read straight from
    phone_agent_config. Deliberately not the full MerchantPhoneConfig: that
    lives behind a sys.path shim in the webhook and is not importable here."""

    def __init__(self, row: dict):
        self.menu_items = row.get("menu_items") or []
        self.business_name = row.get("business_name") or ""


async def _config_for(merchant_id: str):
    """Best-effort menu source for a merchant. None on any failure — mining
    then falls back to evidence-only auto-approval, which is still safe."""
    try:
        from ..db import get_db
        rows = await get_db().select(
            "phone_agent_config",
            columns="menu_items,business_name",
            filters={"merchant_id": f"eq.{merchant_id}"},
            limit=1,
        )
        return _MenuSource(rows[0]) if rows else None
    except Exception as e:  # noqa: BLE001
        logger.warning("menu lookup failed for merchant=%s: %s", merchant_id, e)
        return None


async def mine_merchant_vocab(merchant_id: str, days: int = 30, config=None) -> dict:
    """Mine one merchant's recent transcripts into vocabulary terms.

    Terms are auto-approved when they are provably safe (see `auto_status`);
    everything else lands as a candidate for a human. Upserts by
    (merchant_id, lower(term)) so a term's call-count accumulates across runs
    instead of creating duplicates. A term a human already touched keeps its
    status — re-mining must never silently un-approve a human decision, nor
    re-approve something a human rejected.
    """
    from ..db import get_db
    db = get_db()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    rows = await db.select(
        "phone_call_transcripts",
        columns="caller_text",
        filters={"merchant_id": f"eq.{merchant_id}", "created_at": f"gte.{since}"},
    )
    if not rows:
        return {"merchant_id": merchant_id, "calls": 0, "candidates": 0}

    counts = extract_terms([r.get("caller_text", "") for r in rows])
    ranked = [(t, c) for t, c in counts.most_common() if c >= MIN_CALLS]
    ranked = ranked[:MAX_TERMS_PER_MERCHANT]

    existing = await db.select(
        "phone_vocab_terms",
        columns="id,term,status",
        filters={"merchant_id": f"eq.{merchant_id}"},
    )
    by_term = {(r.get("term") or "").lower(): r for r in (existing or [])}
    now = datetime.now(timezone.utc).isoformat()

    if config is None:
        config = await _config_for(merchant_id)
    menu_vocab = _menu_vocabulary(config) if config is not None else set()

    approved = candidates = 0
    for term, calls in ranked:
        prior = by_term.get(term)
        if prior:
            # A row a human touched (approved or rejected) keeps its status;
            # only the evidence is refreshed. Re-mining must not overrule a
            # person, in either direction.
            await db.update(
                "phone_vocab_terms",
                {"occurrences": calls, "last_seen_at": now},
                filters={"id": f"eq.{prior['id']}"},
            )
            if prior.get("status") == "approved":
                approved += 1
            else:
                candidates += 1
            continue

        status = auto_status(term, calls, menu_vocab)
        await db.insert("phone_vocab_terms", {
            "id": str(uuid4()),
            "merchant_id": merchant_id,
            "term": term,
            "occurrences": calls,
            "source": "menu" if term in menu_vocab else "transcript",
            "status": status,
            "first_seen_at": now,
            "last_seen_at": now,
        })
        if status == "approved":
            approved += 1
        else:
            candidates += 1

    logger.info("Vocab mined merchant=%s calls=%d auto-approved=%d candidates=%d",
                merchant_id, len(rows), approved, candidates)
    return {"merchant_id": merchant_id, "calls": len(rows),
            "approved": approved, "candidates": candidates}


async def approved_terms(merchant_id: str, limit: int = 40) -> list[str]:
    """The vetted keyterm list for one merchant, strongest evidence first.

    Only 'approved' rows. A candidate has been seen but not signed off, and
    must not influence a live call.
    """
    from ..db import get_db
    db = get_db()
    rows = await db.select(
        "phone_vocab_terms",
        columns="term,occurrences",
        filters={"merchant_id": f"eq.{merchant_id}", "status": "eq.approved"},
        order="occurrences.desc",
        limit=limit,
    )
    return [r["term"] for r in (rows or []) if r.get("term")]
