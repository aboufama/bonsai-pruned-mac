"""Turn measured targets into instructions, guaranteeing each one fits exactly one element.

Two kinds:
  direct      names what is visible ("the Export button", "the trash can icon")
  functional  says what the user wants without quoting the label ("save my changes")

An instruction is only emitted when no other visible element could satisfy it. When several
elements share a label, glyph or concept, the instruction is qualified with the list entry
the control belongs to ("... for report.pdf") or its region ("... in the sidebar"); if neither
separates them, it is dropped.
"""
import re

from . import icons
from .splits import SPLITS, assert_disjoint, norm

# {r}/{R}: a reference such as "the Export button" (R = first letter capitalised)
DIRECT_WRAP = {
    "train": ["{R}", "{R}", "Click {r}", "Click on {r}", "Select {r}", "Find {r}", "Where is {r}?", "Press {r}",
              "Go to {r}", "Choose {r}", "Tap {r}", "Hit {r}", "I need {r}", "Can you click {r}?", "Take me to {r}"],
    "dev": ["Point to {r}", "Show me {r}", "Where's {r}?", "Can you find {r}?", "Point at {r}", "Put the cursor on {r}"],
    "test": ["Locate {r}", "Where can I find {r}?", "I'm looking for {r}", "Which one is {r}?", "Move the pointer to {r}",
             "Help me find {r}"],
}
# {i}/{I}: an intent verb phrase such as "save my changes"
FUNC_WRAP = {
    "train": ["{I}", "{I}", "I want to {i}", "How do I {i}?", "Where do I click to {i}?", "Help me {i}", "I need to {i}",
              "Can you {i}?", "{I}, please", "Let me {i}", "Click where I can {i}", "What should I click to {i}?"],
    "dev": ["I'd like to {i}", "What do I press to {i}?", "Show me how to {i}", "Please {i}", "Where can I {i}?",
            "I'm trying to {i}"],
    "test": ["Where should I click to {i}?", "How can I {i}?", "Which control lets me {i}?", "Time to {i}",
             "I'm looking to {i}", "Could you {i}?", "What do I click if I want to {i}?"],
}
assert_disjoint({s: set(DIRECT_WRAP[s]) for s in SPLITS}, "direct phrasing template")
assert_disjoint({s: set(FUNC_WRAP[s]) for s in SPLITS}, "functional phrasing template")


def lower_first(text):
    if len(text) > 1 and text[1].isupper():   # acronym such as "URL"
        return text
    return text[:1].lower() + text[1:]


def upper_first(text):
    return text[:1].upper() + text[1:]


def size_bucket(area_fraction):
    if area_fraction < 0.0003:
        return "xs"
    if area_fraction < 0.001:
        return "s"
    if area_fraction < 0.004:
        return "m"
    return "l"


def _contains_word(haystack, needle):
    return bool(needle) and re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None


def _within(a, b):
    """True if region phrase b could also be meant by a ("the toolbar" vs "the browser toolbar")."""
    wa, wb = set(a.lower().split()), set(b.lower().split())
    return wa <= wb


class Scene:
    """What ended up on screen: targets with their measurements, plus all visible text and glyphs."""

    def __init__(self, ctx, page):
        self.ctx = ctx
        self.t = ctx.targets
        self.m = {m["t"]: m for m in page["targets"]}
        self.vis = [tid for tid, m in self.m.items() if m["part"] and tid in self.t]
        self.valid = [tid for tid, m in self.m.items()
                      if tid in self.t and m["full"] and m["top"] and not m["trunc"] and m["w"] >= 8 and m["h"] >= 8
                      and not self.t[tid].foreign]
        self.texts = [(norm(s), o) for s, o in page["texts"]]
        self.glyphs = page["glyphs"]
        self.shown = {}   # target id -> the text runs drawn inside it (or captioning it)
        for s, o in self.texts:
            self.shown.setdefault(o, []).append(s)
        self.unseen = 0   # text targets whose label could not be found on screen

    # -- who else could be meant -------------------------------------------------------------
    def label_rivals(self, tid):
        """Other owners (target ids, or 0 for free-standing text) showing or meaning the same label."""
        key = norm(self.t[tid].label)
        rivals = {o for s, o in self.texts if s == key and o != tid}
        rivals |= {o for o in self.vis if o != tid and norm(self.t[o].label) == key}
        return rivals

    def icon_rivals(self, tid):
        t = self.t[tid]
        rivals = self.label_rivals(tid)
        mine = norm(t.name or t.label)
        rivals |= {o for s, o in self.texts if s == mine and o != tid}
        rivals |= {o for o in self.vis if o != tid and self.t[o].ui == "icon" and norm(self.t[o].name or self.t[o].label) == mine}
        if t.cid:
            rivals |= {o for o in self.vis if o != tid and self.t[o].cid == t.cid}
        if t.icon:
            rivals |= {o for name, o in self.glyphs if name == t.icon and o != tid}
        return rivals

    def concept_rivals(self, tid):
        t = self.t[tid]
        return {o for o in self.vis if o != tid and self.t[o].fam and self.t[o].fam == t.fam}

    def visible_label(self, tid):
        """A direct instruction quotes the label, so the label must really be readable on the
        element: one of its text runs is the label, or its runs joined together are."""
        key = norm(self.t[tid].label)
        runs = self.shown.get(tid, [])
        return key in runs or norm(" ".join(runs)) == key or norm("".join(runs)) == key

    def separate(self, tid, rivals):
        """How to tell tid from its rivals: ("", None), ("row", text), ("region", text) or None."""
        if not rivals:
            return "", None
        if 0 in rivals:
            return None
        t = self.t[tid]
        others = [self.t[o] for o in rivals]
        if t.row and all(o.row and o.row != t.row for o in others):
            return "row", t.row
        if t.region and all(o.region and not _within(t.region, o.region) for o in others):
            return "region", t.region
        return None

    # -- wording -----------------------------------------------------------------------------
    def direct(self, tid, rng):
        t = self.t[tid]
        if not t.direct:
            return None
        if t.refs:
            if self.label_rivals(tid):
                return None
            return rng.choice(t.refs), "none"
        if t.ui == "text" and not self.visible_label(tid):
            self.unseen += 1
            return None
        rivals = self.icon_rivals(tid) if t.ui == "icon" else self.label_rivals(tid)
        how = self.separate(tid, rivals)
        if how is None:
            return None
        kind, text = how
        if t.ui == "icon":
            name = t.name or lower_first(t.label)
            forms = [f"the {name} {t.noun}"] * 3 + [f"the {name} icon"] * 2
            look = icons.LOOKS.get(t.icon) if t.icon else None
            if look and not kind:
                forms += [f"the {look} icon"] * 2
        else:
            L = t.label
            forms = []
            if t.noun:
                forms += [f"the {L} {t.noun}"] * 4 + [f'the "{L}" {t.noun}'] * 2
                forms += [f'the {t.noun} labeled "{L}"', f"the {t.noun} that says {L}"]
                if t.role in ("row", "nav"):
                    forms += [f"the {t.noun} called {L}", f"the {t.noun} named {L}"]
            if len(L) >= 3 and t.role not in ("field", "select", "slider", "switch", "checkbox", "radio"):
                forms += [L] * 2
            if not forms:
                forms = [f'"{L}"']
        ref = rng.choice(forms)
        if kind == "row":
            opts = [f"{ref} for {text}", f"{ref} next to {text}"]
            if not text.lower().startswith(("the ", "my ")):
                opts.append(f"{ref} in the {text} row")
            ref = rng.choice(opts)
        elif kind == "region":
            ref = f"{ref} in {text}"
        return ref, kind or "none"

    def functional(self, tid, rng):
        t = self.t[tid]
        if not t.intents:
            return None
        how = self.separate(tid, self.concept_rivals(tid))
        if how is None:
            return None
        kind, text = how
        label_key = norm(t.label)
        intents = list(t.intents)
        rng.shuffle(intents)
        for intent in intents:
            obj = t.obj or "this"
            tail = ""
            if kind == "row":
                if "{o}" in intent:
                    obj = text
                else:
                    tail = f" for {text}"
            elif kind == "region":
                tail = rng.choice([", using the control in {}", ", using the one in {}"]).format(text)
            on = bool(t.state)
            phrase = intent.format(o=obj, on="off" if on else "on", enable="disable" if on else "enable",
                                   show="hide" if on else "show") + tail
            low = phrase.lower()
            if _contains_word(low, label_key):
                continue
            if t.ui == "text" and any(_contains_word(low, w) for w in label_key.split() if len(w) > 3 and w not in _STOP):
                continue
            return phrase, kind or "none"
        return None


_STOP = {"this", "that", "with", "from", "into", "your", "file", "files", "item", "items", "page", "view", "list",
         "more", "show", "open", "data", "text", "mode", "time", "date", "name", "type", "size", "line", "window"}


def make_cases(ctx, page, rng, split, per_screen=0):
    """Return (cases, elements): instruction cases and every labelled element with its box."""
    scene = Scene(ctx, page)
    dpr = page["dpr"]
    W, H = page["W"] * dpr, page["H"] * dpr

    def box(tid):
        m = scene.m[tid]
        return [round(m["x"] * dpr), round(m["y"] * dpr), round((m["x"] + m["w"]) * dpr), round((m["y"] + m["h"]) * dpr)]

    def ui_type(tid):
        # "text" when the element shows (or is captioned by) readable text, else "icon"
        return "text" if scene.shown.get(tid) else "icon"

    def describe(tid):
        t = scene.t[tid]
        e = {"role": t.role, "label": t.label, "ui_type": ui_type(tid), "label_visible": scene.visible_label(tid)}
        if t.icon:
            e["icon"] = t.icon
        if t.cid:
            e["concept"] = t.cid
        if t.region:
            e["region"] = t.region
        return e

    elements = [dict(describe(tid), bbox=box(tid)) for tid in sorted(scene.valid)]
    cands = []
    for tid in sorted(scene.valid):
        t = scene.t[tid]
        for kind, maker, wraps, slot in (("direct", scene.direct, DIRECT_WRAP, "r"), ("functional", scene.functional, FUNC_WRAP, "i")):
            got = maker(tid, rng)
            if not got:
                continue
            phrase, how = got
            wrap = rng.choice(wraps[split])
            text = wrap.replace("{" + slot + "}", phrase).replace("{" + slot.upper() + "}", upper_first(phrase))
            b = box(tid)
            area = (b[2] - b[0]) * (b[3] - b[1]) / (W * H)
            cands.append({"tid": tid, "instruction": text, "bbox": b, "element": describe(tid),
                          "tags": {"ui_type": ui_type(tid), "instruction_kind": kind, "size": size_bucket(area), "disambiguation": how}})
    # the same sentence must never point at two elements
    seen = {}
    for c in cands:
        seen.setdefault(c["instruction"].lower(), []).append(c)
    cands = [c for c in cands if len(seen[c["instruction"].lower()]) == 1]
    if per_screen and len(cands) > per_screen:
        cells = {}
        for c in cands:
            cells.setdefault((c["tags"]["ui_type"], c["tags"]["instruction_kind"]), []).append(c)
        for v in cells.values():
            rng.shuffle(v)
        order = sorted(cells)
        rng.shuffle(order)
        picked, used = [], set()
        while len(picked) < per_screen and any(cells.values()):
            for key in order:
                while cells[key]:
                    c = cells[key].pop()
                    if c["tid"] not in used:
                        picked.append(c)
                        used.add(c["tid"])
                        break
                if len(picked) >= per_screen:
                    break
        cands = sorted(picked, key=lambda c: (c["tid"], c["tags"]["instruction_kind"]))
    return cands, elements
