# calendar-reconcile-core

`calendar-reconcile-core` is a small, standard-library runtime package for
comparing already-normalized calendar evidence. It has no connector,
credential, calendar-store, delivery, roster, provider, or deployment code.

The core treats event contents as sensitive. Applications should avoid putting
titles, locations, details, or opaque subject IDs in logs and assertion output.

## Scope

Callers own every boundary concern: fetching data, mapping it to neutral
objects, resolving identities, selecting allowed sources and precedence, and
deciding whether an outcome becomes a human-facing action. The core never
extracts a person from an event title and never mutates a calendar.

Version 0.1 accepts date-only all-day events and UTC timed events. It rejects
non-UTC timed serialization rather than emitting an incomplete `VTIMEZONE`.

## Example

```python
from datetime import date, datetime, timezone

from calendar_reconcile_core import CalendarEvent, EvidenceEvent, ReconcilePolicy
from calendar_reconcile_core.ics import serialize_event
from calendar_reconcile_core.reconcile import reconcile

event = CalendarEvent(
    event_id="event-1", subject_id="subject-a", source_id="source-alpha",
    title="Sample meeting", start=date(2030, 4, 2), end=date(2030, 4, 3),
)
evidence = EvidenceEvent(
    evidence_id="evidence-1", subject_id="subject-a", source_id="source-beta",
    source_rank=10, confidence=0.9, title="Sample meeting",
    start=date(2030, 4, 3), end=date(2030, 4, 4),
)
policy = ReconcilePolicy(allowed_sources=frozenset({"source-alpha", "source-beta"}))
agreements, conflicts = reconcile([event], [evidence], policy)
assert not agreements
assert conflicts  # a machine-readable disagreement; the caller decides next steps

ics = serialize_event(
    event, uid="event-1@example.invalid",
    now=datetime(2030, 1, 1, tzinfo=timezone.utc),
)
```

## Security model

Matching is deterministic, bounded, and uses opaque subject IDs. If identity
is absent, events match only when `allow_subjectless_matches=True`; ambiguous
resolver results fail closed. All source policy is caller supplied. RFC 5545
serialization escapes text, rejects control characters/property injection,
folds at 75 UTF-8 octets, and requires an injected clock.

This library is deliberately not source-compatible with any private adapter.
It is not a calendar client and does not create delivery behavior.
