# 0.1.0rc2 draft release report

- Candidate source commit: pending merge of the RC2 release-preparation pull
  request.
- Release target: public GitHub release candidate; no PyPI publication.
- Artifact build, hashes, lineage verification, and clean-install smoke tests:
  pending from the final candidate commit.
- Privacy-gate status: pending an independent, fail-closed scan using the
  caller-supplied private denylist. No privacy receipt is claimed in this draft.

## Artifacts

| File | SHA-256 |
| --- | --- |
| `calendar_reconcile_core-0.1.0rc2-py3-none-any.whl` | Pending final-candidate build |
| `calendar_reconcile_core-0.1.0rc2.tar.gz` | Pending final-candidate build |

## Required release validation

- Run the full test, Ruff, and mypy suites from the final candidate commit.
- Build wheel and sdist artifacts from that commit, then record their SHA-256
  hashes and archive-lineage receipts here.
- Install both artifacts in clean environments and verify their metadata reports
  `0.1.0rc2`.
- Run `tools/check_release_tree.py` with the supplied private denylist against
  the final candidate and its artifacts. Promotion remains blocked until it
  passes.
