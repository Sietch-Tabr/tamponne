pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Shapes
import Tamponne

/*! Liste déroulante soulignée ; la liste ouverte est une petite feuille
    cerclée d'encre où le choix courant est surligné. Modèle : liste de
    `{ cle, libelle }` ou de simples textes. */
ComboBox {
    id: racine

    implicitHeight: 42
    // Zone de texte d'un « select » Firefox : 4 px à gauche, coupé à 18 px du bord droit.
    leftPadding: 4
    rightPadding: 18
    textRole: "libelle"
    valueRole: "cle"
    font.family: Theme.policeTexte
    font.pixelSize: 16

    Accessible.role: Accessible.ComboBox
    Accessible.name: displayText

    // Texte coupé net, sans points de suspension, comme un « select » du navigateur.
    contentItem: Text {
        text: racine.displayText
        color: Theme.encre
        font: racine.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideNone
        clip: true
    }

    // Chevron du « select » de Firefox : emprise de 8 × 6 px, à 5 px du bord droit.
    indicator: Shape {
        // Rendue en texture : une Shape échappe sinon au découpage d'une zone défilante.
        layer.enabled: true
        layer.samples: 4
        x: racine.width - 5 - width
        // Centré sur toute la hauteur, bordure basse comprise, comme Firefox.
        y: Math.round((racine.height - height) / 2)
        width: 8
        height: 6
        ShapePath {
            strokeColor: Theme.encre
            strokeWidth: 1.5
            fillColor: "transparent"
            capStyle: ShapePath.FlatCap
            joinStyle: ShapePath.BevelJoin
            startX: 0.5
            startY: 0.75
            PathLine { x: 4; y: 4.75 }
            PathLine { x: 7.5; y: 0.75 }
        }
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
