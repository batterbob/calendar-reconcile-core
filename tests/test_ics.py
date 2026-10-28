from datetime import UTC, date, datetime

import pytest

from calendar_reconcile_core.errors import CalendarReconcileError
from calendar_reconcile_core.ics import serialize_correction, serialize_event
from calendar_reconcile_core.types import (
    MAX_SEQUENCE,
    CalendarEvent,
    CorrectionCandidate,
)

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def event(**changes: object) -> CalendarEvent:
    values: dict[str, object] = {
        "event_id": "event-a",
        "title": "Synthetic, event; \\ sample",
        "source_id": "source-alpha",
        "start": date(2026, 2, 3),
        "end": date(2026, 2, 4),
        "details": "first line\nsecond line",
    }
    values.update(changes)
    return CalendarEvent(**values)  # type: ignore[arg-type]


def test_all_day_serialization_uses_exclusive_end_and_escapes() -> None:
    result = serialize_event(event(), uid="opaque-uid@example.invalid", now=NOW)
    assert "DTSTART;VALUE=DATE:20260203\r\nDTEND;VALUE=DATE:20260204" in result
    assert "SUMMARY:Synthetic\\, event\\; \\\\ sample" in result
    assert "DESCRIPTION:first line\\nsecond line" in result
    assert result.endswith("END:VCALENDAR\r\n")
    assert "\n" not in result.replace("\r\n", "")


def test_result_is_accepted_by_an_independent_icalendar_parser() -> None:
    from icalendar import Calendar

    parsed = Calendar.from_ical(serialize_event(event(), uid="opaque@example.invalid", now=NOW))
    component = next(item for item in parsed.subcomponents if item.name == "VEVENT")
    assert str(component["UID"]) == "opaque@example.invalid"


def test_timed_events_are_utc_only() -> None:
    timed = event(
        start=datetime(2026, 2, 3, 8, 0, tzinfo=UTC),
        end=datetime(2026, 2, 3, 9, 0, tzinfo=UTC),
    )
    assert "DTSTART:20260203T080000Z" in serialize_event(timed, uid="a", now=NOW)
    other_zone = event(
        start=datetime.fromisoformat("2026-02-03T08:00:00+01:00"),
        end=datetime.fromisoformat("2026-02-03T09:00:00+01:00"),
    )
    with pytest.raises(CalendarReconcileError, match="must be UTC"):
        serialize_event(other_zone, uid="a", now=NOW)


@pytest.mark.parametrize("field", ["title", "details", "location"])
def test_text_control_characters_cannot_inject_properties(field: str) -> None:
    with pytest.raises(CalendarReconcileError, match="control"):
        serialize_event(event(**{field: "safe\x01EVIL:property"}), uid="a", now=NOW)
    with pytest.raises(CalendarReconcileError, match="UID"):
        serialize_event(event(), uid="a\r\nEVIL:property", now=NOW)


def test_folding_respects_octets_and_utf8_boundaries() -> None:
    result = serialize_event(event(title="é" * 80), uid="a", now=NOW)
    physical = result.split("\r\n")
    assert all(len(line.encode("utf-8")) <= 75 for line in physical if line)
    joined = "".join(line.removeprefix(" ") for line in physical if line)
    assert "SUMMARY:" + "é" * 80 in joined


def test_correction_retains_uid_and_increments_sequence() -> None:
    candidate = CorrectionCandidate(
        event_id="event-a",
        uid="stable@example.invalid",
        sequence=5,
        corrected_start=date(2026, 2, 7),
        corrected_end=date(2026, 2, 8),
    )
    result = serialize_correction(event(), candidate, now=NOW)
    assert "UID:stable@example.invalid" in result
    assert "SEQUENCE:5" in result
    assert "DTSTART;VALUE=DATE:20260207" in result


def test_correction_allows_the_maximum_final_sequence() -> None:
    candidate = CorrectionCandidate(
        event_id="event-a",
        uid="stable@example.invalid",
        sequence=MAX_SEQUENCE,
        corrected_start=date(2026, 2, 7),
        corrected_end=date(2026, 2, 8),
    )
    assert "SEQUENCE:2147483647" in serialize_correction(event(), candidate, now=NOW)
