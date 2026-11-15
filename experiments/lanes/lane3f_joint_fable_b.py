# Lane 3: the joint Fable run restarted from its best (15 Nov 03:05): trunk and decoder of
# step 4,000 (75.9% on report in the run, 75.3% from the exported files), training list = the mix, the
# Fable train cases and now the GroundCUA slice, targets under 24 px drawn three times as often, long
# sides half 1280 half 896. 6,000 steps, scored every 500. Needs a fresh 4B session and the s4000 pair.
PATCH3E, HEAD3E = "bonsai2-4b-joint-fable-trunk-s4000.patch.safetensors", "bonsai2-4b-joint-fable-dec2x768-L20-s4000.safetensors"
SEED3E, TAG3E, STEPS3E, ROUND3E = 311, "4b_joint_fable_b", 6000, 500
# GroundCUA is held to a third of the list here (lane 1 runs with all of it, where it is about 90% of the
# steps): the two lanes are the comparison of how much GroundCUA the 4B wants.
GCUA_SHARE3E = 0.33
exec(open(f"{lab.root}/experiments/lanes/lane3e_joint_fable.py").read())
