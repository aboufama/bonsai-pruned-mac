# Lane 3: squeeze the best 4B pair (the rule of 15 Nov 03:14: once a pair beats 78% on
# report, one run continues it at half the rate instead of restarting). Start: lane 1's pair at 11,000
# steps in all (79.7% on report in its run). Rates halved (multipliers 5e-5, decoder 1.5e-4). Training
# list as lane 1's, which is what produced it (mix, Fable, all of the GroundCUA slice, under-24 px targets
# three times as often), plus the icon practice set as a quarter of the list, and long sides drawn from
# 1280, 896 and 1600 (the decoder gains about 3 points from a 1600 px input even untrained at it).
# 6,000 steps, scored every 500. Needs a fresh 4B session, the s11000 pair and benchdata/pointing/icons_train_s1.
PATCH3E, HEAD3E = "bonsai2-4b-joint-h1-trunk-s11000.patch.safetensors", "bonsai2-4b-joint-h1-dec2x768-L20-s11000.safetensors"
SEED3E, TAG3E, STEPS3E, ROUND3E = 523, "4b_joint_squeeze", 6000, 500
LRS3E, LRH3E, SIZES3E, GCUA_SHARE3E, ICON_SHARE3E = 5e-5, 1.5e-4, (1280, 896, 1600), None, 0.25
exec(open(f"{lab.root}/experiments/lanes/lane3e_joint_fable.py").read())
