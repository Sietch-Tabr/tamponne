import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Shapes
import Tamponne

/*! Bouton secondaire en étiquette kraft : œillet à gauche, perforation
    pointillée, bord droit arrondi. */
AbstractButton {
    id: racine

    /*! Couleur vue à travers l'œillet (le support de l'étiquette). */
    property color trou: Theme.papier

    implicitHeight: 44
    implicitWidth: libelle.implicitWidth + leftPadding + rightPadding + 3
    leftPadding: 37.5
    rightPadding: 17.5
    focusPolicy: Qt.StrongFocus
    hoverEnabled: true

    Accessible.role: Accessible.Button
    Accessible.name: text

    background: Rectangle {
        color: racine.hovered ? Theme.etiquetteSurvol : Theme.etiquette
        border.color: Theme.encre2
        border.width: 1.5
        topLeftRadius: 3
        bottomLeftRadius: 3
        topRightRadius: 8
        bottomRightRadius: 8

        Rectangle {
            // Œillet : 8 px de diamètre intérieur, contour de la couleur du texte.
            x: 11.5
            anchors.verticalCenter: parent.verticalCenter
            width: 11
            height: 11
            radius: 5.5
            color: racine.trou
            border.color: Theme.encre
            border.width: 1.5
        }
        Shape {
            x: 27.5
            y: 8.5
            width: 1.5
            height: parent.height - 17
            ShapePath {
                strokeColor: Theme.encre2
                strokeWidth: 1.5
                strokeStyle: ShapePath.DashLine
                dashPattern: [3, 2]
                fillColor: "transparent"
                startX: 0.75
                startY: 0
                PathLine { x: 0.75; y: racine.height - 17 }
            }
        }
        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -5
            radius: 10
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }

    contentItem: Text {
        id: libelle
        text: racine.text
        color: Theme.encre
        font.family: Theme.policeTexte
        font.pixelSize: 16
        font.weight: Font.Bold
        verticalAlignment: Text.AlignVCenter
    }
}
