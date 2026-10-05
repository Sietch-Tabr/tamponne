import QtQuick
import Tamponne

/*! Cadre en tirets (`border: dashed` de la maquette), que `Rectangle` ne
    sait pas dessiner : un trait ajusté par côté, comme le navigateur. */
Item {
    id: racine

    property color couleur: Theme.pointille
    property real epaisseur: 2

    Pointilles {
        width: racine.width
        couleur: racine.couleur
        epaisseur: racine.epaisseur
        style: "dashed"
        coin: racine.epaisseur
    }
    Pointilles {
        y: racine.height - trait
        width: racine.width
        couleur: racine.couleur
        epaisseur: racine.epaisseur
        style: "dashed"
        coin: racine.epaisseur
    }
    Pointilles {
        height: racine.height
        vertical: true
        couleur: racine.couleur
        epaisseur: racine.epaisseur
        style: "dashed"
        coin: racine.epaisseur
    }
    Pointilles {
        x: racine.width - trait
        height: racine.height
        vertical: true
        couleur: racine.couleur
        epaisseur: racine.epaisseur
        style: "dashed"
        coin: racine.epaisseur
    }
}
