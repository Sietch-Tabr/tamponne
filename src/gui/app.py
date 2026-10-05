"""Ancien point d'entrée, conservé pour la mise à jour depuis la 1.0.x.

Le `lancer.sh` de la 1.0.x, déjà chargé par bash pendant qu'il applique la
mise à jour, relance ensuite `python -m src.gui.app` : ce module démarre
donc la nouvelle interface (et son nettoyage des fichiers obsolètes).
"""

from src.gui.application import main

if __name__ == "__main__":
    raise SystemExit(main())
