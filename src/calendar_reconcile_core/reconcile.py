"""Bounded, deterministic reconciliation outcomes. No calendar is mutated."""
from __future__ import annotations

from datetime import date, datetime

from .errors import BoundsError, IdentityError
from .match import (
    dates_compatible,
    is_matchable,
    resolved_subject,
    subject_is_resolved,
    subjects_compatible,
    times_compatible,
    title_similarity,
)
from .policy import AmbiguityBehavior, ReconcilePolicy
from .types import (
    MAX_SEQUENCE,
    Agreement,
    AmbiguousDuplicateCandidate,
    CalendarEvent,
    Conflict,
    CorrectionCandidate,
    DuplicateCandidate,
    EvidenceEvent,
    Reason,
    SubjectResolver,
)


def _event_key(event: CalendarEvent) -> tuple[str, str]:
    return (event.event_id, event.source_id)


def _evidence_key(item: EvidenceEvent, policy: ReconcilePolicy) -> tuple[int, int, float, str, str]:
    """Policy precedence orders traversal only; it never resolves disagreement."""
    try:
        precedence = len(policy.source_precedence) - policy.source_precedence.index(item.source_id)
    except ValueError:
        precedence = 0
    return (-precedence, -item.source_rank, -item.confidence, item.source_id, item.evidence_id)


def _check_bounds(events: tuple[CalendarEvent, ...], evidence: tuple[EvidenceEvent, ...],
                  policy: ReconcilePolicy) -> None:
    if len(events) > policy.max_events or len(evidence) > policy.max_evidence:
        raise BoundsError("input collection exceeds policy limit")


def _require_unique_ids(identifiers: tuple[str, ...]) -> None:
    if len(identifiers) != len(set(identifiers)):
        raise IdentityError("duplicate opaque identifiers")


def _check_finding_capacity(policy: ReconcilePolicy, *, current_count: int) -> None:
    if current_count >= policy.max_findings:
        raise BoundsError("finding limit exceeded")


def reconcile(events: tuple[CalendarEvent, ...] | list[CalendarEvent],
              evidence: tuple[EvidenceEvent, ...] | list[EvidenceEvent],
              policy: ReconcilePolicy, *, resolver: SubjectResolver | None = None
              ) -> tuple[tuple[Agreement, ...], tuple[Conflict, ...]]:
    """Reconcile supplied evidence without inventing identity or correction action.

    Candidates are bounded before comparison. Equal-ranked candidates for
    different dates fail closed; callers can request a machine-readable conflict
    instead of a silent skip.
    """
    event_items, evidence_items = tuple(events), tuple(evidence)
    _check_bounds(event_items, evidence_items, policy)
    _require_unique_ids(tuple(event.event_id for event in event_items))
    _require_unique_ids(tuple(item.evidence_id for item in evidence_items))
    comparisons = 0
    agreements: list[Agreement] = []
    conflicts: list[Conflict] = []
    for event in sorted(event_items, key=_event_key):
        matches: list[EvidenceEvent] = []
        date_mismatches: list[EvidenceEvent] = []
        for item in sorted(evidence_items, key=lambda item: _evidence_key(item, policy)):
            comparisons += 1
            if comparisons > policy.max_candidate_comparisons:
                raise BoundsError("candidate comparison limit exceeded")
            ok, _ = is_matchable(event, item, policy, resolver)
            if ok:
                matches.append(item)
            # Date mismatch is a separate, non-agreement conflict path. Its
            # subject check occurs before title comparison; it is bounded by the
            # same global comparison budget and cannot create a correction.
            elif (
                event.source_id in policy.allowed_sources
                and item.source_id in policy.allowed_sources
                and subject_is_resolved(event, resolver, policy)
                and subject_is_resolved(item, resolver, policy)
                and subjects_compatible(
                    resolved_subject(event, resolver, policy),
                    resolved_subject(item, resolver, policy),
                    policy,
                )
                and title_similarity(event, item, policy) >= policy.title_match_threshold
            ):
                date_mismatches.append(item)
        if not matches:
            if date_mismatches:
                _check_finding_capacity(policy, current_count=len(agreements) + len(conflicts))
                conflicts.append(Conflict(
                    event.event_id,
                    tuple(sorted(item.evidence_id for item in date_mismatches)),
                    Reason.DATE_MISMATCH,
                ))
            continue
        # A source never becomes authoritative by rank alone. Different dates
        # among matched evidence are an explicit conflict.
        dates = {(item.start, item.end) for item in matches}
        ids = tuple(sorted(item.evidence_id for item in matches))
        if len(dates) > 1:
            _check_finding_capacity(policy, current_count=len(agreements) + len(conflicts))
            conflicts.append(Conflict(event.event_id, ids, Reason.SOURCE_DISAGREEMENT))
        elif all(times_compatible(event, item, policy) for item in matches):
            _check_finding_capacity(policy, current_count=len(agreements) + len(conflicts))
            agreements.append(Agreement(event.event_id, ids))
        else:
            _check_finding_capacity(policy, current_count=len(agreements) + len(conflicts))
            conflicts.append(Conflict(event.event_id, ids, Reason.TIME_MISMATCH))
    return tuple(agreements), tuple(conflicts)


def screen_duplicates(proposed: tuple[CalendarEvent, ...] | list[CalendarEvent],
                      existing: tuple[CalendarEvent, ...] | list[CalendarEvent],
                      policy: ReconcilePolicy, *, resolver: SubjectResolver | None = None
                      ) -> tuple[DuplicateCandidate | AmbiguousDuplicateCandidate, ...]:
    """Return, never delete, deterministic same-date near-duplicate candidates."""
    proposed_items, existing_items = tuple(proposed), tuple(existing)
    if len(proposed_items) > policy.max_events or len(existing_items) > policy.max_events:
        raise BoundsError("input collection exceeds policy limit")
    _require_unique_ids(tuple(event.event_id for event in proposed_items))
    _require_unique_ids(tuple(event.event_id for event in existing_items))
    comparisons = 0
    found: list[DuplicateCandidate | AmbiguousDuplicateCandidate] = []
    for candidate in sorted(proposed_items, key=_event_key):
        if candidate.source_id not in policy.allowed_sources:
            continue
        if not subject_is_resolved(candidate, resolver, policy):
            continue
        candidate_subject = resolved_subject(candidate, resolver, policy)
        if candidate_subject is None:
            continue
        matches: list[tuple[float, CalendarEvent]] = []
        for current in sorted(existing_items, key=_event_key):
            comparisons += 1
            if comparisons > policy.max_candidate_comparisons:
                raise BoundsError("candidate comparison limit exceeded")
            if current.source_id not in policy.allowed_sources:
                continue
            if not dates_compatible(candidate, current, policy):
                continue
            if not subject_is_resolved(current, resolver, policy):
                continue
            current_subject = resolved_subject(current, resolver, policy)
            if current_subject is None:
                continue
            if not subjects_compatible(candidate_subject, current_subject, policy):
                continue
            similarity = title_similarity(candidate, current, policy)
            if similarity >= policy.title_match_threshold:
                matches.append((similarity, current))
        if not matches:
            continue
        matches.sort(key=lambda pair: (-pair[0],) + _event_key(pair[1]))
        top_score = matches[0][0]
        tied = [entry for entry in matches if entry[0] == top_score]
        if len(tied) > 1 and policy.ambiguity_behavior is AmbiguityBehavior.SKIP:
            continue
        if len(tied) > 1:
            _check_finding_capacity(policy, current_count=len(found))
            found.append(AmbiguousDuplicateCandidate(
                candidate.event_id,
                tuple(current.event_id for _, current in tied),
                top_score,
            ))
        else:
            similarity, current = tied[0]
            _check_finding_capacity(policy, current_count=len(found))
            found.append(DuplicateCandidate(candidate.event_id, current.event_id, similarity))
    return tuple(found)


def correction_candidate(event: CalendarEvent, *, uid: str, sequence: int,
                         corrected_start: date | datetime, corrected_end: date | datetime,
                         evidence_ids: tuple[str, ...] = ()) -> CorrectionCandidate:
    """Preserve caller identity and increment sequence without generating delivery."""
    if not uid.strip() or "\x00" in uid:
        raise IdentityError("invalid uid")
    if not isinstance(sequence, int) or sequence < 0 or sequence >= MAX_SEQUENCE:
        raise IdentityError("sequence cannot be incremented")
    return CorrectionCandidate(event.event_id, uid, sequence + 1, corrected_start, corrected_end,
                               tuple(sorted(evidence_ids)))
