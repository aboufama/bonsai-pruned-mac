// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Reminders: smart lists and the user's own lists of reminders.
// State: {lists: [{id, name, color}], items: [{id, list, title, done, flagged, due, note}], next,
//         ui: {list, sel, showCompleted, adding, draft}}
//   items      their order is the display order inside each list
//   due        "2026-11-05" or ""; "today" is the date of the menu bar clock (state.status.clock)
//   ui.list    the id of a list, or one of today / scheduled / all / flagged / completed
(() => {
const {esc, icon, w} = TE;
TE.addIcons({
  rm_tray: 'M3.5 13.5L6.5 5h11l3 8.5V19a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1zM3.5 13.5H8l1.5 3h5l1.5-3h4.5',
  rm_cal: 'M4.5 6h15a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zM3.5 10.5h17M8 3.5v4M16 3.5v4',
  rm_tick: 'M5 12.5l4.5 4.5L19 7.5',
  rm_list: 'M9 7h11M9 12h11M9 17h11M4.5 7h.01M4.5 12h.01M4.5 17h.01',
});
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const pad = n => String(n).padStart(2, '0');
// Day number of a calendar date (days since 1 Jan 1970). Plain arithmetic: no clock is read.
const dayNo = (y, m, d) => { y -= m <= 2 ? 1 : 0; const era = Math.floor(y / 400), yoe = y - era * 400, doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1; return era * 146097 + yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy - 719468; };
// "Today" is the day of the menu bar clock, which is part of the state ("Tue 3 Nov  10:12 AM").
const today = () => {
  const m = /(\d+) ([A-Z][a-z][a-z])/.exec((TE.state.status || {}).clock || '');
  const d = m ? +m[1] : 2, mo = m ? MONTHS.indexOf(m[2]) + 1 || 11 : 11;
  return {d, n: dayNo(2026, mo, d)};
};
const dueNo = it => { const m = /^(\d{4})-(\d\d)-(\d\d)$/.exec(it.due || ''); return m ? dayNo(+m[1], +m[2], +m[3]) : null; };
const dueLabel = (it, t) => { const k = dueNo(it) - t.n, m = it.due.split('-'); return k === 0 ? 'Today' : k === 1 ? 'Tomorrow' : k === -1 ? 'Yesterday' : `${m[2]}/${m[1]}/${m[0]}`; };

const SMART = [
  {id: 'today', name: 'Today', color: '#0a7aff', test: (it, t) => it.due && dueNo(it) <= t.n},
  {id: 'scheduled', name: 'Scheduled', color: '#ff3b30', glyph: 'rm_cal', test: it => !!it.due},
  {id: 'all', name: 'All', color: '#3a3a3c', glyph: 'rm_tray', test: () => true},
  {id: 'flagged', name: 'Flagged', color: '#ff9500', glyph: 'flagfill', test: it => it.flagged},
  {id: 'completed', name: 'Completed', color: '#7c8791', glyph: 'rm_tick', test: () => true},
];
const smart = id => SMART.find(x => x.id === id);
const find = (s, id) => s.items.find(i => i.id === id);
const listOf = (s, id) => s.lists.find(l => l.id === id);
// The reminders of the current view, in display order (a smart list shows them list by list).
const view = s => {
  const u = s.ui, sm = smart(u.list), t = today();
  if (!sm) return s.items.filter(it => it.list === u.list && (!it.done || u.showCompleted));
  const keep = it => u.list === 'completed' ? it.done : sm.test(it, t) && (!it.done || u.showCompleted);
  return s.lists.flatMap(l => s.items.filter(it => it.list === l.id && keep(it)));
};
const tally = (s, id, t) => id === 'completed' ? s.items.filter(it => it.done).length : s.items.filter(it => !it.done && (smart(id) ? smart(id).test(it, t) : it.list === id)).length;
// A reminder being typed is added when Return is pressed or when anything else is done.
const commit = s => {
  const u = s.ui; if (!u.adding) return;
  const title = (u.draft || '').trim();
  if (title && s.lists.length) s.items.push({id: 'r' + s.next++, list: listOf(s, u.list) ? u.list : s.lists[0].id, title, done: false, flagged: false, due: '', note: ''});
  u.adding = false; u.draft = '';
};
// A reminder that is no longer shown is no longer selected.
const tidy = s => { if (s.ui.sel && !view(s).some(it => it.id === s.ui.sel)) s.ui.sel = null; };
const moveToList = (s, id, list) => {
  const it = find(s, id); if (!it || it.list === list || !listOf(s, list)) return;
  s.items.splice(s.items.indexOf(it), 1); it.list = list; s.items.push(it);       // goes to the bottom of the other list
  tidy(s);
};
const todayGlyph = d => `<svg class="ic" width="15" height="15" viewBox="0 0 24 24"><rect x="3.2" y="4.2" width="17.6" height="16.6" rx="3.6" fill="none" stroke="currentColor" stroke-width="2"/><text x="12" y="17.3" text-anchor="middle" font-family="Inter, sans-serif" font-size="10.5" font-weight="700" fill="currentColor">${d}</text></svg>`;

TE.register('reminders', {
  title: 'Reminders', size: [900, 640],
  dock: {bg: 'linear-gradient(#ffffff, #f1f1f4)', glyph: '<svg width="50" height="50" viewBox="0 0 50 50" fill="none"><circle cx="13.5" cy="14.5" r="3.6" fill="#0a84ff"/><circle cx="13.5" cy="25" r="3.6" fill="#ff453a"/><circle cx="13.5" cy="35.5" r="3.6" fill="#ff9f0a"/><path d="M22 14.5h18M22 25h18M22 35.5h18" stroke="#c4c4c9" stroke-width="2" stroke-linecap="round"/></svg>'},
  before(s, act) { if (s.ui.adding && !['draft', 'add_commit', 'add_cancel', 'stay'].includes(act)) commit(s); },
  render(s) {
    const u = s.ui, t = today(), sm = smart(u.list), cur = sm || listOf(s, u.list) || {name: '', color: '#8e8e93'}, rows = view(s);
    const tiles = SMART.map(x => `<div class="r-tile${u.list === x.id ? ' sel' : ''}" style="--c:${x.color}" data-act="go" data-arg="${x.id}">` +
      `<span class="r-tile-ic">${x.glyph ? icon(x.glyph, 15) : todayGlyph(t.d)}</span><b>${tally(s, x.id, t)}</b><span class="r-tile-l">${x.name}</span></div>`).join('');
    const side = `<div class="sidebar" data-windrag><div class="r-tiles">${tiles}</div><div class="sb-head">My Lists</div>` +
      s.lists.map(l => `<div class="r-list${u.list === l.id ? ' sel' : ''}" data-act="go" data-arg="${l.id}" data-drop="list:${l.id}"><span class="r-dot" style="background:${l.color}">${icon('rm_list', 13)}</span>` +
        `<span class="r-lname">${esc(l.name)}</span><span class="count">${tally(s, l.id, t)}</span></div>`).join('') + `</div>`;
    const row = it => {
      const l = listOf(s, it.list) || {color: '#8e8e93'}, late = it.due && !it.done && dueNo(it) < t.n;
      return `<div class="r-row${u.sel === it.id ? ' sel' : ''}${it.done ? ' done' : ''}" style="--c:${l.color}" data-act="select" data-arg="${it.id}" data-ctx="${it.id}" data-drag="${it.id}" data-drop="${it.id}">` +
        `<span class="r-circle" data-act="toggle" data-arg="${it.id}"><i></i></span><span class="r-main"><span class="r-title">${esc(it.title)}</span>` +
        (it.note ? `<span class="r-sub">${esc(it.note)}</span>` : '') + (it.due ? `<span class="r-sub${late ? ' late' : ''}">${dueLabel(it, t)}</span>` : '') + `</span>` +
        (it.flagged ? `<span class="r-flag">${icon('flagfill', 14)}</span>` : '') + `</div>`;
    };
    let body = '', last = null;
    for (const it of rows) {
      if (sm && it.list !== last) { const l = listOf(s, it.list); body += `<div class="r-sect" style="color:${l.color}">${esc(l.name)}</div>`; last = it.list; }
      body += row(it);
    }
    const canAdd = u.list !== 'completed';
    if (u.adding) body += `<div class="r-row r-new" data-act="stay"><span class="r-circle"><i></i></span><span class="r-main">${w.input(u.draft, 'draft', '', {focus: 'newrem', enter: 'add_commit', esc: 'add_cancel', cls: 'r-input'})}</span></div>`;
    else if (canAdd) body += `<div class="r-row r-new" data-act="add"><span class="r-circle r-plus">${icon('plus', 11)}</span><span class="r-main"><span class="r-title">New Reminder</span></span></div>`;
    if (!rows.length && !u.adding) body += `<div class="r-none">${u.list === 'completed' ? 'No Completed Reminders' : 'No Reminders'}</div>`;
    const nDone = sm ? 0 : s.items.filter(it => it.list === u.list && it.done).length;
    const head = `<div class="r-head" style="color:${cur.color}"><span class="r-name">${esc(cur.name)}</span><span class="r-total">${tally(s, u.list, t)}</span></div>` +
      (u.showCompleted && !sm ? `<div class="r-info">${nDone} Completed</div>` : '');
    const main = `<div class="main"><div class="toolbar" data-windrag><span class="spacer"></span><span class="tb-btn${canAdd ? '' : ' off'}" data-act="add">${icon('plus', 19)}</span></div>` +
      `${head}<div class="r-items scroll" data-scroll="reminders-items" data-act="blank" data-ctx="">${body}</div></div>`;
    return `<div class="reminders">${side}${main}</div>`;
  },
  on: {
    go(s, id) { s.ui.list = id; s.ui.sel = null; },
    select(s, id) { s.ui.sel = id; },
    blank(s) { s.ui.sel = null; },
    stay() { return false; },
    toggle(s, id) { const it = find(s, id || s.ui.sel); if (it) it.done = !it.done; tidy(s); },
    flag(s, id) { const it = find(s, id || s.ui.sel); if (it) it.flagged = !it.flagged; tidy(s); },
    del(s, id) { const it = find(s, id || s.ui.sel); if (!it) return; s.items.splice(s.items.indexOf(it), 1); if (s.ui.sel === it.id) s.ui.sel = null; },
    move(s, arg) { const [id, list] = String(arg).split('|'); moveToList(s, id, list); },
    completed(s) { s.ui.showCompleted = !s.ui.showCompleted; tidy(s); },
    add(s) { const u = s.ui; if (u.list === 'completed') return; u.adding = true; u.draft = ''; u.sel = null; TE.focus('newrem'); },
    draft(s, _, text) { s.ui.draft = text; },
    add_commit(s, _, text) { if (typeof text === 'string') s.ui.draft = text; commit(s); },
    add_cancel(s) { s.ui.adding = false; s.ui.draft = ''; },
  },
  // Dropped on a list in the sidebar, a reminder moves to that list. Dropped on another reminder it is put
  // next to it: before it when released on its top third, after it on its bottom third, and in between it
  // takes that reminder's place (before it when dragged upwards, after it when dragged downwards).
  drop(s, drag, drop, info) {
    commit(s);
    if (drop.startsWith('list:')) { moveToList(s, drag, drop.slice(5)); return; }
    const it = find(s, drag), to = find(s, drop); if (!it || !to || it === to) return;
    const from = s.items.indexOf(it), before = info.fy < 1 / 3 ? true : info.fy > 2 / 3 ? false : from > s.items.indexOf(to);
    s.items.splice(from, 1); it.list = to.list;
    s.items.splice(s.items.indexOf(to) + (before ? 0 : 1), 0, it);
    tidy(s);
  },
  context(s, id) {
    const it = find(s, id);
    if (!it) return s.ui.list === 'completed' ? [] : [{label: 'New Reminder', act: 'add'}];
    s.ui.sel = id;
    return [{label: it.done ? 'Mark as Incomplete' : 'Mark as Completed', act: 'toggle'}, '-', {label: it.flagged ? 'Remove Flag' : 'Flag', act: 'flag'},
      {label: 'Move to List', items: s.lists.filter(l => l.id !== it.list).map(l => ({label: l.name, act: 'move', arg: id + '|' + l.id}))}, '-', {label: 'Delete', act: 'del'}];
  },
  menus(s) {
    const it = find(s, s.ui.sel);
    return [
      {label: 'File', items: [{label: 'New Reminder', shortcut: '⌘N', act: 'add', disabled: s.ui.list === 'completed'}, {label: 'New List', shortcut: '⇧⌘N', disabled: true}, '-', {label: 'Print…', shortcut: '⌘P', disabled: true}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true}, '-',
        {label: it && it.flagged ? 'Remove Flag' : 'Flag', shortcut: '⇧⌘F', act: 'flag', disabled: !it}, {label: 'Delete', shortcut: '⌫', act: 'del', disabled: !it}]},
      {label: 'View', items: [{label: s.ui.showCompleted ? 'Hide Completed' : 'Show Completed', shortcut: '⇧⌘H', act: 'completed'}, '-', {label: 'Sort By', disabled: true, items: []}, {label: 'Hide Sidebar', shortcut: '⌥⌘S', disabled: true}]},
    ];
  },
  keys: {'Backspace': 'del', 'Meta+n': 'add', 'Meta+Shift+h': 'completed', 'Meta+Shift+f': 'flag'},
  key(s, e) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return false;
    const L = view(s), i = L.findIndex(it => it.id === s.ui.sel), j = i < 0 ? 0 : i + (e.key === 'ArrowDown' ? 1 : -1);
    if (L[j]) s.ui.sel = L[j].id;
    return true;
  },
});
})();
