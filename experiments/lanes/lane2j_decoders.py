# Lane 2: decoder sweep on the frozen best 4B (15 Nov 02:00). T2, the flips and the rank-16
# side paths showed the trunk has little room left, while the 25 M decoder H1 on frozen layer-20 states
# already matches the 4B's written answers: so the extra skill goes into full-precision parts on top.
# Trunk frozen at bonsai2-4b-point-v3-mixed (0.762 / 0.766). All read request tokens at layer 20:
#   D1  decoder 4 layers x 1024, image states of layer 20
#   D2  decoder 6 layers x 1024, image states of layer 20
#   D3  the H1 shape (2 layers x 768) with image states of layers 16 and 20
# From scratch, 8,000 steps, long sides half 1280 half 896, the full mix plus the Fable train cases; every
# 1,000 steps all sets are scored (select, report, fresh, Mac app windows, the Fable test split by kind):
# on target, within 20 px, click decision; a copy of the heads is kept at every scored step; milliseconds
# per answer of each head alone at the end. Needs a fresh 4B session and data/mac/fable_teacher.
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v3-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v3-mixed patch (size {lab.size}, stack {lab.stack})")
chosen010 = "pod"
_fk = {}
for _it in lab.data("mac:fable_teacher:test", n=20000):
    if os.path.exists(_it["path"]):
        _fk.setdefault("Fable test, %s" % (_it.get("kind") or "all"), {})[_it["id"]] = _it
EXTRA_SETS16 = {k: list(v.values()) for k, v in sorted(_fk.items())}
print("Fable test split:", {k: len(v) for k, v in EXTRA_SETS16.items()}, flush=True)
SPECS16 = [("D1 dec4x1024 k20", "cross_dec:1024:4", 20, (20,)),
           ("D2 dec6x1024 k20", "cross_dec:1024:6", 20, (20,)),
           ("D3 dec2x768 k16+20", "cross_dec:768:2", 20, (16, 20))]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = {"pointer": 1e-3, "cross": 3e-4}, 8000, 1000, "4b_decoders", 16, 0
SIZES16, SCORE_SIZES16, ALLSETS16, EXTRA16, KEEP_ROUNDS16 = (1280, 896), None, True, ["mac:fable_teacher:train"], True
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
KEEP_ROUNDS16 = None
