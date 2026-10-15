pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Écran Aide (« Notice d'utilisation ») : feuilles explicatives. Mise en
    page de la maquette, textes complétés pour couvrir toute l'application. */
Item {
    id: racine

    component FeuilleNotice: Feuille {
        id: feuilleNotice
        property string titre: ""
        default property alias contenuNotice: colonneNotice.data
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        Layout.preferredHeight: colonneNotice.implicitHeight + 40
        halo: Theme.ombrePorteeLegere
        flou: 22

        Accessible.role: Accessible.Grouping
        Accessible.name: titre

        // Column et non ColumnLayout : le layout arrondit les hauteurs
        // fractionnaires (24,8 px par ligne) et décale tout de 1 à 3 px.
        Column {
            id: colonneNotice
            x: 24
            y: 20
            width: parent.width - 48
            spacing: 12

            Texte {
                width: parent.width
                text: feuilleNotice.titre
                font.pixelSize: 20
                font.capitalization: Font.AllUppercase
                font.letterSpacing: 0.5
                font.variableAxes: { "wdth": 88, "wght": 800 }
                bottomPadding: 8
                Accessible.role: Accessible.Heading
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 2
                    color: Theme.encre
                }
            }
        }
    }

    component Terme: Texte {
        width: parent ? parent.width : 0
        font.pixelSize: 17
        font.variableAxes: { "wdth": 90, "wght": 800 }
        Accessible.role: Accessible.Heading
    }

    component Definition: Texte {
        width: parent ? parent.width : 0
        height: lineCount * lineHeight + bottomPadding
        bottomPadding: 6
        lineHeight: 16 * 1.55
    }

    component Exemple: Texte {
        width: parent ? parent.width : 0
        textFormat: Text.StyledText
        font.family: Theme.policeMono
        font.pixelSize: 14
        lineHeight: 14 * 1.7
        height: lineCount * lineHeight + topPadding + bottomPadding
        leftPadding: 15
        rightPadding: 12
        topPadding: 10
        bottomPadding: 10
        Rectangle {
            anchors.fill: parent
            z: -1
            color: Theme.papier2
            Rectangle {
                width: 3
                height: parent.height
                color: Theme.encre
            }
        }
    }

    Flickable {
        id: defilement
        anchors.fill: parent
        contentHeight: colonne.implicitHeight + 56
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        ColumnLayout {
            id: colonne
            x: 28
            y: 28
            width: defilement.width - 56
            spacing: 22

            RowLayout {
                spacing: 18
                Texte {
                    text: "Notice d'utilisation"
                    color: Theme.texteKraft
                    font.pixelSize: 40
                    font.capitalization: Font.AllUppercase
                    font.variableAxes: { "wdth": 80, "wght": 800 }
                    lineHeight: 40
                    wrapMode: Text.NoWrap
                    Layout.preferredHeight: 40
                    Layout.alignment: Qt.AlignBottom
                    Accessible.role: Accessible.Heading
                }
                Texte {
                    text: "à conserver soigneusement"
                    color: Theme.texteKraft
                    font.family: Theme.policeMono
                    font.pixelSize: 14
                    wrapMode: Text.NoWrap
                    Layout.alignment: Qt.AlignBottom
                }
            }

            GridLayout {
                id: grille
                Layout.fillWidth: true
                // « auto-fit, minmax(380px, 1fr) » de la maquette.
                columns: Math.max(1, Math.floor((width + 22) / (380 + 22)))
                columnSpacing: 22
                rowSpacing: 22

                FeuilleNotice {
                    titre: "Les cases du formulaire"
                    Terme { text: "Catégorie" }
                    Definition { text: "Niveau hiérarchique du poste\u00a0: A+ (direction, ou autres emplois fonctionnels), A (cadre), B (profession intermédiaire), C (employé). Le corps / grade affine la catégorie\u00a0: Attaché, Attaché principal, Attaché hors classe, Adjoint administratif…" }
                    Terme { text: "Versant" }
                    Definition { text: "La branche de la fonction publique\u00a0: État, Hospitalier, Territorial. Plusieurs cases à la fois possibles\u00a0; aucune cochée = tous les versants." }
                    Terme { text: "Poste et Lieu" }
                    Definition { text: "Domaines, localisations et organisations s'ouvrent dans une fenêtre de sélection avec un champ de recherche\u00a0: pratique avec 114 localisations et environ 2 400 sous-organisations." }
                    Terme { text: "Type de poste" }
                    Definition { text: "Par défaut, seuls les postes ouverts aux titulaires sont affichés (titulaires + postes ouverts aux deux statuts). «\u00a0Titulaire uniquement\u00a0» et «\u00a0Contractuel uniquement\u00a0» resserrent, «\u00a0Tous (y compris contractuels)\u00a0» ajoute les postes réservés aux contractuels." }
                    Terme { text: "Options" }
                    Definition { text: "Management et Télétravail\u00a0: cochés = seulement les postes concernés. Le mot-clé est transmis tel quel au moteur de recherche de chaque site." }
                    Terme { text: "Expérience et date de publication" }
                    Definition { text: "Expérience souhaitée (débutant, confirmé, expert) et ancienneté de l'offre (48\u00a0heures, 7 ou 14\u00a0jours)\u00a0; «\u00a0Indifférente\u00a0» ne filtre pas." }
                    Terme { text: "RAZ" }
                    Definition { text: "Vide toutes les cases du formulaire." }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 22

                    FeuilleNotice {
                        titre: "Exemples de demande"
                        Terme { text: "Attaché principal territorial (Hérault)" }
                        Exemple { text: "Catégorie → A<br>Corps / grade → Attaché principal<br>Versant → Territorial<br>Lieu → Localisation Hérault" }
                        Definition { text: "Le grade repère «\u00a0attaché principal\u00a0» dans le titre, quel que soit le versant." }
                        Terme { text: "Chef de projet informatique (État)" }
                        Exemple { text: "Catégorie → A<br>Versant → État<br>Poste → Domaine «\u00a0Numérique\u00a0»<br>Options → mot-clé «\u00a0chef de projet\u00a0»" }
                        Definition { text: "Pas de grade statutaire pour ce métier\u00a0: le mot-clé resserre la recherche." }
                    }

                    FeuilleNotice {
                        titre: "Grades supérieurs (IDIV / IP / AFIP)"
                        Definition { text: "Par défaut, les offres dont le titre commence par un grade d'encadrement supérieur de la DGFiP (IDIV, AFIP ou AFIPA, IP suivi d'une majuscule, d'une espace, d'un tiret ou d'une parenthèse, ex. IPFiP) sont écartées du registre\u00a0: postes très spécifiques, peu pertinents pour une recherche large. Cocher «\u00a0Grades supérieurs\u00a0» dans la demande pour les voir quand même." }
                    }
                }

                FeuilleNotice {
                    titre: "La recherche et le registre"
                    Definition { text: "«\u00a0Lancer la recherche\u00a0» interroge les sources actives en même temps et affiche l'avancement de chacune. Une source injoignable est signalée sans arrêter les autres." }
                    Terme { text: "Registre des offres" }
                    Definition { text: "Les offres trouvées, une seule fois même si plusieurs sites les publient. Un clic sur un en-tête de colonne trie. La ligne sous le titre compte les offres inscrites, nouvelles et écartées (grades supérieurs)." }
                    Terme { text: "Filtrer · Nouvelles seulement" }
                    Definition { text: "Filtrer garde les lignes qui contiennent le texte saisi, dans n'importe quelle colonne. «\u00a0Nouvelles seulement\u00a0» ne montre que les offres marquées «\u00a0Nouveau\u00a0»." }
                    Terme { text: "Consulter · Exporter" }
                    Definition { text: "Consulter affiche la fiche de poste, avec «\u00a0Postuler\u00a0» quand le site le permet. Double-clic ou Entrée ouvre l'offre dans le navigateur. Exporter enregistre le registre affiché (tri et filtre compris) en page HTML dans le dossier «\u00a0exports\u00a0»." }
                }

                FeuilleNotice {
                    titre: "Les sources consultées"
                    Definition { text: "Quatre sites, activables dans Réglages\u00a0› Sources consultées. Ils ne comprennent pas tous les mêmes cases\u00a0:" }
                    Terme { text: "Choisir le service public" }
                    Definition { text: "Toutes les cases. Seul site à connaître domaines et organisations." }
                    Terme { text: "emploi-territorial.fr" }
                    Definition { text: "Catégorie, expérience, management, télétravail, mot-clé, «\u00a0Titulaire uniquement\u00a0» et localisations par département (une région seule ne restreint pas le lieu)." }
                    Terme { text: "Passerelles (Bercy) et FHF" }
                    Definition { text: "Mot-clé seulement\u00a0: leurs résultats sont plus larges." }
                    Terme { text: "Pour toutes les sources" }
                    Definition { text: "Corps / grade et Grades supérieurs s'appliquent au titre de chaque offre. Un site n'est pas interrogé si son versant n'est pas coché (emploi-territorial\u00a0: Territorial, Passerelles\u00a0: État, FHF\u00a0: Hospitalier)." }
                }

                FeuilleNotice {
                    titre: "Les fiches de recherche"
                    Definition { text: "Une fiche, c'est une demande de recherche enregistrée sous un nom, avec «\u00a0Créer une fiche\u00a0» dans l'écran Recherche. «\u00a0Nouvelle fiche\u00a0» ouvre un formulaire vierge." }
                    Terme { text: "Lancer" }
                    Definition { text: "Lance la recherche immédiatement (double-clic sur la fiche aussi)." }
                    Terme { text: "Offres nouvelles" }
                    Definition { text: "Une recherche lancée depuis une fiche marque «\u00a0Nouveau\u00a0» les offres jamais vues pour cette fiche. Si les cases ont été changées entre-temps, rien n'est marqué. Une offre absente des résultats pendant 30\u00a0jours redevient nouvelle." }
                    Terme { text: "modifier · dupliquer · supprimer" }
                    Definition { text: "Modifier rouvre le formulaire\u00a0: «\u00a0Enregistrer la fiche\u00a0» garde les nouvelles cases sans lancer, «\u00a0Annuler\u00a0» revient aux fiches. Dupliquer copie la fiche sous un autre nom, supprimer la jette (confirmation demandée)." }
                }

                FeuilleNotice {
                    titre: "Les dossiers de suivi"
                    Definition { text: "Dans le registre, sélectionner une offre puis «\u00a0Tamponner pour suivi\u00a0» ouvre un dossier et archive la fiche de poste en PDF. Le statut est toujours celui du dernier tampon de l'historique." }
                    Terme { text: "voir l'offre · archive PDF · détail" }
                    Definition { text: "L'offre en ligne, la copie PDF conservée au moment du suivi (consultable hors ligne), ou la fiche de poste dans Tamponné." }
                    Terme { text: "ajouter un événement" }
                    Definition { text: "Envoi, accusé de réception, entretien, relance, réponse… Le type proposé est la suite logique du dernier tampon, à sa date. Une note est possible." }
                    Terme { text: "Relance suggérée" }
                    Definition { text: "Post-it collé quand rien ne s'est passé depuis 3 semaines et que le dossier n'est pas clos (réponse positive ou refus)." }
                    Terme { text: "Offre dépubliée" }
                    Definition { text: "«\u00a0Vérifier les offres\u00a0» interroge les sites pour chaque dossier\u00a0: une offre disparue est marquée dépubliée, sa copie archivée reste consultable. Les offres que le site n'a pas pu confirmer sont signalées à part." }
                    Terme { text: "Tampons" }
                    Definition { text: "Un clic sur un tampon de l'historique permet de modifier ou de supprimer l'événement\u00a0; un même événement ne peut pas être tamponné deux fois à la même date." }
                    Terme { text: "Clavier" }
                    Definition { text: "Entrée ouvre le détail du dossier sélectionné, Suppr (ou Retour arrière) arrête son suivi après confirmation\u00a0; clic droit pour toutes les actions." }
                }

                FeuilleNotice {
                    titre: "Les réglages"
                    Terme { text: "Avis de mise à jour" }
                    Definition { text: "Tamponné cherche une nouvelle version à chaque démarrage\u00a0; une pastille sur l'onglet Réglages la signale. «\u00a0Installer et redémarrer\u00a0» l'applique tout de suite, «\u00a0Au prochain lancement\u00a0» plus tard. Si la nouvelle version ne démarre pas, la précédente est remise en place." }
                    Terme { text: "Raccourci" }
                    Definition { text: "Ajoute Tamponné au menu des applications (question posée au premier lancement). Si le dossier de Tamponné est déplacé, le raccourci se met à jour d'un clic." }
                    Terme { text: "Sauvegarde" }
                    Definition { text: "Exporter réunit fiches, dossiers suivis, offres vues et réglages dans un fichier .zip\u00a0; Importer remplace toutes les données par celles d'un tel fichier, après confirmation, et garde une copie des anciennes." }
                    Terme { text: "Maintenance" }
                    Definition { text: "Exports de recherche\u00a0: nombre et taille des pages HTML exportées depuis le registre, avec de quoi ouvrir leur dossier ou les supprimer toutes." }
                    Terme { text: "Classement" }
                    Definition { text: "Thème jour, nuit ou celui du système, animations réduites, et liste des organisations\u00a0: rechargée d'elle-même tous les 7\u00a0jours, «\u00a0Rafraîchir le cache\u00a0» la recharge tout de suite." }
                }

                FeuilleNotice {
                    titre: "Raccourcis et données"
                    Terme { text: "Menus et clavier" }
                    Definition { text: "Fichier\u00a0› Nouvelle recherche (Ctrl+N), Suivi de candidature, Quitter (Ctrl+Q)\u00a0; Aide\u00a0› Aide de Tamponné. Sur Mac, Ctrl correspond à Cmd." }
                    Terme { text: "Bureau de nuit" }
                    Definition { text: "Le bouton en haut à droite passe du thème jour au thème nuit, comme le réglage Thème." }
                    Terme { text: "Où sont mes données\u00a0?" }
                    Definition { text: "Tout reste dans le dossier de Tamponné\u00a0: données dans «\u00a0data\u00a0», pages exportées dans «\u00a0exports\u00a0». Le dossier peut être déplacé ou copié tel quel\u00a0; pour changer d'ordinateur, la Sauvegarde suffit." }
                }
            }
        }
    }
}
