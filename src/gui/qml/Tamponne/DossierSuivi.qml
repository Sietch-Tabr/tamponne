pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Dossier de candidature de l'écran Suivi : référence, titre, statut en
    texte droit, actions au crayon, historique en tampons et post-it de
    relance. Les données viennent d'une ligne de `ModeleDossiers`. */
Feuille {
    id: racine

    required property string reference
    required property string titre
    required property string employeurLieu
    required property string statut
    required property var tampons
    required property int joursSansNouvelles
    required property bool disponible
    /*! Offre retirée d'un dossier encore ouvert : le poste est probablement pourvu. */
    required property bool depublicationASignaler
    required property string depublieeLe

    signal voirOffre(string reference)
    signal voirArchive(string reference)
    signal detail(string reference)
    signal ajouterEvenement(string reference)
    /*! Clic sur un tampon de l'historique : modifier ou supprimer l'événement. */
    signal modifierEvenement(string reference, int indice)
    signal supprimer(string reference)
    /*! Clic droit : position dans le dossier, pour ouvrir le menu. */
    signal menuDemande(string reference, bool disponible, real x, real y)

    /*! Dossier courant de la liste quand celle-ci a le focus clavier. */
    property bool courant: false

    readonly property bool relance: joursSansNouvelles >= 0
    /*! Un seul post-it : la dépublication prime sur la relance (relancer pour
        un poste pourvu n'a plus de sens). */
    readonly property bool postitVisible: depublicationASignaler || relance
    readonly property color fondDossier: disponible ? Theme.papier : Theme.papierGrise

    couleur: fondDossier
    implicitHeight: entete.implicitHeight + 4 + Math.max(colonne.implicitHeight, historique.implicitHeight + 8) + 18

    Accessible.role: Accessible.Grouping
    Accessible.name: titre

    function echapper(texte: string): string {
        return texte.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: (souris) => racine.menuDemande(racine.reference, racine.disponible, souris.x, souris.y)
    }

    Rectangle {
        visible: racine.courant
        anchors.fill: parent
        anchors.margins: -5
        color: "transparent"
        border.color: Theme.tampon
        border.width: 3
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 14
        anchors.bottomMargin: 4
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 4

        // Titre à gauche, référence à droite comme sur la couverture d'un dossier ;
        // à gauche du post-it quand il y en a un.
        RowLayout {
            id: entete
            Layout.fillWidth: true
            Layout.rightMargin: racine.postitVisible ? 190 : 0
            spacing: 24

            Texte {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                text: racine.titre
                font.pixelSize: 22
                font.variableAxes: { "wdth": 90, "wght": 800 }
                Accessible.role: Accessible.Heading
            }
            Texte {
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 5
                text: "Réf. " + racine.reference
                color: Theme.encre2
                font.family: Theme.policeMono
                font.pixelSize: 14
            }
        }

        RowLayout {
            id: corps
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 24

        ColumnLayout {
            id: colonne
            Layout.fillWidth: true
            Layout.minimumWidth: 320
            Layout.alignment: Qt.AlignTop
            Layout.rightMargin: racine.postitVisible ? 170 : 0
            spacing: 2

            Texte {
                Layout.fillWidth: true
                text: racine.employeurLieu
            }
            Texte {
                Layout.fillWidth: true
                Layout.topMargin: 2
                textFormat: Text.StyledText
                text: "<b>Statut\u00a0:</b> " + racine.echapper(racine.statut)
            }
            Row {
                spacing: 4

                LienCrayon {
                    visible: racine.disponible
                    text: "voir l'offre"
                    onClicked: racine.voirOffre(racine.reference)
                }
                LienCrayon {
                    visible: !racine.disponible
                    text: "archive PDF"
                    onClicked: racine.voirArchive(racine.reference)
                }
                LienCrayon {
                    text: "détail"
                    onClicked: racine.detail(racine.reference)
                }
                LienCrayon {
                    visible: racine.disponible
                    text: "ajouter un événement"
                    onClicked: racine.ajouterEvenement(racine.reference)
                }
                LienCrayon {
                    text: "supprimer"
                    encre: Theme.rouge
                    onClicked: racine.supprimer(racine.reference)
                }
            }
        }

        Flow {
            id: historique
            Layout.alignment: Qt.AlignBottom
            Layout.bottomMargin: 8
            Layout.maximumWidth: 520
            spacing: 14

            Accessible.role: Accessible.List
            Accessible.name: "Historique"

            Repeater {
                model: racine.tampons
                AbstractButton {
                    id: boutonTampon
                    required property var modelData
                    required property int index

                    implicitWidth: tampon.implicitWidth
                    implicitHeight: tampon.implicitHeight
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    Accessible.role: Accessible.Button
                    Accessible.name: (modelData.information ? "Information\u00a0: " : "Modifier l'événement ") + modelData.libelle + " du " + modelData.date
                    // Le constat de dépublication n'est pas un événement : rien à modifier.
                    onClicked: if (!modelData.information) racine.modifierEvenement(racine.reference, modelData.indice)

                    contentItem: Tampon {
                        id: tampon
                        // Inclinaisons de la maquette : premier à -3°, courant à -1° (-2° en refus), suivants alternés.
                        rotation: boutonTampon.index === 0 ? -3 : (boutonTampon.modelData.courant ? (boutonTampon.modelData.refus ? -2 : -1) : (boutonTampon.index % 2 === 1 ? 2 : -2))
                        texte: boutonTampon.modelData.libelle
                        date: boutonTampon.modelData.date
                        fond: racine.fondDossier
                        encre: boutonTampon.modelData.information ? Theme.encre2
                             : boutonTampon.modelData.refus ? Theme.rouge
                             : (boutonTampon.modelData.positif ? Theme.vert
                                : (boutonTampon.modelData.courant ? Theme.tampon : Theme.encre2))
                        taille: boutonTampon.modelData.courant ? (racine.tampons.length === 1 ? 16 : 17) : 14
                        doubleFilet: boutonTampon.modelData.courant && !boutonTampon.modelData.refus
                        Accessible.ignored: true
                    }
                    background: Rectangle {
                        visible: !boutonTampon.modelData.information && (boutonTampon.visualFocus || boutonTampon.hovered)
                        anchors.fill: parent
                        anchors.margins: -6
                        color: "transparent"
                        border.color: Theme.tampon
                        border.width: boutonTampon.visualFocus ? 3 : 1
                        radius: 4
                    }
                }
            }
        }
        }
    }

    Rectangle {
        id: postit
        visible: racine.postitVisible
        x: racine.width - 22 - width
        y: -14
        // 160 px de contenu + 2 × 12 px de marge (boîte CSS en content-box).
        width: 184
        height: contenuPostit.implicitHeight + 26
        rotation: 2
        color: Theme.postit

        Accessible.role: Accessible.Note
        Accessible.name: racine.depublicationASignaler
            ? "Offre dépubliée le " + racine.depublieeLe + ", le poste est probablement pourvu"
            : "Relance suggérée, sans nouvelles depuis " + racine.joursSansNouvelles + " jours"

        Column {
            id: contenuPostit
            x: 12
            y: 12
            width: parent.width - 24

            Text {
                width: parent.width
                text: racine.depublicationASignaler ? "Offre dépubliée" : "Relance suggérée"
                color: Theme.postitTexte
                font.family: Theme.policeTexte
                font.pixelSize: 16
                font.weight: Font.Bold
                lineHeightMode: Text.FixedHeight
                lineHeight: Math.round(16 * 1.3)
                wrapMode: Text.Wrap
            }
            Text {
                width: parent.width
                text: racine.depublicationASignaler
                    ? "le " + racine.depublieeLe + ", poste probablement pourvu"
                    : "sans nouvelles depuis " + racine.joursSansNouvelles + " jours"
                color: Theme.postitTexte
                font.family: Theme.policeMono
                font.pixelSize: 14
                lineHeightMode: Text.FixedHeight
                lineHeight: Math.round(14 * 1.3)
                wrapMode: Text.Wrap
            }
        }
    }
}
