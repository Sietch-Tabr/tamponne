import QtQuick
import QtQuick.Shapes
import Tamponne

/*! Filet horizontal en pointillés d'1 px (`border-bottom: 1px dotted`). */
Shape {
    id: racine

    // Rendue en texture : une Shape échappe sinon au découpage d'une zone défilante.
    layer.enabled: true
    layer.samples: 4

    property color couleur: Theme.encre2

    implicitHeight: 1

    ShapePath {
        strokeColor: racine.couleur
        strokeWidth: 1
        strokeStyle: ShapePath.DashLine
        dashPattern: [1, 2]
        fillColor: "transparent"
        startX: 0
        startY: 0.5
        PathLine { x: racine.width; y: 0.5 }
    }
}
