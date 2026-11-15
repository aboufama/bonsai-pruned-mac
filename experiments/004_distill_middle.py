# Experiment 004: re-train Bonsai's layers 4..19, staying ternary, to do what the teacher's
# layers 4..19 do (weightlab/distill.py).
#
# Experiment 002 showed that with the teacher's full-precision layers 4..19 between Bonsai's
# own first 4 and last 12 layers, pointing comes back. Here the same 16 layers stay Bonsai
# layers (ternary codes, one multiplier per 128 inputs, the usual small full-precision parts)
# and are trained, four at a time, to reproduce the teacher's layer outputs on generated
# training screens. No answer labels are used and no benchmark screen is seen in training.
#
# Settings can be preset as globals before running: TEACHER ("P" or "V"), STEPS, GROUP, TAG.
import json
import time

import torch
from weightlab.distill import BlockDistiller

LO, HI = 4, 19
TEACHER = globals().get("TEACHER", "V")
STEPS = globals().get("STEPS", 400)
GROUP = globals().get("GROUP", 4)
TEXT_WEIGHT = globals().get("TEXT_WEIGHT", 1.0)
LR_CODES = globals().get("LR_CODES", 1e-2)
TAG = globals().get("TAG", f"{TEACHER}_s{STEPS}")
LM = "model.language_model."

dev = lab.data("ssv2", n=32)
held = lab.data("ssv2", n=32, offset=23)
train = lab.data("gen:benchdata/pointing/train_s101", n=3000)
probe = lab.data("gen:benchdata/pointing/dev_20261114", n=12)     # screens the training never sees
if "fB" not in globals():
    fB = lab.fast(dev, "B", every=4)
if "fH" not in globals():
    fH = lab.fast(held, "B", every=4)
out = {"teacher": TEACHER, "steps": STEPS, "group": GROUP, "text_weight": TEXT_WEIGHT, "lr_codes": LR_CODES, "rows": []}


def line(label, lo=LO):
    a, h = fB.evaluate(lo, tag=f"004:{TAG}:{label}"), fH.evaluate(lo, tag=f"004:{TAG}:{label}:held")
    fB.discard(); fH.discard()
    out["rows"].append({"label": label, "dev": a, "held": h})
    print("%-44s dev p_hit %.3f (hundreds %.3f tens %.3f)   held-out p_hit %.3f" % (
        label, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], h["p_hit"]), flush=True)
    return a, h


def errors(label):
    for mode in ("teacher", "student"):
        e = D.local_error(probe, mode)
        out.setdefault("local_error", {})[f"{label}:{mode}"] = e
        print(f"  layer error, {mode} inputs, {label}: " + " ".join(f"{i}:{v:.2f}" for i, v in e.items()), flush=True)


print(f"teacher {TEACHER}, {STEPS} steps per group of {GROUP}, text weight {TEXT_WEIGHT}, {len(train)} training cases on generated screens")
line("Bonsai as is", 0)
pred = lambda k: any(f"{LM}layers.{i}." in k for i in range(LO, HI + 1))
with lab.swap(pred, TEACHER):
    line(f"ceiling: teacher's own layers {LO}..{HI} (16-bit)")

D = BlockDistiller(lab, LO, HI, teacher=TEACHER)
orig = f"{lab.dir}/ckpt/orig_L{LO}-{HI}.safetensors"
import os
if not os.path.exists(orig):
    D.save(range(LO, HI + 1), orig)
errors("before")

started = time.time()
for g0 in range(LO, HI + 1, GROUP):
    ids = list(range(g0, min(g0 + GROUP, HI + 1)))
    r = D.train(ids, train, steps=STEPS, text_weight=TEXT_WEIGHT, lr_codes=LR_CODES, seed=g0)
    out.setdefault("train", {}).update({str(k): v for k, v in r.items()})
    print("layers %s: " % ids + "  ".join("L%d loss %.3f -> %.3f, %.2f%% codes changed" % (
        i, v["loss_start"], v["loss_end"], 100 * v["codes_changed_share"]) for i, v in r.items()), flush=True)
    line(f"after training layers {ids[0]}..{ids[-1]}")
print("training took %.0f min" % ((time.time() - started) / 60))
errors("after")
ckpt = D.save(range(LO, HI + 1), f"{lab.dir}/ckpt/distill_{TAG}_L{LO}-{HI}.safetensors")
print("saved", ckpt)
out["canary"] = lab.canary(lab.B, tag=f"004:{TAG}")
print("canary after:", out["canary"]["all"], " (before: see lab journal)")
json.dump(out, open(f"{lab.dir}/exp004_{TAG}.json", "w"), indent=1)
