pragma ComponentBehavior: Bound
import QtQuick

/*! Trait pointillé (`dotted`) ou en tirets (`dashed`) tracé comme Firefox
    (règles relevées au pixel sur ses captures) :
    - épaisseur arrondie au pixel de l'écran, au moins un (1,5 px donne 1
      pixel à l'échelle 1) ;
    - points carrés de cette épaisseur au pas de deux, calés sur la fin du
      trait, ou sur son début pour un soulignement (`ajuste: false`) ;
    - tirets de trois épaisseurs, un à chaque bout, écarts égaux ; sur le
      côté d'un cadre (`coin` : épaisseur des côtés voisins), les tirets
      d'angle mesurent un demi-tiret de plus que cette épaisseur.
    Rectangles plutôt que `Shape` : ni extrémités carrées qui allongent les
    traits, ni texture floue. */
Item {
    id: racine

    property color couleur: Theme.encre2
    property real epaisseur: 1
    /*! « dotted » ou « dashed ». */
    property string style: "dotted"
    property bool vertical: false
    /*! Motif réparti sur toute la longueur (bordure) ; faux pour un
        soulignement de texte, motif régulier depuis le début. */
    property bool ajuste: true
    /*! Épaisseur des côtés voisins d'un cadre en tirets, 0 pour un trait isolé. */
    property real coin: 0

    readonly property real ratio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    readonly property real trait: Math.max(1, Math.floor(epaisseur * ratio)) / ratio
    readonly property real longueur: vertical ? height : width
    readonly property var segments: style === "dashed" ? tirets() : points()
    readonly property var pixels: couverture(segments)

    implicitWidth: vertical ? trait : 0
    implicitHeight: vertical ? 0 : trait

    function points(): var {
        const resultat = []
        const pas = 2 * trait
        if (ajuste) {
            for (let debut = longueur - trait; debut > -trait / 2; debut -= pas)
                resultat.unshift([debut, trait])
        } else {
            for (let debut = 0; debut + trait <= longueur + 0.01; debut += pas)
                resultat.push([debut, trait])
        }
        return resultat
    }

    /*! Segments [début, longueur] découpés aux pixels de l'écran : partie
        pleine et pixels de bord à l'opacité de leur couverture, comme le
        lissage du navigateur (Qt cale les rectangles sur les pixels). */
    function couverture(liste: var): var {
        const resultat = []
        for (const segment of liste) {
            const debut = segment[0] * ratio
            const fin = (segment[0] + segment[1]) * ratio
            const premier = Math.floor(debut)
            const dernier = Math.ceil(fin)
            for (let pixel = premier; pixel < dernier; pixel++) {
                const part = Math.min(fin, pixel + 1) - Math.max(debut, pixel)
                if (part <= 0.001)
                    continue
                const precedent = resultat.length > 0 ? resultat[resultat.length - 1] : null
                if (part >= 0.999 && precedent !== null && precedent[2] >= 0.999
                        && precedent[0] + precedent[1] === pixel / ratio) {
                    precedent[1] += 1 / ratio
                    continue
                }
                resultat.push([pixel / ratio, 1 / ratio, part])
            }
        }
        return resultat
    }

    function tirets(): var {
        const tiret = 3 * trait
        if (longueur <= tiret)
            return [[0, longueur]]
        if (coin > 0) {
            const angle = Math.min(longueur / 2, coin + tiret / 2)
            const interieur = longueur - 2 * angle
            const nombre = Math.max(0, Math.ceil((interieur - tiret) / (2 * tiret)))
            const ecart = (interieur - nombre * tiret) / (nombre + 1)
            const resultat = [[0, angle]]
            for (let i = 0; i < nombre; i++)
                resultat.push([angle + ecart + i * (tiret + ecart), tiret])
            resultat.push([longueur - angle, angle])
            return resultat
        }
        // Assez de tirets pour qu'aucun écart ne dépasse un tiret.
        const nombre = Math.max(2, Math.ceil((longueur + tiret) / (2 * tiret)))
        const pas = (longueur - tiret) / (nombre - 1)
        const resultat = []
        for (let i = 0; i < nombre; i++)
            resultat.push([i * pas, tiret])
        return resultat
    }

    Repeater {
        model: racine.pixels
        Rectangle {
            required property var modelData
            x: racine.vertical ? 0 : modelData[0]
            y: racine.vertical ? modelData[0] : 0
            width: racine.vertical ? racine.trait : modelData[1]
            height: racine.vertical ? modelData[1] : racine.trait
            color: racine.couleur
            opacity: modelData[2]
        }
    }
}
