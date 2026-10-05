import QtQuick
import Tamponne

/*! Texte de l'interface : police Archivo, couleur d'encre et exposition
    aux lecteurs d'écran (un `Text` QML nu n'y apparaît pas). */
Text {
    color: Theme.encre
    font.family: Theme.policeTexte
    font.pixelSize: 16
    wrapMode: Text.Wrap
    textFormat: Text.PlainText
    lineHeightMode: Text.FixedHeight
    lineHeight: Theme.ligneNormale(font.family === Theme.policeMono, font.pixelSize)
    verticalAlignment: Text.AlignVCenter

    Accessible.role: Accessible.StaticText
    Accessible.name: textFormat === Text.PlainText ? text : text.replace(/<[^>]*>/g, "")
}
