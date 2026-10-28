from datetime import UTC, date

from hypothesis import given
from hypothesis import strategies as st

from calendar_reconcile_core import CalendarEvent, EvidenceEvent, ReconcilePolicy
from calendar_reconcile_core.ics import serialize_event
from calendar_reconcile_core.reconcile import reconcile


@given(st.lists(st.sampled_from(["alpha", "beta", "gamma"]), min_size=1, max_size=3, unique=True))
def test_reconciliation_is_independent_of_input_order(source_ids: list[str]) -> None:
    event = CalendarEvent("event", "Synthetic event", "calendar", date(2031, 1, 2), date(2031, 1, 3), "subject-a")
    evidence = [
        EvidenceEvent(f"e-{source}", "Synthetic event", source, date(2031, 1, 2), date(2031, 1, 3), 1, 0.9, "subject-a")
        for source in source_ids
    ]
    policy = ReconcilePolicy(allowed_sources=frozenset({"calendar", *source_ids}))
    forward = reconcile([event], evidence, policy)
    backward = reconcile([event], list(reversed(evidence)), policy)
    assert forward == backward


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=200))
def test_serialization_is_deterministic_and_never_creates_extra_lines(title: str) -> None:
    from datetime import datetime

    now = datetime(2031, 1, 1, tzinfo=UTC)
    try:
        event = CalendarEvent("event", title, "source", date(2031, 1, 2), date(2031, 1, 3))
        one = serialize_event(event, uid="opaque@example.invalid", now=now)
    except ValueError:
        return  # Empty/NUL/control content is deliberately rejected.
    assert one == serialize_event(event, uid="opaque@example.invalid", now=now)
    assert all(line.startswith((" ", "BEGIN", "VERSION", "PRODID", "CALSCALE", "UID", "DTSTAMP", "SEQUENCE", "DTSTART", "DTEND", "SUMMARY", "END")) for line in one.split("\r\n") if line)
