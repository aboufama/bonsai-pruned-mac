# Lane 4: the joint decoder run of lane3e again with another seed (15 Nov 02:30:
# D3's 2-layer shape was ahead of the 4-layer D1 at 3,000 steps of the decoder sweep, 36.1% against 27.8%
# on report, so the 4-layer joint variant is not run). Same needs as lane3e_joint_fable.py.
SEED3E, TAG3E = 977, "4b_joint_fable_s2"
exec(open(f"{lab.root}/experiments/lanes/lane3e_joint_fable.py").read())
