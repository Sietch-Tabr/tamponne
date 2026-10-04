import QtQuick
import QtQuick.Shapes
import Tamponne

/*! Cadre en tirets (`border: dashed` de la maquette), que `Rectangle` ne
    sait pas dessiner. */
Shape {
    id: racine

    // Rendue en texture : une Shape échappe sinon au découpage d'une zone défilante.
    layer.enabled: true
    layer.samples: 4

    property color couleur: Theme.pointille
    property real epaisseur: 2

    // Taille imposée par l'appelant : la taille implicite déduite du tracé bouclerait.
    implicitWidth: 0
    implicitHeight: 0

    ShapePath {
        strokeColor: racine.couleur
        strokeWidth: racine.epaisseur
        strokeStyle: ShapePath.DashLine
        dashPattern: [3, 3]
        fillColor: "transparent"
        startX: racine.epaisseur / 2
        startY: racine.epaisseur / 2
        PathLine { x: racine.width - racine.epaisseur / 2; y: racine.epaisseur / 2 }
        PathLine { x: racine.width - racine.epaisseur / 2; y: racine.height - racine.epaisseur / 2 }
        PathLine { x: racine.epaisseur / 2; y: racine.height - racine.epaisseur / 2 }
        PathLine { x: racine.epaisseur / 2; y: racine.epaisseur / 2 }
    }
}
