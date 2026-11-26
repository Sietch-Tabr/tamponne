"""Mise à jour de l'application via les publications (Releases) GitHub.

Uniquement les publications explicitement faites sur le dépôt — jamais un
`git pull`/`fetch` sur une branche — pour garantir que seul ce qui a été
publié est déployé. La liste vient du flux Atom des publications, sur
`github.com` : les proxys d'entreprise bloquent souvent `api.github.com`.

Ne dépend d'aucune bibliothèque d'UI : ce module est appelé aussi bien
depuis le vérificateur en arrière-plan (`src.gui.travailleurs`) que depuis
la ligne de commande par `src.lanceur` (voir `if __name__ ==
"__main__"` en bas de fichier) avant même que l'application Qt démarre.
"""

import json
import re
import shutil
import sys
import tempfile
import tomllib
lazy import http.client
lazy import urllib.error
lazy import urllib.request
lazy import xml.etree.ElementTree as ElementTree
lazy import zipfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import cast

from src.types import EchecMaj, InfoMaj
from src.utils import ecriture_atomique

URL_FLUX_RELEASES = "https://github.com/Sietch-Tabr/tamponne/releases.atom"
PREFIXE_ARCHIVES = "https://github.com/Sietch-Tabr/tamponne/archive/refs/tags/"
"""Seules les archives des étiquettes du dépôt sont téléchargées."""
HOTE_ARCHIVES = "https://codeload.github.com/Sietch-Tabr/tamponne/"
"""Adresse que doit avoir le téléchargement après la redirection : GitHub
renvoie l'archive depuis `codeload.github.com`, pas depuis `github.com`."""
_USER_AGENT = "tamponne (+https://github.com/Sietch-Tabr/tamponne)"
_ESPACE_NOMS_ATOM = "{http://www.w3.org/2005/Atom}"
_ETIQUETTE_STABLE = re.compile(r"v?\d+(\.\d+)*")
"""Une étiquette de version finale : `v1.7.10`, pas `v1.8.0-rc1`."""
TAILLE_MAX_ARCHIVE = 100 * 1024 * 1024
"""Octets au-delà desquels le téléchargement est abandonné (une publication
pèse quelques Mo)."""
_CLES_INFO_MAJ = ("version", "notes", "url_zip", "url_publication")
# Recalculée ici, pas lue dans `src.chemins` : l'ancien lanceur, resté en mémoire
# pendant une mise à jour, ne doit dépendre d'aucun module qui pourrait changer.
CHEMIN_RACINE = Path(__file__).parent.parent
CHEMIN_PYPROJECT = CHEMIN_RACINE / "pyproject.toml"
CHEMIN_MARQUEUR = CHEMIN_RACINE / "data" / "maj_disponible.json"
CHEMIN_ECHEC = CHEMIN_RACINE / "data" / "maj_echouee.json"
"""Dernière mise à jour annulée : pas de nouvel essai automatique."""
NOM_PRECEDENTE = ".maj-precedente"
"""Copie de la version remplacée, à la racine (hors de l'export de `data/`),
supprimée une fois la nouvelle version démarrée."""
EXCLUS_SAUVEGARDE = frozenset({".git", ".venv", "data", NOM_PRECEDENTE})
_TIMEOUT = 15
_TIMEOUT_TELECHARGEMENT = 60
"""Délai maximal sans données reçues pendant le téléchargement de l'archive."""


def version_locale() -> str:
    """Lit la version courante depuis `pyproject.toml`."""
    with CHEMIN_PYPROJECT.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _tuple_version(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", version.strip().lstrip("vV")))


def version_plus_recente(distante: str, locale: str) -> bool:
    """Compare deux versions par tuple d'entiers (`"1.2.0"` -> `(1, 2, 0)`),
    tolère un préfixe `v` (format des tags du dépôt, ex. `v1.2.0`)."""
    return _tuple_version(distante) > _tuple_version(locale)


class VerificationImpossible(RuntimeError):
    """GitHub n'a pas pu être interrogé.

    `str(erreur)` est le détail technique (journal, bloc « Détail ») ;
    `explication` dit en une ou deux phrases simples ce qui s'est passé et
    quoi faire. Vide, l'interface retombe sur un message générique.
    """

    def __init__(self, detail: str, explication: str = "") -> None:
        super().__init__(detail)
        self.explication = explication


MESSAGE_INJOIGNABLE = (
    "GitHub n'a pas répondu. Vérifiez votre connexion internet ou le proxy "
    "de votre réseau, puis réessayez."
)


def _erreur_http(erreur: urllib.error.HTTPError) -> VerificationImpossible:
    """Traduit une réponse d'erreur de GitHub (ou du proxy) : accès refusé,
    authentification du proxy, panne de GitHub ou autre refus."""
    code = erreur.code
    detail = f"HTTP {code} {erreur.reason}".strip()
    if code == 407:
        return VerificationImpossible(
            detail,
            "Le proxy de votre réseau demande une authentification que "
            "Tamponné ne peut pas fournir. Contactez votre service "
            "informatique.",
        )
    if code in (403, 429):
        return VerificationImpossible(
            detail,
            "L'accès à GitHub est refusé\u00a0: le proxy de votre réseau bloque "
            "probablement github.com ou codeload.github.com. Demandez à votre "
            "service informatique de les autoriser.",
        )
    if code >= 500:
        return VerificationImpossible(
            detail,
            "GitHub rencontre un problème de son côté. Réessayez plus tard.",
        )
    return VerificationImpossible(
        detail,
        "GitHub a répondu par une erreur inattendue. Réessayez plus tard.",
    )


class _HtmlVersMarkdown(HTMLParser):
    """Réduit le HTML des notes de publication au Markdown que l'avis affiche :
    titres, puces, code en ligne, gras ; le reste du balisage est ignoré."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._morceaux: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("h1", "h2", "h3", "h4"):
            self._morceaux.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self._morceaux.append("\n- ")
        elif tag in ("p", "ul", "ol"):
            self._morceaux.append("\n\n")
        elif tag == "code":
            self._morceaux.append("`")
        elif tag in ("strong", "b"):
            self._morceaux.append("**")

    def handle_endtag(self, tag: str) -> None:
        if tag == "code":
            self._morceaux.append("`")
        elif tag in ("strong", "b"):
            self._morceaux.append("**")

    def handle_data(self, data: str) -> None:
        self._morceaux.append(re.sub(r"\s+", " ", data))

    def markdown(self) -> str:
        texte = "".join(self._morceaux)
        texte = "\n".join(ligne.strip() for ligne in texte.split("\n"))
        return re.sub(r"\n{3,}", "\n\n", texte).strip()


def _html_vers_markdown(html: str) -> str:
    convertisseur = _HtmlVersMarkdown()
    convertisseur.feed(html)
    convertisseur.close()
    return convertisseur.markdown()


def _publications_du_flux(flux: bytes) -> list[tuple[str, str, str]]:
    """Lit le flux Atom : liste de (étiquette, notes en Markdown, page).

    Raises:
        ValueError: XML invalide.
    """
    try:
        racine = ElementTree.fromstring(flux)
    except ElementTree.ParseError as erreur:
        raise ValueError(str(erreur)) from erreur
    if racine.tag != f"{_ESPACE_NOMS_ATOM}feed":
        raise ValueError("flux Atom attendu")
    publications = []
    for entree in racine.findall(f"{_ESPACE_NOMS_ATOM}entry"):
        etiquette = (entree.findtext(f"{_ESPACE_NOMS_ATOM}title") or "").strip()
        lien = entree.find(f"{_ESPACE_NOMS_ATOM}link")
        page = lien.get("href", "") if lien is not None else ""
        notes = entree.findtext(f"{_ESPACE_NOMS_ATOM}content") or ""
        publications.append((etiquette, _html_vers_markdown(notes), page))
    return publications


def verifier_derniere_publication() -> InfoMaj | None:
    """Interroge le flux des publications GitHub — `None` si aucune n'est plus
    récente que la version installée.

    Les notes réunissent toutes les publications postérieures à la version
    installée, de la plus récente à la plus ancienne, chacune sous son numéro.
    Les étiquettes qui ne sont pas une version finale (`v1.8.0-rc1`) sont
    ignorées.

    Raises:
        VerificationImpossible: GitHub injoignable ou réponse illisible : on
            ne sait pas s'il existe une version plus récente.
    """
    try:
        requete = urllib.request.Request(
            URL_FLUX_RELEASES,
            headers={
                "Accept": "application/atom+xml",
                "User-Agent": _USER_AGENT,
            },
        )
        with urllib.request.urlopen(requete, timeout=_TIMEOUT) as reponse:
            publications = _publications_du_flux(reponse.read())
    except urllib.error.HTTPError as erreur:
        raise _erreur_http(erreur) from erreur
    except (ValueError, http.client.HTTPException) as erreur:
        # XML invalide, page du proxy à la place du flux ou réponse coupée.
        raise VerificationImpossible(
            str(erreur) or type(erreur).__name__,
            "La réponse de GitHub est illisible, sans doute altérée par le "
            "proxy de votre réseau. Réessayez plus tard.",
        ) from erreur
    except OSError as erreur:
        raise VerificationImpossible(str(erreur), MESSAGE_INJOIGNABLE) from erreur

    installee = version_locale()
    nouvelles = [
        publication
        for publication in publications
        if _ETIQUETTE_STABLE.fullmatch(publication[0])
        and version_plus_recente(publication[0], installee)
    ]
    if not nouvelles:
        return None
    nouvelles.sort(key=lambda p: _tuple_version(p[0]), reverse=True)
    etiquette, _, page = nouvelles[0]
    return {
        "version": etiquette.lstrip("vV"),
        "notes": _notes_cumulees(
            [(p[0].lstrip("vV"), p[1].strip()) for p in nouvelles]
        ),
        "url_zip": f"{PREFIXE_ARCHIVES}{etiquette}.zip",
        "url_publication": page,
    }


def _notes_cumulees(notes: list[tuple[str, str]]) -> str:
    """Notes de plusieurs versions : celle de la dernière seule, ou un titre
    Markdown par version."""
    if len(notes) == 1:
        return notes[0][1]
    return "\n\n".join(
        f"## Version {version}\n\n{corps or 'Pas de notes de version.'}"
        for version, corps in notes
    )


def lire_maj_disponible() -> InfoMaj | None:
    """Lit le marqueur de mise à jour en attente, `None` si absent/corrompu."""
    if not CHEMIN_MARQUEUR.exists():
        return None
    try:
        donnees = json.loads(CHEMIN_MARQUEUR.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        return None
    if not isinstance(donnees, dict) or not all(
        isinstance(donnees.get(cle, ""), str) for cle in _CLES_INFO_MAJ
    ):
        return None
    # Une clé absente vaut « vide » : `appliquer_maj` refuse alors l'archive.
    return cast(InfoMaj, {cle: donnees.get(cle, "") for cle in _CLES_INFO_MAJ})


def ecrire_maj_disponible(info: InfoMaj) -> None:
    """Pose le marqueur — déclenche l'application automatique au prochain
    lancement (`src.lanceur`), indépendamment d'un clic utilisateur."""
    ecriture_atomique(CHEMIN_MARQUEUR, dict(info))


def effacer_maj_disponible() -> None:
    CHEMIN_MARQUEUR.unlink(missing_ok=True)


def lire_echec() -> EchecMaj | None:
    """Dernière mise à jour annulée, `None` si aucune (ou fichier illisible)."""
    if not CHEMIN_ECHEC.exists():
        return None
    try:
        return json.loads(CHEMIN_ECHEC.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        return None


def enregistrer_echec(version: str, motif: str) -> None:
    """Mémorise l'annulation de `version` : la vérification ne la reprogramme
    plus d'elle-même, seul « Installer et redémarrer » la retente."""
    echec: EchecMaj = {
        "version": version,
        "motif": motif,
        "date": date.today().isoformat(),
    }
    ecriture_atomique(CHEMIN_ECHEC, dict(echec))


def maj_en_echec(version: str) -> bool:
    """Vrai si `version` est la dernière mise à jour annulée."""
    echec = lire_echec()
    return echec is not None and echec["version"] == version


def dossier_precedente() -> Path:
    """Copie de la version remplacée par la dernière mise à jour."""
    return CHEMIN_RACINE / NOM_PRECEDENTE


def sauvegarder_version_actuelle() -> None:
    """Copie l'installation (hors `EXCLUS_SAUVEGARDE`) dans
    `dossier_precedente()`, pour revenir en arrière si la mise à jour ne
    démarre pas. Écrite à côté puis renommée : une copie interrompue n'est
    jamais prise pour une sauvegarde complète."""
    dossier = dossier_precedente()
    temporaire = dossier.with_name(dossier.name + ".tmp")
    shutil.rmtree(temporaire, ignore_errors=True)
    temporaire.mkdir()
    for element in CHEMIN_RACINE.iterdir():
        if element.name in EXCLUS_SAUVEGARDE or element == temporaire:
            continue
        if element.is_dir():
            shutil.copytree(
                element,
                temporaire / element.name,
                symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        else:
            shutil.copy2(element, temporaire / element.name)
    shutil.rmtree(dossier, ignore_errors=True)
    temporaire.replace(dossier)


def restaurer_version_precedente() -> bool:
    """Réinstalle la version sauvegardée avant la dernière mise à jour
    (fichiers ajoutés depuis sous `src/` retirés), puis efface la copie.

    Returns:
        Faux s'il n'y avait aucune sauvegarde.
    """
    dossier = dossier_precedente()
    if not dossier.is_dir():
        return False
    installer_archive(dossier, CHEMIN_RACINE)
    shutil.rmtree(dossier, ignore_errors=True)
    return True


def valider_maj() -> None:
    """Rend la dernière mise à jour définitive, une fois l'interface
    chargée : plus de retour arrière possible, échec antérieur oublié."""
    dossier = dossier_precedente()
    if dossier.exists():
        shutil.rmtree(dossier, ignore_errors=True)
        CHEMIN_ECHEC.unlink(missing_ok=True)


def _telecharger(url: str, destination: Path) -> None:
    """Enregistre `url` dans `destination`, sans jamais attendre plus de
    `_TIMEOUT_TELECHARGEMENT` secondes une réponse ou des données.

    Raises:
        RuntimeError: Redirigé hors de `HOTE_ARCHIVES`, ou archive plus grosse
            que `TAILLE_MAX_ARCHIVE`.
    """
    with (
        urllib.request.urlopen(url, timeout=_TIMEOUT_TELECHARGEMENT) as reponse,
        destination.open("wb") as fichier,
    ):
        if not reponse.geturl().startswith(HOTE_ARCHIVES):
            raise RuntimeError(
                "Archive de mise à jour redirigée hors de GitHub, refusée."
            )
        recu = 0
        while morceau := reponse.read(1024 * 1024):
            recu += len(morceau)
            if recu > TAILLE_MAX_ARCHIVE:
                raise RuntimeError("Archive de mise à jour trop volumineuse.")
            fichier.write(morceau)


def appliquer_maj(info: InfoMaj) -> None:
    """Télécharge et applique la publication `info`.

    Installe les fichiers de l'archive dans la racine du projet (voir
    `installer_archive`) : l'archive GitHub ne contient que les fichiers
    suivis par git et publiés, donc `data/`, `.git/` et les fichiers non
    versionnés hors de `src/` ne sont jamais touchés. La version remplacée
    est d'abord copiée (`sauvegarder_version_actuelle`) pour le retour
    arrière du lanceur.

    Raises:
        RuntimeError: Archive hors du dépôt, téléchargement, extraction,
            sauvegarde ou installation impossible. Avant l'installation rien
            n'est modifié ; pendant, la version sauvegardée permet le retour
            arrière du lanceur.
    """
    if not info["url_zip"]:
        raise RuntimeError("URL de l'archive de mise à jour manquante.")
    if not info["url_zip"].startswith(PREFIXE_ARCHIVES):
        raise RuntimeError(
            "Archive de mise à jour hors du dépôt Tamponné refusée\u00a0: "
            f"{info['url_zip']}"
        )

    with tempfile.TemporaryDirectory(prefix="tamponne-maj-") as dossier_tmp:
        chemin_zip = Path(dossier_tmp) / "maj.zip"
        try:
            _telecharger(info["url_zip"], chemin_zip)
            with zipfile.ZipFile(chemin_zip) as archive:
                archive.extractall(dossier_tmp)
                # extractall() n'applique pas les bits Unix (rwx) codés dans
                # l'archive : sans ça, Tamponne.command perd son +x à chaque maj.
                racine_tmp = Path(dossier_tmp).resolve()
                for membre in archive.infolist():
                    permissions = (membre.external_attr >> 16) & 0o777
                    cible = (racine_tmp / membre.filename).resolve()
                    # Un nom d'archive piégé (`../`) ne doit pas viser hors du dossier.
                    if permissions and cible.is_relative_to(racine_tmp):
                        cible.chmod(permissions)
        except (OSError, zipfile.BadZipFile) as e:
            raise RuntimeError(
                f"Impossible de télécharger ou d'extraire la mise à jour\u00a0: {e}"
            ) from e

        # Dossier racine unique de l'archive (ex. « Sietch-Tabr-tamponne-abc1234/ »)
        # déduit plutôt que deviné : la convention de nommage de GitHub peut changer.
        racines = [p for p in Path(dossier_tmp).iterdir() if p.is_dir()]
        if len(racines) != 1:
            raise RuntimeError(
                "Structure d'archive inattendue (racine unique attendue)."
            )
        dossier_extrait = racines[0]

        try:
            sauvegarder_version_actuelle()
        except OSError as e:
            raise RuntimeError(
                f"Impossible de sauvegarder la version actuelle\u00a0: {e}"
            ) from e
        try:
            installer_archive(dossier_extrait, CHEMIN_RACINE)
        except OSError as e:
            raise RuntimeError(
                f"Impossible d'installer la mise \u00e0 jour\u00a0: {e}"
            ) from e


DOSSIERS_PURGES = ("src",)
"""Dossiers où un fichier absent de la nouvelle version est supprimé."""


def installer_archive(dossier_extrait: Path, racine: Path) -> None:
    """Installe le contenu extrait d'une publication dans `racine`.

    Chaque fichier est écrit dans un temporaire puis renommé : un script en
    cours d'exécution (`Tamponne.command` lu par bash) garde son ancien
    contenu au lieu d'être réécrit sous ses pieds. Ensuite, sous `src/`
    seulement, les fichiers absents de la publication sont supprimés avec
    leurs `__pycache__` ; rien n'est purgé dans un clone git (`.git/`).

    Args:
        dossier_extrait: Racine de l'archive extraite.
        racine: Dossier d'installation.
    """
    fichiers_publies: set[Path] = set()
    for fichier_source in dossier_extrait.rglob("*"):
        if fichier_source.is_dir():
            continue
        chemin_relatif = fichier_source.relative_to(dossier_extrait)
        fichiers_publies.add(chemin_relatif)
        fichier_dest = racine / chemin_relatif
        fichier_dest.parent.mkdir(parents=True, exist_ok=True)
        temporaire = fichier_dest.with_name(fichier_dest.name + ".maj")
        shutil.copy2(fichier_source, temporaire)
        temporaire.replace(fichier_dest)
    if not (racine / ".git").exists():
        _purger(racine, fichiers_publies)


def _purger(racine: Path, fichiers_publies: set[Path]) -> None:
    """Supprime sous `DOSSIERS_PURGES` ce que la publication ne contient plus."""
    for nom in DOSSIERS_PURGES:
        dossier = racine / nom
        # Une publication sans ce dossier est anormale : ne rien y supprimer.
        if not dossier.is_dir() or not any(
            p.parts[:1] == (nom,) for p in fichiers_publies
        ):
            continue
        for cache in sorted(dossier.rglob("__pycache__"), reverse=True):
            shutil.rmtree(cache, ignore_errors=True)
        for fichier in sorted(dossier.rglob("*"), reverse=True):
            relatif = fichier.relative_to(racine)
            if fichier.is_file() and relatif not in fichiers_publies:
                fichier.unlink()
            elif fichier.is_dir() and not any(fichier.iterdir()):
                fichier.rmdir()


if __name__ == "__main__":
    if "--appliquer" not in sys.argv:
        print("Usage\u00a0: python -m src.maj --appliquer", file=sys.stderr)
        sys.exit(1)

    info_en_attente = lire_maj_disponible()
    if info_en_attente is None:
        sys.exit(0)  # rien à appliquer, pas une erreur

    try:
        appliquer_maj(info_en_attente)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    effacer_maj_disponible()
