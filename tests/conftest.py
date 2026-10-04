"""Configuration pytest partagée."""

import os
from pathlib import Path

# Rendu Qt hors écran, identique avec ou sans affichage réel ; doit être
# posé avant tout import de PySide6.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from src import candidatures, parametres_affichage  # noqa: E402
from src.gui import travailleurs  # noqa: E402


@pytest.fixture(autouse=True)
def _pas_de_verification_maj_reseau(monkeypatch: pytest.MonkeyPatch) -> None:
    """`FenetrePrincipale` déclenche systématiquement une vérification de
    mise à jour à la construction — jamais de vrai appel réseau pendant
    les tests (même logique que la désactivation des sources réseau,
    voir CLAUDE.md)."""
    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", lambda: None)


@pytest.fixture(autouse=True)
def _rediriger_affichage_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le choix de thème (écran Paramètres) ne doit jamais toucher le vrai
    data/affichage.json pendant les tests."""
    monkeypatch.setattr(
        parametres_affichage, "CHEMIN_AFFICHAGE", tmp_path / "affichage.json"
    )


@pytest.fixture(autouse=True)
def _rediriger_candidatures_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le `Pont` de l'interface QML charge les candidatures dès sa
    construction : jamais le vrai data/candidatures.json pendant les tests."""
    monkeypatch.setattr(
        candidatures, "CHEMIN_CANDIDATURES", tmp_path / "candidatures.json"
    )
    monkeypatch.setattr(candidatures, "DOSSIER_ARCHIVES", tmp_path / "archives")
