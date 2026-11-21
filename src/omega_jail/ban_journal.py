# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Action fail2ban du journal des bans (plan omega-connect, phase 3 ; decision auteur 2026-11-21 : l'action
est installee par omega-jail, omega-connect ne fait que la liaison, omega-fire ecrit ses propres bans).

Lancee par fail2ban (action.d/omega-jail-ban-journal.conf) a chaque ban et levee d'un jail qui la porte :
jails du catalogue, et jails existants choisis avec `--journal` (sshd...). Ecrit dans la zone omega-synchro
(`bans/journal.jsonl` + `bans/actifs.json`) avec l'origine `fail2ban:<jail>` ; les jails RIPOSTE donnent
`fail2ban:omega-serv-riposte-*`, ignores par Active Defense.

Bibliotheque standard seule (D-016, comme synchro_token.py) : MEME format, MEME verrou (`bans/.verrou`) et
memes regles qu'omega_lib.infrastructure.synchro.ban_writer, l'autre ecrivain (omega-fire). Conformite verifiee
par tests/test_ban_journal.py avec le lecteur d'omega-lib. Copie autonome installee par `--apply` dans
/usr/local/lib/omega-jail/ et lancee avec le Python du systeme.

TOUJOURS fail-open : sans zone (omega-connect absent), ou en cas d'erreur, rien n'est ecrit, le code de sortie
reste 0 et le ban reseau n'est jamais affecte."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import stat
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ZONE_DIR_DEFAULT = "/var/lib/omega-synchro"
ZONE_DIR_ENV = "OMEGA_SYNCHRO_DIR"
BANS_DIR = "bans"
BAN_JOURNAL = "journal.jsonl"
ACTIVE_BANS = "actifs.json"
LOCK_NAME = ".verrou"
FILE_MODE = 0o640
JOURNAL_MAX_BYTES = 10 * 1024 * 1024
ACTIVE_MAX_BYTES = 64 * 1024 * 1024
FORMAT_BAN = "omega-ban"
FORMAT_ACTIVE = "omega-bans-actifs"
SCHEMA_VERSION = 1
MACHINE_ID_PATHS = ("/etc/machine-id", "/var/lib/dbus/machine-id")
_ORIGIN_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,63}$")


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(text: object) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        moment = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None
    return moment.astimezone(timezone.utc) if moment.tzinfo else None


def normalize_network(text: str) -> str | None:
    """Meme regle qu'omega-lib : notation CIDR, IPv4-mapped ramenee en IPv4."""
    try:
        network = ipaddress.ip_network(text.strip(), strict=False)
    except ValueError:
        return None
    if isinstance(network, ipaddress.IPv6Network) and network.network_address.ipv4_mapped is not None:
        prefix = max(network.prefixlen - 96, 0)
        return str(ipaddress.ip_network(f"{network.network_address.ipv4_mapped}/{prefix}", strict=False))
    return str(network)


def jail_origin(jail: str) -> str:
    """`fail2ban:<jail>`, ramene au motif des origines (minuscules, 64 caracteres)."""
    cleaned = re.sub(r"[^a-z0-9._-]", "-", jail.lower()).strip("-.") or "jail"
    return f"fail2ban:{cleaned}"[:64]


def machine_fingerprint() -> str:
    for candidate in MACHINE_ID_PATHS:
        try:
            text = Path(candidate).read_text(encoding="ascii", errors="replace").strip()
        except OSError:
            continue
        if text:
            return hashlib.sha256(f"omega-synchro:{text}".encode()).hexdigest()[:16]
    return ""


def build_event(action: str, ip: str, jail: str, bantime: int | None, now: datetime) -> dict | None:
    network = normalize_network(ip)
    origin = jail_origin(jail)
    if network is None or action not in ("ban", "unban") or not _ORIGIN_RE.match(origin):
        return None
    event = {"format": FORMAT_BAN, "schema_version": SCHEMA_VERSION, "id": uuid.uuid4().hex, "at": _utc(now),
             "action": action, "network": network, "origin": origin, "jail": jail[:64], "reason": jail[:64],
             "host": machine_fingerprint()}
    if action == "ban":
        event["expires_at"] = _utc(now + timedelta(seconds=bantime)) if bantime and bantime > 0 else None
    return event


def record(event: dict, *, zone: Path | None = None, now: datetime | None = None) -> str:
    """Ecrit l'evenement (si c'est un vrai changement) et met a jour actifs.json. Rend l'etat (anglais)."""
    bans = (zone or Path(os.environ.get(ZONE_DIR_ENV) or ZONE_DIR_DEFAULT)) / BANS_DIR
    try:
        info = os.lstat(bans)
    except FileNotFoundError:
        return "no-zone"
    if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.geteuid()):
        return "refused"
    lock = os.open(bans / LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, FILE_MODE)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        moment = now or datetime.now(timezone.utc)
        active = _read_active(bans / ACTIVE_BANS, moment)
        key = (event["network"], event["origin"])
        current = active.get(key)
        if event["action"] == "ban":
            if current is not None and current.get("expires_at") == event.get("expires_at"):
                return "unchanged"
            active[key] = event
        else:
            if current is None:
                return "unchanged"
            del active[key]
        _append(bans / BAN_JOURNAL, event)
        _write_active(bans, active.values(), moment)
        return "written"
    finally:
        os.close(lock)


def _entry(event: dict) -> dict:
    keys = ("id", "at", "action", "network", "origin", "jail", "reason", "host", "expires_at")
    return {key: event.get(key) for key in keys if key in event}


def _read_active(path: Path, moment: datetime) -> dict[tuple[str, str], dict]:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(ACTIVE_MAX_BYTES + 1)
        data = json.loads(raw.decode("utf-8")) if len(raw) <= ACTIVE_MAX_BYTES else None
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("format") != FORMAT_ACTIVE or data.get("schema_version") != 1:
        return {}
    active: dict[tuple[str, str], dict] = {}
    for item in data.get("entries") or []:
        if not isinstance(item, dict) or item.get("action") != "ban":
            continue
        end = _parse_utc(item.get("expires_at"))
        if end is not None and end <= moment:
            continue
        active[(str(item.get("network")), str(item.get("origin")))] = item
    return active


def _append(journal: Path, event: dict) -> None:
    try:
        info = os.lstat(journal)
        if stat.S_ISREG(info.st_mode) and info.st_size >= JOURNAL_MAX_BYTES:
            os.replace(journal, journal.with_name(BAN_JOURNAL + ".1"))
    except FileNotFoundError:
        pass
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    fd = os.open(journal, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, FILE_MODE)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError(f"{journal} is not a regular file")
        os.fchmod(fd, FILE_MODE)
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_active(bans: Path, entries, moment: datetime) -> None:
    ordered = sorted((_entry(e) for e in entries), key=lambda e: (e.get("at", ""), e["network"], e["origin"]))
    payload = {"format": FORMAT_ACTIVE, "schema_version": SCHEMA_VERSION, "updated_at": _utc(moment),
               "entries": ordered}
    tmp = bans / f".{ACTIVE_BANS}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, FILE_MODE)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fchmod(handle.fileno(), FILE_MODE)
            os.fsync(handle.fileno())
        os.replace(tmp, bans / ACTIVE_BANS)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="omega-jail : journal des bans (action fail2ban)")
    parser.add_argument("--mode", choices=("ban", "unban"), required=True)
    parser.add_argument("--ip", required=True)
    parser.add_argument("--jail", required=True)
    parser.add_argument("--bantime", default="")
    try:
        args = parser.parse_args(argv)
        bantime = int(args.bantime) if args.bantime.lstrip("-").isdigit() else None
        now = datetime.now(timezone.utc)
        event = build_event(args.mode, args.ip, args.jail, bantime, now)
        if event is not None:
            record(event, now=now)
    except SystemExit:
        return 0
    except Exception as error:  # noqa: BLE001 - fail-open : le ban reseau ne depend jamais du journal
        print(f"omega-jail ban journal: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
