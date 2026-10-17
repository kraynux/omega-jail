"""Detection des jails fail2ban deja presents sur le disque.

Port verbatim de l'algorithme d'omega-fire
(infrastructure/backends/fail2ban/adapter.py::_get_static_config_from_disk
/_extract_section_block/_parse_duration_to_seconds) - omega-jail ne
peut pas importer le code d'omega-fire (projets separes), donc le
meme algorithme est reporte ici plutot que redecouvert. Generalise a
UNE difference pres : l'original cherche le logpath d'un nom de jail
DEJA CONNU ; ici on ne connait aucun nom a l'avance, il faut d'abord
enumerer tous les noms de section presents (list_section_names), puis
resoudre chacun avec la meme logique de fusion multi-fichiers.

Leçon de production citee dans le code source (referentiel §82.4) :
un jail peut vivre dans un fichier au nom totalement different du
sien (plusieurs [section] groupees dans un seul fichier), ou
directement dans jail.conf/jail.local sans jamais toucher jail.d/ -
d'ou le scan dans l'ordre de chargement reel de fail2ban plutot
qu'une simple lecture de jail.d/<nom>.conf."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

_DURATION_MULTIPLIERS: dict[str, int] = {
    "": 1,
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
    "mo": 2592000, "month": 2592000, "months": 2592000,
    "y": 31536000, "year": 31536000, "years": 31536000,
}


def parse_duration_to_seconds(value: str) -> str | None:
    value = value.strip()
    if value.lstrip("-").isdigit():
        return value

    tokens = re.findall(r"(\d+)\s*([a-zA-Z]*)", value)
    if not tokens:
        return None

    total = 0
    for number, unit in tokens:
        multiplier = _DURATION_MULTIPLIERS.get(unit.lower())
        if multiplier is None:
            return None
        total += int(number) * multiplier
    return str(total)


def extract_section_block(content: str, name: str) -> str | None:
    section_re = re.compile(rf'^\[{re.escape(name)}\][ \t]*$', re.MULTILINE)
    match = section_re.search(content)
    if not match:
        return None
    start = match.end()
    next_section = re.search(r'^\[.+?\][ \t]*$', content[start:], re.MULTILINE)
    end = start + next_section.start() if next_section else len(content)
    return content[start:end]


def list_section_names(content: str) -> list[str]:
    """Tous les noms de section `[nom]` d'un fichier ini fail2ban,
    `[DEFAULT]` exclu (jamais un vrai nom de jail)."""
    names = re.findall(r'^\[(.+?)\][ \t]*$', content, re.MULTILINE)
    return [name for name in names if name != "DEFAULT"]


def read_params_from_block(block: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for param in ("logpath", "maxretry", "bantime", "findtime"):
        match = re.search(rf'^\s*{param}\s*=\s*(.+)$', block, re.MULTILINE)
        if not match:
            continue
        raw_value = match.group(1).strip()
        if param in ("bantime", "findtime"):
            parsed = parse_duration_to_seconds(raw_value)
            if parsed is None:
                continue
            result[param] = parsed
        else:
            result[param] = raw_value
    return result


def _candidate_files(
    jail_d_dir: str,
    jail_conf_path: str | None,
    jail_local_path: str | None,
) -> list[str]:
    base_dir = os.path.dirname(os.path.normpath(jail_d_dir))
    if jail_conf_path is None:
        jail_conf_path = os.path.join(base_dir, "jail.conf")
    if jail_local_path is None:
        jail_local_path = os.path.join(base_dir, "jail.local")

    candidate_files = [jail_conf_path]
    if os.path.isdir(jail_d_dir):
        candidate_files += sorted(
            os.path.join(jail_d_dir, fname) for fname in os.listdir(jail_d_dir) if fname.endswith(".conf")
        )
    candidate_files.append(jail_local_path)
    if os.path.isdir(jail_d_dir):
        candidate_files += sorted(
            os.path.join(jail_d_dir, fname) for fname in os.listdir(jail_d_dir) if fname.endswith(".local")
        )
    return candidate_files


@dataclass(frozen=True, slots=True)
class ExistingJail:
    name: str
    logpath: str | None


def scan_existing_jails(
    jail_d_dir: str = "/etc/fail2ban/jail.d",
    jail_conf_path: str | None = None,
    jail_local_path: str | None = None,
) -> list[ExistingJail]:
    """Toutes les jails deja definies sur disque (n'importe quel
    fichier, n'importe quel nom), avec leur logpath s'il a pu etre
    resolu. Jamais autoritatif a 100% (herite des limites de
    l'algorithme d'origine : [DEFAULT] jamais applique ici), mais
    suffisant pour detecter un doublon avant creation."""
    candidate_files = _candidate_files(jail_d_dir, jail_conf_path, jail_local_path)

    contents: dict[str, str] = {}
    all_names: list[str] = []
    for path in candidate_files:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        contents[path] = content
        for name in list_section_names(content):
            if name not in all_names:
                all_names.append(name)

    jails: list[ExistingJail] = []
    for name in all_names:
        merged: dict[str, str] = {}
        for path in candidate_files:
            cached_content = contents.get(path)
            if cached_content is None:
                continue
            block = extract_section_block(cached_content, name)
            if block is None:
                continue
            merged.update(read_params_from_block(block))
        jails.append(ExistingJail(name=name, logpath=merged.get("logpath")))

    return jails


def existing_logpaths(
    jail_d_dir: str = "/etc/fail2ban/jail.d",
    jail_conf_path: str | None = None,
    jail_local_path: str | None = None,
) -> dict[str, str]:
    """{nom_de_jail: logpath} pour chaque jail existant dont le
    logpath a pu etre resolu (les autres sont omis, jamais devines)."""
    return {
        jail.name: jail.logpath
        for jail in scan_existing_jails(jail_d_dir, jail_conf_path, jail_local_path)
        if jail.logpath is not None
    }
