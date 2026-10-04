pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import Tamponne

/*! Champ de date (JJ/MM/AAAA) ouvrant un calendrier mensuel ; le jour
    choisi est entouré d'un coup d'encre. */
AbstractButton {
    id: racine

    property date dateChoisie: new Date()
    readonly property string dateIso: Qt.formatDate(dateChoisie, "yyyy-MM-dd")
    readonly property var localeFr: Qt.locale("fr_FR")

    implicitHeight: 42
    leftPadding: 2
    focusPolicy: Qt.StrongFocus
    text: Qt.formatDate(dateChoisie, "dd/MM/yyyy")

    Accessible.role: Accessible.Button
    Accessible.name: "Date : " + text

    onClicked: calendrier.open()

    contentItem: Text {
        text: racine.text
        color: Theme.encre
        font.family: Theme.policeMono
        font.pixelSize: 16
        verticalAlignment: Text.AlignVCenter
    }

    background: Item {
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 2
            color: Theme.encre
        }
        Rectangle {
            visible: racine.visualFocus
            anchors.fill: parent
            anchors.margins: -5
            color: "transparent"
            border.color: Theme.tampon
            border.width: 3
        }
    }

    Popup {
        id: calendrier

        property int mois: racine.dateChoisie.getMonth()
        property int annee: racine.dateChoisie.getFullYear()

        y: racine.height + 10
        width: Math.max(racine.width, 300)
        padding: 11.5

        onAboutToShow: {
            mois = racine.dateChoisie.getMonth()
            annee = racine.dateChoisie.getFullYear()
        }

        function decaler(ecart: int) {
            const cible = new Date(annee, mois + ecart, 1)
            mois = cible.getMonth()
            annee = cible.getFullYear()
        }

        background: Item {
            RectangularShadow {
                anchors.fill: parent
                offset.y: 10
                blur: 22
                color: Theme.ombrePortee
            }
            Rectangle {
                anchors.fill: parent
                color: Theme.papier
                border.color: Theme.encre
                border.width: 1.5
            }
        }

        contentItem: ColumnLayout {
            spacing: 6

            RowLayout {
                Layout.fillWidth: true

                AbstractButton {
                    implicitWidth: 44
                    implicitHeight: 42
                    text: "‹"
                    Accessible.role: Accessible.Button
                    Accessible.name: "Mois précédent"
                    onClicked: calendrier.decaler(-1)
                    contentItem: Text {
                        text: "‹"
                        color: Theme.encre
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                Texte {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: racine.localeFr.standaloneMonthName(calendrier.mois) + " " + calendrier.annee
                    font.weight: Font.Bold
                    font.capitalization: Font.AllUppercase
                    font.letterSpacing: 0.6
                    font.variableAxes: { "wdth": 85 }
                }
                AbstractButton {
                    implicitWidth: 44
                    implicitHeight: 42
                    text: "›"
                    Accessible.role: Accessible.Button
                    Accessible.name: "Mois suivant"
                    onClicked: calendrier.decaler(1)
                    contentItem: Text {
                        text: "›"
                        color: Theme.encre
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            DayOfWeekRow {
                Layout.fillWidth: true
                locale: racine.localeFr
                spacing: 2
                delegate: Text {
                    required property string shortName
                    text: shortName.substring(0, 2)
                    color: Theme.encre2
                    font.family: Theme.policeMono
                    font.pixelSize: 12
                    font.capitalization: Font.AllUppercase
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    height: 34
                }
            }

            MonthGrid {
                id: grille
                Layout.fillWidth: true
                // Six semaines de 34 px et cinq écarts de 2 px : la grille n'a pas de hauteur implicite.
                Layout.preferredHeight: 6 * 34 + 5 * 2
                locale: racine.localeFr
                month: calendrier.mois
                year: calendrier.annee
                spacing: 2

                Accessible.role: Accessible.Table
                Accessible.name: racine.localeFr.standaloneMonthName(calendrier.mois) + " " + calendrier.annee

                delegate: Rectangle {
                    id: jour
                    required property var model

                    readonly property bool choisi: model.year === racine.dateChoisie.getFullYear()
                        && model.month === racine.dateChoisie.getMonth()
                        && model.day === racine.dateChoisie.getDate()

                    implicitHeight: 34
                    // Transparents plutôt qu'invisibles : la grille retirerait les jours masqués et décalerait le mois.
                    readonly property bool duMois: model.month === grille.month
                    opacity: duMois ? 1 : 0
                    enabled: duMois
                    Accessible.ignored: !duMois
                    color: "transparent"
                    radius: 4
                    border.width: choisi ? 2.5 : 0
                    border.color: Theme.tampon

                    Accessible.role: Accessible.Cell
                    Accessible.name: model.day + " " + racine.localeFr.standaloneMonthName(model.month)

                    Text {
                        anchors.centerIn: parent
                        text: jour.model.day
                        color: Theme.encre
                        font.family: Theme.policeMono
                        font.pixelSize: 14
                        font.weight: jour.choisi ? Font.Bold : Font.Normal
                    }
                }

                onClicked: (dateCliquee) => {
                    if (dateCliquee.getMonth() !== grille.month)
                        return
                    racine.dateChoisie = dateCliquee
                    calendrier.close()
                }
            }
        }
    }
}
