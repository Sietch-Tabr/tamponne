"""Constantes statiques des filtres de recherche."""

import re

from src.types import FiltresRecherche, Offre

CATEGORIES: dict[str, int] = {
    "A+ (direction)": 4327,
    "A+ (autres emplois fonctionnels)": 4328,
    "A": 1805,
    "B": 1806,
    "C": 1807,
}

LIBELLES_CATEGORIES: dict[str, str] = {
    "A+ (direction)": "A+ (direction)",
    "A+ (autres emplois fonctionnels)": "A+ (autres)",
    "A": "A",
    "B": "B",
    "C": "C",
}
"""Catégorie (clé de `CATEGORIES`) → libellé court du formulaire et des fiches."""


def categorie_normalisee(valeur: str) -> str:
    """Clé de `CATEGORIES` d'une catégorie enregistrée, y compris sous son
    libellé court (fiches classées avant la séparation clé / libellé)."""
    for cle, libelle in LIBELLES_CATEGORIES.items():
        if valeur == libelle:
            return cle
    return valeur


VERSANTS: dict[str, int] = {
    "etat": 2456,
    "hospitalier": 2457,
    "territorial": 2458,
}

LABELS_VERSANTS: dict[str, str] = {
    "etat": "Fonction publique de l'État",
    "hospitalier": "Fonction publique Hospitalière",
    "territorial": "Fonction publique Territoriale",
}

LABELS_VERSANTS_ABREGES: dict[str, str] = {
    "etat": "FPE",
    "hospitalier": "FPH",
    "territorial": "FPT",
}

TYPES_POSTE: dict[str, int] = {
    "titulaire-contractuel": 2349,
    "titulaire": 4534,
    "contractuel": 2267,
}

# Par défaut : postes accessibles aux titulaires
TYPES_POSTE_DEFAUT: list[int] = [
    TYPES_POSTE["titulaire"],
    TYPES_POSTE["titulaire-contractuel"],
]

DOMAINES: dict[str, int] = {
    "Achat": 3503,
    "Affaires juridiques": 3504,
    "Agriculture": 3505,
    "Aménagement et développement durable du territoire": 3506,
    "Animation, jeunesse et sports": 3507,
    "Bâtiment": 3508,
    "Communication": 3509,
    "Culture et Patrimoine": 3510,
    "Défense": 3511,
    "Direction et pilotage des politiques publiques": 3512,
    "Enseignement et Formation": 3513,
    "Environnement": 3514,
    "Finances Publiques": 3515,
    "Gestion budgétaire et financière": 3516,
    "International": 3517,
    "Interventions techniques et logistiques": 3520,
    "Justice": 3518,
    "Lecture publique et Documentation": 3519,
    "Médical et paramédical": 3521,
    "Numérique": 3522,
    "Organisation, contrôle et évaluation": 3523,
    "Prévention, conseil et pilotage en santé": 3524,
    "Recherche": 3525,
    "Relation à l'usager": 3526,
    "Renseignement": 3527,
    "Ressources Humaines": 3528,
    "Sécurité": 3529,
    "Social, enfance et famille": 3530,
    "Transports": 3531,
}

LOCALISATIONS: dict[str, int] = {
    "Ain": 330,
    "Aisne": 317,
    "Allier": 243,
    "Alpes Hte Provence": 324,
    "Alpes Maritimes": 325,
    "Ardèche": 331,
    "Ardennes": 264,
    "Ariège": 302,
    "Aube": 265,
    "Aude": 290,
    "Auvergne-Rhône-Alpes": 198,
    "Aveyron": 303,
    "Bas Rhin": 236,
    "Belfort": 276,
    "Bouches du Rhône": 326,
    "Bourgogne-Franche-Comté": 200,
    "Bretagne": 201,
    "Calvados": 247,
    "Cantal": 244,
    "Centre - Val de Loire": 202,
    "Charente": 320,
    "Charente Maritime": 321,
    "Cher": 258,
    "Corse": 204,
    "Corse du Sud": 268,
    "Côtes d Armor": 254,
    "Corrèze": 295,
    "Creuse": 296,
    "Deux Sèvres": 322,
    "DOM": 205,
    "Dordogne": 238,
    "Doubs": 277,
    "Drôme": 332,
    "Essonne": 282,
    "Eure": 280,
    "Eure et Loir": 259,
    "Finistère": 255,
    "Gard": 291,
    "Gers": 304,
    "Gironde": 239,
    "Grand Est": 196,
    "Guadeloupe": 270,
    "Guyane": 271,
    "Haut Rhin": 237,
    "Haute Corse": 269,
    "Haute Garonne": 305,
    "Haute Loire": 245,
    "Haute Savoie": 333,
    "Haute Saône": 278,
    "Haute Vienne": 297,
    "Haute-Marne": 266,
    "Hautes Alpes": 327,
    "Hautes Pyrénées": 306,
    "Hauts de France": 213,
    "Hauts-de-Seine": 283,
    "Hérault": 292,
    "Ille et Vilaine": 256,
    "Ile-de-France": 208,
    "Indre": 260,
    "Indre et Loire": 261,
    "Isère": 334,
    "Jura": 279,
    "Landes": 240,
    "Loir et Cher": 262,
    "Loire": 335,
    "Loire Atlantique": 312,
    "Loiret": 263,
    "Lot": 307,
    "Lot et Garonne": 241,
    "Lozère": 293,
    "Maine et Loire": 313,
    "Manche": 248,
    "Marne": 267,
    "Martinique": 272,
    "Mayenne": 314,
    "Mayotte": 273,
    "Meurthe et Moselle": 298,
    "Meuse": 299,
    "Morbihan": 257,
    "Moselle": 300,
    "Nièvre": 251,
    "Nord": 310,
    "Normandie": 199,
    "Nouvelle Aquitaine": 197,
    "Nouvelle Calédonie": 338,
    "Occitanie": 209,
    "Oise": 318,
    "Orne": 249,
    "Paris": 284,
    "Pas de Calais": 311,
    "Pays de La Loire": 214,
    "Puy de Dôme": 246,
    "Pyrénées Atlantiques": 242,
    "Pyrénées Orientales": 294,
    "Réunion": 274,
    "Rhône": 336,
    "Saône et Loire": 252,
    "Sarthe": 315,
    "Savoie": 337,
    "Seine Maritime": 281,
    "Seine Saint-Denis": 286,
    "Seine et Marne": 285,
    "Somme": 319,
    "Tarn": 308,
    "Tarn et Garonne": 309,
    "Val d'Oise": 288,
    "Val de Marne": 287,
    "Var": 328,
    "Vaucluse": 329,
    "Vendée": 316,
    "Vienne": 323,
    "Vosges": 301,
    "Yvelines": 289,
    "Yonne": 253,
}

# Regex de détection des grades supérieurs (IDiv, IP*, AFIPA)
RE_GRADE_SUPERIEUR = re.compile(r"^(IDIV|AFIPA?|IP[A-Z\s\-\(])", re.IGNORECASE)

CORPS_GRADES: dict[str, dict[str, re.Pattern[str]]] = {
    # Décret n°2011-1317 du 17 octobre 2011, article 4.
    "Attaché": {
        "Attaché": re.compile(
            r"attaché(?!\s+(principal|hors[\s-]classe))", re.IGNORECASE
        ),
        "Attaché principal": re.compile(r"attaché\s+principal", re.IGNORECASE),
        "Attaché hors classe": re.compile(r"attaché\s+hors[\s-]classe", re.IGNORECASE),
    },
    # Décret n°2006-1760 du 23 décembre 2006, article 4. « 1re classe » jamais
    # observé dans les offres réelles, construit par symétrie avec « 2e classe ».
    "Adjoint administratif": {
        "Adjoint administratif": re.compile(
            # « s? » dans la négation : sans lui, le moteur contourne le pluriel
            # (« adjoints administratifs principal » matchait à tort, vérifié).
            r"adjoints?\s+administratifs?(?!s?\s+principal)",
            re.IGNORECASE,
        ),
        "Adjoint administratif principal de 2e classe": re.compile(
            r"adjoints?\s+administratifs?\s+principal(e)?s?\s+(de\s+)?2\s*[eèé]?(me)?\s*classe",
            re.IGNORECASE,
        ),
        "Adjoint administratif principal de 1re classe": re.compile(
            r"adjoints?\s+administratifs?\s+principal(e)?s?\s+(de\s+)?1\s*[eèé]?re\s*classe",
            re.IGNORECASE,
        ),
    },
}
"""Grades reconnus par mots-clés dans le titre, regroupés par corps.

Best-effort : aucune source n'expose ce niveau de granularité côté serveur
(voir RECHERCHES.md §5, mêmes limites que `RE_GRADE_SUPERIEUR`). Une seule
table sert les 3 versants : les intitulés longs embarquent le nom court du
grade (« Attaché principal d'administration de l'État » contient « attaché
principal »).

Corps retenus après croisement avec ~470 intitulés réels du site :
Secrétaire administratif et Rédacteur territorial, bien que statutaires,
n'apparaissent quasiment jamais tels quels dans les titres et ne sont pas
couverts. Chaque corps cite son décret en commentaire.
"""

GRADES: dict[str, re.Pattern[str]] = {
    grade: motif
    for grades_du_corps in CORPS_GRADES.values()
    for grade, motif in grades_du_corps.items()
}


def filtrer_par_grades(offres: list[Offre], grades: list[str]) -> list[Offre]:
    """Ne garde que les offres dont le titre correspond à au moins un grade
    sélectionné (OR) — liste vide = pas de filtre."""
    if not grades:
        return offres
    motifs = [GRADES[g] for g in grades if g in GRADES]
    return [o for o in offres if any(m.search(o["titre"]) for m in motifs)]


EXPERIENCES: dict[str, int] = {
    "Débutant": 1835,
    "Confirmé": 1834,
    "Expert": 1833,
}

DATES_PUBLICATION: dict[str, str] = {
    "Dernières 48 heures": "dernieres_48_heures",
    "7 derniers jours": "7_derniers_jours",
    "14 derniers jours": "14_derniers_jours",
}

# Valeur fixe envoyée par les filtres à bascule (toggle) du site : management, télétravail
VALEUR_TOGGLE_ACTIF = 1814


def resumer_filtres(filtres: FiltresRecherche) -> str:
    """Construit une chaîne lisible résumant les filtres actifs.

    Logique d'affichage indépendante de toute bibliothèque d'UI —
    utilisée par la GUI (`src/gui/`).
    """
    parties = []
    if cats := filtres.get("categories"):
        parties.append("Cat." + "+".join(cats))
    if d := filtres.get("domaines"):
        parties.append(d[0] + (f" +{len(d)-1}" if len(d) > 1 else ""))
    if locs := filtres.get("localisations"):
        parties.append(locs[0] + (f" +{len(locs)-1}" if len(locs) > 1 else ""))
    if orgs := filtres.get("organisations"):
        label = orgs[0].split(" - ")[-1]
        parties.append(label + (f" +{len(orgs)-1}" if len(orgs) > 1 else ""))
    versants = filtres.get("versants") or []
    if not versants:
        parties.append("tous versants")
    elif len(versants) == 1:
        parties.append(LABELS_VERSANTS.get(versants[0], versants[0]))
    else:
        parties.append("+".join(LABELS_VERSANTS_ABREGES.get(v, v) for v in versants))
    if exp := filtres.get("experience"):
        parties.append(exp)
    if date_pub := filtres.get("date_publication"):
        parties.append(date_pub)
    if filtres.get("management"):
        parties.append("Management")
    if filtres.get("teletravail"):
        parties.append("Télétravail")
    if query := filtres.get("query"):
        parties.append(f'"{query}"')
    return " · ".join(parties) if parties else "aucun filtre"
