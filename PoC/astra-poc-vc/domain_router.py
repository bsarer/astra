"""
Domain Router — classifies text/emails into knowledge domains.
Ensures context retrieval is scoped to what's actually relevant.

Domains: finance, sales, travel, team, personal, admin
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Domain taxonomy
# ---------------------------------------------------------------------------

DOMAIN_RULES: dict[str, dict] = {
    "finance": {
        "keywords": [
            "stock", "market", "portfolio", "ticker", "aapl", "msft", "nvda",
            "tsla", "goog", "amzn", "meta", "earnings", "dividend", "bullish",
            "bearish", "price target", "bloomberg", "trading", "investment",
            "shares", "equity", "fund", "analyst", "upgrade", "downgrade",
            "rally", "correction", "nasdaq", "s&p", "dow", "etf", "options",
            "watchlist", "holdings", "financial advisor",
        ],
        "senders": [
            "bloomberg", "marketwatch", "cnbc", "wsj", "reuters",
            "seekingalpha", "motleyfool",
        ],
    },
    "sales": {
        "keywords": [
            "deal", "pipeline", "renewal", "pricing", "client", "prospect",
            "quota", "revenue", "contract", "proposal", "acme", "bluepeak",
            "novatech", "salesforce", "crm", "onboarding", "expansion",
            "discount", "seats", "tier", "close", "demo", "follow-up",
            "negotiation", "security review", "enterprise", "b2b",
        ],
        "senders": [
            "acmecorp", "bluepeak", "novatech", "vertexsolutions",
            "tom.bradley", "rachel.kim", "dave.wilson",
        ],
    },
    "travel": {
        "keywords": [
            "flight", "hotel", "trip", "travel", "airport", "booking",
            "itinerary", "packing", "weather", "helsinki", "finland",
            "rome", "italy", "passport", "visa", "currency", "aurora",
            "check-in", "check-out", "reservation", "confirmation",
            "departure", "arrival", "layover", "seat", "luggage",
        ],
        "senders": [
            "finnair", "hotelkamp", "tripadvisor", "booking.com",
            "visitfinland", "airbnb", "expedia", "delta", "united",
        ],
    },
    "team": {
        "keywords": [
            "1:1", "team", "sdr", "pipeline review", "all-hands",
            "metrics", "leads", "mql", "meetings booked", "performance",
            "report", "weekly", "update", "direct report", "manager",
            "q1", "q2", "q3", "q4", "board deck", "offsite",
        ],
        "senders": [
            "sarah.chen", "jake.morrison", "priya.patel", "lisa.park",
        ],
    },
    "personal": {
        "keywords": [
            "hobby", "craft beer", "football", "hiking", "photography",
            "gym", "crossfit", "weekend", "vacation", "personal",
            "family", "friend",
        ],
        "senders": [],
    },
    "admin": {
        "keywords": [
            "remind", "reminder", "todo", "task", "schedule", "follow up",
            "deadline", "due", "action item", "note to self",
        ],
        "senders": [],
    },
}

# Minimum keyword hits to consider a domain "active"
MIN_HITS = 1
# Ratio threshold: if top domain scores >= DOMINANCE_RATIO * second domain, it's single-domain
DOMINANCE_RATIO = 2.5

# Cross-domain bridge rules: (domain_a, domain_b) -> list of bridging entity patterns
# Bridge is allowed only when a shared entity (person, company, date) is detected
BRIDGE_RULES: list[tuple[str, str]] = [
    ("finance", "sales"),    # e.g. stock alert + client meeting
    ("sales", "team"),       # e.g. client deal + team report
    ("travel", "personal"),  # e.g. trip + packing/hobbies
    ("team", "admin"),       # e.g. team meeting + reminder
]


@dataclass
class ClassificationResult:
    domains: list[str]
    scores: dict[str, int]
    confidence: str  # "high", "medium", "low"
    bridged: bool = False


def classify(text: str, sender: Optional[str] = None) -> ClassificationResult:
    """
    Classify text into one or more domains.

    Args:
        text: The content to classify (email body, user message, file content)
        sender: Optional sender email/domain for email classification

    Returns:
        ClassificationResult with matched domains and confidence
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for domain, rules in DOMAIN_RULES.items():
        score = 0
        # Keyword scoring
        for kw in rules["keywords"]:
            if kw in text_lower:
                score += 1
        # Sender bonus (counts as 3 keyword hits)
        if sender:
            sender_lower = sender.lower()
            for s in rules["senders"]:
                if s in sender_lower:
                    score += 3
                    break
        scores[domain] = score

    # Filter to domains with at least MIN_HITS
    active = {d: s for d, s in scores.items() if s >= MIN_HITS}

    if not active:
        return ClassificationResult(
            domains=["admin"],
            scores=scores,
            confidence="low",
        )

    # Sort by score descending
    ranked = sorted(active.items(), key=lambda x: x[1], reverse=True)
    top_domain, top_score = ranked[0]

    # Single-domain: top score dominates
    if len(ranked) == 1 or top_score >= DOMINANCE_RATIO * ranked[1][1]:
        return ClassificationResult(
            domains=[top_domain],
            scores=scores,
            confidence="high" if top_score >= 3 else "medium",
        )

    # Multi-domain: check if bridge is allowed
    top_two = [ranked[0][0], ranked[1][0]]
    pair = tuple(sorted(top_two))
    bridgeable = any(
        tuple(sorted([a, b])) == pair for a, b in BRIDGE_RULES
    )

    if bridgeable:
        return ClassificationResult(
            domains=top_two,
            scores=scores,
            confidence="medium",
            bridged=True,
        )

    # Not bridgeable — use only the top domain
    return ClassificationResult(
        domains=[top_domain],
        scores=scores,
        confidence="medium",
    )


def classify_email(subject: str, body: str, sender: str) -> ClassificationResult:
    """Convenience wrapper for email classification."""
    combined = f"{subject} {body}"
    return classify(combined, sender=sender)


def domains_for_query(user_message: str) -> list[str]:
    """Quick helper — returns just the domain list for a user message."""
    return classify(user_message).domains
