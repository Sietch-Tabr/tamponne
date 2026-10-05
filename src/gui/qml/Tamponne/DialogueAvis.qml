import QtQuick
import QtQuick.Layouts
import Tamponne

/*! Avis du registre (« Candidature suivie », « Export prêt ») : message,
    chemin éventuel à chasse fixe, tampon facultatif, « Fermer » et une
    action principale facultative. */
Dialogue {
    id: racine

    property string message: ""
    /*! Fichier produit (export), affiché dans un cartouche gris. */
    property string chemin: ""
    property string tampon: ""
    /*! Libellé du bouton principal ; vide pour n'afficher que « Fermer ». */
    property string action: ""

    signal actionDemandee()

    width: 400

    Texte {
        Layout.fillWidth: true
        text: racine.message
        lineHeight: Math.round(16 * 1.55)
    }

    Texte {
        Layout.fillWidth: true
        visible: racine.chemin !== ""
        text: racine.chemin
        font.family: Theme.policeMono
        font.pixelSize: 14
        wrapMode: Text.WrapAnywhere
        leftPadding: 10
        rightPadding: 10
        topPadding: 8
        bottomPadding: 8
        lineHeight: Theme.ligneNormale(true, 14)

        Rectangle {
            anchors.fill: parent
            z: -1
            color: Theme.papier2
        }
    }

    boutons: [
        BoutonEtiquette {
            id: boutonFermer
            text: "Fermer"
            onClicked: racine.close()
        },
        BoutonTampon {
            visible: racine.action !== ""
            Layout.margins: 4
            text: racine.action
            onClicked: {
                racine.close()
                racine.actionDemandee()
            }
        }
    ]

    onOpened: boutonFermer.forceActiveFocus()

    Tampon {
        parent: racine.contentItem
        visible: racine.tampon !== ""
        x: parent.width - width
        y: -8
        rotation: -6
        texte: racine.tampon
        taille: 15
        encre: Theme.vert
        Accessible.ignored: true
    }
}
