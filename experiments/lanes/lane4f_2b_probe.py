# Lane 4: a quick probe of Bonsai 2 2B (24 layers, width 2048), the same port and repair as the 4B got:
# original score, 500 multiplier updates (experiment 020), then the block trainer over layers 4..23 for
# 1,000 steps with long sides weighted to 1280 (the question: can a very small model pinpoint on a sharp
# image), scored at 1280, 1600 and 896. For a two-stage design (a fast
# model points roughly, a detector on a crop picks the element). Stop here and report.
# Needs a fresh lab session with BONSAI_SIZE=2B: tools/restart_lane.sh <this file> 2B
PATCH = ""
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "2B":
    raise RuntimeError(f"this needs a 2B session (size {lab.size})")
_n = len(list(lab.B.model.language_model.layers))
LAYERS20, UPDATES20, LR20, TAG20 = list(range(4, _n)), 500, 1e-3, "2b_scales_u500"
exec(open(f"{lab.root}/experiments/020_port_4b.py").read())
LO10, HI10 = 4, _n - 1
STEPS10, EVERY10, LR_SCALES10, LR_FP10, CODES10, WARM10, MAC_N10, TAG10 = 1000, 500, 2e-4, 2e-5, False, 100, 60, "2b_block"
# sharp screenshots (01:20): half of the training screenshots at 1280, the rest 896 to 1600
SIZES10 = (1280, 1280, 1280, 1280, 896, 1024, 1440, 1600)
SIZE_SCORES10, MAC_SIZES10 = (1280, 1600, 896), (896,)
KEEP10, TEACHER10, TEACH10, EXTRA10, EXTRA_SHARE10, EXTRA_SCORES10, DROP10 = None, None, 0.0, None, None, None, None
exec(open(f"{lab.root}/experiments/010_slow_codes.py").read())
