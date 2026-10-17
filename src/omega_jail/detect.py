"""Detection des chemins de logs reels d'une installation omega-serv
(et, si configure, du script omega-waf.lua qu'elle execute).

Lecture best-effort de quelques cles JSON precises connues du format
de config d'omega-serv (`config/omega-serve.json`), jamais une
reimplementation complete de son parseur de config (domain/config/) -
omega-jail est un projet separe, pas de dependance a son code source
(meme regle que existing_jails.py vis-a-vis d'omega-fire). Les valeurs
par defaut ci-dessous sont copiees depuis omega-serv (domain/config/
entities.py::LogsConfig, domain/security/waf/config.py::
WafLoggingConfig/MagnetPathsConfig, domain/security/active_defense/
config.py::ActiveDefenseLoggingConfig) - a tenir synchronisees si ces
defauts changent un jour cote omega-serv.

Point verifie dans le code d'omega-serv (pas suppose) : le CHEMIN REEL
du log d'alerte WAF ecrit a l'execution vient de
`options.waf.logging.path` (application/server/start_server.py,
`alert_log_path = project_root / waf_config.logging.path`), jamais de
`logs.waf_alerts` - un champ distinct, non utilise pour la
localisation reelle du fichier (seulement pour la maintenance/rotation
cote service_rules.py). Lire le mauvais champ ferait pointer le jail
WAF vers un fichier que personne n'ecrit jamais."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_REL_PATH = "config/omega-serve.json"

_DEFAULT_ACCESS_LOG = "var/log/access.log"
_DEFAULT_WAF_ALERTS_LOG = "var/log/waf-alerts.log"
_DEFAULT_ACTIVE_DEFENSE_LOG = "var/log/active-defense-enriched.jsonl"
_DEFAULT_MAGNET_ALERTS_LOG = "var/log/waf-magnet-alerts.log"
_DEFAULT_MAGNET_BLOCKLIST_LOG = "var/log/waf-magnet-blocklist.log"


@dataclass(frozen=True, slots=True)
class MagnetInfo:
    alerts_log: Path
    blocklist_log: Path
    use_json_logs: bool


@dataclass(frozen=True, slots=True)
class DetectedPaths:
    access_log: Path
    waf_alerts_log: Path | None
    active_defense_log: Path | None
    magnet: MagnetInfo | None

    def resolve_logpath(self, logpath_key: str) -> Path | None:
        if logpath_key == "access_log":
            return self.access_log
        if logpath_key == "waf_alerts_log":
            return self.waf_alerts_log
        if logpath_key == "active_defense_log":
            return self.active_defense_log
        if logpath_key == "waf_magnet_alerts_log":
            return self.magnet.alerts_log if self.magnet else None
        if logpath_key == "waf_magnet_blocklist_log":
            return self.magnet.blocklist_log if self.magnet else None
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def detect_use_json_logs(script_path: Path) -> bool:
    """Lit la valeur REELLE de `use_json_logs` dans le script Lua
    deploye (jamais une valeur par defaut supposee - c'est une
    constante locale codee en dur dans le script, propre a chaque
    deploiement, jamais exposee via la config JSON d'omega-serv)."""
    if not script_path.exists():
        return False
    try:
        content = script_path.read_text(encoding="utf-8")
    except OSError:
        return False
    match = re.search(r"^\s*local\s+use_json_logs\s*=\s*(true|false)", content, re.MULTILINE)
    if match is None:
        return False
    return match.group(1) == "true"


def _resolve_magnet(serv_root: Path, waf_options: dict[str, Any]) -> MagnetInfo | None:
    magnet = waf_options.get("magnet")
    if not magnet or not magnet.get("enabled", False):
        return None
    paths = magnet.get("paths", {}) or {}
    alerts_log = serv_root / paths.get("alerts_log", _DEFAULT_MAGNET_ALERTS_LOG)
    blocklist_log = serv_root / paths.get("blocklist_log", _DEFAULT_MAGNET_BLOCKLIST_LOG)
    script_rel = magnet.get("script") or ""
    use_json_logs = detect_use_json_logs(serv_root / script_rel) if script_rel else False
    return MagnetInfo(alerts_log=alerts_log, blocklist_log=blocklist_log, use_json_logs=use_json_logs)


def detect(serv_root: Path, config_rel_path: str = DEFAULT_CONFIG_REL_PATH) -> DetectedPaths:
    config = _read_json(serv_root / config_rel_path)

    logs = config.get("logs", {}) or {}
    access_log = serv_root / logs.get("access", _DEFAULT_ACCESS_LOG)

    options = config.get("options", {}) or {}
    waf_options = options.get("waf") or {}

    waf_alerts_log: Path | None = None
    if waf_options.get("enabled", False):
        waf_logging = waf_options.get("logging", {}) or {}
        waf_alerts_log = serv_root / waf_logging.get("path", _DEFAULT_WAF_ALERTS_LOG)

    active_defense_options = options.get("active_defense") or {}
    active_defense_log: Path | None = None
    if active_defense_options.get("enabled", False):
        ad_logging = active_defense_options.get("logging", {}) or {}
        active_defense_log = serv_root / ad_logging.get("log_path", _DEFAULT_ACTIVE_DEFENSE_LOG)

    magnet = _resolve_magnet(serv_root, waf_options)

    return DetectedPaths(
        access_log=access_log,
        waf_alerts_log=waf_alerts_log,
        active_defense_log=active_defense_log,
        magnet=magnet,
    )
