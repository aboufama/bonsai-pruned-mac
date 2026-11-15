# Lane 4: the 9B decoder pointer continued from this lane's own best pair (exported by
# tools/after_joint_best.sh as bonsai2-9b-joint-nb-l4-best) with the simulator's training set added
# (macsim_train_s1, at most a quarter of the list, like the icon set), neighbour cases three times as
# often, usual rates, half 1280 half 896, 3,000 steps, scored every 500.
PATCH4H, HEAD4H = "bonsai2-9b-joint-nb-l4-best-trunk.patch.safetensors", "bonsai2-9b-joint-nb-l4-best-dec2x768-L20.safetensors"
SEED4H, TAG4H, STEPS4H, LRS4H, LRH4H, EMPH_FILE4H = 461, "9b_joint_sim_l4", 3000, 1e-4, 3e-4, "_neighbours.py"
exec(open(f"{lab.root}/experiments/lanes/lane4h_joint_9b.py").read())
