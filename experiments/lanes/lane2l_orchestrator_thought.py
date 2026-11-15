# Lane 2: the orchestrator's second run, with a short thought before each step (15 Nov
# 02:55; planned as the second run on the same lane). It continues in the session of the
# first run, from the state that run ended in (its step 3,000, which was also its best: 29.2% of reserved
# steps fully right), so the comparison with the first run is "3,000 more updates with thoughts".
# Same mix and scores; answers may be 160 tokens long. Patches: bonsai2-9b-orch-v2-thought-u<step>.
if "T27" not in globals() or not globals().get("prelude_done"):
    raise RuntimeError("run this in the session of lane2k_orchestrator_9b.py, after it has finished")
UPDATES27, EVERY27, LR27, ACC27, TAG27, PATCHNAME27, THOUGHT27 = 3000, 500, 2e-4, 2, "orch_9b_thought", "bonsai2-9b-orch-v2-thought", True
exec(open(f"{lab.root}/experiments/027_orchestrator.py").read())
