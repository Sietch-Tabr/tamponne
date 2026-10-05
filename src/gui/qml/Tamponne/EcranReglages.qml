pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Écran Réglages : avis de mise à jour, sources consultées, thème,
    animations et cache des organisations. */
Item {
    id: racine

    required property var reglages
    /*! Persistance du thème choisi (`Pont.enregistrer_mode_theme`). */
    signal modeThemeChoisi(string mode)

    readonly property var avis: reglages.avis
    readonly property var modesTheme: [
        { cle: "auto", libelle: "Suivre le système" },
        { cle: "clair", libelle: "Bureau de jour" },
        { cle: "sombre", libelle: "Bureau de nuit" }
    ]

    // « flex: 999 1 520px » et « flex: 1 1 300px » sur une ligne qui
    // passe à la ligne sous 520 + 22 + 300 px.
    readonly property real largeurUtile: width - 56
    readonly property bool surUneLigne: largeurUtile >= 842
    readonly property real largeurAvis: surUneLigne ? 520 + (largeurUtile - 842) * 999 / 1000 : largeurUtile
    readonly property real largeurColonne: surUneLigne ? 300 + (largeurUtile - 842) / 1000 : largeurUtile

    component TitreFeuille: Texte {
        width: parent ? parent.width : 0
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

    component Paragraphe: Texte {
        width: parent ? parent.width : 0
        textFormat: Text.StyledText
        // Hauteur imposée : Qt arrondirait la hauteur de ligne fractionnaire.
        height: lineCount * lineHeight
    }

    Flickable {
        id: defilement
        anchors.fill: parent
        contentHeight: disposition.height + 56
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        Flow {
            id: disposition
            x: 28
            y: 28
            width: racine.largeurUtile
            spacing: 22

            Feuille {
                id: feuilleAvis
                objectName: "feuilleAvis"
                width: racine.largeurAvis
                height: colonneAvis.height + 52
                halo: Theme.ombrePortee
                Accessible.role: Accessible.Grouping
                Accessible.name: "Avis de mise à jour"

                Column {
                    id: colonneAvis
                    objectName: "colonneAvis"
                    x: 28
                    y: 26
                    width: parent.width - 56
                    spacing: 12

                    Item {
                        visible: racine.avis.disponible
                        width: parent.width
                        height: numeroAvis.height
                        Texte {
                            id: numeroAvis
                            text: racine.avis.numero ?? ""
                            color: Theme.encre2
                            font.family: Theme.policeMono
                            font.pixelSize: 14
                            wrapMode: Text.NoWrap
                        }
                        Texte {
                            anchors.right: parent.right
                            text: racine.avis.date ?? ""
                            color: Theme.encre2
                            font.family: Theme.policeMono
                            font.pixelSize: 14
                            wrapMode: Text.NoWrap
                        }
                    }

                    Texte {
                        width: parent.width
                        text: "Avis de mise à jour"
                        font.pixelSize: 40
                        font.capitalization: Font.AllUppercase
                        font.variableAxes: { "wdth": 80, "wght": 800 }
                        lineHeight: 40
                        // « line-height: 1 » : boîte de 40 px que la police déborde ;
                        // centré, Qt remonterait les glyphes de 2 px.
                        height: 40
                        verticalAlignment: Text.AlignTop
                        Accessible.role: Accessible.Heading
                    }

                    Paragraphe {
                        text: "<b>Objet :</b> " + racine.avis.objet
                        font.pixelSize: racine.avis.disponible ? 17 : 16
                        lineHeight: racine.avis.disponible ? 17 * 1.55 : 16 * 1.5
                    }

                    Tampon {
                        visible: !racine.avis.disponible
                        texte: "À jour"
                        encre: Theme.vert
                        taille: 15
                        rotation: Theme.reduireAnimations ? 0 : -3
                        Accessible.ignored: true
                    }

                    Texte {
                        id: notes
                        visible: racine.avis.disponible
                        width: parent.width
                        text: racine.avis.notes ?? ""
                        // HTML préparé par `presentation.notes_en_html` (Markdown converti).
                        textFormat: Text.RichText
                        linkColor: Theme.encre
                        onLinkActivated: lien => {
                            if (lien.startsWith("https://"))
                                Qt.openUrlExternally(lien)
                        }
                        font.family: Theme.policeMono
                        font.pixelSize: 14
                        lineHeight: 14 * 1.6
                        // Hauteur du contenu (titres, listes), dont Qt compte la dernière
                        // ligne sans son interligne ; aligné en haut, sinon il déborde.
                        height: implicitHeight + lineHeight - Theme.ligneNormale(true, 14)
                        verticalAlignment: Text.AlignTop
                        leftPadding: 17
                        rightPadding: 14
                        // Le rendu riche place tout l'interligne au-dessus de la ligne,
                        // le navigateur le partage : on remonte d'un demi-interligne.
                        topPadding: 12 - (lineHeight - Theme.ligneNormale(true, 14)) / 2
                        bottomPadding: 12 + (lineHeight - Theme.ligneNormale(true, 14)) / 2
                        Rectangle {
                            anchors.fill: parent
                            z: -1
                            color: Theme.papier2
                            Rectangle {
                                width: 3
                                height: parent.height
                                color: Theme.encre
                            }
                        }
                    }

                    Flow {
                        visible: racine.avis.disponible
                        width: parent.width
                        topPadding: 6
                        spacing: 14

                        Item {
                            width: boutonInstaller.implicitWidth + 8
                            height: boutonInstaller.implicitHeight + 8
                            BoutonTampon {
                                id: boutonInstaller
                                objectName: "boutonInstaller"
                                x: 4
                                y: 4
                                text: "Installer et redémarrer"
                                onClicked: racine.reglages.installer_maj()
                            }
                        }
                        // « align-items: center » de la rangée de boutons.
                        Item {
                            width: boutonReporter.implicitWidth
                            height: boutonInstaller.implicitHeight + 8
                            BoutonEtiquette {
                                id: boutonReporter
                                objectName: "boutonReporter"
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Au prochain lancement"
                                onClicked: racine.reglages.reporter_maj()
                            }
                        }
                    }
                }
            }

            Column {
                width: racine.largeurColonne
                spacing: 22

                Feuille {
                    width: parent.width
                    height: colonneSources.height + 40
                    halo: Theme.ombrePortee
                    Accessible.role: Accessible.Grouping
                    Accessible.name: "Sources consultées"

                    Column {
                        id: colonneSources
                        x: 22
                        y: 20
                        width: parent.width - 44
                        spacing: 12

                        TitreFeuille { text: "Sources consultées" }

                        Repeater {
                            model: racine.reglages.sources
                            CaseCerfa {
                                required property var modelData
                                objectName: "source_" + modelData.cle
                                width: parent ? parent.width : 0
                                hauteurMinimale: 44
                                retourLigne: true
                                filet: true
                                text: modelData.libelle
                                coche: racine.reglages.sources_actives[modelData.cle] === true
                                onClicked: racine.reglages.basculer_source(modelData.cle)
                            }
                        }
                    }
                }

                Feuille {
                    width: parent.width
                    height: colonneClassement.height + 40
                    halo: Theme.ombrePortee
                    Accessible.role: Accessible.Grouping
                    Accessible.name: "Classement"

                    Column {
                        id: colonneClassement
                        x: 22
                        y: 20
                        width: parent.width - 44
                        spacing: 12

                        TitreFeuille { text: "Classement" }

                        Column {
                            width: parent.width
                            spacing: 4
                            Texte {
                                text: "Thème"
                                color: Theme.encre2
                                font.family: Theme.policeMono
                                font.pixelSize: 13
                                font.capitalization: Font.AllUppercase
                                font.letterSpacing: 0.5
                                wrapMode: Text.NoWrap
                                Accessible.ignored: true
                            }
                            ListeDeroulante {
                                objectName: "listeTheme"
                                width: parent.width
                                implicitHeight: 44
                                model: racine.modesTheme
                                currentIndex: racine.modesTheme.findIndex(m => m.cle === Theme.mode)
                                Accessible.name: "Thème : " + displayText
                                onActivated: indice => {
                                    Theme.mode = racine.modesTheme[indice].cle
                                    racine.modeThemeChoisi(Theme.mode)
                                }
                            }
                        }

                        CaseCerfa {
                            objectName: "caseAnimations"
                            width: parent.width
                            hauteurMinimale: 44
                            retourLigne: true
                            filet: true
                            text: "Réduire les animations"
                            coche: racine.reglages.reduire_animations
                            onClicked: {
                                Theme.reduireAnimations = !racine.reglages.reduire_animations
                                racine.reglages.definir_reduire_animations(Theme.reduireAnimations)
                            }
                        }

                        BoutonEtiquette {
                            objectName: "boutonCache"
                            enabled: !racine.reglages.cache_en_cours
                            text: racine.reglages.cache_en_cours ? "Rafraîchissement…" : "Rafraîchir le cache"
                            onClicked: racine.reglages.rafraichir_cache()
                        }

                        Texte {
                            visible: racine.reglages.message_cache !== ""
                            width: parent.width
                            text: racine.reglages.message_cache
                            color: Theme.rouge
                            Accessible.role: Accessible.AlertMessage
                        }
                    }
                }
            }
        }
    }
}
