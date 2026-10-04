pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Tamponne

/*! Fenêtre de sélection multiple (Domaines, Localisations, Organisations,
    Corps / Grade) : recherche insensible aux accents, groupes repliables
    à case partielle, compteur de cases cochées. */
Dialogue {
    id: racine

    property string liste: ""
    /*! `[{ groupe, elements: [{ valeur, libelle }] }]`, groupe vide pour une liste simple. */
    property var groupes: []
    /*! Valeurs cochées : objet utilisé comme ensemble, réaffecté à chaque changement. */
    property var choisis: ({})
    property var replies: ({})
    property string filtre: ""

    signal valide(string liste, var valeurs)

    width: liste === "organisations" ? 560 : 460

    function ouvrirPour(nomListe: string, titreFenetre: string, groupesProposes: var, selection: var) {
        liste = nomListe
        titre = titreFenetre
        groupes = groupesProposes
        const ensemble = {}
        for (const valeur of selection)
            ensemble[valeur] = true
        choisis = ensemble
        const fermes = {}
        groupesProposes.forEach((g, rang) => { if (rang > 0) fermes[g.groupe] = true })
        replies = fermes
        champRecherche.text = ""
        filtre = ""
        open()
        champRecherche.forceActiveFocus()
    }

    function sansAccents(texte: string): string {
        return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    }

    function correspond(element: var, groupe: string): bool {
        if (filtre === "")
            return true
        const cible = sansAccents(filtre)
        return sansAccents(element.libelle).indexOf(cible) >= 0 || sansAccents(groupe).indexOf(cible) >= 0
    }

    function basculer(valeurs: var, coche: bool) {
        const copie = Object.assign({}, choisis)
        for (const valeur of valeurs) {
            if (coche)
                copie[valeur] = true
            else
                delete copie[valeur]
        }
        choisis = copie
    }

    readonly property var lignes: {
        const resultat = []
        for (const g of groupes) {
            const visibles = g.elements.filter(e => correspond(e, g.groupe))
            if (visibles.length === 0)
                continue
            const ouvert = filtre !== "" || !replies[g.groupe]
            if (g.groupe !== "")
                resultat.push({ type: "groupe", groupe: g.groupe, valeurs: g.elements.map(e => e.valeur), ouvert: ouvert })
            if (g.groupe === "" || ouvert)
                for (const e of visibles)
                    resultat.push({ type: "element", valeur: e.valeur, libelle: e.libelle, enfant: g.groupe !== "" })
        }
        return resultat
    }

    readonly property int nombreChoisis: Object.keys(choisis).length

    ChampSouligne {
        id: champRecherche
        Layout.fillWidth: true
        placeholderText: "Rechercher..."
        Accessible.name: "Rechercher dans « " + racine.titre + " »"
        onTextEdited: racine.filtre = text
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(440, vue.contentHeight + 3)
        color: Theme.papier
        border.color: Theme.encre
        border.width: 1.5

        ListView {
            id: vue
            anchors.fill: parent
            anchors.margins: 1.5
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: racine.lignes
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: racine.titre

            delegate: Rectangle {
                id: ligne
                required property var modelData
                required property int index

                readonly property bool estGroupe: modelData.type === "groupe"
                readonly property int cochesGroupe: estGroupe
                    ? modelData.valeurs.filter(v => racine.choisis[v] === true).length : 0

                width: ListView.view.width
                height: 42
                color: estGroupe ? Theme.papier2 : Theme.papier

                Rectangle {
                    visible: ligne.index < racine.lignes.length - 1
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.regle
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: ligne.estGroupe ? 12 : (ligne.modelData.enfant ? 44 : 12)
                    anchors.rightMargin: 12
                    spacing: 10

                    AbstractButton {
                        visible: ligne.estGroupe
                        implicitWidth: 24
                        implicitHeight: 42
                        Accessible.role: Accessible.Button
                        Accessible.name: (ligne.modelData.ouvert ? "Replier " : "Déplier ") + (ligne.modelData.groupe || "")
                        onClicked: {
                            const copie = Object.assign({}, racine.replies)
                            copie[ligne.modelData.groupe] = ligne.modelData.ouvert
                            racine.replies = copie
                        }
                        contentItem: Text {
                            text: ligne.modelData.ouvert ? "▾" : "▸"
                            color: Theme.encre
                            font.family: Theme.policeMono
                            font.pixelSize: 14
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    CaseCerfa {
                        Layout.fillWidth: true
                        hauteurMinimale: 42
                        text: ligne.estGroupe ? ligne.modelData.groupe : ligne.modelData.libelle
                        gras: ligne.estGroupe
                        coche: ligne.estGroupe
                            ? ligne.cochesGroupe === ligne.modelData.valeurs.length
                            : racine.choisis[ligne.modelData.valeur] === true
                        partiel: ligne.estGroupe && ligne.cochesGroupe > 0
                        onClicked: racine.basculer(
                            ligne.estGroupe ? ligne.modelData.valeurs : [ligne.modelData.valeur], !coche)
                    }
                }
            }
        }
    }

    Texte {
        Layout.fillWidth: true
        text: racine.nombreChoisis === 0 ? "aucun coché"
            : racine.nombreChoisis + (racine.nombreChoisis > 1 ? " cochés" : " coché")
        color: Theme.encre2
        font.family: Theme.policeMono
        font.pixelSize: 14
    }

    boutons: [
        BoutonEtiquette {
            text: "Annuler"
            onClicked: racine.close()
        },
        BoutonTampon {
            Layout.margins: 4
            text: "Valider"
            onClicked: {
                racine.valide(racine.liste, Object.keys(racine.choisis))
                racine.close()
            }
        }
    ]
}
