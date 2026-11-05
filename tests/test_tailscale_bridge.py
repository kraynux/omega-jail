from pathlib import Path
from typing import Any

import pytest

from omega_jail.tailscale_bridge import (
    DEFAULT_TAILSCALE_CIDR,
    find_servcli,
    is_tailscale_address,
    main,
    render_action_conf,
    run_blocklist_command,
)


@pytest.mark.parametrize("ip", ["100.64.0.1", "100.100.100.100", "100.127.255.254"])
def test_is_tailscale_address_true_for_cgnat_range(ip: str) -> None:
    assert is_tailscale_address(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "192.168.1.1", "10.0.0.1", "100.63.255.255", "100.128.0.1"])
def test_is_tailscale_address_false_outside_range(ip: str) -> None:
    assert is_tailscale_address(ip) is False


def test_is_tailscale_address_invalid_input_returns_false() -> None:
    assert is_tailscale_address("not-an-ip") is False
    assert is_tailscale_address("100.64.0.1", cidr="not-a-cidr") is False


def test_is_tailscale_address_respects_custom_cidr() -> None:
    assert is_tailscale_address("10.0.0.5", cidr="10.0.0.0/8") is True
    assert is_tailscale_address("100.64.0.1", cidr="10.0.0.0/8") is False


def test_find_servcli_present(tmp_path: Path) -> None:
    bin_dir = tmp_path / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "omega-serv").write_text("#!/bin/sh\n", encoding="utf-8")
    assert find_servcli(tmp_path) == bin_dir / "omega-serv"


def test_find_servcli_absent(tmp_path: Path) -> None:
    assert find_servcli(tmp_path) is None


def test_render_action_conf_substitutes_values_but_keeps_fail2ban_tags() -> None:
    content = render_action_conf(
        bridge_cli="/opt/omega-jail/.venv/bin/omega-jail-tailscale-bridge",
        servcli="/opt/omega-serv/.venv/bin/omega-serv",
        servconfig="/opt/omega-serv/config/omega-serve.json",
        tailscale_cidr="100.64.0.0/10",
    )
    assert "/opt/omega-jail/.venv/bin/omega-jail-tailscale-bridge" in content
    assert "/opt/omega-serv/.venv/bin/omega-serv" in content
    assert "/opt/omega-serv/config/omega-serve.json" in content
    assert "100.64.0.0/10" in content
    assert "<ip>" in content
    assert "<name>" in content
    assert "<bantime>" in content
    assert "actionban =" in content
    assert "actionunban =" in content


def test_run_blocklist_command_noop_without_servcli(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", lambda *a, **k: calls.append((a, k)))
    run_blocklist_command("", "add", "100.64.0.1")
    assert calls == []


def test_run_blocklist_command_add_includes_reason_and_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "omega_jail.tailscale_bridge.subprocess.run",
        lambda args, **k: calls.append(args),
    )
    run_blocklist_command(
        "/opt/serv/.venv/bin/omega-serv",
        "add",
        "100.64.0.1",
        servconfig="/opt/serv/config/omega-serve.json",
        reason="omega-jail:test",
        bantime_seconds=3600,
    )
    assert len(calls) == 1
    args = calls[0]
    assert args[0] == "/opt/serv/.venv/bin/omega-serv"
    assert "--config" in args and "/opt/serv/config/omega-serve.json" in args
    assert "blocklist" in args and "add" in args
    assert "--network" in args and "100.64.0.1/32" in args
    assert "--reason" in args and "omega-jail:test" in args
    assert "--duration-seconds" in args and "3600" in args


def test_run_blocklist_command_remove_omits_reason_and_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "omega_jail.tailscale_bridge.subprocess.run",
        lambda args, **k: calls.append(args),
    )
    run_blocklist_command("/opt/serv/.venv/bin/omega-serv", "remove", "100.64.0.1")
    args = calls[0]
    assert "remove" in args
    assert "--reason" not in args
    assert "--duration-seconds" not in args


def test_run_blocklist_command_fail_open_on_missing_binary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _raise(*args: Any, **kwargs: Any) -> None:
        raise OSError("binaire introuvable")

    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", _raise)
    run_blocklist_command("/does/not/exist", "add", "100.64.0.1")
    assert "fail-open" in capsys.readouterr().err


class _Done:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout, self.returncode = stdout, returncode


def _fake_run(calls: list[list[str]], listing: str = ""):
    def run(args, **kwargs):
        calls.append(args)
        return _Done(listing if "list" in args else "")
    return run


def test_main_ban_tailscale_ip_triggers_blocklist_add(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", _fake_run(calls))
    exit_code = main(["--ip=100.64.1.2", "--mode=ban", "--servcli=/opt/serv/.venv/bin/omega-serv", "--bantime=3600"])
    assert exit_code == 0
    assert "list" in calls[0]            # lecture de la blocklist d'abord
    assert "add" in calls[-1] and "100.64.1.2/32" in calls[-1]


def test_main_ban_non_tailscale_ip_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_if_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("subprocess.run ne doit jamais etre appele pour une IP non-Tailscale")

    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", _fail_if_called)
    exit_code = main(["--ip=8.8.8.8", "--mode=ban", "--servcli=/opt/serv/.venv/bin/omega-serv"])
    assert exit_code == 0


def test_main_unban_tailscale_ip_triggers_blocklist_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    listing = "100.64.1.2/32\tmanual\t2099-01-01T00:00:00+00:00\tomega-jail:omega-serv-scan\n"
    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", _fake_run(calls, listing))
    exit_code = main(["--ip=100.64.1.2", "--mode=unban", "--servcli=/opt/serv/.venv/bin/omega-serv"])
    assert exit_code == 0
    assert "remove" in calls[-1]


def test_main_always_returns_zero_even_on_subprocess_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: Any, **kwargs: Any) -> None:
        raise OSError("boom")

    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", _raise)
    exit_code = main(["--ip=100.64.1.2", "--mode=ban", "--servcli=/opt/serv/.venv/bin/omega-serv"])
    assert exit_code == 0


def test_default_tailscale_cidr_constant() -> None:
    assert DEFAULT_TAILSCALE_CIDR == "100.64.0.0/10"


# ---- incident du 2026-10-18 : jamais omega-serv lance en root ---------------
def _servcli_tree(tmp_path: Path) -> Path:
    servcli = tmp_path / "omega-serv" / ".venv" / "bin" / "omega-serv"
    servcli.parent.mkdir(parents=True)
    servcli.write_text("#!/bin/sh\n")
    return servcli


def test_as_root_omega_serv_runs_as_installation_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    from omega_jail import tailscale_bridge

    servcli = _servcli_tree(tmp_path)
    captured: dict[str, Any] = {}
    monkeypatch.setattr(tailscale_bridge.os, "geteuid", lambda: 0)
    monkeypatch.setattr(tailscale_bridge.subprocess, "run", lambda args, **kw: captured.update(args=args, **kw))
    run_blocklist_command(str(servcli), "add", "203.0.113.5")
    assert captured["user"] == os.getuid(), "proprietaire de <serv_root>, jamais root"
    assert captured["group"] == os.getgid()
    assert captured["env"]["HOME"]
    assert captured["args"][:3] == [str(servcli), "blocklist", "add"]


def test_not_root_runs_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from omega_jail import tailscale_bridge

    captured: dict[str, Any] = {}
    monkeypatch.setattr(tailscale_bridge.subprocess, "run", lambda args, **kw: captured.update(kw))
    run_blocklist_command(str(_servcli_tree(tmp_path)), "add", "203.0.113.5")
    assert "user" not in captured


def test_root_owned_installation_is_not_switched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from omega_jail import tailscale_bridge

    monkeypatch.setattr(tailscale_bridge.os, "geteuid", lambda: 0)
    real_stat = Path.stat

    def fake_stat(self: Path, *a: Any, **k: Any) -> Any:
        result = real_stat(self, *a, **k)
        if self.name == "omega-serv" and self.is_dir():
            class _S:
                st_uid = 0
            return _S()
        return result

    monkeypatch.setattr(Path, "stat", fake_stat)
    assert tailscale_bridge.run_as_installation_owner(str(_servcli_tree(tmp_path))) is None



# --- Relais derriere un proxy local (2026-11-02, craftdark : Tailscale Funnel) ---------------------------

def _bridge(monkeypatch: pytest.MonkeyPatch, *argv: str) -> list[tuple]:
    from omega_jail import tailscale_bridge

    calls: list[tuple] = []
    monkeypatch.setattr(tailscale_bridge, "run_blocklist_command", lambda *a, **k: calls.append((a, k)))
    assert tailscale_bridge.main(list(argv)) == 0
    return calls


def test_relay_all_relays_a_public_address(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _bridge(monkeypatch, "--ip=186.247.44.211", "--mode=ban", "--servcli=/s", "--jail=omega-serv-waf-block",
                    "--relay-all=1", "--exempt=127.0.0.0/8,100.64.0.0/10")
    assert calls and calls[0][0][1:3] == ("add", "186.247.44.211")


def test_without_relay_all_a_public_address_is_left_to_the_firewall(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _bridge(monkeypatch, "--ip=186.247.44.211", "--mode=ban", "--servcli=/s", "--jail=omega-serv-waf-block") == []


def test_relay_all_never_for_a_riposte_jail(monkeypatch: pytest.MonkeyPatch) -> None:
    """RIPOSTE a deja pose son ban local ; le debannissement de la jail retirerait un ban RIPOSTE plus long."""
    assert _bridge(monkeypatch, "--ip=186.247.44.211", "--mode=unban", "--servcli=/s",
                   "--jail=omega-serv-riposte-1h", "--relay-all=1") == []


def test_relay_all_never_for_an_exempted_address(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _bridge(monkeypatch, "--ip=192.168.1.20", "--mode=ban", "--servcli=/s", "--jail=omega-serv-scan",
                   "--relay-all=1", "--exempt=192.168.0.0/16") == []


def test_render_action_conf_carries_relay_all() -> None:
    content = render_action_conf(bridge_cli="/b", servcli="/s", relay_all=True)
    assert content.count('--relay-all="1"') == 2
    assert render_action_conf(bridge_cli="/b", servcli="/s").count('--relay-all="0"') == 2



# --- Respect des bans existants (2026-11-02, craftdark : un relais de 12 h avait remplace l'auto-ban de 24 h) ---

from datetime import datetime, timedelta, timezone

from omega_jail.tailscale_bridge import (
    BlocklistLine,
    host_network,
    parse_blocklist_list,
    should_add,
    should_remove,
)

_NOW = datetime(2026, 11, 2, 11, 14, tzinfo=timezone.utc)


def _line(network: str, source: str, hours: float | None, reason: str) -> BlocklistLine:
    return BlocklistLine(network, source, None if hours is None else _NOW + timedelta(hours=hours), reason)


def test_ipv6_is_one_address_never_a_whole_block() -> None:
    assert host_network("2a02:8440:a501:9913::be86:aa87") == "2a02:8440:a501:9913::be86:aa87/128"
    assert host_network("186.247.44.211") == "186.247.44.211/32"


def test_longer_auto_ban_is_kept() -> None:
    entries = [_line("187.15.106.65/32", "auto", 24, "récidive sensitive-paths-hostile")]
    assert should_add(entries, "187.15.106.65", 12 * 3600, _NOW) is False


def test_manual_or_permanent_ban_is_never_overwritten() -> None:
    assert should_add([_line("10.9.9.9/32", "manual", 1, "à la main")], "10.9.9.9", 12 * 3600, _NOW) is False
    assert should_add([_line("10.9.9.0/24", "auto", None, "permanent")], "10.9.9.9", 3600, _NOW) is False


def test_shorter_auto_ban_or_own_entry_is_replaced() -> None:
    assert should_add([_line("1.2.3.4/32", "auto", 1, "auto")], "1.2.3.4", 12 * 3600, _NOW) is True
    assert should_add([_line("1.2.3.4/32", "manual", 48, "omega-jail:omega-serv-scan")], "1.2.3.4", 3600, _NOW) is True
    assert should_add([], "1.2.3.4", 3600, _NOW) is True
    assert should_add(None, "1.2.3.4", 3600, _NOW) is True      # illisible : comportement d'avant


def test_unban_removes_only_the_bridge_entry() -> None:
    assert should_remove([_line("1.2.3.4/32", "manual", 5, "omega-jail:omega-serv-scan")], "1.2.3.4", _NOW) is True
    assert should_remove([_line("1.2.3.4/32", "auto", 5, "récidive")], "1.2.3.4", _NOW) is False
    assert should_remove([_line("1.2.3.4/32", "manual", 5, "à la main")], "1.2.3.4", _NOW) is False
    assert should_remove(None, "1.2.3.4", _NOW) is False


def test_parse_blocklist_list_output() -> None:
    out = ("1.2.3.4/32\tauto\t2026-11-03T10:39:08.1+00:00\trécidive : 2 détections\n"
           "5.6.7.0/24\tmanual\tpermanent\tà la main\n")
    first, second = parse_blocklist_list(out)
    assert first.source == "auto" and first.expires_at is not None
    assert second.expires_at is None and second.reason == "à la main"
