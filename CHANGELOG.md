# Historique des versions

Toutes les évolutions notables de Tamponné, de la plus récente à la plus
ancienne. Le détail de chaque version est aussi publié sur la page
[Releases](https://codeberg.org/Kwaite/tamponne/releases) du dépôt.

## [1.4.1] — 2026-10-15

### Corrections

- Aide : la rubrique « Grades supérieurs de la DGFiP » explique les sigles (IDIV, IP, AFIP, AFIPA) et pourquoi ces offres sont masquées par défaut

## [1.4.0] — 2026-10-15

### Nouveautés

- Réglages : nouvelle feuille « Maintenance » qui indique le nombre et la taille des exports de recherche, avec de quoi ouvrir leur dossier ou les supprimer tous (après confirmation)
- Réglages : la date de mise en cache de la liste des organisations s'affiche sous « Rafraîchir le cache »
- Journal `data/tamponne.log` : conservé d'un lancement à l'autre, avec l'heure et le détail de chaque erreur (source injoignable, mise à jour, sauvegarde…) ; archivé au-delà de 1 Mo, à joindre à un signalement
- Aide complète : recherche et registre, sources consultées (cases comprises par chaque site), fiches, suivi, réglages, raccourcis et emplacement des données
- Le bouton « Classer en profil » devient « Créer une fiche »
- Registre : le numéro des offres s'adapte à leur nombre (« 01 » à « 28 » au lieu de « 001 »)

### Corrections

- Les certificats HTTPS sont vérifiés par le système, comme le navigateur : cible l'erreur « certificate verify failed » de Passerelles sous Windows derrière un proxy d'entreprise
- Grades supérieurs : un titre qui commence par « Ip » suivi d'une minuscule n'est plus écarté à tort
- Aide corrigée (catégories, type de poste, mot-clé, clavier du suivi)

### En coulisses

- `src/` et `tests/` rangés par paquets (données, recherche, système, interface), avec un test qui fige les dépendances entre composants
- Nouvelle dépendance : `truststore`

## [1.3.4] — 2026-10-13

### Fiches détaillées (emploi-territorial, FHF, Passerelles)

- Les fiches gardent la mise en forme du site : retours à la ligne, paragraphes, listes à puces (compétences, grades recherchés…) au lieu d'un seul bloc de texte
- FHF : la date limite de candidature apparaît, et la date de publication n'est plus collée à son libellé
- FHF : les adresses e-mail de contact s'affichent en clair au lieu de « [email protected] »
- « Voir la copie archivée » et « Consulter en ligne » n'apparaissent plus quand ils ne mènent à rien

## [1.3.3] — 2026-10-13

### Corrections

- Les offres d'emploi-territorial, de FHF et de Passerelles suivies ou ouvertes en détail ont enfin leur fiche complète (description, dates, contact…) : seule choisirleservicepublic était lue jusqu'ici, les autres restaient vides
- « Vérifier les offres » reconnaît désormais une offre retirée sur toutes les sources (page introuvable, page « Offre dépubliée », retour à l'accueil de Passerelles), et plus seulement sur choisirleservicepublic
- Une source qui répond trop lentement ou dans un format imprévu est signalée comme indisponible au lieu de faire échouer toute la recherche
- L'export HTML porte un titre fidèle aux quatre sources

### Sécurité

- Le nom du PDF archivé ne peut plus sortir du dossier des archives, quelle que soit la référence donnée par un site
- Les mises à jour ne sont téléchargées que depuis le dépôt Codeberg de Tamponné, avec un délai d'attente
- Le message d'erreur du lancement Windows n'affiche plus l'identifiant ni le mot de passe éventuels du proxy, et le journal du lancement remplace le chemin du dossier personnel par `~`
- README : nouvelles sections « En cas de problème » et « Sécurité et confidentialité »

## [1.3.2] — 2026-10-12

### Plus rien de caché

- Réglages › Avis de mise à jour : quand Codeberg ne répond pas (connexion internet ou proxy), l'avis le dit, avec le détail de l'erreur, au lieu d'annoncer « rien de plus récent » ; le tampon « À jour » n'apparaît que si c'est confirmé, et « recherche d'une mise à jour… » s'affiche pendant la vérification
- Une mise à jour qui n'a pas pu être téléchargée l'annonce au lancement (avec le détail) au lieu de redémarrer en silence dans l'ancienne version ; elle n'est plus retentée en silence à chaque lancement et Réglages permet de réessayer
- Suivi : les offres que « Vérifier les offres » n'a pas pu consulter (site qui ne répond pas) sont signalées sous le titre, avec le détail de l'erreur

## [1.3.1] — 2026-10-12

### Mise à jour

- Si une mise à jour ne s'installe pas ou ne démarre pas, Tamponné revient tout seul à la version précédente : vos données restent intactes et un message explique ce qui s'est passé
- La mise à jour qui a échoué n'est plus retentée à chaque lancement : Réglages › Avis de mise à jour en donne la raison, et « Installer et redémarrer » permet de réessayer
- uv, le gestionnaire de Python de Tamponné, se met à jour de lui-même quand il est trop ancien pour la version de Python demandée, y compris derrière un proxy (cause du blocage de la 1.3.0 sous Windows)
- Le téléchargement de Python et des composants s'affiche au fil de l'eau, au lancement comme après une mise à jour (sous Windows, dans une fenêtre ouverte le temps du téléchargement) : plus d'attente devant un écran vide
- Les messages d'erreur au lancement disent quoi faire et donnent le détail technique de l'erreur ; le journal du dernier lancement est enregistré dans `data/journal_lancement.log`, à joindre à un signalement

## [1.3.0] — 2026-10-12

### Installation

- Tamponné fonctionne désormais avec Python 3.15 et PySide6 6.12 : au premier lancement après la mise à jour, la nouvelle version de Python et les composants sont téléchargés une fois

### Démarrage

- Ouverture plus rapide : les modules réseau et d'analyse des pages ne sont chargés qu'à la première recherche

## [1.2.3] — 2026-10-06

### Installation

- Le zip publié ne contient plus les fichiers de développement (tests, outils, maquette, captures, notes techniques) ; ils sont retirés des installations existantes au prochain lancement
- Les outils de développement (mypy, pytest) ne sont plus installés avec Tamponné et sont retirés des installations existantes
- À la fin de l'installation, un message invite à patienter pendant la première ouverture (Windows : la console reste ouverte quelques secondes)

### Démarrage

- La fenêtre s'ouvre sans attendre le site : la liste des organisations est chargée en arrière-plan quand elle est absente ou a plus de 7 jours, l'ancienne servant en attendant
- Tant que la liste n'est pas chargée, la ligne Organisations du formulaire l'indique (« chargement… ») et une recherche filtrée par organisation est refusée au lieu d'ignorer ce filtre
- Réglages › Classement : titre « Liste des organisations » au-dessus du bouton « Rafraîchir le cache »

## [1.2.2] — 2026-10-06

### Corrections

- Windows : derrière un proxy d'entreprise, le premier lancement télécharge Python et les composants au lieu d'échouer (« Hôte inconnu ») ; le proxy configuré dans Windows est détecté à chaque lancement et utilisé aussi pour les recherches et la mise à jour

## [1.2.1] — 2026-10-05

### Corrections

- Linux : lancé par double-clic (KDE, GNOME), le premier lancement s'ouvre dans un terminal pour montrer l'installation de uv et des composants ; en cas d'erreur, le terminal reste ouvert jusqu'à Entrée
- Sur un petit écran (portable), la fenêtre s'ouvre agrandie au lieu de déborder
- Windows : l'avertissement de sécurité ne s'affiche plus qu'au premier lancement (marque du Web retirée des fichiers de Tamponné)
- Windows : l'icône de Tamponné s'affiche dans la barre des tâches au lieu de celle de Python
- Windows : la console du lanceur se ferme une fois Tamponné ouvert (la fermer ne ferme plus l'application) ; les erreurs s'affichent dans une boîte de dialogue
- Créer, mettre à jour ou retirer le raccourci ne fige plus l'interface pendant quelques secondes (Windows)

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
