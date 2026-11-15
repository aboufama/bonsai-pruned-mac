# Experiment 014: one set of weights that points and calls tools.
#
# The assistant we want is one model that reads the screen once and then decides: answer, call a
# tool, or point. So pointing is trained here as a tool call (`point(x, y)`) in the model's own
# chat format, together with ordinary tool calls from our seeded tool benchmark's train split and
# the plain grounding format the earlier experiments used. Only multipliers move (layers 4..31
# and the output head), with the gentle recipe.
#   point_call  screenshot + request -> point(x, y); digits scored by landing in the box
#   tool_call   text request + tools -> the expected calls, token by token
#   no_call     a required value is missing, or no tool applies -> must not start a tool call
#   point       the plain "[x, y]" grounding format
# Measured before and after, on data never trained on: plain pointing (select and report sets),
# pointing as a tool call on the select screens, the tool benchmark's dev split, and the canary.
# Settings: UPDATES14, LR14, ACC14, TAG14, HEAD14 (False on a model whose output head is not ternary, the 4B).
import collections
import json
import random
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab import chat
importlib.reload(chat)
from weightlab.tune import TaskTuner

UPDATES = globals().get("UPDATES14", 600)
LR = globals().get("LR14", 2e-4)
ACC = globals().get("ACC14", 2)
TAG = globals().get("TAG14", f"joint_u{UPDATES}")
HEAD = globals().get("HEAD14", True)
LAYERS = list(range(4, 32))
rng = random.Random(14)

# ---- training samples
if "mix" not in globals():
    raise RuntimeError("run experiment 010 first: it builds the pointing mix")
point_items = list(mix)
rng.shuffle(point_items)
tool_cases = [json.loads(l) for l in open(f"{lab.root}/benchdata/toolcall/train_s11/cases.jsonl")]
tools = [s for s in (chat.tool_case(c) for c in tool_cases) if s]
train14 = ([chat.point_call(it) for it in point_items[:2600]] + point_items[2600:4000]
           + [s for s in tools if s["kind"] == "tool_call"][:3000] + [s for s in tools if s["kind"] == "no_call"][:1000])
rng.shuffle(train14)
print("training samples:", dict(collections.Counter(s.get("kind", "point") for s in train14)))

# ---- measurements
dev_cases = [json.loads(l) for l in open(f"{lab.root}/bench/toolcall/runs/dev_20261114/cases.jsonl")]
tool_dev = [s for s in (chat.tool_case(c) for c in dev_cases) if s]
point_dev = [chat.point_call(it) for it in fS.samples]
rows = []


def measure(label):
    t = time.time()
    a, b = fS.evaluate(4, tag=f"014:{TAG}:{label}:select"), fR.evaluate(4, tag=f"014:{TAG}:{label}:report")
    fS.discard(); fR.discard()
    pc = chat.score(lab, lab.B, point_dev, tag=f"014:{TAG}:{label}:point_call")
    tc = chat.score(lab, lab.B, tool_dev, tag=f"014:{TAG}:{label}:tools")
    can = lab.canary(lab.B, tag=f"014:{TAG}:{label}")
    rows.append({"label": label, "select": a, "report": b, "point_call": pc, "tools": tc, "canary": can})
    print("%s  [%.0f s]" % (label, time.time() - t))
    print("   plain pointing          select %.3f   report %.3f" % (a["p_hit"], b["p_hit"]))
    print("   pointing as a tool call select %.3f   (hundreds %.3f tens %.3f; call written correctly %.0f%%)" % (
        pc["p_hit"], pc["p_ok_hundreds"], pc["p_ok_tens"], 100 * pc["format"]))
    print("   tool benchmark (dev)    every token right on %.1f%% of %d calls   holds back on %.1f%% of %d no-call cases" % (
        100 * tc["tf_exact"], tc["n_tool"], 100 * tc["holds_back"], tc["n_no_call"]))
    print("   canary                  %s" % can["all"], flush=True)
    return a["p_hit"], pc["p_hit"], tc["tf_exact"]


before = measure("before")
T14 = TaskTuner(lab, LAYERS, scales=True, head=HEAD)
snap14 = T14.snapshot()
r = T14.train(train14, UPDATES, lr_scales=LR, warmup=40, accumulate=ACC, ema=0.98, seed=14, report_every=50)
print("training loss %.3f -> %.3f" % (r["loss_start"], r["loss_end"]))
after = measure("after")
torch.save(T14.snapshot(), f"{lab.dir}/ckpt/tune_{TAG}.pt")
json.dump(rows, open(f"{lab.dir}/exp014_{TAG}.json", "w"), indent=1)
print("kept in memory and saved as", f"tune_{TAG}.pt", "(T14.restore(snap14) puts the previous multipliers back)")
