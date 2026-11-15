// macsim: the TRAINING simulator's desktop shell. The engine (windows, menus, drag, keys) is derived from
// taskenv/web/shell.js; no app, layout, content, theme or seed of the test environment is used here.
// Screens have real Mac sizes, light and dark appearance, the system font and Apple's own symbol and app-icon renders
// (served from a folder outside the repository). Every element that can be asked for carries data-role and data-name.
//
// The desktop shell: menu bar, Dock, windows, menus, drag and drop, sliders, text shortcuts.
// Apps register themselves with TE.register(name, def) and are pure "state -> HTML" programs:
//
//   def.title            name in the menu bar and the Dock
//   def.dock             {bg: css background, glyph: svg string} for the Dock icon
//   def.size             [w, h] default window size
//   def.chrome           "toolbar" (traffic lights sit in a 52 px toolbar, default) or "compact"
//   def.render(s)        HTML of the window body, from the app's state s (TE.state.apps[name])
//   def.on[act](s, arg, v, el)   handler; v is the DOM event for clicks, the text for inputs, a
//                        number 0..1 for sliders, the chosen option for selects and menus.
//                        The window is re-rendered afterwards unless the handler returns false
//                        (handlers of text inputs re-render only when they return true).
//   def.menus(s)         [{label, items: [{label, shortcut, act, arg, disabled, checked, items} | '-']}]
//   def.context(s, arg)  items of the right-click menu for an element with data-ctx="arg"
//   def.drop(s, drag, drop, info)   called when an element with data-drag is released over one
//                        with data-drop; info = {pos: 'before'|'after', fx, fy, from: app}
//   def.keys             {'Meta+n': 'act' | {act, arg}}  shortcuts while the app is frontmost
//   def.key(s, e)        any other key press outside a text field; return true if handled
//
// Markup hooks (all handled by delegation here, so an app never adds listeners):
//   data-act="name" data-arg="x"      click
//   data-dbl="name" data-arg="x"      double click
//   data-ctx="x"                      right click -> def.context(s, x)
//   data-input="name" data-arg="x"    text field: every change calls on[name](s, x, text)
//   data-enter="name" / data-esc="name"   Return / Escape in a text field
//   data-focus="key"                  identity of a text field across re-renders (focus is kept)
//   data-scroll="key"                 identity of a scrolling box across re-renders
//   data-drag="x" / data-drop="y"     drag source / drop target
//   data-slider="name" data-arg="x"   slider (use TE.w.slider)
//   data-select="name"                pop-up button (use TE.w.select)
//   data-windrag                      dragging here moves the window
(() => {
'use strict';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const TE = window.TE = {apps: {}, state: null, esc, errors: [], clip: '', pendingFocus: null};
const $ = (q, r = document) => r.querySelector(q);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

// ------------------------------------------------------------------ icons (24 x 24, drawn for this project)
const ICONS = {
  trash: 'M4 7h16M9.5 7V4.5h5V7M6.5 7l.9 13h9.2l.9-13M10 11v6M14 11v6',
  archive: 'M3.5 5h17v4h-17zM5 9v10.5h14V9M9.5 13h5',
  reply: 'M10 6l-6 6 6 6M4 12h9a7 7 0 0 1 7 7',
  forward: 'M14 6l6 6-6 6M20 12h-9a7 7 0 0 0-7 7',
  flag: 'M6 21V4M6 5h11l-2.5 4 2.5 4H6',
  compose: 'M19 13.5V19a1.5 1.5 0 0 1-1.5 1.5h-12A1.5 1.5 0 0 1 4 19V7a1.5 1.5 0 0 1 1.5-1.5H11M17.5 3.5l3 3L12 15l-4 1 1-4z',
  search: 'M10.5 4a6.5 6.5 0 1 0 0 13a6.5 6.5 0 0 0 0-13zM15.5 15.5L20 20',
  plus: 'M12 5v14M5 12h14', minus: 'M5 12h14',
  left: 'M15 5l-7 7 7 7', right: 'M9 5l7 7-7 7', down: 'M5 9l7 7 7-7', up: 'M5 15l7-7 7 7',
  updown: 'M7.5 9.5L12 5l4.5 4.5M7.5 14.5L12 19l4.5-4.5',
  folder: '!M3 7.2C3 6 4 5 5.2 5h3.6c.6 0 1.1.2 1.5.7L11.6 7h7.2C20 7 21 8 21 9.2v8.6c0 1.2-1 2.2-2.2 2.2H5.2C4 20 3 19 3 17.8z',
  doc: 'M6.5 3h7l4.5 4.5V20a1 1 0 0 1-1 1h-10.5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM13.5 3v4.5H18',
  gear: 'M12 5.5a6.5 6.5 0 1 0 0 13a6.5 6.5 0 0 0 0-13zM12 9.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 0 0 0-5zM12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1',
  wifi: 'M2.5 9.5a14 14 0 0 1 19 0M5.5 13a9.5 9.5 0 0 1 13 0M8.6 16.4a5 5 0 0 1 6.8 0M12 19.6h.01',
  bluetooth: 'M7 7.5l10 9-5 4.5V3l5 4.5-10 9',
  speaker: 'M4 9.5h3.5L12 5.5v13l-4.5-4H4zM15.5 9a4.5 4.5 0 0 1 0 6M18 6.5a8 8 0 0 1 0 11',
  speakerlow: 'M6 9.5h3.5L14 5.5v13l-4.5-4H6zM17.5 9.5a4 4 0 0 1 0 5',
  bell: 'M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15zM10 20.5a2 2 0 0 0 4 0',
  moon: 'M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z',
  sun: 'M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8zM12 2.5V5M12 19v2.5M2.5 12H5M19 12h2.5M5.2 5.2L7 7M17 17l1.8 1.8M5.2 18.8L7 17M17 7l1.8-1.8',
  play: '!M7 4.5v15l13-7.5z', pause: '!M6.5 5h4v14h-4zM13.5 5h4v14h-4z',
  next: '!M3.5 6v12l8.5-6zM12 6v12l8.5-6z', prev: '!M20.5 6v12L12 12zM12 6v12l-8.5-6z',
  shuffle: 'M3 7h3.5c3 0 4.5 2 6 5s3 5 6 5H21M3 17h3.5c1.5 0 2.7-.6 3.7-1.6M13.8 8.6c1-1 2.2-1.6 3.7-1.6H21M18.5 4.5L21 7l-2.5 2.5M18.5 14.5L21 17l-2.5 2.5',
  repeat: 'M4 11V9.5A2.5 2.5 0 0 1 6.5 7H19M16.5 4.5L19 7l-2.5 2.5M20 13v1.5a2.5 2.5 0 0 1-2.5 2.5H5M7.5 19.5L5 17l2.5-2.5',
  heart: 'M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.3 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z',
  heartfill: '!M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.3 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z',
  star: 'M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L12 16.9 6.8 19.7l1-5.9L3.5 9.7l5.9-.8z',
  starfill: '!M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L12 16.9 6.8 19.7l1-5.9L3.5 9.7l5.9-.8z',
  flagfill: '!M5 21.5V3.5h1.5v1H18l-2.7 4.5L18 13.5H6.5v8z',
  sidebar: 'M4 5.5h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1zM9 5.5v13',
  grid: 'M4.5 4.5h6v6h-6zM13.5 4.5h6v6h-6zM4.5 13.5h6v6h-6zM13.5 13.5h6v6h-6z',
  list: 'M8 6.5h12M8 12h12M8 17.5h12M4 6.5h.01M4 12h.01M4 17.5h.01',
  share: 'M12 15V3.5M8 7l4-4 4 4M7 11H5.5a1 1 0 0 0-1 1v7.5a1 1 0 0 0 1 1h13a1 1 0 0 0 1-1V12a1 1 0 0 0-1-1H17',
  tag: 'M3.5 12.5V4.5a1 1 0 0 1 1-1h8L21 12l-8.5 8.5zM8 8h.01',
  clock: 'M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 0 0 0-17zM12 7v5l3.5 2',
  calendar: 'M4.5 6h15a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zM3.5 10.5h17M8 3.5v4M16 3.5v4',
  person: 'M12 4a4 4 0 1 0 0 8a4 4 0 0 0 0-8zM4.5 20.5a7.5 7.5 0 0 1 15 0',
  lock: 'M6 11h12a1 1 0 0 1 1 1v7.5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V12a1 1 0 0 1 1-1zM8 11V8a4 4 0 0 1 8 0v3',
  globe: 'M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18',
  battery: 'M3.5 8h15a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zM21.5 10.5v3',
  keyboard: 'M3.5 6.5h17a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-17a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1zM6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M7.5 14h9',
  display: 'M3.5 5h17a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-17a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM9 20.5h6M12 17v3.5',
  photo: 'M4.5 5h15a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM3.5 16l5-5 4 4 3-3 5 5M15.5 9h.01',
  note: 'M9 18V5.5l10-2V16M9 18a2.5 2.5 0 1 1-5 0a2.5 2.5 0 0 1 5 0zM19 16a2.5 2.5 0 1 1-5 0a2.5 2.5 0 0 1 5 0z',
  check: 'M5 12.5l4.5 4.5L19 7.5', x: 'M6 6l12 12M18 6L6 18',
  dots: '!M5.5 10.3a1.7 1.7 0 1 0 0 3.4a1.7 1.7 0 0 0 0-3.4zM12 10.3a1.7 1.7 0 1 0 0 3.4a1.7 1.7 0 0 0 0-3.4zM18.5 10.3a1.7 1.7 0 1 0 0 3.4a1.7 1.7 0 0 0 0-3.4z',
  info: 'M12 3.5a8.5 8.5 0 1 0 0 17a8.5 8.5 0 0 0 0-17zM12 11v6M12 7.5h.01',
  clip: 'M20 11.5l-8 8a5 5 0 0 1-7-7l8.5-8.5a3.5 3.5 0 0 1 5 5L10 17.5a2 2 0 0 1-3-3l7.5-7.5',
  pin: 'M9 4h6l-1 6 3.5 3.5h-11L10 10zM12 13.5V21',
  inbox: 'M3.5 13.5L6.5 5h11l3 8.5V19a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1zM3.5 13.5H8l1.5 3h5l1.5-3h4.5',
  send: 'M21 3L10.5 13.5M21 3l-6.5 18-4-7.5L3 9.5z',
  download: 'M12 4v11M7.5 11l4.5 4.5 4.5-4.5M4.5 19.5h15',
  house: 'M4 11l8-7 8 7M6 9.5V20h12V9.5',
  cloud: 'M7 18.5a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 11a3.8 3.8 0 0 1-.5 7.5z',
  reload: 'M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5v4h-4',
  sort: 'M7 4v16M3.5 16.5L7 20l3.5-3.5M17 20V4M13.5 7.5L17 4l3.5 3.5',
  book: 'M5 4.5h11a3 3 0 0 1 3 3V20H8a3 3 0 0 1-3-3zM5 17a3 3 0 0 1 3-3h11',
  mic: 'M12 3.5a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0v-5a3 3 0 0 0-3-3zM6 11.5a6 6 0 0 0 12 0M12 17.5v3',
  hand: 'M8 12V6a1.5 1.5 0 0 1 3 0v5V4.5a1.5 1.5 0 0 1 3 0V11V6a1.5 1.5 0 0 1 3 0v8a6.5 6.5 0 0 1-12.4 2.7L5 13a1.5 1.5 0 0 1 3-1z',
  cursor: 'M6 3.5l12 9.5h-6.5l-3 6.5z',
  eye: 'M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12zM12 9.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 0 0 0-5z',
  bolt: 'M13 3L5 13.5h6L10 21l8-10.5h-6z',
  circle: 'M12 4a8 8 0 1 0 0 16a8 8 0 0 0 0-16z',
  table: 'M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM3 10h18M3 14.5h18M9 5v14M15 5v14',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  bag: 'M5 8h14l-1 12.5H6zM9 8V6.5a3 3 0 0 1 6 0V8',
  control: 'M5 7.5h9M17 7.5h2M5 16.5h2M10 16.5h9M15.5 5.5a2 2 0 1 0 0 4a2 2 0 0 0 0-4zM8.5 14.5a2 2 0 1 0 0 4a2 2 0 0 0 0-4z',
  apple: '!M16.6 12.6c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.9-3.5.9s-1.8-.8-3-.8c-1.5 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.4 2.9 2.3 1.2 0 1.6-.7 3-.7s1.8.7 3 .7c1.3 0 2.1-1.1 2.8-2.3.9-1.3 1.3-2.5 1.3-2.6 0 0-2.5-1-2.5-3.8zM14.3 5.8c.6-.8 1.1-1.9 1-3-1 .1-2.1.6-2.8 1.5-.6.7-1.2 1.8-1 2.9 1.1.1 2.2-.6 2.8-1.4z',
};
TE.addIcons = more => Object.assign(ICONS, more);
TE.icon = (name, size = 16, cls = '') => {
  let d = ICONS[name] || ICONS.doc, fill = false;
  if (d[0] === '!') { fill = true; d = d.slice(1); }
  return `<svg class="ic ${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${fill ? 'currentColor' : 'none'}" stroke="${fill ? 'none' : 'currentColor'}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${d}"/></svg>`;
};

// ------------------------------------------------------------------ widgets (HTML strings)
TE.w = {
  toggle: (on, act, arg = '') => `<span class="toggle${on ? ' on' : ''}" data-act="${act}" data-arg="${esc(arg)}"><i></i></span>`,
  check: (on, act, arg = '') => `<span class="check${on ? ' on' : ''}" data-act="${act}" data-arg="${esc(arg)}">${on ? TE.icon('check', 12) : ''}</span>`,
  slider: (v, act, arg = '', cls = '') => `<span class="slider ${cls}" data-slider="${act}" data-arg="${esc(arg)}" style="--v:${v}"><i class="fill"></i><i class="knob"></i></span>`,
  select: (value, options, act, arg = '') => `<span class="popup" data-select="${act}" data-arg="${esc(arg)}" data-opts="${esc(JSON.stringify(options))}" data-value="${esc(value)}"><span>${esc(value)}</span>${TE.icon('updown', 13)}</span>`,
  seg: (value, options, act) => `<span class="seg">${options.map(o => `<span class="${o === value ? 'on' : ''}" data-act="${act}" data-arg="${esc(o)}">${esc(o)}</span>`).join('')}</span>`,
  input: (value, act, arg = '', o = {}) => `<input class="field ${o.cls || ''}" type="text" spellcheck="false" autocomplete="off" value="${esc(value)}" placeholder="${esc(o.placeholder || '')}" data-input="${act}" data-arg="${esc(arg)}" data-focus="${esc(o.focus || act + ':' + arg)}"${o.enter ? ` data-enter="${o.enter}"` : ''}${o.esc ? ` data-esc="${o.esc}"` : ''}>`,
  search: (value, act, placeholder = 'Search') => `<label class="search">${TE.icon('search', 13)}<input type="text" spellcheck="false" autocomplete="off" value="${esc(value)}" placeholder="${esc(placeholder)}" data-input="${act}" data-focus="search:${act}"></label>`,
};

// ------------------------------------------------------------------ windows
const front = () => { const w = TE.state.windows.filter(w => !w.min); return w.length ? w[w.length - 1].app : null; };
const winEl = app => $(`.win[data-app="${app}"]`);
TE.front = front;
TE.focus = (key, all = false) => { TE.pendingFocus = {key, all}; };

function restack() {
  const f = front();
  TE.state.windows.forEach((w, i) => {
    const el = winEl(w.app); if (!el) return;
    el.style.zIndex = 10 + i; el.style.display = w.min ? 'none' : '';
    el.classList.toggle('front', w.app === f);
    el.style.left = w.x + 'px'; el.style.top = w.y + 'px'; el.style.width = w.w + 'px'; el.style.height = w.h + 'px';
  });
  renderMenubar(); renderDock();
}
function buildWindow(w) {
  const def = TE.apps[w.app], el = document.createElement('div');
  el.className = 'win chrome-' + (def.chrome || 'toolbar'); el.dataset.app = w.app;
  el.innerHTML = '<div class="traffic"><i class="tl close" data-tl="close" data-role="button" data-name="Close" data-fn="close this window" data-icon="1"></i><i class="tl min" data-tl="min" data-role="button" data-name="Minimise" data-fn="minimise this window|send this window to the Dock" data-icon="1"></i><i class="tl zoom" data-tl="zoom" data-role="button" data-name="Zoom" data-fn="make this window fill the screen|zoom this window" data-icon="1"></i></div><div class="win-body"></div>';
  $('#windows').appendChild(el);
  TE.refresh(w.app);
}
TE.open = app => {
  const def = TE.apps[app]; if (!def) return;
  let w = TE.state.windows.find(w => w.app === app);
  if (!w) {
    const [ww, hh] = def.size || [880, 560], n = TE.state.windows.length;
    w = {app, x: Math.round((innerWidth - ww) / 2) + 24 * (n % 3), y: clamp(Math.round((innerHeight - 28 - 76 - hh) / 2) + 28 + 18 * (n % 3), 34, 60), w: ww, h: hh};
    TE.state.windows.push(w); buildWindow(w);
  }
  w.min = false; raise(app);
};
function raise(app) {
  const i = TE.state.windows.findIndex(w => w.app === app); if (i < 0) return;
  if (i !== TE.state.windows.length - 1) TE.state.windows.push(TE.state.windows.splice(i, 1)[0]);
  restack();
}
TE.close = app => {
  const i = TE.state.windows.findIndex(w => w.app === app); if (i < 0) return;
  TE.state.windows.splice(i, 1); const el = winEl(app); if (el) el.remove(); restack();
};
TE.refresh = app => {
  const win = winEl(app); if (!win) return;
  const def = TE.apps[app], s = TE.state.apps[app], body = $('.win-body', win);
  const scroll = {}; body.querySelectorAll('[data-scroll]').forEach(el => { scroll[el.dataset.scroll] = [el.scrollTop, el.scrollLeft]; });
  let foc = null; const a = document.activeElement;
  if (a && body.contains(a) && a.dataset.focus) foc = {key: a.dataset.focus, s: a.selectionStart, e: a.selectionEnd};
  try { body.innerHTML = def.render(s); } catch (err) { TE.errors.push(app + ' render: ' + err.message); body.innerHTML = ''; }
  body.querySelectorAll('[data-scroll]').forEach(el => { const p = scroll[el.dataset.scroll]; if (p) { el.scrollTop = p[0]; el.scrollLeft = p[1]; } });
  if (TE.pendingFocus) { foc = TE.pendingFocus; TE.pendingFocus = null; }
  if (foc) {
    const el = [...body.querySelectorAll('[data-focus]')].find(e => e.dataset.focus === foc.key);
    if (el) { el.focus(); try { if (typeof foc.all === 'number') el.setSelectionRange(0, foc.all); else if (foc.all) el.select(); else if (foc.s != null) el.setSelectionRange(foc.s, foc.e); else el.setSelectionRange(el.value.length, el.value.length); } catch (_) {} }
  }
};
function dispatch(app, act, arg, v, el, quiet) {
  const def = TE.apps[app], fn = def && def.on && def.on[act];
  if (!fn) return;
  let r;
  try { if (def.before) def.before(TE.state.apps[app], act); r = fn.call(def, TE.state.apps[app], arg, v, el); } catch (err) { TE.errors.push(`${app}.${act}: ${err.message}`); }
  TE.state.events.push([app, act, arg == null ? '' : String(arg)]);
  if (quiet ? r === true : r !== false) TE.refresh(app);
  renderMenubar();
}
TE.dispatch = dispatch;

// ------------------------------------------------------------------ menu bar and Dock (macsim's own)
const MB = () => (TE.state && TE.state.mb) || 24;
TE.A = (role, name, o = {}) => ` data-role="${role}" data-name="${esc(name)}"` + (o.fn ? ` data-fn="${esc(o.fn)}"` : '') + (o.state ? ` data-state="${o.state}"` : '') +
  (o.noun ? ` data-noun="${o.noun}"` : '') + (o.icon ? ' data-icon="1"' : '') + (o.act ? ` data-act="${o.act}"` + (o.arg !== undefined ? ` data-arg="${esc(o.arg)}"` : '') : '');
TE.syms = new Set();                                    // Apple symbols available as renders (set at boot)
TE.sym = (name, size = 16, cls = '') => TE.syms.has(name)
  ? `<i class="sym ${cls}" style="width:${size}px;height:${size}px;-webkit-mask-image:url(/sym/${name}.regular.${size > 22 ? 96 : 48}.black.png)"></i>`
  : TE.icon(({'chevron.left': 'left', 'chevron.right': 'right', 'chevron.down': 'down', 'chevron.up': 'up', magnifyingglass: 'search', plus: 'plus', minus: 'minus', trash: 'trash', flag: 'flag', folder: 'folder', checkmark: 'check', xmark: 'x', gear: 'gear', wifi: 'wifi', calendar: 'calendar'})[name] || 'circle', size, cls);
function menusOf(app) {
  const def = TE.apps[app], own = def.menus ? def.menus(TE.state.apps[app]) : [];
  return [{label: def.title, bold: true, items: [{label: 'About ' + def.title}, '-', {label: 'Settings…', shortcut: '⌘,'}, '-', {label: 'Services', disabled: true}, '-', {label: 'Hide ' + def.title, shortcut: '⌘H', sys: 'min'}, {label: 'Hide Others', shortcut: '⌥⌘H', disabled: true}, '-', {label: 'Quit ' + def.title, shortcut: '⌘Q', sys: 'close'}]},
    ...own, {label: 'Window', items: [{label: 'Minimise', shortcut: '⌘M', sys: 'min'}, {label: 'Zoom'}, {label: 'Fill', shortcut: '⌃F'}, '-', {label: 'Bring All to Front'}]}, {label: 'Help', items: [{label: def.title + ' Help'}]}];
}
const APPLE_MENU = [{label: 'About This Mac'}, '-', {label: 'System Settings…', sys: 'open:settings'}, {label: 'App Store…'}, '-', {label: 'Recent Items', disabled: true}, '-', {label: 'Force Quit…', shortcut: '⌥⌘⎋'}, '-', {label: 'Sleep'}, {label: 'Restart…'}, {label: 'Shut Down…'}, '-', {label: 'Lock Screen', shortcut: '⌃⌘Q'}, {label: 'Log Out…', shortcut: '⇧⌘Q'}];
function renderMenubar() {
  const app = front(), menus = app ? menusOf(app) : [{label: 'Finder', bold: true, items: [{label: 'About Finder'}]}, {label: 'File', items: [{label: 'New Finder Window', shortcut: '⌘N'}]}, {label: 'Edit', items: [{label: 'Undo', disabled: true}]}, {label: 'View', items: [{label: 'as Icons'}]}, {label: 'Go', items: [{label: 'Back'}]}, {label: 'Window', items: [{label: 'Minimise'}]}, {label: 'Help', items: [{label: 'macOS Help'}]}];
  const left = [`<span class="mb-item apple" data-mb="-1"${TE.A('menu', 'Apple menu', {fn: 'open the Apple menu', icon: 1})}>${TE.icon('apple', 16)}</span>`]
    .concat(menus.map((m, i) => `<span class="mb-item${m.bold ? ' bold' : ''}" data-mb="${i}"${TE.A('menu', m.label, {fn: 'open the ' + m.label + ' menu'})}>${esc(m.label)}</span>`));
  const right = (TE.state.extras || []).map(x => `<span class="mb-st"${x.spot ? ' data-spot="1"' : ''}${TE.A('status item', x.name, {fn: x.fn, icon: 1})}>${x.text ? `<b>${esc(x.text)}</b>` : ''}${TE.sym(x.sym, 16)}</span>`).join('') +
    `<span class="mb-clock"${TE.A('status item', 'Clock', {fn: 'show the date and notifications'})}>${esc((TE.state.status || {}).clock || '')}</span>`;
  $('#menubar').innerHTML = `<div class="mb-left">${left.join('')}</div><div class="mb-right">${right}</div>`;
}
function renderDock() {
  const open = new Set(TE.state.windows.map(w => w.app));
  $('#dock').innerHTML = TE.state.dock.map(d => d === '|' ? '<span class="dock-sep"></span>' :
    `<span class="dock-item" data-dock="${d.app || ''}"${TE.A('Dock icon', d.name, {fn: (d.name === 'Bin' ? 'open the Bin' : 'open ' + d.name + '|switch to ' + d.name), icon: 1})}>` +
    (d.icon ? `<img class="app-icon" src="/app/${d.icon}">` : `<span class="app-icon drawn ${d.cls || ''}"></span>`) + `<i class="run-dot${open.has(d.app) || d.running ? ' on' : ''}"></i></span>`).join('');
}
// Spotlight: a search panel over everything. state.spot = {open, query}; state.spot_items = [{name, kind, app?}]
function renderSpot() {
  let el = $('#spot'); const sp = TE.state.spot;
  if (!sp || !sp.open) { if (el) el.remove(); return; }
  if (!el) { el = document.createElement('div'); el.id = 'spot'; $('#overlays').appendChild(el); }
  const q = (sp.query || '').toLowerCase(), hits = q ? (TE.state.spot_items || []).filter(i => i.name.toLowerCase().includes(q)).slice(0, 6) : [];
  const had = document.activeElement && document.activeElement.id === 'spot-in';
  el.innerHTML = `<div class="spot-bar">${TE.sym('magnifyingglass', 22)}<input id="spot-in" type="text" spellcheck="false" autocomplete="off" placeholder="Spotlight Search" value="${esc(sp.query || '')}"${TE.A('search field', 'Spotlight Search', {fn: 'type what to look for'})}></div>` +
    (hits.length ? `<div class="spot-list">${hits.map((h, i) => `<div class="spot-row${i === 0 ? ' sel' : ''}" data-spot-hit="${esc(h.name)}"${TE.A('search result', h.name, {fn: 'open ' + h.name})}>${h.icon ? `<img src="/app/${h.icon}">` : TE.sym(h.sym || 'doc', 22)}<span>${esc(h.name)}</span><em>${esc(h.kind)}</em></div>`).join('')}</div>` : '');
  const inp = $('#spot-in'); if (had || sp.focus) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); sp.focus = false; }
}
function spotOpen(name) { const it = (TE.state.spot_items || []).find(i => i.name === name); TE.state.spot = {open: false, query: ''}; TE.state.opened = name; TE.state.events.push(['spotlight', 'open', name]); renderSpot(); if (it && it.app) TE.open(it.app); }
TE.spotlight = on => { TE.state.spot = {open: on, query: '', focus: on}; renderSpot(); };
document.addEventListener('click', e => {
  if (e.target.closest('[data-spot]')) { TE.spotlight(!(TE.state.spot && TE.state.spot.open)); e.stopPropagation(); return; }
  const hit = e.target.closest('[data-spot-hit]'); if (hit) { spotOpen(hit.dataset.spotHit); e.stopPropagation(); return; }
  if (TE.state.spot && TE.state.spot.open && !e.target.closest('#spot')) TE.spotlight(false);
}, true);
document.addEventListener('input', e => { if (e.target.id === 'spot-in') { TE.state.spot.query = e.target.value; renderSpot(); e.stopPropagation(); } }, true);
document.addEventListener('keydown', e => {
  const sp = TE.state && TE.state.spot;
  if (e.metaKey && e.key === ' ') { TE.spotlight(!(sp && sp.open)); e.preventDefault(); e.stopPropagation(); return; }
  if (!sp || !sp.open) return;
  if (e.key === 'Escape') { TE.spotlight(false); e.preventDefault(); e.stopPropagation(); }
  else if (e.key === 'Enter') { const first = $('#spot .spot-row'); if (first) spotOpen(first.dataset.spotHit); e.preventDefault(); e.stopPropagation(); }
}, true);

// ------------------------------------------------------------------ menus (menu bar, right click, pop-up buttons)
let menus = [], swallow = false, openMb = null;
function closeMenus(from = 0) { menus.splice(from).forEach(m => m.remove()); if (!menus.length) { openMb = null; document.querySelectorAll('.mb-item.open').forEach(e => e.classList.remove('open')); } }
TE.menu = (items, x, y, pick, level = 0) => {
  closeMenus(level);
  const el = document.createElement('div'); el.className = 'menu';
  el.innerHTML = items.map((it, i) => it === '-' ? '<div class="menu-sep"></div>' :
    `<div class="menu-item${it.disabled ? ' disabled' : ''}" data-mi="${i}" data-role="menu item" data-name="${esc(it.label)}"${it.checked ? ' data-state="checked"' : it.disabled ? ' data-state="disabled"' : ''}><span class="mi-check">${it.checked ? TE.icon('check', 12) : ''}</span><span class="mi-label">${esc(it.label)}</span>` +
    `<span class="mi-short">${it.items ? TE.icon('right', 11) : esc(it.shortcut || '')}</span></div>`).join('');
  $('#overlays').appendChild(el);
  const r = el.getBoundingClientRect();
  el.style.left = Math.round(clamp(x, 4, innerWidth - r.width - 4)) + 'px';
  el.style.top = Math.round(clamp(y, MB() + 2, innerHeight - r.height - 4)) + 'px';
  const sub = row => {
    const it = items[+row.dataset.mi]; if (!it || !it.items || it.disabled) return false;
    const b = row.getBoundingClientRect();
    el.querySelectorAll('.menu-item.open').forEach(e => e.classList.remove('open')); row.classList.add('open');
    TE.menu(it.items, b.right + 2 + 180 > innerWidth ? b.left - 182 : b.right + 2, b.top - 5, pick, level + 1); return true;
  };
  el.addEventListener('mouseover', e => { const row = e.target.closest('.menu-item'); if (!row || row.parentNode !== el) return; if (!sub(row) && menus.length > level + 1) { closeMenus(level + 1); el.querySelectorAll('.menu-item.open').forEach(e => e.classList.remove('open')); } });
  el.addEventListener('click', e => {
    const row = e.target.closest('.menu-item'); e.stopPropagation(); if (!row) return;
    const it = items[+row.dataset.mi]; if (it.disabled) return;
    if (it.items) { sub(row); return; }
    closeMenus(); pick(it);
  });
  menus.push(el);
};
function pickMenu(app) {
  return it => {
    if (it.sys === 'close') TE.close(app);
    else if (it.sys === 'min') { const w = TE.state.windows.find(w => w.app === app); if (w) { w.min = true; restack(); } }
    else if (it.sys && it.sys.startsWith('open:')) TE.open(it.sys.slice(5));
    else if (it.act) dispatch(app, it.act, it.arg, it.value !== undefined ? it.value : it.label);
  };
}
function openMenubar(item) {
  const i = +item.dataset.mb, app = front(), r = item.getBoundingClientRect();
  const items = i < 0 ? APPLE_MENU : app ? menusOf(app)[i].items : [{label: 'About Finder'}];
  TE.menu(items, r.left, MB(), pickMenu(app));
  openMb = i; item.classList.add('open');
}

// ------------------------------------------------------------------ pointer
let drag = null, slide = null, wdrag = null;
function sliderValue(el, x) { const r = el.getBoundingClientRect(); return clamp((x - r.left - 9) / (r.width - 18), 0, 1); }
document.addEventListener('mousedown', e => {
  if (menus.length && !e.target.closest('.menu')) {
    const mb = e.target.closest('.mb-item');
    closeMenus(); swallow = true;
    if (mb && e.button === 0) return;                 // the click handler reopens or closes it
    if (e.button === 0) { e.preventDefault(); return; }
  }
  const win = e.target.closest('.win');
  if (win && win.dataset.app !== front()) raise(win.dataset.app);
  if (e.button !== 0 || !win) return;
  const app = win.dataset.app, field = e.target.closest('input, textarea');
  const sl = e.target.closest('[data-slider]');
  if (sl) { slide = {el: sl, app, act: sl.dataset.slider, arg: sl.dataset.arg}; const v = sliderValue(sl, e.clientX); sl.style.setProperty('--v', v); dispatch(app, slide.act, slide.arg, v, sl, true); e.preventDefault(); return; }
  const dr = e.target.closest('[data-drag]');
  if (dr && !field) { drag = {el: dr, arg: dr.dataset.drag, app, x0: e.clientX, y0: e.clientY, on: false}; e.preventDefault(); if (document.activeElement && document.activeElement.blur && document.activeElement !== document.body) document.activeElement.blur(); return; }
  if (e.target.closest('[data-windrag]') && !field && !e.target.closest('[data-act],[data-dbl],.traffic,.search,.popup,.seg')) {
    const w = TE.state.windows.find(w => w.app === app); wdrag = {w, dx: e.clientX - w.x, dy: e.clientY - w.y}; e.preventDefault();
  }
}, true);
document.addEventListener('mousemove', e => {
  if (slide) { const el = slide.el.isConnected ? slide.el : [...document.querySelectorAll('[data-slider]')].find(x => x.dataset.slider === slide.act && x.dataset.arg === slide.arg); if (!el) return; slide.el = el; const v = sliderValue(el, e.clientX); el.style.setProperty('--v', v); dispatch(slide.app, slide.act, slide.arg, v, el, true); return; }
  if (wdrag) { wdrag.w.x = clamp(e.clientX - wdrag.dx, -wdrag.w.w + 80, innerWidth - 80); wdrag.w.y = clamp(e.clientY - wdrag.dy, MB(), innerHeight - 60); restack(); return; }
  if (drag) {
    if (!drag.on && Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) > 5) {
      drag.on = true; const r = drag.el.getBoundingClientRect(), g = drag.el.cloneNode(true);
      g.classList.add('drag-ghost'); g.style.width = r.width + 'px'; g.style.height = r.height + 'px';
      drag.ox = drag.x0 - r.left; drag.oy = drag.y0 - r.top; drag.ghost = g; $('#overlays').appendChild(g); drag.el.classList.add('dragging');
    }
    if (drag.on) {
      drag.ghost.style.left = (e.clientX - drag.ox) + 'px'; drag.ghost.style.top = (e.clientY - drag.oy) + 'px';
      document.querySelectorAll('.drop-hover').forEach(x => x.classList.remove('drop-hover'));
      const t = document.elementFromPoint(e.clientX, e.clientY), d = t && t.closest('[data-drop]');
      if (d && d !== drag.el) d.classList.add('drop-hover');
    }
    return;
  }
  if (openMb !== null) { const mb = e.target.closest && e.target.closest('.mb-item'); if (mb && +mb.dataset.mb !== openMb) { closeMenus(); openMenubar(mb); } }
}, true);
document.addEventListener('mouseup', e => {
  if (slide) { const s = slide; slide = null; TE.refresh(s.app); swallow = true; setTimeout(() => { swallow = false; }, 0); return; }
  if (wdrag) { wdrag = null; return; }
  if (drag) {
    const d = drag; drag = null;
    if (!d.on) return;
    d.ghost.remove(); document.querySelectorAll('.drop-hover,.dragging').forEach(x => x.classList.remove('drop-hover', 'dragging'));
    const t = document.elementFromPoint(e.clientX, e.clientY), tgt = t && t.closest('[data-drop]'), win = tgt && tgt.closest('.win');
    swallow = true; setTimeout(() => { swallow = false; }, 0);
    if (tgt && win && tgt !== d.el) {
      const app = win.dataset.app, def = TE.apps[app], r = tgt.getBoundingClientRect();
      const info = {pos: e.clientY < r.top + r.height / 2 ? 'before' : 'after', fx: (e.clientX - r.left) / r.width, fy: (e.clientY - r.top) / r.height, from: d.app};
      if (def.drop) { try { def.drop(TE.state.apps[app], d.arg, tgt.dataset.drop, info); } catch (err) { TE.errors.push(app + ' drop: ' + err.message); } TE.state.events.push([app, 'drop', d.arg + ' -> ' + tgt.dataset.drop]); TE.refresh(app); if (d.app !== app) TE.refresh(d.app); }
    }
  }
}, true);
document.addEventListener('click', e => {
  if (swallow) { swallow = false; if (!e.target.closest('.mb-item')) { e.stopPropagation(); return; } }
  const mb = e.target.closest('.mb-item');
  if (mb) { if (openMb === +mb.dataset.mb) closeMenus(); else { closeMenus(); openMenubar(mb); } return; }
  const dk = e.target.closest('.dock-item');
  if (dk) { if (dk.dataset.dock !== 'trash') TE.open(dk.dataset.dock); else if (TE.apps.files) { TE.open('files'); dispatch('files', 'go', 'trash'); } return; }
  const win = e.target.closest('.win'); if (!win) return;
  const app = win.dataset.app, tl = e.target.closest('[data-tl]');
  if (tl) { if (tl.dataset.tl === 'close') TE.close(app); else if (tl.dataset.tl === 'min') { TE.state.windows.find(w => w.app === app).min = true; restack(); } return; }
  const sel = e.target.closest('[data-select]');
  if (sel) {
    const r = sel.getBoundingClientRect(), opts = JSON.parse(sel.dataset.opts);
    TE.menu(opts.map(o => ({label: o, checked: o === sel.dataset.value})), r.left - 14, r.bottom + 3, it => dispatch(app, sel.dataset.select, sel.dataset.arg, it.label, sel));
    e.stopPropagation(); return;
  }
  // The second click of a double click arrives as a click with detail 2. (A native dblclick
  // event is not used: the first click re-renders the window, which replaces the element.)
  const dbl = e.detail === 2 && e.target.closest('[data-dbl]');
  if (dbl && win.contains(dbl)) { dispatch(app, dbl.dataset.dbl, dbl.dataset.arg, e, dbl); return; }
  const el = e.target.closest('[data-act]');
  if (el && win.contains(el)) dispatch(app, el.dataset.act, el.dataset.arg, e, el);
}, true);
document.addEventListener('contextmenu', e => {
  e.preventDefault(); closeMenus();
  const win = e.target.closest('.win'), el = e.target.closest('[data-ctx]');
  if (!win || !el) return;
  const app = win.dataset.app, def = TE.apps[app];
  if (!def.context) return;
  let items; try { items = def.context(TE.state.apps[app], el.dataset.ctx); } catch (err) { TE.errors.push(app + ' context: ' + err.message); }
  TE.refresh(app);
  if (items && items.length) TE.menu(items, e.clientX, e.clientY, it => { if (it.act) dispatch(app, it.act, it.arg !== undefined ? it.arg : el.dataset.ctx, it.value !== undefined ? it.value : it.label); });
}, true);

// ------------------------------------------------------------------ keyboard and text fields
function insert(el, text) { el.setRangeText(text, el.selectionStart, el.selectionEnd, 'end'); el.dispatchEvent(new Event('input', {bubbles: true})); }
function editKey(e, el) {
  const k = e.key.toLowerCase();
  if (k === 'a') el.select();
  else if (k === 'c' || k === 'x') { TE.clip = el.value.slice(el.selectionStart, el.selectionEnd); if (k === 'x') insert(el, ''); }
  else if (k === 'v') insert(el, TE.clip);
  else if (k === 'backspace') { el.setSelectionRange(0, el.selectionEnd); insert(el, ''); }
  else return false;
  return true;
}
const comboOf = e => (e.metaKey ? 'Meta+' : '') + (e.ctrlKey ? 'Control+' : '') + (e.altKey ? 'Alt+' : '') + (e.shiftKey ? 'Shift+' : '') + (e.key.length === 1 ? e.key.toLowerCase() : e.key);
document.addEventListener('keydown', e => {
  if (['Meta', 'Shift', 'Control', 'Alt'].includes(e.key)) return;
  const t = e.target, inField = !!(t.matches && t.matches('input, textarea')), combo = comboOf(e);
  if (menus.length) { if (e.key === 'Escape') closeMenus(); e.preventDefault(); return; }
  const win = inField ? t.closest('.win') : null, fapp = win ? win.dataset.app : front();
  if (inField) {
    if (e.metaKey && !e.shiftKey && editKey(e, t)) { e.preventDefault(); return; }
    if (e.key === 'Enter' && t.dataset.enter && !e.shiftKey) { e.preventDefault(); dispatch(fapp, t.dataset.enter, t.dataset.arg, t.value, t); return; }
    if (e.key === 'Escape' && t.dataset.esc) { e.preventDefault(); dispatch(fapp, t.dataset.esc, t.dataset.arg, t.value, t); return; }
  }
  const app = front();
  if (app) {
    const def = TE.apps[app];
    const k = def.keys && (def.keys[combo] || def.keys[combo.replace('Delete', 'Backspace')]);   // an app's own shortcut wins over the window shortcuts below; forward delete counts as delete
    if (k && (!inField || e.metaKey || e.ctrlKey)) { e.preventDefault(); dispatch(app, k.act || k, k.arg, e); return; }
    if (combo === 'Meta+q' || combo === 'Meta+w') { e.preventDefault(); TE.close(app); return; }
    if (combo === 'Meta+m' || combo === 'Meta+h') { e.preventDefault(); TE.state.windows.find(w => w.app === app).min = true; restack(); return; }
    if (!inField && def.key && !e.metaKey) { let h = false; try { h = def.key(TE.state.apps[app], e); } catch (err) { TE.errors.push(app + ' key: ' + err.message); } if (h) { e.preventDefault(); TE.state.events.push([app, 'key', combo]); TE.refresh(app); return; } }
  }
  if (e.metaKey) e.preventDefault();                  // on Linux a Cmd combination would otherwise type its letter
}, true);
document.addEventListener('input', e => {
  const t = e.target, win = t.closest && t.closest('.win');
  if (win && t.dataset.input) dispatch(win.dataset.app, t.dataset.input, t.dataset.arg, t.value, t, true);
}, true);
window.addEventListener('error', e => TE.errors.push('window: ' + e.message));

// ------------------------------------------------------------------ boot
TE.register = (name, def) => { TE.apps[name] = def; };
TE.boot = state => {
  TE.state = state; state.events = state.events || []; state.windows = state.windows.filter(w => TE.apps[w.app]); TE.errors = []; menus = []; drag = slide = wdrag = null; swallow = false; openMb = null;
  document.body.className = 'wp' + (state.wallpaper || 0) + (state.dark ? ' dark' : ' light');
  document.documentElement.style.setProperty('--mb', (state.mb || 24) + 'px'); document.documentElement.style.setProperty('--accent', state.accent || '#0a7aff');
  TE.syms = new Set(state.syms || []); delete state.syms;
  $('#windows').innerHTML = ''; $('#overlays').innerHTML = '';
  state.windows.forEach(buildWindow); restack(); renderSpot();
  return document.fonts.ready.then(() => true);
};
TE.snapshot = () => JSON.parse(JSON.stringify(TE.state));
})();
