"""Instances omega-serv installees sur la machine (RIPOSTE, OMEGA-SERV_PLAN-DETAILLE_RIPOSTE.md lot 6 -
decision utilisateur 2026-11-02 : une seule installation d'omega-jail cree les jails RIPOSTE de TOUTES les
instances). Meme lecture qu'omega-fire (infrastructure/probe/omega_serv_detector.py), sans dependance a son
code (projets separes) :
1. unites systemd `omega-serv*.service` -> `WorkingDirectory=` (l'instance principale ne figure pas dans le
   registre) ; le nom du service = nom de l'unite ;
2. registre d'omega-serv `~/.config/omega-serv/instances.json` (cles `path`, `service_name`), de
   l'utilisateur qui a lance sudo et de root.
Lecture seule, sans doublon (meme dossier reel), dossiers absents ignores."""
from __future__ import annotations

import json
import os
import pwd
from dataclasses import dataclass
from pathlib import Path

SYSTEMD_DIRS = (Path("/etc/systemd/system"), Path("/lib/systemd/system"), Path("/usr/lib/systemd/system"))
DEFAULT_SERVICE_NAME = "omega-serv"


@dataclass(frozen=True, slots=True)
class ServInstance:
    service_name: str
    """Prefixe des jails par instance (`<service>-riposte-<duree>`), comme cote omega-serv."""
    root: Path


def _systemd_instances(dirs: tuple[Path, ...]) -> list[ServInstance]:
    found: list[ServInstance] = []
    for directory in dirs:
        try:
            units = sorted(directory.glob("omega-serv*.service"))
        except OSError:
            continue
        for unit in units:
            try:
                lines = unit.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines:
                key, _sep, value = line.strip().partition("=")
                if key == "WorkingDirectory" and value.strip():
                    found.append(ServInstance(service_name=unit.stem, root=Path(value.strip())))
                    break
    return found


def registry_paths() -> list[Path]:
    homes = [Path.home(), Path("/root")]
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            homes.insert(0, Path(pwd.getpwnam(sudo_user).pw_dir))
        except KeyError:
            pass
    return [home / ".config" / "omega-serv" / "instances.json" for home in homes]


def _registry_instances(paths: list[Path]) -> list[ServInstance]:
    found: list[ServInstance] = []
    for path in paths:
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and entry.get("path") and entry.get("service_name"):
                found.append(ServInstance(service_name=str(entry["service_name"]), root=Path(entry["path"])))
    return found


def detect_instances(
    main_root: Path | None = None,
    *,
    systemd_dirs: tuple[Path, ...] = SYSTEMD_DIRS,
    registry: list[Path] | None = None,
) -> list[ServInstance]:
    """Toutes les instances, `main_root` (celle enregistree par install.sh) comprise : nommee d'apres son
    unite systemd si elle en a une, sinon `omega-serv`."""
    candidates = _systemd_instances(systemd_dirs) + _registry_instances(
        registry if registry is not None else registry_paths())
    if main_root is not None:
        candidates.append(ServInstance(service_name=DEFAULT_SERVICE_NAME, root=main_root))
    unique: dict[Path, ServInstance] = {}
    for instance in candidates:
        try:
            real = instance.root.resolve()
        except OSError:
            continue
        if real.is_dir() and real not in unique:
            unique[real] = ServInstance(service_name=instance.service_name, root=real)
    return list(unique.values())
