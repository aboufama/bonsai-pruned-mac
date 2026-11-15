// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Notes: folders, the notes of one folder, and a plain-text editor.
// State: {folders: [{id, name}], notes: [{id, folder, body, date, pinned}], next, ui: {folder, sel, search}}
//   body   the whole text; its first non-empty line is the title shown in the list
//   date   "2026-10-27 14:05"; a new note takes the time of the menu bar clock (state.status.clock)
(() => {
const {esc, icon, w} = TE;
TE.addIcons({
  nt_checklist: 'M3.5 6.5l1.7 1.7 3-3.4M11.5 6.5h9M3.5 12.5l1.7 1.7 3-3.4M11.5 12.5h9M3.5 18.5l1.7 1.7 3-3.4M11.5 18.5h9',
  nt_pin: '!M8.2 3h7.6v1.6l-1.3 1v4.7l3 2.7v1.7h-4.7V21L12 22.5 11.2 21v-6.3H6.5V13l3-2.7V5.6l-1.3-1z',
});
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const pad = n => String(n).padStart(2, '0');
// Day number of a calendar date (days since 1 Jan 1970). Plain arithmetic: no clock is read.
const dayNo = (y, m, d) => { y -= m <= 2 ? 1 : 0; const era = Math.floor(y / 400), yoe = y - era * 400, doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1; return era * 146097 + yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy - 719468; };
const parse = t => { const m = /^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)$/.exec(t || '') || [0, 2026, 11, 1, 9, 0]; return {y: +m[1], mo: +m[2], d: +m[3], h: +m[4], mi: +m[5], n: dayNo(+m[1], +m[2], +m[3])}; };
// "Now" is the menu bar clock, which is part of the state ("Tue 3 Nov  10:12 AM").
const now = () => {
  const m = /(\d+) ([A-Z][a-z][a-z])\s+(\d+):(\d\d) (AM|PM)/.exec((TE.state.status || {}).clock || '');
  if (!m) return '2026-11-02 09:41';
  const mo = MONTHS.findIndex(x => x.startsWith(m[2])) + 1 || 11, h = +m[3] % 12 + (m[5] === 'PM' ? 12 : 0);
  return `2026-${pad(mo)}-${pad(+m[1])} ${pad(h)}:${m[4]}`;
};
const clock = p => `${p.h % 12 || 12}:${pad(p.mi)} ${p.h < 12 ? 'AM' : 'PM'}`;
const shortDate = (p, t) => { const k = t.n - p.n; return k === 0 ? clock(p) : k === 1 ? 'Yesterday' : k > 1 && k < 7 ? DAYS[(p.n + 4) % 7] : `${pad(p.d)}/${pad(p.mo)}/${p.y}`; };
const longDate = p => `${p.d} ${MONTHS[p.mo - 1]} ${p.y} at ${clock(p)}`;
const group = (p, t) => { const k = t.n - p.n; return k <= 0 ? 'Today' : k === 1 ? 'Yesterday' : k <= 7 ? 'Previous 7 Days' : k <= 30 ? 'Previous 30 Days' : p.y === t.y ? MONTHS[p.mo - 1] : String(p.y); };

const find = (s, id) => s.notes.find(n => n.id === id);
const lines = n => n.body.split('\n').map(l => l.trim()).filter(Boolean);
const titleOf = n => lines(n)[0] || 'New Note';
const snippet = n => lines(n)[1] || 'No additional text';
// The notes of the list column, in display order: pinned first, then newest first.
const listing = s => {
  const q = s.ui.search.trim().toLowerCase();
  const L = s.notes.map((n, i) => [n, i]).filter(([n]) => q ? n.body.toLowerCase().includes(q) : n.folder === s.ui.folder);
  L.sort((a, b) => (b[0].pinned - a[0].pinned) || (a[0].date < b[0].date ? 1 : a[0].date > b[0].date ? -1 : b[1] - a[1]));
  return L.map(x => x[0]);
};
// After the open note left the list (deleted, moved), open the one that took its place.
const reselect = (s, before, id) => {
  if (s.ui.sel !== id) return;
  const L = listing(s), i = before.findIndex(n => n.id === id);
  if (L.some(n => n.id === id)) return;
  s.ui.sel = L.length ? L[Math.min(Math.max(i, 0), L.length - 1)].id : null;
};
const moveTo = (s, id, folder) => {
  const n = find(s, id); if (!n || n.folder === folder || !s.folders.some(f => f.id === folder)) return;
  const before = listing(s); n.folder = folder; reselect(s, before, id);
};
const moveItems = (s, n) => s.folders.filter(f => f.id !== n.folder).map(f => ({label: f.name, act: 'move', arg: n.id + '|' + f.id}));

TE.register('notes', {
  title: 'Notes', size: [980, 640],
  dock: {bg: 'linear-gradient(#ffdf5e 0, #fbc92b 28%, #fff 28%)', glyph: '<svg width="50" height="50" viewBox="0 0 50 50" fill="none"><path d="M3 14.2h44" stroke="#b9891a" stroke-width="1" stroke-dasharray="1.6 2.2"/><path d="M9 23.5h32M9 31.5h32M9 39.5h21" stroke="#c9c9ce" stroke-width="1.7" stroke-linecap="round"/></svg>'},
  render(s) {
    const u = s.ui, L = listing(s), t = parse(now()), cur = find(s, u.sel), q = u.search.trim();
    const count = id => s.notes.filter(n => n.folder === id).length;
    const folderName = id => (s.folders.find(f => f.id === id) || {}).name || '';
    const side = `<div class="sidebar" data-windrag><div class="sb-head">iCloud</div>` +
      s.folders.map(f => `<div class="sb-item${!q && u.folder === f.id ? ' sel' : ''}" data-act="folder" data-arg="${f.id}" data-drop="folder:${f.id}">${icon('folder', 17)}<span>${esc(f.name)}</span><span class="count">${count(f.id)}</span></div>`).join('') + `</div>`;
    let rows = '', last = null;
    for (const n of L) {
      const p = parse(n.date), g = n.pinned ? 'Pinned' : group(p, t);
      if (g !== last) { rows += `<div class="n-group">${n.pinned ? icon('nt_pin', 11) : ''}<span>${g}</span></div>`; last = g; }
      rows += `<div class="n-row${u.sel === n.id ? ' sel' : ''}" data-act="select" data-arg="${n.id}" data-ctx="${n.id}" data-drag="${n.id}"><div class="n-title">${esc(titleOf(n))}</div>` +
        `<div class="n-meta"><span class="n-when">${shortDate(p, t)}</span><span class="n-snip">${esc(snippet(n))}</span></div>` +
        (q ? `<div class="n-where">${icon('folder', 12)}<span>${esc(folderName(n.folder))}</span></div>` : '') + `</div>`;
    }
    if (!L.length) rows = `<div class="n-empty">${q ? 'No Results' : 'No Notes'}</div>`;
    const list = `<div class="n-listcol"><div class="toolbar" data-windrag><span class="tb-group"><span class="tb-btn on">${icon('list', 17)}</span><span class="tb-btn">${icon('grid', 16)}</span></span>` +
      `<span class="spacer"></span><span class="tb-btn${cur ? '' : ' off'}" data-act="del">${icon('trash', 17)}</span></div>` +
      `<div class="n-list scroll" data-scroll="notes-list" data-ctx="">${rows}</div></div>`;
    let page = '<div class="n-page"></div>';
    if (cur) {
      // The textarea's own text is transparent; the same text is drawn over it with the title line emphasised.
      const ls = cur.body.split('\n'), k = ls.findIndex(l => l.trim());
      const mirror = k < 0 ? esc(cur.body) : esc(ls.slice(0, k).map(l => l + '\n').join('')) + `<b>${esc(ls[k])}</b>` + esc(ls.slice(k + 1).map(l => '\n' + l).join(''));
      page = `<div class="n-page scroll" data-scroll="notes-page"><div class="n-date">${longDate(parse(cur.date))}</div>` +
        `<div class="n-sheet"><textarea class="n-text" spellcheck="false" autocomplete="off" rows="${ls.length}" data-input="edit" data-arg="${cur.id}" data-focus="note:${cur.id}">\n${esc(cur.body)}</textarea><div class="n-mirror">${mirror}</div></div>` +
        `<div class="n-tail" data-act="tail"></div></div>`;
    }
    const editor = `<div class="n-editor"><div class="toolbar" data-windrag><span class="tb-btn" data-act="new">${icon('compose', 18)}</span>` +
      `<span class="n-tools"><span class="tb-btn n-aa">Aa</span><span class="tb-btn">${icon('nt_checklist', 18)}</span><span class="tb-btn">${icon('table', 18)}</span></span>` +
      `<span class="spacer"></span>${w.search(u.search, 'search')}</div>${page}</div>`;
    return `<div class="notes">${side}${list}${editor}</div>`;
  },
  on: {
    folder(s, id) { const u = s.ui; u.folder = id; u.search = ''; const L = listing(s); u.sel = L.length ? L[0].id : null; },
    select(s, id) { s.ui.sel = id; },
    search(s, _, text) { const u = s.ui; u.search = text; const L = listing(s); if (!L.some(n => n.id === u.sel)) u.sel = L.length ? L[0].id : null; return true; },
    edit(s, id, text) { const n = find(s, id); if (n) n.body = text; return true; },
    tail(s) { if (find(s, s.ui.sel)) TE.focus('note:' + s.ui.sel); },
    new(s) {
      const u = s.ui; u.search = '';
      if (!s.folders.some(f => f.id === u.folder)) u.folder = s.folders[0].id;
      const id = 'n' + s.next++;
      s.notes.push({id, folder: u.folder, body: '', date: now(), pinned: false});
      u.sel = id; TE.focus('note:' + id);
    },
    del(s, id) {
      const n = find(s, id || s.ui.sel); if (!n) return;
      const before = listing(s); s.notes.splice(s.notes.indexOf(n), 1); reselect(s, before, n.id);
    },
    pin(s, id) { const n = find(s, id || s.ui.sel); if (n) n.pinned = !n.pinned; },
    move(s, arg) { const [id, folder] = String(arg).split('|'); moveTo(s, id, folder); },
  },
  drop(s, drag, drop) { if (drop.startsWith('folder:')) moveTo(s, drag, drop.slice(7)); },
  context(s, id) {
    const n = find(s, id);
    if (!n) return [{label: 'New Note', act: 'new'}];
    return [{label: n.pinned ? 'Unpin Note' : 'Pin Note', act: 'pin'}, {label: 'Lock Note', disabled: true}, '-',
      {label: 'Move to', items: moveItems(s, n)}, {label: 'Share Note…', disabled: true}, '-', {label: 'Delete', act: 'del'}];
  },
  menus(s) {
    const n = find(s, s.ui.sel);
    return [
      {label: 'File', items: [{label: 'New Note', shortcut: '⌘N', act: 'new'}, {label: 'New Folder', shortcut: '⇧⌘N', disabled: true}, '-',
        {label: n && n.pinned ? 'Unpin Note' : 'Pin Note', act: 'pin', disabled: !n}, {label: 'Move to', disabled: !n, items: n ? moveItems(s, n) : []}, '-',
        {label: 'Print…', shortcut: '⌘P', disabled: true}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true},
        {label: 'Paste', shortcut: '⌘V', disabled: true}, '-', {label: 'Delete', shortcut: '⌘⌫', act: 'del', disabled: !n}]},
      {label: 'View', items: [{label: 'as List', checked: true}, {label: 'as Gallery', disabled: true}, '-', {label: 'Hide Folders', disabled: true}]},
    ];
  },
  keys: {'Meta+n': 'new', 'Meta+Backspace': 'del'},
  key(s, e) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return false;
    const L = listing(s), i = L.findIndex(n => n.id === s.ui.sel), j = i + (e.key === 'ArrowDown' ? 1 : -1);
    if (L[j]) s.ui.sel = L[j].id;
    return true;
  },
});
})();
