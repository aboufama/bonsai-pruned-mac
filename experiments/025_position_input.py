# Experiment 025, test P1 (15 Nov 02:20): does writing each image token's screen position into
# its vector, where it enters the language model, help pointing? (weightlab/position.py; the module starts
# at zero, so the start is exactly the patched model.) The module (rate 1e-3) trains with the multipliers
# and small parts of layers 4..31 at the gentle rates (1e-4 / 2e-5), plain pointing cases of the mix at long
# sides half 1280 and half 896, UPDATES25 updates scored every EVERY25: written answers on select and report
# at 1280 and 896 (teacher-forced, full passes: the cached scoring cannot be used once the input changes);
# at the end generated hits on report at 1280 and the canary. MODULE25 = False gives the control: the same
# run without the module.
# Settings: UPDATES25, EVERY25, MODULE25, TAG25.
import json
import random
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab.tune import TaskTuner
from weightlab.distill import BlockDistiller

UPDATES, EVERY = globals().get("UPDATES25", 1500), globals().get("EVERY25", 250)
MODULE = globals().get("MODULE25", True)
TAG = globals().get("TAG25", "position" if MODULE else "position_control")
rs = random.Random(25)
items = [dict(it, max_side=rs.choice((1280, 896))) for it in mix]
rs.shuffle(items)
sets = {side: (lab.data("ssv2", mod=(8, 1), max_side=side), lab.data("ssv2", mod=(8, 5), max_side=side)) for side in (1280, 896)}
pos25 = None
if globals().get("pos25_old") is not None:
    pos25_old.remove()
if MODULE:
    from weightlab.position import PositionInput
    pos25 = pos25_old = PositionInput(lab.B)
T25 = TaskTuner(lab, list(range(4, len(list(lab.B.model.language_model.layers)))), scales=True, fp=True, head=False)
if pos25 is not None:
    T25.extra_groups = [{"params": list(pos25.parameters()), "lr": 1e-3}]
out = {"tag": TAG, "module": MODULE, "rows": []}


def line(label):
    t, row = time.time(), {}
    for side, (a, b) in sets.items():
        row[side] = {"select": lab.digits(lab.B, a, tag=f"025:{TAG}:{label}:select:{side}")["p_hit"],
                     "report": lab.digits(lab.B, b, tag=f"025:{TAG}:{label}:report:{side}")["p_hit"]}
    norm = float(pos25.lin.weight.norm()) if pos25 is not None else 0.0
    out["rows"].append({"label": label, "scores": row, "module_norm": norm})
    print("%-12s " % label + "   ".join("%d px select %.3f report %.3f" % (s, r["select"], r["report"]) for s, r in row.items())
          + "   position layer norm %.3f   [%.0f s]" % (norm, time.time() - t), flush=True)
    json.dump(out, open(f"{lab.dir}/exp025_{TAG}.json", "w"), indent=1)


print("test P1, %s: %d updates, scores every %d; %d pointing cases" % ("WITH the position module" if MODULE else "CONTROL, no module", UPDATES, EVERY, len(items)), flush=True)
line("before")
for r0 in range(0, UPDATES, EVERY):
    n = min(EVERY, UPDATES - r0)
    res = T25.train(items[r0:r0 + n], n, lr_scales=1e-4, lr_fp=2e-5, warmup=100, accumulate=1, ema=0.0, seed=25,
                    report_every=125, offset=r0, total=UPDATES, rewarm=25)
    line("update %d" % (r0 + n))
    BlockDistiller(lab, 4, 19, teacher=None).save(range(4, len(list(lab.B.model.language_model.layers))), f"{lab.dir}/ckpt/pos025_{TAG}_last.safetensors")
    if pos25 is not None:
        pos25.save(f"{lab.dir}/ckpt/pos025_{TAG}_last_module.safetensors")
g = lab.score(lab.B, sets[1280][1], tag=f"025:{TAG}:generated")
out["generated_1280"] = g["acc"]
print("generated answers, report set at 1280 px: %5.1f%% of %d on target" % (100 * g["acc"], len(sets[1280][1])), flush=True)
out["canary"] = lab.canary(lab.B, tag=f"025:{TAG}")
print("canary:", out["canary"]["all"])
json.dump(out, open(f"{lab.dir}/exp025_{TAG}.json", "w"), indent=1)
