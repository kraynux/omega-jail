# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Action fail2ban du journal des bans (plan omega-connect, phase 3, 2026-11-21)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from omega_jail import ban_journal
from omega_jail.existing_jails import read_jail_actions
from omega_jail.install import (
    JOURNAL_OVERRIDE_FILENAME,
    render_journal_action_conf,
    render_journal_override,
    render_journal_script,
)
from omega_jail.render import JOURNAL_ACTION_NAME

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
OMEGA_LIB_SRC = Path.home() / "DEV" / "LIB" / "omega-lib" / "src"


def _zone(tmp_path: Path) -> Path:
    (tmp_path / "bans").mkdir()
    return tmp_path


def _lines(zone: Path) -> list[dict]:
    path = zone / "bans" / "journal.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _active(zone: Path) -> dict:
    return json.loads((zone / "bans" / "actifs.json").read_text())


def test_ban_levee_et_doublons(tmp_path: Path) -> None:
    zone = _zone(tmp_path)
    ban = ban_journal.build_event("ban", "203.0.113.7", "sshd", 3600, NOW)
    assert ban_journal.record(ban, zone=zone, now=NOW) == "written"
    again = ban_journal.build_event("ban", "203.0.113.7", "sshd", 3600, NOW)
    assert ban_journal.record(again, zone=zone, now=NOW) == "unchanged"
    assert _active(zone)["entries"][0]["origin"] == "fail2ban:sshd"
    assert _active(zone)["entries"][0]["expires_at"] == "2026-11-21T13:00:00Z"
    unban = ban_journal.build_event("unban", "203.0.113.7", "sshd", None, NOW)
    assert ban_journal.record(unban, zone=zone, now=NOW) == "written"
    assert [line["action"] for line in _lines(zone)] == ["ban", "unban"]
    assert "expires_at" not in _lines(zone)[1]
    assert _active(zone)["entries"] == []


def test_ban_permanent_et_origine_riposte(tmp_path: Path) -> None:
    event = ban_journal.build_event("ban", "::ffff:198.51.100.4", "omega-serv-riposte-404", -1, NOW)
    assert event["network"] == "198.51.100.4/32" and event["expires_at"] is None
    assert event["origin"] == "fail2ban:omega-serv-riposte-404"
    assert ban_journal.build_event("ban", "pas-une-ip", "sshd", 60, NOW) is None
    assert ban_journal.jail_origin("Mon Jail!") == "fail2ban:mon-jail"


def test_sans_zone_et_lien_jamais_suivi(tmp_path: Path) -> None:
    event = ban_journal.build_event("ban", "203.0.113.7", "sshd", 60, NOW)
    assert ban_journal.record(event, zone=tmp_path / "absente", now=NOW) == "no-zone"
    zone = _zone(tmp_path)
    victime = tmp_path / "victime"
    victime.write_text("intact\n")
    (zone / "bans" / "journal.jsonl").symlink_to(victime)
    with pytest.raises(OSError):
        ban_journal.record(event, zone=zone, now=NOW)
    assert victime.read_text() == "intact\n"


def test_script_autonome_fail_open(tmp_path: Path) -> None:
    script = tmp_path / "omega-jail-ban-journal.py"
    script.write_text(render_journal_script(), encoding="utf-8")
    (tmp_path / "zone").mkdir()
    zone = _zone(tmp_path / "zone")
    env = {**os.environ, "OMEGA_SYNCHRO_DIR": str(zone)}
    run = subprocess.run([sys.executable, "-I", str(script), "--mode=ban", "--ip=203.0.113.7", "--jail=sshd",
                          "--bantime=600"], env=env, capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    assert _lines(zone)[0]["network"] == "203.0.113.7/32"
    bad = subprocess.run([sys.executable, "-I", str(script), "--mode=ban"], env=env, capture_output=True,
                         check=False)
    assert bad.returncode == 0  # jamais un echec vu par fail2ban


def test_conforme_au_lecteur_et_a_l_ecrivain_d_omega_lib(tmp_path: Path) -> None:
    if not OMEGA_LIB_SRC.is_dir():
        pytest.skip("omega-lib absente (hors poste de developpement)")
    sys.path.insert(0, str(OMEGA_LIB_SRC))
    try:
        from omega_lib.infrastructure.synchro.ban_journal import read_active_bans, read_ban_journal
        from omega_lib.infrastructure.synchro.ban_writer import new_ban_event, record_ban_events
        from omega_lib.synchro.models import BanAction
    finally:
        sys.path.remove(str(OMEGA_LIB_SRC))
    zone = _zone(tmp_path)
    ban_journal.record(ban_journal.build_event("ban", "203.0.113.7", "sshd", 600, NOW), zone=zone, now=NOW)
    assert record_ban_events([new_ban_event(BanAction.BAN, "192.0.2.1", "omega-fire:manual", now=NOW, host="h")],
                             zone=zone, now=NOW).ok
    ban_journal.record(ban_journal.build_event("unban", "192.0.2.1", "x", None, NOW), zone=zone, now=NOW)
    journal = read_ban_journal(zone / "bans" / "journal.jsonl")
    assert journal.invalid_lines == 0 and journal.incompatible_lines == 0
    assert [(e.origin, e.action.value) for e in journal.events] == [
        ("fail2ban:sshd", "ban"), ("omega-fire:manual", "ban")]
    active = read_active_bans(zone / "bans" / "actifs.json").value
    assert {(e.network, e.origin) for e in active.entries} == {
        ("203.0.113.7/32", "fail2ban:sshd"), ("192.0.2.1/32", "omega-fire:manual")}


def test_action_et_jails_existants(tmp_path: Path) -> None:
    conf = render_journal_action_conf("/usr/bin/python3 /usr/local/lib/omega-jail/omega-jail-ban-journal.py")
    assert "actionban = /usr/bin/python3 /usr/local/lib/omega-jail/omega-jail-ban-journal.py --mode=ban" in conf
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    (tmp_path / "jail.conf").write_text("[DEFAULT]\naction = %(action_)s\n[sshd]\nport = ssh\n[postfix]\n")
    (tmp_path / "jail.local").write_text("[DEFAULT]\naction = %(action_mwl)s\n[postfix]\naction = %(action_)s\n"
                                         "         sendmail-whois\nenabled = true\n")
    (jail_d / JOURNAL_OVERRIDE_FILENAME).write_text("[sshd]\naction = ancienne\n")  # jamais relue
    actions = read_jail_actions(["sshd", "postfix", "absent"], str(jail_d), str(tmp_path / "jail.conf"),
                                str(tmp_path / "jail.local"), exclude_filename=JOURNAL_OVERRIDE_FILENAME)
    assert actions == {"sshd": "%(action_mwl)s", "postfix": "%(action_)s\nsendmail-whois", "absent": None}
    override = render_journal_override({k: v for k, v in actions.items() if v})
    assert "[sshd]\naction = %(action_mwl)s\n         omega-jail-ban-journal\n" in override
    assert "[postfix]\naction = %(action_)s\n         sendmail-whois\n         omega-jail-ban-journal\n" in override
    assert render_journal_override({}) == ""
    twice = render_journal_override({"sshd": f"%(action_)s\n{JOURNAL_ACTION_NAME}"})
    assert twice.count(JOURNAL_ACTION_NAME) == 1
