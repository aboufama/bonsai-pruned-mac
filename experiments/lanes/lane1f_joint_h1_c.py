# Lane 1: the joint H1 run restarted from its best (15 Nov 03:05): trunk and decoder of
# step 7,500 in all (75.3% on report), training list = the mix, the Fable train cases and the GroundCUA
# slice, targets under 24 px drawn three times as often, long sides half 1280 half 896 (this run had
# trained at 1280 only). 6,000 steps, scored every 500. Needs a fresh 4B session and the s7500 pair.
PATCH3E, HEAD3E = "bonsai2-4b-joint-h1-trunk-s7500.patch.safetensors", "bonsai2-4b-joint-h1-dec2x768-L20-s7500.safetensors"
SEED3E, TAG3E, STEPS3E, ROUND3E = 157, "4b_joint_h1_c", 6000, 500
exec(open(f"{lab.root}/experiments/lanes/lane3e_joint_fable.py").read())
