import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Interrupteur jour/nuit : le libellé annonce le bureau vers lequel
    on bascule, l'aspect plein signale le bureau de nuit en cours. */
AbstractButton {
    id: racine

    property bool allumee: false

    text: allumee ? "Bureau de jour" : "Bureau de nuit"
    // 44 px utiles + bordures de 1,5 px (content-box), rendus sur 46 px par le navigateur.
    implicitHeight: 46
    implicitWidth: libelle.implicitWidth + 32
    focusPolicy: Qt.StrongFocus

    Accessible.role: Accessible.Button
    Accessible.name: text

    background: Rectangle {
        radius: height / 2
        color: racine.allumee ? Theme.logo : "transparent"
        border.color: racine.allumee ? Theme.logo : Theme.sousLogo
        border.width: 1.5

        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -6
            radius: height / 2
            color: "transparent"
            border.color: Theme.logo
            border.width: 3
        }
    }

    contentItem: Text {
        id: libelle
        text: racine.text
        color: racine.allumee ? Theme.bureau : Theme.logo
        font.family: Theme.policeMono
        font.pixelSize: 14
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
