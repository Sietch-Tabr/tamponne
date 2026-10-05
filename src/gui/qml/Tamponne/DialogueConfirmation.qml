import QtQuick
import QtQuick.Layouts
import Tamponne

/*! Demande de confirmation d'une action destructrice : « Non » prend le
    focus, « Oui » est un tampon rouge. */
Dialogue {
    id: racine

    property string message: ""

    signal confirme()

    alerte: true
    width: 380

    function demander(titreFenetre: string, texte: string) {
        titre = titreFenetre
        message = texte
        open()
        boutonNon.forceActiveFocus()
    }

    Texte {
        Layout.fillWidth: true
        text: racine.message
        lineHeight: Math.round(16 * 1.55)
    }

    boutons: [
        BoutonEtiquette {
            id: boutonNon
            text: "Non"
            onClicked: racine.close()
        },
        BoutonTampon {
            Layout.margins: 4
            text: "Oui"
            couleur: Theme.rouge
            onClicked: {
                racine.close()
                racine.confirme()
            }
        }
    ]
}
