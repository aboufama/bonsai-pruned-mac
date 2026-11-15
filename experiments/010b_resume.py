# Experiment 010b: carry on experiment 010 after a deliberate pause.
# 010's trainer stays open in the session (latents, optimiser state and step count intact); the
# pause only hands cached GPU memory back to the machine, which had crept to 89 GB reserved.
# From here training runs in chunks of 50 steps with the cache released after each chunk.
# Uses the variables 010 left in the session (E, packs, STEPS, EVERY, WARM, score_set, mac_set,
# best, best_step, low, s0, out, started, the checkpoint paths, fast_line).
import gc
import json
import shutil
import time

import torch

assert E.training, "the block is not open; nothing to resume"
for m in E.mods:
    m.after_step()                      # a step interrupted half-way must not leave a stale working weight
gc.collect(); torch.cuda.empty_cache()
print("resuming at step %d of %d; GPU %.1f GB in use, %.1f GB reserved" % (
    E.steps_done, STEPS, torch.cuda.memory_allocated() / 1e9, torch.cuda.memory_reserved() / 1e9), flush=True)
CHUNK = 50
stopped = False
while E.steps_done < STEPS and not stopped:
    target = min(STEPS, (E.steps_done // EVERY + 1) * EVERY)
    first, later = [], []
    while E.steps_done < target:
        want = min(CHUNK, target - E.steps_done)
        before = E.steps_done
        res = E.train(packs, want, total_steps=STEPS, task=1.0, hint=0.0, warmup=WARM, final=0.2, seed=10, report_every=50)
        first.append(res["first_question"]); later.append(res["later_questions"])
        torch.cuda.empty_cache()
        if E.steps_done - before < want:          # the trainer's own memory guard stopped it
            stopped = True
            break
    a = E.score(score_set)
    mac = E.score(mac_set)
    flips = E.flips()
    E.checkpoint(last_path)
    mark = ""
    if a["p_hit"] > best:
        best, best_step, mark = a["p_hit"], E.steps_done, "  <- best so far"
        shutil.copyfile(last_path, best_path)
    out["rows"].append({"label": f"step {E.steps_done}", "select": a, "mac": mac, "flips": flips,
                        "train": {"first_question": sum(first) / len(first), "later_questions": sum(later) / len(later)}})
    print("step %5d: select %.3f (hundreds %.3f tens %.3f)   Mac windows %.3f   codes flipped %.3f%%   train loss: first question %.2f, later ones %.2f   [%.0f min]%s" % (
        E.steps_done, a["p_hit"], a["p_ok_hundreds"], a["p_ok_tens"], mac["p_hit"], 100 * flips,
        sum(first) / len(first), sum(later) / len(later), (time.time() - started) / 60, mark), flush=True)
    json.dump(out, open(f"{lab.dir}/exp010_{TAG}.json", "w"), indent=1)
    torch.cuda.empty_cache()
    low = low + 1 if a["p_hit"] < s0["p_hit"] - 0.05 else 0
    if low >= 2 and E.steps_done >= 750:
        print("two checkpoints in a row more than 0.05 below the start: stopping early", flush=True)
        break
if stopped:
    print("training stopped by the memory guard at step", E.steps_done, flush=True)
closed = E.close()
out["closed"] = closed
print("at the end: %.3f%% of the block's codes differ from the start" % (100 * closed["codes_changed_share"]))
E.D.restore(best_path if best_step else start_path)
lab.stack[-1] = f"qat010:{TAG}:best@{best_step}"
print(f"loaded the best checkpoint (step {best_step})")
fast_line(f"best checkpoint (step {best_step})")
out["canary"] = lab.canary(lab.B, tag=f"010:{TAG}")
print("canary:", out["canary"]["all"], "(original Bonsai: tf_exact 0.86, nll 0.074)")
json.dump(out, open(f"{lab.dir}/exp010_{TAG}.json", "w"), indent=1)
