"""Genere le contenu texte des fichiers filter.d/<nom>.conf et
jail.d/<nom>.conf pour chaque entree "available" du catalogue, a
partir des chemins reels detectes (detect.py) et du resultat de la
comparaison aux jails existants (duplicates.py). Pure generation de
texte - aucune ecriture disque ici (voir install.py).

Forme minimale du jail.d genere : memes champs que
`adapter.py::create_jail` d'omega-fire (enabled/filter/logpath/
maxretry/findtime/bantime, PAS de ligne action/backend en dur) - sauf
l'ajout systematique de l'action `omega-jail-tailscale-bridge` en plus
de `%(action_)s` (heritage du banaction deja configure sur l'hote),
jamais a sa place."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omega_jail.catalog import JailSpec
from omega_jail.duplicates import CatalogEntryStatus

FILTER_NAME_PREFIX = "omega-jail-"
BRIDGE_ACTION_NAME = "omega-jail-tailscale-bridge"


def filter_name(jail_name: str) -> str:
    return f"{FILTER_NAME_PREFIX}{jail_name}"


def _failregex_for(jail: JailSpec, use_json_logs: bool) -> str:
    if jail.format == "auto":
        return jail.failregex_json if use_json_logs else jail.failregex_plain  # type: ignore[return-value]
    assert jail.failregex is not None  # garanti par JailSpec.validate()
    return jail.failregex


def render_filter(jail: JailSpec, *, use_json_logs: bool = False) -> str:
    failregex = _failregex_for(jail, use_json_logs)
    return f"# Genere par Omega-Jail pour {jail.name}\n[Definition]\nfailregex = {failregex}\nignoreregex =\n"


def render_jail(jail: JailSpec, logpath: Path, *, include_bridge_action: bool = True) -> str:
    content = (
        "# Genere par Omega-Jail\n"
        f"[{jail.name}]\n"
        "enabled = true\n"
        f"filter = {filter_name(jail.name)}\n"
        f"logpath = {logpath}\n"
        f"maxretry = {jail.maxretry}\n"
        f"findtime = {jail.findtime}\n"
        f"bantime = {jail.bantime}\n"
    )
    if include_bridge_action:
        content += f"action = %(action_)s\n          {BRIDGE_ACTION_NAME}\n"
    return content


@dataclass(frozen=True, slots=True)
class RenderedJail:
    name: str
    filter_filename: str
    filter_content: str
    jail_filename: str
    jail_content: str
    logpath: Path
    """Chemin du log surveille par ce jail - conserve ici (pas seulement
    injecte dans jail_content) pour qu'install.py puisse creer le
    fichier a vide s'il n'existe pas encore avant de recharger fail2ban
    (sinon : `fail2ban-client reload` echoue avec "Have not found any
    log file for '<jail>' jail" - cas reel pour un jail pointant vers
    un log que son emetteur ne cree que lors de son premier evenement,
    ex. blocklist_log d'omega-waf.lua avant toute premiere alerte)."""


def render_entry(
    status: CatalogEntryStatus,
    *,
    use_json_logs: bool = False,
    include_bridge_action: bool = True,
) -> RenderedJail | None:
    if status.status != "available" or status.logpath is None:
        return None
    jail = status.jail
    filename = f"{filter_name(jail.name)}.conf"
    return RenderedJail(
        name=jail.name,
        filter_filename=filename,
        filter_content=render_filter(jail, use_json_logs=use_json_logs),
        jail_filename=filename,
        jail_content=render_jail(jail, status.logpath, include_bridge_action=include_bridge_action),
        logpath=status.logpath,
    )


def render_available_entries(
    statuses: list[CatalogEntryStatus],
    *,
    use_json_logs: bool = False,
    include_bridge_action: bool = True,
) -> list[RenderedJail]:
    rendered = (
        render_entry(status, use_json_logs=use_json_logs, include_bridge_action=include_bridge_action)
        for status in statuses
    )
    return [r for r in rendered if r is not None]
