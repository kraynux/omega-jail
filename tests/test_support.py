"""Contact et support d'omega-jail en ligne de commande (2026-11-09). Jamais de vrai envoi : `send`
et `fetch_sha_list` sont remplaces."""
from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from omega_jail import support
from omega_jail.cli import main

KEY = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "omega-jail"\nversion = "1.2.0"\n', encoding="utf-8")
    monkeypatch.setattr("omega_jail.cli._default_omega_jail_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    messages: list[dict] = []

    def fake_send(payload: dict, version: str, url: str = support.RECEPTION_URL) -> str:
        messages.append(payload)
        return ""

    monkeypatch.setattr(support, "send", fake_send)
    return messages


def test_payload_is_omega_jail_once() -> None:
    assert support.build_payload(KEY, "1.2.0", "EU", "FR") == {
        "cle": KEY, "logiciel": "omega-jail", "version": "1.2.0", "envoi": "unique", "continent": "EU", "pays": "FR",
    }
    assert support.build_payload(KEY, "1.2.0") == {"cle": KEY, "logiciel": "omega-jail", "version": "1.2.0",
                                                   "envoi": "unique"}
    with pytest.raises(ValueError):
        support.build_payload(KEY, "1.2.0", "XX", "ZZ")


def test_closed_lists_match_the_reception_script() -> None:
    """Memes pays et meme nom de logiciel que la reception (sinon 400)."""
    php = Path.home() / "DEV/SERV/compteur-reception/index.php"
    if not php.is_file():
        pytest.skip("script de reception absent de cette machine")
    text = php.read_text(encoding="utf-8")
    countries = text.split("const COUNTRIES", 1)[1].split("];", 1)[0]
    assert all(f"'{code}'" in countries for code in support.COUNTRY_CODES)
    assert len(support.COUNTRY_CODES) == 249
    assert "'omega-jail'" in text.split("const SOFTWARES", 1)[1].split("];", 1)[0]


def test_contact_prints_addresses_without_network(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["contact"]) == 0
    out = capsys.readouterr().out
    for text in ("https://paypal.me/kraynux", "kraynux@proton.me", "https://kraynux.snake-mackarel.ts.net/contact/",
                 "non declare", "omega-jail declaration declare"):
        assert text in out


def test_declare_without_yes_only_shows_the_message(root: Path, sent: list[dict],
                                                   capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["declaration", "declare", "--pays", "fr"]) == 1
    out = capsys.readouterr().out
    assert '"logiciel": "omega-jail"' in out and '"pays": "FR"' in out and "--yes" in out
    assert sent == []
    assert not (root / "var" / "declaration.json").exists()


def test_declare_then_status_then_withdraw(root: Path, sent: list[dict], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["declaration", "declare", "--continent", "EU", "--yes"]) == 0
    path = root / "var" / "declaration.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    key = json.loads(path.read_text(encoding="utf-8"))["cle"]
    assert sent == [{"cle": key, "logiciel": "omega-jail", "version": "1.2.0", "envoi": "unique", "continent": "EU"}]
    # Second envoi : meme cle.
    assert main(["declaration", "declare", "--pays", "BE", "--yes"]) == 0
    assert sent[1]["cle"] == key and sent[1]["pays"] == "BE"
    capsys.readouterr()
    assert main(["declaration", "status"]) == 0
    assert key in capsys.readouterr().out
    assert main(["declaration", "withdraw"]) == 1  # sans --yes : rien
    assert path.exists()
    assert main(["declaration", "withdraw", "--yes"]) == 0
    assert sent[-1] == {"cle": key, "retrait": True}
    assert not path.exists()


def test_unreachable_reception_records_nothing(root: Path, monkeypatch: pytest.MonkeyPatch,
                                               capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(support, "send", lambda payload, version, url=support.RECEPTION_URL: "unreachable")
    assert main(["declaration", "declare", "--yes"]) == 1
    assert "rien n'a ete enregistre" in capsys.readouterr().out
    assert not (root / "var" / "declaration.json").exists()


def test_version_check(root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert "omega-jail 1.2.0" in capsys.readouterr().out
    monkeypatch.setattr(support, "fetch_sha_list", lambda version: "a  omega-jail-1.1.1.tar.gz\nb  omega-jail-1.3.0.tar.gz")
    assert main(["version", "--check"]) == 0
    out = capsys.readouterr().out
    assert "Nouvelle version disponible : 1.3.0" in out and "omega-jail-1.3.0.tar.gz" in out
    monkeypatch.setattr(support, "fetch_sha_list", lambda version: "a  omega-jail-1.2.0.tar.gz")
    assert main(["version", "--check"]) == 0
    assert "derniere version publiee" in capsys.readouterr().out
    monkeypatch.setattr(support, "fetch_sha_list", lambda version: None)
    assert main(["version", "--check"]) == 1
