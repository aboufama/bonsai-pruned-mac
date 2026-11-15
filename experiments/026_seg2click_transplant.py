# Experiment 026 (15 Nov 02:30): transplant Seg2Click's change into Bonsai 4B.
# jcwang0602/Seg2Click-Qwen3.5-4B is Qwen/Qwen3.5-4B with a rank-16 LoRA on every linear layer, merged. So
# for every language-model matrix D = W(Seg2Click) - W(parent) should be rank 16. Here D is recovered per
# matrix by SVD (the share of |D|^2 that rank 16 holds is reported) and attached to Bonsai as full-precision
# side paths y += B (A x) beside the ternary matrices (weightlab/sidepath.py); nothing ternary changes.
# Variants scored (teacher-forced select / report by full passes, generated hits on report at 1280 px,
# canary): the start model; + side paths; + side paths and Seg2Click's vision tower in place of Bonsai's;
# vision tower alone. Then 400 gentle multiplier updates under the best variant.
# Only weight files are read. Seg2Click's own output goes through a mask head that needs its authors' code;
# that is not run here, so "Seg2Click as it is" is scored only as its backbone writing answers in our prompt.
# INTEGRITY: Seg2Click may have seen ScreenSpot screens in training; every ScreenSpot-v2 number of a model
# carrying its change is suspect. Clean measures: the Fable test split and the task environment.
# Settings: TAG26, UPDATES26 (400), RANK26 (16).
import glob
import json
import os
import time

import torch
from safetensors import safe_open
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab.sidepath import SidePaths
from weightlab.tune import TaskTuner

TAG, UPDATES, RANK = globals().get("TAG26", "seg2click"), globals().get("UPDATES26", 400), globals().get("RANK26", 16)
SEG, PAR = f"{lab.root}/hf/Seg2Click-Qwen3.5-{lab.size}", lab.paths["P"]


class Files:
    """Tensor lookup over every safetensors file of a checkpoint folder."""

    def __init__(self, d):
        self.h, self.where = {}, {}
        for f in sorted(glob.glob(f"{d}/*.safetensors")):
            self.h[f] = safe_open(f, framework="pt")
            for k in self.h[f].keys():
                self.where.setdefault(k, f)

    def get(self, k):
        return self.h[self.where[k]].get_tensor(k)


S, Pm = Files(SEG), Files(PAR)
sel, rep = lab.data("ssv2", mod=(8, 1)), lab.data("ssv2", mod=(8, 5))
fab = [it for it in lab.data("mac:fable_teacher:test", n=20000) if os.path.exists(it["path"])] if os.path.exists(f"{lab.root}/data/mac/fable_teacher/cases.jsonl") else []
fab = list({it["id"]: it for it in fab}.values())
out = {"tag": TAG, "rows": []}


def row(label, generated=True):
    t = time.time()
    r = {"label": label, "select": lab.digits(lab.B, sel, tag=f"026:{label}:select")["p_hit"], "report": lab.digits(lab.B, rep, tag=f"026:{label}:report")["p_hit"]}
    if fab:
        r["fable_test"] = lab.digits(lab.B, fab, tag=f"026:{label}:fable")["p_hit"]
    if generated:
        g = lab.score(lab.B, rep, tag=f"026:{label}:generated")
        r["generated"], r["canary"] = g["acc"], lab.canary(lab.B, tag=f"026:{label}")["all"]
    out["rows"].append(r)
    print("026  %-58s select %.3f  report %.3f%s%s   [%.1f min]" % (
        label, r["select"], r["report"], ("  Fable test %.3f" % r["fable_test"]) if fab else "",
        ("  generated %.1f%% of %d  canary %s" % (100 * r["generated"], len(rep), r["canary"])) if generated else "", (time.time() - t) / 60), flush=True)
    json.dump(out, open(f"{lab.dir}/exp026_{TAG}.json", "w"), indent=1)
    return r


# ---- 1. the change, per ternary matrix, at rank RANK
side = SidePaths(lab, range(0, len(list(lab.B.model.language_model.layers))), rank=RANK)
kept, total, missing = 0.0, 0.0, []
with torch.no_grad():
    for name in side.A:
        key = name + ".weight"
        if key not in S.where or key not in Pm.where:
            missing.append(name); continue
        dev = side.A[name].device
        d = S.get(key).to(dev).float() - Pm.get(key).to(dev).float()
        U, sv, Vh = torch.linalg.svd(d, full_matrices=False)
        kept += float((sv[:RANK] ** 2).sum()); total += float((sv ** 2).sum())
        root = sv[:RANK].sqrt()
        side.B[name].copy_(U[:, :RANK] * root); side.A[name].copy_(root[:, None] * Vh[:RANK])
        del d, U, sv, Vh
print("026  Seg2Click minus parent over %d ternary matrices: rank %d holds %.2f%% of the change's energy; no tensor for %d (%s)" % (
    len(side.A) - len(missing), RANK, 100 * kept / max(total, 1e-12), len(missing), ", ".join(missing[:3])), flush=True)
out["rank_energy"] = kept / max(total, 1e-12)
side.save(f"{lab.dir}/ckpt/seg2click_side_r{RANK}_{lab.size}.safetensors")
saved = {n: side.B[n].detach().clone() for n in side.B}


def side_on(on):
    with torch.no_grad():
        for n in side.B:
            side.B[n].copy_(saved[n]) if on else side.B[n].zero_()


# ---- 2. Seg2Click's vision tower (same shapes), swappable
vis = {k: p for k, p in lab.B.named_parameters() if ".visual." in k or k.startswith("visual.")}
own = {k: p.detach().clone() for k, p in vis.items()}
have = [k for k in vis if k in S.where and tuple(S.get(k).shape) == tuple(vis[k].shape)]
print("026  vision tower: %d of %d tensors found in the Seg2Click checkpoint with the same shape" % (len(have), len(vis)), flush=True)


def vision(seg):
    with torch.no_grad():
        for k in have:
            vis[k].copy_((S.get(k) if seg else own[k]).to(vis[k].device, vis[k].dtype))


# ---- 3. the variants
side_on(False); vision(False)
r0 = row("start model (%s)" % ", ".join(lab.stack))
side_on(True)
r1 = row("+ Seg2Click change as rank-%d side paths" % RANK)
vision(bool(have))
r2 = row("+ side paths and Seg2Click's vision tower") if have else None
side_on(False)
r3 = row("Seg2Click's vision tower alone") if have else None
cands = [(r["generated"], i) for i, r in enumerate((r0, r1, r2, r3)) if r]
best = max(cands)[1]
side_on(best in (1, 2)); vision(best in (2, 3) and bool(have))
print("026  best variant by generated hits: %s" % (r0, r1, r2, r3)[best]["label"], flush=True)

# ---- 4. gentle multiplier updates under the best variant
if UPDATES and best != 0:
    T26 = TaskTuner(lab, list(range(4, len(list(lab.B.model.language_model.layers)))), scales=True, head=False)
    res = T26.train(mix, UPDATES, lr_scales=1e-4, warmup=40, accumulate=2, ema=0.98, seed=26, report_every=100)
    print("026  %d gentle multiplier updates: training loss %.3f -> %.3f" % (UPDATES, res["loss_start"], res["loss_end"]), flush=True)
    row("best variant + %d gentle multiplier updates" % UPDATES)
    torch.save(T26.snapshot(), f"{lab.dir}/ckpt/tune_{TAG}_{lab.size}.pt")
print("026 done; side paths in", f"{lab.dir}/ckpt/seg2click_side_r{RANK}_{lab.size}.safetensors", flush=True)
