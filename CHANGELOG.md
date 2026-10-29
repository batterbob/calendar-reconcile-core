# Changelog

## Unreleased

- Corrected recurring-event reconciliation so aligned matches suppress cross-date noise, while unmatched date conflicts are aggregated deterministically.
- Fail closed when reconciliation or duplicate-screening findings exceed the configured bound.
- Match timed start and end instants independently, compare both all-day exclusive endpoints, and normalize aware timestamps to UTC for date checks.
- Reject duplicate opaque collection identifiers and DEL characters in RFC 5545 text fields.
- Retained domain-specific title words during normalization and restored the complete Apache-2.0 license text.

## 0.1.0rc1 — 2026-10-28

- Initial public release candidate.
- Provider-neutral immutable models, bounded matching, and fail-closed identity handling.
- Deterministic RFC 5545 generation for all-day and UTC timed events.
