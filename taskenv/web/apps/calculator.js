// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Calculator: a basic keypad and a scientific one (View menu). State:
//   {display, acc, op, fresh, mode, tape: [{id, expr, result}], next, ui: {toks, expr, label, wait}}
// display is the number on screen as a plain string ("1637.5"; it is drawn with thousands separators).
// While a calculation is pending, acc is its value so far and op its last operator (+ − × ÷ ^); fresh
// means that the next digit starts a new number. Every calculation finished with = is added to tape.
// ui holds the pending calculation in full: toks = [number, operator, number, ...], expr = its text,
// label = the text of the number on screen when a key made it ("15%", "sqrt(16)"), wait = the last key
// was an operator. Results have at most 9 significant digits. Angles are in degrees.
(() => {
const BASIC_W = 248, SCI_W = 422, HGT = 418;
const PREC = {'+': 1, '−': 1, '×': 2, '÷': 2, '^': 3};
TE.addIcons({
  calc_root: 'M2 13.5l2.6-1 3.4 7.5L12.2 4.5H22M14.8 10.5l5 7.5M19.8 10.5l-5 7.5',
  calc_pi: 'M4 10c.8-2.2 1.9-3 3.6-3H20M9.3 7v8.2c0 1.8-.5 3-1.6 3.8M15.2 7v9c0 1.9.8 2.9 2.6 2.9',
});

// ------------------------------------------------------------------ numbers
const apply = (o, a, b) => o === '+' ? a + b : o === '−' ? a - b : o === '×' ? a * b : o === '÷' ? a / b : Math.pow(a, b);
const calc = t => {                                    // value of [number, operator, number, ...], × and ÷ before + and −
  const nums = [t[0]], ops = [];
  const reduce = () => { const b = nums.pop(), a = nums.pop(); nums.push(apply(ops.pop(), a, b)); };
  for (let i = 1; i + 1 < t.length; i += 2) {
    while (ops.length && (PREC[ops[ops.length - 1]] > PREC[t[i]] || (PREC[ops[ops.length - 1]] === PREC[t[i]] && t[i] !== '^'))) reduce();
    ops.push(t[i]); nums.push(t[i + 1]);
  }
  while (ops.length) reduce();
  return nums[0];
};
const fmt = x => {
  if (typeof x !== 'number' || !isFinite(x)) return 'Not a number';
  const r = Number(x.toPrecision(9)), a = Math.abs(r);
  if (r === 0) return '0';
  return a >= 1e9 || a < 1e-6 ? r.toExponential().replace('+', '') : String(r);
};
const val = s => { const v = Number(s.display); return isFinite(v) ? v : 0; };
const text = (s, v) => s.ui.label || (v < 0 ? `(${fmt(v)})` : fmt(v));
const lastTerm = t => { let i = t.length - 1; while (i > 0 && PREC[t[i - 1]] !== 1) i -= 2; return calc(t.slice(i)); };
const fact = v => { if (v < 0 || v > 170 || v !== Math.floor(v)) return NaN; let r = 1; for (let i = 2; i <= v; i++) r *= i; return r; };
const deg = f => v => Math.round(f(v * Math.PI / 180) * 1e12) / 1e12;
const FN = {
  sqr: [v => v * v, a => `${a}^2`], cube: [v => v * v * v, a => `${a}^3`], sqrt: [Math.sqrt, a => `sqrt(${a})`], inv: [v => 1 / v, a => `1/${a}`],
  exp: [Math.exp, a => `e^${a}`], pow10: [v => Math.pow(10, v), a => `10^${a}`], ln: [Math.log, a => `ln(${a})`], log: [Math.log10, a => `log(${a})`],
  sin: [deg(Math.sin), a => `sin(${a})`], cos: [deg(Math.cos), a => `cos(${a})`], tan: [deg(Math.tan), a => `tan(${a})`], fact: [fact, a => `${a}!`],
};

// ------------------------------------------------------------------ keys
const digit = (s, d) => {
  const u = s.ui;
  if (s.fresh) { s.display = d === '.' ? '0.' : d; s.fresh = false; }
  else if (d === '.') { if (!s.display.includes('.')) s.display += '.'; }
  else if (s.display === '0' || s.display === '-0') s.display = s.display.replace('0', d);
  else if (s.display.replace(/[-.]/g, '').length < 12) s.display += d;
  u.wait = false; u.label = '';
};
const operator = (s, o) => {
  const u = s.ui;
  if (u.wait && u.toks.length) { u.toks[u.toks.length - 1] = o; u.expr = u.expr.slice(0, -1) + o; }
  else { const v = val(s); u.expr += text(s, v) + o; u.toks.push(v, o); }
  const done = u.toks.slice(0, -1);
  s.acc = calc(done); s.op = o; s.fresh = true; u.wait = true; u.label = '';
  s.display = fmt(PREC[o] === 1 ? s.acc : lastTerm(done));
};
const equals = s => {
  const u = s.ui;
  if (u.toks.length) {
    const v = val(s), expr = u.expr + text(s, v), result = fmt(calc(u.toks.concat([v])));
    s.tape.push({id: 'n' + s.next++, expr, result});
    s.display = result;
  } else if (u.label) s.tape.push({id: 'n' + s.next++, expr: u.label, result: s.display});
  s.acc = null; s.op = null; s.fresh = true; u.toks = []; u.expr = ''; u.label = ''; u.wait = false;
};
const percent = s => {
  const u = s.ui, v = val(s), label = text(s, v) + '%';
  s.display = fmt(PREC[s.op] === 1 ? s.acc * v / 100 : v / 100); u.label = label; s.fresh = true; u.wait = false;
};
const unary = (s, k) => { const u = s.ui, v = val(s), label = FN[k][1](text(s, v)); s.display = fmt(FN[k][0](v)); u.label = label; s.fresh = true; u.wait = false; };
const constant = (s, k) => { s.display = fmt(k === 'pi' ? Math.PI : Math.E); s.ui.label = k; s.fresh = true; s.ui.wait = false; };
const negate = s => {
  const u = s.ui;
  if (s.fresh && (u.wait || val(s) === 0)) { s.display = '-0'; s.fresh = false; u.label = ''; }
  else if (s.fresh) { const v = val(s); s.display = fmt(-v); u.label = u.label ? `-(${u.label})` : ''; }
  else s.display = s.display[0] === '-' ? s.display.slice(1) : '-' + s.display;
  u.wait = false;
};
const clear = s => {
  const u = s.ui;
  if (s.display !== '0' && u.toks.length) { s.display = '0'; s.fresh = true; u.label = ''; return; }     // C: only the number on screen
  s.display = '0'; s.acc = null; s.op = null; s.fresh = true; u.toks = []; u.expr = ''; u.label = ''; u.wait = false;
};
const backspace = s => { if (s.fresh) return; s.display = s.display.slice(0, -1); if (!/\d/.test(s.display)) s.display = '0'; };
const press = (s, k) => {
  if (/^[0-9.]$/.test(k)) digit(s, k);
  else if (PREC[k]) operator(s, k);
  else if (k === '=') equals(s);
  else if (k === 'clear') clear(s);
  else if (k === 'neg') negate(s);
  else if (k === 'pct') percent(s);
  else if (k === 'pi' || k === 'e') constant(s, k);
  else if (FN[k]) unary(s, k);
  else return false;
  return true;
};

// ------------------------------------------------------------------ window
const group = d => { const m = /^(-?)(\d+)(\.\d*)?$/.exec(d); return (m ? m[1] + m[2].replace(/\B(?=(\d{3})+$)/g, ',') + (m[3] || '') : d).replace('-', '−'); };
const ems = t => [...t].reduce((n, c) => n + (/\d/.test(c) ? .615 : /[,. ]/.test(c) ? .29 : .6), 0);    // rough width of the display text
const SCI = [
  [['sqr', 'x<sup>2</sup>'], ['cube', 'x<sup>3</sup>'], ['^', 'x<sup>y</sup>']],
  [['exp', 'e<sup>x</sup>'], ['pow10', '10<sup>x</sup>'], ['inv', '1/x']],
  [['sqrt', TE.icon('calc_root', 21)], ['ln', 'ln'], ['log', 'log<sub>10</sub>']],
  [['sin', 'sin'], ['cos', 'cos'], ['tan', 'tan']],
  [['pi', TE.icon('calc_pi', 19)], ['e', 'e'], ['fact', 'x!']],
];
const BASIC = [
  [['clear', '', 'fn'], ['neg', '+/−', 'fn'], ['pct', '%', 'fn'], ['÷', '÷', 'op']],
  [['7', '7', 'num'], ['8', '8', 'num'], ['9', '9', 'num'], ['×', '×', 'op']],
  [['4', '4', 'num'], ['5', '5', 'num'], ['6', '6', 'num'], ['−', '−', 'op']],
  [['1', '1', 'num'], ['2', '2', 'num'], ['3', '3', 'num'], ['+', '+', 'op']],
  [['0', '0', 'num wide'], ['.', '.', 'num'], ['=', '=', 'op']],
];

TE.register('calculator', {
  title: 'Calculator', chrome: 'compact',
  get size() { const s = TE.state && TE.state.apps.calculator; return [s && s.mode === 'scientific' ? SCI_W : BASIC_W, HGT]; },
  dock: {bg: 'linear-gradient(#606065, #2b2b2e)', glyph: '<svg width="34" height="34" viewBox="0 0 34 34"><rect x="6" y="3.5" width="22" height="7.5" rx="2.2" fill="#e4e4e9"/>' +
    [0, 1, 2].map(r => [0, 1, 2].map(c => `<circle cx="${9.4 + c * 7.6}" cy="${16.6 + r * 6.4}" r="2.5" fill="${c === 2 ? '#ff9f0a' : '#e4e4e9'}"/>`).join('')).join('') + '</svg>'},
  render(s) {
    const sci = s.mode === 'scientific', u = s.ui, shown = group(s.display);
    const lines = s.tape.slice(-2).map(t => `${t.expr} = ${t.result}`), pending = u.expr || (s.op ? fmt(s.acc) + s.op : '');
    if (pending) lines.push(pending);
    const size = Math.max(17, Math.min(46, Math.floor(((sci ? SCI_W : BASIC_W) - 38) / ems(shown))));
    const key = ([k, label, cls]) => `<span class="ck ${cls || 'sci'}${s.op === k && u.wait ? ' on' : ''}" data-act="press" data-arg="${k}">${k === 'clear' ? (s.display !== '0' ? 'C' : 'AC') : label}</span>`;
    return `<div class="calc${sci ? ' sci' : ''}"><div class="calc-top" data-windrag></div>` +
      `<div class="calc-display" data-windrag><div class="calc-tape">${lines.slice(-2).map(l => `<div>${TE.esc(l)}</div>`).join('')}</div><div class="calc-num" style="font-size:${size}px">${TE.esc(shown)}</div></div>` +
      `<div class="calc-keys">${BASIC.map((row, i) => (sci ? SCI[i] : []).concat(row).map(key).join('')).join('')}</div></div>`;
  },
  on: {
    press(s, k) { press(s, k); },
    // The window is as wide as its keypad: the window record changes and TE.open restacks at once.
    mode(s, m) {
      if (!['basic', 'scientific'].includes(m) || s.mode === m) return;
      s.mode = m;
      const win = TE.state.windows.find(x => x.app === 'calculator');
      if (win) { win.w = m === 'scientific' ? SCI_W : BASIC_W; win.x = Math.max(8, Math.min(win.x, 1440 - win.w - 8)); TE.open('calculator'); }
    },
  },
  key(s, e) {
    if (e.ctrlKey || e.altKey) return false;
    const k = e.key, map = {'+': '+', '-': '−', '*': '×', 'x': '×', 'X': '×', '/': '÷', '^': '^', 'Enter': '=', '=': '=', '%': 'pct', 'Escape': 'clear', 'c': 'clear', 'C': 'clear', ',': '.'};
    if (k === 'Backspace') { backspace(s); return true; }
    return /^[0-9.]$/.test(k) ? press(s, k) : map[k] ? press(s, map[k]) : false;
  },
  menus(s) {
    return [
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true}]},
      {label: 'View', items: [{label: 'Basic', shortcut: '⌘1', act: 'mode', arg: 'basic', checked: s.mode === 'basic'}, {label: 'Scientific', shortcut: '⌘2', act: 'mode', arg: 'scientific', checked: s.mode === 'scientific'}]},
    ];
  },
  keys: {'Meta+1': {act: 'mode', arg: 'basic'}, 'Meta+2': {act: 'mode', arg: 'scientific'}},
});
})();
