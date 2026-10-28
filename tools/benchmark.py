"""Run deterministic local reconciliation measurements; it makes no files."""
from __future__ import annotations

import tracemalloc
from datetime import date
from time import perf_counter

from calendar_reconcile_core import CalendarEvent, EvidenceEvent, ReconcilePolicy
from calendar_reconcile_core.reconcile import reconcile


def measure(size: int) -> None:
    event = CalendarEvent("event", "Synthetic event", "source-a", date(2031, 1, 2), date(2031, 1, 3), "subject-a")
    evidence = [EvidenceEvent(f"e-{index}", "Synthetic event", "source-b", date(2031, 1, 2), date(2031, 1, 3), 1, 1.0, "subject-a") for index in range(size)]
    policy = ReconcilePolicy(allowed_sources=frozenset({"source-a", "source-b"}), max_evidence=size, max_candidate_comparisons=size, max_findings=size)
    tracemalloc.start()
    start = perf_counter()
    reconcile([event], evidence, policy)
    elapsed = perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"evidence={size} comparisons={size} seconds={elapsed:.6f} peak_bytes={peak}")


if __name__ == "__main__":
    for count in (100, 1_000):
        measure(count)
