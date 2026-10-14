"""Tests de src/gui/modele_registre.py : colonnes du registre, numéros,
dates courtes, tampon « Nouveau » et clés de tri."""

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication

from src.formatage import SOURCE_PAR_DEFAUT
from src.gui.modele_offres import ROLE_TRI
from src.gui.modele_registre import ENTETES_REGISTRE, ROLE_NOUVELLE, ModeleRegistre
from src.types import Offre


def _offre(reference: str, date: str, source: str = "") -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://example.org/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": "Paris (75)",
        "versant": "",
        "date": date,
        "source": source,
    }


def _modele(qapp: QApplication) -> ModeleRegistre:
    modele = ModeleRegistre(qapp)
    modele.definir_offres(
        [_offre("A", "02/10/2026"), _offre("B", "", "FHF")], nouvelles={"A"}
    )
    return modele


def _valeur(modele: ModeleRegistre, ligne: int, colonne: int, role: int) -> object:
    return modele.data(modele.index(ligne, colonne, QModelIndex()), role)


def test_entetes_et_nombre_de_colonnes(qapp: QApplication) -> None:
    modele = _modele(qapp)
    assert modele.columnCount() == len(ENTETES_REGISTRE) == 6
    assert [
        modele.headerData(c, Qt.Orientation.Horizontal) for c in range(6)
    ] == ENTETES_REGISTRE


def test_cellules_numero_date_courte_tirets_et_source(qapp: QApplication) -> None:
    modele = _modele(qapp)
    affiche = Qt.ItemDataRole.DisplayRole
    assert _valeur(modele, 0, 0, affiche) == "01"
    assert _valeur(modele, 0, 4, affiche) == "02/10/26"
    assert _valeur(modele, 0, 2, affiche) == "—"
    assert _valeur(modele, 0, 5, affiche) == SOURCE_PAR_DEFAUT
    assert _valeur(modele, 1, 4, affiche) == "—"
    assert _valeur(modele, 1, 5, affiche) == "FHF"


def test_numero_a_la_largeur_du_dernier(qapp: QApplication) -> None:
    modele = ModeleRegistre()
    offres = [_offre(str(i), "01/10/2026") for i in range(120)]
    modele.definir_offres(offres, set())
    assert modele.numero(0) == "001"
    assert modele.numero(119) == "120"
    modele.definir_offres(offres[:9], set())
    assert modele.numero(0) == "01"


def test_tampon_nouveau_sur_l_intitule_seulement(qapp: QApplication) -> None:
    modele = _modele(qapp)
    assert _valeur(modele, 0, 1, ROLE_NOUVELLE) is True
    assert _valeur(modele, 0, 0, ROLE_NOUVELLE) is False
    assert _valeur(modele, 1, 1, ROLE_NOUVELLE) is False


def test_cles_de_tri_numero_et_date(qapp: QApplication) -> None:
    modele = _modele(qapp)
    assert _valeur(modele, 1, 0, ROLE_TRI) == "000001"
    cle_a = _valeur(modele, 0, 4, ROLE_TRI)
    cle_b = _valeur(modele, 1, 4, ROLE_TRI)
    assert isinstance(cle_a, str) and isinstance(cle_b, str)
    assert cle_a != cle_b
