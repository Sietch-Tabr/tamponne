pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import Tamponne

/*! Liste déroulante soulignée ; la liste ouverte est une petite feuille
    cerclée d'encre où le choix courant est surligné. Modèle : liste de
    `{ cle, libelle }` ou de simples textes. */
ComboBox {
    id: racine

    implicitHeight: 42
    leftPadding: 2
    rightPadding: 24
    textRole: "libelle"
    valueRole: "cle"
    font.family: Theme.policeTexte
    font.pixelSize: 16

    Accessible.role: Accessible.ComboBox
    Accessible.name: displayText

    contentItem: Text {
        text: racine.displayText
        color: Theme.encre
        font: racine.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: racine.width - width - 2
        anchors.verticalCenter: parent.verticalCenter
        text: "▾"
        color: Theme.encre
        font.pixelSize: 16
    }

    background: Item {
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 2
            color: Theme.encre
        }
        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -5
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }

    delegate: ItemDelegate {
        id: choix
        required property var modelData
        required property int index

        width: ListView.view ? ListView.view.width : 0
        implicitHeight: 40
        leftPadding: 12
        highlighted: racine.highlightedIndex === index

        contentItem: Text {
            text: typeof choix.modelData === "string" ? choix.modelData : choix.modelData.libelle
            color: choix.highlighted || racine.currentIndex === choix.index ? Theme.surligneTexte : Theme.encre
            font.family: Theme.policeTexte
            font.pixelSize: 16
            font.weight: racine.currentIndex === choix.index ? Font.Bold : Font.Normal
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: choix.highlighted || racine.currentIndex === choix.index ? Theme.surligneur : Theme.papier
        }
    }

    popup: Popup {
        y: racine.height + 4
        width: racine.width
        implicitHeight: Math.min(contentItem.implicitHeight + 11, 360)
        padding: 5.5

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: racine.popup.visible ? racine.delegateModel : null
            currentIndex: racine.highlightedIndex
        }

        background: Item {
            RectangularShadow {
                anchors.fill: parent
                offset.y: 10
                blur: 22
                color: Theme.ombrePortee
            }
            Rectangle {
                anchors.fill: parent
                color: Theme.papier
                border.color: Theme.encre
                border.width: 1.5
            }
        }
    }
}
