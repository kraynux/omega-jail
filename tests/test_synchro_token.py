# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Jeton d'installation d'omega-jail (contrats d'interconnexion, etape 2 du 2026-11-10). omega-jail
n'importe pas omega-lib : la conformite au format est verifiee ici contre les fichiers temoins
d'omega-lib (si le depot est present sur le poste) et, s'il est importable, par son propre lecteur."""
from __future__ import annotations

import json
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from omega_jail import synchro_token as st
from omega_jail.cli import main

NOW = datetime(2026, 11, 10, 14, 3, tzinfo=timezone.utc)
LIB_FIXTURES = Path.home() / "DEV" / "LIB" / "omega-lib" / "tests" / "fixtures" / "synchro"


def test_created_kept_updated(tmp_path: Path) -> None:
    outcome, token, _ = st.refresh_token(tmp_path, "1.2.1", now=NOW, machine="m1")
    assert outcome == "created" and token is not None
    path = tmp_path / "var" / "omega-jeton.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    assert st.refresh_token(tmp_path, "1.2.1", now=NOW, machine="m1")[0] == "unchanged"
    outcome, updated, _ = st.refresh_token(tmp_path, "1.2.2", now=NOW, machine="m1")
    assert outcome == "updated" and updated is not None
    assert updated["installation_id"] == token["installation_id"]
    assert st.refresh_token(tmp_path, "1.2.2", now=NOW, machine="m2")[0] == "new_id"


def test_copy_gets_new_id(tmp_path: Path) -> None:
    original, copy = tmp_path / "a", tmp_path / "b"
    original.mkdir()
    st.refresh_token(original, "1.2.1", machine="m1")
    (copy / "var").mkdir(parents=True)
    (copy / "var" / "omega-jeton.json").write_bytes((original / "var" / "omega-jeton.json").read_bytes())
    assert st.refresh_token(copy, "1.2.1", machine="m1")[0] == "new_id"


def test_never_as_root_nor_other_account(tmp_path: Path) -> None:
    assert st.refresh_token(tmp_path, "1.2.1", euid=0)[0] == "skipped"
    assert st.refresh_token(tmp_path, "1.2.1", euid=tmp_path.stat().st_uid + 1)[0] == "skipped"
    assert not (tmp_path / "var").exists()


def test_same_fingerprint_as_omega_lib() -> None:
    lib = pytest.importorskip("omega_lib.synchro.policies")
    assert st.machine_fingerprint("abc\n") == lib.machine_fingerprint("abc\n")


def test_token_is_read_by_omega_lib(tmp_path: Path) -> None:
    codec = pytest.importorskip("omega_lib.synchro.codec")
    _outcome, token, _ = st.refresh_token(tmp_path, "1.2.1", now=NOW, machine="m1")
    result = codec.token_from_dict(json.loads(json.dumps(token)))
    assert result.ok, result.detail
    assert result.value.tool == "omega-jail" and result.value.offers == ("jails", "bridge")


@pytest.mark.skipif(not LIB_FIXTURES.is_dir(), reason="fichiers temoins d'omega-lib absents (hors poste de dev)")
@pytest.mark.parametrize(("name", "status"), [
    ("jeton_valide.json", "ok"), ("jeton_champs_inconnus.json", "ok"),
    ("jeton_version_future.json", "incompatible"), ("jeton_tronque.json", "invalid"),
    ("jeton_chemin_relatif.json", "invalid"), ("jeton_mauvais_format.json", "invalid"),
    ("jeton_identifiant_invalide.json", "invalid"),
])
def test_reads_omega_lib_fixtures_like_omega_lib(tmp_path: Path, name: str, status: str) -> None:
    (tmp_path / "var").mkdir()
    (tmp_path / "var" / "omega-jeton.json").write_bytes((LIB_FIXTURES / name).read_bytes())
    assert st.read_token(tmp_path)[0] == status


def test_newer_token_is_not_downgraded(tmp_path: Path) -> None:
    (tmp_path / "var").mkdir()
    future = json.dumps({"format": "omega-jeton", "schema_version": 2})
    (tmp_path / "var" / "omega-jeton.json").write_text(future, encoding="utf-8")
    assert st.refresh_token(tmp_path, "1.2.1")[0] == "skipped"
    assert (tmp_path / "var" / "omega-jeton.json").read_text(encoding="utf-8") == future


def test_cli_usage_for_unknown_synchro_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["synchro", "fiche"]) == 2
    assert "usage" in capsys.readouterr().err
