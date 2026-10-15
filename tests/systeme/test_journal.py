"""Tests de src/systeme/journal.py : format, exceptions et messages
de Qt."""

import io
import logging
import sys
import threading
from collections.abc import Iterator

import pytest
from PySide6.QtCore import QMessageLogContext, QtMsgType

from src.gui import application
from src.systeme import journal


@pytest.fixture
def flux() -> Iterator[io.StringIO]:
    """Journal configuré vers un tampon, configuration d'origine rétablie."""
    racine = logging.getLogger()
    gestionnaires, niveau = racine.handlers[:], racine.level
    crochets = sys.excepthook, threading.excepthook
    tampon = io.StringIO()
    journal.configurer(tampon)
    yield tampon
    racine.handlers[:] = gestionnaires
    racine.setLevel(niveau)
    sys.excepthook, threading.excepthook = crochets


def test_configurer_ecrit_heure_niveau_francais_et_module(flux: io.StringIO) -> None:
    logging.getLogger("src.recherche").error("Passerelles indisponible")
    ligne = flux.getvalue().strip()
    assert ligne.endswith(" ERREUR recherche : Passerelles indisponible")
    assert ligne[2] == ligne[5] == ":"


def test_configurer_ignore_les_messages_de_debogage(flux: io.StringIO) -> None:
    logging.getLogger("src.recherche").debug("détail")
    assert flux.getvalue() == ""


def test_configurer_rappelee_ne_double_pas_les_lignes(flux: io.StringIO) -> None:
    journal.configurer(flux)
    logging.getLogger("src.cache").warning("cache illisible")
    assert flux.getvalue().count("cache illisible") == 1


def test_exception_non_rattrapee_journalisee_avec_sa_trace(flux: io.StringIO) -> None:
    try:
        raise ValueError("valeur imprévue")
    except ValueError as erreur:
        sys.excepthook(type(erreur), erreur, erreur.__traceback__)
    texte = flux.getvalue()
    assert "CRITIQUE systeme.journal : Exception non rattrapée" in texte
    assert "Traceback" in texte
    assert "ValueError: valeur imprévue" in texte


def test_exception_d_un_fil_journalisee(flux: io.StringIO) -> None:
    def echouer() -> None:
        raise RuntimeError("fil en panne")

    fil = threading.Thread(target=echouer, name="verification")
    fil.start()
    fil.join()
    texte = flux.getvalue()
    assert "Exception non rattrapée dans le fil verification" in texte
    assert "RuntimeError: fil en panne" in texte


def test_message_qt_journalise_sous_sa_categorie(flux: io.StringIO) -> None:
    application.journaliser_message_qt(
        QtMsgType.QtWarningMsg, QMessageLogContext(), "Fenetre.qml:12: erreur"
    )
    assert " AVERTISSEMENT qt : Fenetre.qml:12: erreur" in flux.getvalue()
