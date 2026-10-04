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

            delegate: DossierSuivi {
                width: ListView.view.width
                onVoirOffre: (reference) => racine.suivi.voir_offre(reference)
                onVoirArchive: (reference) => racine.suivi.voir_archive(reference)
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
