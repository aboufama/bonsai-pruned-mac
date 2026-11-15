"""Screen context: target registration plus the component helpers archetypes are built from.

Every helper returns an HTML string. Anything a user could be asked to point at is registered
with reg(), which hands back a ` data-t="N"` attribute; after rendering, the page script reads
the box of every element carrying one.
"""
import html as _html
from dataclasses import dataclass, field

from . import icons, vocab
from .data import Data, COLORS
from .splits import LABEL_SPLIT, is_generic, norm, stable_hash


def esc(text):
    return _html.escape(str(text), quote=True)


# small affordance glyphs that are not part of the icon set (never targets by themselves)
def _raw(path, cls="", w=10):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" style="width:{w}px;height:{w}px;flex:none;fill:none;stroke:currentColor;'
            f'stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round">{path}</svg>')


CHEV_D = _raw('<path d="m6 9 6 6 6-6"/>')
CHEV_R = _raw('<path d="m9 6 6 6-6 6"/>')
CHEV_U = _raw('<path d="m6 15 6-6 6 6"/>')
CHEV_L = _raw('<path d="m15 6-6 6 6 6"/>')
TICK = '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
CROSS = _raw('<path d="M6 6l12 12M18 6 6 18"/>', w=9)
TICK_S = _raw('<path d="M5 12.5l4.5 4.5L19 7.5"/>', w=11)


@dataclass
class Target:
    tid: int
    role: str
    noun: str
    label: str            # visible text; for an icon, the name of what it does
    ui: str               # "text" or "icon"
    icon: str = None      # canonical glyph name when the element is an icon from the set
    cid: str = None
    region: str = None    # e.g. "the sidebar"; used to tell duplicates apart
    row: str = None       # e.g. "report.pdf"; the list entry this control belongs to
    obj: str = None       # what the action applies to, for functional wording
    refs: list = None     # explicit ways to refer to the element instead of label + noun
    state: bool = None    # for toggles: currently on?
    intents: list = field(default_factory=list)
    fam: str = None
    direct: bool = True
    name: str = None      # for icons: what the control is called ("account"), defaults to the label
    foreign: bool = False  # visible text label owned by another split: drawn, but never a target


class Ctx:
    def __init__(self, rng, split):
        self.rng, self.split = rng, split
        self.d = Data(rng, split)
        self.targets = {}
        self._n = 0
        self._lab, self._ico, self._deco = {}, {}, {}
        # elements overlays can attach to
        self.anchors = {"menubar": [], "row": [], "icon": [], "select": [], "more": [], "account": []}
        self.menus = {}        # menubar concept id -> list of menu entries
        self.ctxmenu = None    # entries for a context menu on a row, set by the archetype
        self.ctxobj = "this item"
        self.options = {}      # select tid -> list of option labels

    # ---- vocabulary -----------------------------------------------------------------------
    def view(self, cid):
        return vocab.CONCEPTS[cid].views[self.split]

    def has(self, cid, icon=False):
        v = self.view(cid)
        return bool(v.labels) and (not icon or bool(v.icons))

    def lab(self, cid):
        if cid not in self._lab:
            labels = self.view(cid).labels
            # a concept this split has no label for is drawn with another split's label; reg() then
            # refuses to make it a target
            self._lab[cid] = self.rng.choice(labels) if labels else vocab.CONCEPTS[cid].labels[0]
        return self._lab[cid]

    def ico(self, cid):
        if cid not in self._ico:
            names = self.view(cid).icons
            self._ico[cid] = self.rng.choice(names) if names else None
        return self._ico[cid]

    def avail(self, cids, icon=False):
        return [c for c in cids if self.has(c, icon)]

    def pick(self, cids, k, icon=False):
        """Up to k available concepts, keeping their listed order."""
        ok = self.avail(cids, icon)
        if len(ok) <= k:
            return ok
        keep = set(self.rng.sample(range(len(ok)), k))
        return [c for i, c in enumerate(ok) if i in keep]

    # ---- registration ---------------------------------------------------------------------
    def reg(self, role, noun, label, *, ui="text", icon=None, cid=None, region=None, row=None, obj=None,
            refs=None, state=None, func=True, direct=True, anchor=None):
        self._n += 1
        c = vocab.CONCEPTS.get(cid) if cid else None
        own = LABEL_SPLIT.get(norm(label))
        foreign = ui == "text" and own is not None and own != self.split and not is_generic(label)
        self.targets[self._n] = Target(
            tid=self._n, role=role, noun=noun, label=str(label), ui=ui, icon=icon, cid=cid, region=region,
            row=row, obj=obj or (c.o if c else None), refs=refs, state=state,
            intents=list(c.views[self.split].intents) if (c and func) else [], fam=c.fam if c else None,
            direct=direct, name=c.names.get(str(label)) if c else None, foreign=foreign)
        if anchor:
            self.anchors[anchor].append(self._n)
        return f' data-t="{self._n}"'

    @property
    def last(self):
        return self._n

    def own(self, text, cls=""):
        """Static text that names the most recently registered target (e.g. a field's caption)."""
        return f'<span class="{cls}" data-o="{self._n}">{esc(text)}</span>'

    # ---- icons ----------------------------------------------------------------------------
    def deco(self, *names, size=None, cls="", blank=False):
        """A decorative icon drawn from the candidates this split may use; '' if none."""
        key = names
        if key not in self._deco:
            ok = [n for n in names if icons.exists(n) and icons.icon_split(n) == self.split]
            self._deco[key] = self.rng.choice(ok) if ok else None
        name = self._deco[key]
        if not name:
            return f'<span style="width:var(--is);height:var(--is);flex:none"></span>' if blank else ""
        return icons.svg(name, cls, size)

    def deco_any(self, names, size=None):
        """A fresh random decorative icon from a list (not cached)."""
        ok = [n for n in names if icons.exists(n) and icons.icon_split(n) == self.split]
        return icons.svg(self.rng.choice(ok), size=size) if ok else ""

    def deco_some(self, names, k, size=None):
        """Up to k different decorative icons from a list."""
        ok = sorted({icons.canon(n) for n in names if icons.exists(n) and icons.icon_split(n) == self.split})
        self.rng.shuffle(ok)
        return [icons.svg(n, size=size) for n in ok[:k]]

    # ---- buttons --------------------------------------------------------------------------
    def ibtn(self, cid, region, *, row=None, obj=None, cls="", noun="button", on=False, anchor="icon",
             size=None, func=True, state=None, tag="div"):
        """Icon-only button for a concept; '' when the split has no glyph for it."""
        if not self.has(cid, icon=True):
            return ""
        name = self.ico(cid)
        attr = self.reg("button", noun, self.lab(cid), ui="icon", icon=name, cid=cid, region=region, row=row,
                        obj=obj, func=func, anchor=anchor, state=state)
        return f'<{tag} class="ib {cls}{" on" if on else ""}"{attr}>{icons.svg(name, size=size)}</{tag}>'

    def ibtns(self, cids, region, sep_every=0, **kw):
        out = []
        for i, cid in enumerate(cids):
            if cid == "|":
                out.append('<div class="vsep"></div>')
                continue
            out.append(self.ibtn(cid, region, **kw))
        return "".join(out)

    def tbtn(self, cid, region, *, cls="", icon=False, row=None, obj=None, noun="button", caret=False,
             anchor=None, func=True, kbd=None):
        """Text button for a concept; '' when the split has no label for it."""
        if not self.has(cid):
            return ""
        label = self.lab(cid)
        attr = self.reg("button", noun, label, cid=cid, region=region, row=row, obj=obj, anchor=anchor, func=func)
        ico = icons.svg(self.ico(cid)) if icon and self.ico(cid) else ""
        tail = CHEV_D if caret else ""
        if kbd:
            tail += f'<span class="kb">{esc(kbd)}</span>'
        return f'<div class="btn {cls}"{attr}>{ico}<span>{esc(label)}</span>{tail}</div>'

    def lbtn(self, label, region, *, cls="", noun="button", icon_html="", refs=None, row=None, anchor=None):
        """Text button with a free label that has no concept (direct instructions only)."""
        attr = self.reg("button", noun, label, region=region, refs=refs, row=row, anchor=anchor)
        return f'<div class="btn {cls}"{attr}>{icon_html}<span>{esc(label)}</span></div>'

    # ---- inputs ---------------------------------------------------------------------------
    def field(self, label, value="", *, ph=None, region=None, cid=None, w=None, cls="", noun="field",
              above=True, area=0, icon_html="", focus=False, tail=""):
        """Fake text input. With above=True the caption sits over the box, else it is the placeholder."""
        attr = self.reg("field", noun, label, cid=cid, region=region)
        tid = self._n
        if value:
            content = f'<span class="el f1">{esc(value)}</span>'
        else:
            content = f'<span class="el f1 ph">{esc(ph if ph is not None else label)}</span>'
        style = (f"width:{w}px;" if w else "") + (f"min-height:{area}px;" if area else "")
        box = (f'<div class="inp {cls}{" area" if area else ""}{" foc" if focus else ""}"{attr} style="{style}">'
               f'{icon_html}{content}{tail}</div>')
        if above:
            return f'<div class="col" style="min-width:0"><div class="lbl" data-o="{tid}">{esc(label)}</div>{box}</div>'
        return box

    def search(self, region, *, w=None, cls="", cid="search", ph=None, kbd=None):
        if not self.has(cid):
            return ""
        label = self.lab(cid)
        ico = self.deco("search", "text-search", "scan-search", "file-search", "folder-search")
        tail = f'<span class="kb">{esc(kbd)}</span>' if kbd else ""
        attr = self.reg("field", self.rng.choice(["field", "box", "bar"]), label, cid=cid, region=region)
        text = ph or (label + "…" if self.rng.random() < 0.5 else label)
        style = f"width:{w}px;" if w else ""
        return f'<div class="inp {cls}"{attr} style="{style}">{ico}<span class="el f1 ph">{esc(text)}</span>{tail}</div>'

    def select(self, label, value, *, options=None, region=None, cid=None, w=None, above=True, cls="", noun="dropdown",
               refs=None, row=None):
        attr = self.reg("select", noun, label, cid=cid, region=region, anchor="select" if options else None, refs=refs, row=row)
        tid = self._n
        if options:
            self.options[tid] = list(options)
        style = f"width:{w}px;" if w else ""
        box = f'<div class="inp {cls}"{attr} style="{style}"><span class="el f1">{esc(value)}</span>{CHEV_D}</div>'
        if above:
            return f'<div class="col" style="min-width:0"><div class="lbl" data-o="{tid}">{esc(label)}</div>{box}</div>'
        return box

    def check(self, label, on=False, *, region=None, cid=None, radio=False, row=None, noun=None, cls=""):
        noun = noun or ("option" if radio else "checkbox")
        attr = self.reg("radio" if radio else "checkbox", noun, label, cid=cid, region=region, state=on, row=row)
        return (f'<div class="chk{" rd" if radio else ""}{" on" if on else ""} {cls}"{attr}>'
                f'<span class="box">{"" if radio else TICK}</span><span>{esc(label)}</span></div>')

    def box(self, label, on=False, *, region=None, row=None, cid=None, refs=None):
        """A bare checkbox whose meaning comes from its row (label is the row's name)."""
        attr = self.reg("checkbox", "checkbox", label, ui="icon", region=region, row=row, cid=cid, state=on, refs=refs)
        return f'<div class="chk{" on" if on else ""}"{attr}><span class="box">{TICK}</span></div>'

    def toggle(self, label, on=False, *, region=None, cid=None, sq=False):
        """Just the switch; pair it with own(label) for the caption."""
        attr = self.reg("switch", self.rng.choice(["toggle", "switch"]), label, cid=cid, region=region, state=on)
        return f'<div class="tog{" on" if on else ""}{" sq" if sq else ""}"{attr}></div>'

    def toggle_row(self, label, on=False, *, region=None, cid=None, desc=None, cls=""):
        sw = self.toggle(label, on, region=region, cid=cid)
        tid = self._n
        text = f'<div class="col f1" style="min-width:0"><span data-o="{tid}" class="m">{esc(label)}</span>'
        if desc:
            text += f'<span class="mut sm">{esc(desc)}</span>'
        return f'<div class="row g12 {cls}">{text}</div>{sw}</div>'

    def slider(self, label, frac, *, region=None, cid=None, w=None):
        attr = self.reg("slider", "slider", label, cid=cid, region=region)
        style = f"width:{w}px;flex:none;" if w else ""
        pct = round(frac * 100)
        return (f'<div class="sld"{attr} style="{style}"><div class="fill" style="width:{pct}%"></div>'
                f'<div class="th" style="left:{pct}%"></div></div>')

    def seg(self, labels, active=0, *, region=None, noun="option", cids=None):
        """Segmented control. labels are strings; cids (same length) attach concepts."""
        parts = []
        for i, lab in enumerate(labels):
            attr = self.reg("tab", noun, lab, region=region, cid=cids[i] if cids else None)
            parts.append(f'<div class="{"on" if i == active else ""}"{attr}>{esc(lab)}</div>')
        return f'<div class="seg">{"".join(parts)}</div>'

    def iseg(self, cids, active=0, *, region=None):
        """Segmented control of icons."""
        parts = []
        for i, cid in enumerate(self.avail(cids, icon=True)):
            name = self.ico(cid)
            attr = self.reg("button", "button", self.lab(cid), ui="icon", icon=name, cid=cid, region=region, anchor="icon")
            parts.append(f'<div class="{"on" if i == active else ""}"{attr}>{icons.svg(name)}</div>')
        return f'<div class="seg">{"".join(parts)}</div>' if parts else ""

    # ---- navigation -----------------------------------------------------------------------
    def nav(self, label, region, *, cid=None, deco=None, icon_html=None, on=False, count=None, noun="item",
            refs=None, cls="", pad=0, func=True, anchor=None, tail=""):
        attr = self.reg("nav", noun, label, cid=cid, region=region, refs=refs, func=func, anchor=anchor)
        ico = icon_html if icon_html is not None else (self.deco(*deco, blank=True) if deco else "")
        cnt = f'<span class="cnt">{esc(count)}</span>' if count is not None else ""
        style = f' style="padding-left:{10 + pad}px"' if pad else ""
        return f'<div class="nav{" on" if on else ""} {cls}"{attr}{style}>{ico}<span class="el">{esc(label)}</span>{cnt}{tail}</div>'

    def navc(self, cid, region, **kw):
        """Navigation entry for a concept (label and decorative icon from the concept)."""
        if not self.has(cid):
            return ""
        name = self.ico(cid)
        kw.setdefault("icon_html", icons.svg(name) if name else f'<span style="width:var(--is);height:var(--is);flex:none"></span>')
        return self.nav(self.lab(cid), region, cid=cid, **kw)

    def tabs(self, items, active=0, *, region=None, cls="", closable=False, noun="tab", icon_fn=None):
        """items: labels or (label, cid). closable adds a small close cross to each tab."""
        out = []
        for i, it in enumerate(items):
            label, cid = (it, None) if isinstance(it, str) else it
            attr = self.reg("tab", noun, label, cid=cid, region=region)
            ico = icon_fn(label) if icon_fn else ""
            x = ""
            if closable:
                xa = self.reg("button", "button", f"Close {label} tab", ui="icon", cid="tab.close", region=region,
                              row=f"the {label} tab", refs=[f"the close button on the {label} tab", f"the X on the {label} tab"])
                x = f'<span class="x"{xa}>{CROSS}</span>'
            out.append(f'<div class="tab{" on" if i == active else ""}"{attr}>{ico}<span>{esc(label)}</span>{x}</div>')
        return f'<div class="tabs {cls}">{"".join(out)}</div>'

    # ---- menus (used by overlays and inline popovers) ---------------------------------------
    def menu(self, entries, region, *, obj=None, checks=False, icons_=False, w=None, hi=None, noun="option"):
        """entries: concept ids, "-" separators, ("#", heading), or (label,) free items."""
        rows = []
        keys = ["⌘N", "⌘O", "⌘S", "⇧⌘S", "⌘P", "⌘Z", "⇧⌘Z", "⌘X", "⌘C", "⌘V", "⌘A", "⌘F", "⌘W", "⌘,", "F2", "Del",
                "Ctrl+D", "Ctrl+E", "Ctrl+K", "Ctrl+Shift+P", "F5", "Alt+Enter", "⌘R", "⌘L", "⌘B", "⌘I"]
        shown = 0
        for e in entries:
            if e == "-":
                if rows and not rows[-1].startswith('<div class="msep"'):
                    rows.append('<div class="msep"></div>')
                continue
            if isinstance(e, tuple) and e[0] == "#":
                rows.append(f'<div class="mhd">{esc(e[1])}</div>')
                continue
            if isinstance(e, tuple):
                label, cid = e[0], None
            else:
                if not self.has(e):
                    continue
                label, cid = self.lab(e), e
            attr = self.reg("menuitem", noun, label, cid=cid, region=region, obj=obj)
            pre = ""
            if checks:
                pre = f'<span class="ck">{TICK_S if self.rng.random() < 0.25 else ""}</span>'
            elif icons_ and cid and self.ico(cid):
                pre = icons.svg(self.ico(cid))
            elif icons_:
                pre = '<span style="width:calc(var(--is) - 2px);flex:none"></span>'
            r = self.rng.random()
            tail = f'<span class="kb">{self.rng.choice(keys)}</span>' if r < 0.45 else (f'<span class="kb">{CHEV_R}</span>' if r < 0.55 else "")
            on = " on" if hi is not None and shown == hi else ""
            rows.append(f'<div class="mi{on}"{attr}>{pre}<span>{esc(label)}{"…" if cid and self.rng.random() < 0.2 else ""}</span>{tail}</div>')
            shown += 1
        while rows and rows[-1].startswith('<div class="msep"'):
            rows.pop()
        style = f' style="width:{w}px"' if w else ""
        return f'<div class="menu"{style}>{"".join(rows)}</div>'

    # ---- small pieces -----------------------------------------------------------------------
    def av(self, name, size=24, sq=False):
        initials = "".join(p[0] for p in name.replace("-", " ").split()[:2]).upper()
        color = COLORS[stable_hash(name) % len(COLORS)]
        return (f'<span class="av{" sq" if sq else ""}" style="width:{size}px;height:{size}px;font-size:{max(9, round(size * 0.4))}px;'
                f'background:{color}">{esc(initials)}</span>')

    def thumb(self, w, h, r=None):
        c1, c2 = self.rng.sample(COLORS, 2)
        rad = f"border-radius:{r}px;" if r is not None else ""
        return f'<div class="thumb" style="width:{w}px;height:{h}px;--c1:{c1};--c2:{c2};{rad}"></div>'

    def spark(self, w=120, h=32, n=16, color="var(--ac)", fill=True):
        """Small line chart with seeded values."""
        v, pts = self.rng.uniform(0.3, 0.7), []
        for i in range(n):
            v = min(0.95, max(0.05, v + self.rng.uniform(-0.18, 0.2)))
            pts.append((round(i * w / (n - 1), 1), round(h - v * h, 1)))
        line = " ".join(f"{x},{y}" for x, y in pts)
        area = f'<polygon points="0,{h} {line} {w},{h}" fill="{color}" opacity=".14"/>' if fill else ""
        return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="width:{w}px;height:{h}px;display:block;flex:none">{area}'
                f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>')

    def bars(self, w=240, h=120, n=12, color="var(--ac)", two=False):
        bw = w / n
        out = []
        for i in range(n):
            v = self.rng.uniform(0.15, 1)
            out.append(f'<rect x="{i * bw + bw * 0.18:.1f}" y="{h - v * h:.1f}" width="{bw * (0.3 if two else 0.64):.1f}" height="{v * h:.1f}" rx="1.5" fill="{color}"/>')
            if two:
                v2 = self.rng.uniform(0.1, 0.9)
                out.append(f'<rect x="{i * bw + bw * 0.52:.1f}" y="{h - v2 * h:.1f}" width="{bw * 0.3:.1f}" height="{v2 * h:.1f}" rx="1.5" fill="var(--fg2)" opacity=".55"/>')
        grid = "".join(f'<line x1="0" x2="{w}" y1="{h * k / 4:.1f}" y2="{h * k / 4:.1f}" stroke="var(--bd)" stroke-width="1"/>' for k in range(1, 4))
        return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="width:100%;height:{h}px;display:block">{grid}{"".join(out)}</svg>'

    def linechart(self, h=140, series=2, n=24):
        w = 600
        cols = ["var(--ac)", "var(--fg2)", "var(--ok)", "var(--warn)"]
        grid = "".join(f'<line x1="0" x2="{w}" y1="{h * k / 4:.1f}" y2="{h * k / 4:.1f}" stroke="var(--bd)" stroke-width="1" vector-effect="non-scaling-stroke"/>' for k in range(1, 4))
        lines = []
        for s in range(series):
            v, pts = self.rng.uniform(0.3, 0.7), []
            for i in range(n):
                v = min(0.95, max(0.05, v + self.rng.uniform(-0.12, 0.13)))
                pts.append(f"{i * w / (n - 1):.1f},{h - v * h:.1f}")
            p = " ".join(pts)
            if s == 0:
                lines.append(f'<polygon points="0,{h} {p} {w},{h}" fill="{cols[0]}" opacity=".10"/>')
            lines.append(f'<polyline points="{p}" fill="none" stroke="{cols[s % 4]}" stroke-width="1.8" vector-effect="non-scaling-stroke"/>')
        return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="width:100%;height:{h}px;display:block">{grid}{"".join(lines)}</svg>'

    def donut(self, size=110):
        r, c = 40, 2 * 3.14159 * 40
        parts, off = [], 0
        fr = sorted([self.rng.uniform(0.1, 0.4) for _ in range(3)], reverse=True)
        tot = sum(fr) + 0.15
        for f, col in zip(fr, ["var(--ac)", "var(--ok)", "var(--warn)"]):
            ln = c * f / tot
            parts.append(f'<circle cx="55" cy="55" r="{r}" fill="none" stroke="{col}" stroke-width="14" stroke-dasharray="{ln:.1f} {c - ln:.1f}" stroke-dashoffset="{-off:.1f}"/>')
            off += ln
        return (f'<svg viewBox="0 0 110 110" style="width:{size}px;height:{size}px;flex:none;transform:rotate(-90deg)">'
                f'<circle cx="55" cy="55" r="{r}" fill="none" stroke="var(--bg4)" stroke-width="14"/>{"".join(parts)}</svg>')

    def scroll(self, top=8, height=30):
        return f'<div class="scr" style="top:{top}%;height:{height}%"></div>'

    def lines(self, n, lo=40, hi=96):
        """Grey placeholder text lines (for document bodies that are never targets)."""
        return "".join(f'<div style="height:8px;border-radius:4px;background:var(--bg4);width:{self.rng.randint(lo, hi)}%;margin:7px 0"></div>' for _ in range(n))
