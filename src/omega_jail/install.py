"""Orchestration complete : catalogue -> detection -> comparaison aux
jails existants -> plan (creer/sauter, pourquoi) -> application
(ecriture reelle + rechargement fail2ban). Separe de cli.py pour
rester testable sans toucher a un vrai systeme de fichiers racine ni a
un vrai fail2ban (tous les repertoires sont des parametres)."""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from omega_jail.catalog import Catalog, load_catalog
from omega_jail.detect import DEFAULT_CONFIG_REL_PATH, detect
from omega_jail.duplicates import CatalogEntryStatus, check_catalog_against_existing
from omega_jail.exemptions import ExemptNetworks, read_exempt_networks
from omega_jail.existing_jails import default_ignoreip_defined, existing_logpaths
from omega_jail.instances import ServInstance, detect_instances
from omega_jail.render import RenderedJail, filter_name, render_entry
from omega_jail.tailscale_bridge import DEFAULT_TAILSCALE_CIDR, find_servcli, render_action_conf

ACTION_CONF_FILENAME = "omega-jail-tailscale-bridge.conf"

PlanOutcome = Literal[
    "create", "overwrite_forced", "update", "skip_unavailable", "skip_duplicate", "skip_collision", "skip_outdated",
]


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
    update: bool = False
    """Regenere les jails d'omega-jail deja installes dont le filtre ou le jail.d differe du catalogue
    (2026-11-02 : une mise a jour ne touchait jamais un jail installe - le correctif des jails 404/401
    restait sans effet)."""
    only: str | None = None
    instances: tuple[ServInstance, ...] | None = None
    """Instances omega-serv pour les jails `per_instance` (RIPOSTE) ; None = detection reelle
    (instances.py : unites systemd + registre d'omega-serv, `serv_root` compris)."""


@dataclass(frozen=True, slots=True)
class InstallReport:
    plan: list[PlannedAction]
    action_conf_content: str
    applied: bool = False
    exemptions: ExemptNetworks | None = None
    keep_default_ignoreip: bool = False
    relay_all: bool = False
    """omega-serv derriere un proxy local : le pont relaie tout ban d'adresse publique en 451 (hors RIPOSTE)."""

    def action_conf_outdated(self, action_d_dir: Path) -> bool:
        """L'action du pont installee differe de celle a installer (ex. relais active par cette version)."""
        current = action_d_dir / ACTION_CONF_FILENAME
        try:
            return current.read_text(encoding="utf-8") != self.action_conf_content
        except OSError:
            return True


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
    ignoreip: tuple[str, ...] = (),
    keep_default_ignoreip: bool = False,
    filter_d_dir: Path | None = None,
    update: bool = False,
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

        rendered = render_entry(
            status, use_json_logs=use_json_logs, ignoreip=ignoreip, keep_default_ignoreip=keep_default_ignoreip,
        )
        assert rendered is not None  # status == "available" => render_entry ne retourne jamais None
        target = jail_d_dir / rendered.jail_filename
        if target.exists() and not force and _installed_differs(rendered, jail_d_dir, filter_d_dir):
            plan.append(
                PlannedAction(
                    name=status.jail.name,
                    outcome="update" if update else "skip_outdated",
                    detail=str(target) if update else "version installee differente du catalogue (--update pour la remplacer)",
                    rendered=rendered if update else None,
                    logpath=rendered.logpath,
                )
            )
            continue
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


def _installed_differs(rendered: RenderedJail, jail_d_dir: Path, filter_d_dir: Path | None) -> bool:
    """Filtre ou jail.d installes differents de ceux que produirait le catalogue actuel. Illisible = inconnu,
    jamais signale (pas de fausse alerte sans droits de lecture)."""
    files = [(jail_d_dir / rendered.jail_filename, rendered.jail_content)]
    if filter_d_dir is not None:
        files.append((filter_d_dir / rendered.filter_filename, rendered.filter_content))
    for path, expected in files:
        try:
            if path.read_text(encoding="utf-8") != expected:
                return True
        except FileNotFoundError:
            return True
        except OSError:
            continue
    return False


def prepare(config: InstallConfig, *, catalog_path: Path | None = None) -> InstallReport:
    catalog = load_catalog(catalog_path or (config.omega_jail_root / "catalog.yaml"))
    errors = catalog.validate()
    if errors:
        raise ValueError("catalogue invalide : " + "; ".join(errors))
    catalog = _select_catalog(catalog, config.only)
    per_instance = [jail for jail in catalog.jails if jail.per_instance]
    catalog = Catalog(jails=[jail for jail in catalog.jails if not jail.per_instance])

    detected = detect(config.serv_root, config.config_rel_path)
    existing = existing_logpaths(
        jail_d_dir=str(config.jail_d_dir),
        jail_conf_path=str(config.jail_conf_path) if config.jail_conf_path else None,
        jail_local_path=str(config.jail_local_path) if config.jail_local_path else None,
    )
    owned = frozenset(
        jail.name for jail in catalog.jails if (config.jail_d_dir / f"{filter_name(jail.name)}.conf").exists()
    )
    statuses = check_catalog_against_existing(catalog, detected, existing, owned_jail_names=owned)
    use_json_logs = detected.magnet.use_json_logs if detected.magnet else False

    servcli = find_servcli(config.serv_root)
    servconfig = Path(config.serv_config_override) if config.serv_config_override else config.serv_root / config.config_rel_path
    exemptions = read_exempt_networks(servcli, servconfig)
    keep_default = default_ignoreip_defined(
        jail_d_dir=str(config.jail_d_dir),
        jail_conf_path=str(config.jail_conf_path) if config.jail_conf_path else None,
        jail_local_path=str(config.jail_local_path) if config.jail_local_path else None,
    )
    plan = build_plan(
        statuses, use_json_logs=use_json_logs, jail_d_dir=config.jail_d_dir, force=config.force,
        ignoreip=exemptions.networks, keep_default_ignoreip=keep_default,
        filter_d_dir=config.filter_d_dir, update=config.update,
    )
    if per_instance:
        instances = config.instances if config.instances is not None else tuple(detect_instances(config.serv_root))
        for instance in instances:
            instance_catalog = Catalog(jails=[
                replace(jail, name=f"{instance.service_name}-{jail.name}", per_instance=False) for jail in per_instance
            ])
            instance_owned = frozenset(
                jail.name for jail in instance_catalog.jails
                if (config.jail_d_dir / f"{filter_name(jail.name)}.conf").exists()
            )
            instance_statuses = check_catalog_against_existing(
                instance_catalog, detect(instance.root, config.config_rel_path), existing, owned_jail_names=instance_owned,
            )
            plan += build_plan(
                instance_statuses, use_json_logs=False, jail_d_dir=config.jail_d_dir, force=config.force,
                ignoreip=exemptions.networks, keep_default_ignoreip=keep_default,
                filter_d_dir=config.filter_d_dir, update=config.update,
            )
    bridge_cli = str(config.omega_jail_root / ".venv" / "bin" / "omega-jail-tailscale-bridge")
    action_conf_content = render_action_conf(
        bridge_cli=bridge_cli,
        servcli=str(servcli) if servcli else "",
        servconfig=config.serv_config_override or "",
        tailscale_cidr=config.tailscale_cidr,
        exempt=",".join(exemptions.networks),
        relay_all=detected.behind_local_proxy,
    )
    return InstallReport(
        plan=plan, action_conf_content=action_conf_content, exemptions=exemptions, keep_default_ignoreip=keep_default,
        relay_all=detected.behind_local_proxy,
    )


def _keep_previous(path: Path) -> None:
    """Copie `<fichier>.bak` avant d'ecraser (reglage modifie a la main recuperable) - fail2ban ne lit que
    *.conf / *.local, la copie n'est jamais chargee."""
    try:
        if path.exists():
            path.with_name(path.name + ".bak").write_bytes(path.read_bytes())
    except OSError:
        pass


def _share_with_serv(logpath: Path) -> None:
    """Un journal cree ici par root (--apply) sortirait root:root 644 : le compte du
    service omega-serv ne pourrait plus y ecrire (cas de riposte-decisions.jsonl, cree
    au premier ban reseau seulement - bans perdus sans message). Il prend donc le
    proprietaire et le groupe de son dossier (var/log, partage avec le service) et
    664, comme FileLineLogger cote omega-serv. Jamais un arret : un echec laisse le
    fichier tel quel."""
    try:
        parent = logpath.parent.stat()
        os.chown(logpath, parent.st_uid, parent.st_gid)
        logpath.chmod(0o664)
    except OSError:
        pass


def apply(report: InstallReport, config: InstallConfig, *, reload_fn: Callable[[], None] | None = None) -> InstallReport:
    config.filter_d_dir.mkdir(parents=True, exist_ok=True)
    config.jail_d_dir.mkdir(parents=True, exist_ok=True)
    config.action_d_dir.mkdir(parents=True, exist_ok=True)

    (config.action_d_dir / ACTION_CONF_FILENAME).write_text(report.action_conf_content, encoding="utf-8")

    for action in report.plan:
        if action.outcome in ("create", "overwrite_forced", "update"):
            rendered = action.rendered
            assert rendered is not None
            for path, content in ((config.filter_d_dir / rendered.filter_filename, rendered.filter_content),
                                  (config.jail_d_dir / rendered.jail_filename, rendered.jail_content)):
                _keep_previous(path)
                path.write_text(content, encoding="utf-8")

        if action.logpath is not None and not action.logpath.exists():
            action.logpath.parent.mkdir(parents=True, exist_ok=True)
            action.logpath.touch()
            _share_with_serv(action.logpath)

    if reload_fn is not None:
        reload_fn()

    return replace(report, applied=True)
