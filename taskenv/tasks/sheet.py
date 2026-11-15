"""Sheets (a spreadsheet in the manner of Numbers / Excel for Mac): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

The sheet holds one of three kinds of table (a household budget, a stock list, a class grade
sheet) with its top left corner at A1, B2 or A3, and a second small table with a totals row
further down, out of view at the start. State: see web/apps/sheet.js.
"""
import re

from ..oracle import Click, Drag, Key, Reveal, Type
from . import pools
from .base import Spec, clone, cond, diff, only, say, task, unchanged, verdict

SIZE = (1010, 624)
WIN = '.win[data-app="sheet"] '
COLS = "ABCDEFGHIJ"
NROWS = 45
KINDS = ["budget", "stock", "grades"]

# ------------------------------------------------------------------ word pools of this app
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
# category: lowest, highest, step, the same amount every month
BUDGET = {"Rent": (1150, 1950, 50, True), "Groceries": (340, 640, 10, False), "Utilities": (95, 240, 5, False),
          "Transport": (60, 190, 5, False), "Internet": (35, 70, 5, True), "Phone": (20, 60, 5, True),
          "Dining out": (80, 260, 10, False), "Gym": (25, 65, 5, True), "Childcare": (320, 700, 20, True),
          "Pets": (30, 130, 5, False), "Clothing": (40, 220, 10, False), "Gifts": (20, 150, 5, False),
          "Streaming": (10, 40, 2, True), "Fuel": (60, 200, 5, False), "Parking": (20, 90, 5, True),
          "Insurance": (60, 180, 5, True), "Hobbies": (20, 140, 5, False), "Charity": (10, 80, 5, True),
          "Car loan": (180, 420, 10, True), "Pharmacy": (10, 70, 5, False)}
STOCK = ["Staplers", "Notebooks", "Copy paper", "Pens", "Envelopes", "Sticky notes", "Binders", "Scissors", "Tape rolls", "Markers",
         "Highlighters", "Paper clips", "Folders", "Erasers", "Rulers", "Glue sticks", "Ink bottles", "Toner", "Labels", "Batteries",
         "Clipboards", "Push pins", "Rubber bands", "Calculators"]
ASSIGNMENTS = ["Quiz 1", "Quiz 2", "Essay", "Project", "Midterm", "Final"]
TITLES = {"budget": ["Household budget", "Monthly budget", "Home budget 2026"], "stock": ["Stock list", "Office supplies", "Stockroom"],
          "grades": ["Class grades", "Grade book", "Class 7B grades"]}
NAME = {"budget": "budget", "stock": "stock list", "grades": "grade sheet"}
# the second table: header, row labels, what a request calls it
LOWER = {"budget": (["Goal", "Target", "Saved"], ["Holiday", "New laptop", "Rainy day", "Car repair", "New bike", "Wedding", "Sofa", "Camera", "Course fees", "Deposit"], "savings goals"),
         "stock": (["Supplier", "Orders", "Owed"], ["Paperline", "Deskwise", "Inkwell", "Staplex", "Brightmark", "Pen & Page", "Cartona", "Officio"], "suppliers"),
         "grades": (["Trip cost", "Budget", "Spent"], ["Bus", "Tickets", "Lunch", "Guide", "Snacks", "Workshop", "Entry fee"], "trip costs")}


def money(rng, lo, hi, cents=(0, 25, 50, 75, 95, 99)):
    return (rng.randint(lo, hi) * 100 + rng.choice(cents)) / 100


# how the numbers of a column are drawn (budget amounts go by category, scores are 52 to 100)
GEN = {"Quantity": lambda rng: rng.randint(3, 180), "Unit price": lambda rng: money(rng, 0, 24, (25, 49, 50, 75, 95, 99)),
       "Reorder at": lambda rng: rng.randrange(5, 45, 5),
       "Target": lambda rng: rng.randrange(300, 5001, 50), "Saved": lambda rng: rng.randrange(40, 2901, 10),
       "Orders": lambda rng: rng.randint(1, 12), "Owed": lambda rng: money(rng, 40, 900),
       "Budget": lambda rng: rng.randrange(40, 401, 10), "Spent": lambda rng: rng.randrange(20, 421, 5)}
CURRENCY = ("Unit price", "Owed")


def draw(rng, kind, row, col):
    if col in GEN:
        return GEN[col](rng)
    if kind == "budget":
        lo, hi, step, _ = BUDGET[row]
        return rng.randrange(lo, hi + 1, step)
    return rng.randint(52, 100)


def new_value(rng, kind, row, col, old):
    """A plausible number for that cell that is not the one it holds."""
    for _ in range(500):
        v = draw(rng, kind, row, col)
        if old is None or abs(v - old) > 1e-9:
            return v
    raise RuntimeError("no other value")


# ------------------------------------------------------------------ cells
def addr(c, r):
    """Column counted from 0, row from 1: addr(1, 4) == "B4"."""
    return f"{COLS[c]}{r}"


def num(x):
    """A number as the app stores it in a cell: "1450", "4.75"."""
    return str(int(x)) if float(x) == int(x) else repr(float(x))


def spoken(x):
    """A number as a person writes it, and as the oracle types it: 1450, 4.75, 412.50."""
    return str(int(x)) if float(x) == int(x) else f"{x:.2f}"


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


NUM = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?", re.I)
SUM = re.compile(r"=SUM\(([A-J])(\d+):([A-J])(\d+)\)")
REF = re.compile(r"(?<![A-Za-z0-9])([A-Za-z])(\d+)(?::([A-Za-z])(\d+))?(?![A-Za-z0-9(])")


def compute_vals(cells):
    """The app's `vals` for these cells. Covers what a start state contains: numbers, text and =SUM(range)."""
    def plain(a):
        v = cells.get(a, {}).get("v", "")
        if v and NUM.fullmatch(v):
            x = float(v)
            return int(x) if x == int(x) else x
        return v

    vals = {}
    for a, c in cells.items():
        v = c.get("v", "")
        if not v:
            continue
        m = SUM.fullmatch(v)
        if m:
            c1, c2 = sorted((COLS.index(m[1]), COLS.index(m[3])))
            r1, r2 = sorted((int(m[2]), int(m[4])))
            total = 0
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    x = plain(addr(c, r))
                    if is_num(x):
                        total += x
            vals[a] = int(total) if total == int(total) else total
        elif v.startswith("="):
            raise ValueError(f"compute_vals does not know {v!r}")
        else:
            vals[a] = plain(a)
    return vals


def without_row(cells, k):
    """The cells after row k is deleted, as the app does it: the rows below move up and the row
    numbers inside formulas follow them."""
    def ref(m):
        c1, n1, c2 = m[1], int(m[2]), m[3]
        if c2 is None:
            return "#REF!" if n1 == k else f"{c1}{n1 - 1 if n1 > k else n1}"
        lo, hi = sorted((n1, int(m[4])))
        if lo > k:
            lo, hi = lo - 1, hi - 1
        elif hi >= k:
            hi -= 1
            if hi < lo:
                return "#REF!"
        return f"{c1}{lo}:{c2}{hi}"

    out = {}
    for a, c in cells.items():
        r = int(a[1:])
        if r == k:
            continue
        c = dict(c)
        if c.get("v", "").startswith("="):
            c["v"] = REF.sub(ref, c["v"])
        out[f"{a[0]}{r - 1 if r > k else r}"] = c
    return out


# ------------------------------------------------------------------ start state
def make(rng, kind=None):
    kind = kind or rng.choice(KINDS)
    c0, r0 = rng.choice([(0, 1), (1, 2), (0, 3)])                # the table's top left corner: A1, B2 or A3
    cells = {}

    def put(c, r, v, **look):
        cells[addr(c, r)] = {"v": v if isinstance(v, str) else num(v), **{k: x for k, x in look.items() if x}}

    def table(r, head, rows):
        """Header in row r (bold, the titles of number columns to the right), then the rows. Returns the last row."""
        for i, label in enumerate(head):
            put(c0 + i, r, label, bold=True, align="right" if i else None)
        for j, row in enumerate(rows):
            for i, v in enumerate(row):
                put(c0 + i, r + 1 + j, v, fmt="currency" if head[i] in CURRENCY else None)
        return r + len(rows)

    if kind == "budget":
        n = rng.randint(4, 6)
        first = rng.randint(0, 12 - n)
        head, rows = ["Category"] + MONTHS[first:first + n], []
        for label in rng.sample(list(BUDGET), rng.randint(7, 9)):
            base = draw(rng, kind, label, None)
            rows.append([label] + [base if BUDGET[label][3] else draw(rng, kind, label, None) for _ in range(n)])
    elif kind == "stock":
        head = ["Item", "Quantity", "Unit price", "Reorder at"]
        rows = [[item] + [draw(rng, kind, item, col) for col in head[1:]] for item in rng.sample(STOCK, rng.randint(8, 10))]
    else:
        picks = sorted(rng.sample(range(len(ASSIGNMENTS)), rng.randint(4, 5)))
        head = ["Student"] + [ASSIGNMENTS[i] for i in picks]
        rows = [[name] + [draw(rng, kind, name, col) for col in head[1:]] for name in rng.sample(pools.FIRST, rng.randint(8, 10))]
    table(r0, head, rows)

    head2, labels, _ = LOWER[kind]
    r2 = rng.randint(30, 36)
    last = table(r2, head2, [[label] + [draw(rng, kind, label, col) for col in head2[1:]] for label in rng.sample(labels, rng.randint(3, 5))])
    put(c0, last + 1, "Total", bold=True)
    for i in (1, 2):
        put(c0 + i, last + 1, f"=SUM({addr(c0 + i, r2 + 1)}:{addr(c0 + i, last)})", bold=True, fmt="currency" if head2[i] in CURRENCY else None)

    return {"title": rng.choice(TITLES[kind]), "ncols": len(COLS), "nrows": NROWS, "cells": cells, "vals": compute_vals(cells),
            "ui": {"sel": "A1", "range": None, "edit": None, "clip": None}}


def default(rng):
    return make(rng)


# ------------------------------------------------------------------ reading a sheet back
class Table:
    """A table found in the cells: `head` [(title, column)], `cols` (the number columns), `rows`
    [(label, row)] without a final Total row, `r0` (header row), `last` (last data row)."""

    def __init__(self, cells, c0, r0):
        text = lambda c, r: cells.get(addr(c, r), {}).get("v", "") if c < len(COLS) and r <= NROWS else ""
        self.c0, self.r0, self.head, self.rows = c0, r0, [], []
        c = c0
        while text(c, r0):
            self.head.append((text(c, r0), c))
            c += 1
        r = r0 + 1
        while text(c0, r) and text(c0, r) != "Total":
            self.rows.append((text(c0, r), r))
            r += 1
        self.cols, self.last = self.head[1:], r - 1


def tables(s):
    """(kind, the main table, the second table further down)."""
    cells = s["cells"]
    filled = sorted((int(a[1:]), COLS.index(a[0])) for a, c in cells.items() if c.get("v"))
    r0, c0 = filled[0]
    main = Table(cells, c0, r0)
    r2 = next(r for r, _ in filled if r > main.last + 1)
    kind = {"Category": "budget", "Item": "stock", "Student": "grades"}[main.head[0][0]]
    return kind, main, Table(cells, c0, r2)


def sheet(st):
    return st["apps"]["sheet"]


def cell(a):
    return WIN + f'.sh-cell[data-arg="{a}"]'


def row_number(r):
    return WIN + f'.sh-rh[data-arg="{r}"]'


def set_header_bold(s, T, on):
    for _, c in T.head:
        if on:
            s["cells"][addr(c, T.r0)]["bold"] = True
        else:
            s["cells"][addr(c, T.r0)].pop("bold", None)


def vals_match(st, cells):
    """(ok, why): the app's computed values are those of the expected cells."""
    d = diff(sheet(st)["vals"], compute_vals(cells))
    return cond(not d, "the computed values are not those of the expected sheet: " + ", ".join(d[:4]))


def stream(S, n):
    """The episode's random stream, moved on by a task-specific amount, so that the tasks of one
    seed do not all pick the same row and column."""
    for _ in range(n):
        S.rng.random()
    return S.rng


def ask_set(rng, kind, row, col, v, old):
    if kind == "budget":
        return say(rng, f"Put {v} for {row} in {col}.", f"Change the {row} amount for {col} to {v}.")
    if kind == "stock":
        return say(rng, f"Set “{col}” for {row} to {v} in the stock list.", f"In the stock list, {row} should have {v} under “{col}”.")
    return say(rng, f"Change {row}'s {col} score to {v}.", f"{row}'s {col} score should be {v}, not {old}. Fix it in the grade sheet.")


# ------------------------------------------------------------------ tasks
@task("sheet.set_cell", "typing")
def set_cell(S):
    rng = stream(S, 0)
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    (row, r), (col, c) = rng.choice(T.rows), rng.choice(T.cols)
    a = addr(c, r)
    val = new_value(rng, kind, row, col, s["vals"][a])
    S.open("sheet")

    def check(st, init):
        exp = clone(sheet(init)["cells"])
        exp[a]["v"] = num(val)
        got = sheet(st)["vals"].get(a)
        return verdict(cond(is_num(got) and abs(got - val) < 1e-6, f"the cell holds {got!r}, not {spoken(val)}"),
                       only(st, init, f"sheet.cells.{a}.v", "sheet.vals.*"),
                       vals_match(st, exp))
    return Spec(request=ask_set(rng, kind, row, col, spoken(val), spoken(s["vals"][a])),
                steps=[Click(cell(a), f"Click the cell in the “{row}” row under “{col}”"), Type(spoken(val)), Key("enter")],
                check=check)


@task("sheet.column_total", "typing")
def column_total(S):
    rng = stream(S, 1)
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    col, c = T.cols[0] if kind == "stock" else rng.choice(T.cols)        # stock: the Quantity column
    fn = "AVERAGE" if kind == "grades" else "SUM"                          # nobody totals a class's scores
    a = addr(c, T.last + 1)
    nums = [s["vals"][addr(c, r)] for _, r in T.rows]
    want = sum(nums) / len(nums) if fn == "AVERAGE" else sum(nums)
    S.open("sheet")
    if kind == "budget":
        request = say(rng, f"Add a formula under the {col} column that totals the month.",
                      f"In the first empty cell below the {col} figures, put a formula that adds them all up.")
    elif kind == "stock":
        request = say(rng, f"Add a formula under the {col} column that totals it.",
                      "In the first empty cell below the quantities, put a formula that adds them all up.")
    else:
        request = say(rng, f"Add a formula under the {col} column that gives the class average.",
                      f"In the first empty cell below the {col} scores, put a formula that works out their average.")

    def check(st, init):
        got, v = sheet(st)["cells"].get(a), sheet(st)["vals"].get(a)
        return verdict(cond(got is not None and str(got.get("v", "")).startswith("="), "there is no formula in the cell below that column"),
                       cond(got and re.search(rf"(?<![A-Z]){COLS[c]}\d", str(got.get("v", "")).upper()), "the formula does not use the cells of that column"),
                       cond(is_num(v) and abs(v - want) < 1e-6, f"the formula gives {v!r}, not {want:g}"),
                       cond(set(got or {}) == {"v"}, "the cell was given formatting as well"),
                       only(st, init, f"sheet.cells.{a}", f"sheet.vals.{a}"))
    return Spec(request=request,
                steps=[Click(cell(a), f"Click the first empty cell below the numbers in the “{col}” column"),
                       Type(f"={fn}({addr(c, T.rows[0][1])}:{addr(c, T.last)})"), Key("enter")],
                check=check)


@task("sheet.bold_header", "chain")
def bold_header(S):
    rng = stream(S, 2)
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    set_header_bold(s, T, False)
    S.open("sheet")
    titles = [addr(c, T.r0) for _, c in T.head]
    whole_row = [addr(c, T.r0) for c in range(len(COLS))]

    def check(st, init):
        cells, exp = sheet(st)["cells"], clone(sheet(init)["cells"])
        for a in titles:
            exp[a]["bold"] = True
        # selecting the whole row makes its empty cells bold as well: that is the same answer
        got = {a: x for a, x in cells.items() if not (a in whole_row and a not in exp and x == {"bold": True})}
        d = diff(got, exp)
        return verdict(cond(all(cells.get(a, {}).get("bold") is True for a in titles), "the header row is not bold"),
                       cond(not d, "other cells changed: " + ", ".join(d[:4])),
                       only(st, init, "sheet.cells.*"))
    return Spec(request=say(rng, f"Make the header row of the {NAME[kind]} bold.",
                            f"The column titles at the top of the {NAME[kind]} ({T.head[0][0]}, {T.head[1][0]} and so on) should be bold."),
                steps=[Click(row_number(T.r0), f"Click the row number {T.r0} at the left edge of the grid, the row of “{T.head[0][0]}”"),
                       Click(WIN + '.tb-btn[data-act="bold"]', "Click the Bold button, the letter B in the toolbar")],
                check=check)


@task("sheet.delete_row", "menu")
def delete_row(S):
    rng = stream(S, 3)
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    row, r = rng.choice(T.rows)
    S.open("sheet")
    if kind == "budget":
        request = say(rng, f"Delete the {row} row from the budget.", f"Remove the whole {row} row from the budget table.")
    elif kind == "stock":
        request = say(rng, f"Delete the row for {row} from the stock list.", f"We no longer stock {row}. Remove that whole row from the list.")
    else:
        request = say(rng, f"Delete {row}'s row from the grade sheet.", f"{row} has left the class. Remove that whole row from the grade sheet.")

    def check(st, init):
        cells, exp = sheet(st)["cells"], without_row(sheet(init)["cells"], r)
        d = diff(cells, exp)
        return verdict(cond(all(x.get("v") != row for x in cells.values()), f"the {row} row is still there"),
                       cond(not d, "the sheet is not what deleting that row gives: " + ", ".join(d[:4])),
                       vals_match(st, exp),
                       only(st, init, "sheet.cells.*", "sheet.vals.*"))
    return Spec(request=request,
                steps=[Click(row_number(r), f"Right-click the row number {r} at the left edge of the grid, the row of “{row}”", button="right"),
                       Click('.menu-item:has-text("Delete Row")', "Click “Delete Row” in the menu")],
                check=check)


@task("sheet.currency_column", "drag")
def currency_column(S):
    rng = stream(S, 4)
    if tables(S.apps["sheet"])[0] == "grades":                             # scores are not money: this task wants a budget or a stock list
        S.apps["sheet"] = make(rng, rng.choice(["budget", "stock"]))
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    col, c = rng.choice(T.cols) if kind == "budget" else next(x for x in T.cols if x[0] == "Unit price")
    column = [addr(c, r) for _, r in T.rows]
    for a in column:
        s["cells"][a].pop("fmt", None)
    S.open("sheet")
    if kind == "budget":
        request = say(rng, f"Format the {col} amounts in the budget as currency.", f"Show the numbers in the {col} column of the budget as currency.")
    else:
        request = say(rng, "Format the unit prices in the stock list as currency.", "Show the numbers in the Unit price column as currency.")

    def check(st, init):
        cells = sheet(st)["cells"]
        return verdict(cond(all(cells.get(a, {}).get("fmt") == "currency" for a in column), "not every number of that column is formatted as currency"),
                       only(st, init, *[f"sheet.cells.{a}.fmt" for a in column]))
    return Spec(request=request,
                steps=[Drag(cell(column[0]), cell(column[-1]), f"the first number under “{col}”, in the “{T.rows[0][0]}” row",
                            f"the last number under “{col}”, in the “{T.rows[-1][0]}” row"),
                       Click(WIN + '.popup[data-select="format"]', "Click the number format pop-up button in the toolbar, which says “Automatic”"),
                       Click('.menu-item:has-text("Currency")', "Click “Currency” in the menu")],
                check=check)


@task("sheet.lower_table", "scroll")
def lower_table(S):
    rng = stream(S, 5)
    s = S.apps["sheet"]
    kind, _, T = tables(s)
    (row, r), (col, c) = rng.choice(T.rows), rng.choice(T.cols)
    a = addr(c, r)
    val = new_value(rng, kind, row, col, s["vals"][a])
    name = LOWER[kind][2]
    S.open("sheet")

    def check(st, init):
        exp = clone(sheet(init)["cells"])
        exp[a]["v"] = num(val)
        got = sheet(st)["vals"].get(a)
        return verdict(cond(is_num(got) and abs(got - val) < 1e-6, f"the cell holds {got!r}, not {spoken(val)}"),
                       only(st, init, f"sheet.cells.{a}.v", "sheet.vals.*"),
                       vals_match(st, exp))                                   # the Total below it follows
    return Spec(request=say(rng, f"Further down this sheet there is a small table of {name}. Set “{col}” for {row} to {spoken(val)} there.",
                            f"In the {name} table lower down this sheet, {row} should have {spoken(val)} under “{col}”."),
                steps=[Reveal(cell(a)), Click(cell(a), f"Click the cell in the “{row}” row under “{col}”"), Type(spoken(val)), Key("enter")],
                check=check)


@task("sheet.copy_cell", "shortcut")
def copy_cell(S):
    rng = stream(S, 6)
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    if kind == "budget":                                                   # along a row: one month's amount into another month
        (row, r), ((col, c), (col2, c2)) = rng.choice(T.rows), rng.sample(T.cols, 2)
        src, tgt = addr(c, r), addr(c2, r)
        request = say(rng, f"Copy the {row} amount for {col} into {col2}.", f"{row} for {col2} is the same as for {col}. Copy that amount across.")
        point, point2 = f"Click the cell in the “{row}” row under “{col}”", f"Click the cell in the “{row}” row under “{col2}”"
    else:                                                                  # down a column: one row's figure into another row
        ((row, r), (row2, r2)), (col, c) = rng.sample(T.rows, 2), rng.choice(T.cols)
        src, tgt = addr(c, r), addr(c, r2)
        if kind == "stock":
            request = say(rng, f"Copy the “{col}” value of {row} into the same column for {row2}.", f"{row2} should have the same “{col}” value as {row}. Copy it over.")
        else:
            request = say(rng, f"Copy {row}'s {col} score into {row2}'s {col} cell.", f"{row2} got the same {col} score as {row}. Copy {row}'s score over.")
        point, point2 = f"Click the cell in the “{row}” row under “{col}”", f"Click the cell in the “{row2}” row under “{col}”"
    if s["vals"][src] == s["vals"][tgt]:                                   # the copy must change something
        s["cells"][src]["v"] = num(new_value(rng, kind, row, col, s["vals"][tgt]))
        s["vals"] = compute_vals(s["cells"])
    S.open("sheet")

    def check(st, init):
        cells, was = sheet(st)["cells"], sheet(init)["cells"]
        return verdict(cond(cells.get(tgt) == was[src], "that cell does not hold a copy of the other one"),
                       only(st, init, f"sheet.cells.{tgt}.*", f"sheet.vals.{tgt}"))
    return Spec(request=request, steps=[Click(cell(src), point), Key("cmd+c"), Click(cell(tgt), point2), Key("cmd+v")], check=check)


@task("sheet.header_already_bold", "already_done")
def header_already_bold(S):
    rng = stream(S, 7)
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    set_header_bold(s, T, True)
    S.open("sheet")
    return Spec(request=say(rng, f"Make the header row of the {NAME[kind]} bold.",
                            f"The column titles at the top of the {NAME[kind]} should be in bold. Make them bold if they are not."),
                steps=[], kind="already_done", check=unchanged)


@task("sheet.missing_row", "infeasible")
def missing_row(S):
    rng = stream(S, 8)
    s = S.apps["sheet"]
    kind, T, _ = tables(s)
    used = {x.get("v") for x in s["cells"].values()}
    ghost = rng.choice([x for x in {"budget": list(BUDGET), "stock": STOCK, "grades": pools.FIRST}[kind] if x not in used])
    col, _ = rng.choice(T.cols)
    v = spoken(new_value(rng, kind, ghost, col, None))
    S.open("sheet")
    if kind == "budget":
        request = say(rng, f"Change the {ghost} amount for {col} to {v}.", f"The {ghost} figure for {col} is wrong. Correct it to {v}.")
    elif kind == "stock":
        request = say(rng, f"Change “{col}” for {ghost} to {v} in the stock list.", f"The “{col}” figure for {ghost} in the stock list is wrong. Correct it to {v}.")
    else:
        request = say(rng, f"Change {ghost}'s {col} score to {v}.", f"{ghost}'s {col} score is wrong. Correct it to {v}.")
    return Spec(request=request, steps=[], kind="infeasible", check=unchanged)
