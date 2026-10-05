#!/bin/bash
# Lanceur macOS et Linux : double-clic dans le Finder, ou ./Tamponne.command.
# Bloc lu en entier avant exécution, puis exit : une mise à jour qui
# réécrit ce fichier pendant qu'il tourne ne peut rien exécuter d'autre.
{
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
# Depuis un raccourci, le PATH est minimal : uv n'y serait pas.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

signaler() {
    echo "$1" >&2
    if [ -t 2 ]; then
        # Terminal ouvert par ce script : il se fermerait avant lecture.
        [ -n "${TAMPONNE_TERMINAL:-}" ] && read -r -p "Appuyez sur Entrée pour fermer." _
        return
    fi
    if command -v osascript >/dev/null 2>&1; then
        osascript -e 'on run argv' \
            -e 'display alert "Tamponné" message (item 1 of argv) as critical' \
            -e 'end run' "$1" >/dev/null 2>&1
    elif command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Tamponné" --text="$1"
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --title "Tamponné" --error "$1"
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "Tamponné" "$1"
    fi
}

# Linux : lancé par double-clic, aucun terminal n'affiche l'installation
# (macOS ouvre toujours Terminal pour un .command). On s'y relance.
if [ ! -t 1 ] && [ "$(uname)" = Linux ] && [ -z "${TAMPONNE_TERMINAL:-}" ] \
    && { ! command -v uv >/dev/null 2>&1 || [ ! -d .venv ]; }; then
    for terminal in x-terminal-emulator konsole gnome-terminal xfce4-terminal xterm; do
        command -v "$terminal" >/dev/null 2>&1 || continue
        case $terminal in
            gnome-terminal) option=-- ;;
            xfce4-terminal) option=-x ;;
            *) option=-e ;;
        esac
        TAMPONNE_TERMINAL=1 exec "$terminal" "$option" /bin/bash "$PWD/Tamponne.command"
    done
    command -v notify-send >/dev/null 2>&1 \
        && notify-send "Tamponné" "Premier lancement : installation en cours (quelques minutes)…"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Installation de uv, le gestionnaire de Python de Tamponné…"
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        wget -qO- https://astral.sh/uv/install.sh | sh
    fi
    if ! command -v uv >/dev/null 2>&1; then
        signaler "Impossible d'installer uv : vérifiez la connexion internet puis relancez Tamponné."
        exit 1
    fi
fi

if [ ! -d .venv ]; then
    echo "Premier lancement : téléchargement de Python et des composants (quelques minutes)…"
    uv sync
else
    uv sync --quiet
fi || {
    signaler "Impossible de préparer Tamponné : vérifiez la connexion internet puis relancez."
    exit 1
}

uv run --quiet python -m src.lanceur \
    || signaler "Tamponné s'est arrêté sur une erreur. Relancez-le ; si le problème persiste, signalez-le sur Codeberg."
exit 0
}
