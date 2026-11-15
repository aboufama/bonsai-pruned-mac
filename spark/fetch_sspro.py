"""Download ScreenSpot-Pro (annotations + every referenced screenshot) and the vision projector for each Bonsai 2 size."""
import json, os, sys, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.expanduser("~/bonsai")
DS = "https://huggingface.co/datasets/likaixin/ScreenSpot-Pro/resolve/main/"

def get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(url, dest + ".part")
            os.replace(dest + ".part", dest)
            return True
        except Exception as e:
            err = e
    print("FAILED", url, err, flush=True)
    return False

with urllib.request.urlopen("https://huggingface.co/api/datasets/likaixin/ScreenSpot-Pro/tree/main/annotations") as r:
    ann = [x["path"] for x in json.load(r) if x["path"].endswith(".json")]
for a in ann:
    get(DS + a, f"{ROOT}/sspro/{a}")
images = set()
for a in ann:
    for item in json.load(open(f"{ROOT}/sspro/{a}")):
        images.add(item["img_filename"])
print(len(ann), "annotation files,", len(images), "images", flush=True)
with ThreadPoolExecutor(16) as pool:
    ok = list(pool.map(lambda p: get(DS + "images/" + urllib.parse.quote(p), f"{ROOT}/sspro/images/{p}"), sorted(images)))
print("images ok:", sum(ok), "of", len(ok), flush=True)
for s in ("2B", "4B", "9B", "27B"):
    f = f"Ternary-Bonsai-2-{s}-mmproj-BF16.gguf"
    print(f, get(f"https://huggingface.co/prism-ml/Ternary-Bonsai-2-{s}-gguf/resolve/main/{f}", f"{ROOT}/models/{f}"), flush=True)
print("SSPRO_FETCH_DONE", flush=True)
