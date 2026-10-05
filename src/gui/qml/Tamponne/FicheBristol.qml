pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Tamponne

/*! Fiche bristol d'un profil de recherche : filet rouge en tête, lignes
    bleues tous les 28 px, intitulé, tampon des nouvelles offres, résumé
    à chasse fixe calé sur les lignes et actions. */
Item {
    id: racine

    required property string nom
    required property string intitule
    required property var lignes
    required property string nouvelles
    /*! Date JJ/MM/AA du comptage des nouvelles (relevé ou lancement). */
    required property string dateNouvelles

    signal lancer(string nom)
    signal modifier(string nom)
    signal dupliquer(string nom)
    signal supprimer(string nom)

    // Lignes de la maquette : motif de 28 px décalé de 64 px, soit y ≡ 7 (mod 28) sous le filet de 3 px.
    readonly property real premiereLigne: 3 + 7
    readonly property real pasLignes: 28

    implicitHeight: Math.max(240, colonne.implicitHeight + 3 + 14 + 16)

    Accessible.role: Accessible.Grouping
    Accessible.name: intitule

    RectangularShadow {
        anchors.fill: parent
        offset.y: 10
        blur: 22
        color: Theme.ombrePorteeLegere
    }
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 2
        anchors.bottomMargin: -2
        color: Theme.ombre
    }
    Rectangle {
        id: carton
        anchors.fill: parent
        color: Theme.bristol

        Repeater {
            model: Math.max(0, Math.floor((carton.height - racine.premiereLigne) / racine.pasLignes) + 1)
            Rectangle {
                required property int index
                y: racine.premiereLigne + index * racine.pasLignes
                width: carton.width
                height: 1
                color: Theme.bristolLigne
            }
        }
        Rectangle {
            width: parent.width
            height: 3
            color: Theme.bristolTete
        }
    }

    MouseArea {
        anchors.fill: parent
        onDoubleClicked: racine.lancer(racine.nom)
    }

    ColumnLayout {
        id: colonne
        x: 18
        y: 3 + 14
        width: parent.width - 36
        height: parent.height - 3 - 14 - 16
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Layout.minimumHeight: 48
            spacing: 10

            Texte {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                text: racine.intitule
                font.pixelSize: 22
                font.variableAxes: { "wdth": 90, "wght": 800 }
                Accessible.role: Accessible.Heading
            }
            Item {
                id: emplacementTampon
                Layout.alignment: Qt.AlignTop
                visible: racine.nouvelles !== ""
                implicitWidth: tamponNouvelles.implicitWidth
                implicitHeight: tamponNouvelles.implicitHeight

                Tampon {
                    id: tamponNouvelles
                    rotation: 3
                    texte: racine.nouvelles
                    date: racine.dateNouvelles
                    encre: Theme.rouge
                    fond: Theme.bristol
                }
            }
        }

        Texte {
            Layout.fillWidth: true
            text: racine.lignes.join("\n")
            color: Theme.encre2
            font.family: Theme.policeMono
            font.pixelSize: 14
            lineHeight: 28
        }

        Item { Layout.fillHeight: true }

        Flow {
            Layout.fillWidth: true
            spacing: 6

            BoutonTampon {
                text: "Lancer"
                Accessible.name: "Lancer la fiche « " + racine.intitule + " »"
                onClicked: racine.lancer(racine.nom)
            }
            Item { width: 4; height: 1 }
            LienCrayon {
                text: "modifier"
                onClicked: racine.modifier(racine.nom)
            }
            LienCrayon {
                text: "dupliquer"
                onClicked: racine.dupliquer(racine.nom)
            }
            LienCrayon {
                text: "supprimer"
                encre: Theme.rouge
                onClicked: racine.supprimer(racine.nom)
            }
        }
    }

    // Encre du tampon mélangée aux lignes bleues qu'il traverse : copie du tampon
    // découpée à la hauteur de chaque ligne, mélangée à la couleur de la ligne.
    Repeater {
        model: emplacementTampon.visible ? 6 : 0
        Item {
            id: bande
            required property int index
            readonly property point origine: emplacementTampon.mapToItem(racine, 0, 0)
            readonly property real premiere: Math.ceil((origine.y - 6 - racine.premiereLigne) / racine.pasLignes)
            y: racine.premiereLigne + (premiere + index) * racine.pasLignes
            width: racine.width
            height: 1
            clip: true
            visible: y >= origine.y - 6 && y <= origine.y + emplacementTampon.height + 6

            Tampon {
                x: bande.origine.x
                y: bande.origine.y - bande.y
                rotation: 3
                texte: racine.nouvelles
                date: racine.dateNouvelles
                encre: Theme.rouge
                fond: Theme.bristolLigne
                Accessible.ignored: true
            }
        }
    }
}
