import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Menu déroulant dessiné comme une fiche bristol lignée (filet rouge
    en tête, lignes bleues), dans sa propre fenêtre pour déborder de la
    fenêtre principale si besoin. */
Menu {
    id: racine

    popupType: Popup.Window
    topPadding: 6
    bottomPadding: 6

    background: Rectangle {
        implicitWidth: 320
        color: Theme.bristol

        Repeater {
            model: Math.ceil(parent.height / 40)
            Rectangle {
                required property int index
                y: 6 + 39 + index * 40
                width: parent.width
                height: 1
                color: Theme.bristolLigne
            }
        }
        Rectangle {
            width: parent.width
            height: 3
            color: Theme.bristolTete
        }
    }

    delegate: MenuItem {
        id: entree

        implicitHeight: 40
        implicitWidth: 320

        contentItem: Item {
            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: entree.text.replace("&", "")
                color: entree.highlighted ? Theme.surligneTexte : Theme.encre
                font.family: Theme.policeTexte
                font.pixelSize: 16
            }
            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: entree.action && entree.action.shortcut
                      ? (Qt.platform.os === "osx"
                         ? String(entree.action.shortcut).replace("Ctrl+", "⌘")
                         : String(entree.action.shortcut))
                      : ""
                color: entree.highlighted ? Theme.surligneTexte : Theme.encre2
                font.family: Theme.policeMono
                font.pixelSize: 13
            }
        }
        leftPadding: 16
        rightPadding: 16

        background: Rectangle {
            color: entree.highlighted ? Theme.surligneur : "transparent"
        }
    }
}
