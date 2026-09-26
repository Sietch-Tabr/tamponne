"""Correspondances de filtres propres à emploi-territorial.fr.

Valeurs vérifiées empiriquement contre le formulaire réel du site (segments
`search_offre_form[...]`) — pas les mêmes identifiants que `src/filtres.py`,
qui sert choisirleservicepublic.gouv.fr.
"""

DEPARTEMENTS: dict[str, str] = {
    "Ain": "001",
    "Aisne": "002",
    "Allier": "003",
    "Alpes Hte Provence": "004",
    "Alpes Maritimes": "006",
    "Ardèche": "007",
    "Ardennes": "008",
    "Ariège": "009",
    "Aube": "010",
    "Aude": "011",
    "Aveyron": "012",
    "Bas Rhin": "067",
    "Belfort": "090",
    "Bouches du Rhône": "013",
    "Calvados": "014",
    "Cantal": "015",
    "Charente": "016",
    "Charente Maritime": "017",
    "Cher": "018",
    "Corse du Sud": "02A",
    "Côtes d Armor": "022",
    "Corrèze": "019",
    "Creuse": "023",
    "Deux Sèvres": "079",
    "Dordogne": "024",
    "Doubs": "025",
    "Drôme": "026",
    "Essonne": "091",
    "Eure": "027",
    "Eure et Loir": "028",
    "Finistère": "029",
    "Gard": "030",
    "Gers": "032",
    "Gironde": "033",
    "Guadeloupe": "971",
    "Guyane": "973",
    "Haut Rhin": "068",
    "Haute Corse": "02B",
    "Haute Garonne": "031",
    "Haute Loire": "043",
    "Haute Savoie": "074",
    "Haute Saône": "070",
    "Haute Vienne": "087",
    "Haute-Marne": "052",
    "Hautes Alpes": "005",
    "Hautes Pyrénées": "065",
    "Hauts-de-Seine": "092",
    "Hérault": "034",
    "Ille et Vilaine": "035",
    "Indre": "036",
    "Indre et Loire": "037",
    "Isère": "038",
    "Jura": "039",
    "Landes": "040",
    "Loir et Cher": "041",
    "Loire": "042",
    "Loire Atlantique": "044",
    "Loiret": "045",
    "Lot": "046",
    "Lot et Garonne": "047",
    "Lozère": "048",
    "Maine et Loire": "049",
    "Manche": "050",
    "Marne": "051",
    "Martinique": "972",
    "Mayenne": "053",
    "Mayotte": "976",
    "Meurthe et Moselle": "054",
    "Meuse": "055",
    "Morbihan": "056",
    "Moselle": "057",
    "Nièvre": "058",
    "Nord": "059",
    "Nouvelle Calédonie": "988",
    "Oise": "060",
    "Orne": "061",
    "Paris": "075",
    "Pas de Calais": "062",
    "Puy de Dôme": "063",
    "Pyrénées Atlantiques": "064",
    "Pyrénées Orientales": "066",
    "Réunion": "974",
    "Rhône": "069",
    "Saône et Loire": "071",
    "Sarthe": "072",
    "Savoie": "073",
    "Seine Maritime": "076",
    "Seine Saint-Denis": "093",
    "Seine et Marne": "077",
    "Somme": "080",
    "Tarn": "081",
    "Tarn et Garonne": "082",
    "Val d'Oise": "095",
    "Val de Marne": "094",
    "Var": "083",
    "Vaucluse": "084",
    "Vendée": "085",
    "Vienne": "086",
    "Vosges": "088",
    "Yvelines": "078",
    "Yonne": "089",
}
"""Département → code INSEE sur 3 caractères attendu par
`search_offre_form[searchdept][]` (ex. « 034 » = Hérault).

Couvre les clés de `src.filtres.LOCALISATIONS` qui sont des départements ;
régions et groupement DOM n'ont pas d'équivalent unique côté ET et restent
volontairement absents.
"""

# search_offre_form[searchcat][] — ET n'a qu'une catégorie « A+ » : les
# deux variantes A+ de src.filtres y sont confondues.
CATEGORIES: dict[str, str] = {
    "A+ (direction)": "A+",
    "A+ (autres emplois fonctionnels)": "A+",
    "A": "A",
    "B": "B",
    "C": "C",
}

# search_offre_form[experience][]
EXPERIENCES: dict[str, str] = {
    "Débutant": "1",
    "Confirmé": "2",
    "Expert": "3",
}

# search_offre_form[management] / [teletravail] — champs à bascule Oui/Non,
# absents de l'URL si indifférent (comme management/teletravail=False).
VALEUR_OUI = "2"

TYPE_CONTRAT_TITULAIRE = "99"
"""Code `search_offre_form[searchtypecontrat][]` d'Emploi permanent.

ET n'a pas de notion titulaire/contractuel, seulement un type de contrat :
seul « Titulaire uniquement » y a un équivalent net. Les autres choix
(défaut, contractuel, tous) ne filtrent rien côté ET plutôt que d'être
mappés à l'aveugle sur plusieurs codes.
"""
