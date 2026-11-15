// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Sheets: a spreadsheet in the manner of Numbers / Excel for Mac.
// State: {title, ncols, nrows, cells, vals, ui}
//   cells  {"B4": {v, bold, italic, align, fmt}}: only cells with content or formatting. v is the raw text ("1450", "Rent",
//          "=SUM(B2:B9)"); align is left | center | right; fmt is number | currency | percent. Unset properties are left out.
//   vals   {"B4": number | text | "#ERROR"}: the computed value of every non-empty cell, rewritten after every change.
//   ui     sel "B4" (the active cell); range "B2:D9" | null (top left : bottom right; sel is one of its corners);
//          edit {text, bar} | null (bar: the typing happens in the formula bar, not in the cell); clip {w, h, cells} | null.
// Rules that are kept simple on purpose:
//   Formatting  Bold, Italic, alignment and number format apply to every cell of the selection, empty ones included (an empty
//               cell then exists as {bold: true}). A toggle looks at the non-empty cells of the selection: all on -> off.
//   Sorting     acts on the table around the active cell: the run of consecutive non-empty rows that contains it (with a whole
//               column selected: the first such run that has something in that column). Its first row is the header and
//               stays; rows at its end that contain a formula are totals and stay; the rows between are reordered as whole
//               rows (all columns) by the computed value in the active cell's column: numbers, then text (case ignored),
//               then empty cells. Formulas inside the sorted rows move as text and are NOT rewritten.
//   Rows        inserting or deleting a row moves the cells below it, and the row numbers inside formulas follow (a reference
//               to a deleted row becomes #REF!, which shows as #ERROR). Content pushed past the last row is lost.
//               The + button of the toolbar inserts a row below the selection; Delete Row removes every row of the selection.
//   Pasting     copies raw text and formatting; the references of a pasted formula are NOT adjusted. Cut empties the cells
//               at once. One copied cell pasted on a range fills the range.
//   Typing      "$1,450.50" or "12.5%" is stored as the plain number and sets the cell's format if it has none.
(() => {
const {esc, icon} = TE;
TE.addIcons({
  'sh-left': 'M4 5.5h16M4 10h10M4 14.5h16M4 19h10',
  'sh-center': 'M4 5.5h16M7 10h10M4 14.5h16M7 19h10',
  'sh-right': 'M4 5.5h16M10 10h10M4 14.5h16M10 19h10',
  'sh-italic': 'M10.5 5h7.5M6 19h7.5M14.5 5l-5 14',
  'sh-arrow': 'M12 4v15.5M6.5 14L12 19.5l5.5-5.5',
  'sh-rowadd': 'M3.5 5h17v5.5h-17zM3.5 10.5V18H11M17.5 13.5v7.5M13.75 17.25h7.5',
});
const COLS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', ERR = '#ERROR', NONE = {};
const FORMATS = [['Automatic', null], ['Number', 'number'], ['Currency', 'currency'], ['Percent', 'percent']];
const KEEP = {editing: 1, fx_input: 1, fx_focus: 1, edit_commit: 1, edit_tab: 1, edit_accept: 1, edit_cancel: 1};   // handlers that deal with the open edit themselves
const DOC = '<svg class="sh-doc" width="17" height="17" viewBox="0 0 17 17"><rect x="1" y="1" width="15" height="15" rx="3.6" fill="#2db55d"/><path d="M4.2 6.6h8.6M4.2 10.4h8.6M7.2 4.2v8.6" stroke="#fff" stroke-width="1.25" stroke-linecap="round" fill="none"/></svg>';
// Tab in a text field does not reach an app through the shell (it has hooks for Return and Escape only), so the two text
// fields of this app carry this one inline handler. It only forwards the key to the ordinary handler on.edit_tab.
const TAB = ` onkeydown="if(event.key==='Tab'&amp;&amp;!event.metaKey&amp;&amp;!event.ctrlKey){event.preventDefault();TE.dispatch('sheet','edit_tab',event.shiftKey?'left':'right',this.value,this)}"`;

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const addr = (c, r) => COLS[c] + (r + 1);                                  // column and row counted from 0
const rc = a => { const m = /^([A-Z])([1-9]\d*)$/.exec(a || ''); return m ? [COLS.indexOf(m[1]), +m[2] - 1] : null; };
const span = (a, b) => { const [c1, r1] = rc(a), [c2, r2] = rc(b); return addr(Math.min(c1, c2), Math.min(r1, r2)) + ':' + addr(Math.max(c1, c2), Math.max(r1, r2)); };
const rect = s => { const [a, b] = (s.ui.range || s.ui.sel + ':' + s.ui.sel).split(':').map(rc); return {c0: a[0], r0: a[1], c1: b[0], r1: b[1]}; };
const picked = s => { const q = rect(s), out = []; for (let r = q.r0; r <= q.r1; r++) for (let c = q.c0; c <= q.c1; c++) out.push(addr(c, r)); return out; };
const raw = (s, a) => { const c = s.cells[a]; return c && c.v != null ? String(c.v) : ''; };
const wholeRows = s => { const q = rect(s); return !!s.ui.range && q.c0 === 0 && q.c1 === s.ncols - 1; };
const wholeCols = s => { const q = rect(s); return !!s.ui.range && q.r0 === 0 && q.r1 === s.nrows - 1; };
const rowSpan = (s, r0, r1) => addr(0, Math.min(r0, r1)) + ':' + addr(s.ncols - 1, Math.max(r0, r1));
const colSpan = (s, c0, c1) => addr(Math.min(c0, c1), 0) + ':' + addr(Math.max(c0, c1), s.nrows - 1);
// Is a property the same on the whole selection? (Judged on its non-empty cells, or on all of them if it has none.)
const uniform = (s, k, v) => { const all = picked(s).map(a => s.cells[a] || NONE), full = all.filter(c => c.v != null && c.v !== ''); return (full.length ? full : all).every(c => c[k] === v); };
const setProp = (s, a, k, v) => { const c = s.cells[a] || {}; if (v == null || v === false || v === '') delete c[k]; else c[k] = v; if (Object.keys(c).length) s.cells[a] = c; else delete s.cells[a]; };

// ------------------------------------------------------------------ numbers as text
const NUM = /^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i;
const group = t => t.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
const plain = n => {                                                       // no trailing zeros, no floating-point dust; decimals are dropped until it fits a cell
  const whole = String(Math.trunc(Math.abs(n))).length;
  let t = String(n);
  for (let p = Math.max(10, whole); p >= whole; p--) { t = String(+n.toPrecision(p)); if (t.length <= 10) break; }
  return t;
};
const fixed = n => { const [i, d] = Math.abs(n).toFixed(2).split('.'); return group(i) + '.' + d; };
const nice = n => { const [i, d] = String(Math.abs(+n.toFixed(2))).split('.'); return (n < 0 && +n.toFixed(2) !== 0 ? '-' : '') + group(i) + (d ? '.' + d : ''); };
const shown = (v, fmt) => {
  if (typeof v !== 'number') return v == null ? '' : String(v);
  const f = fixed(v), neg = v < 0 && f !== '0.00' ? '-' : '';
  return fmt === 'number' ? neg + f : fmt === 'currency' ? neg + '$' + f : fmt === 'percent' ? plain(v * 100) + '%' : plain(v);
};
// What a typed text means: a number written with $ , or % is the plain number, and may set the format.
function typed(text) {
  const m = /^([+-]?)(\$?)((?:\d{1,3}(?:,\d{3})+|\d*)(?:\.\d*)?)(%?)$/.exec(text);
  if (!m || !/\d/.test(m[3]) || (m[2] && m[4])) return null;
  let n = Number(m[3].replace(/,/g, ''));
  if (m[1] === '-') n = -n;
  if (m[4]) n = +(n / 100).toPrecision(12);
  return {n, fmt: m[2] ? 'currency' : m[4] ? 'percent' : null};
}

// ------------------------------------------------------------------ formulas (a small recursive-descent parser; nothing is eval'ed)
//   expr := term (('+' | '-') term)*     term := unary (('*' | '/') unary)*     unary := ('-' | '+') unary | primary
//   primary := number | cell | NAME '(' arg (',' arg)* ')' | '(' expr ')'       arg := cell ':' cell | cell | expr
const FUNCS = {
  SUM: x => x.reduce((a, b) => a + b, 0),
  AVERAGE: x => { if (!x.length) throw ERR; return x.reduce((a, b) => a + b, 0) / x.length; },
  MIN: x => x.length ? Math.min(...x) : 0,
  MAX: x => x.length ? Math.max(...x) : 0,
  COUNT: x => x.length,
};
function lex(src) {
  const out = [], re = /\s*(?:(\d+\.?\d*|\.\d+)|([A-Za-z]+)(\d*)|([-+*\/(),:]))/y;
  let i = 0;
  while (i < src.length) {
    re.lastIndex = i;
    const m = re.exec(src);
    if (!m) { if (/^\s*$/.test(src.slice(i))) break; throw ERR; }
    i = re.lastIndex;
    if (m[1] !== undefined) out.push({k: 'num', v: Number(m[1])});
    else if (m[2] !== undefined) out.push(m[3] ? {k: 'ref', c: m[2].toUpperCase(), r: +m[3]} : {k: 'name', v: m[2].toUpperCase()});
    else out.push({k: m[4]});
  }
  return out;
}
function evaluate(src, s, get) {
  const t = lex(src);
  let p = 0;
  const is = k => p < t.length && t[p].k === k;
  const need = k => { if (!is(k)) throw ERR; return t[p++]; };
  const num = v => { if (v === undefined) return 0; if (typeof v !== 'number') throw ERR; return v; };   // an empty cell counts as 0, text is an error
  const at = x => { const c = COLS.indexOf(x.c); if (x.c.length !== 1 || c < 0 || c >= s.ncols || x.r < 1 || x.r > s.nrows) throw ERR; return [c, x.r - 1]; };
  const range = xs => {                                                    // B2:B9 or one cell: its numbers (text and empty cells are skipped)
    const [c1, r1] = at(t[p++]);
    let c2 = c1, r2 = r1;
    if (is(':')) { p++; [c2, r2] = at(need('ref')); }
    for (let r = Math.min(r1, r2); r <= Math.max(r1, r2); r++) for (let c = Math.min(c1, c2); c <= Math.max(c1, c2); c++) { const v = get(addr(c, r)); if (typeof v === 'number') xs.push(v); }
  };
  const call = name => {
    const f = FUNCS[name], xs = [];
    if (!f) throw ERR;
    need('(');
    if (!is(')')) for (;;) {
      const next = t[p + 1] && t[p + 1].k;
      if (is('ref') && (next === ':' || next === ',' || next === ')')) range(xs); else xs.push(num(expr()));
      if (is(',')) p++; else break;
    }
    need(')');
    return f(xs);
  };
  const primary = () => {
    if (is('num')) return t[p++].v;
    if (is('ref')) { const [c, r] = at(t[p++]); return get(addr(c, r)); }
    if (is('name')) return call(t[p++].v);
    if (is('(')) { p++; const v = expr(); need(')'); return v; }
    throw ERR;
  };
  const unary = () => is('-') ? (p++, -num(unary())) : is('+') ? (p++, num(unary())) : primary();
  const term = () => { let v = unary(); while (is('*') || is('/')) { const op = t[p++].k, w = num(unary()); if (op === '/' && w === 0) throw ERR; v = op === '*' ? num(v) * w : num(v) / w; } return v; };
  function expr() { let v = term(); while (is('+') || is('-')) { const op = t[p++].k, w = num(term()); v = op === '+' ? num(v) + w : num(v) - w; } return v; }
  const v = expr();
  if (p < t.length) throw ERR;
  return v === undefined ? 0 : v;
}
function recalc(s) {
  const vals = {}, busy = {};
  const get = a => {
    if (a in vals) { if (vals[a] === ERR) throw ERR; return vals[a]; }
    const v = raw(s, a);
    if (v === '') return undefined;
    if (v[0] !== '=') return (vals[a] = NUM.test(v) ? Number(v) : v);
    if (busy[a]) throw ERR;                                                // a formula that depends on itself
    busy[a] = true;
    let out;
    try { out = evaluate(v.slice(1), s, get); if (typeof out === 'number' && !isFinite(out)) out = ERR; } catch (_) { out = ERR; }
    busy[a] = false; vals[a] = out;
    if (out === ERR) throw ERR;
    return out;
  };
  Object.keys(s.cells).forEach(a => { try { get(a); } catch (_) {} });
  s.vals = vals;
}

// ------------------------------------------------------------------ changes
function setRaw(s, a, text) {
  const c = s.cells[a] || {}, t = text.trim(), p = t[0] === '=' ? null : typed(t);
  if (!t) delete c.v; else if (p) { c.v = String(p.n); if (p.fmt && !c.fmt) c.fmt = p.fmt; } else c.v = t;
  if (Object.keys(c).length) s.cells[a] = c; else delete s.cells[a];
}
function commit(s) {
  const u = s.ui, e = u.edit;
  if (!e) return;
  u.edit = null;
  if (e.text.trim() !== raw(s, u.sel)) { setRaw(s, u.sel, e.text); recalc(s); }
}
const begin = (s, text) => { const u = s.ui; u.range = null; u.edit = {text, bar: false}; TE.focus('sh-edit'); };
function move(s, dc, dr, extend) {
  const u = s.ui, [c, r] = rc(u.sel);
  if (extend) {
    const q = rect(s), fc = clamp((c === q.c0 ? q.c1 : q.c0) + dc, 0, s.ncols - 1), fr = clamp((r === q.r0 ? q.r1 : q.r0) + dr, 0, s.nrows - 1);
    u.range = fc === c && fr === r ? null : span(u.sel, addr(fc, fr));
  } else { u.sel = addr(clamp(c + dc, 0, s.ncols - 1), clamp(r + dr, 0, s.nrows - 1)); u.range = null; }
}
function clear(s) { picked(s).forEach(a => setProp(s, a, 'v', null)); recalc(s); }
function grab(s) {
  const q = rect(s), cells = [];
  for (let r = q.r0; r <= q.r1; r++) { const row = []; for (let c = q.c0; c <= q.c1; c++) { const x = s.cells[addr(c, r)]; row.push(x ? {...x} : null); } cells.push(row); }
  return {w: q.c1 - q.c0 + 1, h: q.r1 - q.r0 + 1, cells};
}
const REF = /(?<![A-Za-z0-9])([A-Za-z])(\d+)(?::([A-Za-z])(\d+))?(?![A-Za-z0-9(])/g;
function reref(f, k, d) {                                                  // row k (counted from 1) was inserted (d = 1) or deleted (d = -1)
  return f.replace(REF, (m, c1, n1, c2, n2) => {
    n1 = +n1;
    if (c2 === undefined) return d > 0 ? c1 + (n1 >= k ? n1 + 1 : n1) : n1 === k ? '#REF!' : c1 + (n1 > k ? n1 - 1 : n1);
    let lo = Math.min(n1, +n2), hi = Math.max(n1, +n2);
    if (d > 0) { if (lo >= k) { lo++; hi++; } else if (hi >= k) hi++; }
    else if (lo > k) { lo--; hi--; }
    else if (hi >= k) { hi--; if (hi < lo) return '#REF!'; }
    return c1 + lo + ':' + c2 + hi;
  });
}
function shiftRows(s, at, d) {                                             // d = 1: a new empty row at index `at`; d = -1: row `at` goes away
  const out = {};
  Object.keys(s.cells).forEach(a => {
    const [c, r] = rc(a), cell = s.cells[a];
    if (d < 0 && r === at) return;
    const nr = r >= at ? r + d : r;
    if (nr >= s.nrows) return;
    if (typeof cell.v === 'string' && cell.v[0] === '=') cell.v = reref(cell.v, at + 1, d);
    out[addr(c, nr)] = cell;
  });
  s.cells = out;
}
function sortRows(s, dir) {
  const [c, r] = rc(s.ui.sel);
  const any = (row, test) => { for (let i = 0; i < s.ncols; i++) if (test(raw(s, addr(i, row)))) return true; return false; };
  const full = row => any(row, v => v !== ''), formula = row => any(row, v => v[0] === '=');
  let at = r;
  if (wholeCols(s)) { at = 0; while (at < s.nrows && raw(s, addr(c, at)) === '') at++; }
  if (at >= s.nrows || !full(at)) return;
  let r0 = at, r1 = at;
  while (r0 > 0 && full(r0 - 1)) r0--;
  while (r1 < s.nrows - 1 && full(r1 + 1)) r1++;
  while (r1 > r0 && formula(r1)) r1--;
  if (r1 - r0 < 2) return;                                                 // a header and at most one row: nothing to reorder
  const rank = v => typeof v === 'number' ? 0 : v === undefined || v === '' ? 2 : 1, rows = [];
  for (let i = r0 + 1; i <= r1; i++) {
    const row = [];
    for (let j = 0; j < s.ncols; j++) { const a = addr(j, i); row.push(s.cells[a]); delete s.cells[a]; }
    rows.push({row, v: s.vals[addr(c, i)]});
  }
  rows.sort((x, y) => {
    const a = rank(x.v), b = rank(y.v);
    if (a !== b || a === 2) return a - b;
    const p = a ? String(x.v).toLowerCase() : x.v, q = a ? String(y.v).toLowerCase() : y.v;
    return (p < q ? -1 : p > q ? 1 : 0) * dir;
  });
  rows.forEach((x, n) => x.row.forEach((cell, j) => { if (cell) s.cells[addr(j, r0 + 1 + n)] = cell; }));
  recalc(s);
}

TE.register('sheet', {
  title: 'Sheets', size: [1010, 624],
  dock: {bg: 'linear-gradient(#62d680, #1ea548)', glyph: '<svg width="38" height="38" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="2.4" fill="#fff"/><path d="M3.5 6.9a2.4 2.4 0 0 1 2.4-2.4h12.2a2.4 2.4 0 0 1 2.4 2.4v2.4h-17z" fill="#bfeecd"/><path d="M3.5 9.3h17M3.5 14.4h17M9.2 4.5v15M14.8 4.5v15" stroke="#27ad53" stroke-width="1.15" fill="none"/></svg>'},
  before(s, act) { if (!KEEP[act]) commit(s); },
  render(s) {
    const u = s.ui, q = rect(s), [ac, ar] = rc(u.sel), cur = s.cells[u.sel] || NONE, ed = u.edit;
    const rowsAll = wholeRows(s), colsAll = wholeCols(s);
    const btn = (act, arg, on, inner, cls = '') => `<span class="tb-btn${cls}${on ? ' on' : ''}" data-act="${act}" data-arg="${arg}">${inner}</span>`;
    const fname = (FORMATS.find(f => f[1] === cur.fmt) || FORMATS[0])[0];
    const bar = `<div class="toolbar sh-bar" data-windrag>${DOC}<span class="tb-title">${esc(s.title)}</span><span class="spacer"></span>` +
      `<span class="tb-group">${btn('bold', '', uniform(s, 'bold', true), '<b class="sh-b">B</b>')}${btn('italic', '', uniform(s, 'italic', true), icon('sh-italic', 17))}</span><i class="sh-sep"></i>` +
      `<span class="tb-group">${['left', 'center', 'right'].map(a => btn('align', a, uniform(s, 'align', a), icon('sh-' + a, 17))).join('')}</span><i class="sh-sep"></i>` +
      TE.w.select(fname, FORMATS.map(f => f[0]), 'format') + `<i class="sh-sep"></i>` +
      `<span class="tb-group">${btn('sort', 'asc', false, `<span class="sh-az"><b>A</b><b>Z</b></span>${icon('sh-arrow', 14)}`, ' sh-sort')}${btn('sort', 'desc', false, `<span class="sh-az"><b>Z</b><b>A</b></span>${icon('sh-arrow', 14)}`, ' sh-sort')}</span><i class="sh-sep"></i>` +
      btn('insert_row', 'below', false, icon('sh-rowadd', 19)) + `</div>`;
    const fx = `<div class="sh-fx"><span class="sh-name">${u.sel}</span>` +
      `<span class="sh-fxbtn${ed ? '' : ' off'}"${ed ? ' data-act="edit_cancel"' : ''}>${icon('x', 13)}</span><span class="sh-fxbtn${ed ? '' : ' off'}"${ed ? ' data-act="edit_accept"' : ''}>${icon('check', 14)}</span>` +
      `<span class="sh-fxmark">fx</span><input class="sh-fxin" type="text" spellcheck="false" autocomplete="off" value="${esc(ed ? ed.text : raw(s, u.sel))}" data-act="fx_focus" data-input="fx_input" data-focus="sh-fx" data-enter="edit_commit" data-esc="edit_cancel"${TAB}></div>`;
    let head = `<div class="sh-head"><div class="sh-corner" data-act="select_all"></div>`;
    for (let c = 0; c < s.ncols; c++) head += `<div class="sh-ch${c >= q.c0 && c <= q.c1 ? ' hl' : ''}${colsAll && c >= q.c0 && c <= q.c1 ? ' all' : ''}" data-act="select_col" data-arg="${COLS[c]}" data-ctx="col:${COLS[c]}">${COLS[c]}</div>`;
    head += `<div class="sh-gutter"></div></div>`;
    let grid = '';
    for (let r = 0; r < s.nrows; r++) {
      const rin = r >= q.r0 && r <= q.r1;
      grid += `<div class="sh-row"><div class="sh-rh${rin ? ' hl' : ''}${rin && rowsAll ? ' all' : ''}" data-act="select_row" data-arg="${r + 1}" data-ctx="row:${r + 1}">${r + 1}</div>`;
      for (let c = 0; c < s.ncols; c++) {
        const a = addr(c, r), cell = s.cells[a] || NONE, v = s.vals[a], here = c === ac && r === ar;
        let cls = 'sh-cell';
        if (rin && c >= q.c0 && c <= q.c1) cls += ' in' + (here ? ' anchor' : '') + (r === q.r0 ? ' et' : '') + (r === q.r1 ? ' eb' : '') + (c === q.c0 ? ' el' : '') + (c === q.c1 ? ' er' : '');
        if (cell.bold) cls += ' b';
        if (cell.italic) cls += ' i';
        if (here && ed && !ed.bar) {
          grid += `<div class="${cls} editing"><input class="sh-edit" type="text" spellcheck="false" autocomplete="off" size="${ed.text.length + 1}" style="max-width:${(s.ncols - c) * 96 - 1}px" value="${esc(ed.text)}" data-input="editing" data-focus="sh-edit" data-enter="edit_commit" data-esc="edit_cancel"${TAB}></div>`;
          continue;
        }
        const text = here && ed ? ed.text : shown(v, cell.fmt);
        const al = here && ed ? 'left' : cell.align || (typeof v === 'number' ? 'right' : v === ERR ? 'center' : 'left');
        if (al !== 'left') cls += al === 'right' ? ' ar' : ' ac';
        grid += `<div class="${cls}" data-act="select" data-arg="${a}" data-dbl="edit" data-ctx="cell:${a}" data-drag="${a}" data-drop="${a}"${here ? ' tabindex="-1" data-focus="sh-sel"' : ''}>${text === '' ? '' : `<span class="sh-t">${esc(text)}</span>`}</div>`;
      }
      grid += '</div>';
    }
    const nums = picked(s).map(a => s.vals[a]).filter(v => typeof v === 'number'), sum = nums.reduce((a, b) => a + b, 0);
    const stat = nums.length > 1 ? `<span class="sh-stat">Sum <b>${nice(sum)}</b></span><span class="sh-stat">Average <b>${nice(sum / nums.length)}</b></span><span class="sh-stat">Count <b>${nums.length}</b></span>` : '';
    const foot = `<div class="sh-foot"><span class="sh-tabadd">${icon('plus', 13)}</span><span class="sh-tab">Sheet 1</span><span class="spacer"></span>${stat}</div>`;
    return `<div class="sheet">${bar}${fx}${head}<div class="sh-body scroll" data-scroll="sheet-grid">${grid}</div>${foot}</div>`;
  },
  on: {
    select(s, a, ev) { const u = s.ui; if (!rc(a)) return; if (ev && ev.shiftKey) u.range = a === u.sel ? null : span(u.sel, a); else { u.sel = a; u.range = null; } },
    select_row(s, n, ev) {
      const u = s.ui, r = +n - 1;
      if (ev && ev.shiftKey) { const r0 = rc(u.sel)[1]; u.sel = addr(0, r0); u.range = rowSpan(s, r0, r); } else { u.sel = addr(0, r); u.range = rowSpan(s, r, r); }
    },
    select_col(s, name, ev) {
      const u = s.ui, c = COLS.indexOf(name);
      if (ev && ev.shiftKey) { const c0 = rc(u.sel)[0]; u.sel = addr(c0, 0); u.range = colSpan(s, c0, c); } else { u.sel = addr(c, 0); u.range = colSpan(s, c, c); }
    },
    select_all(s) { s.ui.sel = 'A1'; s.ui.range = 'A1:' + addr(s.ncols - 1, s.nrows - 1); },
    edit(s, a) { if (!rc(a)) return; s.ui.sel = a; begin(s, raw(s, a)); },
    editing(s, _, text) { if (s.ui.edit) s.ui.edit.text = text; return true; },
    fx_focus(s) { const u = s.ui; if (u.edit) u.edit.bar = true; else { u.range = null; u.edit = {text: raw(s, u.sel), bar: true}; } },
    fx_input(s, _, text) { const u = s.ui; if (u.edit) { u.edit.text = text; u.edit.bar = true; } else { u.range = null; u.edit = {text, bar: true}; } return true; },
    edit_commit(s, _, text) { if (s.ui.edit && typeof text === 'string') s.ui.edit.text = text; commit(s); move(s, 0, 1); TE.focus('sh-sel'); },
    edit_tab(s, dir, text) { if (s.ui.edit && typeof text === 'string') s.ui.edit.text = text; commit(s); move(s, dir === 'left' ? -1 : 1, 0); TE.focus('sh-sel'); },
    edit_accept(s) { commit(s); },
    edit_cancel(s) { s.ui.edit = null; TE.focus('sh-sel'); },
    bold(s) { const on = uniform(s, 'bold', true); picked(s).forEach(a => setProp(s, a, 'bold', !on)); recalc(s); },
    italic(s) { const on = uniform(s, 'italic', true); picked(s).forEach(a => setProp(s, a, 'italic', !on)); recalc(s); },
    align(s, how) { if (!['left', 'center', 'right'].includes(how)) return; const on = uniform(s, 'align', how); picked(s).forEach(a => setProp(s, a, 'align', on ? null : how)); recalc(s); },
    format(s, _, name) { const f = FORMATS.find(f => f[0] === name); if (!f) return; picked(s).forEach(a => setProp(s, a, 'fmt', f[1])); recalc(s); },
    clear(s) { clear(s); },
    copy(s) { s.ui.clip = grab(s); },
    cut(s) { s.ui.clip = grab(s); picked(s).forEach(a => { delete s.cells[a]; }); recalc(s); },
    paste(s) {
      const u = s.ui, k = u.clip, q = rect(s);
      if (!k) return;
      const put = (c, r, src) => { if (c >= s.ncols || r >= s.nrows) return; if (src) s.cells[addr(c, r)] = {...src}; else delete s.cells[addr(c, r)]; };
      if (k.w === 1 && k.h === 1) picked(s).forEach(a => put(...rc(a), k.cells[0][0]));
      else {
        k.cells.forEach((row, dy) => row.forEach((src, dx) => put(q.c0 + dx, q.r0 + dy, src)));
        u.sel = addr(q.c0, q.r0); u.range = span(u.sel, addr(Math.min(q.c0 + k.w, s.ncols) - 1, Math.min(q.r0 + k.h, s.nrows) - 1));
      }
      recalc(s);
    },
    insert_row(s, where) {
      const u = s.ui, q = rect(s), whole = wholeRows(s), at = where === 'above' ? q.r0 : q.r1 + 1;
      if (at >= s.nrows) return;
      shiftRows(s, at, 1);
      u.sel = addr(whole ? 0 : rc(u.sel)[0], at); u.range = whole ? rowSpan(s, at, at) : null;
      recalc(s);
    },
    delete_row(s) {
      const u = s.ui, q = rect(s), whole = wholeRows(s);
      for (let r = q.r1; r >= q.r0; r--) shiftRows(s, r, -1);
      u.sel = addr(whole ? 0 : rc(u.sel)[0], q.r0); u.range = whole ? rowSpan(s, q.r0, q.r0) : null;
      recalc(s);
    },
    sort(s, dir) { sortRows(s, dir === 'desc' ? -1 : 1); },
  },
  drop(s, from, to, info) {                                                // a drag from one cell to another selects the range
    if (info.from !== 'sheet' || !rc(from) || !rc(to)) return;
    commit(s);
    s.ui.sel = from; s.ui.range = from === to ? null : span(from, to);
  },
  context(s, arg) {
    commit(s);
    const u = s.ui, q = rect(s), [kind, x] = String(arg).split(':');
    if (kind === 'row') {
      const r = +x - 1;
      if (!(wholeRows(s) && r >= q.r0 && r <= q.r1)) { u.sel = addr(0, r); u.range = rowSpan(s, r, r); }
      return [{label: 'Insert Row Above', act: 'insert_row', arg: 'above'}, {label: 'Insert Row Below', act: 'insert_row', arg: 'below'}, '-', {label: 'Delete Row', act: 'delete_row', arg: ''}];
    }
    if (kind === 'col') {
      const c = COLS.indexOf(x);
      if (!(wholeCols(s) && c >= q.c0 && c <= q.c1)) { u.sel = addr(c, 0); u.range = colSpan(s, c, c); }
      return [{label: 'Sort Ascending', act: 'sort', arg: 'asc'}, {label: 'Sort Descending', act: 'sort', arg: 'desc'}];
    }
    const p = rc(x);
    if (!p) return [];
    if (!(p[0] >= q.c0 && p[0] <= q.c1 && p[1] >= q.r0 && p[1] <= q.r1)) { u.sel = x; u.range = null; }
    return [{label: 'Cut', act: 'cut', arg: ''}, {label: 'Copy', act: 'copy', arg: ''}, {label: 'Paste', act: 'paste', arg: '', disabled: !u.clip}, '-', {label: 'Clear Contents', act: 'clear', arg: ''}];
  },
  menus(s) {
    const u = s.ui, cur = s.cells[u.sel] || NONE, fname = (FORMATS.find(f => f[1] === cur.fmt) || FORMATS[0])[0];
    return [
      {label: 'File', items: [{label: 'New', shortcut: '⌘N', disabled: true}, {label: 'Open…', shortcut: '⌘O', disabled: true}, '-', {label: 'Save', shortcut: '⌘S', disabled: true}, {label: 'Duplicate', shortcut: '⇧⌘S', disabled: true}, {label: 'Export To', disabled: true}, '-', {label: 'Print…', shortcut: '⌘P', disabled: true}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', act: 'cut'}, {label: 'Copy', shortcut: '⌘C', act: 'copy'}, {label: 'Paste', shortcut: '⌘V', act: 'paste', disabled: !u.clip}, {label: 'Clear', act: 'clear'}, '-', {label: 'Select All', shortcut: '⌘A', act: 'select_all'}]},
      {label: 'Format', items: [{label: 'Bold', shortcut: '⌘B', act: 'bold', checked: uniform(s, 'bold', true)}, {label: 'Italic', shortcut: '⌘I', act: 'italic', checked: uniform(s, 'italic', true)}, '-',
        {label: 'Align', items: [['Left', 'left'], ['Centre', 'center'], ['Right', 'right']].map(([label, a]) => ({label, act: 'align', arg: a, checked: uniform(s, 'align', a)}))},
        {label: 'Number Format', items: FORMATS.map(f => ({label: f[0], act: 'format', checked: f[0] === fname}))}]},
      {label: 'Table', items: [{label: 'Insert Row Above', act: 'insert_row', arg: 'above'}, {label: 'Insert Row Below', act: 'insert_row', arg: 'below'}, {label: 'Delete Row', act: 'delete_row'}, '-', {label: 'Sort Ascending', act: 'sort', arg: 'asc'}, {label: 'Sort Descending', act: 'sort', arg: 'desc'}]},
    ];
  },
  keys: {'Meta+b': 'bold', 'Meta+i': 'italic', 'Meta+c': 'copy', 'Meta+x': 'cut', 'Meta+v': 'paste', 'Meta+a': 'select_all'},
  key(s, e) {                                                              // every key without Cmd while no text field has the focus
    const u = s.ui, k = e.key;
    const arrows = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1], PageUp: [0, -18], PageDown: [0, 18]};
    if (e.ctrlKey || e.altKey) return false;
    if (u.edit) {                                                          // an edit whose field lost the focus (a menu was opened, say)
      const back = u.edit.bar ? 'sh-fx' : 'sh-edit';
      if (k.length === 1) { u.edit.text += k; TE.focus(back); return true; }
      if (k === 'Backspace') { u.edit.text = u.edit.text.slice(0, -1); TE.focus(back); return true; }
      if (k === 'Escape') { u.edit = null; TE.focus('sh-sel'); return true; }
      if (k !== 'Enter' && k !== 'Tab' && !arrows[k]) return false;
      commit(s);
    }
    if (k.length === 1) { begin(s, k); return true; }                      // typing replaces the content of the cell
    if (k === 'Backspace' || k === 'Delete') clear(s);
    else if (k === 'Enter') move(s, 0, e.shiftKey ? -1 : 1);
    else if (k === 'Tab') move(s, e.shiftKey ? -1 : 1, 0);
    else if (arrows[k]) move(s, arrows[k][0], arrows[k][1], e.shiftKey);
    else if (k === 'Escape') u.range = null;
    else if (k === 'F2') { begin(s, raw(s, u.sel)); return true; }
    else return false;
    TE.focus('sh-sel');                                                    // keeps the active cell in view while moving with the keyboard
    return true;
  },
});
})();
