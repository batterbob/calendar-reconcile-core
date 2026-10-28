"""Deterministic title normalization; it never attempts identity inference."""
from __future__ import annotations

import unicodedata

from .errors import BoundsError

# Punctuation is deleted (rather than made whitespace) to retain possessive-like
# tokens consistently. This fixed list is intentionally neutral and small.
STOPWORDS = frozenset({"a", "an", "the", "at", "on", "for", "vs", "game", "practice"})


def normalize_title(title: str, *, max_tokens: int = 64) -> tuple[str, ...]:
    """Return sorted unique meaningful tokens using NFKC + casefold.

    Unicode letters/numbers are retained, whitespace separates tokens, and all
    punctuation/symbols are deleted. An empty tuple is deliberately not a
    matchable title.
    """
    if not isinstance(title, str) or not 0 < max_tokens <= 256:
        raise BoundsError("invalid title normalization input")
    folded = unicodedata.normalize("NFKC", title).casefold()
    kept = "".join(ch if (ch.isalnum() or ch.isspace()) else "" for ch in folded)
    tokens = tuple(sorted({token for token in kept.split() if token not in STOPWORDS}))
    if len(tokens) > max_tokens:
        raise BoundsError("title has too many tokens")
    return tokens


def jaccard(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    """Token-set Jaccard similarity; an empty token set carries no evidence."""
    if not left or not right:
        return 0.0
    a, b = set(left), set(right)
    return len(a & b) / len(a | b)
