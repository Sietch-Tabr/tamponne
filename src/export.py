"""Export des résultats en HTML cliquable."""

import webbrowser
from datetime import datetime
from pathlib import Path

from src.types import Offre

DOSSIER_EXPORTS = Path(__file__).parent.parent / "exports"

NB_PAR_PAGE = 20
"""Taille de page servant à estimer le nombre total d'offres sur le site
à partir du nombre de pages (« ~N au total » dans l'export) — estimation
d'affichage, indépendante de la pagination réelle de l'API."""

_CSS = """
body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
h1 { font-size: 1.3rem; color: #005b99; border-bottom: 2px solid #005b99; padding-bottom: .5rem; }
.meta { font-size: .85rem; color: #666; margin-bottom: 1.5rem; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
thead th { background: #005b99; color: #fff; padding: .6rem .8rem; text-align: left; }
tbody tr:nth-child(even) { background: #f4f8fc; }
tbody tr:hover { background: #dbeeff; }
td { padding: .55rem .8rem; vertical-align: top; border-bottom: 1px solid #e0e0e0; }
a { color: #005b99; text-decoration: none; }
a:hover { text-decoration: underline; }
.ref { font-size: .78rem; color: #888; }
"""


def _echapper_html(texte: str) -> str:
    return (
        texte.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def exporter_html(
    offres: list[Offre],
    resume_filtres: str,
    nb_pages: int,
    nom_profil: str | None = None,
) -> Path:
    """Génère un fichier HTML et retourne son chemin."""
    DOSSIER_EXPORTS.mkdir(parents=True, exist_ok=True)

    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_base = (
        "".join(
            c if c.isalnum() or c in "-_" else "-"
            for c in (nom_profil or "recherche").lower()
        ).strip("-")
        or "recherche"
    )
    chemin = DOSSIER_EXPORTS / f"{nom_base}_{horodatage}.html"

    lignes_offres = []
    for i, o in enumerate(offres, 1):
        titre_echappe = _echapper_html(o["titre"])
        url = _echapper_html(o["url"])
        ref = _echapper_html(o.get("reference", ""))
        employeur = _echapper_html(o.get("employeur", ""))
        localisation = _echapper_html(o.get("localisation", ""))
        date = _echapper_html(o.get("date", ""))
        lignes_offres.append(
            f"<tr>"
            f"<td>{i}</td>"
            f'<td><a href="{url}" target="_blank">{titre_echappe}</a>'
            f'<br><span class="ref">{ref}</span></td>'
            f"<td>{employeur}</td>"
            f"<td>{localisation}</td>"
            f"<td>{date}</td>"
            f"</tr>"
        )

    nb_total_approx = nb_pages * NB_PAR_PAGE
    date_generation = datetime.now().strftime("%d/%m/%Y à %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offres — {_echapper_html(resume_filtres)}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Offres d'emploi — Choisir le Service Public</h1>
<div class="meta">
  <strong>Filtres :</strong> {_echapper_html(resume_filtres)}<br>
  <strong>Résultats :</strong> {len(offres)} offres affichées
  (~{nb_total_approx} au total, {nb_pages} page(s))<br>
  <strong>Généré le :</strong> {date_generation}
</div>
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Titre</th>
      <th>Employeur</th>
      <th>Localisation</th>
      <th>Publiée le</th>
    </tr>
  </thead>
  <tbody>
    {"".join(lignes_offres)}
  </tbody>
</table>
</body>
</html>"""

    chemin.write_text(html, encoding="utf-8")
    return chemin


def ouvrir_dans_navigateur(chemin: Path) -> None:
    """Ouvre le fichier HTML dans le navigateur par défaut."""
    webbrowser.open(chemin.as_uri())
