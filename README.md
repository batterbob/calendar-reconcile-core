# calendar-reconcile-core

`calendar-reconcile-core` is a provider-neutral Python library for comparing
already-normalized calendar events with independent evidence. It produces
bounded, deterministic agreements, conflicts, duplicate candidates, correction
candidates, and RFC 5545 output without connecting to or mutating a calendar.

It is a library, not a calendar service. The package has no provider connectors,
credentials, network access, persistence, delivery behavior, roster, scheduler,
telemetry, or UI. Callers own those boundaries and decide whether any result is
safe to present or apply.

Version `0.1.x` is a release-candidate API and may change before a stable release.

## Why use it?

Calendar data often arrives from multiple sources that disagree about identity,
dates, times, and titles. This package keeps the risky policy decisions visible:

- sources must be explicitly allowed;
- subject identities are opaque and caller supplied;
- ambiguous or unresolved identity fails closed;
- fuzzy title comparison happens only after identity and date gates;
- source rank orders processing but never silently makes a source authoritative;
- work and output are bounded by policy; an additional finding beyond the configured output cap fails closed rather than truncating results;
- duplicate screening returns candidates and never deletes an event;
- corrections preserve caller-owned UID values and increment sequence numbers;
- serialization uses an injected clock and rejects ambiguous timed output.

```text
provider APIs or exports
          │
          ▼
caller-owned adapters and identity policy
          │ normalized immutable events
          ▼
calendar-reconcile-core
          │
          ├── agreements and conflicts
          ├── duplicate candidates
          ├── correction candidates
          └── safe RFC 5545 text
                    │
                    ▼
          caller review and delivery
```

## What it does not do

The package deliberately does not:

- fetch, create, update, or delete calendar events;
- authenticate users or manage provider credentials;
- infer a person from an event title;
- choose an authoritative source;
- turn a conflict into an automatic correction;
- send invitations, updates, or cancellations;
- emit `VTIMEZONE` components;
- provide process isolation for untrusted adapters.

## Installation

The project is not currently published on PyPI. Download the wheel from the
`v0.1.0-rc2` GitHub release candidate, verify its published SHA-256 value, and
install it locally:

```bash
python -m pip install ./calendar_reconcile_core-0.1.0rc2-py3-none-any.whl
```

Python 3.11 or newer is required. The runtime package uses only the Python
standard library.

For development:

```bash
git clone <repository-url>
cd calendar-reconcile-core
python -m pip install -e ".[test,lint,type,build]"
python -m pytest
```

## End-to-end example

The example uses synthetic identifiers and events. Matching returns data only;
the caller decides what, if anything, should happen next.

```python
from datetime import date, datetime, timezone

from calendar_reconcile_core import (
    CalendarEvent,
    EvidenceEvent,
    ReconcilePolicy,
    serialize_event,
)
from calendar_reconcile_core.reconcile import reconcile

event = CalendarEvent(
    event_id="event-1",
    subject_id="subject-a",
    source_id="source-alpha",
    title="Sample meeting",
    start=date(2030, 4, 2),
    end=date(2030, 4, 3),  # exclusive end for an all-day event
)
evidence = EvidenceEvent(
    evidence_id="evidence-1",
    subject_id="subject-a",
    source_id="source-beta",
    source_rank=10,
    confidence=0.9,
    title="Sample meeting",
    start=date(2030, 4, 3),
    end=date(2030, 4, 4),
)
policy = ReconcilePolicy(
    allowed_sources=frozenset({"source-alpha", "source-beta"}),
)

agreements, conflicts = reconcile([event], [evidence], policy)
assert not agreements
assert conflicts[0].reason.value == "date_mismatch"

ics = serialize_event(
    event,
    uid="event-1@example.invalid",
    now=datetime(2030, 1, 1, tzinfo=timezone.utc),
)
assert "DTSTART;VALUE=DATE:20300402" in ics
```

## Core concepts

### Immutable event contracts

`CalendarEvent` represents an existing or proposed calendar event.
`EvidenceEvent` represents independent evidence and adds caller-supplied rank
and confidence fields. IDs are opaque; the library does not parse or assign
meaning to them. All-day events use `date`, while timed events use aware
`datetime` values.

### Reconciliation policy

`ReconcilePolicy` makes source, matching, ambiguity, and resource limits
explicit. The v0.1 defaults include a `0.75` title threshold, no date or time
tolerance, a 10,000-comparison cap, and subjectless matching disabled.

Title similarity uses normalized token-set Jaccard similarity. It is evidence
for a match, not identity proof. A resolver may supply an opaque subject ID, but
ambiguous or missing resolver results do not fall back to subjectless matching.
Timed matches require both start and end instants to be within the configured
time tolerance; all-day matches compare both exclusive date endpoints. Aware
timestamps are compared as instants in UTC for date compatibility.

### Reconciliation outcomes

`reconcile` returns immutable `Agreement` and `Conflict` tuples in stable order.
Conflicts distinguish date, time, and source disagreement. Rank and precedence
control deterministic traversal only; they never resolve a disagreement by
themselves. Similar-title evidence on different dates is aggregated into one
date conflict only when no aligned match exists for that event.

### Duplicate screening

`screen_duplicates` compares proposed events with existing events and returns
`DuplicateCandidate` values. Tied candidates are either skipped or reported as
`AmbiguousDuplicateCandidate`, according to policy. If another candidate would
exceed `max_findings`, both reconciliation and duplicate screening raise
`BoundsError` rather than returning a partial result. Nothing is mutated or
deleted.

### Corrections and RFC 5545

`correction_candidate` retains the caller's UID, increments the sequence, and
returns a candidate rather than delivering it. `serialize_event` and
`serialize_correction` escape text, reject unsafe controls, fold lines at 75
UTF-8 octets, and require an explicit UTC clock.

Version 0.1 serializes date-only all-day events and UTC timed events. Non-UTC
timed serialization fails closed because the package does not manufacture an
incomplete `VTIMEZONE` component.

## Module map

| Module | Responsibility |
| --- | --- |
| `calendar_reconcile_core.types` | Immutable event and outcome contracts |
| `calendar_reconcile_core.policy` | Caller-owned matching and resource policy |
| `calendar_reconcile_core.normalize` | Deterministic title normalization |
| `calendar_reconcile_core.match` | Identity, date, time, and title gates |
| `calendar_reconcile_core.reconcile` | Reconciliation, duplicates, and corrections |
| `calendar_reconcile_core.ics` | Injection-resistant RFC 5545 serialization |
| `calendar_reconcile_core.errors` | Stable refusal exception hierarchy |

## Privacy and security boundaries

Event titles, locations, details, IDs, and generated calendar text can all be
sensitive. The package performs no logging or telemetry, but applications must
still prevent those values from entering logs, traces, exceptions, analytics,
issues, and test output.

Callers remain responsible for:

- consent, authentication, authorization, and retention;
- securing provider credentials and raw calendar exports;
- defining the identity resolver and allowed-source policy;
- reviewing conflicts and correction candidates before delivery;
- preventing adapters from making unsafe network requests;
- protecting stored and transmitted RFC 5545 content.

Report vulnerabilities through GitHub's private **Report a vulnerability**
form, not a public issue. See [SECURITY.md](SECURITY.md).

## Development and release verification

The repository contains only synthetic fixtures. Real calendar contents,
credentials, subject identifiers, and private deployment details are prohibited
in code, documentation, commits, issues, and test output.

Run the ordinary checks with:

```bash
python -m pytest
python -m ruff check src tests tools
python -m mypy src tools
python -m build
```

Release verification also requires a caller-supplied private denylist. The gate
fails closed for a missing, unreadable, or malformed denylist, and scans tracked
filenames and contents, every Git blob, and wheel/sdist member names and contents.
It emits only pass/fail receipts:

```bash
python tools/check_release_tree.py \
  --denylist /path/to/private-denylist.txt \
  --dist dist
```

See [CHANGELOG.md](CHANGELOG.md) for release notes and
[RELEASE_REPORT.md](RELEASE_REPORT.md) for the local candidate evidence.
