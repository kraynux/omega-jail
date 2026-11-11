"""Jails RIPOSTE (omega-serv 2.1.0, lot 6) : un jail par duree ET par instance omega-serv, sur le journal
riposte-decisions.jsonl de chaque instance ; detection des instances (unites systemd + registre d'omega-serv)."""
import json
import re
from pathlib import Path

from omega_jail.catalog import load_catalog
from omega_jail.detect import detect
from omega_jail.install import InstallConfig, apply, prepare
from omega_jail.instances import ServInstance, detect_instances

REAL_CATALOG = Path(__file__).resolve().parent.parent / "catalog.yaml"

# Ligne reelle ecrite par omega-serv (domain/security/riposte/network_ban.py::network_ban_line).
OMEGA_SERV_LINE = ('{"timestamp": "2026-11-02T10:00:00+00:00", "event": "network_ban", "remote_ip": "203.0.113.7", '
                   '"jail": "6h", "jail_seconds": 21600, "duration_seconds": 43200, "tier": 2, "policy_id": "scan", '
                   '"action_id": "a1b2c3d4e5f6"}')


def _instance(root: Path, *, riposte: bool = True, network_ban_log: bool = True) -> Path:
    (root / "config").mkdir(parents=True)
    options = {"riposte": {"enabled": riposte, "network_ban_log": network_ban_log}} if riposte is not None else {}
    (root / "config" / "omega-serve.json").write_text(json.dumps({"options": options}), encoding="utf-8")
    return root


def _fail2ban_match(failregex: str, line: str) -> str | None:
    """Comme fail2ban : <HOST> devient un groupe d'adresse."""
    match = re.search(failregex.replace("<HOST>", r"(?P<host>[0-9a-fA-F:.]+)"), line)
    return match.group("host") if match else None


def test_each_riposte_jail_matches_only_its_own_duration() -> None:
    catalog = load_catalog(REAL_CATALOG)
    by_name = {jail.name: jail for jail in catalog.jails}
    assert _fail2ban_match(by_name["riposte-6h"].failregex, OMEGA_SERV_LINE) == "203.0.113.7"
    for other in ("riposte-1h", "riposte-24h", "riposte-7d"):
        assert _fail2ban_match(by_name[other].failregex, OMEGA_SERV_LINE) is None
    assert [by_name[n].bantime for n in ("riposte-1h", "riposte-6h", "riposte-24h", "riposte-7d")] == [
        3600, 21600, 86400, 604800]


def test_detect_reads_the_riposte_journal_only_when_network_bans_are_on(tmp_path: Path) -> None:
    on = detect(_instance(tmp_path / "on"))
    assert on.resolve_logpath("riposte_decisions_log") == tmp_path / "on" / "var" / "log" / "riposte-decisions.jsonl"
    assert detect(_instance(tmp_path / "off", riposte=False)).riposte_decisions_log is None
    assert detect(_instance(tmp_path / "nolog", network_ban_log=False)).riposte_decisions_log is None


def test_instances_from_systemd_registry_and_main_root_without_duplicates(tmp_path: Path) -> None:
    main = _instance(tmp_path / "main")
    blog = _instance(tmp_path / "blog")
    units = tmp_path / "systemd"
    units.mkdir()
    (units / "omega-serv.service").write_text(f"[Service]\nWorkingDirectory={main}\n", encoding="utf-8")
    registry = tmp_path / "instances.json"
    registry.write_text(json.dumps([
        {"name": "blog", "path": str(blog), "service_name": "omega-serv-blog"},
        {"name": "gone", "path": str(tmp_path / "absent"), "service_name": "omega-serv-gone"},
    ]), encoding="utf-8")
    found = detect_instances(main, systemd_dirs=(units,), registry=[registry])
    assert sorted((i.service_name, i.root) for i in found) == [
        ("omega-serv", main.resolve()), ("omega-serv-blog", blog.resolve())]


def test_main_root_without_unit_is_named_omega_serv(tmp_path: Path) -> None:
    main = _instance(tmp_path / "main")
    assert detect_instances(main, systemd_dirs=(), registry=[]) == [ServInstance("omega-serv", main.resolve())]


def test_one_jail_per_duration_and_per_instance(tmp_path: Path) -> None:
    main = _instance(tmp_path / "main")
    blog = _instance(tmp_path / "blog")
    quiet = _instance(tmp_path / "quiet", riposte=False)
    base = tmp_path / "fail2ban"
    config = InstallConfig(
        serv_root=main, omega_jail_root=tmp_path / "jail", jail_d_dir=base / "jail.d", filter_d_dir=base / "filter.d",
        action_d_dir=base / "action.d",
        bridge_dir=Path(str(base / "action.d")).parent / "omega-jail-lib", jail_conf_path=base / "jail.conf", jail_local_path=base / "jail.local",
        only=None,
        instances=(ServInstance("omega-serv", main), ServInstance("omega-serv-blog", blog),
                   ServInstance("omega-serv-quiet", quiet)),
    )
    report = prepare(config, catalog_path=REAL_CATALOG)
    outcomes = {action.name: action.outcome for action in report.plan}
    for service in ("omega-serv", "omega-serv-blog"):
        for suffix in ("1h", "6h", "24h", "7d"):
            assert outcomes[f"{service}-riposte-{suffix}"] == "create"
    assert outcomes["omega-serv-quiet-riposte-1h"] == "skip_unavailable"
    assert "riposte-1h" not in outcomes  # jamais un jail sans prefixe d'instance

    apply(report, config)
    jail = (base / "jail.d" / "omega-jail-omega-serv-blog-riposte-24h.conf").read_text(encoding="utf-8")
    assert "[omega-serv-blog-riposte-24h]" in jail
    assert f"logpath = {blog / 'var' / 'log' / 'riposte-decisions.jsonl'}" in jail
    assert "bantime = 86400" in jail
    assert (blog / "var" / "log" / "riposte-decisions.jsonl").exists()  # fail2ban refuse un logpath absent

    # Relance : les jails deja installes par omega-jail ne sont jamais vus comme doublons d'eux-memes.
    again = {a.name: a.outcome for a in prepare(config, catalog_path=REAL_CATALOG).plan}
    assert again["omega-serv-blog-riposte-24h"] == "skip_collision"


def test_only_selects_the_riposte_duration_for_every_instance(tmp_path: Path) -> None:
    main = _instance(tmp_path / "main")
    blog = _instance(tmp_path / "blog")
    base = tmp_path / "fail2ban"
    config = InstallConfig(
        serv_root=main, omega_jail_root=tmp_path / "jail", jail_d_dir=base / "jail.d", filter_d_dir=base / "filter.d",
        action_d_dir=base / "action.d",
        bridge_dir=Path(str(base / "action.d")).parent / "omega-jail-lib", jail_conf_path=base / "jail.conf", jail_local_path=base / "jail.local",
        only="riposte-7d", instances=(ServInstance("omega-serv", main), ServInstance("omega-serv-blog", blog)),
    )
    names = sorted(a.name for a in prepare(config, catalog_path=REAL_CATALOG).plan)
    assert names == ["omega-serv-blog-riposte-7d", "omega-serv-riposte-7d"]
