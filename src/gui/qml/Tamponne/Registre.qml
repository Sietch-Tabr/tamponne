pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import Tamponne

/*! Tableau du registre des offres : en-têtes à chasse fixe triables,
    filets de colonnes, ligne sélectionnée au surligneur, tampon
    « Nouveau » après l'intitulé des offres nouvelles. */
Item {
    id: racine

    /*! `ControleurRecherche` : modèle trié, sélection, tri. */
    required property var recherche

    // Largeurs relevées sur la maquette (49, 265, 165, 108, 97, 154 px pour 838 px), tableau de 820 px minimum.
    readonly property var proportions: [49, 265, 165, 108, 97, 154]
    readonly property real largeurTableau: Math.max(820, width)
    readonly property var entetes: ["N°", "Intitulé", "Employeur", "Lieu", "Publiée", "Source"]

    function largeurColonne(colonne: int): real {
        return largeurTableau * proportions[colonne] / 838
    }

    Accessible.role: Accessible.Table
    Accessible.name: "Registre des offres"

    Flickable {
        id: horizontal
        anchors.fill: parent
        contentWidth: racine.largeurTableau
        flickableDirection: Flickable.HorizontalFlick
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        interactive: contentWidth > width
        ScrollBar.horizontal: ScrollBar {}

        Row {
            id: entete
            width: racine.largeurTableau
            height: 37

            Repeater {
                model: racine.entetes
                AbstractButton {
                    id: enteteColonne
                    required property string modelData
                    required property int index
                    readonly property bool trie: racine.recherche.tri.colonne === index
                    width: racine.largeurColonne(index)
                    height: entete.height
                    focusPolicy: Qt.StrongFocus
                    Accessible.role: Accessible.ColumnHeader
                    Accessible.name: modelData + (trie ? (racine.recherche.tri.ordre === 0 ? ", tri croissant" : ", tri décroissant") : "")
                    onClicked: racine.recherche.trier(index)

                    contentItem: EtiquetteChamp {
                        leftPadding: 10
                        rightPadding: 10
                        text: enteteColonne.modelData + (enteteColonne.trie ? (racine.recherche.tri.ordre === 0 ? " ▴" : " ▾") : "")
                        Accessible.ignored: true
                    }
                    background: Item {
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 2
                            color: Theme.encre
                        }
                        Rectangle {
                            visible: enteteColonne.index < racine.entetes.length - 1
                            anchors.right: parent.right
                            width: 1
                            height: parent.height - 2
                            color: Theme.regle
                        }
                        Rectangle {
                            visible: enteteColonne.visualFocus
                            anchors.fill: parent
                            color: "transparent"
                            border.color: Theme.tampon
                            border.width: 3
                        }
                    }
                }
            }
        }

        TableView {
            id: table
            objectName: "tableRegistre"
            y: entete.height
            width: racine.largeurTableau
            height: horizontal.height - entete.height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: racine.recherche.modele
            columnWidthProvider: (colonne) => racine.largeurColonne(colonne)
            focus: true
            ScrollBar.vertical: ScrollBar {}

            Keys.onUpPressed: racine.recherche.selectionner(Math.max(0, racine.recherche.ligne_selectionnee - 1))
            Keys.onDownPressed: racine.recherche.selectionner(Math.min(rows - 1, racine.recherche.ligne_selectionnee + 1))
            Keys.onReturnPressed: racine.recherche.ouvrir_en_ligne(racine.recherche.ligne_selectionnee)

            delegate: Rectangle {
                id: cellule
                required property int row
                required property int column
                required property string display
                required property bool nouvelle

                readonly property bool selectionnee: racine.recherche.ligne_selectionnee === row
                implicitHeight: contenu.implicitHeight + 20 + 1
                color: selectionnee ? Theme.surligneur : Theme.papier

                Accessible.role: Accessible.Cell
                Accessible.name: display + (nouvelle ? ", nouvelle" : "")
                Accessible.selected: selectionnee

                Flow {
                    id: contenu
                    x: 10
                    y: 10
                    width: cellule.width - 20
                    spacing: 6

                    Texte {
                        width: Math.min(implicitWidth, contenu.width)
                        text: cellule.display
                        color: cellule.selectionnee ? Theme.surligneTexte : Theme.encre
                        font.family: cellule.column === 0 || cellule.column === 4 ? Theme.policeMono : Theme.policeTexte
                        font.pixelSize: cellule.column === 0 || cellule.column === 4 ? 14 : 16
                        font.weight: cellule.column === 1 ? Font.Bold : Font.Normal
                        Accessible.ignored: true
                    }
                    Tampon {
                        visible: cellule.nouvelle
                        rotation: cellule.row % 2 === 0 ? -2 : 2
                        texte: "Nouveau"
                        taille: 13
                        encre: cellule.selectionnee ? Theme.surligneTexte : Theme.tampon
                        fond: cellule.selectionnee ? Theme.surligneur : Theme.papier
                        Accessible.ignored: true
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.regle
                }
                Rectangle {
                    visible: cellule.column < 5
                    anchors.right: parent.right
                    width: 1
                    height: parent.height
                    color: Theme.regle
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        table.forceActiveFocus()
                        racine.recherche.selectionner(cellule.row)
                    }
                    onDoubleClicked: racine.recherche.ouvrir_en_ligne(cellule.row)
                }
            }
        }
    }
}
