"""Constantes statiques des filtres de recherche."""

import re
from collections.abc import Iterable, Mapping
from typing import Final

from src.types import FiltresRecherche, Offre

CATEGORIES: Final[Mapping[str, int]] = {
    "A+ (direction)": 4327,
    "A+ (autres emplois fonctionnels)": 4328,
    "A": 1805,
    "B": 1806,
    "C": 1807,
}

LIBELLES_CATEGORIES: Final[Mapping[str, str]] = {
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


VERSANTS: Final[Mapping[str, int]] = {
    "etat": 2456,
    "hospitalier": 2457,
    "territorial": 2458,
}

LABELS_VERSANTS: Final[Mapping[str, str]] = {
    "etat": "Fonction publique de l'État",
    "hospitalier": "Fonction publique Hospitalière",
    "territorial": "Fonction publique Territoriale",
}

LABELS_VERSANTS_ABREGES: Final[Mapping[str, str]] = {
    "etat": "FPE",
    "hospitalier": "FPH",
    "territorial": "FPT",
}

TYPES_POSTE: Final[Mapping[str, int]] = {
    "titulaire-contractuel": 2349,
    "titulaire": 4534,
    "contractuel": 2267,
}

# Par défaut : postes accessibles aux titulaires
TYPES_POSTE_DEFAUT: list[int] = [
    TYPES_POSTE["titulaire"],
    TYPES_POSTE["titulaire-contractuel"],
]

DOMAINES: Final[Mapping[str, int]] = {
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

LOCALISATIONS: Final[Mapping[str, int]] = {
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

NUMEROS_DEPARTEMENTS: Final[Mapping[str, str]] = {
    "Ain": "01",
    "Aisne": "02",
    "Allier": "03",
    "Alpes Hte Provence": "04",
    "Alpes Maritimes": "06",
    "Ardèche": "07",
    "Ardennes": "08",
    "Ariège": "09",
    "Aube": "10",
    "Aude": "11",
    "Aveyron": "12",
    "Bas Rhin": "67",
    "Belfort": "90",
    "Bouches du Rhône": "13",
    "Calvados": "14",
    "Cantal": "15",
    "Charente": "16",
    "Charente Maritime": "17",
    "Cher": "18",
    "Corse du Sud": "2A",
    "Côtes d Armor": "22",
    "Corrèze": "19",
    "Creuse": "23",
    "Deux Sèvres": "79",
    "Dordogne": "24",
    "Doubs": "25",
    "Drôme": "26",
    "Essonne": "91",
    "Eure": "27",
    "Eure et Loir": "28",
    "Finistère": "29",
    "Gard": "30",
    "Gers": "32",
    "Gironde": "33",
    "Guadeloupe": "971",
    "Guyane": "973",
    "Haut Rhin": "68",
    "Haute Corse": "2B",
    "Haute Garonne": "31",
    "Haute Loire": "43",
    "Haute Savoie": "74",
    "Haute Saône": "70",
    "Haute Vienne": "87",
    "Haute-Marne": "52",
    "Hautes Alpes": "05",
    "Hautes Pyrénées": "65",
    "Hauts-de-Seine": "92",
    "Hérault": "34",
    "Ille et Vilaine": "35",
    "Indre": "36",
    "Indre et Loire": "37",
    "Isère": "38",
    "Jura": "39",
    "Landes": "40",
    "Loir et Cher": "41",
    "Loire": "42",
    "Loire Atlantique": "44",
    "Loiret": "45",
    "Lot": "46",
    "Lot et Garonne": "47",
    "Lozère": "48",
    "Maine et Loire": "49",
    "Manche": "50",
    "Marne": "51",
    "Martinique": "972",
    "Mayenne": "53",
    "Mayotte": "976",
    "Meurthe et Moselle": "54",
    "Meuse": "55",
    "Morbihan": "56",
    "Moselle": "57",
    "Nièvre": "58",
    "Nord": "59",
    "Nouvelle Calédonie": "988",
    "Oise": "60",
    "Orne": "61",
    "Paris": "75",
    "Pas de Calais": "62",
    "Puy de Dôme": "63",
    "Pyrénées Atlantiques": "64",
    "Pyrénées Orientales": "66",
    "Réunion": "974",
    "Rhône": "69",
    "Saône et Loire": "71",
    "Sarthe": "72",
    "Savoie": "73",
    "Seine Maritime": "76",
    "Seine Saint-Denis": "93",
    "Seine et Marne": "77",
    "Somme": "80",
    "Tarn": "81",
    "Tarn et Garonne": "82",
    "Val d'Oise": "95",
    "Val de Marne": "94",
    "Var": "83",
    "Vaucluse": "84",
    "Vendée": "85",
    "Vienne": "86",
    "Vosges": "88",
    "Yvelines": "78",
    "Yonne": "89",
}
"""Département (clé de `LOCALISATIONS`) → numéro officiel (« 2A » et « 2B »
pour la Corse, trois chiffres outre-mer)."""

NUMEROS_REGIONS: Final[Mapping[str, tuple[str, ...]]] = {
    "Auvergne-Rhône-Alpes": (
        "01",
        "03",
        "07",
        "15",
        "26",
        "38",
        "42",
        "43",
        "63",
        "69",
        "73",
        "74",
    ),
    "Bourgogne-Franche-Comté": ("21", "25", "39", "58", "70", "71", "89", "90"),
    "Bretagne": ("22", "29", "35", "56"),
    "Centre - Val de Loire": ("18", "28", "36", "37", "41", "45"),
    "Corse": ("2A", "2B"),
    "DOM": ("971", "972", "973", "974", "976"),
    "Grand Est": ("08", "10", "51", "52", "54", "55", "57", "67", "68", "88"),
    "Hauts de France": ("02", "59", "60", "62", "80"),
    "Ile-de-France": ("75", "77", "78", "91", "92", "93", "94", "95"),
    "Normandie": ("14", "27", "50", "61", "76"),
    "Nouvelle Aquitaine": (
        "16",
        "17",
        "19",
        "23",
        "24",
        "33",
        "40",
        "47",
        "64",
        "79",
        "86",
        "87",
    ),
    "Occitanie": (
        "09",
        "11",
        "12",
        "30",
        "31",
        "32",
        "34",
        "46",
        "48",
        "65",
        "66",
        "81",
        "82",
    ),
    "Pays de La Loire": ("44", "49", "53", "72", "85"),
}
"""Région (clé de `LOCALISATIONS`) → numéros de ses départements, y compris
ceux que `LOCALISATIONS` ne propose pas seuls (Côte-d'Or)."""

_RE_NUMERO_ENTRE_PARENTHESES = re.compile(r"\(\s*(\d{2,3}|2[AB])\s*\)", re.IGNORECASE)
_RE_CODE_POSTAL = re.compile(r"\b(\d{5})\b")
_RE_CATEGORIE = re.compile(r"cat[ée]gorie\s+(A\+|A\b|B\b|C\b)", re.IGNORECASE)


def numeros_departements(localisations: Iterable[str]) -> set[str]:
    """Numéros des départements visés par `localisations` (clés de
    `LOCALISATIONS`) : un département donne son numéro, une région ceux de
    tous ses départements. Les valeurs inconnues sont ignorées."""
    numeros: set[str] = set()
    for lieu in localisations:
        if lieu in NUMEROS_REGIONS:
            numeros.update(NUMEROS_REGIONS[lieu])
        elif lieu in NUMEROS_DEPARTEMENTS:
            numeros.add(NUMEROS_DEPARTEMENTS[lieu])
    return numeros


def numero_departement_texte(texte: str) -> str | None:
    """Numéro de département d'un lieu d'offre, `None` s'il n'y en a pas.

    Reconnaît « Paris (75) », « Haute Corse (2b) » puis, à défaut, le
    dernier code postal d'une adresse (« 93186 Montreuil Cedex »). Un code
    postal de Corse (20xxx) donne 2A ou 2B selon sa tranche, outre-mer les
    trois premiers chiffres.
    """
    if m := _RE_NUMERO_ENTRE_PARENTHESES.search(texte):
        return m.group(1).upper()
    codes = _RE_CODE_POSTAL.findall(texte)
    if not codes:
        return None
    code = codes[-1]
    if code.startswith("20"):
        return "2A" if int(code) < 20200 else "2B"
    if code.startswith(("97", "98")):
        return code[:3]
    return code[:2]


def cle_categorie(texte: str) -> str | None:
    """Clé de `CATEGORIES` d'un libellé de fiche (« Catégorie A (cadre) »),
    `None` si le libellé n'en contient pas."""
    m = _RE_CATEGORIE.search(texte)
    if m is None:
        return None
    lettre = m.group(1).upper()
    if lettre != "A+":
        return lettre
    return (
        "A+ (autres emplois fonctionnels)"
        if "autres" in texte.lower()
        else "A+ (direction)"
    )


# Regex de détection des grades supérieurs (IDiv, IP*, AFIP/AFIPA). « IP »
# reste sensible à la casse : « Ipsum… » ou « Iphone… » ne sont pas des grades.
RE_GRADE_SUPERIEUR = re.compile(r"^(?:(?i:IDIV|AFIPA?)|IP[A-Z\s\-\(/])")

CORPS_GRADES: Final[Mapping[str, Mapping[str, re.Pattern[str]]]] = {
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

GRADES: Final[Mapping[str, re.Pattern[str]]] = {
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


EXPERIENCES: Final[Mapping[str, int]] = {
    "Débutant": 1835,
    "Confirmé": 1834,
    "Expert": 1833,
}

DATES_PUBLICATION: Final[Mapping[str, str]] = {
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
