"""Types partagés entre les modules du projet."""

from typing import NotRequired, TypedDict

Organisations = dict[str, dict[str, int]]
"""Mapping ministère → {nom de sous-organisation → identifiant API}."""


class Offre(TypedDict):
    """Offre d'emploi extraite du HTML de choisirleservicepublic.gouv.fr.

    Attributes:
        titre: Intitulé du poste.
        url: URL absolue de la fiche de l'offre.
        reference: Identifiant extrait de l'URL (segment ``reference-<id>``).
        domaine: Domaine métier affiché sur la carte.
        employeur: Nom de l'employeur.
        localisation: Lieu d'affectation du poste.
        versant: Versant de la fonction publique (FPE, FPH, FPT).
        date: Date de mise en ligne telle qu'affichée sur le site.
        source: Origine réelle de l'offre, déduite du préfixe de
            référence (ex. « MEF » pour Bercy/Passerelles, « MINT »
            pour l'Intérieur) — chaîne vide si native au site.
    """

    titre: str
    url: str
    reference: str
    domaine: str
    employeur: str
    localisation: str
    versant: str
    date: str
    source: str


class OffreCache(Offre):
    """Offre enrichie lors de sa mise en cache.

    Étend :class:`Offre` avec les horodatages de suivi permettant de
    détecter les nouvelles offres et de purger les entrées expirées.

    Attributes:
        vu_le: Horodatage ISO 8601 UTC de la première apparition.
        derniere_vue: Horodatage ISO 8601 UTC du dernier cycle où l'offre
            était présente dans les résultats.
    """

    vu_le: str
    derniere_vue: str


class FiltresRecherche(TypedDict, total=False):
    """Critères du formulaire de recherche (tous optionnels).

    Les listes vides signifient « pas de filtre sur ce critère ».

    Attributes:
        categories: Catégories statutaires (``"A"``, ``"B"``, ``"C"``).
        domaines: Libellés de domaines métier (clés de
            :data:`~src.filtres.DOMAINES`).
        localisations: Noms de départements/régions (clés de
            :data:`~src.filtres.LOCALISATIONS`).
        organisations: Noms au format ``"Ministère - Sous-organisation"``.
        grades: Libellés de grade (clés de :data:`~src.filtres.GRADES`) —
            filtrage best-effort par mots-clés dans le titre, appliqué côté
            client après agrégation (aucune source n'expose ce niveau de
            granularité côté serveur).
        versants: Clés de versant (``"etat"``, ``"hospitalier"``,
            ``"territorial"``) — liste vide = tous les versants, même
            convention que ``domaines``/``localisations``.
        types_poste: ``None`` → titulaire-éligible par défaut ;
            ``"__tous__"`` → tous types ; liste de clés sinon.
        experience: Clé de :data:`~src.filtres.EXPERIENCES`, chaîne vide si
            indifférent.
        date_publication: Clé de :data:`~src.filtres.DATES_PUBLICATION`,
            chaîne vide si indifférent.
        management: ``True`` si seuls les postes d'encadrement sont ciblés.
        teletravail: ``True`` si seuls les postes en télétravail possible
            sont ciblés.
        query: Mot-clé libre saisi par l'utilisateur.
        grades_superieurs: ``True`` pour garder les offres des grades
            d'encadrement supérieur (IDIV, IP, AFIPA), écartées par défaut —
            filtre appliqué côté client, ignoré par les sources.
    """

    categories: list[str]
    domaines: list[str]
    localisations: list[str]
    organisations: list[str]
    grades: list[str]
    versants: list[str]
    types_poste: list[str] | str | None
    experience: str
    date_publication: str
    management: bool
    teletravail: bool
    query: str
    grades_superieurs: bool


class Profil(FiltresRecherche, total=False):
    """Profil de recherche sauvegardé.

    Étend :class:`FiltresRecherche` avec des métadonnées persistées dans
    ``data/profils.json``.

    Attributes:
        label: Nom d'affichage dans les menus.
        cree_le: Date de création au format ``YYYY-MM-DD``.
        dernier_lancement: Date du dernier lancement au format ``YYYY-MM-DD``.
    """

    label: str
    cree_le: str
    dernier_lancement: str


class DetailOffre(TypedDict):
    """Détail structuré d'une fiche de poste, extrait du bloc JSON-LD
    (schema.org JobPosting) intégré dans la page au moment où le suivi
    de candidature démarre — l'offre peut être dépubliée ensuite, ces
    infos ne sont alors plus consultables que dans l'app.

    Pas de champ dédié « personne à contacter » : ce point est couvert
    par `sections_complementaires` (voir plus bas), qui inclut la
    section « Informations complémentaires » quand l'offre en a une —
    plus fiable qu'un champ dédié qui devrait deviner où chercher ces
    coordonnées.

    Attributes:
        description: Description complète des missions.
        salaire: Libellé de salaire tel qu'affiché (souvent
            « Non renseigné »).
        experience_requise: Niveau d'expérience demandé.
        formation_requise: Niveau de formation demandé.
        secteur: Secteur d'activité.
        date_publication: Date de publication telle qu'affichée sur la
            fiche (peut différer du format `Offre.date`).
        a_propos_employeur: Texte de présentation du service/employeur
            (section « Qui sommes-nous ? » de la fiche).
        sections_complementaires: Sections de la partie « À propos de
            l'offre » (accordéon), titre → contenu — inclut entre
            autres « Informations complémentaires » (souvent la
            personne à contacter, quand l'offre en indique une),
            « Conditions particulières d'exercice », « Fondement
            juridique », « Statut du poste », « Métier de référence ».
            Variable d'une offre à l'autre : clé absente si l'offre
            n'a pas cette section.
        page_html: HTML brut complet de la page au moment du suivi —
            filet de sécurité si un champ venait à manquer à
            l'extraction ci-dessus ou si la structure du site change.
        lien_postuler: URL du portail de candidature réel (souvent
            externe au site, ex. Talentsoft) — absent sur certaines
            offres.
        date_limite: Date limite de candidature affichée, chaîne vide
            si non renseignée.
    """

    description: str
    salaire: str
    experience_requise: str
    formation_requise: str
    secteur: str
    date_publication: str
    a_propos_employeur: str
    sections_complementaires: dict[str, str]
    page_html: str
    lien_postuler: str
    date_limite: str


class EvenementCandidature(TypedDict):
    """Un événement horodaté dans l'historique d'une candidature.

    Attributes:
        date: Date de l'événement au format ``YYYY-MM-DD``.
        type: Clé parmi :data:`~src.candidatures.TYPES_EVENEMENT`.
        note: Note libre optionnelle, chaîne vide si absente.
    """

    date: str
    type: str
    note: str


class Candidature(TypedDict):
    """Candidature suivie pour une offre, stockée dans
    ``data/candidatures.json`` sous forme de ``dict[str, Candidature]``
    indexé par la référence de l'offre (clé naturelle, unique — même
    convention que ``cache_profil[ref]`` dans `src/cache.py`).

    Le statut affiché est toujours dérivé du dernier événement de
    `historique` (voir :func:`~src.candidatures.dernier_evenement`),
    jamais stocké comme champ à part qu'on écraserait — pour garder la
    trace complète d'un recrutement qui peut s'étaler sur plusieurs mois.

    Attributes:
        offre_titre: Intitulé du poste au moment de la candidature
            (snapshot — l'offre peut disparaître du site ensuite).
        offre_employeur: Employeur au moment de la candidature.
        offre_url: URL de la fiche de l'offre.
        date_candidature: Date de l'envoi de la candidature, ``YYYY-MM-DD``.
        historique: Liste des événements, dans l'ordre d'ajout.
        disponible: ``False`` si l'offre a été dépubliée du site
            (détecté via :func:`~src.sources.detail.verifier_disponibilite`).
            ``True`` par défaut tant que non vérifiée — ne préjuge pas.
        derniere_verification: Date ISO 8601 de la dernière vérification
            de disponibilité, chaîne vide si jamais vérifiée.
        offre_reference, offre_domaine, offre_localisation,
            offre_versant, offre_date: Reste du snapshot `Offre` au
            moment de la candidature (voir `src.types.Offre`).
        detail: Détail structuré + archive HTML brute, voir
            `DetailOffre`.
        offre_source: Source de l'offre au moment du suivi (absente des
            candidatures enregistrées avant la 2.0, voir
            :func:`~src.candidatures.source_candidature`).
    """

    offre_titre: str
    offre_employeur: str
    offre_url: str
    offre_reference: str
    offre_domaine: str
    offre_localisation: str
    offre_versant: str
    offre_date: str
    date_candidature: str
    historique: list[EvenementCandidature]
    disponible: bool
    derniere_verification: str
    detail: DetailOffre
    offre_source: NotRequired[str]


class PageAPI(TypedDict):
    """Réponse brute d'une page téléchargée depuis l'API WordPress.

    Attributes:
        html: Contenu HTML complet de la page.
        title: Contenu de la balise ``<title>``, chaîne vide si absente.
    """

    html: str
    title: str


class InfoMaj(TypedDict):
    """Publication Codeberg plus récente que la version locale.

    Attributes:
        version: Numéro de version cible (``tag_name``, préfixe ``v`` ôté).
        notes: Notes de version (``body`` de la publication).
        url_zip: URL de l'archive source (``zipball_url``).
        url_publication: Page web de la publication (``html_url``).
    """

    version: str
    notes: str
    url_zip: str
    url_publication: str


class EchecMaj(TypedDict):
    """Mise à jour annulée par le lanceur (retour à la version précédente).

    Attributes:
        version: Version qui n'a pas pu être installée.
        motif: Cause affichée dans l'avis de mise à jour.
        date: Date de l'échec (ISO 8601).
    """

    version: str
    motif: str
    date: str


class ResultatTraite(TypedDict):
    """Résultat d'une recherche après post-traitement
    (`src.recherche.post_traiter_resultats`).

    Attributes:
        offres: Offres conservées après filtres de grade.
        nb_exclus: Nombre d'offres IDiv/IP exclues par le filtre de titre.
        nouvelles: Références des offres jamais vues pour ce profil
            (vide hors profil sauvegardé).
    """

    offres: list[Offre]
    nb_exclus: int
    nouvelles: set[str]
