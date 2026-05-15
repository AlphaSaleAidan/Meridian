"""
Principle Extraction Filter — strips author voice from book/expert content.

When the swarm ingests content from financial books, author blogs, and
investment thought leaders, we want ONLY the actionable business principles —
not the author's personality, writing style, investment philosophy, or
personal brand. This filter rewrites book/author content into depersonalized,
implementable business insights suitable for small business merchants.

Source types that trigger filtering:
  - book_summary: Book summary sites (Blinkist, FourMinuteBooks, etc.)
  - author_content: Author blogs (Seth Godin, James Clear, etc.)
  - financial_expert: Investment thought leaders (Buffett, Dalio, Marks, etc.)

Source types that pass through unfiltered:
  - industry_data: Industry reports, government stats, research (default)
"""
import logging
import re

logger = logging.getLogger("meridian.inference.principle_filter")

FILTERED_SOURCE_TYPES = {"book_summary", "author_content", "financial_expert"}

# Source keys known to be author/book content (fallback if source_type not set)
KNOWN_AUTHOR_SOURCES = {
    "simon_sinek", "seth_godin", "james_clear", "adam_grant", "gary_vee",
    "naval_blog", "tim_ferriss", "fourminutebooks", "readingraphics",
    "getstoryshots", "sam_thomas_davies", "blinkist_free", "buffett_berkshire",
    "bridgewater", "oaktree_memos", "damodaran", "pragcap", "abnormal_returns",
    "collaborative_fund", "stratechery",
}

# Phrases that signal author personality rather than business principle
_AUTHOR_VOICE_PATTERNS = [
    re.compile(r"\b(I believe|I think|In my experience|I've found|I always say)\b", re.I),
    re.compile(r"\b(my (favorite|favourite)|my philosophy|my approach)\b", re.I),
    re.compile(r"\b(as I (wrote|said|mentioned) in)\b", re.I),
    re.compile(r"\bfollow me on\b", re.I),
    re.compile(r"\b(subscribe|newsletter|my (book|podcast|show|channel))\b", re.I),
    re.compile(r"\b(check out my|buy my|order my|get my)\b", re.I),
]

# Investment-specific language that shouldn't bleed into SMB merchant advice
_INVESTMENT_JARGON = [
    re.compile(r"\b(alpha|beta|sharpe ratio|CAPM|efficient frontier)\b", re.I),
    re.compile(r"\b(short (sell|position)|margin call|derivatives|options chain)\b", re.I),
    re.compile(r"\b(hedge fund|private equity|venture capital|IPO|SPAC)\b", re.I),
    re.compile(r"\b(portfolio (allocation|rebalancing)|asset class)\b", re.I),
    re.compile(r"\b(P/E ratio|EV/EBITDA|market cap|price.to.book)\b", re.I),
    re.compile(r"\b(bull market|bear market|market correction|yield curve)\b", re.I),
]

# Principle categories we WANT to extract
_PRINCIPLE_SIGNALS = [
    "cash flow", "profit margin", "revenue", "cost control", "pricing",
    "customer retention", "inventory", "labor cost", "efficiency",
    "growth", "scale", "recurring revenue", "unit economics",
    "break even", "operating leverage", "working capital", "debt",
    "savings", "compound", "reinvest", "margin of safety",
    "diversif", "risk management", "budget", "forecast",
    "negotiate", "supplier", "overhead", "fixed cost", "variable cost",
]


def needs_filtering(source_key: str, source_type: str = "") -> bool:
    """Check if content from this source should be principle-filtered."""
    if source_type in FILTERED_SOURCE_TYPES:
        return True
    return source_key in KNOWN_AUTHOR_SOURCES


def extract_principles(content: str, source_key: str, title: str = "") -> str:
    """Extract actionable business principles from author/book content.

    Returns depersonalized content focused on implementable business insights.
    Strips author voice, personal branding, and investment-specific jargon
    that doesn't apply to small business operations.
    """
    if not content or len(content) < 100:
        return content

    lines = content.split("\n")
    filtered_lines = []
    principles_found = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Strip first-person author voice before checking relevance
        cleaned = _depersonalize(stripped)

        # Skip pure navigation, promo, and author-brand noise
        if _is_noise_line(cleaned):
            continue

        # Check if line contains actionable business principle
        relevance = _score_business_relevance(cleaned)

        if relevance > 0:
            filtered_lines.append(cleaned)
            if relevance >= 2:
                principles_found.append(cleaned)

    if not filtered_lines:
        return content[:500]

    # Build principle-focused output
    parts = []
    if principles_found:
        parts.append("KEY PRINCIPLES:")
        for p in principles_found[:10]:
            parts.append(f"- {p[:300]}")
        parts.append("")

    if filtered_lines:
        parts.append("CONTEXT:")
        parts.append(" ".join(filtered_lines[:30]))

    result = "\n".join(parts)

    logger.debug(
        f"Principle filter [{source_key}]: "
        f"{len(content)} chars -> {len(result)} chars, "
        f"{len(principles_found)} principles extracted"
    )
    return result


def _is_noise_line(line: str) -> bool:
    """True if line is pure navigation, promo, or author branding noise."""
    if len(line) < 10:
        return True
    if line.startswith(("[", "![", "Menu", "Close", "About", "Home")):
        return True
    # Only drop short promo/self-referential lines entirely.
    # Longer lines with author framing get depersonalized instead of dropped.
    if len(line) < 80:
        for pattern in _AUTHOR_VOICE_PATTERNS:
            if pattern.search(line):
                return True
    return False


def _depersonalize(text: str) -> str:
    """Remove first-person author framing while keeping the principle."""
    # "I believe that cash flow is king" -> "Cash flow is king"
    text = re.sub(
        r"^(I (believe|think|know|argue|suggest|recommend) (that )?)",
        "", text, flags=re.I,
    )
    # "In my experience, businesses that..." -> "Businesses that..."
    text = re.sub(
        r"^(In my (experience|view|opinion),?\s*)",
        "", text, flags=re.I,
    )
    # "As I wrote in [Book], ..." -> strip the reference
    text = re.sub(
        r"(As I (wrote|said|mentioned|discussed) in .{5,60}?,?\s*)",
        "", text, flags=re.I,
    )
    return text.strip()


def _score_business_relevance(text: str) -> int:
    """Score how relevant a line is to actionable business advice.

    0 = not relevant, 1 = somewhat, 2+ = strong principle.
    """
    lower = text.lower()
    score = 0

    # Positive: contains business principle language
    for signal in _PRINCIPLE_SIGNALS:
        if signal in lower:
            score += 1

    # Negative: heavy investment jargon (not applicable to SMB merchants)
    jargon_hits = sum(1 for p in _INVESTMENT_JARGON if p.search(text))
    if jargon_hits >= 2:
        score = max(0, score - jargon_hits)

    # Boost: contains numbers/percentages (specific, actionable)
    if re.search(r"\d+%|\$\d+|[0-9]+x", text):
        score += 1

    # Boost: action verbs (implementable advice)
    if re.search(r"\b(reduce|increase|cut|improve|track|measure|automate|negotiate)\b", lower):
        score += 1

    return score


def filter_for_embedding(content: str, source_key: str,
                         source_type: str = "", title: str = "") -> str:
    """Entry point: returns filtered content if source needs it, else passthrough."""
    if not needs_filtering(source_key, source_type):
        return content
    return extract_principles(content, source_key, title)
