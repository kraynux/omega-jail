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

echo -e "${WHITE}    ░▒▓███████████████████████████████████████████████▓▒░${NC}"
echo -e "${WHITE}    ░▒▓ Ω M E G A - J A I L — I N S T A L L A T I O N ▓▒░${NC}"
echo -e "${WHITE}    ░▒▓███████████████████████████████████████████████▓▒░${NC}"
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

# -------------------------------------------------------------------------
# 5. Chemin d'omega-serv a proteger - enregistre UNE FOIS ici
#    (.serv-root, jamais commite - voir .gitignore), pour que les
#    commandes affichees ci-dessous et ./omega-jail.sh soient ensuite
#    utilisables telles quelles, sans placeholder a remplacer a la
#    main (retour utilisateur 2026-10-18 : "le but d'un installateur
#    c'est de pouvoir copier-coller une commande, pas devoir la
#    comprendre et la modifier"). Recherche d'abord automatiquement
#    sous $HOME (retour utilisateur : "l'installateur doit pouvoir
#    trouver le chemin de omega-serv, normalement dans le home") -
#    reconnu par la presence d'omega-serv.sh, jamais par le seul nom
#    du dossier. Un seul candidat trouve -> utilise directement, sans
#    demander (meme principe que la detection d'ancienne installation
#    dans install.sh d'omega-serv : jamais d'action sur un signal
#    ambigu, mais aucune question posee pour autant quand le signal
#    est clair). Zero ou plusieurs candidats -> on demande a l'humain,
#    une seule fois.
# -------------------------------------------------------------------------
echo ""
info "Recherche d'une installation omega-serv sous \$HOME..."
mapfile -t SERV_CANDIDATES < <(find "$HOME" -maxdepth 4 -name "omega-serv.sh" -not -path "*/.*" 2>/dev/null | xargs -r -n1 dirname | sort -u)

SERV_ROOT_INPUT=""
if [ "${#SERV_CANDIDATES[@]}" -eq 1 ]; then
    SERV_ROOT_INPUT="${SERV_CANDIDATES[0]}"
    ok "Installation omega-serv détectée automatiquement : $SERV_ROOT_INPUT"
elif [ "${#SERV_CANDIDATES[@]}" -gt 1 ]; then
    warn "Plusieurs installations omega-serv trouvées sous \$HOME, aucune choisie automatiquement (ambigu) :"
    for c in "${SERV_CANDIDATES[@]}"; do echo "    $c"; done
    read -rp "Collez le chemin exact à utiliser (laisser vide pour le préciser plus tard) : " SERV_ROOT_INPUT
else
    warn "Aucune installation omega-serv trouvée automatiquement sous \$HOME."
    read -rp "Chemin de l'installation omega-serv à protéger (laisser vide pour le préciser plus tard) : " SERV_ROOT_INPUT
fi

if [ -n "$SERV_ROOT_INPUT" ]; then
    SERV_ROOT_INPUT="${SERV_ROOT_INPUT%/}"
    if [ -f "$SERV_ROOT_INPUT/omega-serv.sh" ]; then
        echo "$SERV_ROOT_INPUT" > "$SCRIPT_DIR/.serv-root"
        ok "Chemin enregistré : $SERV_ROOT_INPUT"
    else
        warn "Aucun omega-serv.sh trouvé sous $SERV_ROOT_INPUT - chemin non enregistré."
        tip "Vous pourrez le préciser explicitement avec --serv-root au lancement."
    fi
fi

echo ""
ok "Installation terminée."
if [ -f "$SCRIPT_DIR/.serv-root" ]; then
    tip "Aperçu sans rien écrire : ${SCRIPT_DIR}/omega-jail.sh"
    tip "Installation réelle (nécessite root) : ${SCRIPT_DIR}/omega-jail.sh --apply"
else
    tip "Relancez ./install.sh pour enregistrer le chemin d'omega-serv, ou précisez-le"
    tip "explicitement : ${SCRIPT_DIR}/omega-jail.sh --serv-root <chemin réel> --apply"
fi
