# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Correctifs du 2026-11-10 (etude de l'interconnecteur, etape 1) : copie systeme du pont, une action par
instance, retrait conditionnel par origine, lecture JSON de la blocklist, journal recree pour un jail deja
installe."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from omega_jail import tailscale_bridge as bridge
from omega_jail.install import (
    ACTION_CONF_FILENAME,
    BRIDGE_SCRIPT_NAME,
    InstallConfig,
    apply,
    bridge_action_name,
    prepare,
    render_bridge_script,
    system_python,
)
from omega_jail.instances import ServInstance

REAL_CATALOG = Path(__file__).resolve().parent.parent / "catalog.yaml"


def _instance(root: Path) -> Path:
    (root / "config").mkdir(parents=True)
    (root / "config" / "omega-serve.json").write_text(
        json.dumps({"options": {"riposte": {"enabled": True, "network_ban_log": True}}}), encoding="utf-8")
    return root


def _config(tmp_path: Path, main: Path, instances: tuple[ServInstance, ...]) -> InstallConfig:
    base = tmp_path / "fail2ban"
    return InstallConfig(
        serv_root=main, omega_jail_root=tmp_path / "jail", jail_d_dir=base / "jail.d", filter_d_dir=base / "filter.d",
        action_d_dir=base / "action.d", bridge_dir=base / "lib", jail_conf_path=base / "jail.conf",
        jail_local_path=base / "jail.local", instances=instances,
    )


def test_bridge_script_runs_without_the_omega_jail_package(tmp_path: Path) -> None:
    script = tmp_path / BRIDGE_SCRIPT_NAME
    script.write_text(render_bridge_script(), encoding="utf-8")
    assert "from omega_jail" not in script.read_text(encoding="utf-8")
    # -I : isole (ni site-packages de l'utilisateur, ni dossier courant) ; Python du systeme, jamais un .venv.
    result = subprocess.run([system_python(), "-I", str(script), "--help"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "--relay-all" in result.stdout
    assert ".venv" not in system_python()


def test_apply_installs_system_copy_and_one_action_per_instance(tmp_path: Path) -> None:
    main = _instance(tmp_path / "main")
    blog = _instance(tmp_path / "blog")
    config = _config(tmp_path, main, (ServInstance("omega-serv", main), ServInstance("omega-serv-blog", blog)))
    report = prepare(config, catalog_path=REAL_CATALOG)
    apply(report, config)

    script = config.bridge_dir / BRIDGE_SCRIPT_NAME
    assert script.exists() and (script.stat().st_mode & 0o777) == 0o755
    main_action = (config.action_d_dir / ACTION_CONF_FILENAME).read_text(encoding="utf-8")
    assert str(script) in main_action and ".venv" not in main_action

    blog_action_name = bridge_action_name(ServInstance("omega-serv-blog", blog))
    assert (config.action_d_dir / f"{blog_action_name}.conf").exists()
    blog_jail = (config.jail_d_dir / "omega-jail-omega-serv-blog-riposte-24h.conf").read_text(encoding="utf-8")
    assert blog_action_name in blog_jail
    main_jail = (config.jail_d_dir / "omega-jail-omega-serv-riposte-24h.conf").read_text(encoding="utf-8")
    assert "omega-jail-tailscale-bridge\n" in main_jail and blog_action_name not in main_jail
    assert not report.action_conf_outdated(config.action_d_dir, config.bridge_dir)


def test_missing_log_of_installed_jail_is_recreated(tmp_path: Path) -> None:
    main = _instance(tmp_path / "main")
    config = _config(tmp_path, main, (ServInstance("omega-serv", main),))
    apply(prepare(config, catalog_path=REAL_CATALOG), config)
    log = main / "var" / "log" / "riposte-decisions.jsonl"
    log.unlink()
    again = prepare(config, catalog_path=REAL_CATALOG)
    assert {a.name: a.outcome for a in again.plan}["omega-serv-riposte-24h"] == "skip_collision"
    apply(again, config)
    assert log.exists()  # sinon fail2ban entier refuse de redemarrer


def _done(code: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


def test_unban_uses_origin_in_one_call() -> None:
    calls: list[list[str]] = []

    def fake(servcli, args):
        calls.append(args)
        return _done(0)

    with patch.object(bridge, "_run_servcli_result", side_effect=fake):
        assert bridge.main(["--ip", "100.70.1.2", "--mode", "unban", "--servcli", "/x/omega-serv",
                            "--jail", "omega-serv-scan"]) == 0
    assert len(calls) == 1
    assert calls[0][-2:] == ["--origin", "omega-jail:omega-serv-scan"]
    assert "remove" in calls[0]


def test_unban_falls_back_when_omega_serv_has_no_origin_option() -> None:
    calls: list[list[str]] = []
    listing = "100.70.1.2/32\tmanual\t2099-01-01T00:00:00+00:00\tomega-jail:omega-serv-scan\n"

    def fake(servcli, args):
        calls.append(args)
        if "--origin" in args:
            return _done(2, stderr="error: unrecognized arguments: --origin")
        if "--format" in args:
            return _done(2, stderr="error: unrecognized arguments: --format")
        if "list" in args:
            return _done(0, stdout=listing)
        return _done(0)

    with patch.object(bridge, "_run_servcli_result", side_effect=fake):
        bridge.main(["--ip", "100.70.1.2", "--mode", "unban", "--servcli", "/x/omega-serv", "--jail", "omega-serv-scan"])
    assert calls[-1][-4:] == ["blocklist", "remove", "--network", "100.70.1.2/32"]


def test_unban_of_another_jail_entry_is_not_removed_in_fallback() -> None:
    listing = "100.70.1.2/32\tmanual\t2099-01-01T00:00:00+00:00\tomega-jail:omega-waf-blocklist-sync\n"
    removed = []

    def fake(servcli, args):
        if "--origin" in args or "--format" in args:
            return _done(2, stderr="unrecognized arguments: --origin --format")
        if "list" in args:
            return _done(0, stdout=listing)
        removed.append(args)
        return _done(0)

    with patch.object(bridge, "_run_servcli_result", side_effect=fake):
        bridge.main(["--ip", "100.70.1.2", "--mode", "unban", "--servcli", "/x/omega-serv", "--jail", "omega-serv-scan"])
    assert removed == []


def test_parse_blocklist_json() -> None:
    output = json.dumps({"schema_version": 1, "entries": [
        {"network": "100.70.1.2/32", "source": "manual", "origin": "omega-jail:omega-serv-scan",
         "created_at": "2026-11-10T10:00:00+00:00", "expires_at": None, "reason": "omega-jail:omega-serv-scan"}]})
    lines = bridge.parse_blocklist_json(output)
    assert lines is not None and lines[0].origin == "omega-jail:omega-serv-scan" and lines[0].expires_at is None
    assert bridge.parse_blocklist_json('{"schema_version": 2, "entries": []}') is None
    assert bridge.parse_blocklist_json("pas du json") is None
