"""Fail-closed privacy gate for a local release candidate."""
from __future__ import annotations

import argparse
import re
import subprocess
import tarfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
_RESERVED_EMAIL_DOMAINS = frozenset({"example.com", "example.net", "example.org", "example.invalid"})
_GENERIC_PATTERNS = (
    re.compile(rb"-----BEGIN " rb"(?:[A-Z0-9 ]+ )?PRIVATE " rb"KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}\b"),
    re.compile(
        rb"(?i)\b(?:api" rb"[_-]?key|pass" rb"word|sec" rb"ret|to" rb"ken)\s*[:=]\s*[^\s]{8,}"
    ),
    re.compile(rb"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(rb"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(rb"\b(?:\+?1[-. ])?\(?[2-9]\d{2}\)?[-. ]\d{3}[-. ]\d{4}\b"),
)
_EMAIL = re.compile(rb"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)\b")


class ReleaseGateError(Exception):
    """A release input cannot be safely scanned."""


def load_denylist(path: Path) -> tuple[str, ...]:
    """Load explicit ``- value`` entries and reject malformed active entries."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReleaseGateError("private denylist unreadable") from error
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


def _contains_nonreserved_email(payload: bytes) -> bool:
    for match in _EMAIL.finditer(payload):
        domain = match.group(1).decode("ascii").casefold()
        if domain not in _RESERVED_EMAIL_DOMAINS:
            return True
    return False


def _scan_bytes(label: str, payload: bytes, denylist: tuple[str, ...]) -> None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReleaseGateError(f"unreadable release input: {label}") from error
    if any(entry in text.casefold() for entry in denylist):
        raise ReleaseGateError(f"private data in {label}")
    if any(pattern.search(payload) for pattern in _GENERIC_PATTERNS):
        raise ReleaseGateError(f"generic sensitive data in {label}")
    if _contains_nonreserved_email(payload):
        raise ReleaseGateError(f"generic sensitive data in {label}")


def scan_tracked_files(denylist: tuple[str, ...]) -> int:
    paths = _git_bytes(["ls-files", "-z"]).split(b"\0")
    count = 0
    for raw_path in paths:
        if not raw_path:
            continue
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReleaseGateError("unreadable tracked path") from error
        _scan_bytes("tracked filename", raw_path, denylist)
        try:
            _scan_bytes("tracked file", (ROOT / path).read_bytes(), denylist)
        except OSError as error:
            raise ReleaseGateError("unreadable tracked file") from error
        count += 1
    return count


def scan_git_blobs(denylist: tuple[str, ...]) -> int:
    records = _git_text(["cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)"])
    count = 0
    for record in records.splitlines():
        fields = record.split()
        if len(fields) != 2:
            raise ReleaseGateError("invalid Git object enumeration")
        object_id, object_type = fields
        if object_type != "blob":
            continue
        _scan_bytes("Git blob", _git_bytes(["cat-file", "blob", object_id]), denylist)
        count += 1
    return count


def scan_archives(dist: Path, denylist: tuple[str, ...]) -> int:
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ReleaseGateError("expected exactly one wheel and one sdist")
    members = 0
    with ZipFile(wheels[0]) as wheel:
        for wheel_member in wheel.infolist():
            _scan_bytes(
                "wheel member name", wheel_member.filename.encode("utf-8"), denylist
            )
            if not wheel_member.is_dir():
                _scan_bytes("wheel member", wheel.read(wheel_member), denylist)
            members += 1
    with tarfile.open(sdists[0], "r:gz") as sdist:
        for sdist_member in sdist.getmembers():
            _scan_bytes(
                "sdist member name", sdist_member.name.encode("utf-8"), denylist
            )
            if sdist_member.isfile():
                payload = sdist.extractfile(sdist_member)
                assert payload is not None
                _scan_bytes("sdist member", payload.read(), denylist)
            members += 1
    return members


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--denylist", type=Path, required=True)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        denylist = load_denylist(args.denylist)
        tracked = scan_tracked_files(denylist)
        blobs = scan_git_blobs(denylist)
        members = scan_archives(args.dist, denylist)
    except (ReleaseGateError, OSError, tarfile.TarError, BadZipFile, ValueError):
        print("release privacy gate: FAIL")
        return 1
    print(f"release privacy gate: PASS tracked={tracked} blobs={blobs} archive_members={members}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
