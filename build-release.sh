#!/usr/bin/env bash
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# ==============================================================================
# Construit l'archive distribuable omega-jail.tar.gz : copie le projet
# (sans artefacts dev/test), archive le tout dans ../dist/ (a
# l'exterieur du sous-dossier omega-jail/, meme convention que le
# reste de la suite depuis la restructuration de l'arborescence en
# ~/DEV/<CODE>/omega-<nom>/). Aucune dependance a vendorer (PyYAML,
# seule dependance tierce, vient normalement de PyPI) - contrairement
# a omega-serv/omega-fire/etc. qui vendorent omega-lib.
# Outil de maintenance, jamais lui-meme inclus dans l'archive generee.
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
ok()   { echo -e "${GREEN}✅ $1${NC}"; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${DIST_DIR:-$PROJECT_ROOT/../dist}"
ARCHIVE_NAME="omega-jail.tar.gz"

STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGING_DIR"' EXIT
DEST="$STAGING_DIR/omega-jail"
mkdir -p "$DEST"

info "Copie du projet omega-jail..."
rsync -a \
    --exclude='.venv/' --exclude='venv/' \
    --exclude='__pycache__/' --exclude='*.pyc' --exclude='*.egg-info/' \
    --exclude='.pytest_cache/' --exclude='.mypy_cache/' --exclude='.ruff_cache/' \
    --exclude='.git/' --exclude='.claude/' \
    --exclude='*~' --exclude='*.bak' --exclude='*.swp' \
    --exclude='.coverage' --exclude='htmlcov/' \
    --exclude='build-release.sh' --exclude='omega-jail.tar.gz' --exclude='dist/' \
    "$PROJECT_ROOT/" "$DEST/"

info "Archivage..."
mkdir -p "$DIST_DIR"
tar -C "$STAGING_DIR" -czf "$DIST_DIR/$ARCHIVE_NAME" omega-jail

ok "Archive generee : $DIST_DIR/$ARCHIVE_NAME"
echo "sha256sum :"
sha256sum "$DIST_DIR/$ARCHIVE_NAME"
