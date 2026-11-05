"""Jails sur l'access.log d'omega-serv (2026-11-02) : fail2ban RETIRE la date qu'il reconnait avant d'appliquer
failregex. L'ancien motif `\\[[^\\]]+\\]` exigeait un caractere entre les crochets : il ne correspondait jamais en
production (craftdark : « Total failed: 0 » malgre 28 x 404 en 28 s), alors qu'un test sur une ligne dont la date
n'etait PAS reconnue passait. Ces tests rejouent donc la vraie lecture de fail2ban."""
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from omega_jail.catalog import load_catalog

REAL_CATALOG = Path(__file__).resolve().parent.parent / "catalog.yaml"
STAMP = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")  # mois anglais, comme omega-serv


def _line(ip: str, request: str, status: int, ua: str = "curl/8", request_id: str = "0123456789abcdef") -> str:
    return f'{ip} - - [{STAMP}] "{request}" {status} 90 "-" "{ua}" {request_id}'


LINES = [
    _line("203.0.113.1", "GET /nope HTTP/1.1", 404),
    _line("203.0.113.2", "GET /zone HTTP/1.1", 401),
    _line("203.0.113.3", "GET /ok HTTP/1.1", 200, request_id="404abcdef0123456"),  # identifiant commencant par 404
    _line("203.0.113.4", "GET /ok HTTP/1.1", 200, ua='x\\x22 404 y'),  # guillemet client echappe par omega-serv
    _line("203.0.113.5", "GET /a\\x22b HTTP/1.1", 404),
    _line("203.0.113.6", "-", 400),  # requete illisible, journalisee depuis omega-serv 2.1.0
    _line("2001:db8::7", "GET /nope HTTP/1.1", 404),
]
EXPECTED = {
    "omega-serv-scan": {"203.0.113.1", "203.0.113.5", "2001:db8::7"},
    "omega-serv-auth-bruteforce": {"203.0.113.2"},
}


def _jail_regex(name: str) -> str:
    jail = next(j for j in load_catalog(REAL_CATALOG).jails if j.name == name)
    assert jail.failregex is not None
    return jail.failregex


def _fail2ban_like(regex: str, line: str) -> str | None:
    """Lecture de fail2ban : date reconnue retiree (il reste « [] »), puis failregex avec <HOST>."""
    stripped = re.sub(r"\[\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4}\]", "[]", line, count=1)
    match = re.search(regex.replace("<HOST>", r"(?P<host>\S+)"), stripped)
    return match.group("host") if match else None


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_access_log_jails_match_after_date_removal(name: str) -> None:
    regex = _jail_regex(name)
    hosts = {host for line in LINES if (host := _fail2ban_like(regex, line))}
    assert hosts == EXPECTED[name]


@pytest.mark.skipif(shutil.which("fail2ban-regex") is None, reason="fail2ban-regex absent")
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_access_log_jails_with_real_fail2ban(name: str, tmp_path: Path) -> None:
    log = tmp_path / "access.log"
    log.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    filter_file = tmp_path / "filter.conf"
    filter_file.write_text(f"[Definition]\nfailregex = {_jail_regex(name)}\nignoreregex =\n", encoding="utf-8")
    out = subprocess.run(["fail2ban-regex", str(log), str(filter_file)], capture_output=True, text=True, check=True).stdout
    assert re.search(rf"Lines: {len(LINES)} lines, 0 ignored, {len(EXPECTED[name])} matched", out), out
