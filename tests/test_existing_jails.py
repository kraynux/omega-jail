from pathlib import Path

from omega_jail.existing_jails import existing_logpaths, scan_existing_jails


def test_simple_one_file_per_jail(tmp_path: Path) -> None:
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    (jail_d / "sshd.conf").write_text(
        "[sshd]\nenabled = true\nlogpath = /var/log/auth.log\nmaxretry = 5\n",
        encoding="utf-8",
    )
    jails = scan_existing_jails(jail_d_dir=str(jail_d))
    assert len(jails) == 1
    assert jails[0].name == "sshd"
    assert jails[0].logpath == "/var/log/auth.log"


def test_multiple_sections_grouped_in_one_differently_named_file(tmp_path: Path) -> None:
    """Cas de production reel cite dans adapter.py (referentiel §82.4) :
    plusieurs jails groupes sous un fichier dont le nom ne correspond a
    aucun des deux."""
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    (jail_d / "honeypot.conf").write_text(
        "[decoy-admin]\n"
        "enabled = true\n"
        "logpath = /var/log/decoy-admin.log\n"
        "\n"
        "[decoy-api]\n"
        "enabled = true\n"
        "logpath = /var/log/decoy-api.log\n",
        encoding="utf-8",
    )
    jails = {jail.name: jail.logpath for jail in scan_existing_jails(jail_d_dir=str(jail_d))}
    assert jails == {
        "decoy-admin": "/var/log/decoy-admin.log",
        "decoy-api": "/var/log/decoy-api.log",
    }


def test_jail_defined_directly_in_jail_local_without_jail_d_file(tmp_path: Path) -> None:
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    jail_local = tmp_path / "jail.local"
    jail_local.write_text(
        "[recidive]\nenabled = true\nlogpath = /var/log/fail2ban.log\n",
        encoding="utf-8",
    )
    jails = scan_existing_jails(jail_d_dir=str(jail_d), jail_local_path=str(jail_local))
    assert len(jails) == 1
    assert jails[0].name == "recidive"
    assert jails[0].logpath == "/var/log/fail2ban.log"


def test_later_file_overrides_earlier_field(tmp_path: Path) -> None:
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    jail_conf = tmp_path / "jail.conf"
    jail_conf.write_text("[foo]\nlogpath = /a.log\n", encoding="utf-8")
    (jail_d / "zzz.conf").write_text("[foo]\nlogpath = /b.log\n", encoding="utf-8")

    jails = scan_existing_jails(jail_d_dir=str(jail_d), jail_conf_path=str(jail_conf))
    assert len(jails) == 1
    assert jails[0].logpath == "/b.log"


def test_default_section_never_treated_as_a_jail(tmp_path: Path) -> None:
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    jail_conf = tmp_path / "jail.conf"
    jail_conf.write_text(
        "[DEFAULT]\nbantime = 600\n\n[foo]\nenabled = true\n",
        encoding="utf-8",
    )
    jails = scan_existing_jails(jail_d_dir=str(jail_d), jail_conf_path=str(jail_conf))
    names = {jail.name for jail in jails}
    assert "DEFAULT" not in names
    assert names == {"foo"}


def test_existing_logpaths_omits_jails_without_resolved_logpath(tmp_path: Path) -> None:
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    jail_conf = tmp_path / "jail.conf"
    jail_conf.write_text("[foo]\nenabled = true\n", encoding="utf-8")

    jails = scan_existing_jails(jail_d_dir=str(jail_d), jail_conf_path=str(jail_conf))
    assert len(jails) == 1
    assert jails[0].logpath is None

    assert existing_logpaths(jail_d_dir=str(jail_d), jail_conf_path=str(jail_conf)) == {}


def test_missing_directories_and_files_return_empty(tmp_path: Path) -> None:
    jail_d = tmp_path / "does-not-exist"
    jails = scan_existing_jails(
        jail_d_dir=str(jail_d),
        jail_conf_path=str(tmp_path / "jail.conf"),
        jail_local_path=str(tmp_path / "jail.local"),
    )
    assert jails == []
