// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Files: a Finder-like file browser. State: {items: [{id, name, kind, parent, date, ts, size, bytes, from?}], next, ui}
(() => {
const {esc, icon, w} = TE;
TE.addIcons({
  folderplus: 'M3 7.5A1.5 1.5 0 0 1 4.5 6H9l2 2.5h8.5A1.5 1.5 0 0 1 21 10v8a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18zM12 11.5v5M9.5 14h5',
});
const ROOTS = [['desktop', 'Desktop', 'display'], ['documents', 'Documents', 'doc'], ['downloads', 'Downloads', 'download'], ['pictures', 'Pictures', 'photo']];
const KIND = {folder: 'Folder', pdf: 'PDF document', doc: 'Word document', sheet: 'Spreadsheet', image: 'JPEG image', audio: 'Audio', zip: 'ZIP archive', slides: 'Presentation'};
const TAG = {pdf: 'PDF', doc: 'DOC', sheet: 'XLS', image: 'JPG', audio: 'M4A', zip: 'ZIP', slides: 'KEY'};
const COLS = [['name', 'Name'], ['date', 'Date Modified'], ['size', 'Size'], ['kind', 'Kind']];
const find = (s, id) => s.items.find(i => i.id === id);
const nameOf = (s, id) => { const r = ROOTS.find(r => r[0] === id); return r ? r[1] : id === 'trash' ? 'Trash' : (find(s, id) || {}).name || ''; };
const listing = s => {
  const u = s.ui, q = u.search.trim().toLowerCase();
  const L = q ? s.items.filter(i => i.parent !== 'trash' && i.name.toLowerCase().includes(q)) : s.items.filter(i => i.parent === u.path);
  const k = u.sort.key, val = i => k === 'name' ? i.name.toLowerCase() : k === 'date' ? i.ts : k === 'size' ? i.bytes : KIND[i.kind];
  return L.sort((a, b) => (val(a) < val(b) ? -1 : val(a) > val(b) ? 1 : a.name.localeCompare(b.name)) * u.sort.dir);
};
const glyph = (it, s) => it.kind === 'folder'
  ? `<span class="fi folder" style="--s:${s}px"><svg viewBox="0 0 64 52" width="${s}" height="${s * 52 / 64}"><path d="M2 9a6 6 0 0 1 6-6h13.5c1.9 0 3.6.8 4.8 2.2L29.5 9H56a6 6 0 0 1 6 6v5H2z" fill="#3d9be9"/><rect x="2" y="13.5" width="60" height="36.5" rx="6" fill="#62b8f6"/></svg></span>`
  : `<span class="fi page k-${it.kind}" style="--s:${s}px"><b>${TAG[it.kind] || ''}</b></span>`;
const uniq = (s, parent, name) => {
  const taken = new Set(s.items.filter(i => i.parent === parent).map(i => i.name));
  if (!taken.has(name)) return name;
  for (let n = 2; ; n++) if (!taken.has(`${name} ${n}`)) return `${name} ${n}`;
};
const go = (s, id) => { const u = s.ui; if (u.path !== id || u.search) { u.back.push(u.path); u.fwd = []; } u.path = id; u.sel = null; u.search = ''; };
const startRename = (s, id) => { const it = find(s, id); if (!it) return; s.ui.sel = id; s.ui.rename = id; s.ui.renameText = it.name; const dot = it.kind === 'folder' ? -1 : it.name.lastIndexOf('.'); TE.focus('rename', dot > 0 ? dot : true); };
const commit = s => { const u = s.ui; if (!u.rename) return; const it = find(s, u.rename), t = (u.renameText || '').trim(); if (it && t) it.name = t; u.rename = null; };

TE.register('files', {
  title: 'Files', size: [900, 560],
  dock: {bg: 'linear-gradient(#57c1ff, #1c7df0)', glyph: '<svg width="34" height="34" viewBox="0 0 24 24" fill="#fff"><path d="M3 7.2C3 6 4 5 5.2 5h3.6c.6 0 1.1.2 1.5.7L11.6 7h7.2C20 7 21 8 21 9.2v8.6c0 1.2-1 2.2-2.2 2.2H5.2C4 20 3 19 3 17.8z"/></svg>'},
  before(s, act) { if (!['renaming', 'rename_commit', 'rename_cancel'].includes(act)) commit(s); },
  render(s) {
    const u = s.ui, items = listing(s), title = u.search ? 'Searching' : nameOf(s, u.path);
    const cellName = it => u.rename === it.id ? w.input(u.renameText, 'renaming', it.id, {focus: 'rename', enter: 'rename_commit', esc: 'rename_cancel', cls: 'f-rename'}) : `<span class="f-name">${esc(it.name)}</span>`;
    const attrs = it => `data-act="select" data-arg="${it.id}" data-dbl="open" data-ctx="${it.id}" data-drag="${it.id}"${it.kind === 'folder' ? ` data-drop="${it.id}"` : ''}`;
    const side = `<div class="sidebar" data-windrag><div class="sb-head">Favourites</div>` +
      ROOTS.map(([id, label, ic]) => `<div class="sb-item${u.path === id && !u.search ? ' sel' : ''}" data-act="go" data-arg="${id}" data-drop="${id}">${icon(ic, 16)}<span>${label}</span></div>`).join('') +
      `<div class="sb-head">Locations</div><div class="sb-item${u.path === 'trash' && !u.search ? ' sel' : ''}" data-act="go" data-arg="trash" data-drop="trash">${icon('trash', 16)}<span>Trash</span></div></div>`;
    const bar = `<div class="toolbar" data-windrag><span class="tb-btn${u.back.length ? '' : ' off'}" data-act="back">${icon('left', 18)}</span><span class="tb-btn${u.fwd.length ? '' : ' off'}" data-act="fwd">${icon('right', 18)}</span>` +
      `<span class="tb-title">${esc(title)}</span><span class="spacer"></span>` +
      `<span class="tb-group"><span class="tb-btn${u.view === 'icons' ? ' on' : ''}" data-act="view" data-arg="icons">${icon('grid', 17)}</span><span class="tb-btn${u.view === 'list' ? ' on' : ''}" data-act="view" data-arg="list">${icon('list', 17)}</span></span>` +
      `<span class="tb-btn" data-act="newfolder">${icon('folderplus', 18)}</span><span class="tb-btn${u.sel ? '' : ' off'}" data-act="trash">${icon('trash', 17)}</span>${w.search(u.search, 'search')}</div>`;
    let body;
    if (u.view === 'icons') {
      body = `<div class="f-grid scroll" data-scroll="files-grid" data-ctx="" data-act="clear">` +
        items.map(it => `<div class="f-cell${u.sel === it.id ? ' sel' : ''}" ${attrs(it)}>${glyph(it, 58)}${cellName(it)}</div>`).join('') + `</div>`;
    } else {
      const arrow = k => u.sort.key === k ? icon(u.sort.dir > 0 ? 'up' : 'down', 10) : '';
      body = `<div class="f-head">${COLS.map(([k, l]) => `<span class="c-${k}" data-act="sort" data-arg="${k}">${l}${arrow(k)}</span>`).join('')}</div>` +
        `<div class="f-list scroll" data-scroll="files-list" data-ctx="" data-act="clear">` +
        items.map(it => `<div class="f-row${u.sel === it.id ? ' sel' : ''}" ${attrs(it)}><span class="c-name">${glyph(it, 17)}${cellName(it)}</span><span class="c-date">${esc(it.date)}</span><span class="c-size">${esc(it.size)}</span><span class="c-kind">${KIND[it.kind]}</span></div>`).join('') + `</div>`;
    }
    const pv = find(s, u.preview);
    const preview = pv ? `<div class="f-preview"><div class="f-pv-bar"><span class="tb-btn" data-act="closepreview">${icon('x', 15)}</span><b>${esc(pv.name)}</b><span class="btn" data-act="closepreview">Done</span></div><div class="f-pv-body">${glyph(pv, 150)}<div class="f-pv-name">${esc(pv.name)}</div><div class="muted">${KIND[pv.kind]} · ${esc(pv.size)} · ${esc(pv.date)}</div></div></div>` : '';
    return `<div class="files" style="display:flex;flex:1;min-width:0">${side}<div class="main">${bar}${body}<div class="f-status">${items.length} item${items.length === 1 ? '' : 's'}${u.path === 'trash' ? ' in Trash' : ''}</div></div>${preview}</div>`;
  },
  on: {
    go(s, id) { go(s, id); },
    back(s) { const u = s.ui; if (u.back.length) { u.fwd.push(u.path); u.path = u.back.pop(); u.sel = null; u.search = ''; } },
    fwd(s) { const u = s.ui; if (u.fwd.length) { u.back.push(u.path); u.path = u.fwd.pop(); u.sel = null; u.search = ''; } },
    up(s) { const it = find(s, s.ui.path); if (it) go(s, it.parent); },
    select(s, id) { s.ui.sel = id; },
    clear(s) { s.ui.sel = null; },
    open(s, id) { const it = find(s, id || s.ui.sel); if (!it) return; if (it.kind === 'folder') go(s, it.id); else s.ui.preview = it.id; },
    closepreview(s) { s.ui.preview = null; },
    view(s, v) { s.ui.view = v; },
    sort(s, k) { const o = s.ui.sort; if (o.key === k) o.dir = -o.dir; else { o.key = k; o.dir = 1; } },
    search(s, _, text) { s.ui.search = text; return true; },
    newfolder(s) {
      const u = s.ui, parent = u.search || u.path === 'trash' ? 'documents' : u.path, id = 'n' + s.next++;
      if (u.search || u.path === 'trash') go(s, parent);
      s.items.push({id, name: uniq(s, parent, 'untitled folder'), kind: 'folder', parent, date: 'Today', ts: 99999 + s.next, size: '--', bytes: 0});
      startRename(s, id);
    },
    rename(s, id) { startRename(s, id || s.ui.sel); },
    renaming(s, _, text) { s.ui.renameText = text; },
    rename_commit(s) { commit(s); },
    rename_cancel(s) { s.ui.rename = null; },
    trash(s, id) { const it = find(s, id || s.ui.sel); if (!it || it.parent === 'trash') return; it.from = it.parent; it.parent = 'trash'; s.ui.sel = null; },
    putback(s, id) { const it = find(s, id || s.ui.sel); if (!it || it.parent !== 'trash') return; it.parent = it.from || 'documents'; delete it.from; s.ui.sel = null; },
    duplicate(s, id) {
      const it = find(s, id || s.ui.sel); if (!it) return;
      const dot = it.kind === 'folder' ? -1 : it.name.lastIndexOf('.'), base = dot > 0 ? it.name.slice(0, dot) : it.name, ext = dot > 0 ? it.name.slice(dot) : '';
      const copy = {...it, id: 'n' + s.next++, name: uniq(s, it.parent, base + ' copy') + ext}; s.items.push(copy); s.ui.sel = copy.id;
    },
  },
  drop(s, drag, drop) {
    const it = find(s, drag); if (!it || drag === drop || it.parent === drop) return;
    for (let p = find(s, drop); p; p = find(s, p.parent)) if (p.id === drag) return;      // a folder cannot go into itself
    if (drop === 'trash') it.from = it.parent;
    it.parent = drop; s.ui.sel = null;
  },
  context(s, id) {
    const it = find(s, id);
    if (!it) return [{label: 'New Folder', act: 'newfolder'}, '-', {label: 'View', items: [{label: 'as Icons', act: 'view', arg: 'icons', checked: s.ui.view === 'icons'}, {label: 'as List', act: 'view', arg: 'list', checked: s.ui.view === 'list'}]},
      {label: 'Sort By', items: COLS.map(([k, l]) => ({label: l, act: 'sort', arg: k, checked: s.ui.sort.key === k}))}];
    s.ui.sel = id;
    if (it.parent === 'trash') return [{label: 'Put Back', act: 'putback'}, '-', {label: 'Delete Immediately…', disabled: true}];
    return [{label: 'Open', act: 'open'}, '-', {label: 'Rename', act: 'rename'}, {label: 'Duplicate', act: 'duplicate'}, {label: 'Get Info', disabled: true}, '-', {label: 'Move to Trash', act: 'trash'}];
  },
  menus(s) {
    const sel = !!s.ui.sel;
    return [
      {label: 'File', items: [{label: 'New Folder', shortcut: '⇧⌘N', act: 'newfolder'}, {label: 'Open', shortcut: '⌘O', act: 'open', disabled: !sel}, '-', {label: 'Rename', act: 'rename', disabled: !sel}, {label: 'Duplicate', shortcut: '⌘D', act: 'duplicate', disabled: !sel}, '-', {label: 'Move to Trash', shortcut: '⌘⌫', act: 'trash', disabled: !sel}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true}]},
      {label: 'View', items: [{label: 'as Icons', shortcut: '⌘1', act: 'view', arg: 'icons', checked: s.ui.view === 'icons'}, {label: 'as List', shortcut: '⌘2', act: 'view', arg: 'list', checked: s.ui.view === 'list'}, '-',
        {label: 'Sort By', items: COLS.map(([k, l]) => ({label: l, act: 'sort', arg: k, checked: s.ui.sort.key === k}))}]},
      {label: 'Go', items: [{label: 'Back', shortcut: '⌘[', act: 'back', disabled: !s.ui.back.length}, {label: 'Forward', shortcut: '⌘]', act: 'fwd', disabled: !s.ui.fwd.length}, {label: 'Enclosing Folder', shortcut: '⌘↑', act: 'up'}, '-',
        ...ROOTS.map(([id, label]) => ({label, act: 'go', arg: id}))]},
    ];
  },
  keys: {'Enter': 'rename', 'Meta+Backspace': 'trash', 'Meta+Shift+n': 'newfolder', 'Meta+d': 'duplicate', 'Meta+o': 'open', 'Meta+ArrowDown': 'open', 'Meta+ArrowUp': 'up',
    'Meta+1': {act: 'view', arg: 'icons'}, 'Meta+2': {act: 'view', arg: 'list'}, 'Meta+[': 'back', 'Meta+]': 'fwd', 'Escape': 'closepreview'},
});
})();
