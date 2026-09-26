"""Tests du module source fhf (extraction et dédoublonnage, pas de réseau)."""

from src.sources.fhf.dedoublonnage import filtrer_doublons_fhf
from src.sources.fhf.extraction import (
    SOURCE_LABEL,
    extraire_detail_offre,
    extraire_offres,
)
from src.types import Offre

_CARTE_MINIMALE = """
<article class="card card-offer">
  <div class="card-body">
    <div class="card-inner">
      <div class="field--name-field-publish-date">Publié le 02.09.2026 12:52</div>
      <h3 class="card-title">Infirmier de nuit F/H</h3>
      <div>
        <div class="field--name-field-establishment">Centre hospitalier  (Carcassonne)</div>
        <div class="field--name-field-description">Descriptif court.</div>
      </div>
    </div>
    <div class="card-footer">
      <a class="btn btn-link" href="/emploi/488995"><span>Voir l'offre</span></a>
    </div>
  </div>
</article>
"""


def test_extraire_offres_carte_minimale() -> None:
    offres = extraire_offres(_CARTE_MINIMALE)
    assert len(offres) == 1
    offre = offres[0]
    assert offre["titre"] == "Infirmier de nuit F/H"
    assert offre["url"] == "https://emploi.fhf.fr/emploi/488995"
    assert offre["reference"] == "FHF_488995"
    assert offre["employeur"] == "Centre hospitalier"
    assert offre["localisation"] == "Carcassonne"
    assert offre["versant"] == "Fonction publique Hospitalière"
    assert offre["date"] == "02/09/2026"
    assert offre["source"] == SOURCE_LABEL


def test_extraire_offres_sans_lien_ignoree() -> None:
    html = '<article class="card-offer"><h3 class="card-title">Titre</h3></article>'
    assert extraire_offres(html) == []


def test_extraire_offres_url_domaine_invalide_ignoree() -> None:
    html = """
    <article class="card-offer">
      <h3 class="card-title">Titre</h3>
      <a class="btn-link" href="https://evil.example.com/x">Voir</a>
    </article>
    """
    assert extraire_offres(html) == []


def test_extraire_offres_html_vide() -> None:
    assert extraire_offres("") == []


_FICHE_DETAIL = """
<div class="publication-tools">
  <div class="publication-info">Publié le 02 sep. 2026</div>
</div>
<article class="offer offer--view-mode-full">
  <div class="article__content">
    <div class="section"><div class="section-title">Poste proposé</div>Infirmier de nuit F/H</div>
    <div class="section"><div class="section-title">Contrat</div>CDD</div>
    <div class="section"><div class="section-title">Descriptif</div>Prise en charge des patients la nuit.</div>
    <div class="section"><div class="section-title">Personne à contacter</div>
      Postulez sur le site carrière : https://ch-test.softy.pro/offre/1?idt=2
    </div>
    <div class="section"><div class="section-title">Etablissement</div>Centre hospitalier, 1 rue Test, 11000 Carcassonne</div>
  </div>
</article>
"""


def test_extraire_detail_offre_champs_dedies() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert detail["description"] == "Prise en charge des patients la nuit."
    assert detail["date_publication"] == "02 sep. 2026"
    assert detail["lien_postuler"] == "https://ch-test.softy.pro/offre/1?idt=2"


def test_extraire_detail_offre_sections_complementaires_sans_doublon() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert "Poste proposé" not in detail["sections_complementaires"]
    assert "Descriptif" not in detail["sections_complementaires"]
    assert detail["sections_complementaires"]["Contrat"] == "CDD"
    assert "Etablissement" in detail["sections_complementaires"]


def test_extraire_detail_offre_sans_champs() -> None:
    detail = extraire_detail_offre("<html></html>")
    assert detail["description"] == ""
    assert detail["sections_complementaires"] == {}
    assert detail["page_html"] == "<html></html>"


def _offre(titre: str, employeur: str, reference: str = "X") -> Offre:
    return {
        "titre": titre,
        "url": "",
        "reference": reference,
        "domaine": "",
        "employeur": employeur,
        "localisation": "",
        "versant": "",
        "date": "",
        "source": "",
    }


def test_filtrer_doublons_fhf_meme_titre_employeur_lie_est_retire() -> None:
    # Cas réel vérifié cette session : "EPSYLAN (Établissement Psychiatrique
    # de Loire-Atlantique Nord)" / "Centre Hospitalier Epsylan" — même
    # établissement, un mot distinctif partagé ("epsylan").
    fhf = [
        _offre(
            "Cadre de santé - EHPAD",
            "EPSYLAN (Établissement Psychiatrique de Loire-Atlantique Nord)",
        )
    ]
    existantes = [_offre("Cadre de santé - EHPAD", "Centre Hospitalier Epsylan")]
    assert filtrer_doublons_fhf(fhf, existantes) == []


def test_filtrer_doublons_fhf_titre_generique_employeurs_distincts_conserve() -> None:
    # Cas réel vérifié cette session (faux positif évité) : titre générique
    # "Un(e) Infirmier(ère)" mais employeurs sans rapport.
    fhf = [_offre("Un(e) Infirmier(ère)", "SESSAD L'Elan Antenne de Liévin")]
    existantes = [_offre("Un(e) Infirmier(ère)", "E.P.D.A.H.A.A")]
    assert filtrer_doublons_fhf(fhf, existantes) == fhf


def test_filtrer_doublons_fhf_titre_different_conserve() -> None:
    fhf = [_offre("Infirmier de nuit", "Centre Hospitalier Epsylan")]
    existantes = [_offre("Aide-soignant de jour", "Centre Hospitalier Epsylan")]
    assert filtrer_doublons_fhf(fhf, existantes) == fhf


def test_filtrer_doublons_fhf_liste_existante_vide_conserve_tout() -> None:
    fhf = [_offre("Infirmier de nuit", "Centre Hospitalier X")]
    assert filtrer_doublons_fhf(fhf, []) == fhf
