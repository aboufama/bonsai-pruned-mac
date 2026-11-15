# Experiment 007: generated answers (not teacher-forced) from the model in its CURRENT state on
# sets that training never touched:
#   - ScreenSpot-v2 "report" set (158 real screens; never used to choose between runs)
#   - our seeded pointing benchmark, dev split (generated screens; layouts, themes, wording and
#     icons differ from the train split)
#   - Screen2AX-Task, the reserved apps (real macOS app windows with exact boxes)
# Run it after loading whichever state should be measured. Settings: N7, STATE7 (a label).
import json
import time

N = globals().get("N7", 200)
LABEL = globals().get("STATE7", "current")
sets7 = {
    "ScreenSpot-v2 report set": lab.data("ssv2", mod=(8, 5)),
    "our benchmark (dev)": lab.data("gen:benchdata/pointing/dev_20261114", n=N),
    "Mac app windows (Screen2AX test)": lab.data("mac:screen2ax_task:test", n=N),
}
res7 = globals().get("res7", {})
for name, data in sets7.items():
    t = time.time()
    r = lab.score(lab.B, data, tag=f"007:{LABEL}:{name}")
    res7.setdefault(name, {})[LABEL] = {k: v for k, v in r.items() if k != "answers"}
    print("%-12s %-34s %5.1f%% of %d   median distance %.0f   [%.0fs]" % (
        LABEL, name, 100 * r["acc"], len(data), r["median_dist"] or -1, time.time() - t), flush=True)
json.dump(res7, open(f"{lab.dir}/exp007_generated.json", "w"), indent=1)
