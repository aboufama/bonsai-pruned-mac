# Lane 1: the joint decoder run continued (15 Nov 02:35): the H1 decoder and the trunk as
# lane1d left them after its 4,000 steps (head 76.1% on select at steps 3,000 and 3,500 against 72.3% on
# the frozen trunk), 6,000 more steps to 10,000 in all, same rates (multipliers of layers 0..20 at 1e-4,
# head at 3e-4, no written-answer loss), scores every 500 on select AND report, canary and tool guards,
# a copy of the head and the multiplier gains at every score. If data/mac/groundcua_200k is on the pod its
# cases join the training list. Runs in lane1d's session, right after it.
import os
import random

if not globals().get("prelude_done") or "J" not in globals() or getattr(J, "open", False) is True:
    raise RuntimeError("run this after lane1d_joint_h1 has finished, in the same session")
HEAD18 = J.head
PACKS18 = list(packs)
if os.path.exists(f"{lab.root}/data/mac/groundcua_200k/cases.jsonl"):
    _by = {}
    for _it in lab.data("mac:groundcua_200k:train", n=200000):
        _by.setdefault(_it["path"], {})[_it["id"]] = _it
    for _items in _by.values():
        _items = list(_items.values())
        PACKS18 += [_items[i:i + 5] for i in range(0, len(_items), 5)]
    print("GroundCUA slice added: %d cases on %d screenshots" % (sum(len(v) for v in _by.values()), len(_by)), flush=True)
exec(open(f"{lab.root}/experiments/lanes/_emphasis.py").read())
PACKS18 = emphasise(PACKS18)
random.Random(181).shuffle(PACKS18)
STEPS18, ROUND18, KIND18, LAYER18, KEYS18, LRS18, LRH18, DIGITS18, TAG18 = 6000, 500, "cross_dec:768:2", 20, (20,), 1e-4, 3e-4, 0.0, "4b_joint_h1_b"
LO18, GUARDS18 = 0, True
exec(open(f"{lab.root}/experiments/018_joint_head.py").read())
PACKS18 = None
