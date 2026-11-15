// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Calendar: day, week and month views of seeded events. State:
//   {today, calendars: [{id, name, color, shown}], events: [{id, title, cal, date, start, dur}], next,
//    ui: {view, anchor, sel, edit, draft, search}}
// Dates are ISO strings ("2026-11-12"), times are hours (14.5 is 2:30 PM), weeks start on Monday.
// The red "now" line is drawn at the time of the menu bar clock (state.status.clock).
(() => {
const {esc, icon, w} = TE;
const HH = 44, PAD = 9, POP_H = 152, VIEW0 = 7;
// The hour grid covers the whole day and starts scrolled to VIEW0 (CSS scroll-initial-target). In
// a browser without that property the grid begins at VIEW0 instead, so the first screen is the same.
const H0 = window.CSS && CSS.supports('scroll-initial-target', 'nearest') ? 0 : VIEW0;
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const WD = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const m3 = i => MONTHS[i].slice(0, 3), wd3 = i => WD[i].slice(0, 3);

// ------------------------------------------------------------------ dates and times
const parse = d => { const [y, m, dd] = d.split('-').map(Number); return new Date(Date.UTC(y, m - 1, dd)); };
const iso = t => t.toISOString().slice(0, 10);
const add = (d, n) => { const t = parse(d); t.setUTCDate(t.getUTCDate() + n); return iso(t); };
const addMonths = (d, n) => { const [y, m] = d.split('-').map(Number); return iso(new Date(Date.UTC(y, m - 1 + n, 1))); };
const dow = d => (parse(d).getUTCDay() + 6) % 7;                 // 0 = Monday
const weekOf = d => add(d, -dow(d));
const monthStart = d => d.slice(0, 8) + '01';
const ym = d => d.slice(0, 7), dayNo = d => +d.slice(8), monNo = d => +d.slice(5, 7) - 1;
const clock = h => { const m = Math.round(h * 60), hr = Math.floor(m / 60) % 24, mi = m % 60; return (hr % 12 || 12) + (mi ? ':' + String(mi).padStart(2, '0') : ''); };
const ap = h => Math.floor(Math.round(h * 60) / 60) % 24 < 12 ? 'AM' : 'PM';
const time = h => `${clock(h)} ${ap(h)}`;
const span = (a, b) => ap(a) === ap(b) ? `${clock(a)} – ${time(b)}` : `${time(a)} – ${time(b)}`;
const nowHour = () => { const m = /(\d{1,2}):(\d\d)\s*([AP])M/.exec((TE.state.status || {}).clock || ''); return m ? (+m[1] % 12) + (m[3] === 'P' ? 12 : 0) + m[2] / 60 : null; };
const rgb = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
const mix = (c, to, t) => { const b = rgb(to); return '#' + rgb(c).map((v, i) => Math.round(v + (b[i] - v) * t).toString(16).padStart(2, '0')).join(''); };

// ------------------------------------------------------------------ state
const cal = (s, id) => s.calendars.find(c => c.id === id) || {id: '', name: '', color: '#8e8e93', shown: true};
const ev = (s, id) => s.events.find(e => e.id === id);
const shown = s => { const on = new Set(s.calendars.filter(c => c.shown).map(c => c.id)); return s.events.filter(e => on.has(e.cal)); };
const byStart = (a, b) => a.start - b.start || (a.id < b.id ? -1 : 1);
const range = s => {                                              // [first day, number of days] on screen
  const u = s.ui;
  if (u.view === 'day') return [u.anchor, 1];
  if (u.view === 'month') { const a = monthStart(u.anchor); return [a, Math.round((parse(addMonths(a, 1)) - parse(a)) / 864e5)]; }
  return [weekOf(u.anchor), 7];
};
const dim = (s, e) => { const q = (s.ui.search || '').trim().toLowerCase(); return !!q && !e.title.toLowerCase().includes(q); };
const commit = s => { const u = s.ui; if (!u.edit) return; const e = ev(s, u.edit), t = (u.draft || '').trim(); if (e && t) e.title = t; u.edit = null; u.draft = ''; };
const startEdit = (s, id) => { const e = ev(s, id); if (!e) return; s.ui.edit = id; s.ui.draft = e.title; s.ui.sel = null; TE.focus('evtitle', true); };
const isFree = (s, date, start, dur) => !s.events.some(e => e.date === date && e.start < start + dur && start < e.start + e.dur);
const create = (s, date, hour) => {
  const c = s.calendars.find(c => c.shown); if (!c || !/^\d{4}-\d\d-\d\d$/.test(date)) return;
  let start = hour;
  if (start == null) { start = 9; for (const h of [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 8, 7]) if (isFree(s, date, h, 1)) { start = h; break; } }
  const id = 'n' + s.next++;
  s.events.push({id, title: 'New Event', cal: c.id, date, start, dur: 1});
  startEdit(s, id);
};
const step = (s, n) => { const u = s.ui; u.anchor = u.view === 'month' ? addMonths(u.anchor, n) : add(u.anchor, u.view === 'week' ? 7 * n : n); u.sel = null; };
// Events of one day that overlap share the width of the column.
const lanes = list => {
  const out = {}; let group = [], end = 0;
  const flush = () => {
    const cols = [];
    group.forEach(e => { let i = cols.findIndex(t => t <= e.start + 1e-9); if (i < 0) { i = cols.length; cols.push(0); } cols[i] = e.start + e.dur; out[e.id] = [i, 1]; });
    group.forEach(e => { out[e.id][1] = cols.length; }); group = [];
  };
  list.forEach(e => { if (group.length && e.start >= end - 1e-9) flush(); end = group.length ? Math.max(end, e.start + e.dur) : e.start + e.dur; group.push(e); });
  if (group.length) flush();
  return out;
};

// ------------------------------------------------------------------ pieces
const attrs = e => ` data-act="select" data-arg="${e.id}" data-dbl="rename" data-ctx="${e.id}" data-drag="${e.id}"`;
const field = s => `<input class="cv-edit" type="text" spellcheck="false" autocomplete="off" value="${esc(s.ui.draft)}" data-input="editing" data-focus="evtitle" data-enter="commit" data-esc="cancel">`;
const tint = c => `--c:${c};--c2:${mix(c, '#000000', .2)};--bg:${mix(c, '#ffffff', .78)};--ink:${mix(c, '#000000', .52)}`;
const block = (s, e, lane) => {
  const u = s.ui, editing = u.edit === e.id;
  return `<div class="cv-ev${u.sel === e.id ? ' sel' : ''}${e.dur < .75 ? ' short' : ''}${dim(s, e) ? ' dim' : ''}${editing ? ' editing' : ''}" ` +
    `style="--s:${e.start - H0};--d:${e.dur};--l:${lane[0] / lane[1]};--w:${1 / lane[1]};${tint(cal(s, e.cal).color)}"${editing ? '' : attrs(e)}>` +
    `${editing ? field(s) : `<b>${esc(e.title)}</b>`}<span>${span(e.start, e.start + e.dur)}</span></div>`;
};
const chip = (s, e) => {
  const u = s.ui, editing = u.edit === e.id;
  return `<div class="cv-chip${u.sel === e.id ? ' sel' : ''}${dim(s, e) ? ' dim' : ''}" style="${tint(cal(s, e.cal).color)}"${editing ? '' : attrs(e)}><i></i>` +
    `${editing ? field(s) : `<b>${esc(e.title)}</b><span>${time(e.start)}</span>`}</div>`;
};
const card = (s, e) => {
  const c = cal(s, e.cal);
  return `<div class="cv-pop-title"><b>${esc(e.title)}</b><i style="background:${c.color}"></i></div>` +
    `<div class="cv-pop-when">${WD[dow(e.date)]}, ${dayNo(e.date)} ${MONTHS[monNo(e.date)]} ${e.date.slice(0, 4)}</div>` +
    `<div class="cv-pop-when">${time(e.start)} to ${time(e.start + e.dur)}</div>` +
    `<div class="cv-pop-row"><span>Calendar</span>${w.select(c.name, s.calendars.map(x => x.name), 'setcal', e.id)}</div>` +
    `<div class="cv-pop-foot"><span class="btn danger" data-act="delete" data-arg="${e.id}">Delete</span></div>`;
};
const popFor = (s, e, col, n) => {
  const y = (e.start - H0) * HH, top = Math.max(4, Math.min(y - 18, (24 - H0) * HH - POP_H - 4));
  const ay = Math.max(16, Math.min(y + Math.min(e.dur * HH / 2, 20) - top, POP_H - 16));
  return `<div class="cv-popwrap" style="margin-top:${top}px"><div class="cv-pop ${col < n / 2 ? 'r' : 'l'}" data-act="keep" data-drop="-" style="--ay:${ay}px">${card(s, e)}</div></div>`;
};
const dayHeads = (s, days) => `<div class="cv-days"><span class="cv-gsp"></span>` +
  days.map(d => `<div class="cv-dh${d === s.today ? ' today' : ''}${dow(d) > 4 ? ' weekend' : ''}"><span>${days.length > 1 ? wd3(dow(d)) : WD[dow(d)]}</span><b>${dayNo(d)}</b></div>`).join('') + `</div>` +
  `<div class="cv-allday"><span>all-day</span>${days.map(d => `<i class="${dow(d) > 4 ? 'weekend' : ''}"></i>`).join('')}</div>`;
const timeGrid = (s, days, withPop) => {
  const u = s.ui, list = shown(s), now = nowHour(), line = now != null && now >= H0 && days.includes(s.today);
  const hours = Array.from({length: 24 - H0}, (_, i) => H0 + i);
  const gutter = hours.map(h => `<div class="cv-hl">${h === 0 || (line && Math.abs(now - h) < .3) ? '' : `<span>${h === 12 ? 'Noon' : time(h)}</span>`}</div>`).join('') +
    (line ? `<span class="cv-nowlbl" style="top:${(now - H0) * HH}px">${time(now)}</span>` : '');
  const cols = days.map((d, i) => {
    const evs = list.filter(e => e.date === d).sort(byStart), ln = lanes(evs);
    const cells = hours.map(h => { const k = `${d}@${h}`; return `<div class="cv-cell" data-act="clear" data-dbl="create" data-arg="${k}" data-ctx="${k}" data-drop="${k}"></div>`; }).join('');
    const sel = withPop && evs.find(e => e.id === u.sel && e.id !== u.edit);
    return `<div class="cv-col${dow(d) > 4 ? ' weekend' : ''}${sel ? ' haspop' : ''}" data-drop="${d}@col"><div class="cv-cells">${cells}</div>` +
      `<div class="cv-evs">${evs.map(e => block(s, e, ln[e.id])).join('')}${line && d === s.today ? `<i class="cv-now" style="top:${(now - H0) * HH}px"></i>` : ''}</div>` +
      `${sel ? popFor(s, sel, i, days.length) : ''}</div>`;
  }).join('');
  return `<div class="cv-grid scroll" data-scroll="cal-${u.view}"><div class="cv-gridin"><i class="cv-mark" style="top:${(VIEW0 - H0) * HH}px"></i>` +
    `${line ? `<i class="cv-nowall" style="top:${(now - H0) * HH + PAD}px"></i>` : ''}<div class="cv-gutter">${gutter}</div>${cols}</div></div>`;
};
const dayView = s => {
  const u = s.ui, d = u.anchor, list = shown(s).filter(e => e.date === d).sort(byStart), sel = list.find(e => e.id === u.sel && e.id !== u.edit);
  const rows = list.map(e => `<div class="cv-dp-row" data-act="select" data-arg="${e.id}"><i style="background:${cal(s, e.cal).color}"></i><b>${esc(e.title)}</b><span>${span(e.start, e.start + e.dur)}</span></div>`).join('');
  return `<div class="cv-split"><div class="cv-daymain">${dayHeads(s, [d])}${timeGrid(s, [d], false)}</div>` +
    `<div class="cv-daypane"><div class="cv-dp-wd">${WD[dow(d)]}</div><div class="cv-dp-date">${dayNo(d)} ${MONTHS[monNo(d)]} ${d.slice(0, 4)}</div>` +
    `${sel ? `<div class="cv-dp-card">${card(s, sel)}</div>` : rows || `<div class="cv-dp-none">No Events</div>`}</div></div>`;
};
const monthView = s => {
  const u = s.ui, first = monthStart(u.anchor), start = weekOf(first), last = add(addMonths(first, 1), -1), list = shown(s);
  const weeks = Math.round((parse(weekOf(last)) - parse(start)) / 6048e5) + 1, cap = weeks > 5 ? 4 : 5;
  let cells = '', pop = '';
  for (let i = 0; i < weeks * 7; i++) {
    const d = add(start, i), evs = list.filter(e => e.date === d).sort(byStart), vis = evs.length > cap ? evs.slice(0, cap - 1) : evs, n = dayNo(d);
    cells += `<div class="cv-mcell${ym(d) !== ym(first) ? ' other' : ''}${i % 7 > 4 ? ' weekend' : ''}" data-act="clear" data-dbl="create" data-arg="${d}" data-ctx="${d}" data-drop="${d}">` +
      `<span class="cv-mnum${d === s.today ? ' today' : ''}">${n === 1 && d !== s.today ? `${n} ${m3(monNo(d))}` : n}</span>${vis.map(e => chip(s, e)).join('')}` +
      `${evs.length > vis.length ? `<span class="cv-more" data-act="goday" data-arg="${d}">${evs.length - vis.length} more…</span>` : ''}</div>`;
    const sel = vis.find(e => e.id === u.sel && e.id !== u.edit);
    if (sel) {
      const r = Math.floor(i / 7), c = i % 7;
      pop = `<div class="cv-pop m" data-act="keep" data-drop="-" style="${c < 4 ? `left:calc(${(c + 1) / 7 * 100}% + 6px)` : `right:calc(${(7 - c) / 7 * 100}% + 6px)`};` +
        `${r < weeks / 2 ? `top:calc(${r / weeks * 100}% + 6px)` : `bottom:calc(${(weeks - 1 - r) / weeks * 100}% + 6px)`}">${card(s, sel)}</div>`;
    }
  }
  return `<div class="cv-mhead">${WD.map((_, i) => `<span>${wd3(i)}</span>`).join('')}</div><div class="cv-month" style="grid-template-rows:repeat(${weeks},minmax(0,1fr))">${cells}${pop}</div>`;
};
const mini = s => {
  const u = s.ui, first = monthStart(u.anchor), start = weekOf(first), [r0, n] = range(s), r1 = add(r0, n - 1), hl = u.view !== 'month';
  let g = 'MTWTFSS'.split('').map(c => `<i>${c}</i>`).join('');
  for (let i = 0; i < 42; i++) {
    const d = add(start, i), on = hl && d >= r0 && d <= r1;
    g += `<span class="${ym(d) !== ym(first) ? 'other ' : ''}${d === s.today ? 'today ' : ''}${on ? 'in ' : ''}${on && (d === r0 || i % 7 === 0) ? 'a ' : ''}${on && (d === r1 || i % 7 === 6) ? 'z' : ''}" data-act="goto" data-arg="${d}"><b>${dayNo(d)}</b></span>`;
  }
  return `<div class="cv-mini"><div class="cv-mini-h"><b>${MONTHS[monNo(first)]}</b> ${first.slice(0, 4)}</div><div class="cv-mini-g">${g}</div></div>`;
};
const title = s => {
  const u = s.ui, [a, n] = range(s), b = add(a, n - 1);
  if (u.view !== 'week' || ym(a) === ym(b)) return `<b>${MONTHS[monNo(a)]}</b> ${a.slice(0, 4)}`;
  return a.slice(0, 4) === b.slice(0, 4) ? `<b>${m3(monNo(a))} – ${m3(monNo(b))}</b> ${a.slice(0, 4)}` : `<b>${m3(monNo(a))}</b> ${a.slice(0, 4)} – <b>${m3(monNo(b))}</b> ${b.slice(0, 4)}`;
};

TE.register('calendar', {
  title: 'Calendar', size: [1060, 680],
  get dock() {                                                     // the icon shows the date of the menu bar clock
    const st = TE.state || {}, t = (st.apps && st.apps.calendar && st.apps.calendar.today) || '2026-11-12';
    const m = /^([A-Za-z]{3})[a-z]*\s+(\d{1,2})\b/.exec((st.status || {}).clock || '') || [0, wd3(dow(t)), dayNo(t)];
    return {bg: 'linear-gradient(#ffffff, #ececf0)', glyph: `<svg width="50" height="50" viewBox="0 0 50 50"><text x="25" y="15.5" text-anchor="middle" font-size="9.5" font-weight="600" fill="#ff3b30" letter-spacing=".4">${esc(m[1].toUpperCase())}</text>` +
      `<text x="25" y="41" text-anchor="middle" font-size="27" font-weight="400" fill="#1d1d1f">${+m[2]}</text></svg>`};
  },
  before(s, act) { if (!['editing', 'commit', 'cancel'].includes(act)) commit(s); },
  render(s) {
    const u = s.ui, days = (([a, n]) => Array.from({length: n}, (_, i) => add(a, i)))(range(s));
    const side = `<div class="sidebar" data-windrag><div class="cv-callist"><div class="sb-head">iCloud</div>` +
      s.calendars.map(c => `<div class="cv-cal"><span class="cv-check${c.shown ? ' on' : ''}" style="--c:${c.color}" data-act="toggle" data-arg="${c.id}">${c.shown ? icon('check', 11) : ''}</span><span>${esc(c.name)}</span></div>`).join('') +
      `</div>${mini(s)}</div>`;
    const bar = `<div class="toolbar" data-windrag><div class="cv-tb-l"><span class="tb-btn" data-act="new">${icon('plus', 17)}</span></div>` +
      `${w.seg(u.view[0].toUpperCase() + u.view.slice(1), ['Day', 'Week', 'Month'], 'view')}<div class="cv-tb-r">${w.search(u.search || '', 'search')}</div></div>`;
    const head = `<div class="cv-head" data-windrag><span class="cv-title">${title(s)}</span><span class="cv-nav"><span data-act="prev">${icon('left', 13)}</span>` +
      `<span class="cv-today" data-act="today">Today</span><span data-act="next">${icon('right', 13)}</span></span></div>`;
    const body = u.view === 'month' ? monthView(s) : u.view === 'day' ? dayView(s) : dayHeads(s, days) + timeGrid(s, days, true);
    return `<div class="cal">${side}<div class="main">${bar}${head}${body}</div></div>`;
  },
  on: {
    view(s, v) { const k = String(v).toLowerCase(); if (['day', 'week', 'month'].includes(k)) { s.ui.view = k; s.ui.sel = null; } },
    next(s) { step(s, 1); },
    prev(s) { step(s, -1); },
    today(s) { s.ui.anchor = s.today; s.ui.sel = null; },
    goto(s, d) { s.ui.anchor = d; s.ui.sel = null; },
    goday(s, d) { s.ui.anchor = d; s.ui.view = 'day'; s.ui.sel = null; },
    toggle(s, id) { const c = s.calendars.find(c => c.id === id); if (!c) return; c.shown = !c.shown; const e = ev(s, s.ui.sel); if (e && e.cal === id) s.ui.sel = null; },
    select(s, id) { if (ev(s, id)) s.ui.sel = id; },
    clear(s) { s.ui.sel = null; },
    search(s, _, text) { s.ui.search = text; return true; },
    create(s, at) { const [date, h] = String(at || '').split('@'); create(s, date, h == null || h === '' ? null : +h); },
    new(s) { const [a, n] = range(s); create(s, s.today >= a && s.today <= add(a, n - 1) ? s.today : s.ui.view === 'month' ? a : s.ui.anchor, null); },
    rename(s, id) { startEdit(s, id || s.ui.sel); },
    editing(s, _, text) { s.ui.draft = text; },
    commit(s) { commit(s); },
    cancel(s) { s.ui.edit = null; s.ui.draft = ''; },
    delete(s, id) { const k = id || s.ui.sel, i = s.events.findIndex(e => e.id === k); if (i < 0) return; s.events.splice(i, 1); if (s.ui.sel === k) s.ui.sel = null; },
    setcal(s, id, v) { const e = ev(s, id || s.ui.sel), c = s.calendars.find(c => c.id === v || c.name === v); if (!e || !c) return; e.cal = c.id; if (!c.shown) s.ui.sel = null; },
  },
  // An hour cell gives the day and the hour ("2026-11-12@14"); under an event block the day
  // column answers ("2026-11-12@col") and the hour comes from the height; a month cell gives the day.
  drop(s, drag, drop, info) {
    commit(s);
    const e = ev(s, drag), [date, h] = String(drop).split('@');
    if (!e || info.from !== 'calendar' || !/^\d{4}-\d\d-\d\d$/.test(date)) return;
    e.date = date;
    if (h != null) e.start = Math.max(0, Math.min(h === 'col' ? H0 + Math.min(23 - H0, Math.floor(info.fy * (24 - H0))) : +h, 24 - e.dur));
    s.ui.sel = null;
  },
  context(s, arg) {
    commit(s); s.ui.sel = null;
    const e = ev(s, arg);
    if (!e) return /^\d{4}-\d\d-\d\d/.test(arg) ? [{label: 'New Event', act: 'create'}] : [];
    return [{label: 'Get Info', act: 'select'}, '-', {label: 'Calendar', items: s.calendars.map(c => ({label: c.name, act: 'setcal', value: c.id, checked: c.id === e.cal}))}, '-', {label: 'Delete', act: 'delete'}];
  },
  menus(s) {
    const v = s.ui.view, sel = !!ev(s, s.ui.sel);
    return [
      {label: 'File', items: [{label: 'New Event', shortcut: '⌘N', act: 'new'}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true},
        {label: 'Delete', shortcut: '⌫', act: 'delete', disabled: !sel}]},
      {label: 'View', items: [{label: 'Day', shortcut: '⌘1', act: 'view', arg: 'day', checked: v === 'day'}, {label: 'Week', shortcut: '⌘2', act: 'view', arg: 'week', checked: v === 'week'},
        {label: 'Month', shortcut: '⌘3', act: 'view', arg: 'month', checked: v === 'month'}, '-',
        {label: 'Go to Today', shortcut: '⌘T', act: 'today'}, {label: 'Next', shortcut: '⌘→', act: 'next'}, {label: 'Previous', shortcut: '⌘←', act: 'prev'}]},
    ];
  },
  keys: {'Backspace': 'delete', 'Enter': 'rename', 'Escape': 'clear', 'Meta+n': 'new', 'Meta+t': 'today', 'Meta+ArrowRight': 'next', 'Meta+ArrowLeft': 'prev',
    'Meta+1': {act: 'view', arg: 'day'}, 'Meta+2': {act: 'view', arg: 'week'}, 'Meta+3': {act: 'view', arg: 'month'}},
});
})();
