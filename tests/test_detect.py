import json
from pathlib import Path

from omega_jail.detect import DEFAULT_CONFIG_REL_PATH, detect, detect_use_json_logs


def _write_config(serv_root: Path, config: dict) -> None:
    config_path = serv_root / DEFAULT_CONFIG_REL_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config), encoding="utf-8")


def test_defaults_when_config_file_absent(tmp_path: Path) -> None:
    detected = detect(tmp_path)
    assert detected.access_log == tmp_path / "var/log/access.log"
    assert detected.waf_alerts_log is None
    assert detected.active_defense_log is None
    assert detected.magnet is None


def test_access_log_always_resolved_from_logs_access(tmp_path: Path) -> None:
    _write_config(tmp_path, {"logs": {"access": "custom/access.log"}})
    detected = detect(tmp_path)
    assert detected.access_log == tmp_path / "custom/access.log"


def test_waf_alerts_log_uses_options_waf_logging_path_not_logs_waf_alerts(tmp_path: Path) -> None:
    """Piege reel identifie dans omega-serv : `logs.waf_alerts` existe
    mais n'est PAS le champ reellement utilise pour ecrire le fichier -
    c'est `options.waf.logging.path`. Un chemin different sur les deux
    doit faire gagner options.waf.logging.path."""
    _write_config(
        tmp_path,
        {
            "logs": {"waf_alerts": "var/log/wrong-field.log"},
            "options": {"waf": {"enabled": True, "logging": {"path": "var/log/real-waf-alerts.log"}}},
        },
    )
    detected = detect(tmp_path)
    assert detected.waf_alerts_log == tmp_path / "var/log/real-waf-alerts.log"


def test_waf_alerts_log_none_when_native_waf_disabled(tmp_path: Path) -> None:
    _write_config(tmp_path, {"options": {"waf": {"enabled": False}}})
    detected = detect(tmp_path)
    assert detected.waf_alerts_log is None


def test_active_defense_log_none_when_disabled(tmp_path: Path) -> None:
    _write_config(tmp_path, {"options": {"active_defense": {"enabled": False}}})
    detected = detect(tmp_path)
    assert detected.active_defense_log is None


def test_active_defense_log_resolved_when_enabled(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        {"options": {"active_defense": {"enabled": True, "logging": {"log_path": "var/log/ad.jsonl"}}}},
    )
    detected = detect(tmp_path)
    assert detected.active_defense_log == tmp_path / "var/log/ad.jsonl"


def test_magnet_none_when_absent_or_disabled(tmp_path: Path) -> None:
    _write_config(tmp_path, {"options": {"waf": {"enabled": True}}})
    assert detect(tmp_path).magnet is None

    _write_config(tmp_path, {"options": {"waf": {"enabled": True, "magnet": {"enabled": False}}}})
    assert detect(tmp_path).magnet is None


def test_magnet_resolved_with_custom_paths_and_json_logs(tmp_path: Path) -> None:
    script_rel = "secure/waf/scripts/omega-waf.lua"
    script_path = tmp_path / script_rel
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("local use_json_logs          = true\n", encoding="utf-8")

    _write_config(
        tmp_path,
        {
            "options": {
                "waf": {
                    "enabled": True,
                    "magnet": {
                        "enabled": True,
                        "script": script_rel,
                        "paths": {
                            "alerts_log": "var/log/custom-magnet-alerts.log",
                            "blocklist_log": "var/log/custom-magnet-blocklist.log",
                        },
                    },
                }
            }
        },
    )
    detected = detect(tmp_path)
    assert detected.magnet is not None
    assert detected.magnet.alerts_log == tmp_path / "var/log/custom-magnet-alerts.log"
    assert detected.magnet.blocklist_log == tmp_path / "var/log/custom-magnet-blocklist.log"
    assert detected.magnet.use_json_logs is True


def test_magnet_defaults_when_paths_not_customized(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        {"options": {"waf": {"enabled": True, "magnet": {"enabled": True, "script": "x.lua"}}}},
    )
    detected = detect(tmp_path)
    assert detected.magnet is not None
    assert detected.magnet.alerts_log == tmp_path / "var/log/waf-magnet-alerts.log"
    assert detected.magnet.blocklist_log == tmp_path / "var/log/waf-magnet-blocklist.log"
    assert detected.magnet.use_json_logs is False


def test_resolve_logpath_key_mapping(tmp_path: Path) -> None:
    script_rel = "x.lua"
    (tmp_path / script_rel).write_text("local use_json_logs = false\n", encoding="utf-8")
    _write_config(
        tmp_path,
        {
            "options": {
                "waf": {"enabled": True, "magnet": {"enabled": True, "script": script_rel}},
                "active_defense": {"enabled": True},
            }
        },
    )
    detected = detect(tmp_path)
    assert detected.resolve_logpath("access_log") == detected.access_log
    assert detected.resolve_logpath("waf_alerts_log") == detected.waf_alerts_log
    assert detected.resolve_logpath("active_defense_log") == detected.active_defense_log
    assert detected.resolve_logpath("waf_magnet_alerts_log") == detected.magnet.alerts_log
    assert detected.resolve_logpath("waf_magnet_blocklist_log") == detected.magnet.blocklist_log
    assert detected.resolve_logpath("unknown_key") is None


def test_detect_use_json_logs_missing_file_defaults_false(tmp_path: Path) -> None:
    assert detect_use_json_logs(tmp_path / "does-not-exist.lua") is False


def test_detect_use_json_logs_true_and_false(tmp_path: Path) -> None:
    script = tmp_path / "script.lua"
    script.write_text("local use_json_logs          = true\n", encoding="utf-8")
    assert detect_use_json_logs(script) is True

    script.write_text("local use_json_logs          = false\n", encoding="utf-8")
    assert detect_use_json_logs(script) is False


def test_corrupt_config_json_falls_back_to_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / DEFAULT_CONFIG_REL_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{not valid json", encoding="utf-8")
    detected = detect(tmp_path)
    assert detected.access_log == tmp_path / "var/log/access.log"
