# Lane 4: the 9B decoder pointer once more from this lane's newest best pair (bonsai2-9b-joint-sim-l4-best:
# step 2,500 of the run with the simulator set, 89.2% on report / 93.0% within 20 px in its run), same list
# (mix, Fable, icon set and simulator set each at most a quarter, neighbour cases three times as often),
# usual rates, half 1280 half 896, 2,000 steps, scored every 500. The last run before the 08:30 stop.
PATCH4H, HEAD4H = "bonsai2-9b-joint-sim-l4-best-trunk.patch.safetensors", "bonsai2-9b-joint-sim-l4-best-dec2x768-L20.safetensors"
SEED4H, TAG4H, STEPS4H, LRS4H, LRH4H, EMPH_FILE4H = 479, "9b_joint_sim2_l4", 2000, 1e-4, 3e-4, "_neighbours.py"
exec(open(f"{lab.root}/experiments/lanes/lane4h_joint_9b.py").read())
