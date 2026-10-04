import QtQuick
import QtQuick.Effects
import Tamponne

/*! Feuille de papier posée dans la chemise : arête franche de 2 px sous
    la feuille et halo flou, comme le double `box-shadow` de la maquette. */
Item {
    id: racine

    property color couleur: Theme.papier
    property color halo: Theme.ombrePorteeLegere
    property real flou: 22
    property real decalageHalo: 10
    default property alias contenu: interieur.data

    RectangularShadow {
        anchors.fill: parent
        offset.y: racine.decalageHalo
        blur: racine.flou
        color: racine.halo
    }
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 2
        anchors.bottomMargin: -2
        color: Theme.ombre
    }
    Rectangle {
        anchors.fill: parent
        color: racine.couleur
    }
    Item {
        id: interieur
        anchors.fill: parent
    }
}
