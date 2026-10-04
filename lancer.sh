#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Boucle : une mise à jour en attente (data/maj_disponible.json, posée par
# l'app via src.maj) est appliquée avant le lancement — au prochain
# lancement normal, ou immédiatement si l'app a quitté avec le code 42
# (clic sur « Mettre à jour maintenant » dans Paramètres).
while true; do
    uv sync --quiet
    if [ -f data/maj_disponible.json ]; then
        uv run python -m src.maj --appliquer \
            || echo "Mise à jour indisponible, on continue avec la version actuelle." >&2
        uv sync --quiet
    fi
    # `|| code=$?` plutôt que `code=$?` seul : sous `set -e`, un code de
    # sortie non nul sur la ligne précédente ferait quitter le script
    # avant même d'atteindre la capture du code.
    code=0
    uv run python -m src.gui.application || code=$?
    [ "$code" -eq 42 ] || break
done
