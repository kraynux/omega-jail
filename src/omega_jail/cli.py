"""Point d'entree CLI d'omega-jail. Dry-run par defaut (--apply requis
explicitement pour ecrire quoi que ce soit) ; --apply necessite root
(ecriture sous /etc/fail2ban/, rechargement fail2ban-client) - verifie
ici en plus de l'elevation deja faite par omega-jail.sh, pour un
message d'erreur clair meme si la CLI est invoquee directement.

--serv-root reste un argument explicite obligatoire : aucune
convention universelle ne permet de deviner ou se trouve une
installation omega-serv sur un serveur reel (l'arborescence ~/DEV/ de
la machine de developpement n'a rien a voir avec un deploiement reel,
2026-10-17). En revanche, les jails doivent toujours aller dans le
VRAI dossier fail2ban de la machine - --jail-d-dir/--filter-d-dir/
--action-d-dir sont donc auto-detectes par defaut (autodetect.py),
avec verification honnete que /etc/fail2ban existe reellement plutot
que de l'assumer en silence."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from omega_jail.autodetect import find_fail2ban_base_dir
from omega_jail.install import InstallConfig, InstallReport, apply, prepare
from omega_jail.tailscale_bridge import DEFAULT_TAILSCALE_CIDR

_OUTCOME_LABELS: dict[str, str] = {
    "create": "CREE",
    "overwrite_forced": "ECRASE (--force)",
    "skip_unavailable": "IGNORE (source non configuree)",
    "skip_duplicate": "IGNORE (doublon)",
    "skip_collision": "IGNORE (fichier deja present)",
}


def _default_omega_jail_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _print_report(report: InstallReport) -> None:
    for action in report.plan:
        label = _OUTCOME_LABELS.get(action.outcome, action.outcome)
        print(f"[{label}] {action.name} - {action.detail}")
    created = sum(1 for a in report.plan if a.outcome in ("create", "overwrite_forced"))
    skipped = len(report.plan) - created
    print(f"\n{created} jail(s) a creer, {skipped} ignore(s).")


def _default_reload() -> None:
    result = subprocess.run(["fail2ban-client", "reload"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"avertissement : fail2ban-client reload a echoue : {result.stderr.strip()}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omega-jail", description="Catalogue de jails fail2ban pour omega-serv/omega-waf")
    parser.add_argument("--serv-root", required=True, type=Path, help="Racine de l'installation omega-serv a proteger")
    parser.add_argument("--serv-config", default=None, help="Chemin --config a passer a omega-serv (si non standard)")
    parser.add_argument("--omega-jail-root", type=Path, default=None, help="Racine du projet omega-jail (par defaut, auto-detectee)")
    parser.add_argument("--catalog", type=Path, default=None, help="Chemin vers catalog.yaml (par defaut, celui du projet)")
    parser.add_argument("--jail-d-dir", type=Path, default=None, help="Par defaut, auto-detecte sous l'installation fail2ban reelle")
    parser.add_argument("--filter-d-dir", type=Path, default=None, help="Par defaut, auto-detecte sous l'installation fail2ban reelle")
    parser.add_argument("--action-d-dir", type=Path, default=None, help="Par defaut, auto-detecte sous l'installation fail2ban reelle")
    parser.add_argument("--jail-conf-path", type=Path, default=None)
    parser.add_argument("--jail-local-path", type=Path, default=None)
    parser.add_argument("--tailscale-cidr", default=DEFAULT_TAILSCALE_CIDR)
    parser.add_argument("--only", default=None, help="N'installer qu'un seul jail du catalogue (par nom)")
    parser.add_argument("--force", action="store_true", help="Ecraser un jail.d existant portant le meme nom de fichier")
    parser.add_argument("--apply", action="store_true", help="Ecrit reellement les fichiers (defaut : dry-run)")
    return parser


def _resolve_fail2ban_dirs(args: argparse.Namespace) -> tuple[Path, Path, Path] | None:
    if args.jail_d_dir is not None or args.filter_d_dir is not None or args.action_d_dir is not None:
        base = Path("/etc/fail2ban")
        return (
            args.jail_d_dir or base / "jail.d",
            args.filter_d_dir or base / "filter.d",
            args.action_d_dir or base / "action.d",
        )
    base_dir = find_fail2ban_base_dir()
    if base_dir is None:
        return None
    return base_dir / "jail.d", base_dir / "filter.d", base_dir / "action.d"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    omega_jail_root = args.omega_jail_root or _default_omega_jail_root()

    fail2ban_dirs = _resolve_fail2ban_dirs(args)
    if fail2ban_dirs is None:
        print(
            "erreur : fail2ban ne semble pas installe (/etc/fail2ban introuvable) - installez-le, "
            "ou precisez vous-meme --jail-d-dir/--filter-d-dir/--action-d-dir.",
            file=sys.stderr,
        )
        return 1
    jail_d_dir, filter_d_dir, action_d_dir = fail2ban_dirs

    config = InstallConfig(
        serv_root=args.serv_root,
        omega_jail_root=omega_jail_root,
        jail_d_dir=jail_d_dir,
        filter_d_dir=filter_d_dir,
        action_d_dir=action_d_dir,
        jail_conf_path=args.jail_conf_path,
        jail_local_path=args.jail_local_path,
        tailscale_cidr=args.tailscale_cidr,
        serv_config_override=args.serv_config,
        force=args.force,
        only=args.only,
    )

    try:
        report = prepare(config, catalog_path=args.catalog)
    except ValueError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 1

    _print_report(report)

    if not args.apply:
        print("\nDry-run (aucune ecriture) - relancer avec --apply pour installer.")
        return 0

    if os.geteuid() != 0:
        print("erreur : --apply necessite les privileges root.", file=sys.stderr)
        return 1

    apply(report, config, reload_fn=_default_reload)
    print("\nApplique.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
