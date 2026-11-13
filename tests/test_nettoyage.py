"""Tests de src/nettoyage.py : retrait des fichiers supprimés d'une version
à l'autre que la mise à jour laisse sur le disque."""

from pathlib import Path

from src import nettoyage
from src.nettoyage import (
    FICHIERS_DEVELOPPEMENT,
    FICHIERS_OBSOLETES,
    nettoyer_fichiers_obsoletes,
)


def _creer(racine: Path, relatif: str, contenu: str = "") -> Path:
    chemin = racine / relatif
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_aucun_fichier_obsolete_n_existe_dans_le_depot() -> None:
    for relatif in FICHIERS_OBSOLETES:
        assert not (nettoyage.CHEMIN_RACINE / relatif).exists(), relatif


def test_ancienne_installation_nettoyee_donnees_intactes(tmp_path: Path) -> None:
    _creer(tmp_path, "src/gui/theme.py")
    _creer(tmp_path, "src/gui/__pycache__/theme.cpython-314.pyc")
    _creer(tmp_path, "src/gui/vues/accueil.py")
    _creer(tmp_path, "src/gui/widgets/case_a_cocher.py")
    _creer(tmp_path, "tests/test_gui_app.py")
    _creer(tmp_path, "lancer.sh")
    _creer(tmp_path, "lancer.bat")
    _creer(tmp_path, "src/gui/application.py", "conservé")
    profils = _creer(tmp_path, "data/profils.json", '{"f": {}}')

    supprimes = nettoyer_fichiers_obsoletes(tmp_path)

    assert set(supprimes) == {
        "src/gui/theme.py",
        "src/gui/vues",
        "src/gui/widgets",
        "tests/test_gui_app.py",
        "lancer.sh",
        "lancer.bat",
        "tests",
    }
    assert not (tmp_path / "src/gui/theme.py").exists()
    assert not (tmp_path / "src/gui/__pycache__/theme.cpython-314.pyc").exists()
    assert not (tmp_path / "src/gui/vues").exists()
    assert not (tmp_path / "lancer.sh").exists()
    assert (tmp_path / "src/gui/application.py").exists()
    assert profils.read_text(encoding="utf-8") == '{"f": {}}'


def test_fichiers_de_developpement_exclus_des_publications() -> None:
    """Chaque fichier retiré des installations est aussi exclu du zip des
    publications (`git archive`), sinon la mise à jour suivante le réinstalle."""
    attributs = (nettoyage.CHEMIN_RACINE / ".gitattributes").read_text(encoding="utf-8")
    for relatif in FICHIERS_DEVELOPPEMENT:
        assert (nettoyage.CHEMIN_RACINE / relatif).exists(), relatif
        assert f"/{relatif} export-ignore" in attributs.splitlines(), relatif


def test_installation_existante_debarrassee_du_developpement(tmp_path: Path) -> None:
    for relatif in ("tests/test_x.py", "outils/maquette/a.html", "docs/captures/c.jpg"):
        _creer(tmp_path, relatif)
    for relatif in (".gitattributes", ".gitignore", "RECHERCHES.md"):
        _creer(tmp_path, relatif)
    _creer(tmp_path, "README.md", "conservé")

    supprimes = nettoyer_fichiers_obsoletes(tmp_path)

    assert set(supprimes) == set(FICHIERS_DEVELOPPEMENT)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["README.md"]


def test_nettoyage_idempotent(tmp_path: Path) -> None:
    _creer(tmp_path, "src/gui/theme.py")
    assert nettoyer_fichiers_obsoletes(tmp_path) == ["src/gui/theme.py"]
    assert nettoyer_fichiers_obsoletes(tmp_path) == []


def test_clone_git_jamais_nettoye(tmp_path: Path) -> None:
    _creer(tmp_path, ".git/HEAD", "ref")
    theme = _creer(tmp_path, "src/gui/theme.py")
    assert nettoyer_fichiers_obsoletes(tmp_path) == []
    assert theme.exists()


def test_lien_sortant_de_l_installation_ignore(tmp_path: Path) -> None:
    exterieur = tmp_path / "exterieur"
    _creer(exterieur, "precieux.txt", "ne pas toucher")
    racine = tmp_path / "installation"
    (racine / "src/gui").mkdir(parents=True)
    (racine / "src/gui/vues").symlink_to(exterieur, target_is_directory=True)
    nettoyer_fichiers_obsoletes(racine)
    assert (exterieur / "precieux.txt").exists()
