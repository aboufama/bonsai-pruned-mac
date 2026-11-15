# Experiment 005b: is the gain from tuning only the multipliers (005) real?
#  - generated answers (not teacher-forced) on ScreenSpot-v2 screens used by neither score so far
#  - the same screens with the original multipliers put back
#  - the canary before and after
import json
import time
import torch

tuned5 = T5.snapshot()
torch.save(tuned5, f"{lab.dir}/ckpt/exp005_scales_L4-19_s400.pt")
used = {t["id"] for t in dev} | {t["id"] for t in held}
test = [t for t in lab.data("ssv2", n=150, offset=11) if t["id"] not in used][:120]
print(len(test), "fresh ScreenSpot-v2 screens;", sum(t["group"] == "desktop" for t in test), "desktop,",
      sum(t["group"] == "mobile" for t in test), "mobile,", sum(t["group"] == "web" for t in test), "web")


def show(label, r):
    print(label, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "answers"})[:700], flush=True)


t = time.time()
after = lab.score(lab.B, test, tag="005b:tuned")
show("TUNED multipliers, generated answers:", after)
print("  (%.0f s)" % (time.time() - t))
c_after = lab.canary(lab.B, tag="005b:tuned")
T5.restore(snap5)
before = lab.score(lab.B, test, tag="005b:original")
show("ORIGINAL Bonsai, generated answers:", before)
c_before = lab.canary(lab.B, tag="005b:original")
T5.restore(tuned5)
print("canary original:", c_before["all"], " tuned:", c_after["all"])
for k in c_before:
    if k != "all":
        print("   %-12s tf_exact %.3f -> %.3f   nll %.3f -> %.3f" % (k, c_before[k]["tf_exact"], c_after[k]["tf_exact"], c_before[k]["nll"], c_after[k]["nll"]))
json.dump({"n": len(test), "tuned": {k: v for k, v in after.items() if k != "answers"},
           "original": {k: v for k, v in before.items() if k != "answers"},
           "canary_original": c_before, "canary_tuned": c_after}, open(f"{lab.dir}/exp005b_verify.json", "w"), indent=1)
