import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Bouton secondaire en étiquette kraft : œillet à gauche, perforation
    pointillée, bord droit arrondi. */
AbstractButton {
    id: racine

    /*! Couleur vue à travers l'œillet (le support de l'étiquette). */
    property color trou: Theme.papier
    /*! Couleur du texte et de l'œillet (rouge pour une action destructrice). */
    property color encre: Theme.encre

    implicitHeight: 44
    // Les marges incluent déjà la bordure de 1,5 px (36 + 1,5 et 16 + 1,5).
    implicitWidth: libelle.implicitWidth + leftPadding + rightPadding
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
            border.color: racine.encre
            border.width: 1.5
        }
        // Perforation : « border-left: 1.5px dashed », left 26 px, top et bottom 7 px.
        Pointilles {
            x: 27.5
            y: 8.5
            height: parent.height - 17
            vertical: true
            couleur: Theme.encre2
            epaisseur: 1.5
            style: "dashed"
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
        color: racine.encre
        font.family: Theme.policeTexte
        font.pixelSize: 16
        font.weight: Font.Bold
        verticalAlignment: Text.AlignVCenter
    }
}
