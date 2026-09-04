"""Tests du dialogue de détail d'offre (src/gui/widgets/dialogue_detail_offre.py)."""

import src.gui.widgets.dialogue_detail_offre as module_dialogue
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel

from src.gui.widgets.dialogue_detail_offre import DialogueDetailOffre
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE


def _texte_complet(dialogue: DialogueDetailOffre) -> str:
    morceaux = [label.text() for label in dialogue.findChildren(QLabel)]
    morceaux += [groupe.title() for groupe in dialogue.findChildren(QGroupBox)]
    return "\n".join(morceaux)


def test_dialogue_detail_affiche_toutes_les_sections_renseignees(
    qtbot, tmp_path, monkeypatch
):
    detail = {
        "description": "Missions principales : piloter le projet X.",
        "salaire": "Non renseigné",
        "experience_requise": "Confirmé",
        "formation_requise": "",
        "secteur": "Numérique",
        "date_publication": "31/08/2026",
        "a_propos_employeur": "Présentation du service employeur.",
        "sections_complementaires": {
            "Informations complémentaires": "Contact : Jean Dupont"
        },
        "page_html": "<html></html>",
        "lien_postuler": "https://talent-soft.com/candidature/123",
        "date_limite": "06/09/2026",
    }
    chemin_pdf = tmp_path / "ref-1.pdf"
    chemin_pdf.write_bytes(b"%PDF-1.4 factice")
    monkeypatch.setattr(module_dialogue, "chemin_archive_pdf", lambda ref: chemin_pdf)

    dialogue = DialogueDetailOffre(
        "Chargé de mission numérique",
        "Ministère de test",
        detail,
        "https://choisirleservicepublic.gouv.fr/offre-1/",
        "ref-1",
    )
    qtbot.addWidget(dialogue)
    texte = _texte_complet(dialogue)

    assert "Chargé de mission numérique" in texte
    assert "Ministère de test" in texte
    assert "Description du poste" in texte
    assert "Missions principales : piloter le projet X." in texte
    assert "Salaire : Non renseigné" in texte
    assert "Qui sommes-nous ?" in texte
    assert "Présentation du service employeur." in texte
    assert "Informations complémentaires" in texte
    assert "Contact : Jean Dupont" in texte
    assert "Date limite de candidature : 06/09/2026" in texte
    assert dialogue.bouton_postuler.isEnabled() is True
    assert dialogue.bouton_en_ligne.isEnabled() is True
    assert dialogue.bouton_archive.isEnabled() is True


def test_dialogue_detail_vide_affiche_message_par_defaut(qtbot):
    dialogue = DialogueDetailOffre("Poste sans détail", "Employeur", DETAIL_VIDE)
    qtbot.addWidget(dialogue)
    texte = _texte_complet(dialogue)

    assert "Aucun détail disponible pour cette offre." in texte
    # Ni URL ni référence de candidature fournies : rien à ouvrir.
    assert dialogue.bouton_postuler.isEnabled() is False
    assert dialogue.bouton_en_ligne.isEnabled() is False
    assert dialogue.bouton_archive.isEnabled() is False


def test_bouton_archive_desactive_si_le_pdf_nexiste_pas_encore(qtbot):
    # Cas de l'écran Recherche : offre pas encore suivie, aucune
    # archive PDF n'a encore été générée pour cette référence.
    dialogue = DialogueDetailOffre(
        "Poste", "Employeur", DETAIL_VIDE, reference="ref-jamais-suivie"
    )
    qtbot.addWidget(dialogue)

    assert dialogue.bouton_archive.isEnabled() is False


def test_bouton_en_ligne_ouvre_lurl_dans_le_navigateur(qtbot, monkeypatch):
    ouvertes = []
    monkeypatch.setattr("webbrowser.open", lambda url: ouvertes.append(url))
    dialogue = DialogueDetailOffre(
        "Poste",
        "Employeur",
        DETAIL_VIDE,
        "https://choisirleservicepublic.gouv.fr/offre-1/",
    )
    qtbot.addWidget(dialogue)

    qtbot.mouseClick(dialogue.bouton_en_ligne, Qt.MouseButton.LeftButton)

    assert ouvertes == ["https://choisirleservicepublic.gouv.fr/offre-1/"]


def test_bouton_postuler_ouvre_le_lien_de_candidature(qtbot, monkeypatch):
    ouvertes = []
    monkeypatch.setattr("webbrowser.open", lambda url: ouvertes.append(url))
    detail = dict(DETAIL_VIDE)
    detail["lien_postuler"] = "https://talent-soft.com/candidature/123"
    dialogue = DialogueDetailOffre("Poste", "Employeur", detail)
    qtbot.addWidget(dialogue)

    qtbot.mouseClick(dialogue.bouton_postuler, Qt.MouseButton.LeftButton)

    assert ouvertes == ["https://talent-soft.com/candidature/123"]


def test_bouton_archive_ouvre_le_pdf_archive(qtbot, tmp_path, monkeypatch):
    ouvertes = []
    monkeypatch.setattr("webbrowser.open", lambda uri: ouvertes.append(uri))
    chemin_pdf = tmp_path / "ref-1.pdf"
    chemin_pdf.write_bytes(b"%PDF-1.4 factice")
    monkeypatch.setattr(module_dialogue, "chemin_archive_pdf", lambda ref: chemin_pdf)

    dialogue = DialogueDetailOffre("Poste", "Employeur", DETAIL_VIDE, reference="ref-1")
    qtbot.addWidget(dialogue)

    qtbot.mouseClick(dialogue.bouton_archive, Qt.MouseButton.LeftButton)

    assert ouvertes == [chemin_pdf.as_uri()]
