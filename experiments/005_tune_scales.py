# Experiment 005: the cheapest all-ternary change. Leave every code alone and tune only the
# per-group multipliers (one per 128 weights) on the pointing task itself (weightlab/tune.py).
#
# The loss is the differentiable form of the lab's score: at each digit of the answer, the
# probability mass on digits that keep the point inside the target box. Training data are
# generated screens (train split); ScreenSpot-v2 is only used to measure.
#
# Settings can be preset as globals: LAYERS5 (list of layers), STEPS5, HEAD5, FP5, LR5, TAG5.
import json

from weightlab.tune import TaskTuner

LAYERS = globals().get("LAYERS5", list(range(4, 20)))
STEPS = globals().get("STEPS5", 300)
HEAD = globals().get("HEAD5", False)
FP = globals().get("FP5", False)
LR = globals().get("LR5", 1e-3)
TAG = globals().get("TAG5", f"scales_L{LAYERS[0]}-{LAYERS[-1]}_s{STEPS}")

dev = lab.data("ssv2", n=32)
held = lab.data("ssv2", n=32, offset=23)
train = lab.data("gen:benchdata/pointing/train_s101", n=3000)
if "fB" not in globals():
    fB = lab.fast(dev, "B", every=4)
if "fH" not in globals():
    fH = lab.fast(held, "B", every=4)
rows = []


def line(label, lo):
    a, h = fB.evaluate(lo, tag=f"005:{TAG}:{label}"), fH.evaluate(lo, tag=f"005:{TAG}:{label}:held")
    fB.discard(); fH.discard()
    rows.append({"label": label, "dev": a, "held": h})
    print("%-40s dev p_hit %.3f (hundreds %.3f tens %.3f)   held-out p_hit %.3f" % (
        label, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], h["p_hit"]), flush=True)


print(f"multipliers of layers {LAYERS[0]}..{LAYERS[-1]}{' + head' if HEAD else ''}{' + small parts' if FP else ''}, {STEPS} steps, lr {LR}")
line("before", LAYERS[0])
T5 = TaskTuner(lab, LAYERS, scales=True, codes=False, fp=FP, head=HEAD)
snap5 = T5.snapshot()
r = T5.train(train, STEPS, lr_scales=LR)
print("training loss %.3f -> %.3f" % (r["loss_start"], r["loss_end"]))
line("after", LAYERS[0])
json.dump({"tag": TAG, "layers": LAYERS, "steps": STEPS, "train": r, "rows": rows}, open(f"{lab.dir}/exp005_{TAG}.json", "w"), indent=1)
print("kept in memory; T5.restore(snap5) puts the original multipliers back")
