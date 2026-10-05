# Historique des versions

Toutes les évolutions notables de Tamponné, de la plus récente à la plus
ancienne. Le détail de chaque version est aussi publié sur la page
[Releases](https://codeberg.org/Kwaite/tamponne/releases) du dépôt.

## [1.2.1] — 2026-10-05

### Corrections

- Linux : lancé par double-clic (KDE, GNOME), le premier lancement s'ouvre dans un terminal pour montrer l'installation de uv et des composants ; en cas d'erreur, le terminal reste ouvert jusqu'à Entrée
- Sur un petit écran (portable), la fenêtre s'ouvre agrandie au lieu de déborder
- Windows : l'avertissement de sécurité ne s'affiche plus qu'au premier lancement (marque du Web retirée des fichiers de Tamponné)
- Windows : l'icône de Tamponné s'affiche dans la barre des tâches au lieu de celle de Python

## [1.2.0] — 2026-10-05

### Installation

- Plus rien à installer au préalable : télécharger le zip, le dézipper et double-cliquer sur `Tamponne.command` (macOS, Linux) ou `Tamponne.bat` (Windows)
- uv, puis Python et les composants, s'installent tout seuls au premier lancement, avec un message pendant le téléchargement
- En cas d'échec (pas de connexion…), un message en français s'affiche, y compris lancé depuis le raccourci
- Les anciens lanceurs `lancer.sh` et `lancer.bat` sont remplacés et retirés automatiquement

### Raccourci

- Tamponné peut s'ajouter au menu des applications : menu Démarrer (Windows), `~/Applications` (macOS, avec Spotlight et le Dock), menu des applications (Linux)
- Proposé une fois au premier lancement, puis géré dans Réglages › Raccourci
- Si le dossier de Tamponné a été déplacé, la mise à jour du raccourci est proposée au lancement

### Sauvegarde

- Réglages › Sauvegarde : export de toutes les données (fiches, dossiers suivis et leurs PDF, offres vues, réglages) dans un fichier zip
- Import d'une sauvegarde : remplace les données après confirmation, garde une copie des données d'avant, puis redémarre

### Icône

- Nouvelle icône : un T dans un tampon rond, aussi dans le Dock et la barre des tâches

### Maintenance

- La boucle de mise à jour et de redémarrage est désormais en Python (`src/lanceur.py`), testée
- README réécrit pour une installation sans terminal

## [1.1.0] — 2026-10-05

### Nouvelle interface

- Interface entièrement redessinée façon « dossier administratif » : chemise kraft, fiches bristol, registre des offres, dossiers tamponnés
- Bureau de jour et bureau de nuit, en suivant le système ou au choix dans Réglages
- Onglets Profils, Recherche, Suivi, Aide et Réglages, menus Fichier et Aide dans la fenêtre
- Contrastes vérifiés (WCAG AA), navigation au clavier, option « Réduire les animations »
- Typographie française soignée (espaces insécables avant la ponctuation double)

### Recherche

- Formulaire de demande regroupé par cases : catégorie, corps et grade, versant, poste, lieu, options
- Registre des offres : tri par colonne, filtre en direct, tampon « Nouveau » sur les offres jamais vues pour la fiche, filtre « Nouvelles seulement »
- Détail d'une offre consultable sans quitter le registre, suivi d'une offre en un clic (« Tamponner pour suivi »)
- L'export HTML résume les critères de la recherche affichée

### Fiches de recherche

- Une fiche modifiée garde son intitulé
- L'option « Grades supérieurs » est enregistrée avec la fiche et rappelée sur sa carte quand la catégorie A+ est concernée
- La duplication demande aussi l'intitulé de la copie

### Suivi de candidature

- Historique en tampons datés : un clic sur un tampon permet de modifier ou de supprimer l'événement
- Un même événement ne peut plus être ajouté deux fois à la même date
- La date et le type du prochain événement sont proposés d'après l'historique
- Réponse positive en vert, refus en rouge

### Réglages

- Avis de mise à jour avec notes de version, « Installer et redémarrer » ou « Au prochain lancement »
- Sources consultées, thème, réduction des animations, rafraîchissement du cache des organisations

### Corrections

- La catégorie « A+ (autres emplois fonctionnels) » n'était pas transmise aux sites et la recherche portait sur toutes les catégories
- Une recherche lancée depuis une fiche puis modifiée n'est plus comptée pour la fiche

### Mise à jour

- Les fichiers de l'ancienne interface sont retirés automatiquement au premier lancement ; vos données ne sont pas touchées
- Les mises à jour suivantes suppriment aussi les fichiers retirés d'une version à l'autre

### Maintenance

- Dépendances à jour

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
