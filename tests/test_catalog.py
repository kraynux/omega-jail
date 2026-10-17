from pathlib import Path

from omega_jail.catalog import Catalog, JailSpec, load_catalog

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_CATALOG = REPO_ROOT / "catalog.yaml"


def test_real_catalog_loads_and_validates_clean() -> None:
    catalog = load_catalog(REAL_CATALOG)
    assert catalog.validate() == []
    assert len(catalog.jails) == 6


def test_real_catalog_has_expected_jail_names() -> None:
    catalog = load_catalog(REAL_CATALOG)
    names = {jail.name for jail in catalog.jails}
    assert names == {
        "omega-waf-blocklist-sync",
        "omega-waf-magnet-alerts",
        "omega-serv-waf-block",
        "omega-serv-active-defense",
        "omega-serv-auth-bruteforce",
        "omega-serv-scan",
    }


def test_get_returns_none_for_unknown_name() -> None:
    catalog = load_catalog(REAL_CATALOG)
    assert catalog.get("does-not-exist") is None


def test_invalid_logpath_key_reported() -> None:
    jail = JailSpec(
        name="bad",
        description="",
        logpath_key="not_a_real_key",
        format="plain",
        maxretry=1,
        findtime=60,
        bantime=60,
        failregex="x",
    )
    errors = jail.validate()
    assert any("logpath_key inconnu" in e for e in errors)


def test_auto_format_requires_both_regexes() -> None:
    jail = JailSpec(
        name="bad-auto",
        description="",
        logpath_key="access_log",
        format="auto",
        maxretry=1,
        findtime=60,
        bantime=60,
    )
    errors = jail.validate()
    assert any("format 'auto' requiert" in e for e in errors)


def test_non_auto_format_requires_failregex() -> None:
    jail = JailSpec(
        name="bad-plain",
        description="",
        logpath_key="access_log",
        format="plain",
        maxretry=1,
        findtime=60,
        bantime=60,
    )
    errors = jail.validate()
    assert any("requiert failregex" in e for e in errors)


def test_zero_or_negative_thresholds_rejected() -> None:
    jail = JailSpec(
        name="bad-thresholds",
        description="",
        logpath_key="access_log",
        format="plain",
        maxretry=0,
        findtime=0,
        bantime=0,
        failregex="x",
    )
    errors = jail.validate()
    assert any("maxretry" in e for e in errors)
    assert any("findtime" in e for e in errors)
    assert any("bantime" in e for e in errors)


def test_duplicate_jail_names_rejected() -> None:
    spec = JailSpec(
        name="dup",
        description="",
        logpath_key="access_log",
        format="plain",
        maxretry=1,
        findtime=60,
        bantime=60,
        failregex="x",
    )
    catalog = Catalog(jails=[spec, spec])
    errors = catalog.validate()
    assert any("duplique" in e for e in errors)


def test_load_catalog_from_yaml_file(tmp_path: Path) -> None:
    content = """
jails:
  - name: sample
    description: "une description"
    logpath_key: access_log
    format: plain
    failregex: '^<HOST> bad$'
    maxretry: 2
    findtime: 30
    bantime: 120
"""
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(content, encoding="utf-8")
    catalog = load_catalog(catalog_path)
    assert catalog.validate() == []
    assert catalog.jails[0].name == "sample"
    assert catalog.jails[0].maxretry == 2
