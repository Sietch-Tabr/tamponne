import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Shapes
import Tamponne

/*! Barre de menus Fichier / Aide en bande bristol, dessinée dans la
    fenêtre sur les trois OS (barre native désactivée au démarrage par
    `Qt.AA_DontUseNativeMenuBar`, voir src/gui/application.py). */
MenuBar {
    id: racine

    signal nouvelleRecherche()
    signal ouvrirSuivi()
    signal ouvrirAide()

    leftPadding: 18
    rightPadding: 18
    // Entrées sous le filet rouge de 3 px et au-dessus de la ligne bleue de 1 px.
    topPadding: 3
    bottomPadding: 1

    background: Rectangle {
        implicitHeight: 44
        color: Theme.bristol

        Rectangle {
            width: parent.width
            height: 3
            color: Theme.bristolTete
        }
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Theme.bristolLigne
        }
    }

    delegate: MenuBarItem {
        id: entree

        implicitHeight: 40
        leftPadding: 14
        rightPadding: 14

        contentItem: Text {
            text: entree.text.replace("&", "")
            color: entree.highlighted ? Theme.surligneTexte : Theme.encre
            font.family: Theme.policeTexte
            font.pixelSize: 15
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 1
            font.variableAxes: { "wdth": 85, "wght": 800 }
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: entree.highlighted ? Theme.surligneur : "transparent"
        }
    }

    MenuFiche {
        title: qsTr("&Fichier")
        Action {
            text: qsTr("&Nouvelle recherche")
            shortcut: "Ctrl+N"
            onTriggered: racine.nouvelleRecherche()
        }
        Action {
            text: qsTr("&Suivi de candidature")
            onTriggered: racine.ouvrirSuivi()
        }
        MenuSeparator {
            leftPadding: 16
            rightPadding: 16
            contentItem: Shape {
                // Rendue en texture : une Shape échappe sinon au découpage d'une zone défilante.
                layer.enabled: true
                layer.samples: 4
                id: pointilles
                implicitWidth: 288
                implicitHeight: 13
                ShapePath {
                    strokeColor: Theme.encre2
                    strokeWidth: 1.5
                    strokeStyle: ShapePath.DashLine
                    dashPattern: [2, 2]
                    fillColor: "transparent"
                    startX: 0
                    startY: 6.5
                    PathLine { x: 288; y: 6.5 }
                }
            }
        }
        Action {
            text: qsTr("&Quitter")
            shortcut: "Ctrl+Q"
            onTriggered: Qt.quit()
        }
    }

    MenuFiche {
        title: qsTr("&Aide")
        Action {
            text: qsTr("&Aide de Tamponné")
            onTriggered: racine.ouvrirAide()
        }
    }
}
