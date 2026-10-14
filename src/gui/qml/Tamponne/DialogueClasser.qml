import QtQuick
import QtQuick.Layouts
import Tamponne

/*! « Créer une fiche » : la demande de recherche actuelle devient une
    fiche (nom interne et intitulé affiché). */
Dialogue {
    id: racine

    property string erreur: ""

    signal classe(string nom, string intitule)

    titre: "Créer une fiche"
    width: 470

    function ouvrir() {
        erreur = ""
        champNom.text = ""
        champIntitule.text = ""
        open()
        champNom.forceActiveFocus()
    }

    function refuser(message: string) {
        erreur = message
        champNom.forceActiveFocus()
    }

    Texte {
        Layout.fillWidth: true
        text: "La demande de recherche actuelle devient une fiche."
        color: Theme.encre2
        font.family: Theme.policeMono
        font.pixelSize: 14
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        EtiquetteChamp { text: "Nom de la fiche" }
        ChampSouligne {
            id: champNom
            Layout.fillWidth: true
            placeholderText: "ex. dgal-paris"
            Accessible.name: "Nom de la fiche"
            onAccepted: racine.classe(text, champIntitule.text)
        }
        Item { Layout.preferredHeight: 10 }
        EtiquetteChamp { text: "Intitulé affiché" }
        ChampSouligne {
            id: champIntitule
            Layout.fillWidth: true
            placeholderText: "ex. Attaché, Paris et petite couronne"
            Accessible.name: "Intitulé affiché"
            onAccepted: racine.classe(champNom.text, text)
        }
        Texte {
            Layout.fillWidth: true
            visible: racine.erreur !== ""
            text: racine.erreur
            color: Theme.rouge
            font.pixelSize: 14
            Accessible.role: Accessible.AlertMessage
        }
    }

    boutons: [
        BoutonEtiquette {
            text: "Annuler"
            onClicked: racine.close()
        },
        BoutonTampon {
            Layout.margins: 4
            text: "Créer"
            onClicked: racine.classe(champNom.text, champIntitule.text)
        }
    ]
}
