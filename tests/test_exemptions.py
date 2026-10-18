"""Reseaux jamais bannis (OMEGA-SERV_PLAN-DETAILLE_SENSITIVE_PATHS.md lot 10) :
lus aupres d'omega-serv, jamais copies en dur ; ignoreip des jails ; pont
Tailscale."""
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from omega_jail.exemptions import FALLBACK_NETWORKS, is_exempt, parse_networks, read_exempt_networks
from omega_jail.existing_jails import default_ignoreip_defined
from omega_jail.install import InstallConfig, apply, prepare
from omega_jail.render import render_ignoreip
from omega_jail.tailscale_bridge import main as bridge_main
from omega_jail.tailscale_bridge import render_action_conf

_NETWORKS = ("127.0.0.0/8", "::1/128", "100.64.0.0/10", "192.168.0.0/16")
_CATALOG = """
jails:
  - name: sample-access
    description: "desc"
    logpath_key: access_log
    format: plain
    failregex: '^<HOST> bad$'
    maxretry: 2
    findtime: 30
    bantime: 120
"""


def _fake_servcli(tmp_path: Path, body: str) -> Path:
    """Faux binaire omega-serv (script shell) - teste le VRAI appel subprocess."""
    servcli = tmp_path / "serv" / ".venv" / "bin" / "omega-serv"
    servcli.parent.mkdir(parents=True, exist_ok=True)
    servcli.write_text("#!/bin/sh\n" + body)
    servcli.chmod(servcli.stat().st_mode | stat.S_IXUSR)
    return servcli


# ---- parse / read ----------------------------------------------------------
def test_parse_networks_normalizes() -> None:
    assert parse_networks("127.0.0.1/8\n\n::1/128\n") == ("127.0.0.0/8", "::1/128")


def test_parse_networks_refuses_any_garbage() -> None:
    with pytest.raises(ValueError):
        parse_networks("127.0.0.0/8\nBANNIERE\n")


def test_read_from_omega_serv(tmp_path: Path) -> None:
    servcli = _fake_servcli(tmp_path, 'test "$3" = waf && test "$4" = never-auto-block && printf "100.64.0.0/10\\n10.0.0.0/8\\n"\n')
    result = read_exempt_networks(servcli, tmp_path / "omega-serve.json")
    assert result.from_omega_serv
    assert result.networks == ("100.64.0.0/10", "10.0.0.0/8")
    assert result.warning is None


def test_config_path_is_passed_to_omega_serv(tmp_path: Path) -> None:
    servcli = _fake_servcli(tmp_path, 'test "$1" = --config && test "$2" = /chemin/config.json && echo 10.0.0.0/8\n')
    assert read_exempt_networks(servcli, Path("/chemin/config.json")).networks == ("10.0.0.0/8",)


@pytest.mark.parametrize("body", ['echo "invalid choice: never-auto-block" >&2; exit 2\n', 'echo pas-un-reseau\n'])
def test_old_or_broken_omega_serv_falls_back_with_warning(tmp_path: Path, body: str) -> None:
    result = read_exempt_networks(_fake_servcli(tmp_path, body), tmp_path / "c.json")
    assert not result.from_omega_serv
    assert result.networks == FALLBACK_NETWORKS
    assert result.warning


def test_missing_omega_serv_falls_back(tmp_path: Path) -> None:
    result = read_exempt_networks(None, tmp_path / "c.json")
    assert result.networks == FALLBACK_NETWORKS and result.warning


@pytest.mark.parametrize("ip,expected", [
    ("100.106.10.47", True), ("192.168.1.20", True), ("::ffff:127.0.0.1", True),
    ("198.51.100.7", False), ("100.12.196.99", False), ("not-an-ip", False),
])
def test_is_exempt(ip: str, expected: bool) -> None:
    assert is_exempt(ip, _NETWORKS) is expected


# ---- ignoreip ---------------------------------------------------------------
def test_render_ignoreip_forms() -> None:
    assert render_ignoreip(("10.0.0.0/8",), False) == "ignoreip = 10.0.0.0/8\n"
    assert render_ignoreip(("10.0.0.0/8",), True) == "ignoreip = %(known/ignoreip)s 10.0.0.0/8\n"
    assert render_ignoreip((), False) == ""


def test_default_ignoreip_detection(tmp_path: Path) -> None:
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    conf, local = tmp_path / "jail.conf", tmp_path / "jail.local"
    conf.write_text("[DEFAULT]\n#ignoreip = 127.0.0.1/8 ::1\nbantime = 10m\n[sshd]\nignoreip = 1.2.3.4\n")
    assert default_ignoreip_defined(str(jail_d), str(conf), str(local)) is False, "commentaire ou autre section : non"
    local.write_text("[DEFAULT]\nignoreip = 203.0.113.50\n")
    assert default_ignoreip_defined(str(jail_d), str(conf), str(local)) is True


# ---- installation complete ---------------------------------------------------
def _install(tmp_path: Path, servcli_body: str | None, jail_local: str | None = None):
    serv_root = tmp_path / "serv"
    serv_root.mkdir(exist_ok=True)
    if servcli_body is not None:
        _fake_servcli(tmp_path, servcli_body)
    base = tmp_path / "fail2ban"
    for sub in ("jail.d", "filter.d", "action.d"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    if jail_local is not None:
        (base / "jail.local").write_text(jail_local)
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(_CATALOG)
    config = InstallConfig(
        serv_root=serv_root, omega_jail_root=tmp_path / "oj", jail_d_dir=base / "jail.d",
        filter_d_dir=base / "filter.d", action_d_dir=base / "action.d",
        jail_conf_path=base / "jail.conf", jail_local_path=base / "jail.local",
    )
    report = apply(prepare(config, catalog_path=catalog), config)
    return report, base


def test_install_writes_ignoreip_from_omega_serv(tmp_path: Path) -> None:
    report, base = _install(tmp_path, 'printf "127.0.0.0/8\\n100.64.0.0/10\\n"\n')
    jail = (base / "jail.d" / "omega-jail-sample-access.conf").read_text()
    assert "ignoreip = 127.0.0.0/8 100.64.0.0/10\n" in jail
    assert report.exemptions is not None and report.exemptions.from_omega_serv
    action = (base / "action.d" / "omega-jail-tailscale-bridge.conf").read_text()
    assert '--exempt="127.0.0.0/8,100.64.0.0/10"' in action


def test_install_keeps_user_default_ignoreip(tmp_path: Path) -> None:
    report, base = _install(tmp_path, 'echo 100.64.0.0/10\n', jail_local="[DEFAULT]\nignoreip = 203.0.113.50\n")
    jail = (base / "jail.d" / "omega-jail-sample-access.conf").read_text()
    assert "ignoreip = %(known/ignoreip)s 100.64.0.0/10\n" in jail
    assert report.keep_default_ignoreip


def test_install_without_omega_serv_uses_fallback(tmp_path: Path) -> None:
    report, base = _install(tmp_path, None)
    jail = (base / "jail.d" / "omega-jail-sample-access.conf").read_text()
    assert "ignoreip = 127.0.0.0/8 ::1/128\n" in jail
    assert report.exemptions is not None and report.exemptions.warning


# ---- pont Tailscale ----------------------------------------------------------
def test_bridge_never_relays_an_exempt_address(tmp_path: Path) -> None:
    calls = tmp_path / "calls"
    servcli = _fake_servcli(tmp_path, f'echo "$@" >> {calls}\n')
    code = bridge_main(["--ip=100.106.10.47", "--mode=ban", f"--servcli={servcli}",
                        "--exempt=127.0.0.0/8,100.64.0.0/10", "--jail=t"])
    assert code == 0
    assert not calls.exists(), "aucun appel a omega-serv pour une adresse exemptee"


def test_bridge_still_relays_a_non_exempt_tailscale_address(tmp_path: Path) -> None:
    calls = tmp_path / "calls"
    servcli = _fake_servcli(tmp_path, f'echo "$@" >> {calls}\n')
    bridge_main(["--ip=100.106.10.47", "--mode=ban", f"--servcli={servcli}", "--exempt=10.0.0.0/8", "--jail=t"])
    assert "blocklist add --network 100.106.10.47/32" in calls.read_text()


def test_action_conf_template_renders_exempt() -> None:
    content = render_action_conf("/b", "/s", exempt="10.0.0.0/8")
    assert content.count('--exempt="10.0.0.0/8"') == 2


# ---- validation par le VRAI fail2ban --------------------------------------
@pytest.mark.skipif(shutil.which("fail2ban-client") is None, reason="fail2ban absent")
@pytest.mark.parametrize("jail_local", [None, "[DEFAULT]\nignoreip = 203.0.113.50\n"])
def test_generated_jail_accepted_by_real_fail2ban(tmp_path: Path, jail_local: str | None) -> None:
    """Copie de /etc/fail2ban + jail genere : `fail2ban-client -d` (configuration
    resolue, sans serveur ni root) doit l'accepter dans les DEUX cas - sans
    [DEFAULT] ignoreip, `%(known/ignoreip)s` casserait tout le chargement."""
    copy = tmp_path / "f2b"
    shutil.copytree("/etc/fail2ban", copy, ignore=shutil.ignore_patterns("jail.d", "jail.local"))
    (copy / "jail.d").mkdir()
    if jail_local is not None:
        (copy / "jail.local").write_text(jail_local)
    _report, base = _install(tmp_path, 'printf "127.0.0.0/8\\n::1/128\\n100.64.0.0/10\\n"\n', jail_local=jail_local)
    for name in ("jail.d/omega-jail-sample-access.conf", "filter.d/omega-jail-sample-access.conf"):
        shutil.copy(base / name, copy / name)
    jail = copy / "jail.d" / "omega-jail-sample-access.conf"
    jail.write_text(jail.read_text().split("action =")[0])  # action du pont : hors sujet ici
    dump = subprocess.run(
        ["fail2ban-client", "-c", str(copy), "-d"], capture_output=True, text=True, timeout=60, check=False,
    )
    assert dump.returncode == 0, dump.stderr
    expected = ["127.0.0.0/8", "::1/128", "100.64.0.0/10"]
    if jail_local is not None:
        expected = ["203.0.113.50", *expected]
    assert str(["set", "sample-access", "addignoreip", *expected]) in dump.stdout


# ---- reinstallation (retour reel 2026-10-18, craftdark) ---------------------
def test_reinstall_regenerates_own_jails_with_force(tmp_path: Path) -> None:
    """Les jails d'une installation precedente ne sont PAS des doublons d'eux-memes."""
    _install(tmp_path, None)  # 1re installation : repli, simule l'ancienne version
    jail_file = tmp_path / "fail2ban" / "jail.d" / "omega-jail-sample-access.conf"
    jail_file.write_text(jail_file.read_text().replace("ignoreip = 127.0.0.0/8 ::1/128\n", ""))  # ancien format

    serv_root = tmp_path / "serv"
    _fake_servcli(tmp_path, 'echo 100.64.0.0/10\n')
    base = tmp_path / "fail2ban"
    catalog = tmp_path / "catalog.yaml"

    def _config(force: bool) -> InstallConfig:
        return InstallConfig(
            serv_root=serv_root, omega_jail_root=tmp_path / "oj", jail_d_dir=base / "jail.d",
            filter_d_dir=base / "filter.d", action_d_dir=base / "action.d",
            jail_conf_path=base / "jail.conf", jail_local_path=base / "jail.local", force=force,
        )

    without_force = prepare(_config(False), catalog_path=catalog)
    assert [a.outcome for a in without_force.plan] == ["skip_collision"]
    assert "--force" in without_force.plan[0].detail

    with_force = apply(prepare(_config(True), catalog_path=catalog), _config(True))
    assert [a.outcome for a in with_force.plan] == ["overwrite_forced"]
    assert "ignoreip = 100.64.0.0/10\n" in jail_file.read_text()


def test_external_jail_on_same_log_is_still_a_duplicate(tmp_path: Path) -> None:
    serv_root = tmp_path / "serv"
    (serv_root / "config").mkdir(parents=True)
    (serv_root / "config" / "omega-serve.json").write_text("{}")
    base = tmp_path / "fail2ban"
    for sub in ("jail.d", "filter.d", "action.d"):
        (base / sub).mkdir(parents=True)
    access_log = serv_root / "var" / "log" / "access.log"
    (base / "jail.d" / "mon-jail.conf").write_text(f"[mon-jail]\nenabled = true\nlogpath = {access_log}\n")
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(_CATALOG)
    config = InstallConfig(
        serv_root=serv_root, omega_jail_root=tmp_path / "oj", jail_d_dir=base / "jail.d",
        filter_d_dir=base / "filter.d", action_d_dir=base / "action.d",
        jail_conf_path=base / "jail.conf", jail_local_path=base / "jail.local", force=True,
    )
    report = prepare(config, catalog_path=catalog)
    assert [(a.outcome, a.detail) for a in report.plan] == [
        ("skip_duplicate", "deja surveille par le jail existant 'mon-jail'"),
    ]
