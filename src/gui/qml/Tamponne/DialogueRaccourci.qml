import QtQuick
import QtQuick.Layouts
import Tamponne

/*! Question du raccourci posée au démarrage : le proposer au premier
    lancement (« Non » / « Ajouter »), ou le mettre à jour après un
    déplacement du dossier (« Retirer » détaché à gauche, « Non »,
    « Mettre à jour »). */
Dialogue {
    id: racine

    /*! `premier_lancement` ou `deplace` (`ControleurReglages.question_raccourci`). */
    property string question: "premier_lancement"
    readonly property bool deplace: question === "deplace"

    signal ajoutDemande()
    signal retraitDemande()
    signal refus()

    function demander(nouvelleQuestion: string) {
        question = nouvelleQuestion
        open()
        boutonNon.forceActiveFocus()
    }

    titre: deplace ? "Dossier déplacé" : "Raccourci"
    width: deplace ? 500 : 400
    ressortManuel: deplace

    Texte {
        Layout.fillWidth: true
        text: racine.deplace
            ? "Tamponné a changé de dossier depuis la création du raccourci, qui ne le trouve plus. Mettre à jour le raccourci\u00a0?"
            : "Ajouter Tamponné au menu des applications\u00a0? Vous pourrez le retirer à tout moment dans Réglages."
        lineHeight: Math.round(16 * 1.55)
    }

    boutons: [
        BoutonEtiquette {
            objectName: "boutonRetirerRaccourci"
            visible: racine.deplace
            text: "Retirer"
            onClicked: {
                racine.close()
                racine.retraitDemande()
            }
        },
        Item {
            visible: racine.deplace
            Layout.fillWidth: true
        },
        BoutonEtiquette {
            id: boutonNon
            text: "Non"
            onClicked: {
                racine.close()
                racine.refus()
            }
        },
        BoutonTampon {
            objectName: "boutonAjouterRaccourci"
            Layout.margins: 4
            text: racine.deplace ? "Mettre à jour" : "Ajouter"
            onClicked: {
                racine.close()
                racine.ajoutDemande()
            }
        }
    ]
}
