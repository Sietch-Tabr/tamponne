import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import Tamponne

/*! Menu du clic droit sur un dossier de suivi. */
Menu {
    id: racine

    property bool disponible: true

    signal voirOffre()
    signal voirArchive()
    signal detail()
    signal ajouterEvenement()
    signal supprimer()

    topPadding: 5.5
    bottomPadding: 5.5

    background: Item {
        implicitWidth: 260
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

    delegate: MenuItem {
        id: entree
        implicitHeight: 40
        implicitWidth: 260
        leftPadding: 14
        rightPadding: 14
        contentItem: Text {
            text: entree.text
            color: entree.highlighted ? Theme.surligneTexte
                 : (entree.text === "Supprimer" ? Theme.rouge : Theme.encre)
            font.family: Theme.policeTexte
            font.pixelSize: 16
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: entree.highlighted ? Theme.surligneur : "transparent"
        }
    }

    Action {
        text: racine.disponible ? "Voir l'offre" : "Archive PDF"
        onTriggered: racine.disponible ? racine.voirOffre() : racine.voirArchive()
    }
    Action {
        text: "Détail"
        onTriggered: racine.detail()
    }
    Action {
        text: "Ajouter un événement"
        enabled: racine.disponible
        onTriggered: racine.ajouterEvenement()
    }
    MenuSeparator {
        topPadding: 4
        bottomPadding: 4
        leftPadding: 0
        rightPadding: 0
        contentItem: Rectangle {
            implicitWidth: 260
            implicitHeight: 1
            color: Theme.regle
        }
    }
    Action {
        text: "Supprimer"
        onTriggered: racine.supprimer()
    }
}
