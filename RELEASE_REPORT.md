# 0.1.0rc1 local release report

- Candidate source commit: `95ce25207252346430399548f7a46ea15bb834f9`
- Publication status: local only; no tag, remote, push, or publication.
- Privacy-gate status: passed against tracked files, every Git blob, wheel, and
  sdist using the corrected external denylist.

## Artifacts

| File | SHA-256 |
| --- | --- |
| `calendar_reconcile_core-0.1.0rc1-py3-none-any.whl` | `c76245a6cd09badf0a494a1afd900c60b669ca5e002d1b6e40c96b641d2ba4e5` |
| `calendar_reconcile_core-0.1.0rc1.tar.gz` | `144f2ff56f5e92698b6a70fa1225fdd91f64412442049b68f13c99621d99d2bf` |

## Validation completed

- 29 tests passed, plus Ruff and mypy.
- Built wheel and sdist from the candidate source commit.
- Installed the wheel into a new environment; installed metadata reports
  `0.1.0rc1`.
- Archive lineage passed: every packaged module byte-matches the candidate
  source commit.
- Full privacy receipt: `PASS`.
