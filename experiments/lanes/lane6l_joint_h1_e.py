# Lane 6: a third 4B joint run (the 4B is the product; 15 Nov 03:14), from lane 1's best
# pair (12,500 steps in all; 83.5% on report from its files). Same list as the run that produced it
# (mix, Fable, all of the GroundCUA slice, under-24 px targets three times as often) WITHOUT the icon set,
# and long sides drawn from 1280, 896 and 1600: beside lane 1's run (same start, with the icon set) it
# shows what the icon set adds. 6,000 steps, scored every 500. Needs a fresh 4B session and the s12500 pair.
PATCH3E, HEAD3E = "bonsai2-4b-joint-h1-trunk-s12500.patch.safetensors", "bonsai2-4b-joint-h1-dec2x768-L20-s12500.safetensors"
SEED3E, TAG3E, STEPS3E, ROUND3E = 613, "4b_joint_h1_e", 6000, 500
SIZES3E, GCUA_SHARE3E, ICON_SHARE3E = (1280, 896, 1600), None, 0.25
exec(open(f"{lab.root}/experiments/lanes/lane3e_joint_fable.py").read())
