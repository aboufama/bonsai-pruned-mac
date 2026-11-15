# Lane 1: reward passes on the simulator's pointing set for the best 4B pair (15 Nov;
# experiment 029). Pools of 3,000 fresh macsim_train_s1 cases, classes = the simulator's (name, function,
# same_name, position, state, tiny, partial). The first loop on the older pools (same code, usual rates,
# one mix case per miss) lifted its own pool from 60.3% to 67.7% but dropped report from 83.5% to 74.7%
# after 600 steps, so here: a quarter of the usual rates, two mix cases per miss, 400 steps per pass, and
# the loop stops only if report is more than 3 points under the start (restarts of these joint runs dip
# and recover) or the canary is under 0.90. Held-out per pass: report, select, the neighbour slice, Mac
# windows, macsim_dev (600). Needs a fresh 4B session and the s12500 pair.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-joint-h1-trunk-s12500.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the s12500 trunk (size {lab.size}, stack {lab.stack})")
HEAD29 = f"{lab.root}/export/heads/bonsai2-4b-joint-h1-dec2x768-L20-s12500.safetensors"
POOLSET29, PASSES29, POOL29, STEPS29, LRS29, LRH29, MIX29, DROP29, TAG29 = "gen:benchdata/pointing/macsim_train_s1", 6, 3000, 400, 2.5e-5, 7.5e-5, 2, 0.0301, "4b_reward_macsim"
exec(open(f"{lab.root}/experiments/029_reward_loop_4b.py").read())
