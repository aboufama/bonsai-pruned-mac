#!/bin/sh
# Builds (only when a source file changed) and starts the Bonsai assistant.
#   assistant/run.sh                                     the menu-bar app
#   assistant/run.sh --test                              the checks of the core
#   assistant/run.sh --samples ~/Bonsai-demo/samples     pointing on saved screenshots (no capture, no events)
#   assistant/run.sh --transcribe request.wav            the speech model on a sound file
# Build products go to ~/Bonsai-demo/build/assistant (set BONSAI_ASSISTANT_BUILD for another place).
HERE="$(cd "$(dirname "$0")" && pwd)"
BUILD="${BONSAI_ASSISTANT_BUILD:-$HOME/Bonsai-demo/build/assistant}"
APP="$BUILD/release/bonsai-assistant"
mkdir -p "$BUILD"
# Nothing newer than the program: start it as it is (no build step, so nothing can ask for the network).
if [ ! -x "$APP" ] || [ -n "$(find "$HERE/Sources" "$HERE/Package.swift" -newer "$APP" -print -quit)" ]; then
    echo "building…"
    # --force-resolved-versions: the package versions already fetched, never newer ones
    if ! swift build -c release --force-resolved-versions --package-path "$HERE" --scratch-path "$BUILD" > "$BUILD/build.log" 2>&1; then
        grep -E "error" "$BUILD/build.log" | head -20
        echo "build failed; full output in $BUILD/build.log"
        exit 1
    fi
fi
if [ "$1" = "--test" ]; then exec "$BUILD/release/assistant-tests"; fi
exec "$APP" "$@"
