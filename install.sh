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
#    -xdev, exclusion par chemin via findmnt, filtrage APRES coup par
#    `stat -f`, puis pruning par -fstype verifie EN DIRECT par `find`
#    (toutes tentees successivement, 2026-10-18) : $HOME peut contenir
#    un point de montage reseau/cloud sous forme de partage Samba (deja
#    observe sur cette meme machine : ~/Reseau/hpc-home/,
#    ~/Reseau/mpc-home/, ~/Reseau/craftdark-home/ sont des montages
#    CIFS reels) qui expose(nt) le omega-serv D'UNE AUTRE MACHINE,
#    jamais celui de la machine locale qu'omega-jail est censee
#    proteger (retour utilisateur : "il va aussi sur les partages samba
#    donc j'ai plusieurs omega-serv sur les machines"). Les QUATRE
#    protections precedentes se sont reveles soit insuffisantes sur une
#    autre machine (le parcours entrait malgre tout dans les partages,
#    y compris avec -fstype verifie en direct - mecanisme de montage
#    exact jamais identifie a distance), soit insuffisantes pour la
#    PERFORMANCE (un filtrage apres coup laisse `find` traverser
#    integralement le partage avant de rejeter le resultat - lent meme
#    quand le partage repond : "il met 10mn au moins pour installer
#    (samba)"). Protection supplementaire et PRIORITAIRE desormais :
#    exclusion par NOM de dossier (`-iname`), le seul signal qui ne
#    depend d'AUCUNE detection de montage/systeme de fichiers (ni
#    device, ni fstype, ni table de montage) - donc immunise par
#    construction contre tout mecanisme de montage, quel qu'il soit.
#    Heuristique (les noms couverts sont ceux observes en usage reel
#    plus les plus courants), pas une garantie absolue contrairement
#    aux mecanismes precedents - mais evaluee EN PREMIER (avant meme
#    -fstype) : un dossier nomme "Reseau" est ecarte sans jamais
#    toucher/interroger ce qu'il contient, donc jamais de cout reseau
#    du tout pour ce qui est exclu par ce biais. -xdev et -fstype
#    restent en complement pour tout montage sous un nom non couvert
#    ici. `timeout 8` reste le garde-fou final contre un blocage
#    pendant le parcours lui-meme (ex. disque local defaillant) ; un
#    timeout est traite comme "aucun candidat trouve", jamais comme un
#    echec bloquant.
#    Manuel propose EN PREMIER, avant toute recherche (retour
#    utilisateur 2026-10-18 : "on peut mettre une etape pour la
#    recherche d'une installation soit auto (+long) ou manuelle (plus
#    court) car pour un ~/omega-serv cela peut etre plus rapide") :
#    si l'utilisateur connait deja le chemin (cas frequent : une seule
#    installation omega-serv, toujours au meme endroit), le taper
#    directement evite entierement le parcours de $HOME, aussi rapide
#    et fiable que la recherche soit par ailleurs. L'exemple dans
#    l'invite utilise le vrai $HOME de la machine (jamais un chemin
#    generique/placeholder - meme principe que la discipline deja
#    appliquee aux commandes affichees).
# -------------------------------------------------------------------------
echo ""
read -rp "Chemin de l'installation omega-serv si vous le connaissez deja (ex. $HOME/omega-serv) - laissez vide pour une recherche automatique sous \$HOME (quelques secondes) : " SERV_ROOT_INPUT

if [ -z "$SERV_ROOT_INPUT" ]; then
    info "Recherche d'une installation omega-serv sous \$HOME (max 8s, hors partages montes)..."

    mapfile -t SERV_CANDIDATES < <(timeout 8 find "$HOME" -maxdepth 4 -xdev \
        \( -iname "Reseau" -o -iname "Network" -o -iname "Partages" -o -iname "Shares" \
           -o -iname "nas" -o -iname "smb" -o -iname "cifs" -o -iname "gvfs" \) -prune \
        -o \( -fstype smb2 -o -fstype smbfs -o -fstype smb3 -o -fstype cifs \
              -o -fstype nfs -o -fstype nfs4 -o -fstype fuse.gvfsd-fuse \
              -o -fstype fuse.sshfs -o -fstype afs \) -prune \
        -o -name "omega-serv.sh" -not -path "*/.*" -print 2>/dev/null \
        | xargs -r -n1 dirname | sort -u)

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
