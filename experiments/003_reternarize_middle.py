# Experiment 003: an all-ternary middle block built directly from the parent, no training.
#
# Experiments 001-002 showed that Bonsai's first 4 layers hand a usable state to the parent's
# layers, and Bonsai's last 12 layers decode the parent's state correctly. So a ternary copy of
# the parent's middle layers could slot in between, IF ternary can approximate them well enough.
# Here the middle layers' ternary matrices are re-fitted to the parent's weights in closed form
# (optimal codes and multipliers per group of 128, in Bonsai's own rotated basis), with and
# without also taking the parent's small full-precision parts (which stay full precision in
# the file format anyway). Everything stays ternary: no size or speed change.
import json
import re

import torch
from weightlab.core import Tensors

d = lab.data("ssv2", n=32)
if "fB" not in globals():
    fB = lab.fast(d, "B")
P = Tensors(lab.paths["P"])
LM = "model.language_model."
SMALL = ("layernorm.weight", "norm.weight", "A_log", "dt_bias", "conv1d.weight", "in_proj_a.weight", "in_proj_b.weight")
results = []
torch.cuda.empty_cache()


def in_block(key, lo, hi):
    m = re.search(r"layers\.(\d+)\.", key)
    return bool(m) and lo <= int(m.group(1)) <= hi


def refit_edit(lo, hi, change, source=P, tag="P"):
    e = lab.edit(f"refit-{tag}-{lo}-{hi}-{change}")
    for name in lab.tern:
        if in_block(name, lo, hi):
            e.refit(name, source.get(name + ".weight"), change)
    return e


def report(label, r, stats=None):
    r = dict(r, label=label)
    results.append(r)
    extra = "" if stats is None else "  codes changed %.2fB" % (stats["codes_changed"] / 1e9)
    print("%-46s p_hit %.3f  miss_nll %.3f  hundreds %.3f  tens %.3f%s" % (
        label, r["p_hit"], r["miss_nll"], r["p_ok_hundreds"], r["p_ok_tens"], extra), flush=True)


b = fB.baseline
print("Bonsai as is                                   p_hit %.3f  miss_nll %.3f   (parent 0.707; parent's dense layers 4..19 in place: see exp 002)" % (b["p_hit"], b["miss_nll"]))

for lo, hi in ((8, 19), (4, 19)):
    small = lambda k, lo=lo, hi=hi: k.startswith(LM) and k.endswith(SMALL) and in_block(k, lo, hi)
    # the parent's small full-precision parts alone, Bonsai's ternary matrices untouched
    with lab.swap(small) as n:
        r = fB.evaluate(lo, tag=f"smallfp-P-{lo}-{hi}"); fB.discard()
    report(f"layers {lo}..{hi}: parent's small FP parts only", r)
    for change in ("scales", "codes"):
        e = refit_edit(lo, hi, change)
        stats = e.apply()
        r = fB.evaluate(lo, tag=e.name); fB.discard()
        report(f"layers {lo}..{hi}: ternary re-fit ({change})", r, stats)
        with lab.swap(small):
            r = fB.evaluate(lo, tag=e.name + "+smallfp"); fB.discard()
        report(f"layers {lo}..{hi}: ternary re-fit ({change}) + parent FP parts", r, stats)
        e.revert()
        torch.cuda.empty_cache()

check = fB.evaluate(0, tag="after-revert-check"); fB.discard()
print("after reverting everything: p_hit %.3f (must equal the first line)" % check["p_hit"])
json.dump(results, open(f"{lab.dir}/exp003_reternarize.json", "w"), indent=1)
