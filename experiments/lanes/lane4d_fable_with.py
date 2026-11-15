# Lane 4: do the Fable-written cases help? Single "with" arm (15 Nov 00:45).
# Lane 8b's exact recipe (v3-gentle start, block 4..19, multipliers and small parts, no codes, lr 1e-4 /
# 2e-5, warm-up 100, 896-weighted long sides) plus every data/mac/fable_teacher train case, with half of
# the steps on them; 3,000 steps, scored at 1,000 / 2,000 / 3,000 on lane 8b's sets (select and report at
# 1280, 1024, 896, 768, 640; Mac app windows at 1280 and 896) plus mac:fable_teacher:test by kind
# (direct, intent, next). Lane 8b is the control: this job runs right after it in the same session and
# first scores lane 8b's final checkpoint on the fable test split (generated answers), then v3-gentle,
# then trains. The 85 flagged source cases are left out; the absent requests are not used.
# Teacher-forced p_hit and generated accuracy are different measures; UI-Venus has only the latter.
import gc
import json
import os

import torch

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-gentle.patch.safetensors"     # the 9B base
exec(open(f"{lab.root}/experiments/_prelude.py").read())
_fb = f"{lab.root}/data/mac/fable_teacher"
if not os.path.exists(f"{_fb}/cases.jsonl") or not os.path.exists(f"{_fb}/bad_source_cases.json"):
    raise RuntimeError("data/mac/fable_teacher (cases.jsonl, bad_source_cases.json) is not on this machine")

# the test split by kind, for the generated answers
_test, _seen = {}, set()
for _it in lab.data("mac:fable_teacher:test", n=20000):
    if _it["id"] not in _seen and os.path.exists(_it["path"]):
        _seen.add(_it["id"])
        _test.setdefault(_it.get("kind") or "all", []).append(_it)
_test = dict(sorted(_test.items()))
print("fable test split:", {k: len(v) for k, v in _test.items()}, "  three cases:", flush=True)
for _it in [v[0] for v in _test.values()][:3]:
    print("   %-8s %-60s box %s  image %s" % (_it.get("kind"), _it["instruction"][:60], [round(b) for b in _it["bbox"]], os.path.basename(_it["path"])))


def _lay():
    """Put the session's model at the v3-gentle patch and check it."""
    for n in ("J", "E", "T14"):
        if getattr(globals().get(n), "training", False) or getattr(globals().get(n), "open", False) is True:
            raise RuntimeError(f"{n} is still open in this session; restart the lab session and queue this job again")
    if lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
        print("patch applied over the session's state:", state.apply_patch(lab, PATCH), os.path.basename(PATCH))
        lab.stack[:] = [f"patch:{os.path.basename(PATCH)}"]
    a, b = fS.evaluate(4), fR.evaluate(4)
    fS.discard(); fR.discard()
    print("start state (v3-gentle): select %.3f   report %.3f   (verified: 0.837 / 0.851)" % (a["p_hit"], b["p_hit"]), flush=True)
    if abs(a["p_hit"] - 0.837) > 0.01 or abs(b["p_hit"] - 0.851) > 0.01:
        raise RuntimeError("the model is not at the v3-gentle state; restart the lab session and queue this job again")


def _generated(model, label):
    """Generated answers (one look at 1280 px) on the fable test split, per kind."""
    r = {}
    for k, cases in _test.items():
        g = lab.score(model, cases, tag=f"fable_compare:{label}:{k}")
        r[k] = {"acc": g["acc"], "median_dist": g["median_dist"], "n": len(cases)}
    n = sum(v["n"] for v in r.values())
    r["_all"] = {"acc": sum(v["acc"] * v["n"] for v in r.values()) / n, "n": n}
    print("generated answers, fable test, %-14s " % label + "   ".join("%s %.1f%% of %d" % (k, 100 * v["acc"], v["n"]) for k, v in r.items() if k != "_all")
          + "   all %.1f%%" % (100 * r["_all"]["acc"]), flush=True)
    return r


LO10, HI10 = 4, 19
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10 = 3000, 1000, 1e-4, 2e-5, False, 100, 60
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 1024, 896, 768, 640), (896,)
KEEP10, TEACHER10, TEACH10 = None, None, 0.0
DROP10 = f"{_fb}/bad_source_cases.json"
EXTRA_SCORES10 = {"fable test": "mac:fable_teacher:test"}
_gen = {}
if lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    print("session state before this job:", lab.stack, flush=True)
    _gen["lane 8b final"] = _generated(lab.B, "lane 8b final")
_lay()
_gen["v3-gentle"] = _generated(lab.B, "v3-gentle")
TAG10, EXTRA10, EXTRA_SHARE10 = "fable_with", [("mac:fable_teacher:train", None, None, 3)], 0.5
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
_gen["with fable"] = _generated(lab.B, "with fable")
EXTRA10 = EXTRA_SHARE10 = DROP10 = EXTRA_SCORES10 = None      # variables persist in the session
if os.path.exists(f"{lab.paths['V']}/config.json"):
    _V = lab.load("V")
    _gen["UI-Venus-2-9B"] = _generated(_V, "UI-Venus-2-9B")
    del lab.models["V"], _V
    gc.collect(); torch.cuda.empty_cache()
else:
    print("UI-Venus-2-9B is not on this machine: no UI-Venus line")
print("generated answers on the fable test split, on target:")
for _name, _g in _gen.items():
    print("%-16s" % _name + "".join("%16s" % ("%s %.1f%%" % (k, 100 * v["acc"])) for k, v in _g.items() if k != "_all") + "%14s" % ("all %.1f%%" % (100 * _g["_all"]["acc"])))
json.dump({"generated": _gen}, open(f"{lab.dir}/exp010_fable_with_generated.json", "w"), indent=1)
