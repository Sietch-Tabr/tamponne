import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Shapes
import Tamponne

/*! Ligne du formulaire qui ouvre une fenêtre de sélection : intitulé à
    gauche, valeur à chasse fixe à droite (« tous › », « 2 cochés › »),
    filet pointillé dessous. */
AbstractButton {
    id: racine

    property string valeur: ""

    implicitHeight: 40
    focusPolicy: Qt.StrongFocus

    Accessible.role: Accessible.Button
    Accessible.name: text + " : " + valeur

    contentItem: Item {
        Texte {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: racine.text
            wrapMode: Text.NoWrap
            Accessible.ignored: true
        }
        Texte {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: racine.valeur + " ›"
            font.family: Theme.policeMono
            font.pixelSize: 14
            wrapMode: Text.NoWrap
            Accessible.ignored: true
        }
    }

    background: Item {
        Shape {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            ShapePath {
                strokeColor: Theme.encre2
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                dashPattern: [1, 2]
                fillColor: "transparent"
                startX: 0
                startY: 0.5
                PathLine { x: racine.width; y: 0.5 }
            }
        }
        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -2
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }
}
