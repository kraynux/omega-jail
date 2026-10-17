from pathlib import Path

from omega_jail.catalog import Catalog, JailSpec
from omega_jail.detect import DetectedPaths, MagnetInfo
from omega_jail.duplicates import check_catalog_against_existing


def _jail(name: str, logpath_key: str) -> JailSpec:
    return JailSpec(
        name=name,
        description="",
        logpath_key=logpath_key,
        format="plain",
        maxretry=1,
        findtime=60,
        bantime=60,
        failregex="x",
    )


def test_available_when_no_existing_jail_and_logpath_resolved(tmp_path: Path) -> None:
    catalog = Catalog(jails=[_jail("foo", "access_log")])
    detected = DetectedPaths(
        access_log=tmp_path / "access.log", waf_alerts_log=None, active_defense_log=None, magnet=None
    )
    results = check_catalog_against_existing(catalog, detected, existing_logpaths={})
    assert len(results) == 1
    assert results[0].status == "available"
    assert results[0].logpath == tmp_path / "access.log"


def test_unavailable_when_source_not_configured(tmp_path: Path) -> None:
    catalog = Catalog(jails=[_jail("foo", "waf_alerts_log")])
    detected = DetectedPaths(
        access_log=tmp_path / "access.log", waf_alerts_log=None, active_defense_log=None, magnet=None
    )
    results = check_catalog_against_existing(catalog, detected, existing_logpaths={})
    assert results[0].status == "unavailable"
    assert results[0].reason is not None


def test_duplicate_detected_against_pre_existing_jail(tmp_path: Path) -> None:
    catalog = Catalog(jails=[_jail("omega-serv-waf-block", "waf_alerts_log")])
    waf_log = tmp_path / "var/log/waf-alerts.log"
    detected = DetectedPaths(
        access_log=tmp_path / "access.log", waf_alerts_log=waf_log, active_defense_log=None, magnet=None
    )
    results = check_catalog_against_existing(
        catalog, detected, existing_logpaths={"hand-made-waf-jail": str(waf_log)}
    )
    assert results[0].status == "duplicate"
    assert results[0].duplicate_of == "hand-made-waf-jail"


def test_duplicate_comparison_normalizes_paths(tmp_path: Path) -> None:
    catalog = Catalog(jails=[_jail("foo", "access_log")])
    detected = DetectedPaths(
        access_log=tmp_path / "var/log/access.log", waf_alerts_log=None, active_defense_log=None, magnet=None
    )
    messy_existing_path = str(tmp_path) + "/var/./log/../log/access.log"
    results = check_catalog_against_existing(
        catalog, detected, existing_logpaths={"custom": messy_existing_path}
    )
    assert results[0].status == "duplicate"


def test_two_catalog_entries_sharing_the_same_logpath_never_conflict_with_each_other(tmp_path: Path) -> None:
    """omega-serv-auth-bruteforce et omega-serv-scan visent tous les
    deux access_log par construction - ca ne doit JAMAIS etre traite
    comme un doublon entre elles, seulement contre un jail
    PREEXISTANT externe."""
    catalog = Catalog(
        jails=[
            _jail("omega-serv-auth-bruteforce", "access_log"),
            _jail("omega-serv-scan", "access_log"),
        ]
    )
    detected = DetectedPaths(
        access_log=tmp_path / "access.log", waf_alerts_log=None, active_defense_log=None, magnet=None
    )
    results = check_catalog_against_existing(catalog, detected, existing_logpaths={})
    assert [r.status for r in results] == ["available", "available"]


def test_both_sharing_logpath_skipped_when_an_external_jail_already_watches_it(tmp_path: Path) -> None:
    catalog = Catalog(
        jails=[
            _jail("omega-serv-auth-bruteforce", "access_log"),
            _jail("omega-serv-scan", "access_log"),
        ]
    )
    access_log = tmp_path / "access.log"
    detected = DetectedPaths(access_log=access_log, waf_alerts_log=None, active_defense_log=None, magnet=None)
    results = check_catalog_against_existing(
        catalog, detected, existing_logpaths={"hand-made": str(access_log)}
    )
    assert [r.status for r in results] == ["duplicate", "duplicate"]


def test_magnet_logpaths_resolved_through_detected_paths(tmp_path: Path) -> None:
    catalog = Catalog(jails=[_jail("omega-waf-blocklist-sync", "waf_magnet_blocklist_log")])
    magnet = MagnetInfo(
        alerts_log=tmp_path / "alerts.log", blocklist_log=tmp_path / "blocklist.log", use_json_logs=False
    )
    detected = DetectedPaths(
        access_log=tmp_path / "access.log", waf_alerts_log=None, active_defense_log=None, magnet=magnet
    )
    results = check_catalog_against_existing(catalog, detected, existing_logpaths={})
    assert results[0].status == "available"
    assert results[0].logpath == tmp_path / "blocklist.log"
