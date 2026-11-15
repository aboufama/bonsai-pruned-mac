#!/bin/bash
# One-time download of the icon set and web fonts the generator inlines / serves locally.
# Everything lands in ./assets next to this script; nothing is fetched at generation time.
#
#   icons : lucide-static 1.73.0 (ISC licence; some icons derive from Feather, MIT)
#   more icon sets : heroicons, @tabler/icons, @material-symbols/svg-400 (see below)
#   fonts : @fontsource packages 5.3.x, latin subset, woff2 (all SIL OFL 1.1)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p assets/dl assets/icons assets/fonts
cd assets

fetch() {  # url, output file
  [ -s "$2" ] || curl -fsSL "$1" -o "$2"
}

fetch https://registry.npmjs.org/lucide-static/-/lucide-static-1.73.0.tgz dl/lucide-static.tgz
rm -rf dl/lucide && mkdir -p dl/lucide
tar -xzf dl/lucide-static.tgz -C dl/lucide --wildcards 'package/icons/*.svg' 'package/LICENSE'
cp dl/lucide/package/icons/*.svg icons/
cp dl/lucide/package/LICENSE icons/LICENSE.lucide

for spec in inter:5.3.0 roboto:5.3.0 open-sans:5.3.0 ibm-plex-sans:5.3.0 source-sans-3:5.3.1 \
            jetbrains-mono:5.3.0 fira-code:5.3.0; do
  name=${spec%%:*}; ver=${spec##*:}
  fetch "https://registry.npmjs.org/@fontsource/$name/-/$name-$ver.tgz" "dl/$name.tgz"
  rm -rf "dl/$name" && mkdir -p "dl/$name"
  tar -xzf "dl/$name.tgz" -C "dl/$name"
  for w in 400 500 600 700; do
    f="dl/$name/package/files/$name-latin-$w-normal.woff2"
    [ -f "$f" ] && cp "$f" "fonts/$name-$w.woff2"
  done
  cp "dl/$name/package/LICENSE" "fonts/LICENSE.$name" 2>/dev/null || true
done
rm -rf dl/lucide dl/inter dl/roboto dl/open-sans dl/ibm-plex-sans dl/source-sans-3 dl/jetbrains-mono dl/fira-code
# More web icon sets, for the icon-only screens (generate_icons.py). Outline styles only.
#   heroicons 2.2.0 (MIT), @tabler/icons 3.52.0 (MIT), @material-symbols/svg-400 0.49.0 (Apache-2.0)
for spec in heroicons:heroicons/-/heroicons-2.2.0.tgz:24/outline tabler:@tabler/icons/-/icons-3.52.0.tgz:icons/outline \
            material:@material-symbols/svg-400/-/svg-400-0.49.0.tgz:outlined; do
  IFS=: read -r name tarball sub <<< "$spec"
  if [ ! -s "iconsets/$name/LICENSE" ]; then
    fetch "https://registry.npmjs.org/$tarball" "dl/$name.tgz"
    rm -rf "dl/$name" && mkdir -p "dl/$name" "iconsets/$name"
    tar -xzf "dl/$name.tgz" -C "dl/$name"
    find "dl/$name/package/$sub" -maxdepth 1 -name '*.svg' ! -name '*-fill.svg' -exec cp {} "iconsets/$name/" \;
    cp "dl/$name/package/LICENSE" "iconsets/$name/LICENSE"
    rm -rf "dl/$name"
  fi
  echo "iconsets/$name: $(ls iconsets/$name/*.svg | wc -l)"
done
echo "icons: $(ls icons/*.svg | wc -l)   fonts: $(ls fonts/*.woff2 | wc -l)"
