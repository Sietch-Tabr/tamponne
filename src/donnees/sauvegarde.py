"""Export et import des données de l'utilisateur (changement d'ordinateur,
sauvegarde).

L'export est un zip : fiches, candidatures, offres vues, préférences,
fiches de poste archivées en PDF et un manifeste. Le cache des
organisations, le marqueur de mise à jour et le raccourci, propres à la
machine ou régénérés, n'en font pas partie.

L'import remplace toutes les données, après une copie de sécurité des
données actuelles. Les chemins sont lus à chaque appel dans les modules
propriétaires (redirigés en test par `conftest.py`). Sans dépendance à Qt.
"""

import json
import os
import re
import shutil
import tempfile
lazy import zipfile
from datetime import datetime
from pathlib import Path

from src.donnees import (
    cache,
    candidatures,
    parametres_affichage,
    parametres_sources,
    profils,
)
from src.maj import version_locale

APPLICATION = "Tamponné"
FORMAT = 1
"""Version du format d'export, à incrémenter si son contenu change."""
NOM_MANIFESTE = "manifeste.json"
NOM_COPIE_SECURITE = "sauvegarde-avant-import.zip"
TAILLE_MAX = 500 * 1024 * 1024
"""Taille décompressée maximale acceptée à l'import (archive piégée)."""

_ARCHIVE_PDF = re.compile(r"archives/[^/\\]+\.pdf")


class ErreurSauvegarde(Exception):
    """Export ou import impossible ; le message s'affiche tel quel."""


def _fichiers() -> dict[str, Path]:
    """Nom dans l'export → fichier de données correspondant."""
    return {
        "profils.json": profils.CHEMIN_PROFILS,
        "candidatures.json": candidatures.CHEMIN_CANDIDATURES,
        "offres.json": cache.CHEMIN_OFFRES,
        "sources.json": parametres_sources.CHEMIN_SOURCES,
        "affichage.json": parametres_affichage.CHEMIN_AFFICHAGE,
    }


def chemin_copie_securite() -> Path:
    """Copie des données faite avant le dernier import, dans `data/`."""
    return profils.CHEMIN_PROFILS.parent / NOM_COPIE_SECURITE


def nom_export(jour: datetime | None = None) -> str:
    """Nom de fichier proposé à l'export : `Tamponne-donnees-AAAA-MM-JJ.zip`."""
    return f"Tamponne-donnees-{(jour or datetime.now()):%Y-%m-%d}.zip"


def exporter_donnees(destination: Path) -> None:
    """Écrit toutes les données exportables dans le zip `destination`.

    Raises:
        ErreurSauvegarde: Écriture impossible (dossier protégé, disque plein).
    """
    manifeste = {
        "application": APPLICATION,
        "format": FORMAT,
        "version": version_locale(),
        "date": datetime.now().isoformat(timespec="seconds"),
    }
    temporaire: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descripteur, nom_temporaire = tempfile.mkstemp(
            dir=destination.parent, suffix=".tmp"
        )
        os.close(descripteur)
        temporaire = Path(nom_temporaire)
        with zipfile.ZipFile(temporaire, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(NOM_MANIFESTE, json.dumps(manifeste, ensure_ascii=False))
            for nom, chemin in _fichiers().items():
                if chemin.is_file():
                    archive.write(chemin, nom)
            dossier = candidatures.DOSSIER_ARCHIVES
            if dossier.is_dir():
                for pdf in sorted(dossier.glob("*.pdf")):
                    archive.write(pdf, f"archives/{pdf.name}")
        temporaire.replace(destination)
    except OSError as erreur:
        if temporaire is not None:
            temporaire.unlink(missing_ok=True)
        raise ErreurSauvegarde(
            "Impossible d'écrire la sauvegarde à cet emplacement."
        ) from erreur


def _verifier_manifeste(archive: zipfile.ZipFile) -> None:
    """Manifeste présent, de Tamponné, et d'un format que cette version lit."""
    pas_une_sauvegarde = ErreurSauvegarde(
        "Ce fichier n'est pas une sauvegarde de Tamponné."
    )
    try:
        manifeste = json.loads(archive.read(NOM_MANIFESTE))
    except KeyError, ValueError:
        raise pas_une_sauvegarde from None
    if not isinstance(manifeste, dict) or manifeste.get("application") != APPLICATION:
        raise pas_une_sauvegarde
    format_ = manifeste.get("format")
    if not isinstance(format_, int):
        raise pas_une_sauvegarde
    if format_ > FORMAT:
        raise ErreurSauvegarde(
            "Cette sauvegarde vient d'une version plus récente de Tamponné\u00a0: "
            "mettez d'abord l'application à jour."
        )


def _verifier(archive: zipfile.ZipFile) -> None:
    """Refuse tout ce qui n'est pas une sauvegarde de Tamponné intacte.

    Raises:
        ErreurSauvegarde: Manifeste absent ou inconnu, format plus récent,
            fichier inattendu (dont chemin absolu ou `..`), taille excessive
            ou JSON illisible.
    """
    _verifier_manifeste(archive)

    autorises = set(_fichiers()) | {NOM_MANIFESTE}
    infos = [info for info in archive.infolist() if not info.is_dir()]
    for info in infos:
        if info.filename not in autorises and not _ARCHIVE_PDF.fullmatch(info.filename):
            raise ErreurSauvegarde("Ce fichier n'est pas une sauvegarde de Tamponné.")
    if sum(info.file_size for info in infos) > TAILLE_MAX:
        raise ErreurSauvegarde("Cette sauvegarde est trop volumineuse.")
    for nom in set(_fichiers()) & {info.filename for info in infos}:
        try:
            contenu = json.loads(archive.read(nom))
        except ValueError:
            raise ErreurSauvegarde("Cette sauvegarde est endommagée.") from None
        if not isinstance(contenu, dict | list):
            raise ErreurSauvegarde("Cette sauvegarde est endommagée.")


def _remplacer_archives(archive: zipfile.ZipFile) -> None:
    """Remplace le dossier des PDF archivés par celui de la sauvegarde :
    nouveau dossier préparé à côté, puis échange par renommage."""
    dossier = candidatures.DOSSIER_ARCHIVES
    dossier.parent.mkdir(parents=True, exist_ok=True)
    nouveau = Path(tempfile.mkdtemp(dir=dossier.parent, prefix="archives-import-"))
    for info in archive.infolist():
        if _ARCHIVE_PDF.fullmatch(info.filename):
            # Nom de fichier seul : validé par `_ARCHIVE_PDF`, jamais de sous-dossier.
            (nouveau / Path(info.filename).name).write_bytes(archive.read(info))
    ancien = dossier.with_name(dossier.name + "-ancien")
    if dossier.exists():
        dossier.replace(ancien)
    nouveau.replace(dossier)
    shutil.rmtree(ancien, ignore_errors=True)


def importer_donnees(source: Path) -> None:
    """Remplace toutes les données par celles de la sauvegarde `source`.

    Les données actuelles sont d'abord copiées dans `chemin_copie_securite()`.
    Un fichier absent de la sauvegarde est supprimé (il n'existait pas dans
    l'installation exportée).

    Raises:
        ErreurSauvegarde: Fichier illisible ou refusé par la vérification,
            copie de sécurité ou écriture impossible.
    """
    try:
        with zipfile.ZipFile(source) as archive:
            _verifier(archive)
            exporter_donnees(chemin_copie_securite())
            try:
                for nom, chemin in _fichiers().items():
                    if nom in archive.namelist():
                        chemin.parent.mkdir(parents=True, exist_ok=True)
                        temporaire = chemin.with_name(chemin.name + ".import")
                        temporaire.write_bytes(archive.read(nom))
                        temporaire.replace(chemin)
                    else:
                        chemin.unlink(missing_ok=True)
                _remplacer_archives(archive)
            except OSError as erreur:
                raise ErreurSauvegarde(
                    "Import interrompu\u00a0: vos données d'avant l'import sont "
                    f"dans {NOM_COPIE_SECURITE} (dossier data)."
                ) from erreur
    except (zipfile.BadZipFile, OSError) as erreur:
        raise ErreurSauvegarde(
            "Ce fichier n'est pas une sauvegarde de Tamponné."
        ) from erreur
