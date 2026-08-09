"""
Phone agent vocabulary learning.

Distils the words a given store's callers actually use out of stored call
transcripts, so the transcriber can be primed with them. The point is proper
nouns: menu items pronounced unlike their menu spelling, street and
neighbourhood names, the shorthand regulars use.

Deliberately NOT a prompt change. Learned terms are fed to Deepgram as
keyterms, which improves what the agent *hears*; the script it speaks is
untouched. Prompt rewrites have regressed this agent before.

Mined terms land as `status='candidate'`. Nothing reaches a live call until a
human promotes them to 'approved' — a bad mining run cannot leak into calls on
its own.
"""
import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

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

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")

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
            if w.lower() not in _STOPWORDS
        }
        counts.update(seen_in_this_call)
    return counts


async def mine_merchant_vocab(merchant_id: str, days: int = 30) -> dict:
    """Mine one merchant's recent transcripts into candidate vocabulary terms.

    Upserts by (merchant_id, lower(term)) so a term's call-count accumulates
    across runs instead of creating duplicates. Existing 'approved' terms keep
    their status — re-mining must never silently un-approve something a human
    already vetted.
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

    written = 0
    for term, calls in ranked:
        prior = by_term.get(term)
        if prior:
            # Keep whatever status a human set; only refresh the evidence.
            await db.update(
                "phone_vocab_terms",
                {"occurrences": calls, "last_seen_at": now},
                filters={"id": f"eq.{prior['id']}"},
            )
        else:
            await db.insert("phone_vocab_terms", {
                "id": str(uuid4()),
                "merchant_id": merchant_id,
                "term": term,
                "occurrences": calls,
                "source": "transcript",
                "status": "candidate",
                "first_seen_at": now,
                "last_seen_at": now,
            })
        written += 1

    logger.info("Vocab mined merchant=%s calls=%d candidates=%d",
                merchant_id, len(rows), written)
    return {"merchant_id": merchant_id, "calls": len(rows), "candidates": written}


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
