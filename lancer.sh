#!/bin/bash
set -euo pipefail

# Bloc lu en entier avant exécution, puis exit : une mise à jour qui
# réécrit ce fichier pendant qu'il tourne ne peut rien exécuter d'autre.
{
cd "$(dirname "${BASH_SOURCE[0]}")"

# Une mise à jour en attente (data/maj_disponible.json) est appliquée
# avant le lancement, ou aussitôt si l'app quitte avec le code 42
# (« Installer et redémarrer » dans Réglages).
while true; do
    uv sync --quiet
    if [ -f data/maj_disponible.json ]; then
        uv run python -m src.maj --appliquer \
            || echo "Mise à jour indisponible, on continue avec la version actuelle." >&2
        uv sync --quiet
    fi
    # `|| code=$?` : sous `set -e`, un code non nul ferait quitter le
    # script avant la capture.
    code=0
    uv run python -m src.gui.application || code=$?
    [ "$code" -eq 42 ] || break
done
exit 0
}
