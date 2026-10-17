#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# ==============================================================================
# Script d'amorçage sécurisé - OMEGA-JAIL CLI
# Exige les privilèges root (écriture sous /etc/fail2ban/, rechargement
# fail2ban-client) - même exigence qu'omega-fire pour le même domaine.
# Dry-run par défaut cote CLI (--apply requis pour écrire quoi que ce
# soit) : l'élévation reste inconditionnelle ici, pour éviter un flux a
# deux etapes (dry-run sans sudo, puis --apply redemandant soudain un
# mot de passe) - meme choix qu'omega-fire.sh.
# ==============================================================================

set -e

# Forcer un environnement UTF-8 : sans ça, sudo (qui réinitialise
# l'environnement par défaut) ou une session distante mal configurée
# peuvent faire retomber LANG/LC_ALL sur une locale C/POSIX, ce qui casse
# l'affichage des icônes.
if [ -z "${LC_ALL:-}" ] && [ -z "${LANG:-}" ] || [ "${LANG:-}" = "C" ] || [ "${LANG:-}" = "POSIX" ]; then
    if locale -a 2>/dev/null | grep -qi '^C\.utf8$'; then
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
    elif locale -a 2>/dev/null | grep -qi '^en_US\.utf8$'; then
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
    fi
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${WHITE}${NC}"
echo -e "${WHITE}    ░▒▓██████████████████████▓▒░${NC}"
echo -e "${WHITE}    ░▒▓ Ω M E G A - J A I L █▓▒░${NC}"
echo -e "${WHITE}    ░▒▓██████████████████████▓▒░${NC}"
echo -e "${WHITE}${NC}"

# 1. Vérification / Élévation des privilèges root (sudo)
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[SECURITY] Omega-Jail requiert les privilèges d'administration.${NC}"
    echo -e "${YELLOW}           (Accès requis pour /etc/fail2ban/ et fail2ban-client.)${NC}\n"
    exec sudo --preserve-env=LANG,LC_ALL "$0" "$@"
    exit $?
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Environnement virtuel introuvable : $VENV_DIR${NC}"
    echo ""
    echo "Lancez d'abord : $SCRIPT_DIR/install.sh"
    exit 1
fi

if ! "$VENV_DIR/bin/python" -c "import omega_jail" 2>/dev/null; then
    echo "⚠️  Le venv semble incomplet, reinstallation..."
    "$VENV_DIR/bin/pip" install -q -e "$SCRIPT_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
exec omega-jail "$@"
