from dataclasses import replace
from pathlib import Path

import pytest

import omega_jail.cli as cli_module
from omega_jail.cli import main

_SIMPLE_CATALOG = """
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


def _write_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.yaml"
    path.write_text(_SIMPLE_CATALOG, encoding="utf-8")
    return path


def _common_args(tmp_path: Path) -> list[str]:
    serv_root = tmp_path / "serv"
    serv_root.mkdir(exist_ok=True)
    return [
        "--serv-root", str(serv_root),
        "--catalog", str(_write_catalog(tmp_path)),
        "--jail-d-dir", str(tmp_path / "fail2ban" / "jail.d"),
        "--filter-d-dir", str(tmp_path / "fail2ban" / "filter.d"),
        "--action-d-dir", str(tmp_path / "fail2ban" / "action.d"),
        "--jail-conf-path", str(tmp_path / "fail2ban" / "jail.conf"),
        "--jail-local-path", str(tmp_path / "fail2ban" / "jail.local"),
    ]


def test_dry_run_is_the_default_and_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(_common_args(tmp_path))
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Dry-run" in out
    assert not (tmp_path / "fail2ban" / "jail.d").exists()


def test_apply_without_root_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module.os, "geteuid", lambda: 1000)
    exit_code = main([*_common_args(tmp_path), "--apply"])
    assert exit_code == 1
    assert "privileges root" in capsys.readouterr().err


def test_apply_as_root_invokes_install_apply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module.os, "geteuid", lambda: 0)
    calls = []
    monkeypatch.setattr(
        cli_module,
        "apply",
        lambda report, config, reload_fn=None: calls.append((report, config, reload_fn)) or report,
    )
    exit_code = main([*_common_args(tmp_path), "--apply"])
    assert exit_code == 0
    assert len(calls) == 1


def test_invalid_catalog_returns_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad_catalog = tmp_path / "bad.yaml"
    bad_catalog.write_text("jails:\n  - name: bad\n    logpath_key: not_real\n", encoding="utf-8")
    serv_root = tmp_path / "serv"
    serv_root.mkdir()

    exit_code = main(["--serv-root", str(serv_root), "--catalog", str(bad_catalog)])
    assert exit_code == 1
    assert "erreur" in capsys.readouterr().err


def test_only_flag_restricts_plan_in_dry_run_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([*_common_args(tmp_path), "--only", "sample-access"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "sample-access" in out


def test_serv_root_missing_without_saved_file_shows_clear_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    omega_jail_root = tmp_path / "omega-jail-install"
    omega_jail_root.mkdir()
    args = [
        "--omega-jail-root", str(omega_jail_root),
        "--catalog", str(_write_catalog(tmp_path)),
        "--jail-d-dir", str(tmp_path / "fail2ban" / "jail.d"),
        "--filter-d-dir", str(tmp_path / "fail2ban" / "filter.d"),
        "--action-d-dir", str(tmp_path / "fail2ban" / "action.d"),
    ]
    exit_code = main(args)
    assert exit_code == 1
    assert "aucun chemin omega-serv enregistre" in capsys.readouterr().err


def test_serv_root_read_from_file_saved_by_install_sh(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    omega_jail_root = tmp_path / "omega-jail-install"
    omega_jail_root.mkdir()
    saved_serv_root = tmp_path / "serv"
    saved_serv_root.mkdir()
    (omega_jail_root / ".serv-root").write_text(str(saved_serv_root) + "\n", encoding="utf-8")

    args = [
        "--omega-jail-root", str(omega_jail_root),
        "--catalog", str(_write_catalog(tmp_path)),
        "--jail-d-dir", str(tmp_path / "fail2ban" / "jail.d"),
        "--filter-d-dir", str(tmp_path / "fail2ban" / "filter.d"),
        "--action-d-dir", str(tmp_path / "fail2ban" / "action.d"),
    ]
    exit_code = main(args)
    assert exit_code == 0
    assert "Dry-run" in capsys.readouterr().out


def test_explicit_serv_root_overrides_saved_file(tmp_path: Path) -> None:
    omega_jail_root = tmp_path / "omega-jail-install"
    omega_jail_root.mkdir()
    (omega_jail_root / ".serv-root").write_text(str(tmp_path / "wrong-serv") + "\n", encoding="utf-8")
    real_serv_root = tmp_path / "serv"
    real_serv_root.mkdir()

    args = [
        "--omega-jail-root", str(omega_jail_root),
        "--serv-root", str(real_serv_root),
        "--catalog", str(_write_catalog(tmp_path)),
        "--jail-d-dir", str(tmp_path / "fail2ban" / "jail.d"),
        "--filter-d-dir", str(tmp_path / "fail2ban" / "filter.d"),
        "--action-d-dir", str(tmp_path / "fail2ban" / "action.d"),
    ]
    exit_code = main(args)
    assert exit_code == 0


def test_fail2ban_dirs_autodetected_when_omitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_base = tmp_path / "fail2ban-base"
    fake_base.mkdir()
    monkeypatch.setattr(cli_module, "find_fail2ban_base_dir", lambda: fake_base)
    serv_root = tmp_path / "serv"
    serv_root.mkdir()

    exit_code = main(["--serv-root", str(serv_root), "--catalog", str(_write_catalog(tmp_path))])
    assert exit_code == 0


def test_fail2ban_not_installed_shows_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "find_fail2ban_base_dir", lambda: None)
    serv_root = tmp_path / "serv"
    serv_root.mkdir()

    exit_code = main(["--serv-root", str(serv_root), "--catalog", str(_write_catalog(tmp_path))])
    assert exit_code == 1
    assert "fail2ban ne semble pas installe" in capsys.readouterr().err


def test_explicit_dir_override_bypasses_autodetection_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Meme si fail2ban n'est pas detecte, une --jail-d-dir (etc.)
    explicite reste utilisable (echappatoire pour un cas non standard
    ou pour les tests)."""
    monkeypatch.setattr(cli_module, "find_fail2ban_base_dir", lambda: None)
    exit_code = main(_common_args(tmp_path))
    assert exit_code == 0


def test_pending_lists_only_the_jails_to_create(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """install.sh (mise a jour) lit cette sortie : un nom par ligne, rien d'autre, aucune ecriture."""
    exit_code = main([*_common_args(tmp_path), "--pending"])
    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "sample-access", "omega-jail-tailscale-bridge (action du pont a mettre a jour)",
    ]
    assert not (tmp_path / "fail2ban" / "jail.d").exists()


def test_pending_is_empty_when_everything_is_installed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    jail_d = tmp_path / "fail2ban" / "jail.d"
    jail_d.mkdir(parents=True)
    (jail_d / "omega-jail-sample-access.conf").write_text("[sample-access]\n", encoding="utf-8")
    # action du pont deja a jour : rien a signaler non plus
    from omega_jail.install import ACTION_CONF_FILENAME, InstallConfig, prepare
    args = _common_args(tmp_path)
    config = InstallConfig(
        serv_root=Path(args[1]), omega_jail_root=cli_module._default_omega_jail_root(),
        jail_d_dir=jail_d, filter_d_dir=tmp_path / "fail2ban" / "filter.d",
        action_d_dir=tmp_path / "fail2ban" / "action.d",
        jail_conf_path=tmp_path / "fail2ban" / "jail.conf", jail_local_path=tmp_path / "fail2ban" / "jail.local",
    )
    report = prepare(config, catalog_path=Path(args[3]))
    (tmp_path / "fail2ban" / "action.d").mkdir(parents=True)
    (tmp_path / "fail2ban" / "action.d" / ACTION_CONF_FILENAME).write_text(report.action_conf_content, encoding="utf-8")
    # jail installe mais different du catalogue (ancienne version) : a mettre a jour
    exit_code = main([*_common_args(tmp_path), "--pending"])
    assert exit_code == 0
    assert capsys.readouterr().out == "sample-access (mise a jour)\n"
    # installe dans sa version actuelle : plus rien a signaler
    from omega_jail.install import apply as apply_report
    forced = replace(config, force=True)
    apply_report(prepare(forced, catalog_path=Path(args[3])), forced)
    exit_code = main([*_common_args(tmp_path), "--pending"])
    assert exit_code == 0
    assert capsys.readouterr().out == ""
