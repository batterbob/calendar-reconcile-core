# 0.1.0rc1 release report

- Candidate source commit: `c1d8e372bf98035cb27f8046668650bd8e2ea89d`
- Release target: public GitHub release candidate; no PyPI publication.
- Privacy-gate status: passed against tracked files, every Git blob, wheel, and
  sdist using the corrected external denylist.

## Artifacts

| File | SHA-256 |
| --- | --- |
| `calendar_reconcile_core-0.1.0rc1-py3-none-any.whl` | `e04e41f94e2754f0b0c4d018d4f89076045a20cfca187bb34229e4f2de2018a9` |
| `calendar_reconcile_core-0.1.0rc1.tar.gz` | `698232bd43f53228ba488c34bc1b80e7984e8d72baaec5735adf9d57bdbbd289` |

## Validation completed

- 29 tests passed, plus Ruff and mypy across package, tests, and release tools.
- Built wheel and sdist from the candidate source commit.
- Installed the wheel into a new environment; installed metadata reports
  `0.1.0rc1`.
- Archive lineage passed: every packaged module byte-matches the candidate
  source commit.
- Full candidate privacy receipt: `PASS tracked=23 blobs=48 archive_members=41`.
