#!/bin/bash
cd ~/bonsai/models
get() { # size file
  local repo="prism-ml/Ternary-Bonsai-2-$1-gguf" f="$2"
  curl -sL --fail -C - -o "$f" "https://huggingface.co/$repo/resolve/main/$f" || { echo "FAILED $f"; return; }
  want=$(curl -s "https://huggingface.co/api/models/$repo/tree/main" | python3 -c "import sys,json; [print(x[\"lfs\"][\"oid\"]) for x in json.load(sys.stdin) if x[\"path\"]==\"$f\"]")
  got=$(sha256sum "$f" | cut -d" " -f1)
  [ "$want" = "$got" ] && echo "OK $f $(du -h "$f" | cut -f1)" || echo "CHECKSUM MISMATCH $f"
}
for s in 2B 4B 9B 27B; do get $s Ternary-Bonsai-2-$s-PTQ1_0.gguf; done
for s in 2B 4B 9B 27B; do get $s Ternary-Bonsai-2-$s-PQ2_0.gguf; done
echo FETCH_DONE
