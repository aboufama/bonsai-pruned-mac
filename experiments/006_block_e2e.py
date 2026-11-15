# Experiment 006: train layers 4..19 together as one chain, staying ternary (weightlab/e2e.py).
#
# Two signals per training screen: the block's states should match what the teacher's layers
# produce from the same input (hint), and the answer read out through Bonsai's own frozen top
# layers should land in the target box (task). Codes, multipliers and the small full-precision
# parts of the 16 layers are all open. Training data are generated screens (train split);
# ScreenSpot-v2 is only used to measure.
#
# Settings can be preset as globals: TEACHER, STEPS6, ROUND6, HINT6, TASK6, LR_CODES6,
# TEXT_WEIGHT6, TRAIN6 (a lab.data name), TAG6.
import json
import os
import time

import torch
from weightlab.e2e import BlockTrainer

LO, HI = 4, 19
TEACHER = globals().get("TEACHER", "V")
STEPS = globals().get("STEPS6", 600)
ROUND = globals().get("ROUND6", 150)
HINT = globals().get("HINT6", 1.0)
TASK = globals().get("TASK6", 1.0)
LR_CODES = globals().get("LR_CODES6", 1e-2)
TEXT_WEIGHT = globals().get("TEXT_WEIGHT6", 4.0)
TRAIN = globals().get("TRAIN6", "gen:benchdata/pointing/train_s101")
TAG = globals().get("TAG6", f"{TEACHER}_s{STEPS}_h{HINT:g}_t{TASK:g}")

dev = lab.data("ssv2", n=32)
held = lab.data("ssv2", n=32, offset=23)
train = lab.data(TRAIN, n=globals().get("NTRAIN6", 3000))
if "fB" not in globals():
    fB = lab.fast(dev, "B", every=4)
if "fH" not in globals():
    fH = lab.fast(held, "B", every=4)
out = {"tag": TAG, "teacher": TEACHER, "steps": STEPS, "hint": HINT, "task": TASK, "lr_codes": LR_CODES,
       "text_weight": TEXT_WEIGHT, "train": TRAIN, "rows": []}


def fast_line(label):
    a, h = fB.evaluate(LO, tag=f"006:{TAG}:{label}"), fH.evaluate(LO, tag=f"006:{TAG}:{label}:held")
    fB.discard(); fH.discard()
    out["rows"].append({"label": label, "dev": a, "held": h})
    print("%-34s dev p_hit %.3f (hundreds %.3f tens %.3f)   held-out p_hit %.3f" % (
        label, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], h["p_hit"]), flush=True)


print(f"{TAG}: teacher {TEACHER}, {STEPS} steps, hint x{HINT:g}, task x{TASK:g}, codes lr {LR_CODES:g}, {len(train)} cases from {TRAIN}")
fast_line("before")
E = BlockTrainer(lab, LO, HI, teacher=TEACHER)
orig = f"{lab.dir}/ckpt/orig_L{LO}-{HI}.safetensors"
if not os.path.exists(orig):
    E.D.save(range(LO, HI + 1), orig)
E.open(lr_codes=LR_CODES, lr_scales=globals().get("LR_SCALES6", 1e-3), lr_fp=globals().get("LR_FP6", 1e-4),
       codes=globals().get("CODES6", True), fp=globals().get("FP6", True))
started = time.time()
for r in range(0, STEPS, ROUND):
    res = E.train(train, min(ROUND, STEPS - r), total_steps=STEPS, task=TASK, hint=HINT, text_weight=TEXT_WEIGHT)
    a, h = E.score(dev), E.score(held)
    out["rows"].append({"label": f"step {E.steps_done}", "dev": a, "held": h, "train": res})
    print("after %4d steps: dev p_hit %.3f (hundreds %.3f tens %.3f)   held-out p_hit %.3f   train task loss %.2f   [%.0f min]" % (
        E.steps_done, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], h["p_hit"], res["task_end"],
        (time.time() - started) / 60), flush=True)
closed = E.close()
print("codes changed: %.2f%% of the block" % (100 * closed["codes_changed_share"]))
out["closed"] = closed
fast_line("after, written back as ternary")
ckpt = E.D.save(range(LO, HI + 1), f"{lab.dir}/ckpt/e2e_{TAG}_L{LO}-{HI}.safetensors")
out["canary"] = lab.canary(lab.B, tag=f"006:{TAG}")
print("canary:", out["canary"]["all"], "(before any training: tf_exact 0.86, nll 0.076)")
print("saved", ckpt)
json.dump(out, open(f"{lab.dir}/exp006_{TAG}.json", "w"), indent=1)
