# Experiment 022: UI-Venus as a judge of the training labels and as a teacher on answers.
#
# UI-Venus-2-9B puts 96% of its answers on target where the repaired Bonsai puts 73%, and a hand check
# found that about a third of the real Mac labels do not match their request. Here UI-Venus answers
# every pointing case of the training mix once (greedy, one look at 1280 px, the standard prompt, the
# same selection of cases experiment 010 trains on). Kept per case:
#   - its point, and whether that point is inside the labelled box. Mac cases where it is not are
#     suspect labels; experiment 010 can leave them out (KEEP10). The generator's cases have exact
#     boxes, so their share outside the box is UI-Venus's own miss rate.
#   - for each digit it wrote (up to three per coordinate), its full probability over the ten digit
#     tokens at that position: 6 x 10 numbers, nothing cut off. They are read from the scores of the
#     greedy generation itself, i.e. teacher-forced on its own answer, at no extra forward pass.
#     Experiment 010 can train toward them (TEACHER10, TEACH10).
# The digits are found by their token ids in the generated answer (tune.DIGIT0), not by position, so
# spacing habits do not matter. A case is unusable as a teacher if the answer does not hold two
# numbers of one to three digits; it is still judged in or out of the box when two numbers parse.
# Output: lab/venus_teacher.json  {"<mix name>|<case id>": {"in": bool, "answer": "[x, y]",
#                                  "x": "448", "y": "381"}}   (x, y null when unusable)
#         lab/venus_teacher.npz   keys (the same strings), p (cases x 6 x 10, float16; rows 0..2 the
#                                  digits of x in written order, 3..5 those of y; unused rows zero)
# Resumable: both files are rewritten every 300 cases and done cases are skipped on a restart.
# Settings: LIMIT22 (cases per folder, for a trial), FOLDERS22 (substrings of mix names to run),
# OUT22 (path of the JSON; the .npz sits beside it), MIX22 (a mix list; default the one of 010).
import gc
import json
import os
import re
import time

import numpy as np
import torch
from weightlab import mixes
from weightlab.tune import DIGIT0

LIMIT = globals().pop("LIMIT22", None)
FOLDERS = globals().pop("FOLDERS22", None)
OUT = globals().get("OUT22", f"{lab.dir}/venus_teacher.json")
OUT_P = OUT[:-5] + ".npz"
MIX22 = globals().get("MIX22") or globals().get("MIX10") or mixes.DEFAULT_MIX

# ---- the cases, folder by folder, selected exactly as experiment 010 and mixes.build select them
folders = {}
for name, n, cap in MIX22:
    base = name.split(":")[1] if name.startswith("gen:") else f"data/mac/{name.split(':')[1]}"
    if not os.path.exists(f"{lab.root}/{base}/cases.jsonl"):
        print("not on this machine, skipped:", name)
        continue
    if FOLDERS and not any(f in name for f in FOLDERS):
        continue
    items = lab.data(name, n=int(n * (3 if cap else 1.3)))
    if cap:
        per, kept = {}, []
        for it in items:
            per[it["group"]] = per.get(it["group"], 0) + 1
            if per[it["group"]] <= cap:
                kept.append(it)
        items = kept
    seen, uniq = set(), []
    for it in items:
        if it["id"] not in seen and mixes.usable(it["instruction"]):
            seen.add(it["id"]); uniq.append(it)
    folders[name] = uniq[:n][:LIMIT or None]

done = json.load(open(OUT)) if os.path.exists(OUT) else {}
probs22 = {}
if os.path.exists(OUT_P):
    _z = np.load(OUT_P, allow_pickle=False)
    probs22 = {k: p for k, p in zip(_z["keys"].tolist(), _z["p"])}
# done = judged, and its distributions are stored unless the answer was unusable
done = {k: v for k, v in done.items() if "x" in v and (v["x"] is None or k in probs22)}
todo = [(name, it) for name, items in folders.items() for it in items if f"{name}|{it['id']}" not in done]
print("UI-Venus as judge: %d cases in %d folders, %d already done, %d to do" % (
    sum(len(v) for v in folders.values()), len(folders), sum(len(v) for v in folders.values()) - len(todo), len(todo)), flush=True)


def save22():
    keys = [k for k in done if k in probs22]
    tmp = OUT_P[:-4] + ".tmp.npz"
    np.savez(tmp, keys=np.array(keys), p=np.stack([probs22[k] for k in keys]) if keys else np.zeros((0, 6, 10), np.float16))
    os.replace(tmp, OUT_P)
    tmp = OUT + ".tmp"
    json.dump(done, open(tmp, "w"))
    os.replace(tmp, OUT)


def digits22(ids, scores):
    """The first two numbers in a generated answer as digit strings, with the probability over the ten
    digit tokens at each of their digits. Returns (x, y, 6 x 10 float16) or None if the answer is not
    two numbers of one to three digits."""
    groups, cur = [], []
    for k, tok in enumerate(ids):
        if DIGIT0 <= tok < DIGIT0 + 10:
            cur.append(k)
        elif cur:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    if len(groups) < 2 or not all(1 <= len(g) <= 3 for g in groups[:2]):
        return None
    p = np.zeros((6, 10), np.float16)
    for axis, g in enumerate(groups[:2]):
        for d, k in enumerate(g):
            p[3 * axis + d] = torch.softmax(scores[k][0, DIGIT0:DIGIT0 + 10].float(), dim=-1).cpu().numpy()
    return "".join(str(ids[k] - DIGIT0) for k in groups[0]), "".join(str(ids[k] - DIGIT0) for k in groups[1]), p


if todo:
    V = lab.load("V")
    stop_ids = lab._stop_ids()
    t0, failed = time.time(), 0
    with torch.inference_mode():
        for i, (name, it) in enumerate(todo):
            try:
                inputs, n_prompt = lab._inputs(V, it)
                out = V.generate(**inputs, max_new_tokens=16, do_sample=False, eos_token_id=stop_ids,
                                 output_scores=True, return_dict_in_generate=True)
                new = out.sequences[0, n_prompt:].tolist()
                text = lab.processor.decode(new, skip_special_tokens=True).strip()
                got = digits22(new, out.scores)
            except torch.OutOfMemoryError:
                raise
            except Exception as e:                       # an unreadable screenshot must not end the run
                failed += 1
                text, got = f"(failed: {type(e).__name__})", None
                if failed > 50:
                    save22()
                    raise RuntimeError("more than 50 cases failed; stopping") from e
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
            b = it["box1000"]
            inside = len(nums) >= 2 and b[0] <= nums[0] <= b[2] and b[1] <= nums[1] <= b[3]
            key = f"{name}|{it['id']}"
            if got:
                probs22[key] = got[2]
            done[key] = {"in": bool(inside), "answer": text[:40], "x": got[0] if got else None, "y": got[1] if got else None}
            if (i + 1) % 300 == 0:
                save22()
            if (i + 1) % 500 == 0 or i + 1 == len(todo):
                rate = (i + 1) / (time.time() - t0)
                print("  %6d of %d   %.1f cases/s   about %.0f min left   (%d failed)" % (
                    i + 1, len(todo), rate, (len(todo) - i - 1) / rate / 60, failed), flush=True)
    save22()
    del V, lab.models["V"]
    gc.collect(); torch.cuda.empty_cache()
    print("UI-Venus released; GPU memory %.1f GB" % (torch.cuda.memory_allocated() / 1e9), flush=True)

venus22 = {}
print("UI-Venus's point inside the labelled box, per folder (teacher = inside and its digits stored):")
for name, items in folders.items():
    marks = [done[f"{name}|{it['id']}"]["in"] for it in items if f"{name}|{it['id']}" in done]
    kept = sum(marks)
    teach = sum(1 for it in items if done.get(f"{name}|{it['id']}", {}).get("in") and done[f"{name}|{it['id']}"].get("x"))
    venus22[name] = {"cases": len(marks), "kept": kept, "dropped": len(marks) - kept, "teacher": teach}
    note = "generator, exact boxes: UI-Venus's own miss rate" if name.startswith("gen:") else "would be dropped from the mix"
    print("  %-38s %5d cases   inside %5d (%5.1f%%)   outside %5d (%5.1f%%)  %s" % (
        name, len(marks), kept, 100 * kept / max(1, len(marks)), len(marks) - kept,
        100 * (len(marks) - kept) / max(1, len(marks)), note), "  teacher for %d" % teach, flush=True)
json.dump(venus22, open(f"{lab.dir}/exp022_venus_clean.json", "w"), indent=1)
