"""Orchestration complete : catalogue -> detection -> comparaison aux
jails existants -> plan (creer/sauter, pourquoi) -> application
(ecriture reelle + rechargement fail2ban). Separe de cli.py pour
rester testable sans toucher a un vrai systeme de fichiers racine ni a
un vrai fail2ban (tous les repertoires sont des parametres)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from omega_jail.catalog import Catalog, load_catalog
from omega_jail.detect import DEFAULT_CONFIG_REL_PATH, detect
from omega_jail.duplicates import CatalogEntryStatus, check_catalog_against_existing
from omega_jail.existing_jails import existing_logpaths
from omega_jail.render import RenderedJail, render_entry
from omega_jail.tailscale_bridge import DEFAULT_TAILSCALE_CIDR, find_servcli, render_action_conf

ACTION_CONF_FILENAME = "omega-jail-tailscale-bridge.conf"

PlanOutcome = Literal["create", "overwrite_forced", "skip_unavailable", "skip_duplicate", "skip_collision"]


@dataclass(frozen=True, slots=True)
class PlannedAction:
    name: str
    outcome: PlanOutcome
    detail: str
    rendered: RenderedJail | None = None
    logpath: Path | None = None
    """Meme pour un jail "skip_duplicate" (pas seulement cree/ecrase) :
    fail2ban refuse de demarrer TOUT jail dont le logpath configure
    n'existe pas sur disque - y compris un jail deja existant avant ce
    run (cas reel : le jail casse d'un run precedent reste reference
    dans jail.d/ et continue d'empecher fail2ban de demarrer tant que
    son fichier de log manque, meme apres plusieurs redemarrages -
    retour utilisateur 2026-10-18, "fail2ban marche plus... les
    redemarrages non plus"). apply() doit donc garantir ce fichier pour
    CHAQUE jail du catalogue reellement applicable, quelle que soit la
    raison (cree par ce run ou deja present)."""


@dataclass(frozen=True, slots=True)
class InstallConfig:
    serv_root: Path
    omega_jail_root: Path
    config_rel_path: str = DEFAULT_CONFIG_REL_PATH
    jail_d_dir: Path = Path("/etc/fail2ban/jail.d")
    filter_d_dir: Path = Path("/etc/fail2ban/filter.d")
    action_d_dir: Path = Path("/etc/fail2ban/action.d")
    jail_conf_path: Path | None = None
    jail_local_path: Path | None = None
    tailscale_cidr: str = DEFAULT_TAILSCALE_CIDR
    serv_config_override: str | None = None
    force: bool = False
    only: str | None = None


@dataclass(frozen=True, slots=True)
class InstallReport:
    plan: list[PlannedAction]
    action_conf_content: str
    applied: bool = False


def _select_catalog(catalog: Catalog, only: str | None) -> Catalog:
    if only is None:
        return catalog
    return Catalog(jails=[jail for jail in catalog.jails if jail.name == only])


def build_plan(
    statuses: list[CatalogEntryStatus],
    *,
    use_json_logs: bool,
    jail_d_dir: Path,
    force: bool,
) -> list[PlannedAction]:
    plan: list[PlannedAction] = []
    for status in statuses:
        if status.status == "unavailable":
            plan.append(PlannedAction(name=status.jail.name, outcome="skip_unavailable", detail=status.reason or ""))
            continue
        if status.status == "duplicate":
            plan.append(
                PlannedAction(
                    name=status.jail.name,
                    outcome="skip_duplicate",
                    detail=f"deja surveille par le jail existant {status.duplicate_of!r}",
                    logpath=status.logpath,
                )
            )
            continue

        rendered = render_entry(status, use_json_logs=use_json_logs)
        assert rendered is not None  # status == "available" => render_entry ne retourne jamais None
        target = jail_d_dir / rendered.jail_filename
        if target.exists() and not force:
            plan.append(
                PlannedAction(
                    name=status.jail.name,
                    outcome="skip_collision",
                    detail=f"{target} existe deja (utiliser --force pour ecraser)",
                )
            )
            continue

        outcome: PlanOutcome = "overwrite_forced" if target.exists() else "create"
        plan.append(
            PlannedAction(
                name=status.jail.name, outcome=outcome, detail=str(target), rendered=rendered, logpath=rendered.logpath
            )
        )
    return plan


def prepare(config: InstallConfig, *, catalog_path: Path | None = None) -> InstallReport:
    catalog = load_catalog(catalog_path or (config.omega_jail_root / "catalog.yaml"))
    errors = catalog.validate()
    if errors:
        raise ValueError("catalogue invalide : " + "; ".join(errors))
    catalog = _select_catalog(catalog, config.only)

    detected = detect(config.serv_root, config.config_rel_path)
    existing = existing_logpaths(
        jail_d_dir=str(config.jail_d_dir),
        jail_conf_path=str(config.jail_conf_path) if config.jail_conf_path else None,
        jail_local_path=str(config.jail_local_path) if config.jail_local_path else None,
    )
    statuses = check_catalog_against_existing(catalog, detected, existing)
    use_json_logs = detected.magnet.use_json_logs if detected.magnet else False
    plan = build_plan(statuses, use_json_logs=use_json_logs, jail_d_dir=config.jail_d_dir, force=config.force)

    servcli = find_servcli(config.serv_root)
    bridge_cli = str(config.omega_jail_root / ".venv" / "bin" / "omega-jail-tailscale-bridge")
    action_conf_content = render_action_conf(
        bridge_cli=bridge_cli,
        servcli=str(servcli) if servcli else "",
        servconfig=config.serv_config_override or "",
        tailscale_cidr=config.tailscale_cidr,
    )
    return InstallReport(plan=plan, action_conf_content=action_conf_content)


def apply(report: InstallReport, config: InstallConfig, *, reload_fn: Callable[[], None] | None = None) -> InstallReport:
    config.filter_d_dir.mkdir(parents=True, exist_ok=True)
    config.jail_d_dir.mkdir(parents=True, exist_ok=True)
    config.action_d_dir.mkdir(parents=True, exist_ok=True)

    (config.action_d_dir / ACTION_CONF_FILENAME).write_text(report.action_conf_content, encoding="utf-8")

    for action in report.plan:
        if action.outcome in ("create", "overwrite_forced"):
            rendered = action.rendered
            assert rendered is not None
            (config.filter_d_dir / rendered.filter_filename).write_text(rendered.filter_content, encoding="utf-8")
            (config.jail_d_dir / rendered.jail_filename).write_text(rendered.jail_content, encoding="utf-8")

        if action.logpath is not None and not action.logpath.exists():
            action.logpath.parent.mkdir(parents=True, exist_ok=True)
            action.logpath.touch()

    if reload_fn is not None:
        reload_fn()

    return replace(report, applied=True)
