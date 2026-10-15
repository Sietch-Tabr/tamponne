# Tamponné

_« Les postes publics, enfin au même endroit. »_

Application de bureau pour rechercher des offres d'emploi de la fonction publique, multi-source ([choisirleservicepublic.gouv.fr](https://choisirleservicepublic.gouv.fr), [emploi-territorial.fr](https://www.emploi-territorial.fr), Passerelles/MEF, FHF), avec fiches de recherche sauvegardées et suivi de candidature, dans une interface « dossier administratif » (bureau de jour ou de nuit).

![Registre des offres, bureau de jour](docs/captures/recherche-jour.jpg)

![Dossiers en cours, bureau de nuit](docs/captures/suivi-nuit.jpg)

## Installation

Rien à installer au préalable : au premier lancement, Tamponné installe lui-même ce dont il a besoin ([uv](https://docs.astral.sh/uv/), puis Python et ses composants). Une connexion internet est nécessaire la première fois (quelques minutes).

1. **Télécharger** : sur la page [Releases](https://codeberg.org/Kwaite/tamponne/releases), dans la dernière version, cliquer sur **« Source code (ZIP) »**.
2. **Dézipper** le fichier où vous voulez (Documents, Bureau…). Tamponné est portable : il reste dans ce dossier, avec vos données (`data/`). Pour le déplacer, déplacez tout le dossier.
3. **Double-cliquer** sur le lanceur :

| Système | Lanceur                                                                                               |
| ------- | ----------------------------------------------------------------------------------------------------- |
| Windows | `Tamponne.bat`                                                                                        |
| macOS   | `Tamponne.command`                                                                                    |
| Linux   | `Tamponne.command`, ou `./Tamponne.command` dans un terminal si le double-clic l'ouvre comme un texte |

Au premier lancement, une fenêtre de terminal montre l'installation, puis Tamponné propose de s'ajouter au menu des applications (voir [Raccourci](#raccourci)) : il se lance ensuite comme n'importe quelle application.

> **Windows derrière un proxy d'entreprise** : le proxy configuré dans Windows (Options Internet, script de configuration automatique) est détecté au lancement. Pour en imposer un autre, définissez la variable d'environnement `HTTPS_PROXY` (ex. `http://proxy:3128`) avant de lancer `Tamponne.bat`.

> **macOS : « Tamponne.command ne peut pas être ouvert »**. Au premier double-clic, macOS bloque les fichiers téléchargés qui ne viennent pas de l'App Store ou d'un développeur identifié. Ouvrez **Réglages Système › Confidentialité et sécurité**, descendez jusqu'au message sur `Tamponne.command`, cliquez sur **« Ouvrir quand même »** et confirmez avec votre mot de passe. Une seule fois : les lancements suivants (et le raccourci) ne sont plus bloqués.

## Raccourci

Réglages › **Raccourci** ajoute ou retire Tamponné du menu des applications :

| Système | Raccourci créé                                        | Où le trouver              |
| ------- | ----------------------------------------------------- | -------------------------- |
| Windows | `Tamponné.lnk` dans le menu Démarrer                  | menu Démarrer, épinglable  |
| macOS   | `Tamponné.app` dans `~/Applications`                  | Spotlight, Launchpad, Dock |
| Linux   | `tamponne.desktop` dans `~/.local/share/applications` | menu des applications      |

Si vous déplacez le dossier de Tamponné, relancez-le une fois depuis son lanceur : il propose de mettre le raccourci à jour (ou de le retirer).

## Sauvegarde de vos données

Réglages › **Sauvegarde** :

- **Exporter…** réunit vos fiches de recherche, dossiers suivis (avec les fiches de poste archivées), offres déjà vues et réglages dans un fichier `Tamponne-donnees-AAAA-MM-JJ.zip`, à garder ou à copier sur un autre ordinateur.
- **Importer…** remplace toutes les données par celles d'une sauvegarde, après confirmation, puis redémarre Tamponné. Une copie des données d'avant l'import est conservée dans `data/sauvegarde-avant-import.zip`.

## Maintenance

Réglages › **Maintenance** › Exports de recherche : nombre et taille des exports HTML du registre (dossier `exports/`), avec **Ouvrir le dossier** et **Supprimer…** (tous, après confirmation).

## Désinstaller

1. Si vous avez ajouté le raccourci, retirez-le d'abord : Réglages › Raccourci › **Retirer**.
2. Exportez vos données si vous voulez les garder, puis supprimez le dossier de Tamponné.

uv, installé au premier lancement, peut servir à d'autres logiciels : il reste en place ([le désinstaller](https://docs.astral.sh/uv/getting-started/installation/#uninstallation)).

## Fonctionnalités

- **Multi-source** — choisirleservicepublic.gouv.fr, emploi-territorial.fr, Passerelles/MEF, FHF, chacune activable depuis Réglages › Sources consultées ; dédoublonnage automatique des offres communes
- **Demande de recherche** — catégorie (dont A+), corps et grade (Attaché, Adjoint administratif), versant, domaines, type de poste, expérience, date de publication, localisations, organisations, management, télétravail, grades supérieurs, mot-clé libre
- **Fiches de recherche** — classer une demande, la lancer, la modifier, la dupliquer ou la supprimer depuis l'onglet Profils
- **Nouvelles offres** — à chaque lancement d'une fiche, les offres jamais vues pour elle portent le tampon « Nouveau » dans le registre, avec un filtre pour ne voir qu'elles
- **Registre des offres** — pagination complète (jusqu'à 20 pages par source), tri par colonne, filtre en direct, export HTML des offres affichées
- **Filtre grades supérieurs** — offres IDIV/IP/AFIPA écartées par défaut, réintégrables
- **Suivi de candidature** — dossiers tamponnés depuis le registre avec fiche de poste archivée en PDF, historique d'événements modifiable, relance suggérée après 3 semaines sans nouvelles, vérification des offres dépubliées
- **Accessibilité** — contrastes WCAG AA vérifiés par les tests, navigation au clavier, éléments exposés aux lecteurs d'écran, option « Réduire les animations »
- **Cache organisations** — liste des ministères et sous-organisations mise en cache 7 jours, rafraîchissable depuis Réglages
- **Raccourci et sauvegarde** — ajout au menu des applications, export et import des données (voir plus haut)
- **Mise à jour automatique** — voir ci-dessous

## Mise à jour automatique

Au lancement, l'app vérifie en arrière-plan s'il existe une publication ([Releases](https://codeberg.org/Kwaite/tamponne/releases) Codeberg) plus récente que la version installée — jamais un `git pull` sur une branche, uniquement ce qui a été explicitement publié.

- Une mise à jour disponible se signale par un point rouge sur l'onglet « Réglages », où l'avis de mise à jour présente la nouvelle version et ses notes ; sinon l'avis indique que la version installée est à jour.
- Par défaut, elle s'applique automatiquement **au prochain lancement**, sans action requise (« Au prochain lancement » efface simplement le point rouge).
- « Installer et redémarrer » l'applique **immédiatement** : l'app se ferme et relance toute seule.
- Les fichiers retirés d'une version à l'autre sont supprimés à l'installation ; vos données (`data/`) ne sont jamais touchées.
- Si la nouvelle version ne s'installe pas (Python ou composants impossibles à télécharger) ou ne démarre pas, Tamponné revient tout seul à la version précédente et l'explique. La version en échec n'est plus retentée d'elle-même : l'avis de mise à jour en donne la raison, et « Installer et redémarrer » la retente quand le problème est réglé.
- uv se met à jour de lui-même s'il est trop ancien pour la version de Python demandée.

Ce mécanisme repose sur les lanceurs (`Tamponne.command`, `Tamponne.bat`, ou le raccourci) — un lancement via `uv run python -m src.gui.application` en direct affiche l'avis mais n'applique rien.

## En cas de problème

Les messages d'erreur disent quoi faire, suivis d'une ligne « Détail » qui reprend l'erreur technique. Le journal `data/tamponne.log` garde, lancement après lancement, l'heure et le détail technique de chaque erreur (sources injoignables, mises à jour, sauvegardes…) ainsi que les sorties de uv ; au-delà de 1 Mo, il est archivé dans `data/tamponne.1.log`. Le chemin de votre dossier personnel y est remplacé par `~`, et vos fiches, notes et candidatures n'y figurent pas : joignez-le à un signalement sur [Codeberg](https://codeberg.org/Kwaite/tamponne/issues), après l'avoir relu.

## Sécurité et confidentialité

- **Vos données restent sur votre ordinateur**, dans le dossier `data/` de Tamponné : fiches, dossiers suivis, notes. Rien n'est envoyé ailleurs.
- **Connexions** : uniquement les quatre sites d'offres (pour les recherches, fiches et vérifications), Codeberg (mises à jour) et, à l'installation, les serveurs de uv et de Python. Toutes en HTTPS, certificats vérifiés par le système (comme le navigateur, via `truststore`), avec un User-Agent qui désigne Tamponné.
- **Liens ouverts** : seuls les liens `https://` (offres, notes de version) s'ouvrent dans le navigateur, jamais un autre type d'adresse.
- **Mises à jour** : téléchargées uniquement depuis le dépôt Codeberg de Tamponné, en HTTPS. Elles ne sont pas signées : leur sûreté repose sur la protection du compte qui publie.
- **Installation de uv** : le script officiel (`astral.sh`) est exécuté tel quel, comme le recommande uv ; c'est aussi lui qui sert de secours pour mettre uv à jour sous Windows.
- **Sauvegardes importées** : seuls les fichiers attendus sont acceptés (pas de chemin vers l'extérieur du dossier `data/`), avec une taille plafonnée et une copie des données d'avant l'import.

## Avancé : lancement manuel

```bash
uv sync
uv run python -m src.lanceur           # avec mises à jour et redémarrage
uv run python -m src.gui.application   # interface seule
```

**Dépendances** : `PySide6` (interface Qt Quick/QML), `beautifulsoup4` (parsing HTML). Polices embarquées : [Archivo](https://fonts.google.com/specimen/Archivo) et [IBM Plex Mono](https://github.com/IBM/plex), sous licence SIL OFL 1.1 (`src/gui/qml/Tamponne/polices/`).

## Architecture

```
src/
  gui/
    application.py           point d'entrée : moteur QML, vérification de mise à jour
    pont.py                  objet unique exposé au QML (contrôleurs)
    controleur_*.py          un contrôleur par écran : Profils, Recherche, Suivi, Réglages
    presentation.py          textes affichés, calculés sans Qt
    modele_offres.py         registre : modèle, tri et filtres
    modele_registre.py       colonnes du registre des offres
    travailleurs.py          tâches réseau sur QThread (recherche, vérifications)
    qml/Tamponne/            interface QML : Theme.qml (couleurs jour/nuit), écrans,
                             dialogues, composants, polices embarquées
    icones/                  icône de l'application (SVG source, PNG, ICO, ICNS)
  sources/
    base.py                  Protocol commun aux sources d'offres + dédoublonnage
    choisirleservicepublic/  requêtes GET filtrées + parsing HTML (BeautifulSoup4)
    emploiterritorial/       portail légal CDG/CNFPT (FPT)
    passerellesmef/          portail Talentsoft des ministères économiques et financiers
    fhf/                     portail de la Fédération Hospitalière de France (FPH)
  recherche.py               orchestration multi-source (sans Qt)
  cache.py                   cache organisations (7 j) + offres vues par fiche (30 j)
  candidatures.py            suivi de candidature
  filtres.py                 constantes IDs API (catégories, grades, versants, domaines, localisations)
  parametres_sources.py      sources actives/inactives
  parametres_affichage.py    thème et réduction des animations
  profils.py                 fiches de recherche sauvegardées
  lanceur.py                 boucle de lancement : mise à jour en attente, redémarrage
  maj.py                     vérification/application des mises à jour (publications Codeberg)
  nettoyage.py               retrait des fichiers supprimés d'une version à l'autre
  raccourci.py               raccourci du menu des applications (Windows, macOS, Linux)
  sauvegarde.py              export et import des données
  export.py                  export HTML inline
  utils.py                   écriture JSON atomique
  types.py                   structures de données partagées (TypedDict)
data/
  profils.json               fiches de recherche
  candidatures.json          suivi de candidature
  cache.json                 cache organisations
  offres.json                offres vues par fiche
  sources.json               sources actives/inactives
  affichage.json             thème et animations
  maj_disponible.json        marqueur de mise à jour en attente
  raccourci.json             dossier visé par le raccourci, question déjà posée
  sauvegarde-avant-import.zip  données d'avant le dernier import
  archives/                  archives PDF des offres suivies
exports/                     fichiers HTML générés
outils/
  maquette/                  maquette de référence (HTML)
  comparer_maquette.py       comparaison visuelle maquette / application
  generer_icones.py          génération des icônes depuis les SVG
Tamponne.command             lanceur macOS / Linux
Tamponne.bat                 lanceur Windows
docs/captures/               captures d'écran du README
```

## API

`choisirleservicepublic.gouv.fr` utilise WordPress avec un endpoint AJAX (`admin-ajax.php`, action `get_offers`) pour la **première page uniquement** — le serveur ignore le paramètre de pagination AJAX. La pagination réelle se fait via des **requêtes GET** sur des URLs WordPress au format rewrite :

```
GET /nos-offres/filtres/localisation/284/domaine/3522/versant/2456/categorie/1805/type/4534-2349/
GET /nos-offres/filtres/localisation/284/domaine/3522/versant/2456/categorie/1805/type/4534-2349/page/2/
```

Le mapping paramètres → segments URL est documenté dans `RECHERCHES.md` (spécifique à ce site).

## Filtres disponibles

| Filtre                   | Valeurs                                                                                 |
| ------------------------ | --------------------------------------------------------------------------------------- |
| Catégorie                | A+ (direction), A+ (autres emplois fonctionnels), A, B, C                               |
| Corps / grade            | Attaché (principal, hors classe), Adjoint administratif (principal de 2e et 1re classe) |
| Versant                  | État (défaut), Hospitalier, Territorial — cumulables, aucun = tous                      |
| Type de poste            | Titulaire-éligible (défaut), Titulaire, Contractuel, Tous                               |
| Domaine                  | 29 domaines métier (Numérique, Finances Publiques, etc.)                                |
| Localisation             | 114 départements/régions                                                                |
| Organisation             | scrapées automatiquement (ministères et sous-organisations)                             |
| Expérience               | Débutant, Confirmé, Expert                                                              |
| Date de publication      | Dernières 48 heures, 7 derniers jours, 14 derniers jours                                |
| Management / Télétravail | Basculables indépendamment                                                              |
| Grades supérieurs        | Écartés par défaut (IDIV, IP, AFIPA), réintégrables                                     |

Filtre Corps / grade : reconnaissance par mots-clés dans le titre, appliquée côté client après agrégation — aucune source n'expose ce niveau de granularité côté serveur. Catégorie/Localisation/Expérience/Management/Télétravail sont eux câblés côté serveur sur emploi-territorial.fr (voir `src/sources/emploiterritorial/filtres.py`), en plus de choisirleservicepublic.gouv.fr.

## Développement

```bash
uv sync                    # inclut le groupe dev (pytest, mypy...) par défaut
uv run pytest -q           # suite de tests (pytest-qt, offscreen)
uv run mypy                # typage
uv run pyside6-qmllint -I src/gui/qml src/gui/qml/Tamponne/*.qml
uv run python -m outils.comparer_maquette recherche   # maquette / application, jour et nuit
```

## Données

- `RECHERCHES.md` — notes de reverse engineering de l'API choisirleservicepublic.gouv.fr
- `outils/maquette/` — maquette de référence de l'interface
