pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Écran Aide (« Notice d'utilisation ») : feuilles explicatives, textes
    repris de la maquette. */
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
                    Definition { text: "Niveau hiérarchique du poste : A+ (encadrement supérieur), A (cadre), B (profession intermédiaire), C (employé). Le corps / grade affine la catégorie : Attaché, Attaché principal, Attaché hors classe, Adjoint administratif…" }
                    Terme { text: "Versant" }
                    Definition { text: "La branche de la fonction publique : État, Hospitalier, Territorial. Plusieurs cases à la fois possibles ; aucune cochée = tous les versants." }
                    Terme { text: "Poste et Lieu" }
                    Definition { text: "Domaines, localisations et organisations s'ouvrent dans une fenêtre de sélection avec un champ de recherche : pratique avec 114 localisations et environ 2 400 sous-organisations." }
                    Terme { text: "Type de poste" }
                    Definition { text: "Par défaut, seuls les postes ouverts aux titulaires sont affichés (titulaires + postes ouverts aux deux statuts). Choisir « Tous » pour voir aussi les postes réservés aux contractuels." }
                    Terme { text: "Options" }
                    Definition { text: "Management et Télétravail : cochés = seulement les postes concernés. Le mot-clé cherche dans le titre et le corps de l'offre, pas seulement l'intitulé." }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 22

                    FeuilleNotice {
                        titre: "Exemples de demande"
                        Terme { text: "Attaché principal territorial (Hérault)" }
                        Exemple { text: "Catégorie → A<br>Corps / grade → Attaché principal<br>Versant → Territorial<br>Lieu → Localisation Hérault" }
                        Definition { text: "Le grade repère « attaché principal » dans le titre, quel que soit le versant." }
                        Terme { text: "Chef de projet informatique (État)" }
                        Exemple { text: "Catégorie → A<br>Versant → État<br>Poste → Domaine « Numérique »<br>Options → mot-clé « chef de projet »" }
                        Definition { text: "Pas de grade statutaire pour ce métier : le mot-clé resserre sur l'intitulé." }
                    }

                    FeuilleNotice {
                        titre: "Grades supérieurs (IDIV / IP / AFIPA)"
                        Definition { text: "Par défaut, les offres dont le titre commence par un grade d'encadrement supérieur de la DGFiP (IDIV, AFIPA, IP suivi d'une majuscule, ex. IPFiP) sont écartées du registre : postes très spécifiques, peu pertinents pour une recherche large. Cocher « Grades supérieurs » dans la demande pour les voir quand même." }
                    }
                }

                FeuilleNotice {
                    titre: "Les fiches de recherche"
                    Definition { text: "Une fiche, c'est une demande de recherche classée sous un nom, avec « Classer en profil »." }
                    Terme { text: "Lancer" }
                    Definition { text: "Lance la recherche immédiatement (double-clic sur la fiche aussi)." }
                    Terme { text: "Nouvelles" }
                    Definition { text: "Chaque jour, au premier lancement, les fiches sont relevées en arrière-plan\u00a0: le tampon rouge compte les offres pas encore consultées dans le registre, daté du relevé. Lancer la fiche les marque consultées." }
                    Terme { text: "modifier · dupliquer · supprimer" }
                    Definition { text: "Change les cases sans lancer, copie la fiche sous un autre nom, ou la jette (confirmation demandée)." }
                }

                FeuilleNotice {
                    titre: "Les dossiers de suivi"
                    Definition { text: "Dans le registre, sélectionner une offre puis « Tamponner pour suivi » ouvre un dossier et archive la fiche de poste en PDF. Le statut est toujours celui du dernier tampon de l'historique." }
                    Terme { text: "Relance suggérée" }
                    Definition { text: "Post-it collé quand rien ne s'est passé depuis 3 semaines et que le dossier n'est pas clos (réponse positive ou refus)." }
                    Terme { text: "Offre dépubliée" }
                    Definition { text: "L'offre a disparu du site (« Vérifier les offres ») ; la copie archivée reste consultable." }
                    Terme { text: "Tampons" }
                    Definition { text: "Un clic sur un tampon de l'historique permet de modifier ou de supprimer l'événement ; un même événement ne peut pas être tamponné deux fois à la même date." }
                    Terme { text: "Clavier" }
                    Definition { text: "Entrée ouvre le détail du dossier sélectionné, Suppr arrête son suivi ; clic droit pour toutes les actions." }
                }
            }
        }
    }
}
