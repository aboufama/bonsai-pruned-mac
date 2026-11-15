"""Plan and assemble one screen. Everything about screen i is a function of (seed, split, i)."""
import importlib
import random

from . import chrome, overlays, vocab
from . import data, splits
from .splits import PATTERN, SPLITS, owner
from .theme import pick_style, pick_theme
from .ui import Ctx

import os

ARCH_NAMES = ["settings", "email", "files", "ide", "sheet", "kanban", "chat", "dashboard", "music", "calendar",
              "shop", "video", "design", "terminal", "wizard"]
ARCH_NAMES = [n for n in ARCH_NAMES if os.path.exists(os.path.join(os.path.dirname(__file__), "archetypes", n + ".py"))]
if os.environ.get("POINTGEN_ONLY"):   # development: load only some archetype modules
    ARCH_NAMES = [n for n in ARCH_NAMES if n in os.environ["POINTGEN_ONLY"].split(",")]
ARCHS = {}

# (viewport, device scale factor, weight)
SIZES = [
    ((1280, 800), 1, 2), ((1366, 768), 1, 1), ((1440, 900), 1, 2), ((1512, 982), 1, 1.5), ((1536, 864), 1, 1),
    ((1680, 1050), 1, 1), ((1920, 1080), 1, 4), ((1920, 1200), 1, 1), ((2560, 1440), 1, 3),
    ((1280, 800), 2, 1), ((1440, 900), 2, 1.5), ((1512, 982), 2, 1.5), ((1728, 1117), 2, 1),
]


def _claim_lists(module):
    """Deal every module-level list of strings out to splits by position, before ownership freezes.
    Content lists are consumed through Data.take() while screens are built; claiming them here makes
    a label that sits in two lists belong to the same split in both."""
    for name, value in list(vars(module).items()):
        if name.startswith("__"):
            continue
        groups = value.values() if isinstance(value, dict) else [value]
        for group in groups:
            if isinstance(group, (list, tuple)) and group and all(isinstance(x, str) for x in group):
                for i, label in enumerate(group):
                    if 2 < len(label) < 60 and "\n" not in label:
                        owner(label, PATTERN[i % 5])


def load():
    """Import every archetype (which registers its vocabulary), then freeze the split assignment."""
    if ARCHS:
        return
    extra = importlib.import_module(f"{__package__}.archetypes.settings")   # overlays borrow its switches
    for name in ARCH_NAMES:
        ARCHS[name] = importlib.import_module(f"{__package__}.archetypes.{name}")
    vocab.finalize()                      # concept labels, glyphs and intents get their splits first
    for module in [data, overlays, extra] + list(ARCHS.values()):
        _claim_lists(module)              # then every content list
    splits.FROZEN = True                  # from here on, label ownership can no longer change
    vocab.check()
    for name, mod in ARCHS.items():
        have = set(mod.VARIANTS.values())
        assert have == set(SPLITS), f"archetype {name} needs a layout variant in every split, has {have}"


def variants_of(name, split):
    return [v for v, s in ARCHS[name].VARIANTS.items() if s == split]


def plan(seed, split, index, only=None, only_variant=None):
    load()
    rng = random.Random(f"pointgen:{seed}:{split}:{index}")
    names = [n for n in ARCH_NAMES if not only or n in only]
    order = list(names)
    random.Random(f"pointgen-order:{seed}:{split}:{index // len(names)}").shuffle(order)
    arch = order[index % len(names)]
    mod = ARCHS[arch]
    choices = variants_of(arch, split)
    variant = only_variant if only_variant in choices else rng.choice(choices)
    (w, h), dpr, _ = rng.choices(SIZES, [s[2] for s in SIZES])[0]
    web = mod.KIND == "web" or (mod.KIND == "either" and rng.random() < 0.5)
    kind = rng.choices(["mac", "win", "gnome"], [5, 5, 1] if web else [4, 4, 2])[0]
    shell = rng.random() < 0.6
    floating = shell and w >= 1440 and rng.random() < 0.3
    inset = f"{rng.randint(18, 48)}px {rng.randint(40, 60 + w // 12)}px {rng.randint(14, 44)}px {rng.randint(40, 60 + w // 12)}px"
    return {
        "rng": rng, "index": index, "split": split, "seed": seed, "arch": arch, "variant": variant,
        "w": w, "h": h, "dpr": dpr, "web": web, "chrome": kind, "shell": shell, "floating": floating, "inset": inset,
        "theme": pick_theme(rng, split), "style": pick_style(rng, "web" if web else kind),
        "overlay": rng.random() < 0.42,
    }


def build(seed, split, index, only=None, only_variant=None, overlay_kinds=None):
    """Return (spec, ctx, html, overlay specs)."""
    spec = plan(seed, split, index, only, only_variant)
    ctx = Ctx(spec["rng"], split)
    app = ARCHS[spec["arch"]].build(ctx, spec["variant"], spec)
    html = chrome.build_page(ctx, spec, app)
    ovs, spec["overlay_kind"] = [], "none"
    if spec["overlay"] or overlay_kinds:
        spec["overlay_kind"], ovs = overlays.add(ctx, overlay_kinds)
    return spec, ctx, html, ovs
