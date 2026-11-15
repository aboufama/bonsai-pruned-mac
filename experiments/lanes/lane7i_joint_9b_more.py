# Lane 7: the 9B joint decoder continued from its best scored step (pair s2-s5000), half rates
# (multipliers 5e-5, decoder 1.5e-4), same list (mix + Fable, under-24 px targets three times as often),
# half 1280 half 896, 4,000 steps, scored every 500. Needs a fresh 9B session and the exported pair.
PATCH4H, HEAD4H = "bonsai2-9b-joint-h1-trunk-s2-s5000.patch.safetensors", "bonsai2-9b-joint-h1-dec2x768-L20-s2-s5000.safetensors"
SEED4H, TAG4H, STEPS4H, LRS4H, LRH4H = 739, "9b_joint_h1_s2_b", 4000, 5e-5, 1.5e-4
exec(open(f"{lab.root}/experiments/lanes/lane4h_joint_9b.py").read())
