// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// System Settings. The panes and their controls come with the state (s.schema, written by
// tasks/settings.py), so this file only knows how to draw a row of each type.
// State: {schema: [pane | null], v: {key: value}, networks: [...], owner, ui: {pane, search}}
(() => {
const {esc, icon, w} = TE;
const paneOf = (s, id) => s.schema.find(p => p && p.id === id);
const badge = (p, size = 20) => `<span class="st-badge" style="background:${p.color};width:${size}px;height:${size}px">${icon(p.icon, Math.round(size * .68))}</span>`;
const row = (s, r) => {
  const v = s.v[r.k];
  let ctl = '';
  if (r.t === 'toggle') ctl = w.toggle(v, 'toggle', r.k);
  else if (r.t === 'slider') ctl = `<span class="st-slide">${r.lo ? icon(r.lo, 15) : ''}${w.slider(v, 'slide', r.k)}${r.hi ? icon(r.hi, 17) : ''}</span>`;
  else if (r.t === 'select') ctl = w.select(v, r.opts, 'choose', r.k);
  else if (r.t === 'seg') ctl = `<span class="seg">${r.opts.map(o => `<span class="${o === v ? 'on' : ''}" data-act="set" data-arg="${esc(r.k + '=' + o)}">${esc(o)}</span>`).join('')}</span>`;
  else if (r.t === 'info') ctl = `<span class="muted">${esc(r.value)}</span>`;
  else if (r.t === 'colors') ctl = `<span class="st-colors">${r.opts.map(([name, c]) => `<span class="st-color${name === v ? ' on' : ''}" data-act="set" data-arg="${esc(r.k + '=' + name)}"><i style="background:${c}"></i></span>`).join('')}</span>`;
  else if (r.t === 'thumbs') return `<div class="st-row tall"><span class="st-label">${esc(r.label)}</span><span class="st-thumbs">${r.opts.map(o => `<span class="st-thumb${o === v ? ' on' : ''}" data-act="set" data-arg="${esc(r.k + '=' + o)}"><i class="th-${o.toLowerCase()}"><b></b></i><em>${esc(o)}</em></span>`).join('')}</span></div>`;
  else if (r.t === 'pick') return (s[r.from] || []).map(name => `<div class="st-row pick" data-act="set" data-arg="${esc(r.k + '=' + name)}"><span class="st-tick">${name === v ? icon('check', 14) : ''}</span><span class="st-label">${esc(name)}</span><span class="st-ctl muted">${icon('lock', 13)}${icon('wifi', 15)}</span></div>`).join('');
  return `<div class="st-row"><span class="st-label">${esc(r.label)}${r.sub ? `<small>${esc(r.sub)}</small>` : ''}</span><span class="st-ctl">${ctl}</span></div>`;
};

TE.register('settings', {
  title: 'System Settings', size: [860, 600],
  dock: {bg: 'linear-gradient(#a6a7ad, #5d5e66)', glyph: icon('gear', 36)},
  render(s) {
    const u = s.ui, q = u.search.trim().toLowerCase(), cur = paneOf(s, u.pane);
    const match = p => !q || p.label.toLowerCase().includes(q) || p.groups.some(g => g.rows.some(r => (r.label || '').toLowerCase().includes(q)));
    let side = '', gap = false;
    for (const p of s.schema) {
      if (!p) { gap = true; continue; }
      if (!match(p)) continue;
      side += `<div class="sb-item st-item${u.pane === p.id ? ' sel' : ''}${gap && !q ? ' gap' : ''}" data-act="pane" data-arg="${p.id}">${badge(p)}<span>${esc(p.label)}</span></div>`; gap = false;
    }
    const body = cur.groups.map(g => `${g.title ? `<div class="st-gtitle">${esc(g.title)}</div>` : ''}<div class="st-card">${g.rows.map(r => row(s, r)).join('')}</div>`).join('');
    return `<div class="settings" style="display:flex;flex:1;min-width:0"><div class="sidebar scroll" data-scroll="settings-side" data-windrag>` +
      `<div class="st-search">${w.search(u.search, 'search')}</div>` +
      (q ? '' : `<div class="st-account"><span class="st-avatar">${esc(s.owner.split(' ').map(x => x[0]).join(''))}</span><span><b>${esc(s.owner)}</b><small>Apple Account</small></span></div>`) +
      (side || '<div class="st-none">No Results</div>') + `</div>` +
      `<div class="main st-main"><div class="toolbar st-bar" data-windrag><span class="tb-btn off">${icon('left', 18)}</span><span class="tb-btn off">${icon('right', 18)}</span><span class="tb-title">${esc(cur.label)}</span></div>` +
      `<div class="st-body scroll" data-scroll="settings-${cur.id}"><div class="st-head">${badge(cur, 34)}<span><b>${esc(cur.label)}</b><small>${esc(cur.blurb || '')}</small></span></div>${body}</div></div></div>`;
  },
  on: {
    pane(s, id) { s.ui.pane = id; },
    search(s, _, text) { s.ui.search = text; return true; },
    toggle(s, k) { s.v[k] = !s.v[k]; },
    slide(s, k, v) { s.v[k] = Math.round(v * 1000) / 1000; },
    choose(s, k, val) { s.v[k] = val; },
    set(s, arg) { const i = arg.indexOf('='); s.v[arg.slice(0, i)] = arg.slice(i + 1); },
  },
  menus(s) {
    return [
      {label: 'File', items: [{label: 'Close', shortcut: '⌘W', sys: 'close'}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true}]},
      {label: 'View', items: s.schema.filter(Boolean).map(p => ({label: p.label, act: 'pane', arg: p.id, checked: p.id === s.ui.pane}))},
    ];
  },
});
})();
