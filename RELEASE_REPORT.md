# 0.1.0rc1 local release report

- Candidate source commit: `47315cdc731ee5b5d4f85745056463194c29fe45`
- Publication status: local only; no tag, remote, push, or publication.
- Privacy-gate status: passed against tracked files, every Git blob, wheel, and
  sdist using the corrected external denylist.

## Artifacts

| File | SHA-256 |
| --- | --- |
| `calendar_reconcile_core-0.1.0rc1-py3-none-any.whl` | `0df5e20d1fb41cb39a8eedb7c205e82ae161d4437a5b1ca9862ed034cd87ba03` |
| `calendar_reconcile_core-0.1.0rc1.tar.gz` | `f6a7ea000901d5d8cbbcaa6fcedcd4bce6fd024919b89683143e1412aa551f21` |

## Validation completed

- 29 tests passed, plus Ruff and mypy across package, tests, and release tools.
- Built wheel and sdist from the candidate source commit.
- Installed the wheel into a new environment; installed metadata reports
  `0.1.0rc1`.
- Archive lineage passed: every packaged module byte-matches the candidate
  source commit.
- Full privacy receipt: `PASS tracked=23 blobs=44 archive_members=41`.
