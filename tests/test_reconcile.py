from datetime import date, datetime, timezone
from itertools import permutations

import pytest

from calendar_reconcile_core import (AmbiguityBehavior, BoundsError, CalendarEvent,
                                     EvidenceEvent, ReconcilePolicy, SubjectResolution)
from calendar_reconcile_core.reconcile import (_evidence_key, correction_candidate,
                                                reconcile, screen_duplicates)
from calendar_reconcile_core.types import Reason


def policy(**changes):
    values = dict(allowed_sources=frozenset({"source-alpha", "source-beta"}),
                  allow_subjectless_matches=False, max_candidate_comparisons=20)
    values.update(changes)
    return ReconcilePolicy(**values)


def event(identifier="event-a", day=2, subject="subject-a", title="Fall concert"):
    return CalendarEvent(identifier, title, "source-alpha", date(2026, 1, day),
                         date(2026, 1, day + 1), subject)


def evidence(identifier="evidence-a", day=2, subject="subject-a", title="Fall concert", rank=1):
    return EvidenceEvent(identifier, title, "source-beta", date(2026, 1, day),
                         date(2026, 1, day + 1), rank, 1.0, subject)


def test_agreement_conflict_and_permutation_order_are_stable():
    events = [event("event-b", title="Spring recital"), event("event-a")]
    proof = [evidence("proof-b", title="Spring recital"), evidence("proof-a")]
    expected = reconcile(events, proof, policy())
    assert [x.event_id for x in expected[0]] == ["event-a", "event-b"]
    for evs in permutations(events):
        for proofs in permutations(proof):
            assert reconcile(evs, proofs, policy()) == expected


def test_conflicting_evidence_is_not_resolved_by_rank():
    agreements, conflicts = reconcile([event()], [evidence(day=2, rank=9), evidence("b", day=3, rank=1)],
                                      policy(date_tolerance_days=1))
    assert agreements == ()
    assert conflicts[0].reason is Reason.SOURCE_DISAGREEMENT


def test_precedence_orders_evidence_but_cannot_settle_a_disagreement():
    # source_precedence is caller-owned ordering input, not an authority grant.
    configured = policy(date_tolerance_days=1,
                        source_precedence=("source-alpha", "source-beta"))
    alpha = EvidenceEvent("alpha", "Fall concert", "source-alpha", date(2026, 1, 2),
                          date(2026, 1, 3), 0, 1.0, "subject-a")
    beta = evidence("b", day=3, rank=999)
    assert _evidence_key(alpha, configured) < _evidence_key(beta, configured)
    _, conflicts = reconcile([event()], [alpha, beta], configured)
    assert conflicts[0].reason is Reason.SOURCE_DISAGREEMENT


def test_date_mismatch_is_reported_by_the_separate_nonagreement_path():
    agreements, conflicts = reconcile([event(day=2)], [evidence(day=4)], policy())
    assert agreements == ()
    assert conflicts == (conflicts[0],)
    assert conflicts[0].reason is Reason.DATE_MISMATCH


def test_subjectless_and_ambiguous_identity_fail_closed():
    assert reconcile([event(subject=None)], [evidence(subject=None)], policy()) == ((), ())

    class Ambiguous:
        def resolve(self, **kwargs):
            return SubjectResolution(None, 0.0, ambiguous=True)

    assert reconcile([event(subject=None)], [evidence(subject=None)],
                     policy(allow_subjectless_matches=True), resolver=Ambiguous()) == ((), ())


def test_threshold_boundary_and_comparison_cap():
    # Two of three token-set overlap is exactly 1/2.
    assert reconcile([event(title="alpha beta")], [evidence(title="alpha gamma")],
                     policy(title_match_threshold=0.5))[0]
    with pytest.raises(BoundsError):
        reconcile([event(), event("event-b")], [evidence(), evidence("proof-b")],
                  policy(max_candidate_comparisons=3))


def test_duplicate_screen_is_non_mutating_and_ambiguous_skips():
    proposed = event("new")
    existing = [event("old-a"), event("old-b")]
    assert screen_duplicates([proposed], existing, policy()) == ()
    chosen = screen_duplicates([proposed], existing,
                               policy(ambiguity_behavior=AmbiguityBehavior.REPORT))
    assert chosen[0].existing_event_id == "old-a"
    assert proposed.title == "Fall concert"


def test_correction_preserves_uid_and_increments_with_overflow_check():
    corrected = correction_candidate(event(), uid="opaque-uid", sequence=4,
                                    corrected_start=date(2026, 1, 4), corrected_end=date(2026, 1, 5))
    assert corrected.uid == "opaque-uid" and corrected.sequence == 5
    with pytest.raises(Exception):
        correction_candidate(event(), uid="opaque-uid", sequence=2_147_483_647,
                             corrected_start=date(2026, 1, 4), corrected_end=date(2026, 1, 5))


def test_timed_events_must_be_aware_and_time_conflict_is_reported():
    with pytest.raises(Exception):
        CalendarEvent("bad", "event", "source-alpha", datetime(2026, 1, 1), datetime(2026, 1, 1, 1))
    left = CalendarEvent("timed", "Event", "source-alpha", datetime(2026, 1, 2, 10, tzinfo=timezone.utc), datetime(2026, 1, 2, 11, tzinfo=timezone.utc), "subject-a")
    right = EvidenceEvent("proof", "Event", "source-beta", datetime(2026, 1, 2, 12, tzinfo=timezone.utc), datetime(2026, 1, 2, 13, tzinfo=timezone.utc), 1, 1.0, "subject-a")
    assert reconcile([left], [right], policy(time_tolerance_seconds=0))[1][0].reason is Reason.TIME_MISMATCH
