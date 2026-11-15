# Lane 1: the joint H1 run restarted from its own best (15 Nov 03:14): trunk and decoder
# at 12,500 steps in all (84.2% on report in the run, the best scored step; the final step, 13,500, had 82.3%). List as before (mix, Fable, all of the GroundCUA
# slice, under-24 px targets three times as often) plus the icon practice set as a quarter of the list;
# long sides drawn from 1280, 896 and 1600. Usual rates. 6,000 steps, scored every 500.
# Needs a fresh 4B session, the s12500 pair and benchdata/pointing/icons_train_s1.
PATCH3E, HEAD3E = "bonsai2-4b-joint-h1-trunk-s12500.patch.safetensors", "bonsai2-4b-joint-h1-dec2x768-L20-s12500.safetensors"
SEED3E, TAG3E, STEPS3E, ROUND3E = 829, "4b_joint_h1_d", 6000, 500
SIZES3E, GCUA_SHARE3E, ICON_SHARE3E = (1280, 896, 1600), None, 0.25
exec(open(f"{lab.root}/experiments/lanes/lane3e_joint_fable.py").read())
