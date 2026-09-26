"""Tests du module source passerellesmef (extraction, pas de réseau)."""

from src.sources.passerellesmef.extraction import (
    SOURCE_LABEL,
    extraire_detail_offre,
    extraire_offres,
    extraire_totaux,
)

_TITRE_PAGE = "MINISTERE DE L'ECONOMIE ET DES FINANCES - Résultat de votre recherche (681 offres, page 1) / Tout afficher"

_CARTE_MINIMALE = """
<div class="ts-offer-card Layer">
    <h3 class="ts-offer-card__title">
        <a class="ts-offer-card__title-link" href="/offre-de-emploi/emploi-test_29987.aspx">
            Administrateur systèmes H/F
        </a>
    </h3>
    <span class="ts-offer-card__favorite-link lienfavori" data-reference="2026-29987"></span>
    <div class="ts-offer-card-content offerContent">
        <ul class="ts-offer-card-content__list">
            <li>Réf. : 2026-29987</li><li>02/09/2026</li><li class="noBorder">Direction générale du Trésor (DGT)</li><li class="noBorder">Paris (75)</li>
        </ul>
    </div>
</div>
"""


def test_extraire_totaux() -> None:
    assert extraire_totaux(_TITRE_PAGE) == (681, 1)


def test_extraire_totaux_titre_absent() -> None:
    assert extraire_totaux("") == (0, 1)


def test_extraire_offres_carte_minimale() -> None:
    offres = extraire_offres(_CARTE_MINIMALE)
    assert len(offres) == 1
    offre = offres[0]
    assert offre["titre"] == "Administrateur systèmes H/F"
    assert (
        offre["url"]
        == "https://www.passerelles.economie.gouv.fr/offre-de-emploi/emploi-test_29987.aspx"
    )
    assert offre["reference"] == "2026-29987"
    assert offre["employeur"] == "Direction générale du Trésor (DGT)"
    assert offre["localisation"] == "Paris (75)"
    assert offre["versant"] == "Fonction publique de l'État"
    assert offre["date"] == "02/09/2026"
    assert offre["source"] == SOURCE_LABEL


def test_extraire_offres_sans_lien_ignoree() -> None:
    html = '<div class="ts-offer-card"><h3 class="ts-offer-card__title"></h3></div>'
    assert extraire_offres(html) == []


def test_extraire_offres_url_domaine_invalide_ignoree() -> None:
    html = """
    <div class="ts-offer-card">
        <h3 class="ts-offer-card__title">
            <a class="ts-offer-card__title-link" href="https://evil.example.com/x">Titre</a>
        </h3>
    </div>
    """
    assert extraire_offres(html) == []


def test_extraire_offres_html_vide() -> None:
    assert extraire_offres("") == []


_FICHE_DETAIL = """
<div class="ts-offer-page__content-details" id="contenu-ficheoffre">
    <h2>Informations générales</h2>
    <div id="entityBlock">
        <div class="ts-offer-page__reference">
            <h3>Référence</h3>
            2026-29987
        </div>
        <div class="ts-offer-page__begin-date">
            <h3>Date de début de publication</h3>
            02/09/2026
        </div>
    </div>
    <h3>Date limite d'envoi des candidatures</h3><p>30/11/2026</p>
    <h2 class="JobDescription">Description du poste</h2>
    <h3>Domaine et métier</h3><p>Numérique - Administrateur systèmes</p>
    <h3>Niveau d'expérience min. requis</h3><p>Confirmé</p>
    <h3>Niveau d'études min. souhaité</h3><p>Niveau 6 Licence</p>
    <h3>Descriptif de l'employeur</h3><div class="RichText_viewer_fo"><p>Direction du Trésor.</p></div>
    <h3>Description du profil recherché</h3><div class="RichText_viewer_fo"><p>Profil rigoureux.</p></div>
    <h3>Personne ou service à contacter pour obtenir plus d'informations sur l'offre</h3><p>recrutement@dgtresor.gouv.fr</p>
</div>
<div class="hors-contenu">
    <h3>J'ai déjà un espace candidat</h3><p>Connexion à l'espace candidat.</p>
</div>
"""


def test_extraire_detail_offre_champs_dedies() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert detail["secteur"] == "Numérique - Administrateur systèmes"
    assert detail["experience_requise"] == "Confirmé"
    assert detail["formation_requise"] == "Niveau 6 Licence"
    assert detail["date_publication"] == "02/09/2026"
    assert detail["date_limite"] == "30/11/2026"
    assert detail["lien_postuler"] == ""


def test_extraire_detail_offre_description_combine_les_sections_narratives() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert "Direction du Trésor." in detail["description"]
    assert "Profil rigoureux." in detail["description"]


def test_extraire_detail_offre_ignore_le_bloc_hors_contenu() -> None:
    # Régression : le panneau "espace candidat" (hors zone détail) ne
    # doit pas polluer sections_complementaires.
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert "J'ai déjà un espace candidat" not in detail["sections_complementaires"]


def test_extraire_detail_offre_sections_complementaires_sans_doublon() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert "Domaine et métier" not in detail["sections_complementaires"]
    assert "Niveau d'expérience min. requis" not in detail["sections_complementaires"]
    assert (
        "Personne ou service à contacter pour obtenir plus d'informations sur l'offre"
        in detail["sections_complementaires"]
    )


def test_extraire_detail_offre_sans_champs() -> None:
    detail = extraire_detail_offre("<html></html>")
    assert detail["secteur"] == ""
    assert detail["sections_complementaires"] == {}
    assert detail["page_html"] == "<html></html>"
