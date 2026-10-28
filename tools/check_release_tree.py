"""Reject private/product vocabulary and obvious credential material in release inputs."""
from __future__ import annotations

import re
import subprocess
import tarfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
# Join fragments so this checker can scan Git history without matching its own
# denylist. These are never emitted or logged.
FORBIDDEN = (
    "daily" + "brief",
    "parent" + "vue",
    "fast" + "mail",
    "can" + "vas",
    "ho" + "mer",
)
SENSITIVE_PATTERN = re.compile(
    r"(?i)(api[_-]?key|pass" r"word|sec" r"ret|to" r"ken)\s*[:=]\s*[^\s<]{8,}"
)
SKIP = {
    ".git", ".hypothesis", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__",
    ".venv", ".validation-venv", ".smoke-venv", "dist", "build",
}


def checked_texts() -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for path in ROOT.rglob("*"):
        if (not path.is_file() or any(part in SKIP for part in path.parts)
                or path == Path(__file__).resolve()):
            continue
        try:
            texts.append((str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            raise SystemExit(f"non-UTF-8 release input: {path}")
    for label, args in (("git history", ["git", "log", "--all", "--format=%B", "-p"]),):
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=True)
        texts.append((label, result.stdout))
    dist = ROOT / "dist"
    if dist.is_dir():
        for archive in dist.iterdir():
            if archive.suffix == ".whl":
                with ZipFile(archive) as wheel:
                    for member in wheel.infolist():
                        if not member.is_dir():
                            texts.append((f"{archive.name}:{member.filename}", wheel.read(member).decode("utf-8")))
            elif archive.name.endswith(".tar.gz"):
                with tarfile.open(archive, "r:gz") as sdist:
                    for member in sdist.getmembers():
                        if member.isfile():
                            data = sdist.extractfile(member)
                            assert data is not None
                            texts.append((f"{archive.name}:{member.name}", data.read().decode("utf-8")))
    return texts


def main() -> int:
    failures = []
    for name, content in checked_texts():
        folded = content.casefold()
        if any(term in folded for term in FORBIDDEN) or SENSITIVE_PATTERN.search(content):
            failures.append(name)
    if failures:
        print("release privacy/secret gate failed:", ", ".join(sorted(failures)))
        return 1
    print("release tree check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
