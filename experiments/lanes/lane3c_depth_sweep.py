# Lane 3, after lane3b_all_layers: the pointer-head depth sweep of lane 1 (eight heads, 6,000 steps,
# lr 1e-3) on the best trunk so far, frozen: the state lane 3 has in memory after its two gentle
# block-trainer runs (block 4..19, then layers 4..31). Lane 1 ran the same sweep on v2 (written
# answers select 0.800, report 0.790; best head pointer q20 k20: 68.6 / 71.5 / 77.4 / 32.5% on select /
# report / fresh / Mac app windows), so the two tables show what a better trunk does for a head.
# The trunk's own written-answer scores are printed first, for the comparison with the heads.
# Runs in lane 3's lab session after lane3b (no restart).
if not globals().get("prelude_done") or "E" not in globals() or getattr(E, "training", False):
    raise RuntimeError("run this in lane 3's session after lane3b_all_layers has finished")
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("trunk (frozen), written answers: select %.3f   report %.3f   stack %s" % (_a["p_hit"], _b["p_hit"], lab.stack), flush=True)
chosen010 = "pod"
SPECS16 = [("pointer q16 k16", "pointer", 16, 16), ("pointer q18 k18", "pointer", 18, 18), ("pointer q20 k20", "pointer", 20, 20),
           ("pointer q22 k22", "pointer", 22, 22), ("pointer q24 k24", "pointer", 24, 24), ("pointer q20 k16", "pointer", 20, 16),
           ("pointer q24 k20", "pointer", 24, 20), ("pointer q20 k12", "pointer", 20, 12)]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = 1e-3, 6000, 1000, "sweep_best_trunk", 16, 0
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
