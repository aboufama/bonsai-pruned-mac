# Experiment 017: the full-precision references with generated answers, on the same sets and the
# same harness the repaired Bonsai is measured with (experiment 013): the parent (Qwen3.5-9B) and
# UI-Venus-2-9B. One look at 1280 px, the standard prompt. Runs where their weights are (the Spark).
import gc
import json
import time

import torch

N = globals().get("N17", 200)
sets17 = {"ScreenSpot-v2 report set": lab.data("ssv2", mod=(8, 5)),
          "ScreenSpot-v2 fresh set": lab.data("ssv2", mod=(8, 3)),
          "Mac app windows (Screen2AX, reserved apps)": lab.data("mac:screen2ax_task:test", n=N),
          "our benchmark (dev)": lab.data("gen:benchdata/pointing/dev_20261114", n=N)}
out17 = {}
for which, name in (("V", "UI-Venus-2-9B"), ("P", "parent, Qwen3.5-9B")):
    m = lab.load(which)
    for sname, data in sets17.items():
        t = time.time()
        r = lab.score(m, data, tag=f"017:{which}:{sname}")
        out17.setdefault(sname, {})[name] = {k: v for k, v in r.items() if k != "answers"}
        print("%-22s %-44s %5.1f%% of %d on target   median distance %.0f   [%.0f s]" % (
            name, sname, 100 * r["acc"], len(data), r["median_dist"] or -1, time.time() - t), flush=True)
        json.dump(out17, open(f"{lab.dir}/exp017_baselines.json", "w"), indent=1)
    del lab.models[which], m
    gc.collect(); torch.cuda.empty_cache()
