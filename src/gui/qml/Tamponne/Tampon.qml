import QtQuick
import Tamponne

/*! Coup de tampon : cadre encré, texte en capitales condensées et date
    facultative. L'encre est mélangée au fond uni sur lequel le tampon est
    posé (`fond`), comme le `mix-blend-mode` de la maquette. */
Item {
    id: racine

    property string texte: ""
    /*! Petite ligne sous le texte (date JJ/MM/AA de l'historique). */
    property string date: ""
    property color encre: Theme.tampon
    /*! Couleur unie sous le tampon, pour le mélange d'encre. */
    property color fond: Theme.papier
    property bool melange: true
    property real taille: 14
    /*! Filet extérieur des tampons « courants » et du logotype. */
    property bool doubleFilet: false
    property real paddingHorizontal: date !== "" ? 9 : 8
    property real paddingVertical: date !== "" ? 3 : 2

    readonly property color encreVisible: melange ? Theme.melanger(encre, fond) : encre

    implicitWidth: cadre.width
    implicitHeight: cadre.height

    Accessible.role: Accessible.StaticText
    Accessible.name: date !== "" ? texte + " " + date : texte

    Rectangle {
        id: cadre
        width: colonne.implicitWidth + 2 * racine.paddingHorizontal + 5
        height: colonne.implicitHeight + 2 * racine.paddingVertical + 5
        color: "transparent"
        border.color: racine.encreVisible
        border.width: 2.5
        radius: 4

        Column {
            id: colonne
            anchors.centerIn: parent

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: racine.texte
                color: racine.encreVisible
                font.family: Theme.policeTexte
                font.pixelSize: racine.taille
                font.capitalization: Font.AllUppercase
                font.letterSpacing: 1
                font.variableAxes: { "wdth": 85, "wght": 800 }
                lineHeightMode: Text.FixedHeight
                lineHeight: Math.round(racine.taille * (racine.date !== "" ? 1.25 : 1.3))
                verticalAlignment: Text.AlignVCenter
            }
            Text {
                visible: racine.date !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                text: racine.date
                color: racine.encreVisible
                font.family: Theme.policeMono
                font.pixelSize: 13
                font.weight: Font.DemiBold
                lineHeightMode: Text.FixedHeight
                lineHeight: Math.round(13 * 1.25)
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    Rectangle {
        visible: racine.doubleFilet
        anchors.centerIn: cadre
        width: cadre.width + 7
        height: cadre.height + 7
        color: "transparent"
        border.color: racine.encreVisible
        border.width: 1.5
        radius: 6
    }
}
