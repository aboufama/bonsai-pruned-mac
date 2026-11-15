# Experiment 020: the repair recipe on Bonsai 2 4B (the session runs with BONSAI_SIZE=4B).
# Stage 1 repeats what worked first on the 9B: tune only the multipliers on the pointing task,
# here in every layer from 4 up (which layers the 4B's damage sits in has not been mapped).
# Stage 2 is run by the next script in the lane (the block trainer on real Mac screens).
# Settings: UPDATES20, LR20, TAG20.
import json
import time

import torch
from weightlab.tune import TaskTuner

UPDATES = globals().get("UPDATES20", 500)
LR = globals().get("LR20", 1e-3)
TAG = globals().get("TAG20", f"4b_scales_u{UPDATES}")
rows = []


def line(label):
    a, b = fS.evaluate(4, tag=f"020:{TAG}:{label}:select"), fR.evaluate(4, tag=f"020:{TAG}:{label}:report")
    fS.discard(); fR.discard()
    rows.append({"label": label, "select": a, "report": b})
    print("%-30s select %.3f (hundreds %.3f tens %.3f)   report %.3f" % (label, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], b["p_hit"]), flush=True)


print(f"Bonsai 2 {lab.size}: {len(list(lab.B.model.language_model.layers))} layers, width {lab.B.config.text_config.hidden_size}")
line("original")
c0 = lab.canary(lab.B, tag="020:original")
print("canary original:", c0["all"])
t0 = time.time()
T20 = TaskTuner(lab, globals().get("LAYERS20") or list(range(4, 32)), scales=True, head=False)   # LAYERS20: for models with fewer layers (2B: 24)
r = T20.train(mix, UPDATES, lr_scales=LR, warmup=20, accumulate=2, ema=0.98, seed=20, report_every=50)
print("training loss %.3f -> %.3f   [%.0f min]" % (r["loss_start"], r["loss_end"], (time.time() - t0) / 60))
line("multipliers tuned")
c1 = lab.canary(lab.B, tag="020:tuned")
print("canary tuned:", c1["all"])
torch.save(T20.snapshot(), f"{lab.dir}/ckpt/tune_{TAG}.pt")
json.dump({"rows": rows, "canary": [c0, c1]}, open(f"{lab.dir}/exp020_{TAG}.json", "w"), indent=1)
