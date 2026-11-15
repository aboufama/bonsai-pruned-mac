# Lane 4: the 9B pointer through its decoder (15 Nov 04:56):
# continue from the best pair (lane 7's s2-s5000: 87.3% on report, 91.8% within 20 px) with the neighbour
# cases drawn three times as often (Apple's apps twice again), the icon practice set as at most a quarter
# of the list, and the macsim training set when it is on the pod. Usual rates, half 1280 half 896,
# 4,000 steps, scored every 500. Needs a fresh 9B session, that pair and data/mac/neighbour_ids.json.
PATCH4H, HEAD4H = "bonsai2-9b-joint-h1-trunk-s2-s5000.patch.safetensors", "bonsai2-9b-joint-h1-dec2x768-L20-s2-s5000.safetensors"
SEED4H, TAG4H, STEPS4H, LRS4H, LRH4H, EMPH_FILE4H = 443, "9b_joint_nb_l4", 4000, 1e-4, 3e-4, "_neighbours.py"
exec(open(f"{lab.root}/experiments/lanes/lane4h_joint_9b.py").read())
