"""Spreadsheets: ribbon and web toolbars, formula bar, cell grid, sheet tabs, pivot and database grids."""
from .. import icons
from ..data import COMPANIES, EVENTS
from ..splits import pool
from ..ui import esc, CHEV_D, TICK
from ..vocab import C, P

NAME = "sheet"
KIND = "either"
VARIANTS = {"ribbon": "train", "web_sheets": "train", "pivot_side": "dev", "db_grid": "test"}

FMT = P("sh.f", [
    ("Bold", "make the selected characters heavier", "bold"), ("Italic", "slant the selected characters", "italic"),
    ("Underline", "draw a rule beneath the selected characters", "underline"), ("Strikethrough", "cross out the selected characters", "strikethrough"),
    ("Text color", "change the hue of the letters", "baseline"), ("Fill color", "shade the background of the selected boxes", "paint-bucket"),
    ("Highlight", "mark the selection with a marker tint", "highlighter"), ("Borders", "draw outlines around the selected boxes", "square-dashed"),
    ("Merge cells", "combine the selected boxes into one", "table-cells-merge"), ("Unmerge cells", "split a combined box back apart", "table-cells-split"),
    ("Align left", "push the contents against the box's starting edge", "text-align-start"), ("Align center", "put the contents in the middle horizontally", "text-align-center"),
    ("Align right", "push the contents against the box's far edge", "text-align-end"), ("Wrap text", "let long contents flow onto several lines inside the box", "wrap-text"),
    ("Currency format", "show the numbers as money", "dollar-sign"), ("Percent format", "show the numbers as parts of a hundred", "percent"),
    ("Increase decimals", "show more digits after the point", "decimals-arrow-right"), ("Decrease decimals", "show fewer digits after the point", "decimals-arrow-left"),
    ("AutoSum", "add up the numbers above automatically", "sigma"), ("Insert function", "pick a formula from the catalog", "square-function"),
    ("Sort A to Z", "order the rows alphabetically ascending", "arrow-down-a-z"), ("Sort Z to A", "order the rows alphabetically descending", "arrow-down-z-a"),
    ("Insert chart", "turn the selected numbers into a graph", "chart-column"), ("Pivot table", "summarize the data by dragging fields into rows and columns", "table-properties"),
    ("Freeze panes", "keep the heading rows visible while scrolling", "snowflake"), ("Conditional formatting", "color boxes automatically based on their values", "paintbrush"),
    ("Data validation", "restrict what may be typed into the boxes", "list-checks"), ("Insert row", "add an empty line of boxes above", "between-horizontal-start"),
    ("Insert column", "add an empty vertical strip of boxes", "between-vertical-start"), ("Delete row", "remove the selected line of boxes", "table-rows-split"),
    ("Delete column", "remove the selected vertical strip of boxes", "table-columns-split"), ("Clear formatting", "strip the styling from the selection", "remove-formatting"),
    ("Format painter", "copy the styling of one box onto others", "paint-roller"), ("Font size up", "make the letters larger", "a-arrow-up"),
    ("Font size down", "make the letters smaller", "a-arrow-down"), ("Subscript", "lower the selected characters below the baseline", "subscript"),
    ("Superscript", "raise the selected characters above the baseline", "superscript"), ("Insert image", "place a picture on the grid", "image"),
    ("Spell check", "look for typos in the workbook", "spell-check"), ("Text to columns", "split one strip of values into several at a delimiter", "columns-3"),
    ("Remove duplicates", "drop rows that repeat", "copy-x"), ("Group rows", "tuck a block of lines under a toggle", "group"),
    ("Protect sheet", "stop others from editing this tab", "file-lock"), ("Named ranges", "give a block of boxes a reusable title", "text-select"),
    ("Calculate now", "recompute every formula immediately", "calculator"), ("Show formulas", "display the equations instead of their results", "square-sigma"),
    ("Rotate text", "tilt the contents at an angle", "rotate-cw-square"), ("Vertical align", "choose top, middle or bottom placement inside the box", "align-vertical-justify-center"),
    ("Indent more", "push the contents further from the edge", "indent-increase"), ("Indent less", "pull the contents back toward the edge", "indent-decrease"),
    ("Cell styles", "apply a preset look to the selection", "palette"), ("Trace precedents", "draw arrows to the boxes a formula depends on", "route"),
    ("Flash fill", "complete a strip of values by following the pattern I started", "zap"),
])
C("sh.addsheet", "Add sheet|New tab|Insert worksheet", "plus|circle-plus|square-plus", "get another blank grid in this workbook|append an empty page of cells to the workbook|start one more grid alongside the existing ones", n="add sheet|new tab|insert worksheet")
C("sh.formula", "Formula bar|Formula input|Function line", "", "edit the calculation behind the active cell|type an equation for the selected cell|change what the selected cell computes")
C("sh.namebox", "Name box|Cell reference|Address box", "", "jump to a cell by typing its coordinates|go straight to a cell by entering where it is|type a location such as D12 to select it")
C("sh.hidefields", "Hide fields|Hide columns|Choose columns", "eye-off|eye-closed|columns-3-cog", "pick which attributes are shown in the grid|stop some attributes from being displayed|trim the grid down to the attributes I care about")
C("sh.group", "Group|Group by|Cluster rows", "square-stack|layers-2|rows-4", "bundle the records under headings by a shared value|collect records with the same value under one heading|organize the records into collapsible sets")
C("sh.color", "Color|Color rows|Row colors", "palette|paintbrush-vertical|swatch-book", "tint the records according to a rule|give records a tint based on their values|make certain records stand out with a tint")
C("sh.rowheight", "Row height|Row size|Line spacing", "rows-3|unfold-vertical|move-vertical", "make each record taller or shorter|change how much vertical room every record gets|switch between short and tall records")
C("sh.newview", "Create view|New view|Add a view", "plus|circle-plus|square-plus", "set up another way of looking at this table|make an additional saved layout for this table|start one more saved perspective on these records")
C("sh.addrow", "Add record|New row|Insert record", "plus|circle-plus|square-plus", "append an empty entry at the bottom of the table|start one more entry in this table|put a blank line at the end of the records")
C("sh.expand", "Expand record|Open record|Show details", "square-arrow-out-up-right|panel-right-open|arrow-up-right", "see every attribute of {o} in a larger form|bring up the full form for {o}|look at {o} in its own detail window", o="this record")
C("sh.resolve", "Resolve|Mark as resolved|Close thread", "check|circle-check|check-check", "settle the discussion started by {o}|mark the remark from {o} as dealt with|wrap up the conversation {o} began", o="this commenter")
C("sh.update", "Update|Refresh pivot|Apply layout", "", "rebuild the summary with the fields as arranged|recompute the summary table from the chosen fields|make the summary reflect the current field arrangement")
C("sh.defer", "Defer layout update|Update manually|Pause automatic updates", "", "hold off on rebuilding the summary until I say so|keep the summary from recomputing after each change|make the summary wait for my go-ahead before rebuilding")


def _pool(name, text):
    items = [x.strip() for x in text.replace("\n", "|").split("|") if x.strip()] if isinstance(text, str) else list(text)
    pool(name, items, "train")   # claim labels at import so ownership never depends on run order
    return items


HEADS = _pool("sh.heads", """Region|Product|Units|Unit price|Revenue|Cost|Margin|Owner|Quarter|Target|Forecast|Variance|Status|Category|SKU
Discount|Tax|Net total|Growth|Share|Channel|Country|Segment|Plan|Seats|MRR|Churn|Start date|End date|Notes|Priority|Stage|Deal size
Close date|Lead source|Headcount|Budget|Actuals|Run rate|Backlog|Assignee|Due date|Estimate|Sprint|Location|Supplier|Reorder level
On hand|Lead time|Rating""")
RIBBON = _pool("sh.ribbon", """Home|Insert|Page Layout|Formulas|Data|Review|View|Draw|Automate|Developer|Add-ins|Tell me|Design|Analyze
Table tools|Query|Charts|Collaborate|Layout|Scripts""")
SHEETS = _pool("sh.sheets", """Summary|Q1|Q2|Raw data|Pivot|Charts|Assumptions|Inputs|Lookup|Archive|FY2025|FY2026|Forecast|Actuals|Budget
Scratch|Dashboard|Regions|Products|Customers|Q3|Q4|Headcount|Pipeline|Glossary""")
FONTS = _pool("sh.fonts", "Arial|Inter|Roboto|Georgia|Verdana|Courier New|Helvetica|Tahoma|Cambria|Lato|Open Sans|Times New Roman|Garamond|Futura|Menlo")
NUMFMT = _pool("sh.numfmt", "General|Number|Currency|Accounting|Short date|Long date|Percentage|Fraction|Scientific|Plain text|Time|Custom|Duration|Automatic|Rounded")
TABLES = _pool("sh.tables", "Projects|Tasks|Clients|Contacts|Invoices|Assets|Sprints|Bugs|Leads|Vendors|Events|Content calendar|Inventory|Candidates|OKRs|Campaigns|Releases|Suppliers|Renewals|Requests")
VIEWS = _pool("sh.views", """All records|By status|My items|This week|Kanban by owner|Calendar|Gallery|Overdue|Archived|High priority|Unassigned
Recently updated|Timeline|Intake form|Budget review|Grid view|Main view|Needs triage|Done this month|By team|Blocked items
Q3 priorities|Stale records|Owner workload|Waiting on client|Launch checklist|Roadmap board|Signed contracts|Low stock|Due tomorrow
Pinned|Vendor scorecard|Mobile view|Print layout|Exec summary|By region|Drafts only|Top accounts|Missing fields|Weekly review""")
CELL_REFS = _pool("sh.ref.cell", ["cell {a}", "the cell at column {c}, row {r}", "the {a} cell in the grid", "the cell in column {c} of row {r}", "grid cell {a}"])
COL_REFS = _pool("sh.ref.col", ["the header of column {c}", "column {c}'s header", "the column {c} header at the top of the grid", "the letter {c} above the grid", "the {c} column heading"])
ROW_REFS = _pool("sh.ref.row", ["the header of row {r}", "row {r}'s number at the left edge", "the row {r} header", "the number {r} at the left of the grid", "the row heading {r}"])

CSS = """
.sh-grid{display:grid;font-size:calc(var(--fs) - .5px);background:var(--bg)}
.sh-c{border-right:1px solid var(--bd);border-bottom:1px solid var(--bd);padding:0 6px;display:flex;align-items:center;white-space:nowrap;overflow:hidden;min-width:0}
.sh-c.h{background:var(--bg2);color:var(--fg1);justify-content:center;font-size:.9em}
.sh-c.n{justify-content:flex-end}.sh-c.b{font-weight:600}.sh-c.sel{outline:2px solid var(--ac);outline-offset:-2px;overflow:visible}
.sh-grp{display:flex;flex-direction:column;align-items:center;padding:4px 10px 2px;border-right:1px solid var(--bd);gap:2px;flex:none}
.sh-grp .cap{font-size:.78em;color:var(--fg2);margin-top:auto}
.sh-big{display:flex;flex-direction:column;align-items:center;gap:3px;padding:4px 8px;border-radius:var(--r);font-size:.88em;white-space:nowrap}
.sh-big svg.i{width:26px;height:26px}
.sh-chip{display:flex;align-items:center;gap:4px;height:22px;padding:0 6px;border:1px solid var(--bd2);border-radius:var(--r);background:var(--bg);font-size:.9em;white-space:nowrap}
.sh-zone{border:1px solid var(--bd);border-radius:var(--r);padding:6px;display:flex;flex-direction:column;gap:4px;min-height:92px;background:var(--bg)}
.sh-acc .ib{color:inherit}
.sh-nb.tabs{border-bottom:none;flex:0 1 auto;min-width:0;overflow:hidden}
"""
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _refs(ctx, name, pats, **kw):
    return [p.format(**kw) for p in ctx.d.take(name, pats)]


def _grid(ctx, W, H, avail_w, region="the grid", pivot=False):
    """Lettered columns, numbered rows, seeded numbers; a few cells and all headers are targets."""
    rng, d = ctx.rng, ctx.d
    cw, rh = rng.choice([88, 96, 104, 112]), rng.choice([21, 22, 24])
    nc, nr = min(26, max(6, avail_w // cw + 1)), H // rh
    heads = d.take("sh.heads", HEADS, min(nc, rng.randint(5, 9)))
    names = d.products(nr) + d.take("company", COMPANIES) + d.people(24)
    sel = (rng.randint(2, min(nr, 14)), rng.randint(1, len(heads) - 1))
    picks = {(rng.randint(2, min(nr - 1, 24)), rng.randint(1, min(nc - 1, len(heads) + 1))) for _ in range(7)} | {sel}
    out = ['<div class="sh-c h"></div>']
    for c in range(nc):
        L = LETTERS[c]
        attr = ctx.reg("columnheader", "column header", f"column {L} header", region=region, refs=_refs(ctx, "sh.ref.col", COL_REFS, c=L)) if rng.random() < 0.4 else ""
        out.append(f'<div class="sh-c h"{attr}>{L}</div>')
    for r in range(1, nr + 1):
        attr = ctx.reg("rowheader", "row header", f"row {r} header", region=region, refs=_refs(ctx, "sh.ref.row", ROW_REFS, r=r)) if rng.random() < 0.15 else ""
        out.append(f'<div class="sh-c h"{attr}>{r}</div>')
        for c in range(nc):
            text, cls, attr = "", "", ""
            if r == 1 and c < len(heads):
                text, cls = heads[c], " b"
                attr = ctx.reg("cell", "cell", text, region=region, anchor="row")
            elif c == 0 and r - 2 < min(len(names), nr * 2 // 3):
                text = names[r - 2]
                attr = ctx.reg("cell", "cell", text, region=region, anchor="row")
                if pivot and r % 4 == 2:
                    cls = " b"
            elif 0 < c < len(heads) and r - 2 < min(len(names), nr * 2 // 3):
                kind = c % 4
                text = (f"{rng.uniform(40, 99000):,.2f}" if kind == 1 else str(rng.randint(1, 4800)) if kind == 2 else
                        f"{rng.uniform(-12, 48):.1f}%" if kind == 3 else rng.choice(["EMEA", "APAC", "AMER", "Open", "Won", "Hold", "Q1", "Q2"]))
                cls = " n" if kind else ""
            if (r, c) in picks and not attr:
                a = f"{LETTERS[c]}{r}"
                attr = ctx.reg("cell", "cell", f"cell {a}", region=region, refs=_refs(ctx, "sh.ref.cell", CELL_REFS, a=a, c=LETTERS[c], r=r))
            inner = f'<span class="el">{esc(text)}</span>' if attr and text else esc(text)
            out.append(f'<div class="sh-c{cls}{" sel" if (r, c) == sel else ""}"{attr}>{inner}</div>')
    style = f"grid-template-columns:42px {cw + 80}px repeat({nc - 1},{cw}px);grid-auto-rows:{rh}px"
    return f'<div class="f1 clip"><div class="sh-grid" style="{style}">{"".join(out)}</div></div>', f"{LETTERS[sel[1]]}{sel[0]}"


def _fbar(ctx, ref):
    region = "the formula bar"
    nattr = fattr = ""
    if ctx.has("sh.namebox"):
        nb = ctx.lab("sh.namebox")
        nattr = ctx.reg("field", "box", nb, cid="sh.namebox", region=region, refs=[f"the {nb.lower()} showing {ref}", f"the box that says {ref} left of the formula"])
    if ctx.has("sh.formula"):
        fl = ctx.lab("sh.formula")
        fattr = ctx.reg("field", "field", fl, cid="sh.formula", region=region, refs=[f"the {fl.lower()}", "the long input next to the fx symbol"])
    formula = ctx.rng.choice([f"=SUM({ref[0]}2:{ref[0]}48)", "=VLOOKUP(A7,Lookup!A:D,3,FALSE)", f"=ROUND({ref[0]}3*1.19,2)", "=IF(E5>D5,\"over\",\"ok\")", "=AVERAGEIFS(F:F,B:B,\"EMEA\")"])
    return (f'<div class="row g6 px8 bb fn" style="height:calc(var(--ch) + 8px)"><div class="inp" style="width:86px"{nattr}><span class="f1">{ref}</span>{CHEV_D}</div>'
            f'<span class="mut" style="font-style:italic;font-family:serif">fx</span><div class="inp f1 mono"{fattr}><span>{esc(formula)}</span></div></div>')


def _sheet_tabs(ctx, n):
    region = "the sheet tabs"
    names = ctx.d.take("sh.sheets", SHEETS, n)
    tabs = ctx.tabs(names, active=ctx.rng.randrange(len(names)), region=region, cls="box sh-nb", noun="sheet tab")
    return f'<div class="row bt bg1 fn">{ctx.ibtn("sh.addsheet", region, cls="s")}{ctx.ibtn("view.list", region, cls="s", obj="the sheets")}{tabs}<div class="sp"></div>'


def _avatar(ctx, who, region, size=28):
    """The signed-in user's avatar; a target (and anchor for the account menu) when the split names it."""
    if not ctx.has("account"):
        return ctx.av(who, size)
    attr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=region, anchor="account")
    return f"<span{attr}>{ctx.av(who, size)}</span>"


def _ic(ctx, cids, region, **kw):
    return "".join(ctx.ibtn(c, region, **kw) for c in cids)


def _big(ctx, cid, region):
    if not ctx.has(cid):
        return ""
    attr = ctx.reg("button", "button", ctx.lab(cid), cid=cid, region=region)
    ico = icons.svg(ctx.ico(cid)) if ctx.ico(cid) else ""
    return f'<div class="sh-big"{attr}>{ico}<span>{esc(ctx.lab(cid))}</span></div>'


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    doc = d.files("sheet", 1, ext=False)[0]
    fmt = ctx.avail(FMT, icon=True)
    me = d.person()
    menus = ["mb.file", "mb.edit", "mb.view", "mb.insert", "mb.format", "mb.data", "mb.tools", "mb.help"]
    ctx.menus.update({"mb.format": fmt[:14], "mb.insert": [c for c in fmt if "insert" in c][:8] + ["comment", "link"], "mb.data": ["sort", "filter", "-"] + fmt[14:24]})
    ctx.ctxmenu = ["cut", "copy", "paste", "-"] + [c for c in fmt if "row" in c or "column" in c or "merge" in c][:6] + ["-", "comment", "link", "clear"]
    ctx.ctxobj = "the selected cells"
    fonts, nums = d.take("sh.fonts", FONTS, 5), d.take("sh.numfmt", NUMFMT, 5)

    if variant == "ribbon":
        region = "the ribbon"
        rt = ctx.tabs(d.take("sh.ribbon", RIBBON, 7), active=0, region="the ribbon tabs", cls="sh-nb")
        top = f'<div class="row bg2 fn" style="padding-right:8px">{rt}<div class="sp"></div>{ctx.ibtn("comment", "the ribbon tabs", cls="s", obj="this workbook")}{ctx.tbtn("share", "the ribbon tabs", cls="sm pri", icon=True, obj="this workbook")}</div>'
        rest = [c for c in fmt]
        rng.shuffle(rest)
        font = ctx.select("Font", fonts[0], options=fonts, region=region, above=False, w=120, refs=[f"the font dropdown showing {fonts[0]}"]) if fonts else ""
        size = ctx.select("Font size", str(rng.choice([10, 11, 12, 14])), region=region, above=False, w=54, refs=["the font size dropdown in the ribbon"])
        numf = ctx.select("Number format", nums[0], options=nums, region=region, above=False, w=130, refs=[f"the number format dropdown showing {nums[0]}"]) if nums else ""
        k = max(3, len(rest) // 5)
        groups = [
            ("Clipboard", _big(ctx, "paste", region), _ic(ctx, ["cut", "copy"], region, cls="s", obj="the selected cells"), ""),
            ("Typeface", "", f'<div class="row g4">{font}{size}</div>', _ic(ctx, rest[:k], region, cls="s")),
            ("Alignment", "", _ic(ctx, rest[k:k + k // 2 + 1], region, cls="s"), _ic(ctx, rest[k + k // 2 + 1:2 * k], region, cls="s")),
            ("Numbers", "", numf, _ic(ctx, rest[2 * k:3 * k], region, cls="s")),
            ("Structure", "".join(_big(ctx, c, region) for c in rest[3 * k:3 * k + 2]), "", ""),
            ("Find and sort", "", _ic(ctx, rest[3 * k + 2:4 * k + 1] + ["sort"], region, cls="s"), _ic(ctx, rest[4 * k + 1:5 * k] + ["filter", "search"], region, cls="s")),
        ]
        gh = "".join(f'<div class="sh-grp"><div class="row g6" style="align-items:flex-start">{big}<div class="col g2"><div class="row g2">{r1}</div><div class="row g2">{r2}</div></div></div>'
                     f'<span class="cap">{cap}</span></div>' for cap, big, r1, r2 in groups if big or r1 or r2)
        grid, ref = _grid(ctx, W, H, W)
        sr = "the status bar"
        zoom = ctx.slider("Zoom", rng.uniform(0.3, 0.7), region=sr, w=110, cid=None)
        ctx.targets[ctx.last].refs = ["the zoom slider in the status bar", "the magnification slider at the bottom right"]
        sb = (f'<div class="sbar"><span>Ready</span><div class="sp"></div><span>Average: {rng.uniform(100, 9000):,.2f}</span><span>Count: {rng.randint(2, 60)}</span><span>Sum: {rng.uniform(1000, 99000):,.2f}</span>'
              f'{ctx.ibtn("zoomout", sr, cls="s")}{zoom}{ctx.ibtn("zoomin", sr, cls="s")}<span>{rng.choice([90, 100, 110, 125])}%</span></div>')
        body = f'{top}<div class="row bb bg1 fn clip" style="min-height:92px;align-items:stretch">{gh}</div>{_fbar(ctx, ref)}{grid}{_sheet_tabs(ctx, rng.randint(3, 6))}</div>{sb}'
    elif variant == "web_sheets":
        region = "the toolbar"
        mr = "the menu row"
        mrow = "".join(f'<div class="mb"{ctx.reg("menu", "menu", ctx.lab(c), cid=c, region=mr, anchor="menubar")}>{esc(ctx.lab(c))}</div>' for c in menus if ctx.has(c))
        head = (f'<div class="row g10 px12 fn" style="padding-top:8px"><div class="thumb" style="width:30px;height:36px;border-radius:5px;--c1:#1e8e3e;--c2:#34a853"></div>'
                f'<div class="col f1"><div class="row g6"><span class="lg m">{esc(doc)}</span>{ctx.ibtn("fav", "the header", cls="s", obj="this spreadsheet")}{ctx.ibtn("move", "the header", cls="s", obj="this spreadsheet")}</div>'
                f'<div class="row" style="height:24px;margin-left:-8px">{mrow}</div></div>{ctx.ibtn("history", "the header", obj="this spreadsheet")}{ctx.ibtn("comment", "the header", obj="this spreadsheet")}'
                f'{ctx.tbtn("share", "the header", cls="pri", icon=True, obj="this spreadsheet")}{_avatar(ctx, me, "the header", 30)}</div>')
        a, b = len(fmt) // 2, len(fmt)
        font = ctx.select("Font", fonts[0], options=fonts, region=region, above=False, w=110, cls="soft", refs=[f"the font dropdown showing {fonts[0]}"]) if fonts else ""
        step = (f'<div class="step"><div{ctx.reg("button", "button", "decrease font size", ui="icon", region=region, refs=["the minus next to the font size", "the smaller-font button left of the size number"])}>−</div>'
                f'<div class="v">{rng.choice([10, 11, 12])}</div><div{ctx.reg("button", "button", "increase font size", ui="icon", region=region, refs=["the plus next to the font size", "the larger-font button right of the size number"])}>+</div></div>')
        zoom = ctx.select("Zoom", "100%", region=region, above=False, w=72, cls="soft", refs=["the zoom dropdown in the toolbar"])
        tb = (f'<div class="tb" style="margin:6px 10px;border-radius:999px;border:none;background:var(--bg3);padding:3px 12px">{_ic(ctx, ["undo", "redo", "print"], region, cls="s", obj="this spreadsheet")}'
              f'{zoom}<div class="vsep"></div>{_ic(ctx, fmt[:a // 2], region, cls="s")}<div class="vsep"></div>{font}{step}<div class="vsep"></div>{_ic(ctx, fmt[a // 2:a], region, cls="s")}'
              f'<div class="vsep"></div>{_ic(ctx, fmt[a:b] if W > 1500 else fmt[a:a + 5], region, cls="s")}{_ic(ctx, ["link", "comment", "filter"], region, cls="s", obj="the selected cells")}'
              f'<div class="sp"></div>{ctx.ibtn("collapse", region, cls="s", obj="the toolbar and menus")}</div>')
        panel, pw = "", 0
        if W >= 1440 and rng.random() < 0.6:
            pr, pw = "the comments panel", rng.choice([280, 320])
            threads = "".join(
                f'<div class="col g4 p8 card"><div class="row g6">{ctx.av(p, 24)}<span class="m f1">{esc(p)}</span>{ctx.ibtn("sh.resolve", pr, row=p, obj=p, cls="s")}{ctx.ibtn("more", pr, row=p, obj=f"the comment by {p}", cls="s", anchor="more")}</div>'
                f'<span class="sm mut">{esc(d.sentence())}</span></div>' for p in d.people(rng.randint(3, 5))[1:])
            panel = (f'<div class="side bl p8 g8" style="width:{pw}px"><div class="row"><span class="b f1">Comments</span>{ctx.ibtn("notif", pr, cls="s")}{ctx.ibtn("close.panel", pr, cls="s", obj="the comments panel")}</div>'
                     f'{threads}{ctx.field("Reply", "", ph="Add a comment…", region=pr, above=False)}</div>')
        grid, ref = _grid(ctx, W, H, W - pw)
        body = f'{head}{tb}{_fbar(ctx, ref)}<div class="row str f1">{grid}{panel}</div>{_sheet_tabs(ctx, rng.randint(3, 6))}{ctx.tbtn("help", "the sheet tabs", cls="sm ghost", icon=True)}</div>'
        menus = []
    elif variant == "pivot_side":
        region = "the toolbar"
        tb = (f'<div class="tb">{ctx.tbtn("refresh", region, icon=True, obj="the pivot data")}{ctx.tbtn("filter", region, icon=True)}{ctx.tbtn("sort", region, icon=True)}{ctx.tbtn("export", region, icon=True, obj="this summary")}'
              f'<div class="vsep"></div>{_ic(ctx, fmt[:18], region, cls="s")}<div class="sp"></div>{ctx.search(region, w=200)}{ctx.ibtn("settings", region)}</div>')
        pr, pw = "the field list", rng.choice([300, 340, 380])
        heads = d.take("sh.heads", HEADS)
        rng.shuffle(heads)
        checks = "".join(f'<div class="li fn" style="min-height:calc(var(--rh) - 2px)">{ctx.check(h, i < 4, region=pr)}</div>' for i, h in enumerate(heads))
        zones = []
        for zone, items in zip(d.take("sh.zones", ZONES, 4), [heads[:1], heads[1:2], heads[2:4], ["Sum of " + heads[0], "Count of " + heads[3 % len(heads)]]]):
            zr = f"the {zone} box"
            chips = "".join(f'<div class="sh-chip"{ctx.reg("button", "field chip", it, region=zr, anchor="more")}><span class="f1">{esc(it)}</span>{CHEV_D}</div>' for it in items)
            zones.append(f'<div class="sh-zone"><span class="xs b mut">{esc(zone)}</span>{chips}</div>')
        dl = ctx.lab("sh.defer") if ctx.has("sh.defer") else ""
        panel = (f'<div class="side bl" style="width:{pw}px"><div class="row p8 bb"><span class="b f1">Summary fields</span>{ctx.ibtn("settings", pr, cls="s")}{ctx.ibtn("close.panel", pr, cls="s", obj="the field list")}</div>'
                 f'<div class="p8">{ctx.search(pr, cls="soft")}</div><div class="col f1 clip">{checks}</div><div class="p8 bt" style="display:grid;grid-template-columns:1fr 1fr;gap:8px">{"".join(zones)}</div>'
                 f'<div class="row g8 p8 bt">{ctx.check(dl, False, region=pr, cid="sh.defer") if dl else ""}<div class="sp"></div>{ctx.tbtn("sh.update", pr, cls="sm pri")}</div></div>')
        grid, ref = _grid(ctx, W, H, W - pw, pivot=True)
        body = f'{tb}{_fbar(ctx, ref)}<div class="row str f1">{grid}{panel}</div>{_sheet_tabs(ctx, rng.randint(2, 4))}</div><div class="sbar"><span>{rng.randint(200, 9000):,} source rows</span><div class="sp"></div><span>Sum: {rng.uniform(1000, 99000):,.2f}</span></div>'
    else:  # db_grid
        tr = "the table tabs"
        tabs = ctx.tabs(d.take("sh.tables", TABLES, rng.randint(3, 5)), active=0, region=tr, cls="sh-nb")
        top = (f'<div class="row g8 px12 fn sh-acc" style="background:var(--ac);color:var(--acf);height:44px"><span class="b lg">{esc(doc)}</span>{CHEV_D}<div class="sp"></div>'
               f'{ctx.ibtn("help", tr)}{ctx.ibtn("notif", tr)}{ctx.tbtn("share", tr, cls="sm", icon=True, obj="this base")}{_avatar(ctx, me, tr)}</div>'
               f'<div class="row bg2 bb fn">{tabs}{ctx.ibtn("add", tr, cls="s", obj="the list of tables")}</div>')
        vr = "the view bar"
        views = d.take("sh.views", VIEWS, 9)
        vattr = ctx.reg("button", "view switcher", views[0], region=vr, refs=[f"the view switcher that says {views[0]}", f"the {views[0]} dropdown in the view bar"])
        vb = (f'<div class="tb plain">{ctx.ibtn("sidebar.toggle", vr)}<div class="btn ghost b"{vattr}>{ctx.deco("table", "sheet", "grid-3x3", "table-2")}<span>{esc(views[0])}</span>{CHEV_D}</div><div class="vsep"></div>'
              + "".join(ctx.tbtn(c, vr, cls="ghost", icon=True, obj="this view") for c in ["sh.hidefields", "filter", "sh.group", "sort", "sh.color", "sh.rowheight", "share"])
              + f'<div class="sp"></div>{ctx.ibtn("search", vr)}{ctx.ibtn("more", vr, anchor="more", obj="this view")}</div>')
        sr = "the views sidebar"
        vnav = "".join(ctx.nav(v, sr, noun="view", deco=("table", "kanban", "calendar", "layout-grid", "list", "gallery-vertical", "chart-gantt"), on=i == 0) for i, v in enumerate(views[1:]))
        side = f'<div class="side br" style="width:{rng.choice([220, 250])}px"><div class="p8">{ctx.field("Find a view", "", region=sr, above=False, cls="soft")}</div><div class="col g2 f1 clip">{vnav}</div><div class="p8 bt">{ctx.tbtn("sh.newview", sr, cls="ghost", icon=True)}</div></div>'
        gr = "the grid"
        heads = d.take("sh.heads", HEADS, min(9, 3 + (W - 260) // 190))
        kinds = ["text"] + [rng.choice(["pill", "person", "date", "num", "check"]) for _ in heads[1:]]
        widths = [rng.choice([240, 280])] + [rng.choice([130, 150, 170]) for _ in heads[1:]]
        tico = {"text": ("text", "type", "letter-text"), "pill": ("circle-chevron-down", "list", "tags"), "person": ("user", "users", "circle-user"), "date": ("calendar", "calendar-days", "clock"),
                "num": ("hash", "sigma", "calculator"), "check": ("square-check", "check", "list-checks")}
        hrow = '<div class="td" style="width:66px"><div class="chk"><span class="box"></span></div></div>' + "".join(
            f'<div class="td br" style="width:{w}px"{ctx.reg("columnheader", "column header", h, region=gr, refs=[f"the {h} column header", f"the header of the {h} field"], anchor="more")}>'
            f'<span class="mut">{ctx.deco(*tico[k], size=13)}</span><span class="el f1">{esc(h)}</span><span class="fnt">{CHEV_D}</span></div>' for h, k, w in zip(heads, kinds, widths))
        people, rows = d.people(8), []
        for i, name in enumerate((d.tasks(40) + d.files("doc", 40, ext=False) + d.take("events", EVENTS) + d.products(40))[:H // 30]):
            cells = [f'<div class="td mut" style="width:66px"><span style="width:20px">{i + 1}</span>{ctx.ibtn("sh.expand", gr, row=name, obj=f"the record {name}", cls="s")}</div>']
            for j, (k, w) in enumerate(zip(kinds, widths)):
                if j == 0:
                    inner = f'<span class="el"{ctx.reg("row", "record", name, region=gr, anchor="row")}>{esc(name)}</span>'
                elif k == "pill":
                    inner = f'<span class="pill {rng.choice(["g", "y", "r", "a", ""])}">{rng.choice(["Planned", "Active", "Blocked", "Shipped", "Review", "Paused"])}</span>'
                elif k == "person":
                    p = rng.choice(people)
                    inner = f'{ctx.av(p, 18)}<span class="el sm">{esc(p)}</span>'
                elif k == "date":
                    inner = f'<span class="mut">{d.date(True)}</span>'
                elif k == "num":
                    inner = f'<span class="sp"></span><span>{rng.randint(1, 980)}</span>'
                else:
                    on = rng.random() < 0.5
                    inner = f'<div class="chk{" on" if on else ""}"><span class="box">{TICK}</span></div>'
                cells.append(f'<div class="td br" style="width:{w}px">{inner}</div>')
            rows.append(f'<div class="tr">{"".join(cells)}</div>')
        foot = f'<div class="row g12 px12 bt bg1 fn" style="height:30px">{ctx.tbtn("sh.addrow", gr, cls="sm ghost", icon=True)}<span class="mut sm">{rng.randint(40, 900)} records</span><div class="sp"></div><span class="mut sm">Sum {rng.randint(900, 99000):,}</span></div>'
        body = f'{top}{vb}<div class="row str f1">{side}<div class="col f1"><div class="tr h">{hrow}</div><div class="col f1 clip">{"".join(rows)}</div>{foot}</div></div>'
        ctx.ctxmenu, ctx.ctxobj = ["sh.expand", "-", "copy", "duplicate", "link", "comment", "-", "delete"], "the selected record"
        menus = []
    return {"title": f"{doc} — {rng.choice(['Sheets', 'Workbook', 'Tables', 'Grid'])}", "body": f'<div class="col f1">{body}</div>', "menus": menus, "app": "Sheets", "css": CSS,
            "url": "sheets.example.com/d/" + doc.lower().replace(" ", "-")}


ZONES = _pool("sh.zones", ["Filters", "Columns", "Rows", "Values", "Report filter", "Column labels", "Row labels", "Measures", "Slicers", "Series", "Categories", "Totals",
                           "Page fields", "Across", "Down", "Metrics", "Split by", "Legend", "Axis", "Summaries"])
