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


def test_main_ban_tailscale_ip_triggers_blocklist_add(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "omega_jail.tailscale_bridge.subprocess.run",
        lambda args, **k: calls.append(args),
    )
    exit_code = main(["--ip=100.64.1.2", "--mode=ban", "--servcli=/opt/serv/.venv/bin/omega-serv", "--bantime=3600"])
    assert exit_code == 0
    assert len(calls) == 1
    assert "add" in calls[0]


def test_main_ban_non_tailscale_ip_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_if_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("subprocess.run ne doit jamais etre appele pour une IP non-Tailscale")

    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", _fail_if_called)
    exit_code = main(["--ip=8.8.8.8", "--mode=ban", "--servcli=/opt/serv/.venv/bin/omega-serv"])
    assert exit_code == 0


def test_main_unban_tailscale_ip_triggers_blocklist_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "omega_jail.tailscale_bridge.subprocess.run",
        lambda args, **k: calls.append(args),
    )
    exit_code = main(["--ip=100.64.1.2", "--mode=unban", "--servcli=/opt/serv/.venv/bin/omega-serv"])
    assert exit_code == 0
    assert "remove" in calls[0]


def test_main_always_returns_zero_even_on_subprocess_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: Any, **kwargs: Any) -> None:
        raise OSError("boom")

    monkeypatch.setattr("omega_jail.tailscale_bridge.subprocess.run", _raise)
    exit_code = main(["--ip=100.64.1.2", "--mode=ban", "--servcli=/opt/serv/.venv/bin/omega-serv"])
    assert exit_code == 0


def test_default_tailscale_cidr_constant() -> None:
    assert DEFAULT_TAILSCALE_CIDR == "100.64.0.0/10"
