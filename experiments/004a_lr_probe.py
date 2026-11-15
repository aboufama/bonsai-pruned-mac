# Experiment 004a: how fast should the ternary codes be allowed to move?
# One layer (8, inside the damaged block) is trained for a short run at several learning rates
# for the latent codes, from the same start each time. Judged on screens the training never saw
# (the generator's dev split): the layer's error against the teacher's output.
import json
import torch
from weightlab.distill import BlockDistiller

LAYER = globals().get("LAYER", 8)
STEPS = globals().get("PROBE_STEPS", 120)
TEACHER = globals().get("TEACHER", "V")
train = lab.data("gen:benchdata/pointing/train_s101", n=3000)
probe = lab.data("gen:benchdata/pointing/dev_20261114", n=12)
D = BlockDistiller(lab, 4, 19, teacher=TEACHER)
orig = f"{lab.dir}/ckpt/orig_L4-19.safetensors"
base = D.local_error(probe)[LAYER]
print(f"layer {LAYER} before training: error {base:.3f} against the teacher's output (unseen screens)")

# Part 1: is a ternary copy of the teacher's layer (no training) a better start than Bonsai's own
# layer? Codes and multipliers are re-derived in closed form from the teacher's weights; the
# second number also takes the teacher's small full-precision parts.
from weightlab.core import Tensors
Vt = Tensors(lab.paths[TEACHER])
SMALL = ("layernorm.weight", "norm.weight", "A_log", "dt_bias", "conv1d.weight", "in_proj_a.weight", "in_proj_b.weight")
before = D.local_error(probe)
refit_rows = []
for L in globals().get("REFIT_LAYERS", (6, 8, 11, 15)):
    e = lab.edit(f"refit-{TEACHER}-{L}")
    for name in lab.tern:
        if f"layers.{L}." in name:
            e.refit(name, Vt.get(name + ".weight"), "codes")
    st = e.apply()
    err_t = D.local_error(probe)[L]
    with lab.swap(lambda k, L=L: f"layers.{L}." in k and k.endswith(SMALL), TEACHER):
        err_b = D.local_error(probe)[L]
    e.revert()
    refit_rows.append({"layer": L, "bonsai": before[L], "refit": err_t, "refit_plus_small": err_b})
    print("layer %2d: Bonsai's own %.2f | ternary copy of the teacher %.2f | plus the teacher's small parts %.2f" % (
        L, before[L], err_t, err_b), flush=True)
torch.cuda.empty_cache()

# Part 2: short training runs of one layer at several learning rates for the codes.
rows = []
for name, kw in (("multipliers and small parts only", dict(codes=False)),
                 ("codes lr 0.003", dict(lr_codes=3e-3)),
                 ("codes lr 0.01", dict(lr_codes=1e-2)),
                 ("codes lr 0.03", dict(lr_codes=3e-2))):
    r = D.train([LAYER], train, steps=STEPS, seed=1, report_every=40, **kw)[LAYER]
    e = D.local_error(probe)[LAYER]
    rows.append({"setting": name, "error_unseen": e, **r})
    print("%-34s error on unseen screens %.3f   train loss %.3f -> %.3f   codes changed %.2f%%" % (
        name, e, r["loss_start"], r["loss_end"], 100 * r["codes_changed_share"]), flush=True)
    D.restore(orig)
    lab.stack.pop()
json.dump({"layer": LAYER, "steps": STEPS, "before": base, "refit": refit_rows, "rows": rows}, open(f"{lab.dir}/exp004a_lr_probe.json", "w"), indent=1)
