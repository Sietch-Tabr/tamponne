import QtQuick
import QtQuick.Layouts
import Tamponne

/*! « Ajouter un événement » à l'historique d'un dossier : type, date et
    note facultative ; « Tamponner » enregistre. */
Dialogue {
    id: racine

    /*! Types proposés : liste de `{ cle, libelle }`. */
    property var types: []
    property string reference: ""
    property string titreDossier: ""

    /*! Émis à la validation, date au format ISO `YYYY-MM-DD`. */
    signal tamponne(string reference, string typeEvenement, string dateIso, string note)

    titre: "Ajouter un événement"
    width: 470

    function ouvrirPour(referenceDossier: string, titreOffre: string) {
        reference = referenceDossier
        titreDossier = titreOffre
        champType.currentIndex = 0
        champDate.dateChoisie = new Date()
        champNote.text = ""
        open()
        champType.forceActiveFocus()
    }

    Texte {
        Layout.fillWidth: true
        text: racine.titreDossier + " · Réf. " + racine.reference
        color: Theme.encre2
        font.family: Theme.policeMono
        font.pixelSize: 14
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        EtiquetteChamp { text: "Type" }
        ListeDeroulante {
            id: champType
            objectName: "champType"
            Layout.fillWidth: true
            model: racine.types
            Accessible.name: "Type : " + displayText
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        EtiquetteChamp { text: "Date" }
        ChampDate {
            id: champDate
            objectName: "champDate"
            Layout.fillWidth: true
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        EtiquetteChamp { text: "Note (optionnel)" }
        ChampSouligne {
            id: champNote
            Layout.fillWidth: true
            Accessible.name: "Note (optionnel)"
        }
    }

    boutons: [
        BoutonEtiquette {
            text: "Annuler"
            onClicked: racine.close()
        },
        BoutonTampon {
            Layout.margins: 4
            text: "Tamponner"
            onClicked: {
                racine.tamponne(racine.reference, champType.currentValue, champDate.dateIso, champNote.text)
                racine.close()
            }
        }
    ]
}
