"""Tests du module source emploiterritorial (extraction, pas de réseau)."""

from src.sources.emploiterritorial.extraction import (
    SOURCE_LABEL,
    extraire_detail_offre,
    extraire_offres,
    extraire_totaux,
)

_LIGNE_MINIMALE = """
<tr id="O059260901001397">
  <td></td>
  <td>
    <div class="detail-offres d-lg-none">
      <span class="badge-success badge" title="Emploi de catégorie A">A</span>
      <div class="detail-offre-titre">
        <a class="lien-details-offre" href="/offre/ingenieur-systemes-32127">
          Ingénieur systèmes et réseau
        </a>
      </div>
      <div class="detail-offre-collectivite">
        <span class="label">Employeur :</span>
        <span class="valeur"><a href="/x">REGION HAUTS-DE-FRANCE</a></span>
        <span class="font-weight-bold text-secondary">Nord</span>
      </div>
      <button data-tooltip="publié le 01/09/2026">publié aujourd'hui</button>
      <button data-tooltip="Date limite de candidature le 01/10/2026">expire dans 29 jours</button>
    </div>
    <div class="d-none d-lg-block">
      <a class="lien-details-offre" href="/offre/ingenieur-systemes-32127">
        Ingénieur systèmes et réseau (doublon desktop)
      </a>
    </div>
  </td>
</tr>
"""

_PAGE_RECHERCHE = f"""
<input type="hidden" id="nb-offres" value="585" />
<input type="hidden" id="search-limit" value="20" />
<table><tbody>{_LIGNE_MINIMALE}</tbody></table>
"""


def test_extraire_totaux() -> None:
    assert extraire_totaux(_PAGE_RECHERCHE) == (585, 20)


def test_extraire_totaux_champs_absents() -> None:
    assert extraire_totaux("<html></html>") == (0, 20)


def test_extraire_offres_ligne_minimale() -> None:
    offres = extraire_offres(_PAGE_RECHERCHE)
    assert len(offres) == 1
    offre = offres[0]
    assert offre["reference"] == "O059260901001397"
    assert offre["titre"] == "Ingénieur systèmes et réseau"
    assert (
        offre["url"]
        == "https://www.emploi-territorial.fr/offre/ingenieur-systemes-32127"
    )
    assert offre["employeur"] == "REGION HAUTS-DE-FRANCE"
    assert offre["localisation"] == "Nord"
    assert offre["versant"] == "Fonction publique Territoriale"
    assert offre["date"] == "01/09/2026"
    assert offre["source"] == SOURCE_LABEL


def test_extraire_offres_ignore_le_bloc_desktop_duplique() -> None:
    # Un seul lien "lien-details-offre" extrait par offre malgré les deux
    # blocs responsive (mobile/desktop) présents dans le DOM.
    offres = extraire_offres(_PAGE_RECHERCHE)
    assert len(offres) == 1


def test_extraire_offres_sans_lien_ignoree() -> None:
    html = '<tr id="O1"><td><div class="detail-offres"></div></td></tr>'
    assert extraire_offres(html) == []


def test_extraire_offres_url_domaine_invalide_ignoree() -> None:
    html = """
    <tr id="O1"><td><div class="detail-offres">
      <a class="lien-details-offre" href="https://evil.example.com/x">Titre</a>
    </div></td></tr>
    """
    assert extraire_offres(html) == []


def test_extraire_offres_html_vide() -> None:
    assert extraire_offres("") == []


_FICHE_DETAIL = """
<div class="row px-3">Offre n° <span class="pl-1 set-color-green">O059260901001397</span></div>
<div class="row px-3">Publiée le <span class="pl-1 set-color-green">01/09/2026</span></div>
<h2>Ingénieur systèmes et réseau</h2>
<h3>Synthèse de l'offre</h3>
<div class="offre-item"><div class="offre-item-label">Employeur</div>
<div class="offre-item-value">Region Hauts-de-France</div></div>
<div class="offre-item"><div class="offre-item-label">Rémunération indicative</div>
<div class="offre-item-value">Non renseigné</div></div>
<div class="offre-item"><div class="offre-item-label">Experience souhaitée</div>
<div class="offre-item-value">Confirmé</div></div>
<div class="offre-item"><div class="offre-item-label">Famille de métiers</div>
<div class="offre-item-value">Informatique</div></div>
<div class="offre-item"><div class="offre-item-label">Date limite de candidature</div>
<div class="offre-item-value">01/10/2026</div></div>
<div class="offre-item"><div class="offre-item-label">Lien de candidature</div>
<div class="offre-item-value"><a href="https://www.hautsdefrance.fr/offres/123">https://www.hautsdefrance.fr/offres/123</a></div></div>
<div class="offre-item"><div class="offre-item-label">Contact</div>
<div class="offre-item-value">0374270000</div></div>
<div class="offre-item row p-2 font-weight-bold"><div class="offre-item-label">Descriptif de l'emploi</div></div>
<div class="offre-item-text row px-3 mb-3">
  <div class="px-3">Poste rattaché à la direction des systèmes d'information.</div>
</div>
"""


def test_extraire_detail_offre_champs_dedies() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert detail["salaire"] == "Non renseigné"
    assert detail["experience_requise"] == "Confirmé"
    assert detail["secteur"] == "Informatique"
    assert detail["date_publication"] == "01/09/2026"
    assert detail["date_limite"] == "01/10/2026"
    assert detail["lien_postuler"] == "https://www.hautsdefrance.fr/offres/123"


def test_extraire_detail_offre_description_narrative_optionnelle() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert "direction des systèmes d'information" in detail["description"]


def test_extraire_detail_offre_titre_h2_non_capture_dans_description() -> None:
    # Régression : le titre <h2> de l'offre ne doit jamais se retrouver
    # dans description (piège vérifié sur une offre réelle).
    detail = extraire_detail_offre(_FICHE_DETAIL)
    assert "Ingénieur systèmes et réseau" not in detail["description"]


def test_extraire_detail_offre_sans_description_narrative() -> None:
    html = """
    <h2>Poste sans texte libre</h2>
    <div class="offre-item"><div class="offre-item-label">Employeur</div>
    <div class="offre-item-value">Mairie de Test</div></div>
    """
    assert extraire_detail_offre(html)["description"] == ""


def test_extraire_detail_offre_sections_complementaires_sans_doublon() -> None:
    detail = extraire_detail_offre(_FICHE_DETAIL)
    # « Contact » reste ici ; les champs ayant un emplacement dédié
    # (rémunération, expérience, lien, date limite…) ne sont pas dupliqués.
    assert detail["sections_complementaires"] == {
        "Employeur": "Region Hauts-de-France",
        "Contact": "0374270000",
    }


def test_extraire_detail_offre_sans_champs() -> None:
    detail = extraire_detail_offre("<html></html>")
    assert detail["salaire"] == ""
    assert detail["sections_complementaires"] == {}
    assert detail["page_html"] == "<html></html>"
