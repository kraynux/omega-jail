from pathlib import Path

from omega_jail.catalog import JailSpec
from omega_jail.duplicates import CatalogEntryStatus
from omega_jail.render import (
    BRIDGE_ACTION_NAME,
    filter_name,
    render_available_entries,
    render_entry,
    render_filter,
    render_jail,
)


def _plain_jail(name: str = "omega-serv-scan") -> JailSpec:
    return JailSpec(
        name=name,
        description="desc",
        logpath_key="access_log",
        format="plain",
        maxretry=15,
        findtime=120,
        bantime=3600,
        failregex=r'^<HOST> \S+ \S+ \[[^\]]+\] ".*" 404',
    )


def _auto_jail(name: str = "omega-waf-magnet-alerts") -> JailSpec:
    return JailSpec(
        name=name,
        description="desc",
        logpath_key="waf_magnet_alerts_log",
        format="auto",
        maxretry=3,
        findtime=300,
        bantime=43200,
        failregex_json='"ip":"<HOST>"',
        failregex_plain="^\\[.*\\] ip=<HOST> method=",
    )


def test_filter_name_has_omega_jail_prefix() -> None:
    assert filter_name("omega-serv-scan") == "omega-jail-omega-serv-scan"


def test_render_filter_plain_format_uses_its_failregex() -> None:
    jail = _plain_jail()
    content = render_filter(jail)
    assert "[Definition]" in content
    assert jail.failregex in content
    assert "ignoreregex =" in content


def test_render_filter_auto_format_picks_json_or_plain() -> None:
    jail = _auto_jail()
    json_content = render_filter(jail, use_json_logs=True)
    plain_content = render_filter(jail, use_json_logs=False)
    assert jail.failregex_json in json_content
    assert jail.failregex_plain not in json_content
    assert jail.failregex_plain in plain_content
    assert jail.failregex_json not in plain_content


def test_render_jail_includes_core_fields_and_bridge_action(tmp_path: Path) -> None:
    jail = _plain_jail()
    logpath = tmp_path / "access.log"
    content = render_jail(jail, logpath)
    assert f"[{jail.name}]" in content
    assert "enabled = true" in content
    assert f"filter = {filter_name(jail.name)}" in content
    assert f"logpath = {logpath}" in content
    assert f"maxretry = {jail.maxretry}" in content
    assert f"findtime = {jail.findtime}" in content
    assert f"bantime = {jail.bantime}" in content
    assert "action = %(action_)s" in content
    assert BRIDGE_ACTION_NAME in content


def test_render_jail_without_bridge_action(tmp_path: Path) -> None:
    jail = _plain_jail()
    content = render_jail(jail, tmp_path / "access.log", include_bridge_action=False)
    assert "action" not in content
    assert BRIDGE_ACTION_NAME not in content


def test_render_jail_never_writes_backend_or_banaction_line(tmp_path: Path) -> None:
    """Meme forme minimale que adapter.py::create_jail d'omega-fire :
    jamais de ligne backend/banaction en dur, herite du defaut global."""
    content = render_jail(_plain_jail(), tmp_path / "access.log")
    assert "backend" not in content
    assert "banaction" not in content


def test_render_entry_returns_none_for_duplicate_status() -> None:
    status = CatalogEntryStatus(jail=_plain_jail(), status="duplicate", duplicate_of="hand-made")
    assert render_entry(status) is None


def test_render_entry_returns_none_for_unavailable_status() -> None:
    status = CatalogEntryStatus(jail=_plain_jail(), status="unavailable", reason="non configure")
    assert render_entry(status) is None


def test_render_entry_available_produces_matching_filenames(tmp_path: Path) -> None:
    jail = _plain_jail()
    status = CatalogEntryStatus(jail=jail, status="available", logpath=tmp_path / "access.log")
    rendered = render_entry(status)
    assert rendered is not None
    assert rendered.name == jail.name
    assert rendered.filter_filename == rendered.jail_filename == f"{filter_name(jail.name)}.conf"
    assert jail.failregex in rendered.filter_content
    assert str(tmp_path / "access.log") in rendered.jail_content
    assert rendered.logpath == tmp_path / "access.log"


def test_render_available_entries_filters_and_preserves_order(tmp_path: Path) -> None:
    available_1 = CatalogEntryStatus(
        jail=_plain_jail("omega-serv-scan"), status="available", logpath=tmp_path / "access.log"
    )
    skipped = CatalogEntryStatus(jail=_plain_jail("omega-serv-auth-bruteforce"), status="duplicate")
    available_2 = CatalogEntryStatus(
        jail=_auto_jail(), status="available", logpath=tmp_path / "alerts.log"
    )
    rendered = render_available_entries([available_1, skipped, available_2], use_json_logs=True)
    assert [r.name for r in rendered] == ["omega-serv-scan", "omega-waf-magnet-alerts"]
    assert '"ip":"<HOST>"' in rendered[1].filter_content
