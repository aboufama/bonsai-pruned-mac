#!/bin/sh
# Puts everything the app needs at run time into one folder that can be copied to another Mac
# (Apple silicon, macOS 14 or later, no compiler needed there):
#   package.sh [TARGET_FOLDER]        default ~/bonsai-macvm/app-package
set -e
here=$(cd "$(dirname "$0")" && pwd)
build="$HOME/Bonsai-demo/build/assistant"
target=${1:-$HOME/bonsai-macvm/app-package}
swift build -c release --force-resolved-versions --package-path "$here" --scratch-path "$build" > "$build/build.log" 2>&1 \
  || { echo "build failed; see $build/build.log" >&2; exit 1; }
mkdir -p "$target"
cp "$build/release/bonsai-assistant" "$target/bonsai-assistant"
for bundle in "$build"/release/*.bundle; do
  rm -rf "$target/$(basename "$bundle")"
  cp -R "$bundle" "$target/"
done
cp "$here/package/README.md" "$here/package/run-batch.sh" "$here/package/requests-example.txt" "$here/package/planner-system-candidate.txt" "$target/"
cp "$here"/package/voice-example-*.wav "$target/"
chmod +x "$target/bonsai-assistant" "$target/run-batch.sh"
{
  echo "commit $(git -C "$here" rev-parse --short HEAD)$(git -C "$here" diff --quiet HEAD -- "$here" || echo ' plus uncommitted changes')"
  echo "built $(date '+%Y-%m-%d %H:%M %Z') on macOS $(sw_vers -productVersion), $(swift --version 2>/dev/null | head -1)"
  shasum -a 256 "$target/bonsai-assistant" | cut -d' ' -f1 | sed 's/^/sha256 /'
} > "$target/VERSION"
echo "package written to $target"
ls -la "$target"
