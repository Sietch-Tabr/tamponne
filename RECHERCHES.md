# Recherches et analyses — Choisir le Service Public

## Objectif

Automatiser la recherche d'offres d'emploi de la fonction publique sur
`choisirleservicepublic.gouv.fr` sans passer par le site manuellement.

**Architecture actuelle** : application interactive (questionary + rich), profils de
recherche sauvegardés, cache organisations avec TTL, export HTML cliquable.

---

## 1. Exploration des sources de données

### data.gouv.fr — CSV officiel

- Dataset ID : `6322e99e12175f7eb26ff465`
- URL API : `https://www.data.gouv.fr/api/1/datasets/6322e99e12175f7eb26ff465/`
- Dernier fichier : `offres-datagouv-20260301.csv` (~27 Mo), mis à jour le 09/03/2026
- Licence : Licence Ouverte v2.0 (réutilisation libre)
- Colonnes utiles : `Organisme de rattachement`, `Référence`, `Versant`, `Métier`,
  `Intitulé du poste`, `Localisation du poste`, `Lieu d'affectation`, `Catégorie`,
  `Date de vacance de l'emploi`, `Date de première publication`
- Fréquence de mise à jour : hebdomadaire
- Limite : décalage d'une semaine maximum par rapport au site

### API WordPress REST — namespace custom `api`

- URL racine : `https://choisirleservicepublic.gouv.fr/wp-json/api/`
- Endpoints découverts :
  - `GET  /api/employeur` — liste des employeurs
  - `GET  /api/employeur/{id}` — détail d'un employeur
  - `POST /api/offer-list` — liste d'offres (pagination uniquement, **les filtres sont ignorés**)
  - `POST /api/employeurs_elasticsearch` — recherche d'employeurs
- Conclusion : l'endpoint `offer-list` n'applique pas les filtres envoyés dans le body JSON.
  Il retourne toujours les 51 996 offres sans tri. **Non utilisable pour filtrer.**

### admin-ajax.php — endpoint réel de recherche

- URL : `https://choisirleservicepublic.gouv.fr/wp-admin/admin-ajax.php`
- Méthode : POST, `Content-Type: application/x-www-form-urlencoded`
- **C'est cet endpoint que le site utilise réellement** (découvert en lisant le chunk
  webpack `searchOffer.js`)

Paramètres requis :

| Paramètre     | Type   | Description                                      |
| ------------- | ------ | ------------------------------------------------ |
| `action`      | string | Toujours `get_offers`                            |
| `nonce`       | string | Token anti-CSRF, récupéré depuis le HTML du site |
| `query`       | string | Mot-clé libre (peut être vide)                   |
| `rewrite_url` | string | URL de la page de résultats (cosmétique)         |
| `filters`     | JSON   | Objet de filtres (voir structure ci-dessous)     |

Structure du JSON `filters` :

```json
{
  "keywords": [],
  "date": [],
  "contenu": [],
  "thematique": [],
  "geoloc": [],
  "locations": [284],
  "domains": [3522],
  "versants": [],
  "categories": [1805],
  "organisations": [10736],
  "jobs": [],
  "managements": [],
  "remotes": [],
  "experiences": [],
  "search_order": ""
}
```

Réponse JSON :

```json
{
  "html": "<div>...cartes d'offres en HTML...</div>",
  "action": "get_offers",
  "title": "Offres d'emploi (page 1 sur N) | Choisir le service public"
}
```

---

## 2. Reverse engineering du frontend

### Architecture

- Site WordPress avec thème custom `biep`
- Frontend compilé avec **webpack** (lazy-loading via `conditioner-core`)
- Fichier principal : `/wp-content/themes/biep/assets/js/app.js` (~984 Ko)
- Modules chargés à la demande depuis `/wp-content/themes/biep/assets/js/chunks/`

### Module de recherche

- Fichier source : `./assets/js/modules/components/searchOffer.js`
- Chunk webpack : `be26f351d3a5b1a0e164.js` (111 Ko)
- Logique : construit un `FormData`, l'envoie via `XMLHttpRequest` à `admin-ajax.php`
- Le nonce est lu depuis `window.ParamsDataSearch.nonce`, injecté dans le HTML par PHP

### Mapping URL ↔ paramètres internes

Extrait depuis `window.ParamsDataSearch.url_keywords` dans le HTML :

| Paramètre interne | Paramètre URL  |
| ----------------- | -------------- |
| `keywords`        | `mot-cles`     |
| `locations`       | `localisation` |
| `domains`         | `domaine`      |
| `versants`        | `versant`      |
| `categories`      | `categorie`    |
| `organisations`   | `organisme`    |
| `jobs`            | `type`         |
| `managements`     | `management`   |
| `remotes`         | `teletravail`  |
| `experiences`     | `experience`   |

---

## 3. IDs des filtres

Extraits depuis le formulaire HTML de `/nos-offres/` (inputs `js-search-input`
avec attributs `data-slug` et `value`).

### Catégories

| Valeur | ID        | Notes                                                                                                                                  |
| ------ | --------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| A      | 1805      |                                                                                                                                        |
| A+     | 4327-4328 | Valeur composite (deux sous-IDs : 4327 et 4328) — le formulaire HTML a `value="4327-4328"`. Le regex `\d+` ne matche pas cette valeur. |
| B      | 1806      |                                                                                                                                        |
| C      | 1807      |                                                                                                                                        |

Note : la catégorie A inclut les grades IDiv (Inspecteur Divisionnaire) et IP (Inspecteur
Principal), qui sont techniquement des grades A mais des emplois de niveau supérieur.
Ces offres sont retournées par le filtre `categories: [1805]`. Voir section 6 pour
les stratégies d'exclusion.

### Types de poste

| Type de poste            | ID   |
| ------------------------ | ---- |
| Titulaire et contractuel | 2349 |
| Titulaire uniquement     | 4534 |
| Contractuel uniquement   | 2267 |

Ces IDs correspondent au paramètre `jobs` dans le JSON `filters`.
Le paramètre accepte un tableau multi-valeurs (confirmé) : `jobs: [4534, 2349]` est valide.

**Comportement par défaut du script** : `jobs: [4534, 2349]` — postes accessibles aux
titulaires (titulaire seul + titulaire/contractuel). Les offres contractuels uniquement
sont exclues. Flag `--inclure-contractuels` pour désactiver.

---

### Versants

| Versant                        | ID   |
| ------------------------------ | ---- |
| Fonction Publique de l'Etat    | 2456 |
| Fonction Publique Hospitalière | 2457 |
| Fonction Publique Territoriale | 2458 |

**Comportement par défaut du script** : `versants: [2456]` — FPE uniquement.
Flag `--tous-versants` pour désactiver et inclure tous les versants.
Flag `--versant hospitalier|territorial` pour sélectionner un versant spécifique.

### Domaines métier (liste complète)

| Domaine                                            | ID       |
| -------------------------------------------------- | -------- |
| Achat                                              | 3503     |
| Affaires juridiques                                | 3504     |
| Agriculture                                        | 3505     |
| Aménagement et développement durable du territoire | 3506     |
| Animation, jeunesse et sports                      | 3507     |
| Bâtiment                                           | 3508     |
| Communication                                      | 3509     |
| Culture et Patrimoine                              | 3510     |
| Défense                                            | 3511     |
| Direction et pilotage des politiques publiques     | 3512     |
| Enseignement et Formation                          | 3513     |
| Environnement                                      | 3514     |
| Finances Publiques                                 | 3515     |
| Gestion budgétaire et financière                   | 3516     |
| International                                      | 3517     |
| Interventions techniques et logistiques            | 3520     |
| Justice                                            | 3518     |
| Lecture publique et Documentation                  | 3519     |
| Médical et paramédical                             | 3521     |
| **Numérique**                                      | **3522** |
| Organisation, contrôle et évaluation               | 3523     |
| Prévention, conseil et pilotage en santé           | 3524     |
| Recherche                                          | 3525     |
| Relation à l'usager                                | 3526     |
| Renseignement                                      | 3527     |
| Ressources Humaines                                | 3528     |
| Sécurité                                           | 3529     |
| Social, enfance et famille                         | 3530     |
| Transports                                         | 3531     |

### Organisations — Ministère de l'Agriculture (extraites)

| Organisation            | ID    |
| ----------------------- | ----- |
| Administration centrale | 10736 |
| DAAF                    | 13857 |

Note : le site présente les organisations sur deux niveaux. Le niveau 1
(Ministère) n'a pas d'ID propre utilisable dans le filtre `organisations` —
seules les sous-organisations (niveau 2) fonctionnent. Pour les autres ministères,
il faut extraire leurs IDs de la même façon (voir section 4).

### Localisations — sélection Île-de-France

| Département                    | ID  |
| ------------------------------ | --- |
| Paris                          | 284 |
| Hauts-de-Seine                 | 283 |
| Seine-Saint-Denis              | 286 |
| Seine et Marne                 | 285 |
| Val de Marne                   | 287 |
| Val d'Oise                     | 288 |
| Essonne                        | 282 |
| Yvelines                       | 289 |
| Île-de-France (région entière) | 208 |

---

## 4. Structure HTML des organisations — cache automatique

Les organisations sont désormais scrappées automatiquement par `src/cache.py`
au premier lancement (TTL 7 jours). **L'extraction manuelle n'est plus nécessaire.**

### Structure HTML découverte

Deux niveaux d'`<input>` dans `/nos-offres/` :

**Niveau 1 — Ministère (parent)** : présence de `data-has-children`, `id` dynamique (hash de session)

```html
<input
  data-desc="Ministère de l'Agriculture..."
  class="js-search-input"
  type="checkbox"
  id="organisations-checkbox-HASH"
  data-slug="organisations"
  value="PARENT_ID"
  data-has-children
/>
```

**Niveau 2 — Sous-organisation (enfant)** : présence de `data-parent` référençant l'`id` du parent.
**Attention** : `data-parent` apparaît **avant** `data-slug` dans le HTML.

```html
<input
  data-desc="Administration centrale"
  class="js-search-input"
  type="checkbox"
  data-parent="organisations-checkbox-HASH"
  value="10736"
  data-slug="organisations"
/>
```

Les `id` de hash changent à chaque session PHP — le scraper mappe par `id` dans la même requête.

### Statistiques (relevé 10/03/2026)

- 26 ministères / groupes d'employeurs
- ~2 369 sous-organisations au total
- Groupes importants : Centres Hospitaliers (~600), FPH (~100+)

### Cache `data/cache.json`

```json
{
  "organisations": {
    "cached_at": "2026-03-10T21:57:38+00:00",
    "data": {
      "Ministère de l'Agriculture...": {
        "Administration centrale": 10736,
        "DAAF": 13857
      }
    }
  }
}
```

Rafraîchissement : menu `Organisations → Rafraîchir` dans l'application.

---

## 5. Exclusion des offres IDiv / IP

### Contexte

Le filtre `categories: [1805]` (catégorie A) remonte aussi des offres réservées aux
grades **IDiv** (Inspecteur Divisionnaire) et **IP** (Inspecteur Principal). Ces grades
sont des emplois supérieurs de catégorie A, donc techniquement inclus, mais inaccessibles
aux fonctionnaires A standard.

Ces offres sont identifiables car leur **titre** commence généralement par `IDIV` ou `IP`
(souvent en majuscules dans le titre de l'offre).

Exemples d'offres IDiv confirmées :

- `https://choisirleservicepublic.gouv.fr/offre-emploi/idiv-hc--ap----pgpspl---mission-regionale-de-conseil-aux-decideurs-publics----charge-de-mission--hf-reference-MEF_2026-28138/`
- `https://choisirleservicepublic.gouv.fr/offre-emploi/idiv-cnap---adjointe-au-responsable-du-pole-d-evaluation-domaniale-ped-hf-reference-MEF_2026-29121/`

### Implémentation (approche A — active par défaut)

Filtre post-traitement sur le titre extrait depuis la carte d'offre :

```python
PREFIXES_GRADES_SUPERIEURS = ("IDIV", "IP ", "IP-", "IP(")

def est_grade_superieur(titre: str) -> bool:
    titre_maj = titre.upper()
    return any(titre_maj.startswith(p) for p in PREFIXES_GRADES_SUPERIEURS)
```

Le script filtre automatiquement après `extraire_offres()` et affiche un compteur :
`"N offre(s) IDiv/IP exclues par filtre de titre."`.

Limites : peut rater des offres IDiv dont le titre ne commence pas par `IDIV`/`IP`.
Une approche B (fetch page de détail) a été envisagée mais jugée superflue pour l'instant.

---

## 6. Interface — application interactive (historique, CLI retiré)

> Cette section décrit le CLI (questionary + rich) tel qu'il existait
> avant son retrait au profit d'une interface graphique (PySide6),
> conservée pour mémoire — voir `CLAUDE.md` pour l'architecture
> actuelle. `recherche_offres.py` n'existe plus.

```bash
./lancer.sh                      # uv sync + lancement de la GUI
```

### Arbre des menus

```
[Accueil]
  ├── <Profil 1 — résumé filtres>  →  Lancer | Modifier | Dupliquer | Supprimer
  ├── + Nouvelle recherche         →  [Wizard recherche]
  ├── Actualiser la liste des ministères
  └── Quitter

[Wizard recherche]
  1. Catégorie(s)      checkbox  A / B / C
  2. Domaine(s)        checkbox  liste complète
  3. Localisation(s)   checkbox  MULTI — liste complète
  4. Ministère(s)      checkbox  → puis sous-organisations MULTI
  5. Versant           select    FPE (défaut) | Hospitalier | Territorial | Tous
  6. Type de poste     select    Titulaire-éligible (défaut) | Titulaire | Contractuel | Tous
  7. Mot-clé libre     text      optionnel

[Résultats]
  rich : tableau 20 offres + résumé filtres
  ├── Exporter en HTML  →  exports/nom_YYYYMMDD_HHMMSS.html
  │     └── Ouvrir dans le navigateur
  ├── Sauvegarder comme profil  (si recherche ponctuelle)
  └── Retour au menu principal
```

### Comportements par défaut (conservés)

- **Versant** : FPE uniquement (`versants: [2456]`)
- **Type de poste** : titulaire-éligible (`jobs: [4534, 2349]`)
- **Grades IDiv/IP** : exclus automatiquement par filtre de titre

### Profils sauvegardés

Stockés dans `data/profils.json` (versionnable). Format :

```json
{
  "dgal-paris": {
    "label": "DGAL Paris — Numérique",
    "categories": ["A"],
    "domaines": ["Numérique"],
    "localisations": ["Paris", "Hauts-de-Seine"],
    "organisations": [
      "Ministère de l'Agriculture... - Administration centrale"
    ],
    "versant": "etat",
    "types_poste": null,
    "query": "",
    "cree_le": "2026-03-10"
  }
}
```

---

## 7. Pagination — analyse complète (2026-03-15)

### admin-ajax.php ne pagine pas

L'endpoint `POST /wp-admin/admin-ajax.php` avec `action=get_offers` retourne
**toujours la page 1** quel que soit le paramètre de pagination envoyé.

Variantes testées (toutes échouent — même `ref[0]`, `page 1 sur 16`) :

| Paramètre testé                               | Résultat |
| --------------------------------------------- | -------- |
| `rewrite_url=/nos-offres/page/2/`             | page 1   |
| `rewrite_url=/nos-offres/filtres/.../page/2/` | page 1   |
| `paged=2` dans `filters` JSON                 | page 1   |
| `page=2` + `offset=20` dans `filters` JSON    | page 1   |

Le `rewrite_url` est cosmétique : il met à jour la barre d'adresse du navigateur
via `pushState` côté JS. Il ne contrôle pas la pagination côté serveur.

### Pagination réelle : GET sur les URLs WordPress rewrite

Format découvert par analyse de `searchOffer.js` et tests directs :

```
Page 1 : GET /nos-offres/filtres/localisation/284/domaine/3522/versant/2456/categorie/1805/type/4534-2349/
Page 2 : GET /nos-offres/filtres/localisation/284/domaine/3522/versant/2456/categorie/1805/type/4534-2349/page/2/
```

Règles :

- `/page/N/` se place **après** les filtres, pas avant
- `/page/2/filtres/...` → 404
- `/nos-offres/page/2/` (sans filtres) → retourne toujours page 1

### Mapping paramètres → segments URL (ordre important, issu de `url_keywords` JS)

| Paramètre interne | Segment URL    |
| ----------------- | -------------- |
| `locations`       | `localisation` |
| `domaines`        | `domaine`      |
| `versants`        | `versant`      |
| `categories`      | `categorie`    |
| `organisations`   | `organisme`    |
| `types_poste`     | `type`         |
| `query`           | `mot-cles`     |

IDs multiples séparés par `-` (ex : `type/4534-2349/`).

### Implémentation

`src/sources/choisirleservicepublic/api.py` — `construire_url_filtres()` +
`obtenir_page_offres()` (GET pur, pas de nonce). La pagination multi-pages
est gérée dans `src/sources/choisirleservicepublic/__init__.py` avec
déduplication par `refs_vues` (protection contre la boucle API après dernière page).

---

## 8. Limitations connues

- **Filtre `query` large** : le mot-clé `DGAL` remonte aussi `DGA` (Défense).
  Combiner avec la sélection d'organisation dans le wizard pour affiner.
- **Organisations résolues** : ~~les IDs étaient hardcodés~~ → désormais scrappés
  automatiquement (cache 7 jours). Résolu.
- **Filtre IDiv/IP** : exclusion par préfixe de titre uniquement. Les offres IDiv
  dont le titre ne commence pas par `IDIV`/`IP` peuvent passer. Cas marginal.
- **Nonce** : ~~nécessaire et non cachable~~ → supprimé. La pagination GET ne
  nécessite aucun nonce. Résolu.
