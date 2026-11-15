#!/bin/bash
cd ~/bonsai/ssv2
B=https://huggingface.co/datasets/OS-Copilot/ScreenSpot-v2/resolve/main
for f in screenspot_desktop_v2.json screenspot_mobile_v2.json screenspot_web_v2.json screenspotv2_image.zip; do curl -sL --fail -C - -o $f $B/$f || echo "FAILED $f"; done
python3 -c "import zipfile; zipfile.ZipFile(\"screenspotv2_image.zip\").extractall(\".\")"
ls | head; find . -name "*.png" | wc -l; echo SSV2_DONE
