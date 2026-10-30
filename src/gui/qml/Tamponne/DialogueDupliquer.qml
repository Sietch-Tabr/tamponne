import QtQuick
import QtQuick.Layouts
import Tamponne

/*! « Dupliquer la demande » : nom et intitulé de la copie, proposés
    « <nom>-copie » et « <intitulé> (copie) ». */
Dialogue {
    id: racine

    property string nom: ""
    property string intitule: ""
    property string erreur: ""

    /*! Émis à la validation ; l'appelant renvoie un message d'erreur via
        `refuser()` ou ferme la fenêtre. */
    signal duplique(string nom, string nouveauNom, string intituleCopie)

    titre: "Dupliquer la demande"
    width: 470

    function ouvrirPour(nomFiche: string, intituleFiche: string) {
        nom = nomFiche
        intitule = intituleFiche
        erreur = ""
        champNom.text = nomFiche + "-copie"
        champIntitule.text = intituleFiche + " (copie)"
        open()
        champNom.forceActiveFocus()
        champNom.selectAll()
    }

    function refuser(message: string) {
        erreur = message
        champNom.forceActiveFocus()
    }

    Texte {
        Layout.fillWidth: true
        text: "Copie de «\u00a0" + racine.intitule + "\u00a0»"
        color: Theme.encre2
        font.family: Theme.policeMono
        font.pixelSize: 14
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        EtiquetteChamp { text: "Nom de la nouvelle demande" }
        ChampSouligne {
            id: champNom
            objectName: "champNom"
            Layout.fillWidth: true
            Accessible.name: "Nom de la nouvelle demande"
            onAccepted: racine.duplique(racine.nom, text, champIntitule.text)
        }
        Item { Layout.preferredHeight: 10 }
        EtiquetteChamp { text: "Intitulé de la copie" }
        ChampSouligne {
            id: champIntitule
            Layout.fillWidth: true
            Accessible.name: "Intitulé de la copie"
            onAccepted: racine.duplique(racine.nom, champNom.text, text)
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
            text: "Dupliquer"
            onClicked: racine.duplique(racine.nom, champNom.text, champIntitule.text)
        }
    ]
}
