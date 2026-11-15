# Experiment 018: the pointing head trained together with the model's own multipliers
# (weightlab/head.py, JointHeadTuner). Experiment 016 trained heads on a frozen model; the best
# one read layer 20 and reached 42% after 1,000 steps. A frozen model was never asked to make
# location easy to read from its state, so here the multipliers of layers 4..19 learn with the
# head, while the written-answer loss keeps ordinary pointing intact.
# Settings: STEPS18, ROUND18, KIND18 ("pointer" or "cross"), LAYER18, KEYS18, LRS18, DIGITS18, TAG18.
import json
import time

import torch
import weightlab.head as headmod
from weightlab.distill import BlockDistiller

STEPS = globals().get("STEPS18", 4000)
ROUND = globals().get("ROUND18", 500)
KIND = globals().get("KIND18", "pointer")
LAYER = globals().get("LAYER18", 20)
KEYS = globals().get("KEYS18", None)
LRS = globals().get("LRS18", 2e-4)
DIGITS = globals().get("DIGITS18", 1.0)
TAG = globals().get("TAG18", f"{KIND}_L{LAYER}_s{STEPS}")
sets = {"select": fS.samples, "report": fR.samples, "fresh ScreenSpot-v2": lab.data("ssv2", mod=(8, 3)),
        "Mac app windows": lab.data("mac:screen2ax_task:test", n=120)}
out = {"tag": TAG, "kind": KIND, "layer": LAYER, "lr_scales": LRS, "digits": DIGITS, "rows": []}


def digits_score(label):
    a, b = fS.evaluate(4), fR.evaluate(4)
    fS.discard(); fR.discard()
    return a["p_hit"], b["p_hit"]


print(f"{TAG}: {KIND} head at layer {LAYER}, multipliers of layers 4..{LAYER - 1} trained with it (lr {LRS:g}), written-answer loss x{DIGITS:g}")
d0 = digits_score("before")
print("written answers before: select %.3f   report %.3f" % d0, flush=True)
LO = globals().get("LO18", 4)                        # first layer whose multipliers train with the head
GUARDS = globals().get("GUARDS18", False)            # also watch the canary and the tool benchmark every round
J = headmod.JointHeadTuner(lab, range(LO, LAYER), kind=KIND, layer=LAYER, key_layers=KEYS, head=globals().pop("HEAD18", None))
if GUARDS:
    import json as _json
    from weightlab import chat
    _dev = [_json.loads(l) for l in open(f"{lab.root}/bench/toolcall/runs/dev_20261114/cases.jsonl")]
    _tool_dev = [x for x in (chat.tool_case(c) for c in _dev) if x]
t0 = time.time()
best = (-1, 0)
for r0 in range(0, STEPS, ROUND):
    res = J.train(globals().get("PACKS18") or packs, min(ROUND, STEPS - r0), total=STEPS, lr_scales=LRS, lr_head=globals().get("LRH18", 1e-3), digits=DIGITS, seed=18)
    h = J.score(sets["select"])
    hr = J.score(sets["report"])
    print("step %5d: head on REPORT on target %5.1f%%   within 20 px %5.1f%%   (select within 20 px %5.1f%%)" % (
        J.steps, 100 * hr["hit"], 100 * hr.get("within20", 0), 100 * h.get("within20", 0)), flush=True)
    d = digits_score(f"step {J.steps}")
    out["rows"].append({"steps": J.steps, "head_select": h, "head_report": hr, "digits_select": d[0], "digits_report": d[1], "train": res})
    mark = ""
    if h["hit"] > best[0]:
        best, mark = (h["hit"], J.steps), "  <- best head so far"
        torch.save({"spec": J.spec, "steps": J.steps, "head": J.head.state_dict(),
                    "gains": [g.detach().cpu() for g in J.gains]}, f"{lab.dir}/ckpt/joint018_{TAG}_best.pt")
    print("step %5d: head on target %5.1f%% (median distance %.0f, click right %.0f%%)   written answers: select %.3f report %.3f   [%.0f min]%s" % (
        J.steps, 100 * h["hit"], h["median_dist"], 100 * h["click_acc"], d[0], d[1], (time.time() - t0) / 60, mark), flush=True)
    torch.save({"spec": J.spec, "steps": J.steps, "head": J.head.state_dict(), "gains": [g.detach().cpu() for g in J.gains]},
               f"{lab.dir}/ckpt/joint018_{TAG}_s{J.steps}.pt")        # a copy at every scored step
    if GUARDS:
        _can = lab.canary(lab.B, tag=f"018:{TAG}:{J.steps}")
        _tc = chat.score(lab, lab.B, _tool_dev, tag=f"018:{TAG}:{J.steps}:tools")
        out["rows"][-1]["guards"] = {"canary": _can["all"], "tools": _tc["tf_exact"], "format": _tc.get("format"), "holds_back": _tc["holds_back"]}
        print("   guards: canary %s   tool benchmark every token right %.1f%%   holds back %.1f%%" % (
            _can["all"], 100 * _tc["tf_exact"], 100 * _tc["holds_back"]), flush=True)
        if _can["all"]["tf_exact"] < 0.88:
            print("canary under 0.88: stopping", flush=True)
            json.dump(out, open(f"{lab.dir}/exp018_{TAG}.json", "w"), indent=1)
            break
    json.dump(out, open(f"{lab.dir}/exp018_{TAG}.json", "w"), indent=1)
J.close()
out["final"] = {name: J.score(data) for name, data in sets.items()}
for name, v in out["final"].items():
    print("  %-22s head on target %5.1f%%   median distance %5.1f   click decision right %5.1f%%" % (name, 100 * v["hit"], v["median_dist"], 100 * v["click_acc"]), flush=True)
d = digits_score("after")
print("written answers after: select %.3f   report %.3f   (before: %.3f, %.3f)" % (d + d0))
torch.save({"spec": J.spec, "steps": J.steps, "head": J.head.state_dict()}, f"{lab.dir}/ckpt/joint018_{TAG}_head.pt")
BlockDistiller(lab, 4, 19, teacher=None).save(range(LO, LAYER), f"{lab.dir}/ckpt/joint018_{TAG}_L{LO}-{LAYER - 1}.safetensors")
out["canary"] = lab.canary(lab.B, tag=f"018:{TAG}")
print("canary:", out["canary"]["all"])
json.dump(out, open(f"{lab.dir}/exp018_{TAG}.json", "w"), indent=1)
