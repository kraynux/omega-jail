"""Pont Tailscale -> blocklist native omega-serv (2026-10-17).

Derriere Tailscale, la regle nftables qui accepte le trafic du tunnel
(plage de confiance) passe toujours avant celle que fail2ban insere
pour bannir - le ban reseau est donc un no-op pour ces clients. Ce
module a deux roles distincts dans le meme fichier (coherent, pas un
melange de responsabilites) :
- A L'INSTALLATION (render_action_conf/find_servcli) : localiser le
  binaire omega-serv deja installe et produire le contenu de
  action.d/omega-jail-tailscale-bridge.conf a partir de son gabarit.
- A L'EXECUTION (main, invoque par fail2ban comme actionban/actionunban) :
  si l'IP bannie tombe dans la plage Tailscale, relayer la decision
  vers `omega-serv blocklist add/remove` pour qu'elle recoive un 451
  explicite - sinon ne rien faire (le ban nftables par defaut suffit).

TOUJOURS fail-open cote execution : une erreur ici (binaire absent,
config introuvable, commande en echec) ne doit jamais faire echouer
le ban nftables principal pour tous les autres jails - avertissement
sur stderr (capte par fail2ban dans son propre journal), code de
sortie toujours 0."""
from __future__ import annotations

import argparse
import ipaddress
import os
import pwd
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template

from omega_jail.exemptions import is_exempt

DEFAULT_TAILSCALE_CIDR = "100.64.0.0/10"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "action.d" / "omega-jail-tailscale-bridge.conf"


def find_servcli(serv_root: Path) -> Path | None:
    candidate = serv_root / ".venv" / "bin" / "omega-serv"
    return candidate if candidate.exists() else None


def render_action_conf(
    bridge_cli: str,
    servcli: str,
    servconfig: str = "",
    tailscale_cidr: str = DEFAULT_TAILSCALE_CIDR,
    exempt: str = "",
    relay_all: bool = False,
) -> str:
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.substitute(
        bridge_cli=bridge_cli,
        servcli=servcli,
        servconfig=servconfig,
        tailscale_cidr=tailscale_cidr,
        exempt=exempt,
        relay_all="1" if relay_all else "0",
    )


def is_tailscale_address(ip: str, cidr: str = DEFAULT_TAILSCALE_CIDR) -> bool:
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return address in network


def _warn(message: str) -> None:
    print(f"omega-jail-tailscale-bridge: {message}", file=sys.stderr)


@dataclass(frozen=True, slots=True)
class RunAs:
    """Compte sous lequel lancer omega-serv (kwargs de subprocess.run)."""
    user: int
    group: int
    extra_groups: tuple[int, ...]
    home: str


def run_as_installation_owner(servcli: str) -> RunAs | None:
    """Incident reel du 2026-10-18 (craftdark) : fail2ban execute ce pont en
    ROOT ; `omega-serv blocklist add` reecrivait alors secure/waf/blocklist.json
    en root:root 600 - le service ne pouvait plus le lire et levait
    PermissionError sur CHAQUE requete (site entier en 502). On lance donc
    omega-serv sous le PROPRIETAIRE de son installation (racine
    `<serv_root>` = 3 niveaux au-dessus de `<serv_root>/.venv/bin/omega-serv`),
    jamais en root. None = rien a changer (pas root, ou installation possedee
    par root, ou proprietaire introuvable)."""
    if os.geteuid() != 0 or not servcli:
        return None
    try:
        serv_root = Path(servcli).resolve().parents[2]
        owner_uid = serv_root.stat().st_uid
        entry = pwd.getpwuid(owner_uid)
    except (OSError, IndexError, KeyError):
        return None
    if owner_uid == 0:
        return None
    groups = tuple(g for g in os.getgrouplist(entry.pw_name, entry.pw_gid) if g != entry.pw_gid)
    return RunAs(user=owner_uid, group=entry.pw_gid, extra_groups=groups, home=entry.pw_dir)


def run_blocklist_command(
    servcli: str,
    action: str,
    ip: str,
    *,
    servconfig: str = "",
    reason: str = "omega-jail",
    bantime_seconds: int | None = None,
    origin: str | None = None,
) -> bool | None:
    """True : commande acceptee ; False : refusee (ex. aucune entree de cette origine) ; None : omega-serv
    trop ancien pour `--origin` (option inconnue) ou injoignable - l'appelant retombe sur l'ancien
    comportement."""
    if not servcli:
        _warn("servcli non configure, pont ignore (fail-open)")
        return None

    args = [servcli]
    if servconfig:
        args += ["--config", servconfig]
    args += ["blocklist", action, "--network", host_network(ip)]
    if action == "add":
        args += ["--reason", reason]
        if bantime_seconds is not None:
            args += ["--duration-seconds", str(bantime_seconds)]
    if origin is not None:
        result = _run_servcli_result(servcli, args + ["--origin", origin])
        if result is None:
            return None
        if result.returncode == 2 and "--origin" in result.stderr:
            # omega-serv d'avant 2.6.1 : l'option n'existe pas encore.
            if action == "add":
                _run_servcli(servcli, args)
                return True
            return None
        return result.returncode == 0
    _run_servcli(servcli, args)
    return True


def host_network(ip: str) -> str:
    """Une seule adresse : /32 en IPv4, /128 en IPv6 (2026-11-02 : « /32 » etait ajoute aussi a une IPv6,
    soit un bloc entier d'operateur - sans effet tant que seules les IP Tailscale etaient relayees)."""
    try:
        return f"{ip}/128" if ipaddress.ip_address(ip).version == 6 else f"{ip}/32"
    except ValueError:
        return f"{ip}/32"


def _run_servcli(servcli: str, args: list[str], *, capture: bool = False) -> str | None:
    result = _run_servcli_result(servcli, args)
    if result is None:
        return None
    if capture:
        return result.stdout if result.returncode == 0 else None
    return None


def _run_servcli_result(servcli: str, args: list[str]) -> subprocess.CompletedProcess[str] | None:
    run_as = run_as_installation_owner(servcli)
    # Francais force : sortie de « blocklist list » jamais traduite (« permanent »), lue par le pont.
    env = {**os.environ, "OMEGA_SERV_LANG": "fr"}
    extra: dict[str, object] = {"env": env}
    if run_as is not None:
        extra = {
            "user": run_as.user, "group": run_as.group, "extra_groups": list(run_as.extra_groups),
            "env": {**env, "HOME": run_as.home},
        }
    try:
        return subprocess.run(args, check=False, capture_output=True, text=True, timeout=10, **extra)  # type: ignore[call-overload]
    except OSError as exc:
        _warn(f"echec appel {servcli} (fail-open, ban nftables inchange) : {exc}")
        return None
    except subprocess.TimeoutExpired:
        _warn(f"timeout appel {servcli} (fail-open)")
        return None


@dataclass(frozen=True, slots=True)
class BlocklistLine:
    network: str
    source: str
    expires_at: datetime | None
    """None = permanent (ou date illisible : traitee comme permanente, dans le doute on ne touche a rien)."""
    reason: str
    origin: str | None = None
    """Outil qui a pose le ban (omega-serv 2.6.1+, `blocklist list --format json`) ; None sinon."""


BRIDGE_REASON_PREFIX = "omega-jail:"
BRIDGE_ORIGIN_PREFIX = "omega-jail:"


def bridge_origin(jail: str) -> str:
    """Origine posee dans omega-serv : `omega-jail:<jail>` (minuscules, caracteres admis par omega-serv)."""
    cleaned = "".join(ch if ch.isalnum() or ch in "._:-" else "-" for ch in jail.lower())
    return f"{BRIDGE_ORIGIN_PREFIX}{cleaned}"[:64]


def _from_bridge(entry: BlocklistLine) -> bool:
    return (entry.origin or "").startswith(BRIDGE_ORIGIN_PREFIX) or entry.reason.startswith(BRIDGE_REASON_PREFIX)


def read_blocklist(servcli: str, servconfig: str = "") -> list[BlocklistLine] | None:
    """Entrees de la blocklist d'omega-serv ; None si illisible (le pont reste alors prudent)."""
    if not servcli:
        return None
    base = [servcli] + (["--config", servconfig] if servconfig else []) + ["blocklist", "list"]
    # Sortie JSON versionnee (omega-serv 2.6.1+), jamais traduite ; sinon ancienne sortie texte.
    output = _run_servcli(servcli, base + ["--format", "json"], capture=True)
    if output is not None:
        parsed = parse_blocklist_json(output)
        if parsed is not None:
            return parsed
    output = _run_servcli(servcli, base, capture=True)
    if output is None:
        return None
    return parse_blocklist_list(output)


def parse_blocklist_json(output: str) -> list[BlocklistLine] | None:
    import json

    try:
        payload = json.loads(output)
        if payload.get("schema_version") != 1:
            return None
        lines: list[BlocklistLine] = []
        for item in payload["entries"]:
            expires: datetime | None = None
            if item.get("expires_at"):
                try:
                    expires = datetime.fromisoformat(item["expires_at"])
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=timezone.utc)
                except ValueError:
                    expires = None
            lines.append(BlocklistLine(item["network"], item.get("source", ""), expires, item.get("reason", ""),
                                       item.get("origin")))
        return lines
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def parse_blocklist_list(output: str) -> list[BlocklistLine]:
    lines: list[BlocklistLine] = []
    for raw in output.splitlines():
        fields = raw.split("\t")
        if len(fields) < 4:
            continue
        try:
            expires: datetime | None = datetime.fromisoformat(fields[2])
            if expires is not None and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
        except ValueError:
            expires = None
        lines.append(BlocklistLine(fields[0], fields[1], expires, "\t".join(fields[3:])))
    return lines


def _covering(entries: list[BlocklistLine], ip: str, now: datetime) -> list[BlocklistLine]:
    address = ipaddress.ip_address(ip)
    found = []
    for entry in entries:
        if entry.expires_at is not None and entry.expires_at <= now:
            continue
        try:
            if address in ipaddress.ip_network(entry.network, strict=False):
                found.append(entry)
        except ValueError:
            continue
    return found


def should_add(entries: list[BlocklistLine] | None, ip: str, bantime_seconds: int | None, now: datetime) -> bool:
    """Jamais ecraser un ban plus fort qui n'est pas celui du pont : un ban manuel (decision humaine), permanent
    ou plus long (ex. auto-ban WAF de 24 h, qu'un relais de 12 h aurait raccourci - constate le 2026-11-02 sur
    craftdark, car `blocklist add` remplace toujours). Blocklist illisible : ajout (comportement d'avant)."""
    if entries is None:
        return True
    target = None if bantime_seconds is None else now + timedelta(seconds=bantime_seconds)
    for entry in _covering(entries, ip, now):
        if _from_bridge(entry):
            # Ban d'un autre jail du pont : garde s'il dure plus longtemps (2026-11-10 : un jail de 12 h
            # remplacait le ban de 24 h d'un autre jail, puis le levait au bout de 12 h).
            if entry.expires_at is None or (target is not None and entry.expires_at >= target):
                return False
            continue
        if entry.source == "manual" or entry.expires_at is None:
            return False
        if target is not None and entry.expires_at >= target:
            return False
    return True


def should_remove(entries: list[BlocklistLine] | None, ip: str, now: datetime, jail: str | None = None) -> bool:
    """Ne retirer que l'entree posee par le pont lui-meme - et, si `jail` est donne, par CE jail.
    Illisible : rien (elle expire d'elle-meme)."""
    if entries is None:
        return False
    network = ipaddress.ip_network(host_network(ip), strict=False)
    for entry in _covering(entries, ip, now):
        try:
            same = ipaddress.ip_network(entry.network, strict=False) == network
        except ValueError:
            continue
        if not same or not _from_bridge(entry):
            continue
        if jail is None or entry.reason == f"{BRIDGE_REASON_PREFIX}{jail}" or entry.origin == bridge_origin(jail):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omega-jail-tailscale-bridge")
    parser.add_argument("--ip", required=True)
    parser.add_argument("--mode", required=True, choices=["ban", "unban"])
    parser.add_argument("--servcli", default="")
    parser.add_argument("--servconfig", default="")
    parser.add_argument("--cidr", default=DEFAULT_TAILSCALE_CIDR)
    parser.add_argument("--jail", default="omega-jail")
    parser.add_argument("--bantime", type=int, default=None)
    parser.add_argument(
        "--relay-all", default="0",
        help="1 : omega-serv derriere un proxy local (Funnel) - relayer TOUTE adresse publique, pas seulement Tailscale",
    )
    parser.add_argument(
        "--exempt", default="",
        help="reseaux jamais bannis (virgules), fournis par omega-serv a l'installation",
    )
    args = parser.parse_args(argv)

    exempt_networks = tuple(n for n in args.exempt.split(",") if n.strip())
    if is_exempt(args.ip, exempt_networks):
        # OMEGA-SERV_PLAN-DETAILLE_SENSITIVE_PATHS.md lot 10 : jamais un ban
        # relaye pour une adresse exemptee (hote local, Tailscale, reseau local).
        _warn(f"{args.ip} est exemptee de ban automatique : rien n'est relaye")
        return 0
    # Derriere un proxy local (2026-11-02), le ban pare-feu ne touche pas le visiteur : relais de toute adresse
    # publique. Jamais pour une jail RIPOSTE : RIPOSTE a deja pose son ban local, et le debannissement de la
    # jail (1 h) retirerait avant terme un ban RIPOSTE plus long (palier de 2 h -> jail de 1 h).
    relay_all = args.relay_all == "1" and "-riposte-" not in args.jail
    if relay_all or is_tailscale_address(args.ip, args.cidr):
        now = datetime.now(timezone.utc)
        origin = bridge_origin(args.jail)
        if args.mode == "unban":
            # Retrait conditionnel en UNE operation (omega-serv 2.6.1+) : seulement si l'entree vient
            # toujours de ce jail - jamais un ban pose entre-temps par le WAF, RIPOSTE ou une personne.
            done = run_blocklist_command(args.servcli, "remove", args.ip, servconfig=args.servconfig, origin=origin)
            if done is not None:
                return 0
            entries = read_blocklist(args.servcli, args.servconfig)
            if should_remove(entries, args.ip, now, jail=args.jail):
                run_blocklist_command(args.servcli, "remove", args.ip, servconfig=args.servconfig)
            return 0
        entries = read_blocklist(args.servcli, args.servconfig)
        if not should_add(entries, args.ip, args.bantime, now):
            _warn(f"{args.ip} deja bannie plus fortement dans omega-serv : ban existant conserve")
            return 0
        run_blocklist_command(
            args.servcli, "add", args.ip,
            servconfig=args.servconfig,
            reason=f"{BRIDGE_REASON_PREFIX}{args.jail}",
            bantime_seconds=args.bantime,
            origin=origin,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
