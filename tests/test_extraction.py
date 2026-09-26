"""Tests pour src/extraction.py — parsing HTML et validation des URLs."""

import pytest

from src.sources.choisirleservicepublic.extraction import (
    _valider_url,
    est_grade_superieur,
    extraire_detail_offre,
    extraire_offres,
    extraire_pagination,
    filtrer_grades_superieurs,
)
from src.types import Offre

# Une ligne par <p>, sans indentation, comme le HTML minifié du site : seuls
# les <br/> doivent produire des sauts de ligne, pas la mise en forme du test.
_DESCRIPTION_AVEC_BR = (
    '<div class="fr-col-lg-6 col-left rte"><h2>Vos missions en quelques mots</h2>'
    '<div><div class="fr-mb-3w"><p>Première phrase du poste.<br/>'
    "Deuxième phrase, juste après.<br/><br/>"
    "DESCRIPTION DES MISSIONS :<br/>"
    "- Premier point de mission ;<br/>"
    "- Second point de mission.</p></div></div></div>"
)

_CARTE_MINIMALE = """
<div class="fr-card__body">
  <h3><a href="/offre/reference-ABC123/">Chargé de mission numérique</a></h3>
  <a class="fr-tag">Numérique</a>
  <ul>
    <li class="fr-icon--sm fr-icon-map-pin-2-line">
      <span class="sr-only">Localisation</span> Paris (75)
    </li>
    <li class="fr-icon--sm fr-icon-file-line">
      <span class="sr-only">Versant</span> Fonction publique de l'État
    </li>
    <li class="fr-icon--sm fr-icon-user-line">
      <span class="sr-only">Employeur</span> Ministère de test
    </li>
    <li class="fr-icon--sm fr-icon-calendar-line">
      <span class="sr-only">Date</span> En ligne depuis le 01/01/2026
    </li>
  </ul>
</div>
"""


# --- _valider_url ---


def test_valider_url_relative_est_prefixee() -> None:
    assert (
        _valider_url("/offre/reference-1/")
        == "https://choisirleservicepublic.gouv.fr/offre/reference-1/"
    )


def test_valider_url_domaine_autorise_conservee() -> None:
    url = "https://choisirleservicepublic.gouv.fr/offre/reference-1/"
    assert _valider_url(url) == url


def test_valider_url_sous_domaine_autorise() -> None:
    url = "https://www.choisirleservicepublic.gouv.fr/offre/reference-1/"
    assert _valider_url(url) == url


def test_valider_url_domaine_externe_rejetee() -> None:
    assert _valider_url("https://evil.example.com/reference-1/") == ""


def test_valider_url_vide_rejetee() -> None:
    assert _valider_url("") == ""


# --- extraire_offres ---


def test_extraire_offres_carte_minimale() -> None:
    offres = extraire_offres(_CARTE_MINIMALE)
    assert len(offres) == 1
    offre = offres[0]
    assert offre["titre"] == "Chargé de mission numérique"
    assert offre["reference"] == "ABC123"
    assert offre["domaine"] == "Numérique"
    assert offre["localisation"] == "Paris (75)"
    assert offre["versant"] == "Fonction publique de l'État"
    assert offre["employeur"] == "Ministère de test"
    assert offre["date"] == "01/01/2026"
    assert offre["url"].startswith("https://choisirleservicepublic.gouv.fr")
    assert offre["source"] == ""


def test_extraire_offres_source_deduite_du_prefixe_connu() -> None:
    html = _CARTE_MINIMALE.replace("reference-ABC123", "reference-MEF_2026-30262")
    offre = extraire_offres(html)[0]
    assert offre["reference"] == "MEF_2026-30262"
    assert offre["source"] == "Ministère de l'Économie et des Finances"


def test_extraire_offres_source_prefixe_inconnu_retourne_le_prefixe_brut() -> None:
    html = _CARTE_MINIMALE.replace("reference-ABC123", "reference-XYZ_2026-1")
    offre = extraire_offres(html)[0]
    assert offre["source"] == "XYZ"


def test_extraire_offres_sans_lien_ignoree() -> None:
    html = '<div class="fr-card__body"><h3>Pas de lien ici</h3></div>'
    assert extraire_offres(html) == []


def test_extraire_offres_url_domaine_invalide_ignoree() -> None:
    html = """
    <div class="fr-card__body">
      <h3><a href="https://evil.example.com/reference-1/">Titre</a></h3>
    </div>
    """
    assert extraire_offres(html) == []


def test_extraire_offres_html_vide() -> None:
    assert extraire_offres("") == []


# --- filtrer_grades_superieurs / est_grade_superieur ---


def _offre(titre: str) -> Offre:
    return {
        "titre": titre,
        "url": "",
        "reference": titre,
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": "",
    }


def test_est_grade_superieur_idiv() -> None:
    assert est_grade_superieur("IDIV Classe normale - Chef de service")


def test_est_grade_superieur_ip() -> None:
    assert est_grade_superieur("IPA - Inspecteur principal")


def test_est_grade_superieur_afipa() -> None:
    assert est_grade_superieur("AFIPA - Attaché principal")


def test_est_grade_superieur_grade_normal_refuse() -> None:
    assert not est_grade_superieur("Technicien informatique")


def test_filtrer_grades_superieurs() -> None:
    offres = [
        _offre("IDIV - Chef de service"),
        _offre("Technicien informatique"),
        _offre("Gestionnaire administratif"),
    ]
    filtrees, nb_exclus = filtrer_grades_superieurs(offres)
    assert nb_exclus == 1
    assert [o["titre"] for o in filtrees] == [
        "Technicien informatique",
        "Gestionnaire administratif",
    ]


def test_filtrer_grades_superieurs_liste_vide() -> None:
    assert filtrer_grades_superieurs([]) == ([], 0)


# --- extraire_pagination ---


def test_extraire_pagination_present() -> None:
    assert extraire_pagination("Résultats — page 2 sur 5") == (2, 5)


def test_extraire_pagination_absent() -> None:
    assert extraire_pagination("Titre sans pagination") == (1, 1)


def test_extraire_pagination_titre_vide() -> None:
    assert extraire_pagination("") == (1, 1)


# --- extraire_detail_offre ---

_JSON_LD_COMPLET = """
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Chargé de mission numérique",
  "Description": "Missions principales : piloter le projet X.",
  "baseSalary": "Non renseigné",
  "experienceRequirements": "Confirmé",
  "educationRequirements": "Niveau 6 Licence/diplômes équivalents",
  "industry": "Numérique",
  "datePosted": "31/08/2026"
}
</script>
"""

_ABOUT_AGENCY = """
<div class="strate-two-columns about-agency">
  <h2>Qui sommes-nous&nbsp;?</h2>
  <div class="rte"><div><p>Présentation du service employeur.</p></div></div>
</div>
"""

_ACCORDEON = """
<section class="fr-accordion">
  <h3><button class="fr-accordion__btn">Informations complémentaires</button></h3>
  <div class="fr-collapse rte"><p>Contact : Jean Dupont — jean.dupont@exemple.fr</p></div>
</section>
<section class="fr-accordion">
  <h3><button class="fr-accordion__btn">Statut du poste</button></h3>
  <div class="fr-collapse">Vacant à partir du 01/09/2026</div>
</section>
"""

_BOUTONS_ET_DATE_LIMITE = """
<a href="https://talent-soft.com/candidature/123">Postuler sur le site employeur</a>
<p>Date limite de candidature : 06/09/2026</p>
"""

_PAGE_COMPLETE = _JSON_LD_COMPLET + _ABOUT_AGENCY + _ACCORDEON + _BOUTONS_ET_DATE_LIMITE


def test_extraire_detail_offre_json_ld_complet() -> None:
    detail = extraire_detail_offre(_PAGE_COMPLETE)
    assert detail["description"] == "Missions principales : piloter le projet X."
    assert detail["salaire"] == "Non renseigné"
    assert detail["experience_requise"] == "Confirmé"
    assert detail["formation_requise"] == "Niveau 6 Licence/diplômes équivalents"
    assert detail["secteur"] == "Numérique"
    assert detail["date_publication"] == "31/08/2026"
    assert detail["page_html"] == _PAGE_COMPLETE


def test_extraire_detail_offre_a_propos_employeur() -> None:
    detail = extraire_detail_offre(_PAGE_COMPLETE)
    assert detail["a_propos_employeur"] == "Présentation du service employeur."


def test_extraire_detail_offre_sections_complementaires() -> None:
    detail = extraire_detail_offre(_PAGE_COMPLETE)
    assert detail["sections_complementaires"] == {
        "Informations complémentaires": "Contact : Jean Dupont — jean.dupont@exemple.fr",
        "Statut du poste": "Vacant à partir du 01/09/2026",
    }


def test_extraire_detail_offre_description_depuis_le_dom_avec_sauts_de_ligne() -> None:
    detail = extraire_detail_offre(_JSON_LD_COMPLET + _DESCRIPTION_AVEC_BR)
    assert detail["description"] == (
        "Première phrase du poste.\n"
        "Deuxième phrase, juste après.\n"
        "\n"
        "DESCRIPTION DES MISSIONS :\n"
        "- Premier point de mission ;\n"
        "- Second point de mission."
    )


def test_extraire_detail_offre_description_json_ld_utilisee_si_dom_absent() -> None:
    # Filet de sécurité : sans bloc `col-left` dans la page, on retombe
    # sur le champ JSON-LD malgré sa mise en forme dégradée.
    detail = extraire_detail_offre(_JSON_LD_COMPLET)
    assert detail["description"] == "Missions principales : piloter le projet X."


def test_extraire_detail_offre_json_ld_absent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    detail = extraire_detail_offre(_ABOUT_AGENCY + _ACCORDEON)
    assert detail["description"] == ""
    assert detail["salaire"] == ""
    # le reste (accordéon, à propos) reste extrait même sans JSON-LD
    assert detail["a_propos_employeur"] == "Présentation du service employeur."
    assert "Statut du poste" in detail["sections_complementaires"]
    assert "JSON-LD absent" in capsys.readouterr().err


def test_extraire_detail_offre_json_ld_invalide(
    capsys: pytest.CaptureFixture[str],
) -> None:
    html = '<script type="application/ld+json">{ceci n"est pas du json}</script>'
    detail = extraire_detail_offre(html)
    assert detail["description"] == ""
    assert "JSON invalide" in capsys.readouterr().err


def test_extraire_detail_offre_description_vide_avec_data_logge_avertissement(
    capsys: pytest.CaptureFixture[str],
) -> None:
    html = """
    <script type="application/ld+json">
    {"title": "Poste", "baseSalary": "1500"}
    </script>
    """
    detail = extraire_detail_offre(html)
    assert detail["description"] == ""
    assert detail["salaire"] == "1500"
    assert "Description vide" in capsys.readouterr().err


def test_extraire_detail_offre_sans_a_propos_employeur() -> None:
    detail = extraire_detail_offre(_JSON_LD_COMPLET)
    assert detail["a_propos_employeur"] == ""


def test_extraire_detail_offre_sans_accordeon() -> None:
    detail = extraire_detail_offre(_JSON_LD_COMPLET)
    assert detail["sections_complementaires"] == {}


def test_extraire_detail_offre_html_vide() -> None:
    detail = extraire_detail_offre("")
    assert detail["description"] == ""
    assert detail["sections_complementaires"] == {}
    assert detail["page_html"] == ""
    assert detail["lien_postuler"] == ""
    assert detail["date_limite"] == ""


def test_extraire_detail_offre_lien_postuler_et_date_limite() -> None:
    detail = extraire_detail_offre(_PAGE_COMPLETE)
    assert detail["lien_postuler"] == "https://talent-soft.com/candidature/123"
    assert detail["date_limite"] == "06/09/2026"


def test_extraire_detail_offre_sans_lien_postuler_ni_date_limite() -> None:
    detail = extraire_detail_offre(_JSON_LD_COMPLET + _ABOUT_AGENCY + _ACCORDEON)
    assert detail["lien_postuler"] == ""
    assert detail["date_limite"] == ""
