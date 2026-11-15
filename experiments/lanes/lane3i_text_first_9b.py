# Lane 3, the research pod (15 Nov 05:35, from a scan of the literature): "instruction before
# the image". With the image first, its tokens never see the request; a published report gains 3 to 4
# points by putting the request first. Here: the best 9B decoder pair (s2-s5000, 87.3% on report), the
# target description placed BEFORE the screenshot in the prompt (lab.text_first), decoder and multipliers
# of layers 0..19 retrained jointly. One question per screenshot (later questions cannot precede the
# image), usual rates, mix + Fable, half 1280 half 896, 4,000 steps, scored every 500 on report and select.
# Compare with the same pair's continuations on lanes 4 and 7 at equal steps (those use up to five
# questions per screenshot). Needs a fresh 9B session and the pair.
lab.text_first = True
PATCH4H, HEAD4H = "bonsai2-9b-joint-h1-trunk-s2-s5000.patch.safetensors", "bonsai2-9b-joint-h1-dec2x768-L20-s2-s5000.safetensors"
SEED4H, TAG4H, STEPS4H, LRS4H, LRH4H, EMPH_FILE4H, SINGLE4H = 457, "9b_joint_text_first", 4000, 1e-4, 3e-4, "_emphasis.py", True
exec(open(f"{lab.root}/experiments/lanes/lane4h_joint_9b.py").read())
