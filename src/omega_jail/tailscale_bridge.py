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
import subprocess
import sys
from pathlib import Path
from string import Template

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
) -> str:
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.substitute(
        bridge_cli=bridge_cli,
        servcli=servcli,
        servconfig=servconfig,
        tailscale_cidr=tailscale_cidr,
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

    try:
        subprocess.run(args, check=False, capture_output=True, timeout=10)
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
    args = parser.parse_args(argv)

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
