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

    implicitHeight: entete.height + table.contentHeight

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
                // Le TableView ne remesure pas seul une ligne dont le texte s'est replié.
                onImplicitHeightChanged: Qt.callLater(table.forceLayout)
                color: selectionnee ? Theme.surligneur : Theme.papier

                Accessible.role: Accessible.Cell
                Accessible.name: display + (nouvelle ? ", nouvelle" : "")
                Accessible.selected: selectionnee

                Item {
                    id: contenu
                    x: 10
                    y: 10
                    width: cellule.width - 20
                    // Tampon « Nouveau » à la suite de la dernière ligne de l'intitulé, ou dessous s'il n'y tient pas.
                    // L'espace entre l'intitulé et le tampon dans le HTML, plus « margin-left: 6px ».
                    readonly property real ecartTampon: espaceIntitule.advanceWidth + 6
                    readonly property bool tamponALaSuite: texteCellule.largeurDerniereLigne + ecartTampon + tamponNouveau.implicitWidth <= width
                    implicitHeight: tamponNouveau.visible
                        ? Math.max(texteCellule.yDerniereLigne + texteCellule.lineHeight,
                                   tamponNouveau.y + tamponNouveau.implicitHeight)
                        : texteCellule.height

                    Texte {
                        id: texteCellule
                        property real largeurDerniereLigne: 0
                        property real yDerniereLigne: 0
                        width: contenu.width
                        text: cellule.display
                        color: cellule.selectionnee ? Theme.surligneTexte : Theme.encre
                        font.family: cellule.column === 0 || cellule.column === 4 ? Theme.policeMono : Theme.policeTexte
                        // 16 px partout : dans la maquette, « .registre td » l'emporte sur « .mono ».
                        font.pixelSize: 16
                        font.weight: cellule.column === 1 ? Font.Bold : Font.Normal
                        Accessible.ignored: true
                        onLineLaidOut: (ligne) => {
                            if (!ligne.isLast)
                                return
                            largeurDerniereLigne = ligne.implicitWidth
                            // Tampon accolé (« vertical-align: bottom ») : il agrandit la
                            // dernière ligne, que le navigateur descend d'autant.
                            if (tamponNouveau.visible
                                    && ligne.implicitWidth + contenu.ecartTampon + tamponNouveau.implicitWidth <= contenu.width)
                                ligne.y += Math.max(0, tamponNouveau.implicitHeight - lineHeight)
                            yDerniereLigne = ligne.y
                        }
                    }
                    TextMetrics {
                        id: espaceIntitule
                        font: texteCellule.font
                        text: " "
                    }
                    Tampon {
                        id: tamponNouveau
                        visible: cellule.nouvelle
                        x: contenu.tamponALaSuite ? texteCellule.largeurDerniereLigne + contenu.ecartTampon : 0
                        // Aligné sur le bas de la dernière ligne pour ne pas mordre sur la ligne du dessus.
                        y: contenu.tamponALaSuite
                            ? texteCellule.yDerniereLigne + texteCellule.lineHeight - implicitHeight
                            : texteCellule.height + 4
                        rotation: cellule.row % 2 === 0 ? -2 : 2
                        texte: "Nouveau"
                        taille: 11
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
