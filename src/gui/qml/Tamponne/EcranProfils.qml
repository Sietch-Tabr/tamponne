pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Écran Profils (« Mes fiches de recherche ») : une fiche bristol par
    profil enregistré, plus la carte « Nouvelle fiche ». */
Item {
    id: racine

    /*! `ControleurProfils` (src/gui/controleur_profils.py). */
    required property var profils

    /*! Recherche vierge demandée (carte « Nouvelle fiche »). */
    signal nouvelleFiche()

    function ouvrirDuplication(nom: string) {
        duplication.ouvrirPour(nom, profils.intitule(nom))
    }

    function demanderSuppression(nom: string) {
        confirmation.action = () => racine.profils.supprimer(nom)
        confirmation.demander("Supprimer la fiche",
            "Supprimer la fiche « " + profils.intitule(nom) + " » ?")
    }

    DialogueDupliquer {
        id: duplication
        onDuplique: (nom, nouveauNom, intituleCopie) => {
            const erreur = racine.profils.dupliquer(nom, nouveauNom, intituleCopie)
            if (erreur === "")
                close()
            else
                refuser(erreur)
        }
    }

    DialogueConfirmation {
        id: confirmation
        /*! Action exécutée sur « Oui ». */
        property var action: null
        onConfirme: if (action) action()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 22

        RowLayout {
            Layout.fillWidth: true
            spacing: 18

            Texte {
                text: "Mes fiches de recherche"
                color: Theme.texteKraft
                font.pixelSize: 40
                font.capitalization: Font.AllUppercase
                font.variableAxes: { "wdth": 80, "wght": 800 }
                lineHeight: 40
                wrapMode: Text.NoWrap
                // Hauteur de ligne de 1 dans la maquette : le texte seul ne s'y tient pas.
                Layout.preferredHeight: 40
                Layout.alignment: Qt.AlignBottom
                Accessible.role: Accessible.Heading
            }
            Texte {
                visible: racine.profils.nombre > 0
                text: racine.profils.texte_nombre
                color: Theme.texteKraft
                font.family: Theme.policeMono
                font.pixelSize: 14
                wrapMode: Text.NoWrap
                Layout.alignment: Qt.AlignBottom
            }
            Item { Layout.fillWidth: true }
        }

        Flickable {
            id: defilement
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: racine.profils.nombre > 0
            contentHeight: grille.height + 12
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            GridLayout {
                id: grille

                // Grille « auto-fill, minmax(320px, 1fr) » de la maquette, rangées étirées.
                readonly property int colonnes: Math.max(1, Math.floor((width + 24) / (320 + 24)))
                readonly property real largeurCarte: (width - 24 * (colonnes - 1)) / colonnes

                width: defilement.width
                columns: colonnes
                columnSpacing: 24
                rowSpacing: 24

                Repeater {
                    model: racine.profils.modele
                    delegate: FicheBristol {
                        required property int index
                        Layout.preferredWidth: grille.largeurCarte
                        Layout.fillHeight: true
                        rotation: Theme.reduireAnimations ? 0 : (index % 2 === 0 ? -0.5 : 0.4)
                        onLancer: (nom) => racine.profils.lancer(nom)
                        onModifier: (nom) => racine.profils.modifier(nom)
                        onDupliquer: (nom) => racine.ouvrirDuplication(nom)
                        onSupprimer: (nom) => racine.demanderSuppression(nom)
                    }
                }

                AbstractButton {
                    id: carteNouvelle
                    Layout.preferredWidth: grille.largeurCarte
                    Layout.fillHeight: true
                    implicitHeight: 240
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    text: "Nouvelle fiche"
                    Accessible.role: Accessible.Button
                    Accessible.name: text
                    onClicked: racine.nouvelleFiche()

                    background: Rectangle {
                        color: carteNouvelle.hovered ? Theme.ongletSurvol : "transparent"
                        CadrePointille {
                            anchors.fill: parent
                            couleur: Theme.pointille
                        }
                        Rectangle {
                            visible: carteNouvelle.visualFocus
                            anchors.fill: parent
                            anchors.margins: -5
                            color: "transparent"
                            border.color: Theme.tampon
                            border.width: 3
                        }
                    }
                    contentItem: Item {
                    Column {
                        anchors.centerIn: parent
                        spacing: 6
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "+"
                            color: Theme.texteKraft
                            font.family: Theme.policeTexte
                            font.pixelSize: 34
                            lineHeightMode: Text.FixedHeight
                            lineHeight: 34
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: carteNouvelle.text
                            color: Theme.texteKraft
                            font.family: Theme.policeTexte
                            font.pixelSize: 17
                            font.capitalization: Font.AllUppercase
                            font.letterSpacing: 0.6
                            font.variableAxes: { "wdth": 90, "wght": 800 }
                        }
                    }
                    }
                }
            }
        }

        Feuille {
            visible: racine.profils.nombre === 0
            Layout.fillWidth: true
            Layout.preferredHeight: videFiches.height + 40

            CadrePointille {
                id: videFiches
                x: 22
                y: 20
                width: parent.width - 44
                height: Math.max(140, contenuVide.implicitHeight + 32)

                Column {
                    id: contenuVide
                    anchors.centerIn: parent
                    width: parent.width - 32
                    spacing: 10

                    Texte {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        lineHeight: 24
                        text: "Aucune fiche classée.\nLancer une recherche puis « Classer en profil »."
                    }
                    BoutonEtiquette {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Nouvelle fiche"
                        onClicked: racine.nouvelleFiche()
                    }
                }
            }
        }
    }
}
