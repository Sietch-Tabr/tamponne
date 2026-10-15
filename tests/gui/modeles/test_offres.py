"""Tests du modèle des résultats de recherche (src/gui/modeles/offres.py)."""

from PySide6.QtCore import Qt

from src.gui.modeles.offres import ROLE_OFFRE, ModeleOffres, ProxyOffres
from src.types import Offre


def _offre(reference: str, titre: str, date: str, employeur: str = "") -> Offre:
    return {
        "titre": titre,
        "url": f"https://example.org/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": employeur,
        "localisation": "",
        "versant": "",
        "date": date,
        "source": "",
    }


_OFFRES = [
    _offre("A", "Attaché RH", "5 mars 2026", "DGFiP"),
    _offre("B", "Infirmier de nuit", "26 août 2026", "CHU Nantes"),
    _offre("C", "Juriste", "1er janvier 2025", "Préfecture"),
]


def _proxy(nouvelles: set[str] | None = None) -> ProxyOffres:
    modele = ModeleOffres()
    modele.definir_offres(_OFFRES, nouvelles or set())
    proxy = ProxyOffres()
    proxy.setSourceModel(modele)
    return proxy


def _references(proxy: ProxyOffres) -> list[str]:
    return [offre["reference"] for offre in proxy.offres_visibles()]


def test_modele_expose_entetes_et_cellules() -> None:
    modele = ModeleOffres()
    modele.definir_offres(_OFFRES, set())
    assert modele.rowCount() == 3
    assert modele.columnCount() == 5
    assert modele.headerData(3, Qt.Orientation.Horizontal) == "Publiée le"
    assert modele.index(0, 3).data() == "05/03/2026"
    assert modele.index(1, 0).data(ROLE_OFFRE)["reference"] == "B"


def test_modele_marque_les_nouvelles_offres_dune_etoile() -> None:
    modele = ModeleOffres()
    modele.definir_offres(_OFFRES, {"B"})
    assert modele.index(1, 0).data() == "★ Infirmier de nuit"
    assert modele.index(1, 0).data(Qt.ItemDataRole.ToolTipRole) == ("Infirmier de nuit")
    assert modele.index(0, 0).data() == "Attaché RH"


def test_proxy_sans_tri_conserve_lordre_dorigine() -> None:
    assert _references(_proxy()) == ["A", "B", "C"]


def test_proxy_tri_par_date_chronologique_et_non_alphabetique() -> None:
    proxy = _proxy()
    proxy.sort(3, Qt.SortOrder.AscendingOrder)
    # Tri alphabétique sur JJ/MM/AAAA donnerait A (05/03), C (01/01), B (26/08).
    assert _references(proxy) == ["C", "A", "B"]
    proxy.sort(3, Qt.SortOrder.DescendingOrder)
    assert _references(proxy) == ["B", "A", "C"]


def test_proxy_tri_texte_insensible_a_la_casse() -> None:
    modele = ModeleOffres()
    modele.definir_offres(
        [
            _offre("X", "zèbre", ""),
            _offre("Y", "Abeille", ""),
            _offre("Z", "bison", ""),
        ],
        set(),
    )
    proxy = ProxyOffres()
    proxy.setSourceModel(modele)
    proxy.sort(0, Qt.SortOrder.AscendingOrder)
    assert _references(proxy) == ["Y", "Z", "X"]


def test_proxy_filtre_texte_sur_toutes_les_colonnes() -> None:
    proxy = _proxy()
    proxy.setFilterFixedString("chu")  # colonne Employeur, casse ignorée
    assert _references(proxy) == ["B"]
    proxy.setFilterFixedString("")
    assert _references(proxy) == ["A", "B", "C"]


def test_proxy_nouvelles_seulement_se_combine_au_filtre_texte() -> None:
    proxy = _proxy(nouvelles={"A", "B"})
    proxy.definir_nouvelles_seulement(True)
    assert _references(proxy) == ["A", "B"]
    proxy.setFilterFixedString("infirmier")
    assert _references(proxy) == ["B"]
    proxy.definir_nouvelles_seulement(False)
    proxy.setFilterFixedString("")
    assert _references(proxy) == ["A", "B", "C"]
