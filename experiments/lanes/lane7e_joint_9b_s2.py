# Lane 7: a second joint decoder run on the 9B, so the 9B has two (15 Nov 03:05): the same
# as lane4h_joint_9b.py with another seed for the decoder's start and the order of the training list. The
# GroundCUA slice joins at the next restart if it is on the pod by then. Needs a fresh 9B session.
SEED4H, TAG4H = 733, "9b_joint_h1_s2"
exec(open(f"{lab.root}/experiments/lanes/lane4h_joint_9b.py").read())
