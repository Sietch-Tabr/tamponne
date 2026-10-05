"""Génère les icônes de l'application à partir des SVG de `src/gui/icones/`.

Produit `tamponne.png` (fenêtre, Linux), `tamponne.ico` (Windows) et
`tamponne.icns` (macOS), versionnés : l'application n'a pas besoin de ces
outils. Nécessite `rsvg-convert` et `magick` ; `iconutil` (macOS) pour le
`.icns`.

    uv run python -m outils.generer_icones
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DOSSIER_ICONES = Path(__file__).parent.parent / "src" / "gui" / "icones"
SVG_GRAND = DOSSIER_ICONES / "tamponne.svg"
SVG_PETIT = DOSSIER_ICONES / "tamponne-petit.svg"
TAILLE_MAX_PETIT = 32
"""Jusqu'à cette taille, la variante sans grain ni filet fin reste lisible."""

TAILLES_ICO = (16, 24, 32, 48, 64, 128, 256)
TAILLES_ICNS = (16, 32, 128, 256, 512)
"""Tailles de base d'un `.iconset`, chacune aussi en @2x."""


def _rendre(taille: int, destination: Path) -> Path:
    """PNG carré de `taille` px, depuis la variante adaptée à la taille."""
    svg = SVG_PETIT if taille <= TAILLE_MAX_PETIT else SVG_GRAND
    subprocess.run(
        [
            "rsvg-convert",
            "-w",
            str(taille),
            "-h",
            str(taille),
            str(svg),
            "-o",
            str(destination),
        ],
        check=True,
    )
    return destination


def generer(dossier_tmp: Path) -> None:
    """Écrit les trois fichiers d'icône dans `DOSSIER_ICONES`."""
    _rendre(512, DOSSIER_ICONES / "tamponne.png")

    pngs = [_rendre(t, dossier_tmp / f"ico-{t}.png") for t in TAILLES_ICO]
    subprocess.run(
        ["magick", *map(str, pngs), str(DOSSIER_ICONES / "tamponne.ico")], check=True
    )

    if shutil.which("iconutil") is None:
        print(
            "iconutil absent (macOS uniquement) : .icns non régénéré.", file=sys.stderr
        )
        return
    iconset = dossier_tmp / "tamponne.iconset"
    iconset.mkdir()
    for taille in TAILLES_ICNS:
        _rendre(taille, iconset / f"icon_{taille}x{taille}.png")
        _rendre(taille * 2, iconset / f"icon_{taille}x{taille}@2x.png")
    subprocess.run(
        [
            "iconutil",
            "-c",
            "icns",
            str(iconset),
            "-o",
            str(DOSSIER_ICONES / "tamponne.icns"),
        ],
        check=True,
    )


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="tamponne-icones-") as dossier:
        generer(Path(dossier))
