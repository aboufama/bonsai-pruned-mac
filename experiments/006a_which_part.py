# Experiment 006a: experiment 006 (everything in layers 4..19 open) lost ground within 150 steps
# although no code had flipped yet. Which opened part does the damage? Each variant starts from
# the multiplier-tuned state of experiment 005 and trains 100 steps on the same screens.
import json
import torch
from weightlab.e2e import BlockTrainer
from weightlab.tune import TaskTuner

STATE = f"{lab.dir}/ckpt/tune005_L4-19.safetensors"
N = globals().get("STEPS6A", 100)
train2 = lab.data("gen:benchdata/pointing/train_s202", n=6000)
train1 = lab.data("gen:benchdata/pointing/train_s101", n=3000)
E = BlockTrainer(lab, 4, 19, teacher="V")
rows = []


def fast(label):
    a, h = fB.evaluate(4), fH.evaluate(4)
    fB.discard(); fH.discard()
    rows.append({"label": label, "dev": a["p_hit"], "held": h["p_hit"], "hundreds": a["p_ok_hundreds"], "tens": a["p_ok_tens"]})
    print("%-58s dev p_hit %.3f (hundreds %.3f tens %.3f)   held-out %.3f" % (label, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], h["p_hit"]), flush=True)


def reset():
    E.D.restore(STATE)
    lab.stack[:] = ["tune:scales:L4-19:400"]


fast("start: multipliers tuned (005)")
variants = [
    ("block trainer, multipliers only, new screens", dict(codes=False, fp=False), train2),
    ("block trainer, multipliers + small parts, new screens", dict(codes=False, fp=True), train2),
    ("block trainer, multipliers only, the 005 screens", dict(codes=False, fp=False), train1),
]
for label, kw, data in variants:
    E.open(lr_scales=1e-3, lr_fp=1e-4, **kw)
    r = E.train(data, N, total_steps=N, task=1.0, hint=0.0, report_every=50)
    E.close()
    fast(f"{label}, {N} steps")
    reset()

T = TaskTuner(lab, list(range(4, 20)), scales=True)
r = T.train(train2, N, lr_scales=1e-3, report_every=50)
fast(f"task tuner (the 005 code path), multipliers only, new screens, {N} steps")
reset()
fast("restored")
json.dump(rows, open(f"{lab.dir}/exp006a_which_part.json", "w"), indent=1)
