"""Chargement et validation du catalogue de jails (catalog.yaml).

Donnees pures, aucune I/O fail2ban ici (voir render.py/install.py)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

LogFormat = Literal["plain", "json", "auto"]

KNOWN_LOGPATH_KEYS: frozenset[str] = frozenset(
    {
        "waf_magnet_blocklist_log",
        "waf_magnet_alerts_log",
        "waf_alerts_log",
        "active_defense_log",
        "access_log",
    }
)


@dataclass(frozen=True, slots=True)
class JailSpec:
    name: str
    description: str
    logpath_key: str
    format: LogFormat
    maxretry: int
    findtime: int
    bantime: int
    failregex: str | None = None
    failregex_json: str | None = None
    failregex_plain: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("name est requis")
        if self.logpath_key not in KNOWN_LOGPATH_KEYS:
            errors.append(f"{self.name or '?'}: logpath_key inconnu : {self.logpath_key!r}")
        if self.maxretry < 1:
            errors.append(f"{self.name}: maxretry doit etre >= 1")
        if self.findtime < 1:
            errors.append(f"{self.name}: findtime doit etre >= 1")
        if self.bantime < 1:
            errors.append(f"{self.name}: bantime doit etre >= 1")
        if self.format == "auto":
            if not self.failregex_json or not self.failregex_plain:
                errors.append(f"{self.name}: format 'auto' requiert failregex_json et failregex_plain")
        else:
            if not self.failregex:
                errors.append(f"{self.name}: format {self.format!r} requiert failregex")
        return errors


@dataclass(frozen=True, slots=True)
class Catalog:
    jails: list[JailSpec]

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen_names: set[str] = set()
        for jail in self.jails:
            errors.extend(jail.validate())
            if jail.name in seen_names:
                errors.append(f"nom de jail duplique dans le catalogue : {jail.name!r}")
            seen_names.add(jail.name)
        return errors

    def get(self, name: str) -> JailSpec | None:
        for jail in self.jails:
            if jail.name == name:
                return jail
        return None


def _jail_spec_from_dict(data: dict[str, Any]) -> JailSpec:
    return JailSpec(
        name=str(data.get("name", "")),
        description=str(data.get("description", "")).strip(),
        logpath_key=str(data.get("logpath_key", "")),
        format=data.get("format", "plain"),
        maxretry=int(data.get("maxretry", 0)),
        findtime=int(data.get("findtime", 0)),
        bantime=int(data.get("bantime", 0)),
        failregex=data.get("failregex"),
        failregex_json=data.get("failregex_json"),
        failregex_plain=data.get("failregex_plain"),
    )


def load_catalog(path: Path) -> Catalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    jails_raw = raw.get("jails", [])
    jails = [_jail_spec_from_dict(entry) for entry in jails_raw]
    return Catalog(jails=jails)
