import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import Tamponne

/*! Fenêtre modale en feuille de papier : bord kraft en tête, titre en
    capitales souligné d'encre, pied de boutons alignés à droite, voile
    sur le bureau. */
Popup {
    id: racine

    property string titre: ""
    property bool alerte: false
    /*! Contenu entre le titre et le pied. */
    default property alias contenu: corps.data
    /*! Boutons du pied, de gauche à droite, alignés à droite. */
    property alias boutons: rangeeBoutons.data
    /*! Vrai si l'appelant place lui-même un ressort parmi ses boutons
        (bouton détaché à gauche). */
    property bool ressortManuel: false
    /*! Croix en haut à droite : une fenêtre dont le pied déborderait reste
        fermable. */
    property bool croixFermeture: false

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    dim: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    topPadding: 28
    bottomPadding: 22
    leftPadding: 24
    rightPadding: 24

    /*! Nom annoncé par les lecteurs d'écran (le titre par défaut). */
    property string nomAccessible: titre

    Overlay.modal: Rectangle {
        color: Theme.voile
    }

    background: Item {
        RectangularShadow {
            anchors.fill: parent
            offset.y: 18
            blur: 40
            color: Theme.ombreDialogue
        }
        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 2
            anchors.bottomMargin: -2
            color: Theme.ombre
        }
        Rectangle {
            anchors.fill: parent
            color: Theme.papier
        }
        Rectangle {
            width: parent.width
            height: 6
            color: Theme.kraft
        }
        AbstractButton {
            visible: racine.croixFermeture
            x: parent.width - width - 4
            y: 8
            width: 26
            height: 24
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.role: Accessible.Button
            Accessible.name: "Fermer la fenêtre"
            onClicked: racine.close()

            contentItem: Text {
                text: "\u2715"
                color: Theme.encre
                opacity: parent.hovered || parent.visualFocus ? 1 : 0.65
                font.family: Theme.policeTexte
                font.pixelSize: 15
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: "transparent"
                border.color: Theme.tampon
                border.width: parent.visualFocus ? 2 : 0
                radius: 3
            }
        }
    }

    contentItem: ColumnLayout {
        spacing: 14

        Accessible.role: racine.alerte ? Accessible.AlertMessage : Accessible.Dialog
        Accessible.name: racine.nomAccessible

        Texte {
            id: titreTexte
            Layout.fillWidth: true
            visible: racine.titre !== ""
            text: racine.titre
            font.pixelSize: 26
            font.capitalization: Font.AllUppercase
            font.variableAxes: { "wdth": 80, "wght": 800 }
            lineHeight: Math.round(26 * 1.05)
            bottomPadding: 10
            Accessible.role: Accessible.Heading

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 2
                color: Theme.encre
            }
        }

        ColumnLayout {
            id: corps
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.regle
        }

        RowLayout {
            id: rangeeBoutons
            Layout.fillWidth: true
            spacing: 14

            Item {
                visible: !racine.ressortManuel
                Layout.fillWidth: true
            }
        }
    }
}
