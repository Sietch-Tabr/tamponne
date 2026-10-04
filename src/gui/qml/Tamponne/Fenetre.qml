pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Fenêtre principale : bande de menus bristol, bureau avec logotype et
    interrupteur jour/nuit, onglets d'intercalaire et chemise kraft qui
    reçoit l'écran de l'onglet actif. */
ApplicationWindow {
    id: fenetre

    /*! Objet Python `src.gui.pont.Pont` (actions et états métier). */
    required property var pont

    /*! Index de l'onglet actif : 0 Profils, 1 Recherche, 2 Suivi, 3 Aide, 4 Réglages. */
    property int ongletCourant: 0

    width: 1280
    height: 900
    minimumWidth: 900
    minimumHeight: 600
    visible: true
    title: "Tamponné"
    color: Theme.bureau

    menuBar: BandeMenus {
        onNouvelleRecherche: fenetre.ongletCourant = 1
        onOuvrirSuivi: fenetre.ongletCourant = 2
        onOuvrirAide: fenetre.ongletCourant = 3
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 24
        anchors.rightMargin: 24
        // 16 px sous la bande de menus, comme la maquette.
        anchors.topMargin: 16
        anchors.bottomMargin: 28
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            Layout.bottomMargin: 18
            spacing: 20

            Logotype {}
            Text {
                text: "Offres de la fonction publique · 4 sources"
                color: Theme.sousLogo
                font.family: Theme.policeTexte
                font.pixelSize: 15
            }
            Item { Layout.fillWidth: true }
            BoutonLampe {
                allumee: Theme.nuit
                onClicked: {
                    Theme.mode = Theme.nuit ? "clair" : "sombre"
                    fenetre.pont.enregistrer_mode_theme(Theme.mode)
                }
            }
        }

        Row {
            Layout.leftMargin: 20
            Layout.preferredHeight: 52
            spacing: 4

            Repeater {
                model: [
                    "Profils",
                    "Recherche",
                    "Suivi",
                    "Aide",
                    "Réglages"
                ]
                Onglet {
                    required property string modelData
                    required property int index
                    anchors.bottom: parent.bottom
                    text: modelData
                    actif: fenetre.ongletCourant === index
                    pastille: index === 4 && fenetre.pont.mise_a_jour_disponible
                    onClicked: fenetre.ongletCourant = index
                }
            }
        }

        Rectangle {
            id: chemise
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.kraft
            topLeftRadius: 4
            topRightRadius: 12
            bottomLeftRadius: 12
            bottomRightRadius: 12

            StackLayout {
                anchors.fill: parent
                currentIndex: fenetre.ongletCourant

                Item { objectName: "ecranProfils" }
                Item { objectName: "ecranRecherche" }
                EcranSuivi {
                    objectName: "ecranSuivi"
                    suivi: fenetre.pont.suivi
                }
                Item { objectName: "ecranAide" }
                Item { objectName: "ecranReglages" }
            }
        }
    }
}
