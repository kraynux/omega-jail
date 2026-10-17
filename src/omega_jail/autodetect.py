"""Auto-detection du vrai dossier fail2ban de la machine - pour que
les jails generes aillent reellement ou fail2ban les lira, jamais vers
un chemin suppose en silence.

Ne cherche PAS a deviner l'emplacement d'une installation omega-serv :
aucune convention universelle n'existe pour ca sur un serveur reel
(l'arborescence ~/DEV/ d'une machine de developpement n'a rien a voir
avec un deploiement reel, 2026-10-17) - --serv-root reste un argument
explicite obligatoire (voir cli.py)."""
from __future__ import annotations

from pathlib import Path

DEFAULT_FAIL2BAN_BASE_DIR = Path("/etc/fail2ban")


def find_fail2ban_base_dir() -> Path | None:
    """`/etc/fail2ban` est la convention quasi universelle de fail2ban
    sur toutes les distributions - pas de recherche multi-emplacements
    fantaisiste ici, seulement une verification honnete que ce
    repertoire existe reellement avant d'y ecrire quoi que ce soit."""
    return DEFAULT_FAIL2BAN_BASE_DIR if DEFAULT_FAIL2BAN_BASE_DIR.is_dir() else None
