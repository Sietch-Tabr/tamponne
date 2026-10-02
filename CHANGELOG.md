# Historique des versions

Toutes les évolutions notables de Tamponné, de la plus récente à la plus
ancienne. Le détail de chaque version est aussi publié sur la page
[Releases](https://codeberg.org/Kwaite/tamponne/releases) du dépôt.

## [1.0.5] — 2026-10-03

### Fiabilité

- Réorganisation interne du moteur de recherche, sans changement visible : recherche, résultats et suivi de candidature fonctionnent comme avant
- Couverture de tests renforcée sur la recherche multi-source et le suivi d'offre

### Maintenance

- Outils de vérification du code mis à jour

## [1.0.4] — 2026-09-26

### Recherche

- Les 4 sources sont interrogées en même temps : une recherche complète est environ 3 fois plus rapide
- Progression plus lisible : pages chargées toutes sources confondues et nombre de sources terminées
- Tri des résultats en cliquant sur un en-tête de colonne (dates dans l'ordre chronologique)
- Nouveau champ « Filtrer les résultats… » pour affiner la liste sans relancer de recherche
- L'export HTML reprend exactement les offres affichées, dans l'ordre affiché

### Apparence

- Thème clair, en plus du thème sombre
- Choix du thème dans Paramètres, carte Apparence : automatique (suit le système), sombre ou clair
- En mode automatique, le thème change dès que le système bascule entre clair et sombre
- Rendu identique sur macOS, Windows et Linux
- Contrastes des textes vérifiés selon les normes d'accessibilité (WCAG AA)
- La puce verte de mise à jour s'affiche désormais sur le bouton Paramètres

### Suivi de candidature

- Liste plus fluide avec de nombreuses candidatures
- Nouveaux raccourcis : Entrée ouvre le détail, Suppr arrête le suivi, clic droit pour toutes les actions

### Corrections

- Titres des cartes de Paramètres et d'Aide qui étaient rognés
- Ligne sélectionnée plus lisible dans le tableau de résultats

## [1.0.3] — 2026-09-05

### Filtre grade

- Le filtre grade distingue désormais Catégorie, Corps et Grade — trois notions statutaires distinctes que le bouton unique « Grade(s) » confondait
- Nouveau sélecteur Corps / Grade (arbre avec recherche) à la place de la liste plate
- Nouveau corps « Adjoint administratif » (catégorie C), en plus d'« Attaché »
- Retrait du sous-titre « Catégorie(s) » redondant avec le titre de section « Catégorie »

### Aide

- Exemples de recherche reformatés en liste (champ → valeur) au lieu d'un paragraphe continu
- Terminologie mise à jour suite à la séparation Catégorie / Versant

## [1.0.2] — 2026-09-05

### Corrections

- Le bit exécutable de `lancer.sh` était perdu à chaque mise à jour automatique (permissions non conservées lors de l'extraction de l'archive) — corrigé, avec un contournement documenté dans le README pour une installation déjà touchée (`chmod +x lancer.sh`)

### Interface

- Bandeau de navigation plus compact, avec une taille minimale garantie
- Écran Sources fusionné dans Paramètres (carte en haut de l'écran)
- Aide déplacée en fin de bandeau
- Filtres Catégorie et Versant séparés en deux sections distinctes
- Sections du panneau de recherche toujours dépliées (plus de repli/dépli)
- Management et Télétravail regroupés sur la même ligne
- Localisation(s) et Organisation(s) côte à côte, qui repassent l'une sous l'autre si la fenêtre est trop étroite
- Boutons de sélection (Domaine, Localisation, Organisation, Grade) redimensionnés à leur contenu au lieu d'occuper toute la largeur du panneau
- Titres des cartes (Aide, Paramètres) mieux centrés sur leur filet
- La taille du texte respecte désormais les préférences d'affichage du système, au lieu d'une taille fixe
- Le panneau de filtres ne peut plus être réduit à zéro par erreur, et la fenêtre a une taille minimale

### Documentation

- Instructions d'installation d'uv séparées par système d'exploitation dans le README

## [1.0.1] — 2026-09-04

### Technique

- Migration vers Python 3.14

### Corrections

- Message d'erreur clair (au lieu d'un plantage) quand choisirleservicepublic.gouv.fr est indisponible

### Interface

- La carte de mise à jour de l'écran Paramètres est désormais toujours visible (version installée si à jour, version disponible sinon)

## [1.0.0] — 2026-09-04

Version initiale.

- Recherche multi-source : choisirleservicepublic.gouv.fr, emploi-territorial.fr, Passerelles/MEF, FHF
- Profils de recherche sauvegardés
- Suivi de candidature
- Mise à jour automatique

[1.0.5]: https://codeberg.org/Kwaite/tamponne/compare/v1.0.4...v1.0.5
[1.0.4]: https://codeberg.org/Kwaite/tamponne/compare/v1.0.3...v1.0.4
[1.0.3]: https://codeberg.org/Kwaite/tamponne/compare/v1.0.2...v1.0.3
[1.0.2]: https://codeberg.org/Kwaite/tamponne/compare/v1.0.1...v1.0.2
[1.0.1]: https://codeberg.org/Kwaite/tamponne/compare/v1.0.0...v1.0.1
[1.0.0]: https://codeberg.org/Kwaite/tamponne/releases/tag/v1.0.0
