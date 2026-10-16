"""Interface commune à toutes les sources d'offres."""

import re
lazy import urllib.error
lazy import urllib.request
from collections.abc import Callable
from typing import Protocol
from urllib.parse import urlparse

lazy from bs4 import Tag

from src.types import FicheFiltrage, FiltresRecherche, Offre

# Sites sans WAF : User-Agent identifiant l'application et son dépôt.
USER_AGENT_IDENTIFIE = "tamponne (+https://codeberg.org/Kwaite/tamponne)"
_TIMEOUT = 30
_RE_TITRE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_RE_ESPACES = re.compile(r"\s+")
_RE_LIGNES_VIDES = re.compile(r"\n{3,}")
_SAUT = "\x00"
"""Marque provisoire d'un saut de ligne, que la réduction des espaces épargne."""


def adresse_cloudflare(code: str) -> str:
    """Adresse e-mail masquée par Cloudflare (`data-cfemail`) : octets en
    hexadécimal, le premier sert de clé (XOR) aux suivants ; vide si le
    code est illisible."""
    try:
        octets = bytes.fromhex(code)
    except ValueError:
        return ""
    if len(octets) < 2:
        return ""
    return bytes(octet ^ octets[0] for octet in octets[1:]).decode(
        "utf-8", errors="replace"
    )


def texte_lisible(bloc: Tag) -> str:
    """Texte d'un bloc HTML d'une fiche, mis en lignes comme sur le site :
    `<br>` et fin d'élément de liste passent à la ligne, un paragraphe est
    suivi d'une ligne vide, un élément de liste commence par « • ». Les
    sauts du code HTML ne comptent pas, et les adresses e-mail masquées par
    Cloudflare sont rendues lisibles, comme dans un navigateur. Modifie
    `bloc`."""
    for masque in bloc.find_all(True, attrs={"data-cfemail": True}):
        adresse = adresse_cloudflare(str(masque.get("data-cfemail", "")))
        if adresse:
            masque.replace_with(adresse)
    for saut in bloc.find_all("br"):
        saut.replace_with(_SAUT)
    for element in bloc.find_all("li"):
        element.insert(0, "• ")
        element.append(_SAUT)
    for paragraphe in bloc.find_all("p"):
        paragraphe.append(_SAUT * 2)
    texte = _RE_ESPACES.sub(" ", bloc.get_text())
    lignes = [ligne.strip() for ligne in texte.split(_SAUT)]
    return _RE_LIGNES_VIDES.sub("\n\n", "\n".join(lignes).strip())


def sur_domaine(url: str, domaine: str) -> bool:
    """Vrai si l'hôte de `url` est `domaine` ou l'un de ses sous-domaines."""
    hote = urlparse(url).hostname or ""
    return hote == domaine or hote.endswith(f".{domaine}")


def valider_url(url: str, url_base: str, domaine: str) -> str:
    """URL d'un lien extrait d'une page : un chemin relatif est rattaché à
    `url_base`, une URL http(s) n'est gardée que sur `domaine` ; chaîne
    vide sinon (lien externe, `javascript:`, vide)."""
    if url.startswith("/"):
        return f"{url_base}{url}"
    if url.startswith(("https://", "http://")) and sur_domaine(url, domaine):
        return url
    return ""


class PageIntrouvable(RuntimeError):
    """Le site répond que la page n'existe pas (HTTP 404 ou 410)."""


def consulter_page(url: str) -> tuple[str, str]:
    """Charge `url` en suivant les redirections.

    Returns:
        URL finale et titre (`<title>`) de la page.

    Raises:
        PageIntrouvable: HTTP 404 ou 410.
        RuntimeError: Autre code d'erreur HTTP, ou échec réseau.
    """
    requete = urllib.request.Request(url, headers={"User-Agent": USER_AGENT_IDENTIFIE})
    try:
        with urllib.request.urlopen(requete, timeout=_TIMEOUT) as reponse:
            url_finale = reponse.geturl()
            html = reponse.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as erreur:
        if erreur.code in (404, 410):
            raise PageIntrouvable(f"Page introuvable (HTTP {erreur.code})") from erreur
        raise RuntimeError(
            f"Erreur HTTP {erreur.code} lors du chargement de {url}"
        ) from erreur
    except OSError as erreur:
        raise RuntimeError(
            f"Erreur réseau lors du chargement de {url}\u00a0: {erreur}"
        ) from erreur
    titre = _RE_TITRE.search(html)
    return url_finale, titre.group(1).strip() if titre else ""


def deduplique_offres(offres: list[Offre]) -> list[Offre]:
    """Retire les doublons par référence (insensible à la casse), garde
    la première occurrence — appeler avec choisirleservicepublic en
    premier pour conserver sa version (détail enrichi, PDF archivé)
    quand une offre territoriale déjà syndiquée apparaît aussi côté
    choisirleservicepublic (même référence sur les deux sites)."""
    vues: set[str] = set()
    resultat: list[Offre] = []
    for offre in offres:
        ref = offre["reference"].upper()
        if ref and ref in vues:
            continue
        vues.add(ref)
        resultat.append(offre)
    return resultat


class CacheFiches(Protocol):
    """Mémoire des fiches déjà lues, par URL d'offre : une fiche lue pour une
    recherche n'est pas relue pour la suivante. Sûre entre threads."""

    def lire(self, url: str) -> FicheFiltrage | None:
        """Fiche mémorisée de `url`, `None` si absente ou trop ancienne."""
        ...

    def ecrire(self, url: str, fiche: FicheFiltrage) -> None:
        """Mémorise la fiche de `url`."""
        ...


class SourceOffres(Protocol):
    """Contrat qu'une source de données doit respecter pour être branchée
    sur le moteur de recherche.

    Convertit des filtres génériques (indépendants de la source) en
    offres, en gérant elle-même la pagination propre à son API/site.
    Ne filtre pas les grades supérieurs (IDIV/IP*/AFIPA) : ça reste un
    post-traitement appliqué par l'appelant, pour permettre de les
    afficher ponctuellement (bouton dédié dans la TUI).
    """

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Retourne (offres de toutes les pages chargées, nb_pages, arret_anticipe).

        Args:
            filtres: Filtres génériques du wizard/TUI.
            on_page: Callback optionnel appelé après chaque page chargée
                avec (page_courante, nb_pages_a_charger), pour permettre
                à l'appelant d'afficher une progression sans coupler
                cette méthode à une bibliothèque d'UI particulière.
            on_fiche: Callback optionnel appelé après chaque fiche lue
                pour filtrer (sources qui le font), avec (fiches lues,
                fiches à lire) ; ignoré par les autres.

        Returns:
            Tuple ``(offres, nb_pages, arret_anticipe)`` où ``nb_pages``
            est le nombre de pages annoncé par la source (peut dépasser
            le nombre de pages effectivement chargées si la source plafonne),
            et ``arret_anticipe`` indique un arrêt avant la fin (page vide
            ou boucle détectée).
        """
        ...
