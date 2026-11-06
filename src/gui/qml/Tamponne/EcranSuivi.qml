pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Écran Suivi (« Dossiers en cours ») : un dossier par candidature
    suivie, vérification de disponibilité des offres. */
Item {
    id: racine

    /*! `ControleurSuivi` (src/gui/controleurs/suivi.py). */
    required property var suivi

    function titreDe(reference: string): string {
        const fiche = suivi.detail(reference)
        return fiche.titre || ""
    }

    function ouvrirDetail(reference: string) {
        if (reference !== "")
            detail.afficher(suivi.detail(reference))
    }

    function ouvrirEvenement(reference: string) {
        const proposition = suivi.proposition(reference)
        evenement.ouvrirPour(reference, titreDe(reference), proposition.type || "", proposition.date || "")
    }

    function modifierEvenement(reference: string, indice: int) {
        evenement.modifier(reference, titreDe(reference), indice, suivi.evenement(reference, indice))
    }

    function demanderSuppression(reference: string) {
        if (reference === "")
            return
        confirmation.action = () => racine.suivi.supprimer(reference)
        confirmation.demander("Arrêter le suivi",
            "Retirer le dossier «\u00a0" + titreDe(reference) + "\u00a0» du suivi\u00a0? Son historique et sa copie archivée seront jetés.")
    }

    function demanderSuppressionEvenement(reference: string, indice: int) {
        const fiche = suivi.evenement(reference, indice)
        confirmation.action = () => {
            racine.suivi.supprimer_evenement(reference, indice)
            evenement.close()
        }
        confirmation.demander("Supprimer l'événement",
            "Retirer «\u00a0" + (fiche.libelle || "") + "\u00a0» du " + (fiche.dateAffichee || "") + " de l'historique de ce dossier\u00a0?")
    }

    DialogueDetail {
        id: detail
        onPostuler: (reference) => racine.suivi.postuler(reference)
        onConsulterEnLigne: (reference) => racine.suivi.voir_offre(reference)
        onVoirArchive: (reference) => racine.suivi.voir_archive(reference)
    }

    DialogueEvenement {
        id: evenement
        types: racine.suivi.types_evenement
        onTamponne: (reference, typeEvenement, dateIso, note) => {
            const erreur = racine.suivi.ajouter_evenement(reference, typeEvenement, dateIso, note)
            if (erreur === "")
                close()
            else
                refuser(erreur)
        }
        onEnregistre: (reference, indice, typeEvenement, dateIso, note) => {
            const erreur = racine.suivi.modifier_evenement(reference, indice, typeEvenement, dateIso, note)
            if (erreur === "")
                close()
            else
                refuser(erreur)
        }
        onSuppressionDemandee: (reference, indice) => racine.demanderSuppressionEvenement(reference, indice)
    }

    DialogueConfirmation {
        id: confirmation
        /*! Action exécutée sur « Oui ». */
        property var action: null
        onConfirme: if (action) action()
    }

    MenuDossier {
        id: menu
        property string reference: ""
        onVoirOffre: racine.suivi.voir_offre(reference)
        onVoirArchive: racine.suivi.voir_archive(reference)
        onDetail: racine.ouvrirDetail(reference)
        onAjouterEvenement: racine.ouvrirEvenement(reference)
        onSupprimer: racine.demanderSuppression(reference)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 18

            Texte {
                text: racine.suivi.titre
                color: Theme.texteKraft
                font.pixelSize: 40
                font.capitalization: Font.AllUppercase
                font.variableAxes: { "wdth": 80, "wght": 800 }
                lineHeightMode: Text.FixedHeight
                lineHeight: 40
                wrapMode: Text.NoWrap
                Layout.alignment: Qt.AlignBottom
                Accessible.role: Accessible.Heading
            }
            Texte {
                text: racine.suivi.texte_nombre
                color: Theme.texteKraft
                font.family: Theme.policeMono
                font.pixelSize: 14
                wrapMode: Text.NoWrap
                Layout.alignment: Qt.AlignBottom
            }
            Item { Layout.fillWidth: true }
            BoutonEtiquette {
                Layout.alignment: Qt.AlignBottom
                text: racine.suivi.texte_verification
                trou: Theme.kraft
                enabled: !racine.suivi.verification_en_cours
                onClicked: racine.suivi.verifier_offres()
            }
        }

        // Offres que la dernière vérification n'a pas pu consulter.
        Texte {
            Layout.fillWidth: true
            visible: racine.suivi.avertissement !== ""
            text: racine.suivi.avertissement
            color: Theme.texteKraft
            font.family: Theme.policeMono
            font.pixelSize: 14
            Accessible.role: Accessible.AlertMessage
        }

        ListView {
            id: liste
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: racine.suivi.nombre > 0
            // Marge haute : le post-it de relance déborde de 14 px au-dessus du premier dossier.
            topMargin: 14
            bottomMargin: 12
            spacing: 22
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: racine.suivi.modele

            ScrollBar.vertical: ScrollBar {}

            focus: true
            keyNavigationEnabled: true
            Accessible.role: Accessible.List
            Accessible.name: "Dossiers en cours"

            Keys.onReturnPressed: racine.ouvrirDetail(liste.referenceCourante())
            Keys.onEnterPressed: racine.ouvrirDetail(liste.referenceCourante())
            Keys.onDeletePressed: racine.demanderSuppression(liste.referenceCourante())
            Keys.onPressed: (touche) => {
                if (touche.key === Qt.Key_Backspace) {
                    racine.demanderSuppression(liste.referenceCourante())
                    touche.accepted = true
                }
            }

            function referenceCourante(): string {
                return currentItem ? (currentItem as DossierSuivi).reference : ""
            }

            delegate: DossierSuivi {
                required property int index
                width: ListView.view.width
                courant: ListView.isCurrentItem && ListView.view.activeFocus
                onVoirOffre: (reference) => racine.suivi.voir_offre(reference)
                onVoirArchive: (reference) => racine.suivi.voir_archive(reference)
                onDetail: (reference) => racine.ouvrirDetail(reference)
                onAjouterEvenement: (reference) => racine.ouvrirEvenement(reference)
                onSupprimer: (reference) => racine.demanderSuppression(reference)
                onModifierEvenement: (reference, indice) => racine.modifierEvenement(reference, indice)
                onMenuDemande: (reference, disponible, x, y) => {
                    liste.currentIndex = index
                    menu.reference = reference
                    menu.disponible = disponible
                    menu.popup(this, x, y)
                }
            }
        }

        Feuille {
            visible: racine.suivi.nombre === 0
            Layout.fillWidth: true
            Layout.topMargin: 14
            Layout.preferredHeight: vide.height + 40

            CadrePointille {
                id: vide
                x: 22
                y: 20
                width: parent.width - 44
                height: Math.max(140, messageVide.implicitHeight + 32)

                Texte {
                    id: messageVide
                    anchors.centerIn: parent
                    width: parent.width - 32
                    horizontalAlignment: Text.AlignHCenter
                    lineHeightMode: Text.FixedHeight
                    lineHeight: 24
                    text: "Aucun dossier en cours.\nDans le registre, «\u00a0Tamponner pour suivi\u00a0»."
                }
            }
        }
    }
}
