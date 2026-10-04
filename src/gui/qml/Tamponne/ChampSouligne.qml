import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Champ de saisie souligné d'un trait d'encre, sans cadre. */
TextField {
    id: racine

    property bool mono: false

    implicitHeight: 42
    leftPadding: 2
    rightPadding: 2
    topPadding: 0
    bottomPadding: 0
    color: Theme.encre
    placeholderTextColor: Theme.encre2
    selectionColor: Theme.surligneur
    selectedTextColor: Theme.surligneTexte
    font.family: mono ? Theme.policeMono : Theme.policeTexte
    font.pixelSize: 16
    verticalAlignment: TextInput.AlignVCenter

    Accessible.role: Accessible.EditableText

    background: Item {
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 2
            color: Theme.encre
        }
        Rectangle {
            visible: racine.activeFocus && racine.focusReason !== Qt.MouseFocusReason
            anchors.fill: parent
            anchors.margins: -5
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }
}
