pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Écran Suivi (« Dossiers en cours ») : un dossier par candidature
    suivie, vérification de disponibilité des offres. */
Item {
    id: racine

    /*! `ControleurSuivi` (src/gui/controleur_suivi.py). */
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
        evenement.ouvrirPour(reference, titreDe(reference))
    }

    function demanderSuppression(reference: string) {
        if (reference === "")
            return
        confirmation.reference = reference
        confirmation.demander("Arrêter le suivi",
            "Retirer le dossier « " + titreDe(reference) + " » du suivi ? Son historique et sa copie archivée seront jetés.")
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
        onTamponne: (reference, typeEvenement, dateIso, note) =>
            racine.suivi.ajouter_evenement(reference, typeEvenement, dateIso, note)
    }

    DialogueConfirmation {
        id: confirmation
        property string reference: ""
        onConfirme: racine.suivi.supprimer(reference)
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
                text: "Dossiers en cours"
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
                    text: "Aucun dossier en cours.\nDans le registre, « Tamponner pour suivi »."
                }
            }
        }
    }
}
