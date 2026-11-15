# Lane 4 (or any free 9B lane): do the Fable-written cases help? (15 Nov 00:35)
# data/mac/fable_teacher: natural requests (direct, by intent, first step of a task) for elements with
# exact boxes on 160 real Mac screenshots; 16 screenshots (330 cases) are the test split.
# Two runs of lane 3's gentle recipe from the v3-gentle patch (block 4..19, multipliers and small
# parts, no codes, lr 1e-4 / 2e-5, warm-up 100), 1,500 steps each, 896-weighted long sides:
#   fable_without   the training mix as it is
#   fable_with      the mix plus every fable_teacher train case
# Both leave out the 85 bad source cases (bad_source_cases.json). Scored before training (= v3-gentle)
# and every 500 steps: select and report at 1280 and 896, Mac app windows at 1280 and 896, and the
# fable test split by kind (direct, intent, next), teacher-forced. Generated answers on the fable test
# split are added for the three states, and for UI-Venus if it is on the pod (teacher-forced p_hit and
# generated accuracy are different measures; only the generated lines compare with UI-Venus).
#
# How much the fable cases are seen: 1,500 steps cannot show 4,200 cases three times each next to the
# usual mix (a step is one screenshot with up to five questions). Here the fable packs get half of
# the steps (EXTRA_SHARE10 = 0.5), always five questions per screenshot, which is about 0.9 views per
# case; the exact figure is printed ("each extra case is seen about ...").
# Not used: cases_absent.jsonl. The written-answer format the block trainer trains ("[x, y]") has no
# answer for a target that is not on the screen; only the pointing heads train on absent targets.
# Needs on the pod: data/mac/fable_teacher/{cases.jsonl, bad_source_cases.json} (its images are the
# os_atlas_mac and screen2ax_tree ones already there). Runs in a fresh or a used 9B session.
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
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10 = 1500, 500, 1e-4, 2e-5, False, 100, 60
SIZES10 = (896, 896, 896, 896, 640, 768, 1024, 1280)
SIZE_SCORES10, MAC_SIZES10 = (1280, 896), (896,)
KEEP10, TEACHER10, TEACH10 = None, None, 0.0
DROP10 = f"{_fb}/bad_source_cases.json"
EXTRA_SCORES10 = {"fable test": "mac:fable_teacher:test"}
_gen, _res = {}, {}

_lay()
_gen["v3-gentle"] = _generated(lab.B, "v3-gentle")
TAG10, EXTRA10, EXTRA_SHARE10 = "fable_without", None, None
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
_res["without"] = out
_gen["without"] = _generated(lab.B, "without")

_lay()
TAG10, EXTRA10, EXTRA_SHARE10 = "fable_with", [("mac:fable_teacher:train", None, None, 3)], 0.5
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
_res["with"] = out
_gen["with"] = _generated(lab.B, "with")
EXTRA10 = EXTRA_SHARE10 = DROP10 = EXTRA_SCORES10 = None      # variables persist in the session

if os.path.exists(f"{lab.paths['V']}/config.json"):
    _V = lab.load("V")
    _gen["UI-Venus-2-9B"] = _generated(_V, "UI-Venus-2-9B")
    del lab.models["V"], _V
    gc.collect(); torch.cuda.empty_cache()
else:
    print("UI-Venus-2-9B is not on this machine: no UI-Venus line")


def _row(d, report):
    s = d.get("sizes") or {}
    x = (d.get("extra") or {}).get("fable test") or {}
    return [d["select"]["p_hit"], report["p_hit"], s.get(896, {}).get("select", {}).get("p_hit"), s.get(896, {}).get("report", {}).get("p_hit"),
            d["mac"]["p_hit"], s.get(896, {}).get("mac", {}).get("p_hit")] + [x.get(k, {}).get("p_hit") for k in _test]


_w, _f = _res["without"], _res["with"]
_rows = {"v3-gentle (before)": _row(_w["before"], _w["rows"][0]["report"]),
         "without, best step %d" % _w["best_step"]: _row(_w["best"], _w["best"]["report"]),
         "with, best step %d" % _f["best_step"]: _row(_f["best"], _f["best"]["report"])}
_cols = ["select", "report", "select 896", "report 896", "Mac win", "Mac win 896"] + ["fable %s" % k for k in _test]
print("\nFABLE COMPARISON, teacher-forced p_hit (1,500 steps each; select and Mac windows measured with the block open, report closed)")
print("%-24s" % "" + "".join("%13s" % c for c in _cols))
for _name, _vals in _rows.items():
    print("%-24s" % _name + "".join("%13s" % ("-" if v is None else "%.3f" % v) for v in _vals))
print("generated answers on the fable test split, on target:")
for _name, _g in _gen.items():
    print("%-24s" % _name + "".join("%13s" % ("%s %.1f%%" % (k, 100 * v["acc"])) for k, v in _g.items() if k != "_all") + "%13s" % ("all %.1f%%" % (100 * _g["_all"]["acc"])))
json.dump({"teacher_forced": {k: dict(zip(_cols, v)) for k, v in _rows.items()}, "generated": _gen,
           "extra_seen": {"with": _f.get("extra"), "extra_packs": _f.get("extra_packs")}},
          open(f"{lab.dir}/exp010_fable_compare.json", "w"), indent=1)
