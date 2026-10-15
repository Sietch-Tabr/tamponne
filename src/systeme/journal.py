"""Journal de l'interface : messages horodatés sur la sortie d'erreur, que
`src.lanceur` recopie dans `data/tamponne.log`.

Un seul processus écrit le fichier (le lanceur) : pas de verrou à partager
avec l'interface, et l'anonymisation du lanceur s'applique à tout.
"""

import logging
import sys
import threading
from types import TracebackType
from typing import Final, TextIO

NIVEAUX: Final = {
    logging.DEBUG: "DÉBOGAGE",
    logging.INFO: "INFO",
    logging.WARNING: "AVERTISSEMENT",
    logging.ERROR: "ERREUR",
    logging.CRITICAL: "CRITIQUE",
}

journal = logging.getLogger(__name__)


class FormatJournal(logging.Formatter):
    """`20:15:07 ERREUR recherche : message`, niveau en français et module
    sans le préfixe `src.`."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(niveau)s %(module_court)s : %(message)s")
        self.datefmt = "%H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        record.niveau = NIVEAUX.get(record.levelno, record.levelname)
        record.module_court = record.name.removeprefix("src.")
        return super().format(record)


def _exception_non_rattrapee(
    type_: type[BaseException],
    valeur: BaseException,
    trace: TracebackType | None,
) -> None:
    journal.critical("Exception non rattrapée", exc_info=(type_, valeur, trace))


def _exception_de_fil(arguments: threading.ExceptHookArgs) -> None:
    if arguments.exc_value is None:
        return
    nom = arguments.thread.name if arguments.thread is not None else "?"
    journal.critical(
        "Exception non rattrapée dans le fil %s",
        nom,
        exc_info=(arguments.exc_type, arguments.exc_value, arguments.exc_traceback),
    )


def configurer(flux: TextIO | None = None) -> None:
    """Journal racine niveau INFO vers `flux` (sortie d'erreur par défaut),
    au format `FormatJournal` ; exceptions non rattrapées, du fil principal
    comme des autres, journalisées avec leur trace. Rappelée, elle remplace
    la configuration précédente au lieu de doubler les lignes."""
    gestionnaire = logging.StreamHandler(flux if flux is not None else sys.stderr)
    gestionnaire.setFormatter(FormatJournal())
    racine = logging.getLogger()
    for ancien in racine.handlers[:]:
        if isinstance(ancien.formatter, FormatJournal):
            racine.removeHandler(ancien)
    racine.addHandler(gestionnaire)
    racine.setLevel(logging.INFO)
    sys.excepthook = _exception_non_rattrapee
    threading.excepthook = _exception_de_fil
