pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Écran Recherche : formulaire « Demande de recherche » à gauche,
    « Registre des offres » à droite, avec ses états (vide, en cours,
    aucun résultat, recherche impossible). */
Item {
    id: racine

    /*! `ControleurRecherche` (src/gui/controleur_recherche.py). */
    required property var recherche
    /*! `ControleurSuivi`, pour la copie archivée d'une offre déjà suivie. */
    required property var suivi

    /*! « Voir le suivi » depuis l'avis de candidature suivie. */
    signal suiviDemande()

    readonly property string phase: recherche.phase

    function ouvrirSelection(liste: string, titre: string) {
        selection.ouvrirPour(liste, titre, recherche.groupes_selection(liste), recherche.etat[liste])
    }

    function exporter() {
        const resultat = recherche.exporter()
        avisExport.chemin = resultat.chemin
        avisExport.message = "Registre exporté (" + resultat.nombre + " offre" + (resultat.nombre > 1 ? "s" : "") + ")\u00a0:"
        avisExport.open()
    }

    Connections {
        target: racine.recherche
        function onDetail_attendu(apercu: var) {
            preparation.stop()
            detail.attendre(apercu)
        }
        // Une fiche arrivée après la fermeture de la fenêtre, ou pour une autre
        // offre, ne la rouvre pas.
        function onDetail_pret(fiche: var) {
            if (detail.chargement && detail.opened && detail.fiche.reference === fiche.reference)
                detail.afficher(fiche)
        }
        function onSelection_change() { preparation.restart() }
        function onSuivi_termine(titre: string) {
            avisSuivi.message = "«\u00a0" + titre + "\u00a0» rejoint les dossiers en cours, avec sa fiche archivée."
            avisSuivi.open()
        }
        function onAction_echouee(message: string) {
            if (detail.chargement)
                detail.close()
            avisErreur.message = message
            avisErreur.open()
        }
    }

    // Fiche de l'offre sélectionnée téléchargée à l'avance : sa consultation
    // s'ouvre ensuite sans attendre le site.
    Timer {
        id: preparation
        interval: 350
        onTriggered: racine.recherche.precharger_selection()
    }

    DialogueSelection {
        id: selection
        objectName: "dialogueSelection"
        onValide: (liste, valeurs) => racine.recherche.definir(liste, valeurs)
    }

    DialogueClasser {
        id: classement
        onClasse: (nom, intitule) => {
            const erreur = racine.recherche.classer(nom, intitule)
            if (erreur === "")
                close()
            else
                refuser(erreur)
        }
    }

    DialogueDetail {
        id: detail
        objectName: "dialogueDetail"
        onPostuler: racine.recherche.ouvrir_lien(detail.fiche.lienPostuler || "")
        onConsulterEnLigne: racine.recherche.ouvrir_lien(detail.fiche.url || "")
        onVoirArchive: (reference) => racine.suivi.voir_archive(reference)
    }

    DialogueAvis {
        id: avisSuivi
        titre: "Candidature suivie"
        tampon: "Classé"
        action: "Voir le suivi"
        onActionDemandee: racine.suiviDemande()
    }

    DialogueAvis {
        id: avisExport
        titre: "Export prêt"
        action: "Ouvrir"
        onActionDemandee: racine.recherche.ouvrir_fichier(chemin)
    }

    DialogueAvis {
        id: avisErreur
        titre: "Opération impossible"
        alerte: true
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 18

        Flickable {
            id: defilementFormulaire
            // Base de 300 px de la maquette (flex: 1 1 300px face au registre en 999).
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            contentHeight: formulaire.implicitHeight + 12
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            FormulaireRecherche {
                id: formulaire
                width: defilementFormulaire.width
                height: implicitHeight
                recherche: racine.recherche
                onSelectionDemandee: (liste, titre) => racine.ouvrirSelection(liste, titre)
                onClassementDemande: classement.ouvrir()
            }
        }

        Feuille {
            id: feuilleRegistre
            Layout.fillWidth: true
            // Hauteur du contenu comme la maquette, bornée par la chemise (le tableau défile alors).
            Layout.preferredHeight: colonneRegistre.implicitHeight + 36
            Layout.maximumHeight: parent.height
            Layout.alignment: Qt.AlignTop
            halo: Theme.ombrePortee
            flou: 24

            ColumnLayout {
                id: colonneRegistre
                anchors.fill: parent
                anchors.topMargin: 18
                anchors.bottomMargin: 18
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 14

                Item {
                    Layout.fillWidth: true
                    implicitHeight: enteteRegistre.implicitHeight + 10

                    // Retour à la ligne de la maquette (flex-wrap) : titre seul, puis résumé et tampon.
                    ColumnLayout {
                        id: enteteRegistre
                        width: parent.width
                        spacing: 8

                        readonly property bool surUneLigne: titreRegistre.implicitWidth + 18
                            + resumeRegistre.implicitWidth + 18 + tamponRegistre.implicitWidth <= width

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 18

                            Texte {
                                id: titreRegistre
                                text: "Registre des offres"
                                font.pixelSize: 34
                                font.capitalization: Font.AllUppercase
                                font.variableAxes: { "wdth": 80, "wght": 800 }
                                lineHeight: 34
                                wrapMode: Text.NoWrap
                                Layout.preferredHeight: 34
                                Layout.alignment: Qt.AlignBottom
                                Accessible.role: Accessible.Heading
                            }
                            Item {
                                Layout.fillWidth: true
                                visible: !enteteRegistre.surUneLigne
                            }
                            Loader {
                                active: enteteRegistre.surUneLigne
                                visible: active
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignBottom
                                sourceComponent: resumeEtTampon
                            }
                        }
                        Loader {
                            Layout.fillWidth: true
                            active: !enteteRegistre.surUneLigne && resumeRegistre.text !== ""
                            visible: active
                            sourceComponent: resumeEtTampon
                        }
                    }

                    Component {
                        id: resumeEtTampon
                        RowLayout {
                            spacing: 18
                            Texte {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignBottom
                                bottomPadding: 3
                                text: resumeRegistre.text
                                color: Theme.encre2
                                font.family: Theme.policeMono
                                font.pixelSize: 14
                                Accessible.role: racine.phase === "en_cours" ? Accessible.StatusBar : Accessible.StaticText
                            }
                            Tampon {
                                visible: tamponRegistre.affiche
                                Layout.alignment: Qt.AlignBottom
                                rotation: 3
                                texte: tamponRegistre.texte
                                taille: 14
                                Accessible.ignored: true
                            }
                        }
                    }

                    // Mesures seulement : textes invisibles servant à choisir la disposition.
                    Texte {
                        id: resumeRegistre
                        visible: false
                        text: racine.phase === "en_cours" ? racine.recherche.statut : racine.recherche.resume
                        font.family: Theme.policeMono
                        font.pixelSize: 14
                        wrapMode: Text.NoWrap
                        Accessible.ignored: true
                    }
                    Tampon {
                        id: tamponRegistre
                        visible: false
                        readonly property bool affiche: racine.phase === "resultats" || racine.phase === "en_cours"
                        texte: racine.phase === "en_cours" ? "En cours" : "Dédoublonné"
                        taille: 14
                        Accessible.ignored: true
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
                    visible: racine.recherche.avertissements !== "" && racine.phase !== "en_cours"
                    text: racine.recherche.avertissements
                    color: Theme.rouge
                    font.family: Theme.policeMono
                    font.pixelSize: 14
                }

                // Recherche en cours : avancement source par source.
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: racine.phase === "en_cours"
                    spacing: 6
                    Accessible.role: Accessible.List
                    Accessible.name: "Avancement par source"

                    Repeater {
                        model: racine.recherche.avancement
                        Item {
                            id: ligneSource
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: 34
                            Accessible.role: Accessible.ListItem
                            Accessible.name: modelData.nom + "\u00a0: " + modelData.etat

                            Texte {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                text: ligneSource.modelData.nom
                                wrapMode: Text.NoWrap
                                Accessible.ignored: true
                            }
                            Texte {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: ligneSource.modelData.etat
                                color: ligneSource.modelData.etat.startsWith("terminé") ? Theme.vert
                                     : (ligneSource.modelData.etat === "indisponible" ? Theme.rouge : Theme.encre)
                                font.family: Theme.policeMono
                                font.pixelSize: 14
                                wrapMode: Text.NoWrap
                                Accessible.ignored: true
                            }
                            LignePointillee {
                                anchors.bottom: parent.bottom
                                width: parent.width
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }

                // Rien de lancé, aucun résultat ou recherche impossible.
                CadrePointille {
                    id: cadreVide
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(140, messageVide.implicitHeight + 32)
                    visible: racine.phase === "vide" || racine.phase === "aucun" || racine.phase === "erreur"
                    couleur: racine.phase === "erreur" ? Theme.rouge : Theme.pointille

                    Column {
                        id: messageVide
                        anchors.centerIn: parent
                        width: parent.width - 32
                        spacing: 10

                        Tampon {
                            anchors.horizontalCenter: parent.horizontalCenter
                            rotation: racine.phase === "erreur" ? -5 : -4
                            texte: racine.phase === "erreur" ? "Refoulé" : "Néant"
                            encre: racine.phase === "erreur" ? Theme.rouge : Theme.tampon
                            taille: 16
                            Accessible.ignored: true
                        }
                        Texte {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            lineHeight: 24
                            textFormat: Text.StyledText
                            text: racine.phase === "erreur"
                                ? "<b>Recherche impossible.</b><br>" + racine.recherche.erreur
                                : (racine.phase === "aucun"
                                   ? "Aucune offre trouvée.<br>Élargir la demande (versants, lieu, mot-clé)."
                                   : "Aucune recherche lancée.<br>Remplir la demande puis «\u00a0Lancer la recherche\u00a0».")
                            Accessible.role: racine.phase === "erreur" ? Accessible.AlertMessage : Accessible.StaticText
                        }
                    }
                }
                Item {
                    Layout.fillHeight: true
                    visible: cadreVide.visible
                }

                // Registre rempli : filtre, tableau, actions.
                RowLayout {
                    Layout.fillWidth: true
                    visible: racine.phase === "resultats"
                    spacing: 18

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        EtiquetteChamp { text: "Filtrer" }
                        ChampSouligne {
                            Layout.fillWidth: true
                            implicitHeight: 40
                            placeholderText: "titre, employeur, lieu…"
                            Accessible.name: "Filtrer le registre"
                            onTextEdited: racine.recherche.filtrer(text)
                        }
                    }
                    CaseCerfa {
                        id: caseNouvelles
                        visible: racine.recherche.peut_filtrer_nouvelles
                        text: "Nouvelles seulement"
                        onClicked: {
                            coche = !coche
                            racine.recherche.nouvelles_seulement(coche)
                        }
                    }
                }

                Registre {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: implicitHeight
                    Layout.maximumHeight: implicitHeight
                    visible: racine.phase === "resultats"
                    recherche: racine.recherche
                }

                Item {
                    Layout.fillWidth: true
                    visible: racine.phase === "resultats"
                    implicitHeight: actions.implicitHeight + 15

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Theme.regle
                    }
                    RowLayout {
                        id: actions
                        y: 15
                        width: parent.width
                        spacing: 12

                        Texte {
                            Layout.fillWidth: true
                            text: racine.recherche.numero_selection !== ""
                                ? "Sélection\u00a0: ligne " + racine.recherche.numero_selection
                                : ""
                            color: Theme.encre2
                            font.family: Theme.policeMono
                            font.pixelSize: 14
                        }
                        BoutonEtiquette {
                            text: "Consulter"
                            enabled: racine.recherche.ligne_selectionnee >= 0
                            onClicked: racine.recherche.consulter()
                        }
                        BoutonEtiquette {
                            text: "Exporter"
                            onClicked: racine.exporter()
                        }
                        BoutonTampon {
                            Layout.margins: 4
                            text: "Tamponner pour suivi"
                            enabled: racine.recherche.ligne_selectionnee >= 0
                            onClicked: racine.recherche.tamponner_pour_suivi()
                        }
                    }
                }
            }
        }
    }
}
