"""Fail-closed privacy gate for a local release candidate."""
from __future__ import annotations

import argparse
import subprocess
import tarfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]


class ReleaseGateError(Exception):
    """A release input cannot be safely scanned."""


def load_denylist(path: Path) -> tuple[str, ...]:
    """Load explicit ``- value`` entries and reject malformed active entries."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReleaseGateError("private denylist is unreadable") from error
    entries: list[str] = []
    for number, line in enumerate(lines, start=1):
        if not line.startswith("-"):
            continue
        raw_entry = line[1:]
        if len(raw_entry) <= 1:
            raise ReleaseGateError(f"invalid active denylist entry at line {number}")
        entry = raw_entry.removeprefix(" ").strip()
        if len(entry) < 2:
            raise ReleaseGateError(f"invalid active denylist entry at line {number}")
        entries.append(entry.casefold())
    if not entries:
        raise ReleaseGateError("private denylist has no active entries")
    return tuple(entries)


def _git_text(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReleaseGateError("Git object enumeration failed") from error


def _git_bytes(args: list[str]) -> bytes:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReleaseGateError("Git blob read failed") from error


def _scan_bytes(label: str, payload: bytes, denylist: tuple[str, ...]) -> None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReleaseGateError(f"unreadable release input: {label}") from error
    if any(entry in text.casefold() for entry in denylist):
        raise ReleaseGateError(f"private denylist match in {label}")


def scan_tracked_files(denylist: tuple[str, ...]) -> None:
    paths = _git_bytes(["ls-files", "-z"]).split(b"\0")
    for raw_path in paths:
        if not raw_path:
            continue
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReleaseGateError("unreadable tracked path") from error
        try:
            _scan_bytes(path, (ROOT / path).read_bytes(), denylist)
        except OSError as error:
            raise ReleaseGateError(f"unreadable tracked file: {path}") from error


def scan_git_blobs(denylist: tuple[str, ...]) -> None:
    object_ids = {
        line.split(" ", 1)[0]
        for line in _git_text(["rev-list", "--objects", "--all"]).splitlines()
    }
    for object_id in sorted(object_ids):
        if _git_text(["cat-file", "-t", object_id]) != "blob\n":
            continue
        _scan_bytes(
            f"git-blob:{object_id}",
            _git_bytes(["cat-file", "blob", object_id]),
            denylist,
        )


def scan_archives(dist: Path, denylist: tuple[str, ...]) -> None:
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ReleaseGateError("expected exactly one wheel and one sdist")
    with ZipFile(wheels[0]) as wheel:
        for member in wheel.infolist():
            if not member.is_dir():
                _scan_bytes(f"wheel:{member.filename}", wheel.read(member), denylist)
    with tarfile.open(sdists[0], "r:gz") as sdist:
        for member in sdist.getmembers():
            if member.isfile():
                payload = sdist.extractfile(member)
                assert payload is not None
                _scan_bytes(f"sdist:{member.name}", payload.read(), denylist)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--denylist", type=Path, required=True)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        denylist = load_denylist(args.denylist)
        scan_tracked_files(denylist)
        scan_git_blobs(denylist)
        scan_archives(args.dist, denylist)
    except (ReleaseGateError, OSError, tarfile.TarError, BadZipFile, ValueError) as error:
        print(f"release privacy gate failed: {error}")
        return 1
    print("release privacy gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
