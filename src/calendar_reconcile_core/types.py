"""Immutable provider-neutral calendar contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Protocol

from .errors import CalendarReconcileError

MAX_TEXT = 4096
MAX_ID = 512
MAX_SEQUENCE = 2_147_483_647


def _text(value: str | None, name: str, *, required: bool = False, limit: int = MAX_TEXT) -> None:
    if value is None:
        if required:
            raise CalendarReconcileError(f"{name} is required")
        return
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise CalendarReconcileError(f"invalid {name}")
    if "\x00" in value:
        raise CalendarReconcileError(f"invalid {name}")


def _when(value: date | datetime, name: str) -> None:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise CalendarReconcileError(f"{name} must be timezone-aware")
    elif not isinstance(value, date):
        raise CalendarReconcileError(f"invalid {name}")


def _range(start: date | datetime, end: date | datetime) -> None:
    _when(start, "start")
    _when(end, "end")
    if type(start) is not type(end) or end <= start:
        raise CalendarReconcileError("start and end must be the same temporal type and ordered")


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    event_id: str
    title: str
    source_id: str
    start: date | datetime
    end: date | datetime
    subject_id: str | None = None
    location: str | None = None
    details: str | None = None

    def __post_init__(self) -> None:
        _text(self.event_id, "event_id", required=True, limit=MAX_ID)
        _text(self.source_id, "source_id", required=True, limit=MAX_ID)
        _text(self.subject_id, "subject_id", limit=MAX_ID)
        _text(self.title, "title", required=True)
        _text(self.location, "location")
        _text(self.details, "details")
        _range(self.start, self.end)

    @property
    def is_all_day(self) -> bool:
        return isinstance(self.start, date) and not isinstance(self.start, datetime)


@dataclass(frozen=True, slots=True)
class EvidenceEvent:
    evidence_id: str
    title: str
    source_id: str
    start: date | datetime
    end: date | datetime
    source_rank: int
    confidence: float
    subject_id: str | None = None
    location: str | None = None
    details: str | None = None

    def __post_init__(self) -> None:
        _text(self.evidence_id, "evidence_id", required=True, limit=MAX_ID)
        _text(self.source_id, "source_id", required=True, limit=MAX_ID)
        _text(self.subject_id, "subject_id", limit=MAX_ID)
        _text(self.title, "title", required=True)
        _text(self.location, "location")
        _text(self.details, "details")
        _range(self.start, self.end)
        if not isinstance(self.source_rank, int) or self.source_rank < 0:
            raise CalendarReconcileError("invalid source_rank")
        if not isinstance(self.confidence, (int, float)) or not 0 <= self.confidence <= 1:
            raise CalendarReconcileError("invalid confidence")

    @property
    def is_all_day(self) -> bool:
        return isinstance(self.start, date) and not isinstance(self.start, datetime)


@dataclass(frozen=True, slots=True)
class SubjectResolution:
    subject_id: str | None
    confidence: float
    ambiguous: bool = False

    def __post_init__(self) -> None:
        _text(self.subject_id, "subject_id", limit=MAX_ID)
        if not isinstance(self.confidence, (int, float)) or not 0 <= self.confidence <= 1:
            raise CalendarReconcileError("invalid confidence")
        if self.ambiguous and self.subject_id is not None:
            raise CalendarReconcileError("ambiguous resolution cannot select a subject")


class SubjectResolver(Protocol):
    def resolve(self, *, normalized_title: tuple[str, ...], source_id: str) -> SubjectResolution: ...


class Reason(str, Enum):
    AGREEMENT = "agreement"
    DATE_MISMATCH = "date_mismatch"
    TIME_MISMATCH = "time_mismatch"
    SOURCE_DISAGREEMENT = "source_disagreement"
    AMBIGUOUS_MATCH = "ambiguous_match"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class Agreement:
    event_id: str
    evidence_ids: tuple[str, ...]
    reason: Reason = Reason.AGREEMENT


@dataclass(frozen=True, slots=True)
class Conflict:
    event_id: str
    evidence_ids: tuple[str, ...]
    reason: Reason


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    proposed_event_id: str
    existing_event_id: str
    similarity: float
    reason: Reason = Reason.DUPLICATE


@dataclass(frozen=True, slots=True)
class CorrectionCandidate:
    event_id: str
    uid: str
    sequence: int
    corrected_start: date | datetime
    corrected_end: date | datetime
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _text(self.uid, "uid", required=True, limit=MAX_ID)
        _range(self.corrected_start, self.corrected_end)
        if not isinstance(self.sequence, int) or not 0 <= self.sequence <= MAX_SEQUENCE:
            raise CalendarReconcileError("invalid sequence")
