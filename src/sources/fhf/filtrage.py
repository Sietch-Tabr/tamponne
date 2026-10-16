"""Filtrage côté client des offres FHF : le site ne donne le département que
dans l'adresse de l'établissement, sur la fiche de l'offre."""

from src.filtres import numero_departement_texte
from src.types import DetailOffre, FicheFiltrage


def extraire_fiche(detail: DetailOffre) -> FicheFiltrage | None:
    """Ce que la fiche apprend pour filtrer, `None` si elle est illisible.

    Le site n'indique ni catégorie, ni domaine, ni direction : seul le
    département (code postal de l'établissement) est renseigné.
    """
    if not detail["page_html"]:
        return None
    adresse = detail["sections_complementaires"].get("Etablissement", "")
    return {
        "numero": numero_departement_texte(adresse) or "",
        "categorie": "",
        "secteur": "",
        "direction": "",
        "experience": "",
        "management": False,
        "teletravail": False,
    }
