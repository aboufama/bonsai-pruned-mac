"""The training mix of generated and real macOS pointing cases, and its packing into steps."""
import os
import random

DEFAULT_MIX = [                                 # (lab.data name, cases, cap per app)
    ("gen:benchdata/pointing/train_s303", 9000, None),
    ("gen:benchdata/pointing/train_s202", 3000, None),
    ("mac:os_atlas_mac:train", 6000, None),
    ("mac:screen2ax_tree:train", 6000, 400),
    ("mac:scalecua_mac:train", 1400, None),
    ("mac:showui_desktop_mac:train", 1037, None),
    ("mac:agentnet:train", 1500, None),
]

# Optional and OFF by default: single computer_use actions from AgentNet trajectories (weightlab/actions.py,
# docs/ACTION_FORMAT.md). Not in DEFAULT_MIX and never read by build(). These are chat samples, which a
# training script adds to its sample list itself:   samples += mixes.action_samples(lab)
ACTION_MIX = ("mac:agentnet:actions:train", 3000)             # (name, samples)


def action_samples(lab, mix=ACTION_MIX, seed=10, **options):
    """The optional action samples, ready for TaskTuner and chat.score. Empty if the cases are not on this machine."""
    from . import actions
    if not os.path.exists(f"{lab.root}/data/mac/agentnet/cases_actions.jsonl"):
        print("not on this machine, skipped:", mix[0])
        return []
    return actions.samples(lab, split=mix[0].split(":")[-1], n=mix[1], seed=seed, **options)


# Optional and OFF by default as well: orchestrator steps, the next step in words with no coordinates
# (the `next_step` tool, docs/ACTION_FORMAT.md "Orchestrator steps").   samples += mixes.step_samples(lab)
STEP_MIX = ("mac:agentnet:steps:train", 3000)                 # (name, samples)


def step_samples(lab, mix=STEP_MIX, seed=10, **options):
    """The optional orchestrator-step samples. Empty if the cases are not on this machine."""
    from . import actions
    if not os.path.exists(f"{lab.root}/data/mac/agentnet/cases_steps.jsonl"):
        print("not on this machine, skipped:", mix[0])
        return []
    return actions.step_samples(lab, split=mix[0].split(":")[-1], n=mix[1], seed=seed, **options)


def usable(text):
    """Drop labels that are not instructions a person could follow: icon-font glyphs (private-use
    characters), no letters at all, or absurd lengths. Mostly raw accessibility labels."""
    return (2 <= len(text) <= 200 and any(c.isalpha() for c in text)
            and not any(0xE000 <= ord(c) <= 0xF8FF for c in text))


def build(lab, mix=None, kmax=5, seed=10, quiet=False):
    """Returns (cases, packs, counts). A pack is 1..kmax cases on the same screenshot, asked one
    after the other in one training step. Sets that are not on this machine are skipped."""
    cases, counts = [], {}
    for name, n, cap in (mix or DEFAULT_MIX):
        base = name.split(":")[1] if name.startswith("gen:") else f"data/mac/{name.split(':')[1]}"
        if not os.path.exists(f"{lab.root}/{base}/cases.jsonl"):
            if not quiet:
                print("not on this machine, skipped:", name)
            continue
        items = lab.data(name, n=int(n * (3 if cap else 1.3)))
        if cap:
            per, kept = {}, []
            for it in items:
                per[it["group"]] = per.get(it["group"], 0) + 1
                if per[it["group"]] <= cap:
                    kept.append(it)
            items = kept
        seen, uniq = set(), []
        for it in items:
            if it["id"] not in seen and usable(it["instruction"]):
                seen.add(it["id"]); uniq.append(it)
        uniq = uniq[:n]
        counts[name] = len(uniq)
        cases += uniq
    rng = random.Random(seed)
    rng.shuffle(cases)
    by_image = {}
    for it in cases:
        by_image.setdefault(it["path"], []).append(it)
    packs = []
    for items in by_image.values():
        rng.shuffle(items)
        i = 0
        while i < len(items):
            k = rng.randint(1, kmax)
            packs.append(items[i:i + k])
            i += k
    rng.shuffle(packs)
    return cases, packs, counts
