# Tamponné

_« Les postes publics, enfin au même endroit. »_

Application de bureau pour rechercher des offres d'emploi de la fonction publique, multi-source ([choisirleservicepublic.gouv.fr](https://choisirleservicepublic.gouv.fr), [emploi-territorial.fr](https://www.emploi-territorial.fr), Passerelles/MEF, FHF), avec profils de recherche sauvegardés et suivi de candidature.

## Prérequis

- [Python 3.14+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — gestionnaire de paquets Python

Installation uv (si absent) :

**macOS/Linux** :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS (Homebrew)** :

```bash
brew install uv
```

**Windows** :

```bash
winget install astral-sh.uv
```

## Installation et lancement

Téléchargez le zip depuis la page [Releases](https://codeberg.org/Kwaite/tamponne/releases) (lien « Source code (zip) » de la dernière version), puis dézippez-le.

Dans le dossier obtenu :

| Système       | Commande      |
| ------------- | ------------- |
| macOS / Linux | `./lancer.sh` |
| Windows       | `lancer.bat`  |

> **macOS/Linux** : si le terminal répond `permission denied`, le bit exécutable n'a pas été conservé à la décompression — lancez `chmod +x lancer.sh` une fois, puis relancez `./lancer.sh`.

`uv sync` installe automatiquement le virtualenv et les dépendances au premier lancement. Ces deux scripts appliquent aussi les mises à jour en attente (voir plus bas) — c'est la façon recommandée de lancer l'app.

```bash
# Ou manuellement (toutes plateformes) — pas de mise à jour automatique dans ce cas
uv sync
uv run python -m src.gui.app
```

**Dépendances** : `PySide6` (interface), `beautifulsoup4` (parsing HTML).

## Fonctionnalités

- **Multi-source** — choisirleservicepublic.gouv.fr, emploi-territorial.fr, Passerelles/MEF, FHF, chacune activable/désactivable depuis l'onglet Sources ; dédoublonnage automatique des offres communes
- **Recherche multi-critères** — catégorie (dont A+), grade (Attaché/Attaché principal/Attaché hors classe), domaine, localisation, organisation, versant, type de poste, expérience, date de publication, management, télétravail, mot-clé libre
- **Profils de recherche sauvegardés** — lancer, modifier, dupliquer, supprimer en un clic depuis l'écran d'accueil
- **Pagination complète** — toutes les pages de résultats chargées automatiquement (jusqu'à 20 pages)
- **Badge nouvelles offres** — les offres non vues restent marquées ★ pendant 24h, avec un filtre dédié pour ne voir qu'elles
- **Filtre grades supérieurs** — exclusion par défaut des postes IDIV/IP/AFIPA, désactivable
- **Suivi de candidature** — historique d'événements par offre (candidature envoyée, entretien, réponse...), badge de relance suggérée
- **Export HTML** — tableau cliquable avec liens directs vers les offres
- **Cache organisations** — liste des ministères/sous-organisations scrapée et mise en cache 7 jours
- **Mise à jour automatique** — vérification en arrière-plan des publications du dépôt, voir ci-dessous

## Mise à jour automatique

Au lancement, l'app vérifie en arrière-plan s'il existe une publication ([Releases](https://codeberg.org/Kwaite/tamponne/releases) Codeberg) plus récente que la version installée — jamais un `git pull` sur une branche, uniquement ce qui a été explicitement publié.

- Une mise à jour disponible se signale par un point vert à côté de « Paramètres » dans le bandeau de navigation. La carte « Mise à jour » de l'écran Paramètres est toujours visible : elle indique la version installée quand tout est à jour, ou la version disponible (notes de version incluses) avec le bouton de mise à jour actif sinon.
- Par défaut, elle s'applique automatiquement **au prochain lancement**, sans action requise.
- Le bouton « Mettre à jour maintenant » de cette carte l'applique **immédiatement** : l'app se ferme et relance toute seule.

Ce mécanisme repose sur `lancer.sh`/`lancer.bat` (voir ci-dessus) — un lancement via `uv run python -m src.gui.app` en direct affiche l'indicateur mais n'applique rien tant que l'un de ces deux scripts n'est pas utilisé au moins une fois.

## Architecture

```
src/
  gui/
    app.py                 point d'entrée, fenêtre principale et bandeau de navigation
    theme.py                feuille de style QSS
    travailleurs.py          recherche réseau + vérification de mise à jour, sur QThread
    vues/                   écrans : accueil, recherche+résultats, candidatures, sources, aide, paramètres
    widgets/                composants réutilisables (CaseACocher, dialogues de sélection,
                             détail d'offre, ligne responsive, point de statut)
  sources/
    base.py                 Protocol commun aux sources d'offres + dédoublonnage
    choisirleservicepublic/ requêtes GET filtrées + parsing HTML (BeautifulSoup4)
    emploiterritorial/       portail légal CDG/CNFPT (FPT)
    passerellesmef/          portail Talentsoft des ministères économiques et financiers
    fhf/                     portail de la Fédération Hospitalière de France (FPH)
  cache.py                  cache organisations (7j) + cache offres vues par profil (30j)
  candidatures.py            CRUD suivi de candidature
  filtres.py                 constantes IDs API (catégories, grades, versants, domaines, localisations)
  parametres_sources.py       sources actives/inactives
  profils.py                  CRUD profils sauvegardés
  maj.py                      vérification/application des mises à jour (publications Codeberg)
  export.py                   export HTML inline
  utils.py                    écriture JSON atomique
  types.py                     structures de données partagées (TypedDict)
data/
  profils.json                profils sauvegardés
  candidatures.json           suivi de candidature
  cache.json                  cache organisations
  offres.json                 cache offres vues par profil
  sources.json                sources actives/inactives
  maj_disponible.json         marqueur de mise à jour en attente
  archives/                   archives PDF des offres suivies
exports/                      fichiers HTML générés
```

## API

`choisirleservicepublic.gouv.fr` utilise WordPress avec un endpoint AJAX (`admin-ajax.php`, action `get_offers`) pour la **première page uniquement** — le serveur ignore le paramètre de pagination AJAX. La pagination réelle se fait via des **requêtes GET** sur des URLs WordPress au format rewrite :

```
GET /nos-offres/filtres/localisation/284/domaine/3522/versant/2456/categorie/1805/type/4534-2349/
GET /nos-offres/filtres/localisation/284/domaine/3522/versant/2456/categorie/1805/type/4534-2349/page/2/
```

Le mapping paramètres → segments URL est documenté dans `RECHERCHES.md` (spécifique à ce site).

## Filtres disponibles

| Filtre                   | Valeurs                                                     |
| ------------------------ | ----------------------------------------------------------- |
| Catégorie                | A+ (direction / autres emplois fonctionnels), A, B, C       |
| Grade                    | Attaché, Attaché principal, Attaché hors classe             |
| Versant                  | FPE (défaut), Hospitalier, Territorial, Tous                |
| Type de poste            | Titulaire-éligible (défaut), Titulaire, Contractuel, Tous   |
| Domaine                  | 29 domaines métier (Numérique, Finances Publiques, etc.)    |
| Localisation             | 114 départements/régions                                    |
| Organisation             | scrapées automatiquement (ministères et sous-organisations) |
| Expérience               | Débutant, Confirmé, Expert                                  |
| Date de publication      | Dernières 48h, 7 derniers jours, 14 derniers jours          |
| Management / Télétravail | Basculables indépendamment                                  |

Filtre Grade : reconnaissance par mots-clés dans le titre, appliquée côté client après agrégation — aucune source n'expose ce niveau de granularité côté serveur. Catégorie/Localisation/Expérience/Management/Télétravail sont eux câblés côté serveur sur emploi-territorial.fr (voir `src/sources/emploiterritorial/filtres.py`), en plus de choisirleservicepublic.gouv.fr.

## Développement

```bash
uv sync                 # inclut le groupe dev (pytest, mypy...) par défaut
uv run pytest -q       # suite de tests (pytest-qt, offscreen)
uv run mypy src/
```

## Données

- `RECHERCHES.md` — notes de reverse engineering de l'API choisirleservicepublic.gouv.fr
- `CLAUDE.md` — contexte pour le développement
