"""Configuration pytest partagée."""

import os

# Force un rendu Qt hors écran pour que les tests GUI (pytest-qt) tournent
# sans display réel — cohérent, que la machine en ait un ou non. Doit être
# posé avant tout import de PySide6.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from src.gui import travailleurs  # noqa: E402


@pytest.fixture(autouse=True)
def _pas_de_verification_maj_reseau(monkeypatch):
    """`FenetrePrincipale` déclenche systématiquement une vérification de
    mise à jour à la construction — jamais de vrai appel réseau pendant
    les tests (même logique que la désactivation des sources réseau,
    voir CLAUDE.md)."""
    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", lambda: None)
