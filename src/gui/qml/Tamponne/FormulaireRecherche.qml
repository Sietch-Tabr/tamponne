pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Formulaire « Demande de recherche » (cases façon Cerfa) ou, en mode
    édition, « Modification de fiche ». L'état vit dans le contrôleur. */
Feuille {
    id: racine

    /*! `ControleurRecherche` (src/gui/controleur_recherche.py). */
    required property var recherche

    signal selectionDemandee(string liste, string titre)
    signal classementDemande()

    readonly property var etat: recherche.etat
    readonly property var choix: recherche.choix

    halo: Theme.ombrePortee
    flou: 24
    implicitHeight: colonne.implicitHeight + 36

    Accessible.role: Accessible.Form
    Accessible.name: recherche.edition ? "Modification de fiche" : "Critères de recherche"

    component Champ: ColumnLayout {
        id: champ
        property string intitule: ""
        default property alias contenuChamp: emplacement.data
        Layout.fillWidth: true
        spacing: 2
        EtiquetteChamp { text: champ.intitule }
        Item {
            id: emplacement
            Layout.fillWidth: true
            implicitHeight: childrenRect.height
        }
    }

    ColumnLayout {
        id: colonne
        x: 18
        y: 18
        width: parent.width - 36
        spacing: 12

        Item {
            Layout.fillWidth: true
            implicitHeight: entete.implicitHeight + 10

            RowLayout {
                id: entete
                width: parent.width
                Texte {
                    Layout.fillWidth: true
                    text: racine.recherche.edition ? "Modification de fiche" : "Demande de recherche"
                    font.pixelSize: 18
                    font.capitalization: Font.AllUppercase
                    font.letterSpacing: 0.6
                    font.variableAxes: { "wdth": 90, "wght": 700 }
                    wrapMode: Text.NoWrap
                    Accessible.role: Accessible.Heading
                }
                Texte {
                    text: "Form. R-02"
                    color: Theme.encre2
                    font.family: Theme.policeMono
                    font.pixelSize: 14
                    wrapMode: Text.NoWrap
                    Accessible.ignored: true
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 2
                color: Theme.encre
            }
        }

        Texte {
            Layout.fillWidth: true
            visible: racine.recherche.edition
            text: "Fiche « " + racine.recherche.intitule_edition + " » : les cases ci-dessous remplacent ses critères."
            font.pixelSize: 15
            lineHeight: Math.round(15 * 1.55)
        }

        CadreCerfa {
            Layout.fillWidth: true
            legende: "Catégorie"

            Flow {
                Layout.fillWidth: true
                spacing: 18
                Repeater {
                    model: racine.choix.categories.slice(0, 2)
                    CaseCerfa {
                        required property string modelData
                        text: modelData
                        coche: racine.etat.categories.indexOf(modelData) >= 0
                        onClicked: racine.recherche.basculer("categories", modelData, !coche)
                    }
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 18
                Repeater {
                    model: racine.choix.categories.slice(2)
                    CaseCerfa {
                        required property string modelData
                        text: modelData
                        coche: racine.etat.categories.indexOf(modelData) >= 0
                        onClicked: racine.recherche.basculer("categories", modelData, !coche)
                    }
                }
            }
            LigneChoix {
                Layout.fillWidth: true
                text: "Corps / grade"
                valeur: racine.etat.libelle_grades
                onClicked: racine.selectionDemandee("grades", "Corps / Grade")
            }
        }

        CadreCerfa {
            Layout.fillWidth: true
            legende: "Versant"

            Flow {
                Layout.fillWidth: true
                spacing: 18
                Repeater {
                    model: racine.choix.versants
                    CaseCerfa {
                        required property var modelData
                        text: modelData.libelle
                        coche: racine.etat.versants.indexOf(modelData.cle) >= 0
                        onClicked: racine.recherche.basculer("versants", modelData.cle, !coche)
                    }
                }
            }
        }

        CadreCerfa {
            Layout.fillWidth: true
            legende: "Poste"

            LigneChoix {
                Layout.fillWidth: true
                text: "Domaines"
                valeur: racine.etat.libelle_domaines
                onClicked: racine.selectionDemandee("domaines", "Domaines")
            }
            Champ {
                intitule: "Type de poste"
                ListeDeroulante {
                    width: parent.width
                    implicitHeight: 40
                    textRole: ""
                    valueRole: ""
                    model: racine.choix.types_poste
                    currentIndex: racine.etat.type_poste
                    onActivated: (index) => racine.recherche.definir("type_poste", index)
                }
            }
            Champ {
                intitule: "Expérience souhaitée"
                ListeDeroulante {
                    width: parent.width
                    implicitHeight: 40
                    textRole: ""
                    valueRole: ""
                    model: racine.choix.experiences
                    currentIndex: racine.choix.experiences.indexOf(racine.etat.experience)
                    onActivated: (index) => racine.recherche.definir("experience", racine.choix.experiences[index])
                }
            }
            Champ {
                intitule: "Date de publication"
                ListeDeroulante {
                    width: parent.width
                    implicitHeight: 40
                    textRole: ""
                    valueRole: ""
                    model: racine.choix.dates_publication
                    currentIndex: racine.choix.dates_publication.indexOf(racine.etat.date_publication)
                    onActivated: (index) => racine.recherche.definir("date_publication", racine.choix.dates_publication[index])
                }
            }
        }

        CadreCerfa {
            Layout.fillWidth: true
            legende: "Lieu"

            LigneChoix {
                Layout.fillWidth: true
                text: "Localisations"
                valeur: racine.etat.libelle_localisations
                onClicked: racine.selectionDemandee("localisations", "Localisations")
            }
            LigneChoix {
                Layout.fillWidth: true
                text: "Organisations"
                valeur: racine.etat.libelle_organisations
                onClicked: racine.selectionDemandee("organisations", "Organisations")
            }
        }

        CadreCerfa {
            Layout.fillWidth: true
            legende: "Options"

            CaseCerfa {
                text: "Management"
                coche: racine.etat.management
                onClicked: racine.recherche.definir("management", !coche)
            }
            CaseCerfa {
                text: "Télétravail"
                coche: racine.etat.teletravail
                onClicked: racine.recherche.definir("teletravail", !coche)
            }
            CaseCerfa {
                text: "Grades supérieurs"
                coche: racine.etat.grades_superieurs
                onClicked: racine.recherche.definir("grades_superieurs", !coche)
            }
            Champ {
                intitule: "Mot-clé"
                ChampSouligne {
                    width: parent.width
                    implicitHeight: 40
                    mono: true
                    placeholderText: "ex. IDIV"
                    text: racine.etat.mot_cle
                    Accessible.name: "Mot-clé"
                    onTextEdited: racine.recherche.definir("mot_cle", text)
                    onAccepted: racine.recherche.valider()
                }
            }
        }

        BoutonTampon {
            Layout.fillWidth: true
            Layout.topMargin: 6
            Layout.leftMargin: 4
            Layout.rightMargin: 4
            Layout.bottomMargin: 4
            text: racine.recherche.texte_bouton
            enabled: racine.recherche.phase !== "en_cours"
            onClicked: racine.recherche.valider()
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            visible: !racine.recherche.edition

            BoutonEtiquette {
                Layout.fillWidth: true
                text: "Classer en profil"
                onClicked: racine.classementDemande()
            }
            BoutonEtiquette {
                text: "RAZ"
                ToolTip.visible: hovered
                ToolTip.text: "Réinitialise tous les filtres de cet écran"
                onClicked: racine.recherche.reinitialiser()
            }
        }

        BoutonEtiquette {
            Layout.fillWidth: true
            visible: racine.recherche.edition
            text: "Annuler"
            onClicked: racine.recherche.annuler_edition()
        }
    }
}
