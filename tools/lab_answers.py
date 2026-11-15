"""The lab's written answers on the first N report cases at 1280 px, for comparing another runtime (a GGUF
in llama.cpp) with it. Writes one JSON line per case: id, image file name, instruction, box1000, answer,
and the shrunk PNG the lab feeds the processor.   BONSAI_SIZE=9B python3 tools/lab_answers.py <patch> <out dir> [N=20]"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
from weightlab import state
from weightlab.core import Lab

patch, out_dir = sys.argv[1:3]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
os.makedirs(f"{out_dir}/images", exist_ok=True)
lab = Lab(ROOT)
lab.B
state.apply_patch(lab, patch)
data = lab.data("ssv2", mod=(8, 5))[:n]
answers = lab.score(lab.B, data, tag="lab_answers")["answers"]
with open(f"{out_dir}/answers.jsonl", "w") as f:
    for it, text in zip(data, answers):
        lab.image(it).save(f"{out_dir}/images/{it['id']}.png")
        f.write(json.dumps({"id": it["id"], "image": it["id"] + ".png", "instruction": it["instruction"],
                            "box1000": [round(v, 2) for v in it["box1000"]], "answer": text}) + "\n")
print("LAB ANSWERS: %d cases in %s" % (len(data), out_dir), flush=True)
