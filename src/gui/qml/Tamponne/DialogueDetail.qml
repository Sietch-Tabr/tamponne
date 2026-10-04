pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Fiche de poste d'une offre : actions (postuler, consulter en ligne,
    copie archivée), description, informations et rubriques suivantes. */
Dialogue {
    id: racine

    /*! Contenu fourni par le contrôleur (`detail(reference)`). */
    property var fiche: ({})

    signal postuler(string reference)
    signal consulterEnLigne(string reference)
    signal voirArchive(string reference)

    titre: ""
    width: Math.min(860, parent ? parent.width - 56 : 860)
    height: Math.min(implicitHeight, parent ? parent.height - 56 : implicitHeight)
    topPadding: 32
    leftPadding: 30
    rightPadding: 30
    bottomPadding: 26

    nomAccessible: fiche.titre || ""

    function afficher(contenu: var) {
        fiche = contenu
        open()
        boutonFermer.forceActiveFocus()
    }

    Flickable {
        id: defilement
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.preferredHeight: fichePage.implicitHeight
        contentHeight: fichePage.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        ColumnLayout {
            id: fichePage
            width: defilement.width
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                Texte {
                    text: "Réf. " + (racine.fiche.reference || "")
                    color: Theme.encre2
                    font.family: Theme.policeMono
                    font.pixelSize: 14
                }
                Item { Layout.fillWidth: true }
                Texte {
                    text: "Fiche de poste"
                    color: Theme.encre2
                    font.family: Theme.policeMono
                    font.pixelSize: 14
                }
            }
            Texte {
                Layout.fillWidth: true
                text: racine.fiche.titre || ""
                font.pixelSize: 36
                font.capitalization: Font.AllUppercase
                font.variableAxes: { "wdth": 80, "wght": 800 }
                lineHeight: Math.round(36 * 1.05)
                Accessible.role: Accessible.Heading
            }
            Texte {
                Layout.fillWidth: true
                visible: text !== ""
                text: racine.fiche.sousTitre || ""
                color: Theme.encre2
                lineHeight: Math.round(16 * 1.6)
            }
            Flow {
                Layout.fillWidth: true
                spacing: 14

                BoutonTampon {
                    text: "Postuler"
                    enabled: racine.fiche.peutPostuler === true
                    onClicked: racine.postuler(racine.fiche.reference)
                }
                BoutonEtiquette {
                    text: "Consulter en ligne"
                    enabled: racine.fiche.enLigne === true
                    onClicked: racine.consulterEnLigne(racine.fiche.reference)
                }
                BoutonEtiquette {
                    text: "Voir la copie archivée"
                    enabled: racine.fiche.archivePresente === true
                    ToolTip.visible: hovered
                    ToolTip.text: "PDF autonome de la fiche telle qu'elle était au moment du suivi, consultable hors ligne ou après dépublication"
                    onClicked: racine.voirArchive(racine.fiche.reference)
                }
            }

            Rubrique {
                visible: (racine.fiche.description || "") !== ""
                titreRubrique: "Description du poste"
                texte: racine.fiche.description || ""
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: (racine.fiche.informations || []).length > 0
                spacing: 16

                TitreRubrique { texte: "Informations" }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 18
                    rowSpacing: 6

                    Repeater {
                        model: racine.fiche.informations || []
                        delegate: EtiquetteChamp {
                            required property var modelData
                            required property int index
                            Layout.row: index
                            Layout.column: 0
                            Layout.alignment: Qt.AlignTop
                            topPadding: 3
                            text: modelData.libelle
                        }
                    }
                    Repeater {
                        model: racine.fiche.informations || []
                        delegate: Texte {
                            required property var modelData
                            required property int index
                            Layout.row: index
                            Layout.column: 1
                            Layout.fillWidth: true
                            text: modelData.valeur
                        }
                    }
                }
            }

            Repeater {
                model: racine.fiche.rubriques || []
                delegate: Rubrique {
                    required property var modelData
                    titreRubrique: modelData.titre
                    texte: modelData.texte
                }
            }

            Texte {
                visible: (racine.fiche.description || "") === ""
                    && (racine.fiche.informations || []).length === 0
                    && (racine.fiche.rubriques || []).length === 0
                text: "Aucun détail disponible pour cette offre."
                color: Theme.encre2
            }
        }

        Tampon {
            visible: racine.fiche.archivePresente === true
            x: defilement.width - width
            y: 26
            rotation: -6
            texte: "Copie archivée"
            taille: 15
            Accessible.ignored: true
        }
    }

    boutons: [
        BoutonEtiquette {
            id: boutonFermer
            text: "Fermer"
            onClicked: racine.close()
        }
    ]

    component TitreRubrique: Texte {
        property string texte: ""
        Layout.fillWidth: true
        text: texte
        font.pixelSize: 20
        font.capitalization: Font.AllUppercase
        font.letterSpacing: 0.5
        font.variableAxes: { "wdth": 88, "wght": 800 }
        bottomPadding: 8
        Accessible.role: Accessible.Heading

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 2
            color: Theme.encre
        }
    }

    component Rubrique: ColumnLayout {
        id: rubrique
        property string titreRubrique: ""
        property string texte: ""
        Layout.fillWidth: true
        spacing: 16

        TitreRubrique { texte: rubrique.titreRubrique }
        Texte {
            Layout.fillWidth: true
            text: rubrique.texte
            lineHeight: Math.round(16 * 1.6)
        }
    }
}
