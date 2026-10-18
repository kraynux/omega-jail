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
) -> str:
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.substitute(
        bridge_cli=bridge_cli,
        servcli=servcli,
        servconfig=servconfig,
        tailscale_cidr=tailscale_cidr,
        exempt=exempt,
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
) -> None:
    if not servcli:
        _warn("servcli non configure, pont ignore (fail-open)")
        return

    args = [servcli]
    if servconfig:
        args += ["--config", servconfig]
    args += ["blocklist", action, "--network", f"{ip}/32"]
    if action == "add":
        args += ["--reason", reason]
        if bantime_seconds is not None:
            args += ["--duration-seconds", str(bantime_seconds)]

    run_as = run_as_installation_owner(servcli)
    extra: dict[str, object] = {}
    if run_as is not None:
        extra = {
            "user": run_as.user, "group": run_as.group, "extra_groups": list(run_as.extra_groups),
            "env": {**os.environ, "HOME": run_as.home},
        }
    try:
        subprocess.run(args, check=False, capture_output=True, timeout=10, **extra)  # type: ignore[call-overload]
    except OSError as exc:
        _warn(f"echec appel {servcli} (fail-open, ban nftables inchange) : {exc}")
    except subprocess.TimeoutExpired:
        _warn(f"timeout appel {servcli} (fail-open)")


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
    if is_tailscale_address(args.ip, args.cidr):
        run_blocklist_command(
            args.servcli,
            "add" if args.mode == "ban" else "remove",
            args.ip,
            servconfig=args.servconfig,
            reason=f"omega-jail:{args.jail}",
            bantime_seconds=args.bantime,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
