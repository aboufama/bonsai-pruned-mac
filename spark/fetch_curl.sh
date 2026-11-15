#!/bin/bash
# Direct downloads (the hub client stalled). usage: fetch_curl.sh <repo> <dest-dir> <file-regex>
repo=$1; dest=$2; pat=$3
mkdir -p "$dest"; cd "$dest"
curl -s "https://huggingface.co/api/models/$repo/tree/main" | python3 -c "
import sys, json, re
for f in json.load(sys.stdin):
    if f[\"type\"] == \"file\" and re.search(sys.argv[1], f[\"path\"]): print(f[\"path\"])" "$pat" > .files.txt
cat .files.txt | xargs -P 4 -I{} sh -c "curl -sL --fail -C - -o \"{}\" \"https://huggingface.co/$repo/resolve/main/{}\" || echo FAILED {}"
echo "DONE $repo: $(ls | wc -l) files, $(du -sh . | cut -f1)"
