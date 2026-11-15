# Lane 3: a second joint decoder run that combines the two things that work (15 Nov 02:35):
# trunk = bonsai2-4b-point-v3-fable (the 4B trained with the Fable-written cases: report 0.787, Fable test
# intent 0.316 -> 0.438), decoder = H1 from its exported 6,000-step weights (trained on the frozen v2-mixed
# trunk), trained together with the multipliers of layers 0..20 (1e-4; head 3e-4), no written-answer loss.
# Training list: the mix plus every Fable train case (and the GroundCUA slice if it is on the pod), long
# sides half 1280 half 896. 8,000 steps, scores every 1,000 on select and report, canary and tool guards, a
# copy of head and gains at every score. Needs a fresh 4B session, export/heads/bonsai2-4b-h1-dec2x768-L20-s6000.safetensors
# and data/mac/fable_teacher.
import os
import random

import torch
from safetensors.torch import load_file
import weightlab.head as headmod

PATCH = f"{lab.root}/export/patches/" + globals().get("PATCH3E", "bonsai2-4b-point-v3-fable.patch.safetensors")
exec(open(f"{lab.root}/experiments/_prelude.py").read())
_h = f"{lab.root}/export/heads/" + globals().get("HEAD3E", "bonsai2-4b-h1-dec2x768-L20-s6000.safetensors")
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"] or not os.path.exists(_h):
    raise RuntimeError(f"this needs a fresh 4B session on {os.path.basename(PATCH)} and {_h} (size {lab.size}, stack {lab.stack})")
HEAD18 = headmod.DecoderHead((20,), d=lab.B.config.text_config.hidden_size, r=768, layers=2).to(lab.B.device).float()
HEAD18.load_state_dict({k: v.to(lab.B.device) for k, v in load_file(_h).items()})
_rs = random.Random(globals().get("SEED3E", 183))
_packs = list(packs)
_icons = "gen:benchdata/pointing/icons_train_s1"      # the icon practice set (generated screens with real system icons)
for _name in ("mac:fable_teacher:train", "mac:groundcua_200k:train", _icons):
    if not os.path.exists(f"{lab.root}/{_name[4:]}/cases.jsonl" if _name.startswith("gen:") else f"{lab.root}/data/mac/{_name.split(':')[1]}/cases.jsonl"):
        continue
    _by, _ok = {}, {}
    for _it in lab.data(_name, n=200000):
        if _it["path"] not in _ok:
            _ok[_it["path"]] = os.path.exists(_it["path"])
        if _ok[_it["path"]]:
            _by.setdefault(_it["path"], {})[_it["id"]] = _it
    _new = []
    for _items in _by.values():
        _items = list(_items.values()); _rs.shuffle(_items)
        _new += [_items[i:i + 5] for i in range(0, len(_items), 5)]
    # shares: GroundCUA and the icon set are each at most this share of the list as it stands when they are added
    _cap = globals().get("GCUA_SHARE3E") if "groundcua" in _name else globals().get("ICON_SHARE3E", 0.25) if _name == _icons else None
    if _cap and len(_new) > len(_packs) * _cap / (1 - _cap):
        _rs.shuffle(_new)
        _new = _new[:round(len(_packs) * _cap / (1 - _cap))]
        print("training list: %s cut to %d packs (%.0f%% of the list)" % (_name, len(_new), 100 * _cap), flush=True)
    _packs += _new
    print("training list: %s added, %d cases on %d screenshots" % (_name, sum(len(v) for v in _by.values()), len(_by)), flush=True)
exec(open(f"{lab.root}/experiments/lanes/_emphasis.py").read())
_packs = emphasise(_packs)
PACKS18 = [[dict(it, max_side=side) for it in pack] for pack in _packs for side in [_rs.choice(globals().get("SIZES3E", (1280, 896)))]]
_rs.shuffle(PACKS18)
print("training list: %d packs, long sides drawn from %s" % (len(PACKS18), globals().get("SIZES3E", (1280, 896))), flush=True)
STEPS18, ROUND18, KIND18, LAYER18, KEYS18, LRS18, LRH18, DIGITS18 = globals().get("STEPS3E", 8000), globals().get("ROUND3E", 1000), "cross_dec:768:2", 20, (20,), globals().get("LRS3E", 1e-4), globals().get("LRH3E", 3e-4), 0.0
TAG18 = globals().get("TAG3E", "4b_joint_fable")
LO18, GUARDS18 = 0, True
exec(open(f"{lab.root}/experiments/018_joint_head.py").read())
PACKS18 = None
