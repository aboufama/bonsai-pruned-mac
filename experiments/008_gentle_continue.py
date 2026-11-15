# Experiment 008: experiment 006a showed that 100 more steps at the original learning rate make
# the multiplier-tuned model (005) worse on real screens whatever is opened and whichever
# screens are used. With one screen per step and Adam restarting at full step size, the model is
# knocked off a good spot and the short run ends before it settles. Two changes here:
#   1. a larger yardstick: two disjoint sets of 159 ScreenSpot-v2 screens (positions 1 and 5
#      modulo 8), "select" for choosing between runs and "report" for the number we quote
#   2. a gentle continuation: learning rate 5x lower with a warm-up, two screens per update,
#      and the multipliers written back are a running average over the run
# Settings: LR8, UPDATES8, ACC8, EMA8, WARM8, LAYERS8, TAG8.
import json
import random
import time
import torch
if globals().get("RELOAD8", True):
    import weightlab.hot as hot, importlib
    importlib.reload(hot); hot.reload(globals())
from weightlab.tune import TaskTuner
from weightlab.distill import BlockDistiller

LR = globals().get("LR8", 2e-4)
UPDATES = globals().get("UPDATES8", 300)
ACC = globals().get("ACC8", 2)
EMA = globals().get("EMA8", 0.98)
WARM = globals().get("WARM8", 30)
LAYERS = globals().get("LAYERS8", list(range(4, 20)))
HEAD = globals().get("HEAD8", False)
TAG = globals().get("TAG8", f"gentle_lr{LR:g}_u{UPDATES}_a{ACC}")
D8 = BlockDistiller(lab, 4, 19, teacher="V")
orig, s005 = f"{lab.dir}/ckpt/orig_L4-19.safetensors", f"{lab.dir}/ckpt/tune005_L4-19.safetensors"

if "fS" not in globals():
    sel = lab.data("ssv2", mod=(8, 1))
    rep = lab.data("ssv2", mod=(8, 5))
    t = time.time()
    fS = lab.fast(sel, "B", keep={0, 4})
    fR = lab.fast(rep, "B", keep={0, 4})
    print(f"select {len(sel)} and report {len(rep)} screens warmed in {time.time() - t:.0f}s")
rows = []


def line(label, lo=4):
    r = {}
    for name, f in (("select", fS), ("report", fR), ("dev32", fB), ("held32", fH)):
        r[name] = f.evaluate(lo, tag=f"008:{TAG}:{label}:{name}")
        f.discard()
    rows.append({"label": label, **{k: v["p_hit"] for k, v in r.items()},
                 "hundreds": r["select"]["p_ok_hundreds"], "tens": r["select"]["p_ok_tens"]})
    print("%-34s select %.3f (hundreds %.3f tens %.3f)  report %.3f   | old 32s: %.3f  %.3f" % (
        label, r["select"]["p_hit"], r["select"]["p_ok_hundreds"], r["select"]["p_ok_tens"], r["report"]["p_hit"],
        r["dev32"]["p_hit"], r["held32"]["p_hit"]), flush=True)
    return r["select"]["p_hit"]


if "base8" not in globals():
    D8.restore(orig)
    line("original Bonsai")
    D8.restore(s005)
    base8 = line("multipliers tuned (005)")
    lab.stack[:] = ["tune:scales:L4-19:400"]
train1 = lab.data("gen:benchdata/pointing/train_s101", n=3000)
train2 = lab.data("gen:benchdata/pointing/train_s202", n=6000)
mix = train1 + train2
random.Random(8).shuffle(mix)
best8 = globals().get("best8", base8)
print(f"{TAG}: multipliers of layers {LAYERS[0]}..{LAYERS[-1]}{' + head' if HEAD else ''}, {UPDATES} updates of {ACC} screens, lr {LR:g}; to beat on select: {best8:.3f}")
T8 = TaskTuner(lab, LAYERS, scales=True, head=HEAD)
snap8 = T8.snapshot()
r = T8.train(mix, UPDATES, lr_scales=LR, warmup=WARM, accumulate=ACC, ema=EMA, seed=globals().get("SEED8", 8))
print("training loss %.3f -> %.3f" % (r["loss_start"], r["loss_end"]))
after8 = line(f"after {TAG}")
json.dump(rows, open(f"{lab.dir}/exp008_{TAG}.json", "w"), indent=1)
if after8 > best8:
    best8 = after8
    torch.save(T8.snapshot(), f"{lab.dir}/ckpt/tune_{TAG}.pt")
    if LAYERS[0] >= 4 and LAYERS[-1] <= 19 and not HEAD:
        D8.save(range(4, 20), f"{lab.dir}/ckpt/tune008_{TAG}_L4-19.safetensors")
    print("better on the select set: kept in memory and saved as", f"tune_{TAG}.pt")
else:
    T8.restore(snap8)
    lab.stack.pop()
    print("not better on the select set: put back")
