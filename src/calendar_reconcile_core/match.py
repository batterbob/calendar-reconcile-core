"""Pure matching primitives with opaque subject discipline."""
from __future__ import annotations

from datetime import date, datetime

from .normalize import jaccard, normalize_title
from .policy import ReconcilePolicy
from .types import CalendarEvent, EvidenceEvent, SubjectResolver


def resolved_subject(event: CalendarEvent | EvidenceEvent, resolver: SubjectResolver | None,
                     policy: ReconcilePolicy) -> str | None:
    """Return an explicit/resolved opaque subject, or None on ambiguity/no result."""
    if event.subject_id is not None:
        return event.subject_id
    if resolver is None:
        return None
    resolution = resolver.resolve(
        normalized_title=normalize_title(event.title, max_tokens=policy.max_tokens),
        source_id=event.source_id,
    )
    return None if resolution.ambiguous else resolution.subject_id


def subject_is_resolved(event: CalendarEvent | EvidenceEvent, resolver: SubjectResolver | None,
                        policy: ReconcilePolicy) -> bool:
    """A resolver's no-result is fail-closed, never a subjectless fallback."""
    if event.subject_id is not None or resolver is None:
        return True
    resolution = resolver.resolve(
        normalized_title=normalize_title(event.title, max_tokens=policy.max_tokens),
        source_id=event.source_id,
    )
    return not resolution.ambiguous and resolution.subject_id is not None


def subjects_compatible(left: str | None, right: str | None, policy: ReconcilePolicy) -> bool:
    if left is None and right is None:
        return policy.allow_subjectless_matches
    return left is not None and right is not None and left == right


def title_similarity(left: CalendarEvent | EvidenceEvent, right: CalendarEvent | EvidenceEvent,
                     policy: ReconcilePolicy) -> float:
    return jaccard(normalize_title(left.title, max_tokens=policy.max_tokens),
                   normalize_title(right.title, max_tokens=policy.max_tokens))


def _day(value: date | datetime) -> date:
    return value if isinstance(value, date) and not isinstance(value, datetime) else value.date()


def dates_compatible(left: CalendarEvent | EvidenceEvent, right: CalendarEvent | EvidenceEvent,
                     policy: ReconcilePolicy) -> bool:
    return abs((_day(left.start) - _day(right.start)).days) <= policy.date_tolerance_days


def times_compatible(left: CalendarEvent | EvidenceEvent, right: CalendarEvent | EvidenceEvent,
                     policy: ReconcilePolicy) -> bool:
    if left.is_all_day != right.is_all_day:
        return True
    if left.is_all_day:
        return True
    assert isinstance(left.start, datetime) and isinstance(right.start, datetime)
    return abs((left.start - right.start).total_seconds()) <= policy.time_tolerance_seconds


def is_matchable(event: CalendarEvent, evidence: EvidenceEvent, policy: ReconcilePolicy,
                 resolver: SubjectResolver | None = None) -> tuple[bool, float]:
    """Check identity/date gate before fuzzy title comparison."""
    if event.source_id not in policy.allowed_sources or evidence.source_id not in policy.allowed_sources:
        return False, 0.0
    if not subject_is_resolved(event, resolver, policy) or not subject_is_resolved(evidence, resolver, policy):
        return False, 0.0
    if not subjects_compatible(resolved_subject(event, resolver, policy),
                               resolved_subject(evidence, resolver, policy), policy):
        return False, 0.0
    if not dates_compatible(event, evidence, policy):
        return False, 0.0
    similarity = title_similarity(event, evidence, policy)
    return similarity >= policy.title_match_threshold, similarity
