import QtQuick
import QtQuick.Layouts
import Tamponne

/*! Événement de l'historique d'un dossier : « Ajouter un événement »
    (type et date préremplis sur l'étape suivante) ou « Modifier
    l'événement » (avec suppression). Un doublon est refusé avec un
    message, la fenêtre reste alors ouverte. */
Dialogue {
    id: racine

    /*! Types proposés : liste de `{ cle, libelle }`. */
    property var types: []
    property string reference: ""
    property string titreDossier: ""
    /*! Position de l'événement modifié dans l'historique, -1 en ajout. */
    property int indice: -1
    property string erreur: ""
    readonly property bool modification: indice >= 0

    /*! Ajout validé, date au format ISO `YYYY-MM-DD`. */
    signal tamponne(string reference, string typeEvenement, string dateIso, string note)
    /*! Modification validée. */
    signal enregistre(string reference, int indice, string typeEvenement, string dateIso, string note)
    /*! Suppression demandée (l'appelant confirme). */
    signal suppressionDemandee(string reference, int indice)

    titre: modification ? "Modifier l'événement" : "Ajouter un événement"
    ressortManuel: modification
    width: modification ? 600 : 470

    function dateDepuisIso(iso: string): date {
        const morceaux = iso.split("-")
        return new Date(Number(morceaux[0]), Number(morceaux[1]) - 1, Number(morceaux[2]))
    }

    function preparer(referenceDossier: string, titreOffre: string, typeEvenement: string, dateIso: string, note: string) {
        reference = referenceDossier
        titreDossier = titreOffre
        erreur = ""
        const rang = types.findIndex(t => t.cle === typeEvenement)
        champType.currentIndex = rang >= 0 ? rang : 0
        champDate.dateChoisie = dateIso !== "" ? dateDepuisIso(dateIso) : new Date()
        champNote.text = note
        open()
        champType.forceActiveFocus()
    }

    function ouvrirPour(referenceDossier: string, titreOffre: string, typePropose: string, datePropose: string) {
        indice = -1
        preparer(referenceDossier, titreOffre, typePropose, datePropose, "")
    }

    function modifier(referenceDossier: string, titreOffre: string, indiceEvenement: int, evenement: var) {
        indice = indiceEvenement
        preparer(referenceDossier, titreOffre, evenement.type, evenement.date, evenement.note)
    }

    function refuser(message: string) {
        erreur = message
        champType.forceActiveFocus()
    }

    function valider() {
        if (modification)
            enregistre(reference, indice, champType.currentValue, champDate.dateIso, champNote.text)
        else
            tamponne(reference, champType.currentValue, champDate.dateIso, champNote.text)
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
            onActivated: racine.erreur = ""
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
            onDateChoisieChanged: racine.erreur = ""
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
            onAccepted: racine.valider()
        }
    }

    Texte {
        Layout.fillWidth: true
        visible: racine.erreur !== ""
        text: racine.erreur
        color: Theme.rouge
        font.pixelSize: 14
        Accessible.role: Accessible.AlertMessage
    }

    boutons: [
        BoutonEtiquette {
            visible: racine.modification
            text: "Supprimer l'événement"
            encre: Theme.rougeEtiquette
            onClicked: racine.suppressionDemandee(racine.reference, racine.indice)
        },
        Item {
            visible: racine.modification
            Layout.fillWidth: true
        },
        BoutonEtiquette {
            text: "Annuler"
            onClicked: racine.close()
        },
        BoutonTampon {
            Layout.margins: 4
            text: racine.modification ? "Enregistrer" : "Tamponner"
            onClicked: racine.valider()
        }
    ]
}
