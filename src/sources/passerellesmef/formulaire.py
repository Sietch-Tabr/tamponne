"""Formulaire de recherche de Passerelles/MEF : ce que le site filtre lui-même.

Le site filtre par catégorie, région, domaine (métier) et organisme de
rattachement, mais seulement par l'envoi de son formulaire (le lien d'une
page de résultats ne porte aucun critère). Les noms de champs et leurs
valeurs sont relus sur la page à chaque recherche plutôt que figés ici. Un
critère que la page ne propose plus, ou qui ne se rattache pas sans
ambiguïté à un choix du site, n'est pas demandé au site : il reste filtré
côté client.
"""

import re
from dataclasses import dataclass, field
from typing import NamedTuple

lazy from bs4 import BeautifulSoup, Tag

from src.filtres import (
    CATEGORIES,
    NUMEROS_REGIONS,
    cle_categorie,
    numeros_departements,
)
from src.sources.passerellesmef.filtrage import normaliser, ressemblent
from src.types import FiltresRecherche

_REGIONS_HORS_TABLE = {
    numero: "Provence-Cote d'Azur" for numero in ("04", "05", "06", "13", "83", "84")
}
"""Départements dont la région manque à `NUMEROS_REGIONS`."""

_ALIAS_REGIONS = {"dom": "drom", "paysdelaloire": "paysdeloire"}
"""Régions que le site écrit autrement que `NUMEROS_REGIONS`."""

_RE_EFFECTIF = re.compile(r"\s*\(\d+\)\s*$")
_RE_SIGLE = re.compile(r"\(([^()]+)\)\s*$")


class Case(NamedTuple):
    """Case à cocher du formulaire : libellé affiché (sans effectif), nom du
    champ et valeur envoyée."""

    libelle: str
    nom: str
    valeur: str


@dataclass
class Formulaire:
    """Champs du formulaire de recherche, tels que la page les propose."""

    caches: dict[str, str] = field(default_factory=dict)
    bouton: tuple[str, str] = ("", "")
    mots_cles: str = ""
    champ_categorie: str = ""
    categories: dict[str, str] = field(default_factory=dict)
    """Clé de `CATEGORIES` → valeur de la liste déroulante."""
    regions: list[Case] = field(default_factory=list)
    domaines: list[Case] = field(default_factory=list)
    """Domaines de premier niveau (cocher l'un coche ses métiers)."""
    organismes: list[Case] = field(default_factory=list)

    def exploitable(self) -> bool:
        """Vrai si la page a bien livré un formulaire de recherche."""
        return bool(self.bouton[0] and self.caches)


def _cle(texte: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normaliser(texte))


def _sans_effectif(libelle: str) -> str:
    return _RE_EFFECTIF.sub("", libelle).strip()


def analyser_formulaire(html: str) -> Formulaire:
    """Formulaire de recherche de la page `html` (vide si elle n'en a pas)."""
    soup = BeautifulSoup(html, "html.parser")
    formulaire = Formulaire()
    page = soup.find("form", id="aspnetForm")
    if not isinstance(page, Tag):
        return formulaire

    for champ in page.find_all("input"):
        nom = str(champ.get("name", ""))
        type_champ = str(champ.get("type", "text")).lower()
        if type_champ == "hidden" and nom:
            formulaire.caches[nom] = str(champ.get("value", ""))
        elif type_champ == "submit" and nom.endswith("BT_recherche"):
            formulaire.bouton = (nom, str(champ.get("value", "")))
        elif nom.endswith("OfferCriteria_Keywords"):
            formulaire.mots_cles = nom
        elif type_champ == "checkbox" and nom:
            case = Case(
                _sans_effectif(str(champ.get("aria-label", ""))),
                nom,
                str(champ.get("value", "")),
            )
            niveaux = len(str(champ.get("aria-labelledby", "")).split())
            if "GeographicalAreaCollection" in nom:
                formulaire.regions.append(case)
            elif "PrimaryProfile" in nom and niveaux == 1:
                formulaire.domaines.append(case)
            elif "Entity" in nom:
                formulaire.organismes.append(case)

    for liste in page.find_all("select"):
        options = {
            cle: str(option.get("value", ""))
            for option in liste.find_all("option")
            if (cle := cle_categorie(option.get_text())) is not None
        }
        if options:
            formulaire.champ_categorie = str(liste.get("name", ""))
            formulaire.categories = options
            break
    return formulaire


def _regions_visees(localisations: list[str]) -> set[str] | None:
    """Régions couvrant `localisations`, `None` si un département visé n'en
    a pas de connue."""
    numeros = numeros_departements(localisations)
    if not numeros:
        return None
    region_de = {
        numero: region
        for region, numeros_region in NUMEROS_REGIONS.items()
        for numero in numeros_region
    }
    region_de.update(_REGIONS_HORS_TABLE)
    if any(numero not in region_de for numero in numeros):
        return None
    return {region_de[numero] for numero in numeros}


def _cocher_regions(
    formulaire: Formulaire, localisations: list[str]
) -> list[Case] | None:
    regions = _regions_visees(localisations)
    if regions is None:
        return None
    cases = {_cle(case.libelle): case for case in formulaire.regions}
    choisies: list[Case] = []
    for region in regions:
        cle = _cle(region)
        case = cases.get(_ALIAS_REGIONS.get(cle, cle)) or cases.get(cle)
        if case is None:
            return None
        choisies.append(case)
    return choisies


def _cocher_domaines(formulaire: Formulaire, domaines: list[str]) -> list[Case] | None:
    choisies: list[Case] = []
    for domaine in domaines:
        trouvees = [c for c in formulaire.domaines if ressemblent(c.libelle, domaine)]
        if len(trouvees) != 1:
            return None
        choisies.append(trouvees[0])
    return choisies


def _sigle(libelle: str) -> str:
    correspondance = _RE_SIGLE.search(libelle)
    return _cle(correspondance.group(1)) if correspondance else ""


def _entite_correspond(case: Case, organisation: str) -> bool:
    sigle = _sigle(organisation)
    return ressemblent(case.libelle, organisation) or (
        bool(sigle) and sigle == _cle(case.libelle)
    )


def _cocher_organismes(
    formulaire: Formulaire, organisations: list[str]
) -> list[Case] | None:
    choisies: list[Case] = []
    for organisation in organisations:
        trouvees = [
            c for c in formulaire.organismes if _entite_correspond(c, organisation)
        ]
        if len(trouvees) != 1:
            return None
        choisies.append(trouvees[0])
    return choisies


def construire_recherche(
    formulaire: Formulaire,
    filtres: FiltresRecherche,
    sous_organisations: list[str],
) -> tuple[dict[str, str], frozenset[str]]:
    """Champs à envoyer au site, et critères qu'il applique exactement
    (parmi `categories`, `domaines`, `organisations` : inutile de les
    revérifier sur les fiches).

    Un critère n'est demandé au site que s'il se rattache sans ambiguïté à
    ses choix. La région se demande quand elle est connue mais ne dispense
    pas du filtre par département, que le site ne propose pas. Vide si rien
    n'est demandé au site.
    """
    champs: dict[str, str] = {}
    appliques: set[str] = set()

    categories = [c for c in filtres.get("categories", []) if c in CATEGORIES]
    if len(categories) == 1 and categories[0] in formulaire.categories:
        champs[formulaire.champ_categorie] = formulaire.categories[categories[0]]
        appliques.add("categories")

    if domaines := filtres.get("domaines"):
        if (cases := _cocher_domaines(formulaire, domaines)) is not None:
            champs.update({c.nom: c.valeur for c in cases})
            appliques.add("domaines")

    if sous_organisations:
        if (cases := _cocher_organismes(formulaire, sous_organisations)) is not None:
            champs.update({c.nom: c.valeur for c in cases})
            appliques.add("organisations")

    if localisations := filtres.get("localisations"):
        if (cases := _cocher_regions(formulaire, localisations)) is not None:
            champs.update({c.nom: c.valeur for c in cases})

    if not champs:
        return {}, frozenset()
    if (requete := filtres.get("query", "")) and formulaire.mots_cles:
        champs[formulaire.mots_cles] = requete
    return champs, frozenset(appliques)
