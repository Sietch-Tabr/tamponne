import QtQuick
import Tamponne

/*! Logotype « Tamponné » : tampon à double filet posé sur le bureau. */
Item {
    id: racine

    // Le filet extérieur déborde sans occuper de place, comme un `outline` CSS.
    implicitWidth: cadre.width
    implicitHeight: cadre.height
    rotation: -3

    Accessible.role: Accessible.Heading
    Accessible.name: "Tamponné"

    Rectangle {
        id: filetExterieur
        anchors.centerIn: parent
        width: cadre.width + 9
        height: cadre.height + 9
        color: "transparent"
        border.color: Theme.logo
        border.width: 1.5
        radius: 7
    }

    Rectangle {
        id: cadre
        anchors.centerIn: parent
        width: texte.implicitWidth + 21
        height: texte.implicitHeight + 9
        color: "transparent"
        border.color: Theme.logo
        border.width: 2.5
        radius: 4

        Text {
            id: texte
            anchors.centerIn: parent
            text: "Tamponné"
            color: Theme.logo
            font.family: Theme.policeTexte
            font.pixelSize: 26
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 1
            font.variableAxes: { "wdth": 85, "wght": 800 }
            lineHeightMode: Text.FixedHeight
            lineHeight: Math.round(26 * 1.3)
            verticalAlignment: Text.AlignVCenter
            Accessible.ignored: true
        }
    }
}
