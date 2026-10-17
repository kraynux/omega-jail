"""Compare le catalogue de jails aux jails fail2ban deja presents sur
le disque (existing_jails.py) pour decider, pour chaque entree du
catalogue, si elle est disponible, deja couverte par un doublon
externe, ou tout simplement inapplicable (source de log non
configuree cote omega-serv - WAF natif desactive, Active Defense
desactive, magnet absent).

Comparaison faite UNIQUEMENT contre des jails preexistants (scannes
avant toute ecriture de ce run) - jamais entre deux entrees du
catalogue elles-memes : plusieurs jails du catalogue visant
legitimement le meme fichier (ex. omega-serv-auth-bruteforce et
omega-serv-scan surveillent tous les deux access_log, avec des
failregex differents) ne doivent jamais se signaler mutuellement comme
doublons."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from omega_jail.catalog import Catalog, JailSpec
from omega_jail.detect import DetectedPaths

CatalogEntryState = Literal["available", "unavailable", "duplicate"]


@dataclass(frozen=True, slots=True)
class CatalogEntryStatus:
    jail: JailSpec
    status: CatalogEntryState
    logpath: Path | None = None
    duplicate_of: str | None = None
    reason: str | None = None


def _normalize(path: str) -> str:
    return os.path.normpath(path)


def check_catalog_against_existing(
    catalog: Catalog,
    detected: DetectedPaths,
    existing_logpaths: dict[str, str],
) -> list[CatalogEntryStatus]:
    normalized_existing = {name: _normalize(path) for name, path in existing_logpaths.items()}

    results: list[CatalogEntryStatus] = []
    for jail in catalog.jails:
        logpath = detected.resolve_logpath(jail.logpath_key)
        if logpath is None:
            results.append(
                CatalogEntryStatus(
                    jail=jail,
                    status="unavailable",
                    reason=f"source non configuree cote omega-serv pour logpath_key={jail.logpath_key!r}",
                )
            )
            continue

        normalized = _normalize(str(logpath))
        duplicate_of = next(
            (name for name, existing_path in normalized_existing.items() if existing_path == normalized),
            None,
        )
        if duplicate_of is not None:
            results.append(
                CatalogEntryStatus(jail=jail, status="duplicate", logpath=logpath, duplicate_of=duplicate_of)
            )
        else:
            results.append(CatalogEntryStatus(jail=jail, status="available", logpath=logpath))

    return results
