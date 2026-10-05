import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Shapes
import Tamponne

/*! Case à cocher du formulaire : carré cerclé d'encre, coche pleine à
    l'encre de tampon (la couleur seule ne suffirait pas à distinguer
    l'état coché). */
AbstractButton {
    id: racine

    property real hauteurMinimale: 36
    /*! État affiché, lié par l'appelant (l'état réel vit côté Python) ;
        un clic émet `clicked` sans modifier la liaison. */
    property bool coche: false
    /*! Groupe dont une partie seulement est cochée : trait d'encre. */
    property bool partiel: false
    /*! Libellé de groupe (fenêtres de sélection) : graisse 800, largeur 90 %. */
    property bool gras: false
    /*! Écart réservé après la case dans un `Flow` (colonnes à 18 px, lignes à 2 px). */
    property real ecartApres: 0
    /*! Libellé long renvoyé à la ligne au lieu d'être tronqué (Réglages). */
    property bool retourLigne: false
    /*! Filet pointillé sous la case (`border-bottom: 1px dotted`), compté
        dans la hauteur comme une bordure CSS. */
    property bool filet: false

    implicitHeight: Math.max(hauteurMinimale, libelle.implicitHeight) + bottomPadding
    bottomPadding: filet ? 1 : 0
    // Le libellé porte déjà la marge de 30 px réservée à la case.
    implicitWidth: libelle.implicitWidth + ecartApres
    focusPolicy: Qt.StrongFocus

    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    Accessible.checkable: true
    Accessible.checked: coche
    Accessible.description: partiel && !coche ? "en partie coché" : ""

    background: LignePointillee {
        visible: racine.filet
        y: racine.height - 1
        width: racine.width
        couleur: Theme.regle
    }

    indicator: Rectangle {
        x: 0
        y: (racine.height - racine.bottomPadding - height) / 2
        width: 20
        height: 20
        color: Theme.papier
        border.color: Theme.encre
        border.width: 2

        Shape {
            // Rendue en texture : une Shape échappe sinon au découpage d'une zone défilante.
            layer.enabled: true
            layer.samples: 4
            // Coche de la maquette : polygone clip-path dans un carré de 13 px.
            visible: racine.coche
            x: 3.5
            y: 3.5
            width: 13
            height: 13
            ShapePath {
                strokeWidth: -1
                fillColor: Theme.tampon
                startX: 13 * 0.14; startY: 13 * 0.44
                PathLine { x: 0; y: 13 * 0.65 }
                PathLine { x: 13 * 0.50; y: 13 }
                PathLine { x: 13; y: 13 * 0.16 }
                PathLine { x: 13 * 0.80; y: 0 }
                PathLine { x: 13 * 0.43; y: 13 * 0.62 }
                PathLine { x: 13 * 0.14; y: 13 * 0.44 }
            }
        }
        Rectangle {
            visible: racine.partiel && !racine.coche
            anchors.centerIn: parent
            width: 12
            height: 3
            color: Theme.tampon
        }
        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -5
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }

    contentItem: Texte {
        id: libelle
        leftPadding: 30
        text: racine.text
        wrapMode: racine.retourLigne ? Text.Wrap : Text.NoWrap
        elide: racine.retourLigne ? Text.ElideNone : Text.ElideRight
        font.variableAxes: racine.gras ? { "wdth": 90, "wght": 800 } : { "wdth": 100, "wght": 400 }
        Accessible.ignored: true
    }
}
