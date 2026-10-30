pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Tamponne

/*! Fiche bristol d'un profil de recherche : filet rouge en tête, lignes
    bleues tous les 28 px, intitulé, résumé à chasse fixe calé sur les
    lignes et actions. */
Item {
    id: racine

    required property string nom
    required property string intitule
    required property var lignes

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
        }

        // Occupe la hauteur restante (« margin-top: auto » des actions) sans
        // l'écart d'un élément d'espacement ; le texte garde sa hauteur propre.
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            implicitHeight: resume.implicitHeight
            Texte {
                id: resume
                width: parent.width
                text: racine.lignes.join("\n")
                color: Theme.encre2
                font.family: Theme.policeMono
                font.pixelSize: 14
                lineHeight: 28
            }
        }

        // « gap: 6px 8px », « align-items: center » de la maquette.
        RangeeFlex {
            Layout.fillWidth: true
            ecartColonnes: 8
            ecartLignes: 6

            // « margin: 4px 10px 4px 4px » du tampon.
            Item {
                implicitWidth: boutonLancer.implicitWidth + 14
                implicitHeight: boutonLancer.implicitHeight + 8
                BoutonTampon {
                    id: boutonLancer
                    x: 4
                    y: 4
                    text: "Lancer"
                    Accessible.name: "Lancer la demande «\u00a0" + racine.intitule + "\u00a0»"
                    onClicked: racine.lancer(racine.nom)
                }
            }
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
}
