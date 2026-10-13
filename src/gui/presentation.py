"""Textes affichés par l'interface, calculés sans Qt pour rester testables
sans rendu : l'interface QML ne fait que les afficher."""

import html
import re
from dataclasses import dataclass
from datetime import date, datetime

from src.candidatures import (
    TYPES_EVENEMENT,
    dernier_evenement,
    relance_suggeree,
)
from src.filtres import LIBELLES_CATEGORIES, categorie_normalisee
from src.types import Candidature, DetailOffre, Profil

LIBELLES_TAMPON: dict[str, str] = {
    "candidature_envoyee": "Envoyée",
    "accuse_reception": "Accusé de réception",
    "entretien_planifie": "Entretien",
    "entretien_passe": "Entretien passé",
    "relance": "Relance",
    "reponse_positive": "Réponse positive",
    "refus": "Refus",
    "autre": "Autre",
}
"""Type d'événement → texte du tampon de l'historique (maquette « dossier »)."""


def reformater_date_iso(date_iso: str, annee_courte: bool = False) -> str:
    """Reformate une date ISO (`YYYY-MM-DD`) en JJ/MM/AAAA, ou JJ/MM/AA si
    `annee_courte`. Retourne la chaîne d'origine si le format n'est pas
    reconnu (ne devrait pas arriver, écrit uniquement par `src.candidatures`)."""
    try:
        jour = date.fromisoformat(date_iso)
    except ValueError:
        return date_iso
    return jour.strftime("%d/%m/%y" if annee_courte else "%d/%m/%Y")


@dataclass(frozen=True)
class TamponHistorique:
    """Un événement de l'historique, affiché comme un coup de tampon."""

    libelle: str
    date: str
    """Date courte JJ/MM/AA."""
    courant: bool
    """Dernier événement (celui qui donne le statut) : tampon plein et encadré."""
    refus: bool
    """Encre rouge plutôt que l'encre de tampon."""
    positif: bool
    """Réponse positive : encre verte."""
    indice: int
    """Position de l'événement dans l'historique enregistré (modification)."""


@dataclass(frozen=True)
class ContenuDossier:
    """Textes d'un dossier de l'écran Suivi."""

    reference: str
    titre: str
    employeur_lieu: str
    statut: str
    """Phrase du statut, en texte droit : l'information ne doit jamais
    dépendre des seuls tampons inclinés."""
    tampons: tuple[TamponHistorique, ...]
    """Historique trié par date (tri stable, comme `dernier_evenement`)."""
    jours_sans_nouvelles: int | None
    """Renseigné seulement si une relance est suggérée (post-it)."""
    disponible: bool


def _phrase_statut(candidature: Candidature, archive_presente: bool) -> str:
    dernier = dernier_evenement(candidature)
    if dernier is None:
        phrase = "aucun événement"
    else:
        libelle = TYPES_EVENEMENT.get(dernier["type"], dernier["type"])
        phrase = f"{libelle[:1].lower()}{libelle[1:]} le {reformater_date_iso(dernier['date'])}"
        if dernier.get("note"):
            phrase += f" ({dernier['note']})"
    if not candidature.get("disponible", True):
        phrase += " · offre dépubliée"
        if archive_presente:
            phrase += ", archive PDF conservée"
    return phrase


def contenu_dossier(
    reference: str,
    candidature: Candidature,
    aujourd_hui: date,
    archive_presente: bool,
) -> ContenuDossier:
    """Construit les textes d'un dossier de suivi.

    Args:
        reference: Référence de l'offre suivie (clé de `candidatures.json`).
        candidature: Candidature telle que stockée par `src.candidatures`.
        aujourd_hui: Date du jour, pour le nombre de jours sans nouvelles.
        archive_presente: Vrai si la copie PDF de la fiche existe
            (`src.candidatures.chemin_archive_pdf`).

    Returns:
        Référence, titre, employeur et lieu, phrase de statut, tampons de
        l'historique et jours sans nouvelles si une relance est suggérée.
    """
    # Tri stable par date, en gardant la position d'origine de chaque événement.
    historique = sorted(
        enumerate(candidature.get("historique") or []),
        key=lambda paire: paire[1]["date"],
    )
    tampons = tuple(
        TamponHistorique(
            libelle=LIBELLES_TAMPON.get(evenement["type"], evenement["type"]),
            date=reformater_date_iso(evenement["date"], annee_courte=True),
            courant=rang == len(historique) - 1,
            refus=evenement["type"] == "refus",
            positif=evenement["type"] == "reponse_positive",
            indice=indice,
        )
        for rang, (indice, evenement) in enumerate(historique)
    )

    jours: int | None = None
    if relance_suggeree(candidature) and historique:
        jours = (aujourd_hui - date.fromisoformat(historique[-1][1]["date"])).days

    lieu = candidature.get("offre_localisation") or ""
    employeur = candidature.get("offre_employeur") or ""
    return ContenuDossier(
        reference=reference,
        titre=candidature["offre_titre"],
        employeur_lieu=" · ".join(partie for partie in (employeur, lieu) if partie),
        statut=_phrase_statut(candidature, archive_presente),
        tampons=tampons,
        jours_sans_nouvelles=jours,
        disponible=candidature.get("disponible", True),
    )


@dataclass(frozen=True)
class ContenuDetail:
    """Textes de la fenêtre « fiche de poste » d'une offre."""

    reference: str
    titre: str
    sous_titre: str
    """Employeur, lieu et source connus, séparés par « · »."""
    description: str
    """Rubrique « Description du poste », vide si absente."""
    informations: tuple[tuple[str, str], ...]
    """(libellé, valeur) de la rubrique « Informations », valeurs vides omises."""
    rubriques: tuple[tuple[str, str], ...]
    """(titre, texte) affichés après les informations : « Qui sommes-nous ? »
    puis les sections complémentaires de l'offre."""
    lien_postuler: str
    """Portail de candidature, vide s'il n'est pas en https."""
    url: str
    """Offre en ligne, vide si elle n'est pas en https."""
    archive_presente: bool


def contenu_detail(
    reference: str,
    titre: str,
    parties_sous_titre: list[str],
    detail: DetailOffre,
    url: str,
    archive_presente: bool,
) -> ContenuDetail:
    """Construit le contenu de la fenêtre de détail d'une offre.

    Args:
        reference: Référence de l'offre.
        titre: Intitulé du poste.
        parties_sous_titre: Employeur, lieu, source… (les vides sont ignorés).
        detail: Détail structuré de l'offre (`src.types.DetailOffre`).
        url: URL de l'offre en ligne.
        archive_presente: Vrai si la copie PDF archivée existe.

    Returns:
        Description, informations non vides, rubriques suivantes et liens
        utilisables (https uniquement).
    """
    rubriques: list[tuple[str, str]] = []
    informations = tuple(
        (libelle, str(detail.get(cle) or ""))
        for libelle, cle in (
            ("Salaire", "salaire"),
            ("Expérience requise", "experience_requise"),
            ("Formation requise", "formation_requise"),
            ("Secteur", "secteur"),
            ("Publiée le", "date_publication"),
            ("Date limite", "date_limite"),
        )
        if detail.get(cle)
    )
    if detail.get("a_propos_employeur"):
        rubriques.append(("Qui sommes-nous\u00a0?", detail["a_propos_employeur"]))
    rubriques.extend((detail.get("sections_complementaires") or {}).items())
    lien = detail.get("lien_postuler") or ""
    return ContenuDetail(
        reference=reference,
        titre=titre,
        sous_titre=" · ".join(p for p in parties_sous_titre if p),
        description=detail.get("description") or "",
        informations=informations,
        rubriques=tuple(rubriques),
        lien_postuler=lien if lien.startswith("https://") else "",
        url=url if url.startswith("https://") else "",
        archive_presente=archive_presente,
    )


_VERSANTS_FICHE: dict[str, str] = {
    "etat": "État",
    "hospitalier": "Hospitalier",
    "territorial": "Territorial",
}


def _premier_et_reste(valeurs: list[str]) -> str:
    """« Premier +N » : la fiche n'a la place que pour le premier élément."""
    return valeurs[0] + (f" +{len(valeurs) - 1}" if len(valeurs) > 1 else "")


def lignes_fiche(profil: Profil) -> list[str]:
    """Résumé d'un profil sur la fiche bristol de l'écran Profils.

    Args:
        profil: Profil tel que stocké par `src.profils`.

    Returns:
        Une à trois lignes : catégories et versants ; lieu et options ;
        autres critères (domaines, organisations, grades, expérience,
        date de publication, mot-clé, grades supérieurs quand la catégorie
        A+ est concernée), omise s'il n'y en a aucun.
    """
    categories = [
        LIBELLES_CATEGORIES.get(c, c)
        for c in dict.fromkeys(
            map(categorie_normalisee, profil.get("categories") or [])
        )
    ]
    versants = [_VERSANTS_FICHE.get(v, v) for v in profil.get("versants") or []]
    ligne_statut = " · ".join(
        [
            ("Cat. " + ", ".join(categories)) if categories else "Toutes catégories",
            ", ".join(versants) if versants else "tous versants",
        ]
    )

    localisations = profil.get("localisations") or []
    lieu = [_premier_et_reste(localisations) if localisations else "Toute la France"]
    if profil.get("teletravail"):
        lieu.append("télétravail")
    if profil.get("management"):
        lieu.append("management")

    autres: list[str] = []
    if domaines := profil.get("domaines"):
        autres.append(_premier_et_reste(domaines))
    if organisations := profil.get("organisations"):
        autres.append(_premier_et_reste([o.split(" - ")[-1] for o in organisations]))
    if grades := profil.get("grades"):
        autres.append(_premier_et_reste(grades))
    if experience := profil.get("experience"):
        autres.append(experience.lower())
    if date_publication := profil.get("date_publication"):
        autres.append(date_publication.lower())
    if mot_cle := profil.get("query"):
        autres.append(f"mot-clé «\u00a0{mot_cle}\u00a0»")
    # Les grades supérieurs (IDIV, IP, AFIPA) ne concernent que la catégorie A+.
    if not categories or any(c.startswith("A+") for c in categories):
        inclus = profil.get("grades_superieurs")
        autres.append(f"grades supérieurs {'inclus' if inclus else 'exclus'}")

    lignes = [ligne_statut, " · ".join(lieu)]
    if autres:
        lignes.append(" · ".join(autres))
    return lignes


def texte_nombre_fiches(nombre: int) -> str:
    """Compteur sous le titre « Mes fiches de recherche »."""
    return (
        f"{nombre} fiche{'s' if nombre > 1 else ''} classée{'s' if nombre > 1 else ''}"
    )


def libelle_selection(selection: list[str]) -> str:
    """Valeur affichée à droite d'une ligne de choix du formulaire
    (« tous », le nom de l'unique élément choisi, ou « N cochés »)."""
    if not selection:
        return "tous"
    if len(selection) == 1:
        return selection[0].split(" - ")[-1]
    return f"{len(selection)} cochés"


def resume_registre(
    nombre: int, nouvelles: int, ecartees: int, horodatage: datetime
) -> str:
    """Ligne sous le titre « Registre des offres » après une recherche.

    Args:
        nombre: Offres inscrites au registre.
        nouvelles: Offres jamais vues pour la fiche lancée.
        ecartees: Offres écartées par le filtre des grades supérieurs.
        horodatage: Fin de la recherche.
    """
    parties = [f"{nombre} inscrite{'s' if nombre > 1 else ''}"]
    if nouvelles:
        parties.append(f"{nouvelles} nouvelle{'s' if nouvelles > 1 else ''}")
    if ecartees:
        parties.append(
            f"{ecartees} écartée{'s' if ecartees > 1 else ''} (grades supérieurs)"
        )
    parties.append(horodatage.strftime("%d/%m/%Y %H:%M"))
    return " · ".join(parties)


def date_courte(date_affichee: str) -> str:
    """JJ/MM/AAAA → JJ/MM/AA pour la colonne « Publiée » du registre ;
    toute autre valeur est rendue telle quelle."""
    morceaux = date_affichee.split("/")
    if len(morceaux) == 3 and len(morceaux[2]) == 4 and morceaux[2].isdigit():
        return f"{morceaux[0]}/{morceaux[1]}/{morceaux[2][2:]}"
    return date_affichee


def evenement_propose(candidature: Candidature, aujourd_hui: date) -> tuple[str, str]:
    """Type et date (ISO) proposés à l'ouverture de « Ajouter un événement ».

    La suite d'un dossier vient toujours après son dernier événement : la
    date proposée est celle du plus récent, le type celui qui le suit dans
    `TYPES_EVENEMENT`. Sans historique : « Candidature envoyée » du jour.
    """
    dernier = dernier_evenement(candidature)
    types = list(TYPES_EVENEMENT)
    if dernier is None:
        return types[0], aujourd_hui.isoformat()
    rang = types.index(dernier["type"]) if dernier["type"] in types else len(types) - 1
    return types[min(rang + 1, len(types) - 1)], dernier["date"]


_CODE = re.compile(r"`([^`]+)`")
_GRAS = re.compile(r"\*\*(.+?)\*\*")
_LIEN = re.compile(r"\[([^\]]+)\]\(([^)\s\"<>]+)\)")
_PUCE = re.compile(r"^[-*+] +")


def _en_ligne(texte: str) -> str:
    """Code, gras et liens d'une ligne Markdown, après échappement HTML."""
    texte = html.escape(texte, quote=False)
    texte = _CODE.sub(r'<span style="font-weight:600">\1</span>', texte)
    texte = _GRAS.sub(r"<b>\1</b>", texte)

    def lien(trouve: re.Match[str]) -> str:
        libelle, url = trouve.group(1), trouve.group(2)
        if not url.startswith("https://"):
            return libelle
        return f'<a href="{url}">{libelle}</a>'

    return _LIEN.sub(lien, texte)


def _marges(blocs: list[str]) -> str:
    """12 px avant un bloc, sauf le premier ; 0 après (titre collé à sa liste)."""
    haut = 12 if blocs else 0
    return f' style="margin-top:{haut}px;margin-bottom:0"'


def notes_en_html(markdown: str) -> str:
    """Notes de version Codeberg (Markdown) en HTML au style maîtrisé.

    Le rendu Markdown de Qt affiche le code dans une police de secours et
    agrandit les titres : seuls les éléments des publications du projet
    sont convertis (titres, listes à puces, paragraphes, `code`, gras,
    liens https), le reste est gardé en texte échappé.

    Args:
        markdown: Corps de la publication (`InfoMaj["notes"]`).

    Returns:
        Fragment HTML pour un `Text` QML en `RichText`.
    """
    blocs: list[str] = []
    paragraphe: list[str] = []
    puces: list[str] = []

    def fermer() -> None:
        if paragraphe:
            blocs.append(f"<p{_marges(blocs)}>{_en_ligne(' '.join(paragraphe))}</p>")
            paragraphe.clear()
        if puces:
            elements = "".join(f"<li>{_en_ligne(p)}</li>" for p in puces)
            blocs.append(f'<ul style="margin-top:4px;margin-bottom:0">{elements}</ul>')
            puces.clear()

    for ligne in markdown.replace("\r\n", "\n").split("\n"):
        brute = ligne.strip()
        if not brute:
            fermer()
        elif brute.startswith("#"):
            fermer()
            titre = _en_ligne(brute.lstrip("#").strip())
            blocs.append(f"<p{_marges(blocs)}><b>{titre}</b></p>")
        elif _PUCE.match(brute):
            if paragraphe:
                fermer()
            puces.append(_PUCE.sub("", brute))
        elif puces and ligne[:1].isspace():
            puces[-1] += " " + brute
        else:
            if puces:
                fermer()
            paragraphe.append(brute)
    fermer()
    return "".join(blocs)


TEXTES_RACCOURCI: dict[str, str] = {
    "absent": "Tamponné n'est pas encore dans le menu des applications.",
    "a_jour": "Tamponné figure dans le menu des applications.",
    "deplace": "Le dossier a été déplacé\u00a0: le raccourci ne trouve plus Tamponné.",
}
"""État du raccourci (`src.raccourci.etat`) → phrase de la feuille Raccourci."""


def texte_avis_sans_publication(installee: str, en_cours: bool, erreur: str) -> str:
    """Objet de l'avis de mise à jour quand aucune publication n'est
    proposée : vérification en cours, impossible (avec le détail technique
    `erreur`), ou version déjà la plus récente."""
    if en_cours:
        return f"version {installee} installée, recherche d'une mise à jour…"
    if erreur:
        return (
            f"version {installee} installée\u00a0; impossible de savoir s'il existe "
            "plus récent, Codeberg ne répond pas (connexion internet ou proxy). "
            f"Détail\u00a0: {erreur}"
        )
    return f"version {installee} installée, rien de plus récent."


def texte_offres_non_verifiees(nombre: int, erreur: str) -> str:
    """Avertissement de l'écran Suivi après une vérification où `nombre`
    offres n'ont pas pu être consultées (vide si aucune), avec le détail
    technique de la première erreur."""
    if nombre == 0:
        return ""
    offres = "1 offre non vérifiée" if nombre == 1 else f"{nombre} offres non vérifiées"
    return (
        f"{offres}\u00a0: le site de l'offre ne répond pas (connexion internet "
        f"ou proxy). Réessayez plus tard.\nDétail\u00a0: {erreur}"
    )


def texte_confirmation_import(nom_fichier: str) -> str:
    """Question posée avant de remplacer les données par une sauvegarde ;
    le nom du fichier ne se coupe pas (espaces et traits d'union insécables)."""
    insecable = nom_fichier.replace(" ", "\u00a0").replace("-", "\u2011")
    return (
        "Remplacer toutes vos données par celles de "
        f"«\u00a0{insecable}\u00a0»\u00a0? Une copie des données actuelles "
        "est conservée. Tamponné redémarrera ensuite."
    )
