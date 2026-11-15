# Lane 5, second job: the same written-answer study on the ORIGINAL Bonsai, for the before/after table.
# Needs a fresh lab session (restart the kernel first): the prelude only applies a patch once.
PATCH = ""
exec(open(f"{lab.root}/experiments/_prelude.py").read())
TAG13, N13 = "original", 200
exec(open(f"{lab.root}/experiments/013_looks.py").read())
