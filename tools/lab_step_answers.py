"""The lab's answers of a planner (orchestrator) patch, for checking a GGUF of it in another runtime:
N report cases as written "[x, y]" answers (as tools/lab_answers.py) and M reserved next_step cases as
generated tool calls, with everything needed to ask the same question elsewhere (system text, user text,
the tool schema, the shrunk PNG).   BONSAI_SIZE=9B python3 tools/lab_step_answers.py <patch> <out dir> [N=20] [M=10]"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
from weightlab import actions, chat, state
from weightlab.core import Lab

patch, out_dir = sys.argv[1:3]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
m = int(sys.argv[4]) if len(sys.argv) > 4 else 10
os.makedirs(f"{out_dir}/images", exist_ok=True)
lab = Lab(ROOT)
lab.B
state.apply_patch(lab, patch)
data = lab.data("ssv2", mod=(8, 5))[:n]
answers = lab.score(lab.B, data, tag="lab_step_answers")["answers"]
with open(f"{out_dir}/answers.jsonl", "w") as f:
    for it, text in zip(data, answers):
        lab.image(it).save(f"{out_dir}/images/{it['id']}.png")
        f.write(json.dumps({"id": it["id"], "image": it["id"] + ".png", "instruction": it["instruction"],
                            "box1000": [round(v, 2) for v in it["box1000"]], "answer": text}) + "\n")
adir = f"{ROOT}/data/mac/agentnet"
want, cases = [], {}
if os.path.exists(f"{adir}/step_pick.json"):             # screenshot steps, when their cases are on this machine
    want = json.load(open(f"{adir}/step_pick.json"))["reserved"]
    for line in open(f"{adir}/cases_steps.jsonl"):
        c = json.loads(line)
        if c["id"] in want and os.path.exists(os.path.normpath(os.path.join(adir, c["image"]))):
            cases[c["id"]] = c
actions.install()
with open(f"{out_dir}/steps.jsonl", "w") as f:
    pdir = f"{ROOT}/data/mac/planner_sim_s1"             # planner turns in format v1 (text only), the simulator's held-out ones
    if os.path.exists(pdir):
        from weightlab import planner
        import random
        turns = planner.load(pdir, "dev")
        random.Random(5).shuffle(turns)
        for s in turns[:m]:
            text, _ = chat.generate(lab, lab.B, s, max_new_tokens=96)
            f.write(json.dumps({"id": s["id"], "image": None, "system": s["messages"][0]["content"], "request": s["messages"][1]["content"],
                                "tools": s["tools"], "expected": s["turn"]["answer"], "answer": text}) + "\n")
    for i, cid in enumerate([c for c in want if c in cases][:m]):
        s = actions.step_case(cases[cid], base=adir)
        text, _ = chat.generate(lab, lab.B, s, max_new_tokens=96)
        name = f"step_{i:02d}.png"
        lab.image(s["item"]).save(f"{out_dir}/images/{name}")
        f.write(json.dumps({"id": cid, "image": name, "system": s["system"], "request": s["request"], "tools": s["tools"],
                            "expected": cases[cid]["step"], "answer": text}) + "\n")
print("LAB STEP ANSWERS: %d pointing cases and %d step cases in %s" % (len(data), m, out_dir), flush=True)
