import QtQuick
import QtQuick.Controls.Basic
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
        // Texte : hauteur de ligne du navigateur (19 px), centrée comme l'inline-flex.
        Texte {
            id: libelle
            // Position fractionnaire : l'ancrage au centre arrondirait 12,5 à 12.
            y: (parent.height - height) / 2
            text: racine.text
            color: racine.encre
            font.family: Theme.policeMono
            font.pixelSize: 14
            wrapMode: Text.NoWrap
            Accessible.ignored: true
        }
        // « text-decoration: underline dotted 1.5px ; text-underline-offset: 4px ».
        Pointilles {
            x: libelle.x
            y: libelle.y + libelle.baselineOffset + 4
            width: libelle.implicitWidth
            couleur: racine.encre
            epaisseur: 1.5
            style: "dotted"
            ajuste: false
        }
    }

    background: Rectangle {
        color: "transparent"
        border.color: Theme.tampon
        border.width: racine.visualFocus ? 3 : 0
    }
}
