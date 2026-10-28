from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def release_gate_module():
    path = Path(__file__).parents[1] / "tools" / "check_release_tree.py"
    spec = importlib.util.spec_from_file_location("release_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_denylist_rejects_the_active_one_character_entry(tmp_path: Path) -> None:
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("- alpha\n" + "header\n" * 20 + "- \n", encoding="utf-8")
    gate = release_gate_module()
    with pytest.raises(gate.ReleaseGateError, match="line 22"):
        gate.load_denylist(denylist)


def test_denylist_is_readable_and_casefolded(tmp_path: Path) -> None:
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("section\n- Example Entry\n", encoding="utf-8")
    assert release_gate_module().load_denylist(denylist) == ("example entry",)
