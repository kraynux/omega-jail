#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# ==============================================================================
# Script d'installation - OMEGA-JAIL
# À lancer depuis le dossier extrait de l'archive : cd omega-jail && ./install.sh
# Résilient : peut être relancé sans erreur si une étape a déjà été faite.
# Cette étape elle-même ne nécessite PAS les privilèges root (venv/pip
# uniquement) - seul ./omega-jail.sh --apply en demandera au lancement.
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
tip()  { echo -e "${WHITE}💡 $1${NC}"; }

echo -e "${WHITE}    ░▒▓███████████████████████████████████████▓▒░${NC}"
echo -e "${WHITE}    ░▒▓ Ω M E G A - J A I L — I N S T A L L A T I O N ▓▒░${NC}"
echo -e "${WHITE}    ░▒▓███████████████████████████████████████▓▒░${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# -------------------------------------------------------------------------
# 1. Environnement virtuel Python
# -------------------------------------------------------------------------
if [ -d ".venv" ]; then
    info ".venv existe déjà, création ignorée."
else
    if ! python3 -m venv .venv 2>/tmp/omega-jail-venv-err.log; then
        err "Échec de la création de l'environnement virtuel."
        warn "Sur Debian/Ubuntu (et dérivées), le module venv n'est pas toujours inclus avec python3 de base."
        tip "Installez-le puis relancez ce script : sudo apt install python3-venv"
        cat /tmp/omega-jail-venv-err.log >&2
        rm -f /tmp/omega-jail-venv-err.log
        exit 1
    fi
    rm -f /tmp/omega-jail-venv-err.log
    ok "Environnement virtuel créé (.venv)."
fi

# -------------------------------------------------------------------------
# 2. Dépendances — pyproject.toml reste l'unique source de verite
#    (PyYAML, seule dependance tierce). Installation editable pour que
#    les consoles scripts omega-jail/omega-jail-tailscale-bridge
#    existent reellement dans .venv/bin/ (le pont Tailscale -> 451
#    omega-serv y fait reference par chemin absolu).
# -------------------------------------------------------------------------
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e .
ok "Dépendances installées."

# -------------------------------------------------------------------------
# 3. Scripts exécutables
# -------------------------------------------------------------------------
chmod +x omega-jail.sh
chmod +x "$SCRIPT_DIR/install.sh"
ok "Scripts rendus exécutables."

# -------------------------------------------------------------------------
# 4. Verification de la presence de fail2ban-client (le seul vrai
#    prerequis externe : omega-jail genere des fichiers de config
#    fail2ban mais ne peut rien recharger sans fail2ban installe).
# -------------------------------------------------------------------------
if command -v fail2ban-client >/dev/null 2>&1; then
    ok "fail2ban-client détecté ($(fail2ban-client --version 2>&1 | head -n1))."
else
    warn "fail2ban-client introuvable : omega-jail peut generer les fichiers de configuration,"
    warn "mais aucun jail ne sera reellement actif sans fail2ban installe."
    tip "Installez-le via le gestionnaire de paquets de votre distribution (pacman -S fail2ban, apt install fail2ban)."
fi

echo ""
ok "Installation terminée."
tip "Aperçu sans rien écrire : ${SCRIPT_DIR}/omega-jail.sh --serv-root /chemin/vers/omega-serv"
tip "Installation réelle (nécessite root) : ${SCRIPT_DIR}/omega-jail.sh --serv-root /chemin/vers/omega-serv --apply"
