from pathlib import Path

from omega_jail.install import InstallConfig, apply, prepare

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
  - name: sample-waf
    description: "desc"
    logpath_key: waf_alerts_log
    format: json
    failregex: '"remote_ip": "<HOST>"'
    maxretry: 1
    findtime: 10
    bantime: 60
"""


def _write_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.yaml"
    path.write_text(_SIMPLE_CATALOG, encoding="utf-8")
    return path


def _fake_fs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    serv_root = tmp_path / "serv"
    serv_root.mkdir()
    jail_d = tmp_path / "fail2ban" / "jail.d"
    filter_d = tmp_path / "fail2ban" / "filter.d"
    action_d = tmp_path / "fail2ban" / "action.d"
    return serv_root, jail_d, filter_d, action_d


def _config(tmp_path: Path, serv_root: Path, jail_d: Path, filter_d: Path, action_d: Path, **overrides) -> InstallConfig:
    return InstallConfig(
        serv_root=serv_root,
        omega_jail_root=tmp_path / "omega-jail-install",
        jail_d_dir=jail_d,
        filter_d_dir=filter_d,
        action_d_dir=action_d,
        jail_conf_path=tmp_path / "fail2ban" / "jail.conf",
        jail_local_path=tmp_path / "fail2ban" / "jail.local",
        **overrides,
    )


def test_prepare_marks_access_log_available_and_waf_unavailable(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d)
    report = prepare(config, catalog_path=_write_catalog(tmp_path))

    outcomes = {a.name: a.outcome for a in report.plan}
    assert outcomes["sample-access"] == "create"
    assert outcomes["sample-waf"] == "skip_unavailable"
    assert report.applied is False


def test_dry_run_never_writes_anything(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d)
    prepare(config, catalog_path=_write_catalog(tmp_path))

    assert not jail_d.exists()
    assert not filter_d.exists()
    assert not action_d.exists()


def test_apply_writes_filter_jail_and_action_files(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d)
    report = prepare(config, catalog_path=_write_catalog(tmp_path))

    applied = apply(report, config)

    assert applied.applied is True
    jail_file = jail_d / "omega-jail-sample-access.conf"
    filter_file = filter_d / "omega-jail-sample-access.conf"
    action_file = action_d / "omega-jail-tailscale-bridge.conf"
    assert jail_file.exists()
    assert filter_file.exists()
    assert action_file.exists()
    assert "[sample-access]" in jail_file.read_text(encoding="utf-8")
    assert "bad" in filter_file.read_text(encoding="utf-8")


def test_apply_creates_empty_logpath_file_when_missing(tmp_path: Path) -> None:
    """fail2ban-client refuse de charger un jail dont le logpath
    n'existe pas encore sur disque ("Have not found any log file for
    '<jail>' jail") - cas reel pour un jail pointant vers un log que
    son emetteur ne cree que lors de son premier evenement."""
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d, only="sample-access")
    report = prepare(config, catalog_path=_write_catalog(tmp_path))

    logpath = serv_root / "var" / "log" / "access.log"
    assert not logpath.exists()

    apply(report, config)

    assert logpath.exists()
    assert logpath.read_text(encoding="utf-8") == ""


def test_apply_never_overwrites_an_existing_logpath_file(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d, only="sample-access")
    report = prepare(config, catalog_path=_write_catalog(tmp_path))

    logpath = serv_root / "var" / "log" / "access.log"
    logpath.parent.mkdir(parents=True)
    logpath.write_text("ligne existante\n", encoding="utf-8")

    apply(report, config)

    assert logpath.read_text(encoding="utf-8") == "ligne existante\n"


def test_action_conf_written_even_when_nothing_to_create(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d, only="sample-waf")
    report = prepare(config, catalog_path=_write_catalog(tmp_path))
    assert all(a.outcome == "skip_unavailable" for a in report.plan)

    apply(report, config)
    assert (action_d / "omega-jail-tailscale-bridge.conf").exists()


def test_only_restricts_plan_to_a_single_jail(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d, only="sample-access")
    report = prepare(config, catalog_path=_write_catalog(tmp_path))
    assert len(report.plan) == 1
    assert report.plan[0].name == "sample-access"


def test_collision_without_force_is_skipped_and_not_overwritten(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    jail_d.mkdir(parents=True)
    existing_file = jail_d / "omega-jail-sample-access.conf"
    existing_file.write_text("[sample-access]\n# edite a la main, aucun logpath\n", encoding="utf-8")

    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d)
    report = prepare(config, catalog_path=_write_catalog(tmp_path))
    outcome = next(a for a in report.plan if a.name == "sample-access")
    assert outcome.outcome == "skip_collision"

    apply(report, config)
    assert "edite a la main" in existing_file.read_text(encoding="utf-8")


def test_collision_with_force_overwrites(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    jail_d.mkdir(parents=True)
    existing_file = jail_d / "omega-jail-sample-access.conf"
    existing_file.write_text("[sample-access]\n# edite a la main, aucun logpath\n", encoding="utf-8")

    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d, force=True)
    report = prepare(config, catalog_path=_write_catalog(tmp_path))
    outcome = next(a for a in report.plan if a.name == "sample-access")
    assert outcome.outcome == "overwrite_forced"

    apply(report, config)
    assert "edite a la main" not in existing_file.read_text(encoding="utf-8")


def test_duplicate_logpath_against_existing_jail_is_skipped_without_force(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    jail_d.mkdir(parents=True)
    access_log = serv_root / "var" / "log" / "access.log"
    (jail_d / "hand-made.conf").write_text(f"[hand-made]\nlogpath = {access_log}\n", encoding="utf-8")

    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d)
    report = prepare(config, catalog_path=_write_catalog(tmp_path))
    outcome = next(a for a in report.plan if a.name == "sample-access")
    assert outcome.outcome == "skip_duplicate"
    assert "hand-made" in outcome.detail


def test_apply_creates_logpath_even_for_a_skipped_duplicate_jail(tmp_path: Path) -> None:
    """fail2ban refuse de DEMARRER tout jail (meme preexistant, pas
    seulement nouvellement cree) dont le logpath configure n'existe
    pas - cas reel observe en production : un jail casse d'un run
    precedent reste reference dans jail.d/ et continue d'empecher
    fail2ban de demarrer tant que son fichier de log manque, meme apres
    plusieurs redemarrages, puisqu'un nouveau run le voit comme un
    doublon (deja surveille) et ne le retouchait jamais avant ce
    correctif."""
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    jail_d.mkdir(parents=True)
    access_log = serv_root / "var" / "log" / "access.log"
    assert not access_log.exists()
    (jail_d / "hand-made.conf").write_text(f"[hand-made]\nlogpath = {access_log}\n", encoding="utf-8")

    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d, only="sample-access")
    report = prepare(config, catalog_path=_write_catalog(tmp_path))
    outcome = next(a for a in report.plan if a.name == "sample-access")
    assert outcome.outcome == "skip_duplicate"

    apply(report, config)

    assert access_log.exists()
    assert access_log.read_text(encoding="utf-8") == ""


def test_reload_fn_called_on_apply(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d)
    report = prepare(config, catalog_path=_write_catalog(tmp_path))

    calls = []
    apply(report, config, reload_fn=lambda: calls.append(True))
    assert calls == [True]


def test_invalid_catalog_raises_value_error(tmp_path: Path) -> None:
    serv_root, jail_d, filter_d, action_d = _fake_fs(tmp_path)
    config = _config(tmp_path, serv_root, jail_d, filter_d, action_d)
    bad_catalog = tmp_path / "bad.yaml"
    bad_catalog.write_text("jails:\n  - name: bad\n    logpath_key: not_real\n", encoding="utf-8")

    try:
        prepare(config, catalog_path=bad_catalog)
        assert False, "aurait du lever ValueError"
    except ValueError as exc:
        assert "logpath_key" in str(exc)
