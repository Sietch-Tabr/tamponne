import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Onglet d'intercalaire du bandeau de navigation. L'onglet
    actif prend la couleur de la chemise et dépasse un peu plus haut. */
AbstractButton {
    id: racine

    property bool actif: false
    /*! Pastille rouge « mise à jour disponible » (onglet Réglages). */
    property bool pastille: false

    implicitHeight: actif ? 52 : 44
    implicitWidth: contenu.implicitWidth + leftPadding + rightPadding
    leftPadding: 18
    rightPadding: 18
    focusPolicy: Qt.StrongFocus

    Accessible.role: Accessible.PageTab
    Accessible.name: pastille ? text + " (mise à jour disponible)" : text
    Accessible.selected: actif

    background: Rectangle {
        topLeftRadius: 10
        topRightRadius: 10
        color: racine.actif ? Theme.kraft : (racine.hovered ? Theme.ongletSurvol : Theme.onglet)

        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -5
            topLeftRadius: 13
            topRightRadius: 13
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }

    contentItem: Row {
        id: contenu
        spacing: 8

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: racine.text
            color: Theme.encre
            font.family: Theme.policeTexte
            font.pixelSize: 16
            font.variableAxes: { "wdth": 90, "wght": 700 }
            Accessible.ignored: true
        }
        Rectangle {
            visible: racine.pastille
            anchors.verticalCenter: parent.verticalCenter
            width: 10
            height: 10
            radius: 5
            color: Theme.rouge
        }
    }
}
