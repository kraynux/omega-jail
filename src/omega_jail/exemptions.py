"""Reseaux jamais bannis automatiquement (OMEGA-SERV_PLAN-DETAILLE_
SENSITIVE_PATHS.md §3.13, lot 10) - decision utilisateur : seul le trafic
externe peut etre banni ; hote local, Tailscale et reseau local sont exemptes.

La liste vient TOUJOURS d'omega-serv (`omega-serv waf never-auto-block`,
reseaux reellement exemptes pour SA configuration, garde-fou du proxy de
confiance compris), jamais d'une copie en dur ici : un changement de
`options.waf.reputation.never_auto_block` cote omega-serv est repris a la
prochaine installation d'omega-jail, sans rien modifier dans ce projet.

Repli si omega-serv est introuvable ou trop ancien : l'hote local seul
(`127.0.0.0/8 ::1/128`, deja exempte par fail2ban lui-meme via `ignoreself`)
avec un avertissement dans le rapport d'installation - jamais une liste
devinee."""
from __future__ import annotations

import ipaddress
import subprocess
from dataclasses import dataclass
from pathlib import Path

FALLBACK_NETWORKS: tuple[str, ...] = ("127.0.0.0/8", "::1/128")


@dataclass(frozen=True, slots=True)
class ExemptNetworks:
    networks: tuple[str, ...]
    from_omega_serv: bool
    warning: str | None = None


def parse_networks(output: str) -> tuple[str, ...]:
    """Un reseau par ligne ; une ligne illisible invalide TOUTE la sortie
    (jamais une liste partielle silencieuse)."""
    networks: list[str] = []
    for line in output.splitlines():
        value = line.strip()
        if not value:
            continue
        networks.append(str(ipaddress.ip_network(value, strict=False)))
    return tuple(networks)


def read_exempt_networks(servcli: Path | None, servconfig: Path) -> ExemptNetworks:
    if servcli is None:
        return ExemptNetworks(FALLBACK_NETWORKS, False, "binaire omega-serv introuvable : seul l'hote local est exempte")
    try:
        result = subprocess.run(
            [str(servcli), "--config", str(servconfig), "waf", "never-auto-block"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ExemptNetworks(FALLBACK_NETWORKS, False, f"omega-serv injoignable ({exc}) : seul l'hote local est exempte")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-1:] or ["code " + str(result.returncode)]
        return ExemptNetworks(
            FALLBACK_NETWORKS, False,
            f"omega-serv ne fournit pas les reseaux exemptes ({detail[0]}) - version trop ancienne ? "
            "Seul l'hote local est exempte",
        )
    try:
        networks = parse_networks(result.stdout)
    except ValueError as exc:
        return ExemptNetworks(FALLBACK_NETWORKS, False, f"sortie d'omega-serv illisible ({exc}) : seul l'hote local est exempte")
    return ExemptNetworks(networks, True)


def is_exempt(ip: str, networks: tuple[str, ...]) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    for network in networks:
        try:
            parsed = ipaddress.ip_network(network, strict=False)
        except ValueError:
            continue
        if parsed.version == address.version and address in parsed:
            return True
    return False
