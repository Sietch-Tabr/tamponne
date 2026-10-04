import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Shapes
import Tamponne

/*! Action tertiaire « annotation au crayon » : texte à chasse fixe
    souligné en pointillés (QML ne sait souligner qu'en trait plein). */
AbstractButton {
    id: racine

    property color encre: Theme.encre

    implicitHeight: 44
    implicitWidth: libelle.implicitWidth + leftPadding + rightPadding
    leftPadding: 6
    rightPadding: 6
    focusPolicy: Qt.StrongFocus

    Accessible.role: Accessible.Button
    Accessible.name: text

    contentItem: Item {
        Text {
            id: libelle
            anchors.verticalCenter: parent.verticalCenter
            text: racine.text
            color: racine.encre
            font.family: Theme.policeMono
            font.pixelSize: 14
        }
        Shape {
            x: libelle.x
            y: libelle.y + libelle.baselineOffset + 4
            width: libelle.implicitWidth
            height: 1.5
            ShapePath {
                strokeColor: racine.encre
                strokeWidth: 1.5
                strokeStyle: ShapePath.DashLine
                dashPattern: [1, 1]
                fillColor: "transparent"
                startX: 0
                startY: 0.75
                PathLine { x: libelle.implicitWidth; y: 0.75 }
            }
        }
    }

    background: Rectangle {
        color: "transparent"
        border.color: Theme.tampon
        border.width: racine.visualFocus ? 3 : 0
    }
}
