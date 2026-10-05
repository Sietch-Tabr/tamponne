import QtQuick

/*! Rangée qui passe à la ligne comme `display: flex; flex-wrap: wrap;
    align-items: center` : écarts distincts entre colonnes et entre lignes,
    éléments centrés verticalement dans leur ligne (le `Flow` de Qt n'a
    qu'un espacement et aligne en haut). Les enfants sont placés à leur
    taille implicite. */
Item {
    id: racine

    property real ecartColonnes: 8
    property real ecartLignes: 6

    implicitHeight: hauteurContenu
    property real hauteurContenu: 0

    // Toute variation de taille d'un enfant relance la disposition.
    readonly property var tailles: {
        const resultat = []
        for (let i = 0; i < children.length; i++) {
            const enfant = children[i]
            resultat.push(enfant.visible ? enfant.implicitWidth + "x" + enfant.implicitHeight : "-")
        }
        return resultat.join(" ")
    }

    onTaillesChanged: Qt.callLater(disposer)
    onWidthChanged: Qt.callLater(disposer)
    Component.onCompleted: disposer()

    function disposer(): void {
        const lignes = []
        let ligne = []
        let largeurLigne = 0
        for (let i = 0; i < children.length; i++) {
            const enfant = children[i]
            if (!enfant.visible)
                continue
            const largeur = enfant.implicitWidth
            if (ligne.length > 0 && largeurLigne + ecartColonnes + largeur > width) {
                lignes.push(ligne)
                ligne = []
                largeurLigne = 0
            }
            largeurLigne += (ligne.length > 0 ? ecartColonnes : 0) + largeur
            ligne.push(enfant)
        }
        if (ligne.length > 0)
            lignes.push(ligne)

        let y = 0
        for (const elements of lignes) {
            let hauteurLigne = 0
            for (const element of elements)
                hauteurLigne = Math.max(hauteurLigne, element.implicitHeight)
            let x = 0
            for (const element of elements) {
                element.x = x
                element.y = y + (hauteurLigne - element.implicitHeight) / 2
                element.width = element.implicitWidth
                element.height = element.implicitHeight
                x += element.implicitWidth + ecartColonnes
            }
            y += hauteurLigne + ecartLignes
        }
        hauteurContenu = lignes.length > 0 ? y - ecartLignes : 0
    }
}
