"""Replay pages: one static HTML page per run, and an index of all runs.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    python -m taskenv.viewer --runs ~/Bonsai-demo/taskenv-runs

Writes <runs>/<name>/index.html for every run (it shows the screenshots in <name>/shots/ next to
it) and <runs>/index.html. A page replays each episode step by step: the screenshot the model
saw, where it acted, what it wrote, how the environment read it, and the final verdict.
"""
import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taskenv import actions as A  # noqa: E402

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { --bg: #f4f4f1; --panel: #ffffff; --ink: #1c1c1a; --ink2: #6b6b66; --line: #dddcd6; --ok: #1f8a4c; --bad: #c8372d; --mark: #ff2d78; --sel: #e9e8e2; --mono: ui-monospace, "SF Mono", Menlo, monospace; }
@media (prefers-color-scheme: dark) { :root { --bg: #161615; --panel: #1f1f1d; --ink: #ecebe6; --ink2: #9a9992; --line: #33332f; --sel: #2c2c29; --ok: #4cc27f; --bad: #f0685d; } }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--ink); font: 14px/1.45 -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif; height: 100vh; display: flex; flex-direction: column; }
header { flex: none; padding: 12px 18px; border-bottom: 1px solid var(--line); display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; }
header h1 { font-size: 16px; font-weight: 650; }
header .meta { color: var(--ink2); font-size: 13px; }
header .score { margin-left: auto; font-variant-numeric: tabular-nums; font-weight: 600; }
header a { color: inherit; }
main { flex: 1; min-height: 0; display: flex; }
nav { flex: none; width: 300px; border-right: 1px solid var(--line); display: flex; flex-direction: column; }
.filters { flex: none; display: flex; gap: 6px; padding: 10px 12px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.filters button { font: inherit; font-size: 12.5px; color: var(--ink); background: none; border: 1px solid var(--line); border-radius: 999px; padding: 3px 11px; cursor: pointer; }
.filters button.on { background: var(--ink); color: var(--bg); border-color: var(--ink); }
#list { flex: 1; overflow-y: auto; padding: 6px; }
.ep { display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.ep:hover { background: var(--sel); } .ep.on { background: var(--sel); font-weight: 600; }
.dot { flex: none; width: 9px; height: 9px; border-radius: 50%; background: var(--bad); } .dot.ok { background: var(--ok); }
.ep .seed { margin-left: auto; color: var(--ink2); font-size: 11.5px; font-weight: 400; font-variant-numeric: tabular-nums; }
section { flex: 1; min-width: 0; overflow-y: auto; padding: 16px 20px 28px; }
.req { font-size: 17px; font-weight: 600; margin-bottom: 4px; }
.verdict { display: flex; gap: 10px; align-items: baseline; margin-bottom: 12px; color: var(--ink2); font-size: 13px; flex-wrap: wrap; }
.badge { font-weight: 700; padding: 1px 9px; border-radius: 999px; color: #fff; background: var(--bad); font-size: 12.5px; } .badge.ok { background: var(--ok); }
.stage { position: relative; width: 100%; max-width: 1180px; aspect-ratio: 1440 / 900; background: #000; border-radius: 8px; overflow: hidden; border: 1px solid var(--line); }
.stage img, .stage svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.stage .noimg { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
.bar { display: flex; align-items: center; gap: 8px; margin: 10px 0; flex-wrap: wrap; max-width: 1180px; }
.bar button { font: inherit; background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: 6px; padding: 4px 12px; cursor: pointer; }
.chips { display: flex; gap: 4px; flex-wrap: wrap; }
.chip { min-width: 26px; text-align: center; font-size: 12px; padding: 3px 7px; border-radius: 5px; border: 1px solid var(--line); cursor: pointer; font-variant-numeric: tabular-nums; background: var(--panel); }
.chip.on { background: var(--ink); color: var(--bg); border-color: var(--ink); } .chip.bad { border-color: var(--bad); color: var(--bad); } .chip.bad.on { background: var(--bad); color: #fff; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; max-width: 1180px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; min-width: 0; }
.card h3 { font-size: 11.5px; font-weight: 600; color: var(--ink2); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 5px; }
pre { font: 12.5px/1.45 var(--mono); white-space: pre-wrap; word-break: break-word; max-height: 260px; overflow-y: auto; }
.kv { display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; font-size: 13px; } .kv span:nth-child(odd) { color: var(--ink2); }
.err { color: var(--bad); }
@media (max-width: 900px) { nav { width: 210px; } .cols { grid-template-columns: 1fr; } }
</style></head><body>
<header><h1>__TITLE__</h1><span class="meta">__META__</span><span class="score" id="score"></span><a class="meta" href="../index.html">all runs</a></header>
<main><nav><div class="filters" id="filters"></div><div id="list"></div></nav>
<section><div class="req" id="req"></div><div class="verdict" id="verdict"></div>
<div class="stage"><img id="shot" alt=""><div class="noimg" id="noimg">screenshot not copied to this machine</div><svg id="ov" viewBox="0 0 1440 900"></svg></div>
<div class="bar"><button id="prev">◀</button><button id="next">▶</button><div class="chips" id="chips"></div></div>
<div class="cols"><div class="card"><h3>What the model wrote</h3><pre id="raw"></pre></div>
<div class="card"><h3>What the environment did</h3><div class="kv" id="kv"></div></div></div></section></main>
<script>
const RUN = __DATA__;
const $ = id => document.getElementById(id);
let filter = 'all', cur = 0, step = 0, shown = [];
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
function listing() {
  shown = RUN.episodes.map((e, i) => i).filter(i => filter === 'all' || (filter === 'pass') === RUN.episodes[i].success || filter === RUN.episodes[i].category);
  $('list').innerHTML = shown.map(i => { const e = RUN.episodes[i]; return `<div class="ep${i === cur ? ' on' : ''}" data-i="${i}"><span class="dot${e.success ? ' ok' : ''}"></span><span>${esc(e.task)}</span><span class="seed">${e.seed}</span></div>`; }).join('');
  const cats = [...new Set(RUN.episodes.map(e => e.category))];
  $('filters').innerHTML = [['all', 'All'], ['pass', 'Passed'], ['fail', 'Failed'], ...cats.map(c => [c, c.replace('_', ' ')])].map(([k, l]) => `<button class="${k === filter ? 'on' : ''}" data-f="${k}">${l}</button>`).join('');
  const ok = RUN.episodes.filter(e => e.success).length;
  $('score').textContent = `${ok} of ${RUN.episodes.length} tasks done (${Math.round(100 * ok / RUN.episodes.length)}%)`;
}
function mark(a, s) {
  let o = '';
  const ring = (x, y, label) => `<circle cx="${x}" cy="${y}" r="17" fill="none" stroke="#fff" stroke-width="6"/><circle cx="${x}" cy="${y}" r="17" fill="rgba(255,45,120,.18)" stroke="#ff2d78" stroke-width="3.5"/><circle cx="${x}" cy="${y}" r="3.2" fill="#ff2d78"/>` +
    (label ? `<text x="${x + 24}" y="${y - 16}" font-size="19" font-weight="700" fill="#ff2d78" stroke="#fff" stroke-width="4.5" paint-order="stroke" font-family="-apple-system, Arial">${esc(label)}</text>` : '');
  const arrow = (x1, y1, x2, y2) => { const t = Math.atan2(y2 - y1, x2 - x1), h = 16, p = (d) => `${x2 - h * Math.cos(t + d)},${y2 - h * Math.sin(t + d)}`;
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#fff" stroke-width="7"/><line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#ff2d78" stroke-width="3.5"/><polygon points="${x2},${y2} ${p(.45)} ${p(-.45)}" fill="#ff2d78" stroke="#fff" stroke-width="1.5"/>`; };
  for (const b of (s.boxes || [])) if (b) o += `<rect x="${b[0]}" y="${b[1]}" width="${b[2] - b[0]}" height="${b[3] - b[1]}" fill="none" stroke="#19c463" stroke-width="2.5" stroke-dasharray="7 5"/>`;
  if (!a) return o;
  if (a.type === 'click') o += ring(a.x, a.y, a.button === 'right' ? 'right-click' : a.count === 2 ? 'double-click' : a.count === 3 ? 'triple-click' : 'click');
  else if (a.type === 'move') o += ring(a.x, a.y, 'move');
  else if (a.type === 'drag') o += arrow(a.x1, a.y1, a.x2, a.y2) + ring(a.x1, a.y1, 'drag') + ring(a.x2, a.y2, '');
  else if (a.type === 'scroll') o += arrow(a.x, a.y, a.x + Math.sign(a.dx || 0) * 80, a.y + Math.sign(a.dy || 0) * 80) + ring(a.x, a.y, 'scroll');
  else if (['type', 'key', 'wait', 'say', 'done'].includes(a.type)) {
    const t = a.type === 'type' ? 'type  ' + JSON.stringify(a.text) : a.type === 'key' ? 'press  ' + a.keys : a.type === 'say' ? 'say  ' + JSON.stringify(a.text) : a.type === 'done' ? (a.status === 'infeasible' ? 'stop: cannot be done' : 'stop: done') : 'wait';
    const w = Math.min(1100, 60 + t.length * 13);
    o += `<rect x="${720 - w / 2}" y="806" width="${w}" height="46" rx="23" fill="rgba(20,20,20,.86)" stroke="#ff2d78" stroke-width="2.5"/><text x="720" y="837" text-anchor="middle" font-size="22" font-weight="600" fill="#fff" font-family="-apple-system, Arial">${esc(t.length > 80 ? t.slice(0, 78) + '…' : t)}</text>`;
  }
  return o;
}
function show() {
  const e = RUN.episodes[cur], n = e.steps.length; step = Math.max(0, Math.min(n, step));
  document.querySelectorAll('.ep').forEach(x => x.classList.toggle('on', +x.dataset.i === cur));
  $('req').textContent = '“' + e.request + '”';
  $('verdict').innerHTML = `<span class="badge${e.success ? ' ok' : ''}">${e.success ? 'DONE' : 'NOT DONE'}</span><span>${esc(e.why || '')}</span><span>${esc(e.task)} · seed ${e.seed} · ${esc(e.category.replace('_', ' '))} · needs ${e.needed == null ? '?' : e.needed} step${e.needed === 1 ? '' : 's'}, used ${e.n_steps} of ${e.limit}${e.stopped ? '' : ' · did not stop by itself'}</span>`;
  $('chips').innerHTML = e.steps.map((s, i) => `<span class="chip${i === step ? ' on' : ''}${s.action ? '' : ' bad'}" data-s="${i}">${i + 1}</span>`).join('') + `<span class="chip${step === n ? ' on' : ''}" data-s="${n}">end</span>`;
  const s = step < n ? e.steps[step] : null, file = s ? s.shot : e.last_shot;
  $('shot').style.display = file ? '' : 'none'; $('noimg').style.display = file ? 'none' : '';
  if (file) { $('shot').src = 'shots/' + file; $('shot').onerror = () => { $('shot').style.display = 'none'; $('noimg').style.display = ''; }; }
  $('ov').innerHTML = s ? mark(s.action, s) : '';
  $('raw').textContent = s ? (s.instruction ? 'Asked: ' + s.instruction + '\n\n' : '') + (s.raw || '') : 'Final state of the screen.\n\n' + (e.events || []).map(v => v.join('  ')).slice(-14).join('\n');
  const kv = s ? [['Action', s.action ? s.text : 'none (the step is lost)'], ['Seconds', s.seconds], ...(s.inside ? [['Inside the element', s.inside.map(v => v ? 'yes' : 'no').join(', ')]] : []), ...(s.error ? [['Problem', s.error]] : [])]
    : [['Verdict', e.success ? 'done' : 'not done'], ['Reason', e.why || ''], ['Stopped by itself', e.stopped ? 'yes' + (e.status === 'infeasible' ? ', saying it cannot be done' : '') : 'no'], ['Unreadable actions', e.invalid]];
  $('kv').innerHTML = kv.map(([k, v]) => `<span>${esc(k)}</span><span class="${k === 'Problem' ? 'err' : ''}">${esc(v)}</span>`).join('');
}
$('list').onclick = ev => { const t = ev.target.closest('.ep'); if (t) { cur = +t.dataset.i; step = 0; show(); } };
$('filters').onclick = ev => { const t = ev.target.closest('button'); if (t) { filter = t.dataset.f; listing(); if (!shown.includes(cur) && shown.length) { cur = shown[0]; step = 0; } listing(); show(); } };
$('chips').onclick = ev => { const t = ev.target.closest('.chip'); if (t) { step = +t.dataset.s; show(); } };
$('prev').onclick = () => { step--; show(); }; $('next').onclick = () => { step++; show(); };
document.onkeydown = ev => {
  if (ev.key === 'ArrowLeft') { step--; show(); } else if (ev.key === 'ArrowRight') { step++; show(); }
  else if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') { const i = shown.indexOf(cur) + (ev.key === 'ArrowDown' ? 1 : -1); if (shown[i] != null) { cur = shown[i]; step = 0; show(); const el = document.querySelector('.ep.on'); if (el) el.scrollIntoView({block: 'nearest'}); } ev.preventDefault(); }
};
listing(); show();
</script></body></html>"""

INDEX = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Task environment runs</title>
<style>
:root { --bg: #f4f4f1; --panel: #fff; --ink: #1c1c1a; --ink2: #6b6b66; --line: #dddcd6; }
@media (prefers-color-scheme: dark) { :root { --bg: #161615; --panel: #1f1f1d; --ink: #ecebe6; --ink2: #9a9992; --line: #33332f; } }
body { background: var(--bg); color: var(--ink); font: 15px/1.5 -apple-system, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 28px 16px 60px; }
.wrap { max-width: 980px; margin: 0 auto; } h1 { font-size: 22px; margin: 0 0 4px; } p { color: var(--ink2); margin: 0 0 18px; }
.tw { overflow-x: auto; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; } th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
th { font-size: 12px; color: var(--ink2); font-weight: 600; } tr:last-child td { border-bottom: none; } a { color: inherit; font-weight: 600; }
</style></head><body><div class="wrap"><h1>Task environment runs</h1>
<p>Each row is one run of one agent through the tasks. Open a run to replay every episode step by step. Web replicas of Mac apps, not real macOS; test only, never training data.</p>
<div class="tw"><table><tr><th>Run</th><th>Agent</th><th>Model</th><th>Input</th><th>Tasks done</th><th>Episodes</th><th>Seeds</th></tr>__ROWS__</table></div></div></body></html>"""


def build_run(run_dir):
    meta = json.load(open(os.path.join(run_dir, "meta.json")))
    eps = {}
    for line in open(os.path.join(run_dir, "episodes.jsonl")):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        eps[(r["task"], r["seed"])] = r
    have = set(os.listdir(os.path.join(run_dir, "shots"))) if os.path.isdir(os.path.join(run_dir, "shots")) else set()
    out = []
    for r in eps.values():
        steps = []
        for s in r["steps"]:
            raw = s.get("raw", "")
            steps.append({"shot": s["shot"] if s.get("shot") in have else None, "raw": raw if len(raw) < 3000 else raw[:3000] + " …",
                          "action": s["action"], "text": A.describe(s["action"]) if s["action"] else "", "seconds": s.get("model_seconds", s["seconds"]),
                          "error": s.get("error"), "instruction": s.get("instruction"), "inside": s.get("inside"), "boxes": s.get("boxes")})
        out.append({k: r.get(k) for k in ("task", "seed", "app", "category", "kind", "request", "limit", "success", "why", "stopped", "status", "n_steps", "invalid", "needed", "events")}
                   | {"steps": steps, "last_shot": r.get("last_shot") if r.get("last_shot") in have else None})
    out.sort(key=lambda e: (e["seed"], e["task"]))
    name = os.path.basename(run_dir.rstrip("/"))
    who = {"oracle": "Scripted oracle", "noop": "Does nothing", "random": "Random clicks"}.get(meta.get("agent")) or f"{meta.get('model')}{' (' + meta['tag'] + ')' if meta.get('tag') else ''}"
    info = f"{meta.get('agent')} mode" + (f" · input {meta.get('input', '')[1:]} px" if meta.get("model") else "") + f" · {meta.get('time_utc', '')} UTC · commit {(meta.get('git_commit') or '')[:7]}"
    page = (PAGE.replace("__TITLE__", html.escape(f"{who}: {name}")).replace("__META__", html.escape(info))
            .replace("__DATA__", json.dumps({"name": name, "meta": {k: meta.get(k) for k in ("agent", "model", "tag", "input", "ask", "prompt")}, "episodes": out}, ensure_ascii=False).replace("</", "<\\/")))
    open(os.path.join(run_dir, "index.html"), "w").write(page)
    return name, meta, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    args = ap.parse_args()
    root = os.path.expanduser(args.runs)
    rows = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if os.path.isfile(os.path.join(d, "meta.json")) and os.path.isfile(os.path.join(d, "episodes.jsonl")):
            name, meta, eps = build_run(d)
            ok = sum(e["success"] for e in eps)
            rows.append((meta.get("agent") or "", -ok / max(1, len(eps)),
                         f"<tr><td><a href='{html.escape(name)}/index.html'>{html.escape(name)}</a></td><td>{html.escape(meta.get('agent') or '')}</td>"
                         f"<td>{html.escape((meta.get('model') or '') + (' (' + meta['tag'] + ')' if meta.get('tag') else ''))}</td><td>{html.escape((meta.get('input') or '')[1:] + ' px' if meta.get('model') else '')}</td>"
                         f"<td>{ok} of {len(eps)} ({round(100 * ok / max(1, len(eps)))}%)</td><td>{len(eps)}</td><td>{html.escape(', '.join(str(s) for s in sorted({e['seed'] for e in eps})))}</td></tr>"))
    rows.sort()
    open(os.path.join(root, "index.html"), "w").write(INDEX.replace("__ROWS__", "".join(r[2] for r in rows)))
    print(f"{len(rows)} run pages -> {os.path.join(root, 'index.html')}")


if __name__ == "__main__":
    main()
