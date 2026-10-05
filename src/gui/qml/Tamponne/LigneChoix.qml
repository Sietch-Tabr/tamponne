import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Ligne du formulaire qui ouvre une fenêtre de sélection : intitulé à
    gauche, valeur à chasse fixe à droite (« tous › », « 2 cochés › »),
    filet pointillé dessous. */
AbstractButton {
    id: racine

    property string valeur: ""

    implicitHeight: 40
    focusPolicy: Qt.StrongFocus

    Accessible.role: Accessible.Button
    Accessible.name: text + " : " + valeur

    contentItem: RowLayout {
        spacing: 12
        Texte {
            text: racine.text
            wrapMode: Text.NoWrap
            Accessible.ignored: true
        }
        Texte {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Layout.preferredWidth: 0
            horizontalAlignment: Text.AlignRight
            text: racine.valeur + " ›"
            font.family: Theme.policeMono
            font.pixelSize: 14
            wrapMode: Text.NoWrap
            // Une organisation au long nom ne doit jamais chevaucher l'intitulé.
            elide: Text.ElideLeft
            Accessible.ignored: true
        }
    }

    background: Item {
        LignePointillee {
            anchors.bottom: parent.bottom
            width: parent.width
        }
        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -2
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }
}
