# Experiment 008b: the parent (Qwen3.5-9B) and UI-Venus-2-9B on the same two 159-screen sets,
# with the same teacher-forced score, so the repaired Bonsai has a measured target.
import gc
import json
import time
import torch

out = {}
for which, name in (("P", "parent (Qwen3.5-9B)"), ("V", "UI-Venus-2-9B")):
    t = time.time()
    m = lab.load(which)
    r = {}
    for label, data in (("select", sel), ("report", rep)):
        r[label] = lab.digits(m, data, tag=f"008b:{which}:{label}")
    out[which] = r
    print("%-22s select %.3f (hundreds %.3f tens %.3f)  report %.3f (hundreds %.3f tens %.3f)   [%.0fs]" % (
        name, r["select"]["p_hit"], r["select"]["p_ok_hundreds"], r["select"]["p_ok_tens"],
        r["report"]["p_hit"], r["report"]["p_ok_hundreds"], r["report"]["p_ok_tens"], time.time() - t), flush=True)
    del lab.models[which], m
    gc.collect(); torch.cuda.empty_cache()
json.dump(out, open(f"{lab.dir}/exp008b_ceilings.json", "w"), indent=1)
print("GPU %.1f GB" % (torch.cuda.memory_allocated() / 1e9))
