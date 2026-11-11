# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Jeton d'installation d'omega-jail : `var/omega-jeton.json` (contrats d'interconnexion, etape 2 du
2026-11-10 ; spec ~/DEV/CONNECT/SPEC_ETAPE2_CONTRATS_OMEGA_LIB.md §3).

omega-jail ne depend pas d'omega-lib (D-016 : bibliotheque standard seule) : ce module ecrit le MEME
format qu'omega_lib.infrastructure.synchro.install_token, avec les memes regles (jamais en root, seul le
proprietaire du dossier ecrit, autre machine ou dossier copie = nouvel identifiant, ecriture atomique en
0644). Conformite verifiee par tests/test_synchro_token.py contre les fichiers temoins d'omega-lib.

omega-jail n'a pas de fiche : ce qu'il a pose (jails, action du pont) est lu par omega-connect dans
/etc/fail2ban, ou ces fichiers appartiennent a fail2ban."""
from __future__ import annotations

import hashlib
import json
import os
import pwd
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORMAT = "omega-jeton"
SCHEMA_VERSION = 1
TOKEN_RELATIVE_PATH = "var/omega-jeton.json"
TOOL = "omega-jail"
CONTRACTS: dict[str, list[int]] = {}
OFFERS = ("jails", "bridge")
WANTS = ("waf-logs", "riposte-decisions", "blocklist", "protected-list")
MACHINE_ID_PATHS = ("/etc/machine-id", "/var/lib/dbus/machine-id")
_ID = re.compile(r"^[0-9a-f]{32}$")


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def machine_fingerprint(machine_id: str) -> str:
    cleaned = machine_id.strip()
    if not cleaned:
        return ""
    return hashlib.sha256(f"omega-synchro:{cleaned}".encode()).hexdigest()[:16]


def read_machine_fingerprint(paths: tuple[str, ...] = MACHINE_ID_PATHS) -> str:
    for candidate in paths:
        try:
            text = Path(candidate).read_text(encoding="ascii", errors="replace")
        except OSError:
            continue
        if text.strip():
            return machine_fingerprint(text)
    return ""


def read_token(root: Path) -> tuple[str, dict[str, Any] | None]:
    """("ok", jeton) ; ("absent" | "unreadable" | "invalid" | "incompatible", None)."""
    try:
        raw = (root / TOKEN_RELATIVE_PATH).read_bytes()
    except FileNotFoundError:
        return "absent", None
    except OSError:
        return "unreadable", None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "invalid", None
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        return "invalid", None
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        return "invalid", None
    if version > SCHEMA_VERSION:
        return "incompatible", None
    if not isinstance(data.get("installation_id"), str) or not _ID.match(data["installation_id"]):
        return "invalid", None
    if not isinstance(data.get("root"), str) or not data["root"].startswith("/"):
        return "invalid", None
    return "ok", data


def _old_root_has_same_id(existing: dict[str, Any], root: Path) -> bool:
    old_root = Path(existing["root"])
    try:
        if old_root.resolve() == root:
            return False
    except OSError:
        return False
    status, other = read_token(old_root)
    return status == "ok" and other is not None and other["installation_id"] == existing["installation_id"]


def refresh_token(root: Path, version: str, *, now: datetime | None = None, machine: str | None = None,
                  euid: int | None = None) -> tuple[str, dict[str, Any] | None, str]:
    """(issue, jeton, raison) ; issue : created, new_id, updated, unchanged, skipped. Ne leve jamais."""
    try:
        real_root = root.resolve()
        owner_uid = real_root.stat().st_uid
    except OSError as error:
        return "skipped", None, f"root not readable: {error.strerror}"
    effective = os.geteuid() if euid is None else euid
    if effective == 0:
        return "skipped", None, "never written as root"
    if effective != owner_uid:
        return "skipped", None, "only the owner of the directory writes the token"
    status, existing = read_token(real_root)
    if status in ("unreadable", "incompatible"):
        return "skipped", None, f"existing token {status}"
    if existing is not None and existing.get("tool") != TOOL:
        existing = None
    try:
        owner = pwd.getpwuid(owner_uid).pw_name
    except KeyError:
        owner = str(owner_uid)
    fingerprint = read_machine_fingerprint() if machine is None else machine
    wanted = {"tool": TOOL, "version": version, "root": str(real_root), "owner": owner, "machine": fingerprint,
              "contracts": CONTRACTS, "offers": list(OFFERS), "wants": list(WANTS)}

    if existing is None:
        outcome = "created"
    elif existing.get("machine") and fingerprint and existing.get("machine") != fingerprint or existing.get("root") != str(real_root) and _old_root_has_same_id(existing, real_root):
        outcome = "new_id"
    elif all(existing.get(key) == value for key, value in wanted.items()):
        return "unchanged", existing, ""
    else:
        outcome = "updated"

    stamp = _utc(now or datetime.now(timezone.utc))
    fresh = outcome in ("created", "new_id")
    token = {
        "format": FORMAT, "schema_version": SCHEMA_VERSION, "tool": TOOL, "version": version,
        "installation_id": secrets.token_hex(16) if fresh else existing["installation_id"],  # type: ignore[index]
        "machine": fingerprint, "root": str(real_root), "owner": owner,
        "installed_at": stamp if fresh else existing.get("installed_at", stamp),  # type: ignore[union-attr]
        "updated_at": stamp, "contracts": CONTRACTS, "offers": list(OFFERS), "wants": list(WANTS),
    }
    path = real_root / TOKEN_RELATIVE_PATH
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(token, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except OSError as error:
        tmp.unlink(missing_ok=True)
        return "skipped", None, f"write failed: {error.strerror}"
    return outcome, token, ""


def run_synchro(arguments: list[str], project_root: Path, version: str) -> int:
    """`omega-jail synchro jeton` : cree ou met a jour le jeton et l'affiche en JSON."""
    if arguments != ["synchro", "jeton"]:
        print("usage: omega-jail synchro jeton", file=sys.stderr)
        return 2
    _outcome, token, reason = refresh_token(project_root, version)
    if token is None:
        print(f"omega-jail: installation token not written ({project_root / TOKEN_RELATIVE_PATH}): {reason}",
              file=sys.stderr)
        return 1
    print(json.dumps(token, indent=2, ensure_ascii=False))
    return 0
