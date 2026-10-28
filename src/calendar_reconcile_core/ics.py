"""Pure, injection-resistant RFC 5545 serialization.

Version 0.1 emits either all-day values or UTC timed values.  It deliberately
does not manufacture ``VTIMEZONE`` components, so non-UTC timed values are
rejected instead of being rendered with ambiguous semantics.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Final

from .errors import CalendarReconcileError
from .types import MAX_SEQUENCE, CalendarEvent, CorrectionCandidate

PRODID: Final = "-//calendar-reconcile-core//EN"
_DISALLOWED_CONTROLS: Final = frozenset(chr(value) for value in range(32)) - {
    "\n",
    "\r",
    "\t",
}


def _safe_text(value: str, field: str) -> str:
    if "\x00" in value or any(char in _DISALLOWED_CONTROLS for char in value):
        raise CalendarReconcileError(f"invalid control character in {field}")
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")


def _safe_uid(uid: str) -> str:
    if not uid or len(uid) > 512 or any(ord(char) < 33 or ord(char) == 127 for char in uid):
        raise CalendarReconcileError("invalid UID")
    return uid


def _utc_timestamp(value: datetime, field: str) -> str:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise CalendarReconcileError(f"{field} must be UTC")
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _event_time_lines(start: date | datetime, end: date | datetime) -> list[str]:
    if isinstance(start, datetime):
        if not isinstance(end, datetime):  # protected by immutable contract
            raise CalendarReconcileError("timed event needs a timed end")
        return [f"DTSTART:{_utc_timestamp(start, 'start')}", f"DTEND:{_utc_timestamp(end, 'end')}"]
    if isinstance(end, datetime):
        raise CalendarReconcileError("all-day event needs a date end")
    return [
        f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
    ]


def _fold(line: str) -> list[str]:
    """Fold a content line at 75 UTF-8 octets without splitting code points."""
    pieces: list[str] = []
    current = ""
    limit = 75
    for char in line:
        encoded = char.encode("utf-8")
        if len(encoded) > limit:
            raise CalendarReconcileError("unsupported character width")
        if current and len(current.encode("utf-8")) + len(encoded) > limit:
            pieces.append(current)
            current = " " + char
            limit = 74
        else:
            current += char
    pieces.append(current)
    return pieces


def _render(lines: list[str]) -> str:
    return "\r\n".join(part for line in lines for part in _fold(line)) + "\r\n"


def serialize_event(event: CalendarEvent, *, uid: str, now: datetime, sequence: int = 0) -> str:
    """Serialize one caller-approved event with an injected UTC timestamp."""
    if not isinstance(sequence, int) or not 0 <= sequence <= MAX_SEQUENCE:
        raise CalendarReconcileError("invalid sequence")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{_safe_uid(uid)}",
        f"DTSTAMP:{_utc_timestamp(now, 'now')}",
        f"SEQUENCE:{sequence}",
        *_event_time_lines(event.start, event.end),
        f"SUMMARY:{_safe_text(event.title, 'title')}",
    ]
    if event.location is not None:
        lines.append(f"LOCATION:{_safe_text(event.location, 'location')}")
    if event.details is not None:
        lines.append(f"DESCRIPTION:{_safe_text(event.details, 'details')}")
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    return _render(lines)


def serialize_correction(event: CalendarEvent, correction: CorrectionCandidate, *, now: datetime) -> str:
    """Serialize an update retaining caller UID and final emitted SEQUENCE."""
    if correction.event_id != event.event_id:
        raise CalendarReconcileError("correction event_id does not match event")
    corrected = CalendarEvent(
        event_id=event.event_id,
        title=event.title,
        source_id=event.source_id,
        start=correction.corrected_start,
        end=correction.corrected_end,
        subject_id=event.subject_id,
        location=event.location,
        details=event.details,
    )
    return serialize_event(
        corrected, uid=correction.uid, now=now, sequence=correction.sequence
    )
