"""Explicit caller-owned reconciliation policy."""
from dataclasses import dataclass
from enum import Enum

from .errors import CalendarReconcileError


class AmbiguityBehavior(str, Enum):
    SKIP = "skip"
    REPORT = "report"


@dataclass(frozen=True, slots=True)
class ReconcilePolicy:
    allowed_sources: frozenset[str]
    source_precedence: tuple[str, ...] = ()
    title_match_threshold: float = 0.75
    date_tolerance_days: int = 0
    time_tolerance_seconds: int = 0
    max_events: int = 1_000
    max_evidence: int = 1_000
    max_candidate_comparisons: int = 10_000
    max_findings: int = 100
    max_tokens: int = 64
    allow_subjectless_matches: bool = False
    ambiguity_behavior: AmbiguityBehavior = AmbiguityBehavior.SKIP

    def __post_init__(self) -> None:
        if not self.allowed_sources or any(not isinstance(x, str) or not x.strip() for x in self.allowed_sources):
            raise CalendarReconcileError("allowed_sources must be nonempty opaque IDs")
        if len(self.allowed_sources) > 256 or len(self.source_precedence) > 256:
            raise CalendarReconcileError("too many sources")
        if len(set(self.source_precedence)) != len(self.source_precedence) or not set(self.source_precedence) <= self.allowed_sources:
            raise CalendarReconcileError("invalid source_precedence")
        if not 0 < self.title_match_threshold <= 1:
            raise CalendarReconcileError("invalid title_match_threshold")
        for name in ("date_tolerance_days", "time_tolerance_seconds", "max_events", "max_evidence", "max_candidate_comparisons", "max_findings", "max_tokens"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise CalendarReconcileError(f"invalid {name}")
        if self.max_events == 0 or self.max_evidence == 0 or self.max_candidate_comparisons == 0 or self.max_findings == 0 or self.max_tokens == 0:
            raise CalendarReconcileError("resource limits must be positive")
