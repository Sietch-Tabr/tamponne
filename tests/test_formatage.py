"""Tests de la mise en forme des offres (src/formatage.py)."""

from src.formatage import cle_tri_date, offre_vers_ligne, reformater_date
from src.types import Offre


def test_reformater_date_format_reel_du_site() -> None:
    assert reformater_date("26 août 2026") == "26/08/2026"


def test_reformater_date_jour_sur_un_chiffre() -> None:
    assert reformater_date("5 mars 2026") == "05/03/2026"


def test_reformater_date_premier_du_mois_avec_suffixe_er() -> None:
    assert reformater_date("1er janvier 2026") == "01/01/2026"


def test_reformater_date_format_non_reconnu_retourne_tel_quel() -> None:
    assert reformater_date("il y a 6 jours") == "il y a 6 jours"


def test_reformater_date_chaine_vide_retourne_tel_quel() -> None:
    assert reformater_date("") == ""


_OFFRE_TEST: Offre = {
    "titre": "Attaché principal",
    "url": "https://example.org/1",
    "reference": "O1",
    "domaine": "RH",
    "employeur": "DGFiP Hérault",
    "localisation": "Montpellier (34)",
    "versant": "Fonction publique de l'État",
    "date": "26 août 2026",
    "source": "",
}


def test_offre_vers_ligne_reformate_la_date() -> None:
    assert offre_vers_ligne(_OFFRE_TEST) == (
        "Attaché principal",
        "DGFiP Hérault",
        "Montpellier (34)",
        "26/08/2026",
        "Choisir le service public",
    )


def test_offre_vers_ligne_date_absente() -> None:
    offre: Offre = {**_OFFRE_TEST, "date": ""}
    assert offre_vers_ligne(offre)[3] == "—"


def test_offre_vers_ligne_source_territoriale() -> None:
    offre: Offre = {**_OFFRE_TEST, "source": "Fonction publique territoriale"}
    assert offre_vers_ligne(offre)[4] == "Fonction publique territoriale"


def test_cle_tri_date_convertit_jj_mm_aaaa_en_iso() -> None:
    assert cle_tri_date("05/03/2026") == "2026-03-05"


def test_cle_tri_date_format_non_reconnu_retourne_chaine_vide() -> None:
    assert cle_tri_date("—") == ""
    assert cle_tri_date("il y a 6 jours") == ""
