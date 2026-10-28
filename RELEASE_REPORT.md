# 0.1.0rc1 local release report

- Candidate source commit: `9f4685240fe163b42b141b27c0292c90a831271b`
- Publication status: local only; no tag, remote, push, or publication.
- Privacy-gate status: blocked intentionally. The external denylist contains an
  invalid active entry at line 22; the gate fails closed before scanning until
  that entry is corrected by the user.

## Artifacts

| File | SHA-256 |
| --- | --- |
| `calendar_reconcile_core-0.1.0rc1-py3-none-any.whl` | `3f1dd130e9135768834a4f33e703347b724390007a982e30241972a5123bab0c` |
| `calendar_reconcile_core-0.1.0rc1.tar.gz` | `1148b24451f28b6fab6d96cf2225d647820231d0a59549b6de5cc3519decc0e3` |

## Validation completed

- 26 tests passed, plus Ruff and mypy.
- Built wheel and sdist from the candidate source commit.
- Installed the wheel into a new environment; installed metadata reports
  `0.1.0rc1`.
- The final tracked-file, Git-blob, wheel, and sdist privacy scan is pending
  only the denylist correction described above.
