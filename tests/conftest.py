"""Configuration pytest partagée."""

import os
from pathlib import Path

# Rendu Qt hors écran, identique avec ou sans affichage réel ; doit être
# posé avant tout import de PySide6.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from src import cache, candidatures, parametres_affichage, profils, raccourci  # noqa: E402
from src.gui import travailleurs  # noqa: E402


@pytest.fixture(autouse=True)
def _pas_de_verification_maj_reseau(monkeypatch: pytest.MonkeyPatch) -> None:
    """La vérification de mise à jour (`ControleurReglages`) ne doit jamais
    faire de vrai appel réseau pendant les tests (même logique que la
    désactivation des sources réseau, voir CLAUDE.md)."""
    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", lambda: None)


@pytest.fixture(autouse=True)
def _rediriger_affichage_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le choix de thème (écran Réglages) ne doit jamais toucher le vrai
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


@pytest.fixture(autouse=True)
def _rediriger_profils_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le `Pont` de l'interface QML charge les profils dès sa construction."""
    monkeypatch.setattr(profils, "CHEMIN_PROFILS", tmp_path / "profils.json")


@pytest.fixture(autouse=True)
def _rediriger_caches_vers_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lancer une fiche met à jour le cache des offres vues : jamais le vrai
    data/offres.json (ni data/cache.json) pendant les tests."""
    monkeypatch.setattr(cache, "CHEMIN_OFFRES", tmp_path / "offres.json")
    monkeypatch.setattr(cache, "CHEMIN_CACHE", tmp_path / "cache.json")


@pytest.fixture(autouse=True)
def _rediriger_raccourci_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Jamais de raccourci dans le vrai menu des applications pendant les
    tests : profil utilisateur et préférence redirigés."""
    profil = tmp_path / "profil"
    monkeypatch.setenv("HOME", str(profil))
    monkeypatch.setenv("APPDATA", str(profil / "AppData/Roaming"))
    monkeypatch.setenv("XDG_DATA_HOME", str(profil / ".local/share"))
    monkeypatch.setattr(raccourci, "CHEMIN_PREFERENCE", tmp_path / "raccourci.json")
