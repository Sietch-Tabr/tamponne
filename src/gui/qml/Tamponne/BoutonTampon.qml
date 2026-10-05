import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Bouton principal en coup de tampon : aplat d'encre, double filet,
    légèrement penché ; se redresse au survol et s'écrase au clic. */
AbstractButton {
    id: racine

    property color couleur: Theme.tampon
    property color surCouleur: Theme.surTampon

    implicitHeight: 48
    implicitWidth: libelle.implicitWidth + leftPadding + rightPadding
    leftPadding: 22
    rightPadding: 22
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    rotation: !enabled || hovered || Theme.reduireAnimations ? 0 : -1
    scale: pressed && !Theme.reduireAnimations ? 0.97 : 1

    Behavior on rotation {
        enabled: !Theme.reduireAnimations
        NumberAnimation { duration: 120 }
    }
    Behavior on scale {
        enabled: !Theme.reduireAnimations
        NumberAnimation { duration: 120 }
    }

    Accessible.role: Accessible.Button
    Accessible.name: text

    background: Item {
        Rectangle {
            // Filet extérieur à 3 px (outline CSS), remplacé par l'encre au focus clavier.
            anchors.fill: parent
            anchors.margins: racine.visualFocus ? -6 : -5
            radius: 6
            color: "transparent"
            border.width: racine.visualFocus ? 3 : 2
            border.color: racine.visualFocus ? Theme.encre : (racine.enabled ? racine.couleur : Theme.encre2)
        }
        Rectangle {
            anchors.fill: parent
            radius: 3
            color: racine.enabled ? racine.couleur : Theme.papier2

            Rectangle {
                anchors.fill: parent
                anchors.margins: 3
                radius: 1
                color: "transparent"
                border.width: 1.5
                border.color: racine.enabled ? racine.surCouleur : Theme.encre2
            }
        }
    }

    contentItem: Text {
        id: libelle
        text: racine.text
        color: racine.enabled ? racine.surCouleur : Theme.encre
        font.family: Theme.policeTexte
        font.pixelSize: 16
        font.capitalization: Font.AllUppercase
        font.letterSpacing: 1.2
        font.variableAxes: { "wdth": 85, "wght": 800 }
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
