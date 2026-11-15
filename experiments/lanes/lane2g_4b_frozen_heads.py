# Lane 2 filler after the 4B joint-tools job (until the action cases are ready): the frozen-trunk
# pointing heads at depth 20 on the repaired 4B, long run. Depth 20 was best in the 4B sweep on lane 6
# (pointer q20 k20: 61.0 / 60.8 / 58.5 / 31.7% on select / report / fresh / Mac app windows after 4,000
# steps). Heads: pointer q20 k20 (lr 1e-3) and the cross head with the repaired click output over
# layers 0+12+20 (lr 5e-4). 20,000 steps, all four sets every 2,000 steps. The trunk's written
# answers are printed first for comparison.
# Runs in lane 2's 4B session after lane2e, which leaves the pointing-only 4B in memory.
if not globals().get("prelude_done") or lab.size != "4B":
    raise RuntimeError("run this in the 4B lab session, after lane2e")
for _n in ("T14", "E", "J"):
    if getattr(globals().get(_n), "training", False) or getattr(globals().get(_n), "open", False) is True:
        raise RuntimeError(f"{_n} is still open in this session")
_a, _b = fS.evaluate(4), fR.evaluate(4)
fS.discard(); fR.discard()
print("trunk (frozen), written answers: select %.3f   report %.3f" % (_a["p_hit"], _b["p_hit"]), flush=True)
if abs(_a["p_hit"] - 0.700) > 0.01:
    raise RuntimeError("the trunk is not the pointing-only 4B (0.700 / 0.712)")
chosen010 = "pod"
SPECS16 = [("pointer q20 k20", "pointer", 20, 20), ("crossq q20 k0+12+20", "cross_qclick", 20, (0, 12, 20))]
LR16, STEPS16, ROUND16, TAG16, ALLSETS16 = {"pointer": 1e-3, "cross": 5e-4}, 20000, 2000, "4b_frozen20k", True
SEED16, HEADSEED16 = 16, 0
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
