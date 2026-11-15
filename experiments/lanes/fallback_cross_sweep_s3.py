# Fallback filler: lane 1b's cross-attention sweep with a third set of seeds and its own tag, for a
# machine whose next job is not decided yet. Frozen model. If experiment 014 left its tuned
# multipliers in memory, they are put back first so the model is the same one lane 1 uses.
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if "T14" in globals() and "snap14" in globals():
    T14.restore(snap14)
    print("multipliers put back to the state before experiment 014 (the tuned ones are in lab/ckpt/tune_*.pt)")
chosen010 = "pod"
SPECS16 = [("cross q20 k20", "cross", 20, (20,)), ("cross q18 k18", "cross", 18, (18,)), ("cross q22 k22", "cross", 22, (22,)),
           ("cross q20 k16+20", "cross", 20, (16, 20)), ("cross q20 k12+16+20", "cross", 20, (12, 16, 20)),
           ("cross q20 k0+20", "cross", 20, (0, 20)), ("cross q24 k20", "cross", 24, (20,)), ("cross q16 k16", "cross", 16, (16,))]
LR16, STEPS16, ROUND16, TAG16, SEED16, HEADSEED16 = 5e-4, 8000, 1000, "cross_sweep_s3", 3, 3
exec(open(f"{lab.root}/experiments/016_point_head_v2.py").read())
