pragma Singleton
import QtQuick

/*!
    Jetons visuels du thème « dossier administratif » (bureau de jour /
    bureau de nuit), seule source des couleurs de l'interface : le code
    Python n'en connaît aucune. Valeurs reprises à l'identique de la
    maquette validée ; toute nouvelle paire texte/fond doit être ajoutée
    au test de contraste (tests/test_gui_qml_theme.py).
*/
QtObject {
    id: theme

    /*! Mode choisi dans Réglages : "auto", "clair" ou "sombre"
        (voir src/parametres_affichage.py). */
    property string mode: "auto"

    /*! Désactive les inclinaisons animées des boutons tampons (réglage
        de l'app : Qt 6.11 n'expose pas la préférence du système). */
    property bool reduireAnimations: false

    // Un schéma système inconnu donne le bureau de nuit, comme l'ancien thème.
    readonly property bool nuit: mode === "sombre"
        || (mode === "auto" && Application.styleHints.colorScheme !== Qt.ColorScheme.Light)

    readonly property bool contrasteEleve:
        Application.styleHints.accessibility.contrastPreference === Qt.HighContrast

    // Bureau, chemise kraft et onglets d'intercalaire
    readonly property color bureau: nuit ? "#0F1512" : "#23302A"
    readonly property color kraft: nuit ? "#4A3B24" : "#D9BF8C"
    readonly property color onglet: nuit ? "#33291A" : "#C4A66C"
    readonly property color ongletSurvol: nuit ? "#4D3E27" : "#D0B57E"
    readonly property color texteKraft: nuit ? "#EADCBE" : "#3E2F12"
    readonly property color pointille: nuit ? "#B89D68" : "#6B5428"

    // Feuilles de papier et encre
    readonly property color papier: nuit ? "#1C221F" : "#FBFAF6"
    readonly property color papier2: nuit ? "#252C28" : "#F2EEE3"
    readonly property color papierGrise: nuit ? "#161B18" : "#ECE8DD"
    readonly property color encre: nuit ? "#ECE6D6" : "#1C1A17"
    readonly property color encre2: nuit ? "#B5AE9E" : "#4A463E"
    readonly property color regle: nuit ? "#3A433E" : "#CFC8B6"
    readonly property color regleMarquee: nuit ? "#56605A" : "#8A8473"

    // Encre de tampon : violet le jour, orange la nuit (violet pastel illisible sur sombre)
    readonly property color tampon: nuit ? "#FFB672" : "#4B2C9E"
    readonly property color surTampon: nuit ? "#1F1408" : "#FFFFFF"
    readonly property color rouge: nuit ? "#FF8E80" : "#B3261E"
    // Vert de jour un peu plus foncé que la maquette (#1F7A45) : 4,5:1 sur le papier grisé.
    readonly property color vert: nuit ? "#82D9A4" : "#1C7240"
    /*! Fusion des tampons avec le papier : produit le jour, écran la nuit. */
    readonly property bool fusionEcran: nuit

    // Surligneur, post-it et fiches bristol
    readonly property color surligneur: nuit ? "#5B521C" : "#F4E27A"
    readonly property color surligneTexte: nuit ? "#FFF4C2" : "#1C1A17"
    readonly property color postit: nuit ? "#D9C44C" : "#F7E36A"
    readonly property color postitTexte: "#1C1A17"
    readonly property color bristol: nuit ? "#1E2530" : "#FFFFFF"
    readonly property color bristolLigne: nuit ? "#2D3A50" : "#C9D6EE"
    readonly property color bristolTete: nuit ? "#E36A60" : "#C8423B"

    // Étiquettes kraft (boutons secondaires)
    readonly property color etiquette: nuit ? "#5E4C2E" : "#E9D7AA"
    readonly property color etiquetteSurvol: nuit ? "#6E5A37" : "#F1E2BC"
    /*! Rouge d'une action destructrice sur étiquette : le rouge de nuit
        n'y atteint que 3,7:1, d'où une teinte plus claire. */
    readonly property color rougeEtiquette: nuit ? "#FFCFC8" : "#B3261E"

    // Logotype et texte posés directement sur le bureau
    readonly property color logo: nuit ? "#E6DCC2" : "#EDE6D3"
    readonly property color sousLogo: nuit ? "#9DAEA3" : "#C9D2CB"

    // Ombres : arête franche sous la feuille, puis halo plus ou moins dense selon l'objet
    readonly property color ombre: nuit ? "#080B09" : "#B39257"
    readonly property color ombrePortee: nuit ? Qt.rgba(0, 0, 0, 0.45) : Qt.rgba(28 / 255, 26 / 255, 23 / 255, 0.18)
    readonly property color ombrePorteeLegere: nuit ? Qt.rgba(0, 0, 0, 0.45) : Qt.rgba(28 / 255, 26 / 255, 23 / 255, 0.16)
    readonly property color ombreMenu: nuit ? Qt.rgba(0, 0, 0, 0.6) : Qt.rgba(28 / 255, 26 / 255, 23 / 255, 0.25)
    readonly property color ombreDialogue: nuit ? Qt.rgba(0, 0, 0, 0.6) : Qt.rgba(28 / 255, 26 / 255, 23 / 255, 0.30)
    readonly property color voile: nuit ? Qt.rgba(0, 0, 0, 0.6) : Qt.rgba(15 / 255, 21 / 255, 18 / 255, 0.55)

    /*! Couleur d'une encre de tampon posée sur un fond uni, mélangée comme
        le `mix-blend-mode` de la maquette : produit le jour, écran la nuit.
        Sur fond uni, le résultat est identique au mélange pixel à pixel. */
    function melanger(encre: color, fond: color): color {
        if (fusionEcran)
            return Qt.rgba(1 - (1 - encre.r) * (1 - fond.r),
                           1 - (1 - encre.g) * (1 - fond.g),
                           1 - (1 - encre.b) * (1 - fond.b), encre.a)
        return Qt.rgba(encre.r * fond.r, encre.g * fond.g, encre.b * fond.b, encre.a)
    }

    /*! Hauteur de ligne « normale » du CSS de la maquette : ascendante et
        descendante de la police (tables hhea, en em) arrondies chacune au
        pixel supérieur, comme le moteur de rendu du navigateur. */
    function ligneNormale(mono: bool, taille: real): real {
        if (mono)
            return Math.ceil(1.025 * taille) + Math.ceil(0.275 * taille)
        return Math.ceil(0.878 * taille) + Math.ceil(0.210 * taille)
    }

    // Polices embarquées (SIL OFL 1.1, licences dans polices/)
    readonly property FontLoader _archivo: FontLoader { source: "polices/Archivo-Variable.ttf" }
    readonly property FontLoader _plexMono: FontLoader { source: "polices/IBMPlexMono-Regular.ttf" }
    readonly property FontLoader _plexMonoDemiGras: FontLoader { source: "polices/IBMPlexMono-SemiBold.ttf" }
    readonly property string policeTexte: _archivo.name
    readonly property string policeMono: _plexMono.name
}
