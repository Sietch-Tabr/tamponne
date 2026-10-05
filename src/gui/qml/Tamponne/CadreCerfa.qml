import QtQuick
import QtQuick.Layouts
import Tamponne

/*! Case numérotée d'un formulaire administratif (`fieldset` de la
    maquette) : cadre d'encre interrompu par la légende en capitales. */
Item {
    id: racine

    property string legende: ""
    default property alias contenu: colonne.data

    // Légende posée à cheval sur le filet du haut, comme un `legend` HTML.
    readonly property real hauteurLegende: titre.implicitHeight

    implicitHeight: hauteurLegende + 10 + colonne.implicitHeight + 12 + 1.5

    Accessible.role: Accessible.Grouping
    Accessible.name: legende

    Rectangle {
        // Fond et trois côtés ; le haut est dessiné à part autour de la légende.
        x: 0
        y: racine.hauteurLegende / 2
        width: parent.width
        height: parent.height - y
        color: Theme.papier
        border.color: Theme.encre
        border.width: 1.5
    }
    Rectangle {
        // Efface le filet du haut derrière la légende (2 px de marge de part et d'autre).
        x: 12 - 2
        y: racine.hauteurLegende / 2 - 1
        width: titre.implicitWidth + 4
        height: 3
        color: Theme.papier
    }
    EtiquetteChamp {
        id: titre
        x: 12
        y: 0
        text: racine.legende
        Accessible.ignored: true
    }

    ColumnLayout {
        id: colonne
        x: 1.5 + 12
        y: racine.hauteurLegende + 10
        width: parent.width - 3 - 24
        spacing: 8
    }
}
