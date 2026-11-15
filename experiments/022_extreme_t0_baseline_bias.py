# Experiment 022, baseline and trial T0 (coordinate bias, analysis only).
#
# Baseline: v3-gentle measured the way every trial is measured, plus 896 px and Mac app windows.
# T0: from the baseline's generated answers on the select set, the mean signed error (answer minus
# target centre, in thousandths of the image) in x and y: overall, by target size and by screen
# third. If there is a consistent offset above 3 thousandths, it is subtracted from the generated
# answers on the report set and the hits are counted again. No training, no weights change.
exec(open(f"{lab.root}/experiments/022_extreme_common.py").read())
import statistics

t0 = time.time()
if x22_base_score is None:
    row = x22_measure("base", "v3-gentle", t0, extra=True)
    x22_base_score = (row["select"], row["report"])
    x22_base_row = row
print("vision modules:", [n for n, _ in lab.B.model.visual.named_children()],
      "| merger:", [(n, type(m).__name__) for n, m in lab.B.model.visual.merger.named_children()], flush=True)

# ---- T0
t0 = time.time()
g = lab.score(lab.B, x22_sel, tag="022x:T0:generated:select")
sel_pts = x22_points(g["answers"])
rep_pts = x22_points(x22_base_row["gen_answers"])


def errors(points, samples):
    """(dx, dy, sample) per answered case: answer minus target centre, thousandths."""
    return [(p[0] - (it["box1000"][0] + it["box1000"][2]) / 2, p[1] - (it["box1000"][1] + it["box1000"][3]) / 2, it)
            for p, it in zip(points, samples) if p is not None]


def summary(rows):
    if not rows:
        return None
    dx, dy = [r[0] for r in rows], [r[1] for r in rows]
    n = len(rows)
    se = lambda v: (statistics.pstdev(v) / n ** 0.5) if n > 1 else 0.0
    return {"n": n, "mean_dx": round(statistics.mean(dx), 2), "se_dx": round(se(dx), 2), "median_dx": round(statistics.median(dx), 2),
            "mean_dy": round(statistics.mean(dy), 2), "se_dy": round(se(dy), 2), "median_dy": round(statistics.median(dy), 2)}


def show(label, s):
    if s:
        print("  %-30s n %3d   dx mean %+6.2f (se %.2f) median %+5.1f   dy mean %+6.2f (se %.2f) median %+5.1f" % (
            label, s["n"], s["mean_dx"], s["se_dx"], s["median_dx"], s["mean_dy"], s["se_dy"], s["median_dy"]), flush=True)


err = errors(sel_pts, x22_sel)
# answers on the wrong element are hundreds of thousandths off and say nothing about a calibration
# offset; "near" keeps the answers within 60 thousandths of the centre on both axes
near = [r for r in err if abs(r[0]) <= 60 and abs(r[1]) <= 60]
T0 = {"select_hits": x22_hits(sel_pts, x22_sel), "select_n": len(x22_sel), "all": summary(err), "near": summary(near), "splits": {}}
print("T0: select generated %d/%d; %d answered, %d within 60 thousandths of the centre" % (
    T0["select_hits"], len(x22_sel), len(err), len(near)))
show("all answers", T0["all"]); show("near answers", T0["near"])
area = lambda it: (it["box1000"][2] - it["box1000"][0]) * (it["box1000"][3] - it["box1000"][1])
cuts = sorted(area(r[2]) for r in near)
a1, a2 = cuts[len(cuts) // 3], cuts[2 * len(cuts) // 3]
splits = {
    "size: small third": lambda it: area(it) < a1, "size: middle third": lambda it: a1 <= area(it) < a2, "size: large third": lambda it: area(it) >= a2,
    "x: left third": lambda it: it["target"][0] < 333, "x: middle third": lambda it: 333 <= it["target"][0] < 667, "x: right third": lambda it: it["target"][0] >= 667,
    "y: top third": lambda it: it["target"][1] < 333, "y: middle third": lambda it: 333 <= it["target"][1] < 667, "y: bottom third": lambda it: it["target"][1] >= 667,
    "desktop": lambda it: it["group"] == "desktop", "mobile": lambda it: it["group"] == "mobile", "web": lambda it: it["group"] == "web",
}
for label, f in splits.items():
    T0["splits"][label] = summary([r for r in near if f(r[2])])
    show(label + " (near)", T0["splits"][label])

# ---- corrections, fitted on select only, applied to report
base_hits = x22_hits(rep_pts, x22_rep)
ox, oy = T0["near"]["mean_dx"], T0["near"]["mean_dy"]
mx, my = T0["near"]["median_dx"], T0["near"]["median_dy"]


def corrected(points, fx, fy):
    return [None if p is None else (p[0] - fx(p[0]), p[1] - fy(p[1])) for p in points]


def line_fit(xs, ys):
    """Least-squares y = a + b x."""
    n, sx, sy = len(xs), sum(xs), sum(ys)
    b = (n * sum(x * y for x, y in zip(xs, ys)) - sx * sy) / max(1e-9, n * sum(x * x for x in xs) - sx * sx)
    return (sy - b * sx) / n, b


ax, bx = line_fit([r[2]["target"][0] + r[0] for r in near], [r[0] for r in near])     # error against the answered coordinate
ay, by = line_fit([r[2]["target"][1] + r[1] for r in near], [r[1] for r in near])
T0["report_base_hits"] = base_hits
T0["corrections"] = {
    "mean offset": {"dx": ox, "dy": oy, "report_hits": x22_hits(corrected(rep_pts, lambda v: ox, lambda v: oy), x22_rep),
                    "select_hits": x22_hits(corrected(sel_pts, lambda v: ox, lambda v: oy), x22_sel)},
    "median offset": {"dx": mx, "dy": my, "report_hits": x22_hits(corrected(rep_pts, lambda v: mx, lambda v: my), x22_rep),
                      "select_hits": x22_hits(corrected(sel_pts, lambda v: mx, lambda v: my), x22_sel)},
    "line per axis": {"x": [round(ax, 2), round(bx, 4)], "y": [round(ay, 2), round(by, 4)],
                      "report_hits": x22_hits(corrected(rep_pts, lambda v: ax + bx * v, lambda v: ay + by * v), x22_rep),
                      "select_hits": x22_hits(corrected(sel_pts, lambda v: ax + bx * v, lambda v: ay + by * v), x22_sel)},
}
# what any constant shift could give at best on report (fitted on report itself: an upper bound, not a result)
best = max(((x22_hits(corrected(rep_pts, lambda v, a=a: a, lambda v, b=b: b), x22_rep), a, b) for a in range(-10, 11) for b in range(-10, 11)))
T0["oracle_constant_shift_on_report"] = {"hits": best[0], "dx": best[1], "dy": best[2]}
print("T0: report generated %d/%d as answered" % (base_hits, len(x22_rep)))
for k, v in T0["corrections"].items():
    print("  %-14s %s -> report %d (%+d), select %d (%+d)" % (k, {a: b for a, b in v.items() if "hits" not in a}, v["report_hits"],
                                                         v["report_hits"] - base_hits, v["select_hits"], v["select_hits"] - T0["select_hits"]))
print("  best constant shift chosen on the report set itself (upper bound): %d hits at dx %+d, dy %+d" % best, flush=True)
T0["minutes"] = round((time.time() - t0) / 60, 1)
x22_notes.append({"T0": T0})
x22_save()
