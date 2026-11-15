# Lane 4: the 9B pointer (15 Nov 02:45). Joint decoder on the 9B: the H1 shape (2 layers x 768)
# reading layer 20, from scratch, trained together with the multipliers of layers 0..19 (1e-4; head 3e-4),
# trunk bonsai2-9b-point-v3-mixed896, no written-answer loss. Training list: the mix plus every Fable train
# case, long sides half 1280 half 896. 6,000 steps, scored every 500 on report and select (on target, within
# 20 px), canary and tool guards, a copy of head and gains at every score. Lines to beat: the 9B's written
# answers, 86.1% generated on report at 1280, then the parent's 91.8%. Needs a fresh 9B session.
import os
import random

import torch
import weightlab.head as headmod

PATCH = f"{lab.root}/export/patches/bonsai2-9b-point-v3-mixed896.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "9B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 9B session on the v3-mixed896 patch (size {lab.size}, stack {lab.stack})")
_rs = random.Random(globals().get("SEED4H", 419))
_packs = list(packs)
for _name in ("mac:fable_teacher:train", "mac:groundcua_200k:train"):
    if not os.path.exists(f"{lab.root}/data/mac/{_name.split(':')[1]}/cases.jsonl"):
        continue
    _by, _ok = {}, {}
    for _it in lab.data(_name, n=200000):
        if _it["path"] not in _ok:
            _ok[_it["path"]] = os.path.exists(_it["path"])
        if _ok[_it["path"]]:
            _by.setdefault(_it["path"], {})[_it["id"]] = _it
    for _items in _by.values():
        _items = list(_items.values()); _rs.shuffle(_items)
        _packs += [_items[i:i + 5] for i in range(0, len(_items), 5)]
    print("training list: %s added, %d cases on %d screenshots" % (_name, sum(len(v) for v in _by.values()), len(_by)), flush=True)
exec(open(f"{lab.root}/experiments/lanes/_emphasis.py").read())
_packs = emphasise(_packs)
PACKS18 = [[dict(it, max_side=side) for it in pack] for pack in _packs for side in [_rs.choice((1280, 896))]]
_rs.shuffle(PACKS18)
print("training list: %d packs, long sides half 1280 half 896" % len(PACKS18), flush=True)
STEPS18, ROUND18, KIND18, LAYER18, KEYS18, LRS18, LRH18, DIGITS18, TAG18 = 6000, 500, "cross_dec:768:2", 20, (20,), 1e-4, 3e-4, 0.0, globals().get("TAG4H", "9b_joint_h1")
LO18, GUARDS18 = 0, True
torch.manual_seed(globals().get("SEED4H", 419))
# the joint tuner builds only pointer and cross heads by itself, so the decoder is made here (from scratch)
HEAD18 = headmod.DecoderHead((20,), d=lab.B.config.text_config.hidden_size, r=768, layers=2).to(lab.B.device).float()
exec(open(f"{lab.root}/experiments/018_joint_head.py").read())
PACKS18 = None
