from pathlib import Path

import pytest

import omega_jail.autodetect as autodetect_module
from omega_jail.autodetect import find_fail2ban_base_dir


def test_find_fail2ban_base_dir_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_base = tmp_path / "etc" / "fail2ban"
    fake_base.mkdir(parents=True)
    monkeypatch.setattr(autodetect_module, "DEFAULT_FAIL2BAN_BASE_DIR", fake_base)
    assert find_fail2ban_base_dir() == fake_base


def test_find_fail2ban_base_dir_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autodetect_module, "DEFAULT_FAIL2BAN_BASE_DIR", tmp_path / "does-not-exist")
    assert find_fail2ban_base_dir() is None
