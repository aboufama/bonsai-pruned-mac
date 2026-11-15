"""Icon-dense, Mac-style screens whose only targets are small icon-only controls.

A separate generation mode (generate_icons.py), not one of the archetypes in screen.py, so adding
it does not change what any index of the main generator renders.

Icons are real ones only, from six sources:
  lucide     assets/icons                      (the set the main generator uses; its glyph split applies)
  heroicons  assets/iconsets/heroicons         web sets, fetched by fetch_assets.sh
  tabler     assets/iconsets/tabler
  material   assets/iconsets/material
  sf         assets/apple/symbols  + index.json   Apple system symbols rendered on a Mac with AppKit
  app        assets/apple/apps     + index.json   application icons from the same Mac
Requests come from pointgen/icon_vocab.txt (hand-written, one line per drawing) and, for system
symbols, from the search words in Apple's own symbol catalogue (carried in index.json).

Splits: a Lucide glyph belongs to the split icons.icon_split() gives it, exactly as in the main
generator; every other icon is dealt out by splits.weighted_split() on its id. Themes, accents,
phrasing templates and layout variants are the main generator's split-disjoint ones.
"""
import base64
import functools
import io
import json
import os
import random
import re

from . import icons, screen
from .instruct import DIRECT_WRAP, FUNC_WRAP, size_bucket, upper_first
from .splits import SPLITS, norm, weighted_split
from .theme import pick_style, pick_theme

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
VOCAB = os.path.join(HERE, "icon_vocab.txt")
ARCH = "icondense"
VARIANTS = {"rail": "train", "rows": "train", "inspector": "train", "palette": "dev", "ribbon": "test"}
PREFIX = {"h": "heroicons", "t": "tabler", "m": "material", "s": "sf"}
WEB_SETS = ("lucide", "heroicons", "tabler", "material")
# (image width, image height, weight); every page is laid out 1280 CSS px wide and rendered at
# device scale width/1280, so a control of N CSS px is N px on a 1280 px wide screenshot
SIZES = [(1280, 800, 2), (1440, 900, 2), (1512, 982, 1.5), (1728, 1117, 1), (1920, 1080, 3), (1920, 1200, 1),
         (2560, 1440, 2), (2880, 1800, 1.5), (3024, 1964, 1)]
_SF_VARIANT = re.compile(r"\.(fill|circle|square|slash|badge\..*|rectangle)$")

POOLS = {}     # split -> icon set -> [icon]
STATS = {}


@functools.lru_cache(maxsize=None)
def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


@functools.lru_cache(maxsize=None)
def _app_b64(path):
    from PIL import Image
    im = Image.open(path).convert("RGBA").resize((112, 112), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


@functools.lru_cache(maxsize=None)
def _web_svg(iset, name):
    with open(os.path.join(ASSETS, "iconsets", iset, name + ".svg"), encoding="utf-8") as f:
        text = re.sub(r"<!--.*?-->", "", f.read(), flags=re.S)
    text = text[text.index("<svg"):]
    head, rest = text[:text.index(">")], text[text.index(">"):]
    head = re.sub(r'\s(width|height|class|aria-hidden|data-slot)="[^"]*"', "", head)
    return re.sub(r"\s+", " ", head + rest).strip()


def _web_exists(iset, name):
    return os.path.exists(os.path.join(ASSETS, "iconsets", iset, name + ".svg"))


def load():
    """Read the vocabulary and the icon indexes and deal every icon to a split. Idempotent."""
    if POOLS:
        return
    screen.load()   # fixes the Lucide glyph split exactly as the main generator has it
    apple = {"symbols": [], "apps": []}
    idx = os.path.join(ASSETS, "apple", "index.json")
    if os.path.exists(idx):
        with open(idx, encoding="utf-8") as f:
            apple = json.load(f)
    sf = {e["name"]: e for e in apple["symbols"]}
    out, seen, sf_group, missing = [], set(), {}, []

    def add(iset, name, group, surf, nouns, actions, hand):
        iid = name if iset == "lucide" else f"{iset}:{name}"
        if iid in seen:
            return
        seen.add(iid)
        split = icons.icon_split(name) if iset == "lucide" else weighted_split("icon:" + iid)
        out.append({"id": iid, "set": iset, "name": name, "group": group, "surf": surf, "nouns": nouns,
                    "actions": actions, "hand": hand, "split": split, "label": re.sub(r"^the ", "", nouns[0])})

    with open(VOCAB, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            group, names, surf, nouns, actions = [x.strip() for x in line.split("|")]
            nouns = ["the " + x.strip() for x in nouns.split(";") if x.strip()]
            actions = [x.strip() for x in actions.split(";") if x.strip()]
            for tok in names.split():
                if tok[1:2] == ":":
                    iset, name = PREFIX[tok[0]], tok[2:]
                    if iset == "sf":
                        if name not in sf:
                            missing.append(tok)
                            continue
                        sf_group[name] = group
                        # Apple's own name for the symbol; its search words are left to symbols without a vocabulary line
                        extra = [p for p in sf[name]["phrasings"][:1] if sf[name].get("named") and p not in nouns]
                        add("sf", name, group, surf or "ts", nouns + extra, actions, True)
                    else:
                        name = name.replace("_", "-") if iset != "material" else name
                        if not _web_exists(iset, name):
                            missing.append(tok)
                            continue
                        add(iset, name, group, surf or "ts", nouns, actions, True)
                else:
                    got = [n for n in tok.split("/") if icons.exists(n)]
                    if not got:
                        missing.append(tok)
                        continue
                    add("lucide", icons.canon(got[0]), group, surf or "ts", nouns, actions, True)
    for name, e in sf.items():        # system symbols the vocabulary does not cover: Apple's search words only
        base = name
        while _SF_VARIANT.search(base):
            base = _SF_VARIANT.sub("", base)
        group = sf_group.get(base) or sf_group.get(name) or "sf:" + base
        surf = "tsm" if set(e.get("categories", [])) & {"connectivity"} else "ts"
        add("sf", name, group, surf, e["phrasings"], [], False)
    for e in apple["apps"]:
        n = e["name"]
        add("app", n, "app:" + n, "d", [f"the {n} app", f"the {n} icon", f"{n} in the Dock"], [f"open {n}", f"launch {n}"], True)
        out[-1]["file"] = e["file"]
    for s in SPLITS:
        POOLS[s] = {}
    for ic in out:
        POOLS[ic["split"]].setdefault(ic["set"], []).append(ic)
    STATS.update(missing=missing, total=len(out))


def describe():
    load()
    rows = {s: {k: len(v) for k, v in sorted(POOLS[s].items())} for s in SPLITS}
    return {"icons": rows, "unresolved_names": STATS["missing"]}


CSS = """
.imb{flex:none;height:24px;display:flex;align-items:center;padding:0 12px;font-size:13px;color:#fff;background:rgba(22,22,28,.6)}
.imb.light{color:#111;background:rgba(246,246,248,.74)}.imb .mi{margin-right:16px}.imb .ap{font-weight:700}
.istage{flex:1 1 0;min-height:0;display:flex;flex-direction:column}
.iwin{flex:1 1 0;min-height:0;display:flex;flex-direction:column;background:var(--bg);overflow:hidden;color:var(--fg)}
.iwin.float{border-radius:10px;box-shadow:0 22px 70px rgba(0,0,0,.42),0 0 0 1px rgba(0,0,0,.28)}
.bar{flex:none;display:flex;align-items:center;background:var(--bg2);border-bottom:1px solid var(--bd);padding:0 12px}
.bar.v{flex-direction:column;border-bottom:none;padding:10px 0;background:var(--bg1)}
.bar.bot{border-bottom:none;border-top:1px solid var(--bd);background:var(--bg1)}
.cl{display:flex;align-items:center;flex:none}.bar.v .cl{flex-direction:column}
.ib{flex:none;display:flex;align-items:center;justify-content:center;border-radius:var(--r);color:var(--fg1)}
.ib.border{border:1px solid var(--bd2);background:var(--bg)}.ib.soft{background:var(--bg3)}
.ib.on{background:var(--acs2);color:var(--ac)}.ib.dis>*{opacity:.3}
.seg{display:flex;flex:none;border:1px solid var(--bd2);border-radius:var(--r);overflow:hidden;background:var(--bg)}
.seg .ib{border-radius:0}.seg .ib+.ib{border-left:1px solid var(--bd2)}.bar.v .seg{flex-direction:column}
.bar.v .seg .ib+.ib{border-left:none;border-top:1px solid var(--bd2)}
.g{display:block;flex:none}.g svg{width:100%;height:100%;display:block}.g.ms svg{fill:currentColor}img.g{opacity:.86}
.tl{display:flex;gap:8px;margin-right:14px;flex:none}.tl i{width:12px;height:12px;border-radius:50%;display:block}
.sk{height:8px;border-radius:4px;background:var(--bg4);flex:none}.vsep{width:1px;height:18px;background:var(--bd2);flex:none}
.hsep{height:1px;width:18px;background:var(--bd2);flex:none}
.pill{height:22px;border-radius:6px;background:var(--bg3);border:1px solid var(--bd);flex:none;display:flex;align-items:center;padding:0 8px}
.side{flex:none;display:flex;flex-direction:column;background:var(--bg1);padding:8px 8px;overflow:hidden}
.srow{display:flex;align-items:center;gap:8px;border-radius:6px;padding:0 4px;flex:none}.srow.sel{background:var(--bg4)}
.tabs{flex:none;display:flex;align-items:flex-end;background:var(--bg2);border-bottom:1px solid var(--bd);padding:0 10px}
.tab{flex:none;display:flex;align-items:center;justify-content:center;color:var(--fg1);border-radius:6px 6px 0 0}
.tab.on{background:var(--bg);box-shadow:0 0 0 1px var(--bd)}.tab.dis>*{opacity:.3}
.tabs.pilltabs{align-items:center}.tabs.pilltabs .tab{border-radius:6px}.tabs.pilltabs .tab.on{background:var(--acs2)}
.idock{flex:none;align-self:center;display:flex;align-items:flex-end;margin:5px 0 6px;border-radius:14px;
background:rgba(240,240,244,.32);box-shadow:0 0 0 1px rgba(255,255,255,.25),0 6px 20px rgba(0,0,0,.25)}
.dk{flex:none;display:flex;align-items:center;justify-content:center;position:relative}
.dk img{width:100%;height:100%;display:block}.dk.run:after{content:"";position:absolute;bottom:-4px;left:50%;width:3px;height:3px;
margin-left:-1.5px;border-radius:50%;background:rgba(255,255,255,.85)}.dk.dis img{opacity:.4}
.mbi{flex:none;display:flex;align-items:center;justify-content:center;border-radius:4px}.mbi.on{background:rgba(127,127,127,.4)}
.mbi.dis>*{opacity:.35}.mbi img.g{opacity:1}
.cont{flex:1 1 0;min-width:0;min-height:0;overflow:hidden;padding:18px 22px;display:flex;flex-direction:column;gap:12px}
.card{border:1px solid var(--bd);border-radius:8px;background:var(--bg1);flex:none}
.num{color:var(--fg2);font-size:12px;white-space:nowrap}
"""


class Screen:
    def __init__(self, seed, split, index):
        load()
        self.rng = rng = random.Random(f"iconscreens:{seed}:{split}:{index}")
        self.split = split
        self.variant = rng.choice(sorted(v for v, s in VARIANTS.items() if s == split))
        self.W, self.H, _ = rng.choices(SIZES, [s[2] for s in SIZES])[0]
        self.vh = round(self.H * 1280 / self.W)
        self.dsf = self.W / 1280
        self.theme = pick_theme(rng, split)
        self.style = pick_style(rng, "mac")
        self.dark = self.theme["mode"] == "dark"
        pools = POOLS[split]
        web = [s for s in WEB_SETS if len(pools.get(s, [])) >= 30]
        self.kind = "mac" if (rng.random() < 0.5 and pools.get("sf")) or not web else "web"
        self.iset = "sf" if self.kind == "mac" else rng.choice(web)
        self.sf_weight = rng.choices(["light", "regular", "semibold"], [1, 4, 2])[0]
        self.sw = rng.choice([1.5, 1.75, 2])
        self.targets = {}
        self.groups, self.placed, self.dupd = set(), [], set()
        self.dups = rng.choices([0, 1, 2], [55, 30, 15])[0]
        self.menubar = rng.random() < 0.75
        self.dock = bool(pools.get("app")) and rng.random() < 0.55
        self.floating = rng.random() < 0.6

    # ---- choosing icons ---------------------------------------------------------------------
    def pick(self, iset, surf, n, region, hard=False):
        rng = self.rng
        cands = [ic for ic in POOLS[self.split].get(iset, []) if ic["group"] not in self.groups and (not hard or surf in ic["surf"])]
        w = [(6 if surf in ic["surf"] else 1) * (4 if ic["hand"] else 1) for ic in cands]
        out = []
        while len(out) < n and cands:
            if self.dups and rng.random() < 0.2:
                prev = [ic for ic, reg in self.placed if reg != region and ic["set"] == iset and ic["id"] not in self.dupd
                        and ic["hand"] and ic not in out]
                if prev:
                    ic = rng.choice(prev)
                    self.dupd.add(ic["id"])
                    self.dups -= 1
                    out.append(ic)
                    continue
            ic = cands[rng.choices(range(len(cands)), w)[0]]
            self.groups.add(ic["group"])
            out.append(ic)
            keep = [j for j, c in enumerate(cands) if c["group"] != ic["group"]]
            cands, w = [cands[j] for j in keep], [w[j] for j in keep]
        self.placed += [(ic, region) for ic in out]
        return out

    # ---- drawing ----------------------------------------------------------------------------
    def glyph(self, ic, px, white=None):
        st = f"width:{px}px;height:{px}px"
        if ic["set"] == "lucide":
            return icons.svg(ic["name"], size=px, sw=self.sw)
        if ic["set"] == "sf":
            res = 96 if px * self.dsf > 40 else 48
            col = "white" if (self.dark if white is None else white) else "black"
            path = os.path.join(ASSETS, "apple", "symbols", f"{ic['name']}.{self.sf_weight}.{res}.{col}.png")
            return f'<img class="g" style="{st}" src="data:image/png;base64,{_b64(path)}">'
        if ic["set"] == "app":
            return f'<img src="data:image/png;base64,{_app_b64(os.path.join(ASSETS, "apple", ic["file"]))}">'
        return f'<span class="g{" ms" if ic["set"] == "material" else ""}" style="{st}">{_web_svg(ic["set"], ic["name"])}</span>'

    def reg(self, ic, region, role, surface, state):
        tid = len(self.targets) + 1
        self.targets[tid] = {"icon": ic, "region": region, "role": role, "surface": surface, "state": state}
        return f' data-t="{tid}"'

    def state(self, p_dis=0.07, p_on=0.08):
        r = self.rng.random()
        return "dis" if r < p_dis else "on" if r < p_dis + p_on else ""

    def btn(self, ic, region, box, px, kind, surface="toolbar", role="button", cls="ib", white=None):
        st = self.state()
        return (f'<div class="{cls} {kind} {st}"{self.reg(ic, region, role, surface, st or "normal")} '
                f'style="width:{box}px;height:{box}px">{self.glyph(ic, px, white)}</div>')

    def clusters(self, items, region, box, px, kind, gap, surface, vertical=False):
        """Buttons in groups of 1-5; returns the groups' HTML."""
        rng, out, i = self.rng, [], 0
        while i < len(items):
            k = rng.randint(1, 5)
            part = items[i:i + k]
            i += k
            inner = "".join(self.btn(ic, region, box, px, "" if kind == "seg" else kind, surface) for ic in part)
            if kind == "seg" and len(part) > 1:
                out.append(f'<div class="seg">{inner}</div>')
            else:
                out.append(f'<div class="cl" style="gap:{gap}px">{inner}</div>')
        return out

    def sk(self, lo=30, hi=120, h=8):
        return f'<div class="sk" style="width:{self.rng.randint(lo, hi)}px;height:{h}px"></div>'

    def toolbar(self, region, n, big=True, lights=False):
        rng = self.rng
        box = rng.randint(22, 34) if big else rng.randint(20, 27)
        px = max(13, round(box * rng.uniform(0.55, 0.74)))
        kind = rng.choice(["", "", "", "border", "soft", "seg"])
        gap = rng.choice([0, 2, 4, 6, 8, 12]) if kind != "border" else rng.choice([4, 6, 8])
        cl = self.clusters(self.pick(self.iset, "t", n, region), region, box, px, kind, gap, "toolbar")
        sep = rng.choice(['<div class="vsep" style="margin:0 8px"></div>', '<div style="width:14px"></div>', '<div style="width:22px"></div>'])
        tl = ('<div class="tl"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>'
              if lights else "")
        fill = rng.choice(["title", "pill", "sp"])
        mid = {"title": f'<div class="sp"></div><b style="font-size:13px">{rng.choice(["Untitled", "Document", "Project", "Window"])} {rng.randint(2, 40)}</b><div class="sp"></div>',
               "pill": f'<div class="sp"></div><div class="pill" style="width:{rng.randint(160, 320)}px">{self.sk(40, 110)}</div><div class="sp"></div>',
               "sp": '<div class="sp"></div>'}[fill]
        if self.kind == "web" and big:
            brand = f'<div style="width:22px;height:22px;border-radius:6px;background:var(--ac);margin-right:12px;flex:none"></div>{self.sk(50, 90, 10)}<div style="width:18px"></div>{self.sk(30, 60)}<div class="sp"></div>'
            body = brand + sep.join(cl)
        else:
            cut = rng.randint(0, len(cl))
            body = sep.join(cl[:cut]) + mid + sep.join(cl[cut:])
        h = box + rng.choice([8, 10, 14, 18])
        return f'<div class="bar" style="height:{h}px">{tl}{body}</div>'

    def rail(self, region, n, side="left", cols=1):
        rng = self.rng
        box = rng.randint(24, 36) if cols == 1 else rng.randint(22, 30)
        px = max(14, round(box * rng.uniform(0.52, 0.7)))
        kind = rng.choice(["", "", "soft", "border"]) if cols == 1 else rng.choice(["", "border", "seg"])
        gap = rng.choice([2, 4, 6, 10])
        items = self.pick(self.iset, "s" if cols == 1 else "t", n, region)
        bd = f"border-{'right' if side == 'left' else 'left'}:1px solid var(--bd)"
        if cols > 1:
            cells = "".join(self.btn(ic, region, box, px, "" if kind == "seg" else kind, "sidebar") for ic in items)
            return (f'<div class="bar v" style="{bd};padding:10px 8px"><div style="display:grid;grid-template-columns:repeat({cols},{box}px);'
                    f'gap:{0 if kind == "seg" else gap}px">{cells}</div></div>')
        cut = rng.randint(max(1, len(items) - 3), len(items))
        top = "".join(self.clusters(items[:cut], region, box, px, kind, gap, "sidebar", True))
        bot = "".join(self.clusters(items[cut:], region, box, px, kind, gap, "sidebar", True))
        return (f'<div class="bar v" style="width:{box + rng.choice([10, 14, 20])}px;gap:{gap}px;{bd}">{top}<div class="sp"></div>{bot}</div>')

    def rows(self, region, n):
        rng = self.rng
        box, rh = rng.randint(18, 24), rng.randint(24, 30)
        px = max(13, box - rng.choice([2, 4, 6]))
        sel = rng.randrange(max(1, n))
        out = []
        for i, ic in enumerate(self.pick(self.iset, "s", n, region)):
            if i and rng.random() < 0.18:
                out.append(f'<div style="height:{rh - 6}px;display:flex;align-items:flex-end;padding:0 4px 4px">{self.sk(30, 70, 6)}</div>')
            out.append(f'<div class="srow{" sel" if i == sel else ""}" style="height:{rh}px">'
                       f'{self.btn(ic, region, box, px, "", "sidebar")}{self.sk(40, 120)}</div>')
        return f'<div class="side" style="width:{rng.randint(160, 230)}px;border-right:1px solid var(--bd);gap:2px">{"".join(out)}</div>'

    def tabs(self, region, n):
        rng = self.rng
        w, h = rng.randint(26, 36), rng.randint(20, 28)
        px = max(13, min(h - 6, rng.randint(14, 18)))
        pills = rng.random() < 0.4
        on = rng.randrange(max(1, n))
        out = []
        for i, ic in enumerate(self.pick(self.iset, "b", n, region)):
            st = "on" if i == on else ("dis" if rng.random() < 0.06 else "")
            out.append(f'<div class="tab {st}"{self.reg(ic, region, "tab", "tabbar", st or "normal")} style="width:{w}px;height:{h}px">{self.glyph(ic, px)}</div>')
        return (f'<div class="tabs{" pilltabs" if pills else ""}" style="height:{h + (10 if pills else 6)}px;gap:{rng.choice([2, 4, 8])}px;'
                f'justify-content:{rng.choice(["flex-start", "center", "flex-start"])}">{"".join(out)}</div>')

    def inspector(self, region, n):
        rng = self.rng
        box = rng.randint(22, 28)
        px = max(13, round(box * rng.uniform(0.55, 0.7)))
        kind = rng.choice(["", "seg", "soft"])
        strip = "".join(self.clusters(self.pick(self.iset, "t", n, region), region, box, px, kind, rng.choice([2, 4, 8]), "inspector"))
        form = "".join(f'<div style="display:flex;gap:10px;align-items:center;height:26px">{self.sk(40, 80)}<div class="pill" style="flex:1 1 0"></div></div>'
                       for _ in range(rng.randint(4, 9)))
        return (f'<div class="side" style="width:{rng.randint(210, 260)}px;border-left:1px solid var(--bd);gap:10px">'
                f'<div style="display:flex;justify-content:center;gap:6px;padding:2px 0 8px;border-bottom:1px solid var(--bd)">{strip}</div>{form}</div>')

    def bottom(self, region, n):
        rng = self.rng
        box = rng.randint(16, 22)
        px = max(12, box - rng.choice([2, 4]))
        cl = self.clusters(self.pick(self.iset, "t", n, region), region, box, px, "", rng.choice([2, 6, 10]), "bottombar")
        cut = rng.randint(0, len(cl))
        return (f'<div class="bar bot" style="height:{box + rng.choice([6, 8, 10])}px;gap:10px">{"".join(cl[:cut])}{self.sk(60, 160, 6)}'
                f'<div class="sp"></div><span class="num">{rng.randint(2, 900)} / {rng.randint(900, 4000)}</span>{"".join(cl[cut:])}</div>')

    def content(self):
        rng = self.rng
        kind = rng.choice(["doc", "grid", "list"])
        if kind == "doc":
            body = "".join(f'<div class="sk" style="width:{rng.randint(35, 98)}%;height:{rng.choice([8, 8, 8, 14])}px"></div>' for _ in range(rng.randint(14, 30)))
        elif kind == "grid":
            cw, chh = rng.randint(120, 200), rng.randint(90, 150)
            cards = "".join(f'<div class="card" style="width:{cw}px;height:{chh}px"></div>' for _ in range(rng.randint(8, 24)))
            body = f'<div style="display:flex;flex-wrap:wrap;gap:14px">{cards}</div>'
        else:
            body = "".join(f'<div style="display:flex;align-items:center;gap:18px;height:28px;border-bottom:1px solid var(--bd);flex:none">'
                           f'{self.sk(90, 260)}<div class="sp"></div><span class="num">{rng.randint(1, 28)}.{rng.randint(1, 12):02d}.{rng.randint(2019, 2026)}</span>'
                           f'<span class="num" style="width:60px;text-align:right">{rng.randint(1, 980)} {rng.choice(["KB", "MB"])}</span></div>'
                           for _ in range(rng.randint(10, 22)))
        return f'<div class="cont">{body}</div>'

    def menu_strip(self):
        rng = self.rng
        light = not self.dark and rng.random() < 0.6
        ih, px = rng.randint(18, 22), rng.randint(13, 16)
        pad, gap = rng.randint(2, 5), rng.choice([2, 4, 6, 10])
        items = self.pick("sf" if POOLS[self.split].get("sf") else self.iset, "m", rng.randint(5, 9), "the menu bar", hard=True)
        out = []
        for ic in items:
            st = self.state(0.05, 0.07)
            out.append(f'<div class="mbi {st}"{self.reg(ic, "the menu bar", "status item", "menubar", st or "normal")} '
                       f'style="width:{px + 2 * pad}px;height:{ih}px">{self.glyph(ic, px, white=not light)}</div>')
        app = rng.choice(["Finder", "Preview", "Notes", "Pages", "Viewer", "Studio"])
        menus = "".join(f'<span class="mi">{m}</span>' for m in ["File", "Edit", "View", "Go", "Window", "Help"][:rng.randint(4, 6)])
        clock = f"{rng.choice(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])} {rng.randint(1, 28)} {rng.choice(['Mar', 'Jun', 'Sep', 'Nov'])}  {rng.randint(8, 18)}:{rng.randint(10, 59)}"
        return (f'<div class="imb{" light" if light else ""}"><span class="mi ap">{app}</span>{menus}<div class="sp"></div>'
                f'<div style="display:flex;align-items:center;gap:{gap}px;margin-right:12px">{"".join(out)}</div><span>{clock}</span></div>')

    def dock_row(self):
        rng = self.rng
        tile, gap = rng.randint(28, 36), rng.choice([3, 4, 6, 8])
        out = []
        for ic in self.pick("app", "d", rng.randint(7, 13), "the Dock"):
            st = "run" if rng.random() < 0.3 else ""
            out.append(f'<div class="dk {st}"{self.reg(ic, "the Dock", "dock item", "dock", "normal")} style="width:{tile}px;height:{tile}px">{self.glyph(ic, tile)}</div>')
        return f'<div class="idock" style="gap:{gap}px;padding:{rng.choice([4, 5, 6])}px {rng.choice([6, 8, 10])}px">{"".join(out)}</div>'

    # ---- the page ---------------------------------------------------------------------------
    def html(self):
        rng, v = self.rng, self.variant
        top = self.menu_strip() if self.menubar else ""
        parts, left, right, bot = [], "", "", ""
        unified = rng.random() < 0.6
        if not unified:
            parts.append('<div class="bar" style="height:28px"><div class="tl"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i>'
                         f'<i style="background:#28c840"></i></div><div class="sp"></div><b style="font-size:13px">{rng.choice(["Untitled", "Document", "Project"])} {rng.randint(2, 40)}</b>'
                         '<div class="sp"></div><div style="width:52px"></div></div>')
        parts.append(self.toolbar("the toolbar", rng.randint(6, 16), lights=unified))
        if v == "rail":
            left = self.rail("the sidebar", rng.randint(5, 10))
            if rng.random() < 0.5:
                parts.append(self.tabs("the tab bar", rng.randint(4, 8)))
            if rng.random() < 0.4:
                bot = self.bottom("the bottom bar", rng.randint(3, 6))
        elif v == "rows":
            left = self.rows("the sidebar", rng.randint(6, 12))
            if rng.random() < 0.45:
                parts.append(self.toolbar("the formatting bar", rng.randint(5, 10), big=False))
            if rng.random() < 0.45:
                parts.append(self.tabs("the tab bar", rng.randint(4, 8)))
        elif v == "inspector":
            left = self.rows("the sidebar", rng.randint(6, 10)) if rng.random() < 0.5 else self.rail("the sidebar", rng.randint(5, 9))
            right = self.inspector("the inspector", rng.randint(4, 7))
            if rng.random() < 0.4:
                bot = self.bottom("the bottom bar", rng.randint(3, 6))
        elif v == "palette":
            left = self.rail("the tool palette", rng.randint(8, 14), cols=2)
            parts.append(self.tabs("the tab bar", rng.randint(4, 8)))
            if rng.random() < 0.5:
                right = self.inspector("the inspector", rng.randint(4, 7))
        else:
            parts.append(self.toolbar("the formatting bar", rng.randint(6, 12), big=False))
            right = self.rail("the right-hand bar", rng.randint(5, 10), side="right")
        dock = self.dock_row() if self.dock else ""
        pad = (f"{rng.randint(14, 40)}px {rng.randint(40, 150)}px {rng.randint(10, 36)}px {rng.randint(40, 150)}px" if self.floating else "0")
        vars_ = dict(self.theme["vars"])
        vars_.update(self.style["vars"])
        hue = rng.randint(0, 359)
        vars_["--wall"] = (f"linear-gradient({rng.randint(110, 160)}deg,hsl({hue} {rng.randint(35, 60)}% {rng.randint(28, 46)}%),"
                           f"hsl({(hue + rng.randint(30, 80)) % 360} {rng.randint(40, 65)}% {rng.randint(14, 26)}%))")
        vars_["--font"] = f'"{self.style["font"]}"'
        vars_["--mono"] = f'"{self.style["mono"]}"'
        root = ";".join(f"{k}:{val}" for k, val in vars_.items())
        return ('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/base.css">'
                f'<style>:root{{{root}}}{CSS}</style></head><body><div id="desk">{top}'
                f'<div class="istage" style="padding:{pad}"><div class="iwin{" float" if self.floating else ""}">{"".join(parts)}'
                f'<div style="flex:1 1 0;min-height:0;display:flex">{left}{self.content()}{right}</div>{bot}</div></div>{dock}</div></body></html>')

    def meta(self, seed, index):
        return {"seed": seed, "split": self.split, "screen": index, "archetype": ARCH, "variant": self.variant,
                "theme_family": self.theme["family"], "accent": self.theme["accent"], "font": self.style["font"],
                "density": self.style["density"], "chrome": "mac", "os_bars": self.menubar, "floating": self.floating,
                "overlay": "none", "dpr": round(self.dsf, 4), "style": self.kind, "icon_set": self.iset}

    # ---- cases ------------------------------------------------------------------------------
    def cases(self, report, rng, per_screen=8):
        """(cases, elements) from the page report: one request per chosen icon, never ambiguous."""
        d = self.dsf
        m = {x["t"]: x for x in report["targets"] if x["t"] in self.targets}
        vis = [t for t, x in m.items() if x["part"]]
        valid = sorted(t for t, x in m.items() if x["full"] and x["top"] and x["w"] >= 8 and x["h"] >= 8)
        owners = {}
        for t in vis:
            ic = self.targets[t]["icon"]
            for p in ic["nouns"] + ic["actions"]:
                owners.setdefault(norm(p), set()).add(ic["id"])

        def box(t):
            x = m[t]
            return [max(0, round(x["x"] * d)), max(0, round(x["y"] * d)),
                    min(self.W, round((x["x"] + x["w"]) * d)), min(round(report["H"] * d), round((x["y"] + x["h"]) * d))]

        def element(t):
            g = self.targets[t]
            return {"role": g["role"], "label": g["icon"]["label"], "ui_type": "icon", "label_visible": False,
                    "icon": g["icon"]["id"], "icon_set": g["icon"]["set"], "region": g["region"]}

        elements = [dict(element(t), bbox=box(t)) for t in valid]
        cands = []
        for t in valid:
            g = self.targets[t]
            ic = g["icon"]
            twins = [o for o in vis if o != t and self.targets[o]["icon"]["id"] == ic["id"]]
            if any(self.targets[o]["region"] == g["region"] for o in twins):
                continue
            nouns = [p for p in ic["nouns"] if owners[norm(p)] == {ic["id"]}]
            acts = [p for p in ic["actions"] if owners[norm(p)] == {ic["id"]}]
            if twins:
                nouns = [p for p in nouns if not p.endswith("in the Dock")]
            if nouns or acts:
                cands.append((t, nouns, acts, bool(twins)))
        rng.shuffle(cands)
        cands.sort(key=lambda c: not c[3])       # requests that need the position come first
        by_region = {}
        for c in cands[2:] if len(cands) > 2 else []:
            by_region.setdefault(self.targets[c[0]]["region"], []).append(c)
        order = cands[:2]
        while any(by_region.values()):           # then round-robin over the surfaces
            for r in sorted(by_region):
                if by_region[r]:
                    order.append(by_region[r].pop())
        out, said = [], set()
        for t, nouns, acts, twin in order:
            if len(out) >= per_screen:
                break
            g = self.targets[t]
            func = bool(acts) and (not nouns or rng.random() < 0.4)
            if func:
                phrase = rng.choice(acts) + (rng.choice([", using the one in {}", " from {}", " in {}"]).format(g["region"]) if twin else "")
                wrap, slot = rng.choice(FUNC_WRAP[self.split]), "i"
            else:
                phrase = rng.choice(nouns) + (f" in {g['region']}" if twin else "")
                wrap, slot = rng.choice(DIRECT_WRAP[self.split]), "r"
            text = wrap.replace("{" + slot + "}", phrase).replace("{" + slot.upper() + "}", upper_first(phrase))
            if text.lower() in said:
                continue
            said.add(text.lower())
            b = box(t)
            w1, h1 = m[t]["w"], m[t]["h"]
            out.append({"tid": t, "instruction": text, "bbox": b, "element": element(t),
                        "tags": {"ui_type": "icon", "instruction_kind": "functional" if func else "direct",
                                 "size": size_bucket((b[2] - b[0]) * (b[3] - b[1]) / (self.W * self.H)),
                                 "disambiguation": "region" if twin else "none", "icon_set": g["icon"]["set"],
                                 "surface": g["surface"], "state": g["state"],
                                 "w1280": round(w1, 1), "h1280": round(h1, 1)}})
        out.sort(key=lambda c: c["tid"])
        return out, elements
