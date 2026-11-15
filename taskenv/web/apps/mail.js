// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Mail. State: {boxes: [{id, name, icon}], messages: [{id, box, from, email, to, subject, body, date, ts, unread, flagged}],
//               me: {name, email}, next, ui: {box, sel, search, compose: null | {to, subject, body, re}}}
(() => {
const {esc, icon, w} = TE;
const msg = (s, id) => s.messages.find(m => m.id === id);
const target = (s, id) => msg(s, typeof id === 'string' && id ? id : s.ui.sel);
const listing = s => {
  const u = s.ui, q = u.search.trim().toLowerCase();
  return s.messages.filter(m => (u.box === 'flagged' ? m.flagged && m.box !== 'trash' : m.box === u.box) &&
    (!q || (m.from + ' ' + m.subject + ' ' + m.body).toLowerCase().includes(q))).sort((a, b) => b.ts - a.ts);
};
const initials = n => n.split(' ').map(x => x[0]).slice(0, 2).join('');
const HUES = ['#5e8ef7', '#f2994a', '#35b37e', '#bb6bd9', '#eb5757', '#2d9cdb', '#8a8f98', '#d4a017'];
const hue = n => HUES[[...n].reduce((a, c) => a + c.charCodeAt(0), 0) % HUES.length];
const moveTo = (s, m, box) => { if (!m) return; if (box === 'flagged') { m.flagged = true; return; } m.box = box; if (s.ui.sel === m.id) s.ui.sel = null; };

TE.register('mail', {
  title: 'Mail', size: [1040, 640],
  dock: {bg: 'linear-gradient(#5cc4ff, #1a73f0)', glyph: '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"><rect x="3" y="5.5" width="18" height="13" rx="2.2" fill="#fff" stroke="none"/><path d="M4 7.5l8 6 8-6" stroke="#2a86f3"/></svg>'},
  render(s) {
    const u = s.ui, rows = listing(s), cur = msg(s, u.sel), box = u.box === 'flagged' ? {name: 'Flagged'} : s.boxes.find(b => b.id === u.box);
    const count = id => id === 'inbox' ? s.messages.filter(m => m.box === 'inbox' && m.unread).length : id === 'flagged' ? s.messages.filter(m => m.flagged && m.box !== 'trash').length : id === 'drafts' ? s.messages.filter(m => m.box === 'drafts').length : 0;
    const sbItem = (id, name, ic) => `<div class="sb-item${u.box === id ? ' sel' : ''}" data-act="box" data-arg="${id}" data-drop="${id}">${icon(ic, 16)}<span>${esc(name)}</span>${count(id) ? `<span class="count">${count(id)}</span>` : ''}</div>`;
    const fav = ['inbox', 'drafts', 'sent'], side = `<div class="sidebar" data-windrag><div class="sb-head">Favourites</div>` +
      sbItem('inbox', 'Inbox', 'inbox') + sbItem('flagged', 'Flagged', 'flag') + s.boxes.filter(b => fav.includes(b.id) && b.id !== 'inbox').map(b => sbItem(b.id, b.name, b.icon)).join('') +
      `<div class="sb-head">Mailboxes</div>` + s.boxes.filter(b => !fav.includes(b.id)).map(b => sbItem(b.id, b.name, b.icon)).join('') + `</div>`;
    const dim = cur ? '' : ' off';
    const bar = `<div class="toolbar" data-windrag><span class="tb-title">${esc(box.name)}<span class="tb-sub">${rows.length} message${rows.length === 1 ? '' : 's'}</span></span><span class="spacer"></span>` +
      `<span class="tb-btn" data-act="compose">${icon('compose', 18)}</span><span class="m-sep"></span>` +
      `<span class="tb-btn${dim}" data-act="archive">${icon('archive', 18)}</span><span class="tb-btn${dim}" data-act="trash">${icon('trash', 18)}</span><span class="m-sep"></span>` +
      `<span class="tb-btn${dim}" data-act="reply">${icon('reply', 18)}</span><span class="tb-btn${dim}" data-act="forward">${icon('forward', 18)}</span><span class="m-sep"></span>` +
      `<span class="tb-btn${dim}${cur && cur.flagged ? ' m-flagged' : ''}" data-act="flag">${icon(cur && cur.flagged ? 'flagfill' : 'flag', 18)}</span><span class="spacer"></span>${w.search(u.search, 'search')}</div>`;
    const list = `<div class="m-list scroll" data-scroll="mail-list-${u.box}">` + (rows.length ? rows.map(m =>
      `<div class="m-row${u.sel === m.id ? ' sel' : ''}" data-act="select" data-arg="${m.id}" data-ctx="${m.id}" data-drag="${m.id}"><span class="m-dot${m.unread ? ' on' : ''}"></span><div class="m-rb">` +
      `<div class="m-r1"><b>${esc(u.box === 'sent' || u.box === 'drafts' ? 'To: ' + m.to : m.from)}</b><span>${esc(m.date)}</span></div>` +
      `<div class="m-r2"><span>${esc(m.subject)}</span>${m.flagged ? `<i class="m-flag">${icon('flagfill', 12)}</i>` : ''}</div><div class="m-r3">${esc(m.body)}</div></div></div>`).join('') : '<div class="m-empty">No Messages</div>') + `</div>`;
    const read = cur ? `<div class="m-read scroll" data-scroll="mail-read"><div class="m-head"><span class="m-avatar" style="background:${hue(cur.from)}">${esc(initials(cur.from))}</span>` +
      `<div class="m-hb"><div class="m-r1"><b>${esc(cur.from)}</b><span>${esc(cur.date)}</span></div><div class="m-subj">${esc(cur.subject)}</div><div class="muted">To: ${esc(cur.to)}</div></div></div>` +
      `<div class="m-body">${esc(cur.body).split('\n').map(p => `<p>${p || '&nbsp;'}</p>`).join('')}</div></div>` : `<div class="m-read m-none">No Message Selected</div>`;
    const c = u.compose, comp = c ? `<div class="m-compose"><div class="m-cbar"><span class="tb-btn" data-act="discard">${icon('x', 15)}</span><b>${esc(c.subject || 'New Message')}</b><span class="spacer"></span><span class="btn primary" data-act="send">${icon('send', 14)}Send</span></div>` +
      `<label class="m-cf"><span>To:</span><input type="text" spellcheck="false" autocomplete="off" value="${esc(c.to)}" data-input="c_to" data-focus="to"></label>` +
      `<label class="m-cf"><span>Subject:</span><input type="text" spellcheck="false" autocomplete="off" value="${esc(c.subject)}" data-input="c_subject" data-focus="subject"></label>` +
      `<label class="m-cf faint"><span>From:</span><em>${esc(s.me.name)} — ${esc(s.me.email)}</em></label>` +
      `<textarea spellcheck="false" data-input="c_body" data-focus="body" placeholder="">${esc(c.body)}</textarea></div>` : '';
    return `<div class="mail" style="display:flex;flex:1;min-width:0">${side}<div class="main">${bar}<div class="m-split">${list}${read}</div></div>${comp}</div>`;
  },
  on: {
    box(s, id) { s.ui.box = id; s.ui.sel = null; },
    select(s, id) { s.ui.sel = id; const m = msg(s, id); if (m) m.unread = false; },
    archive(s, id) { moveTo(s, target(s, id), 'archive'); },
    trash(s, id) { moveTo(s, target(s, id), 'trash'); },
    junk(s, id) { moveTo(s, target(s, id), 'junk'); },
    moveto(s, box) { moveTo(s, msg(s, s.ui.sel), box); },
    flag(s, id) { const m = target(s, id); if (m) m.flagged = !m.flagged; },
    unread(s, id) { const m = target(s, id); if (m) m.unread = !m.unread; },
    compose(s) { s.ui.compose = {to: '', subject: '', body: '', re: null}; TE.focus('to'); },
    reply(s, id) { const m = target(s, id); if (!m) return; s.ui.compose = {to: m.email, subject: /^re:/i.test(m.subject) ? m.subject : 'Re: ' + m.subject, body: '', re: m.id}; TE.focus('body'); },
    forward(s, id) { const m = target(s, id); if (!m) return; s.ui.compose = {to: '', subject: 'Fwd: ' + m.subject, body: `\n\n---------- Forwarded message ----------\nFrom: ${m.from} <${m.email}>\nSubject: ${m.subject}\n\n${m.body}`, re: m.id}; TE.focus('to'); },
    c_to(s, _, t) { s.ui.compose.to = t; },
    c_subject(s, _, t) { s.ui.compose.subject = t; },
    c_body(s, _, t) { s.ui.compose.body = t; },
    send(s) {
      const c = s.ui.compose; if (!c || !c.to.trim()) return;
      s.messages.push({id: 's' + s.next++, box: 'sent', from: s.me.name, email: s.me.email, to: c.to.trim(), subject: c.subject.trim(), body: c.body, date: 'Just now', ts: 100000 + s.next, unread: false, flagged: false});
      s.ui.compose = null;
    },
    discard(s) { s.ui.compose = null; },
    search(s, _, t) { s.ui.search = t; return true; },
  },
  drop(s, drag, drop) { moveTo(s, msg(s, drag), drop); },
  context(s, id) {
    const m = msg(s, id); if (!m) return [];
    s.ui.sel = id;
    return [{label: 'Reply', act: 'reply'}, {label: 'Forward', act: 'forward'}, '-', {label: m.unread ? 'Mark as Read' : 'Mark as Unread', act: 'unread'}, {label: m.flagged ? 'Remove Flag' : 'Flag', act: 'flag'}, '-',
      {label: 'Archive', act: 'archive'}, {label: 'Move to', items: s.boxes.filter(b => b.id !== m.box && b.id !== 'drafts' && b.id !== 'sent').map(b => ({label: b.name, act: 'moveto', arg: b.id}))}, {label: 'Delete', act: 'trash'}];
  },
  menus(s) {
    const none = !s.ui.sel, m = msg(s, s.ui.sel);
    return [
      {label: 'File', items: [{label: 'New Message', shortcut: '⌘N', act: 'compose'}, '-', {label: 'Print…', shortcut: '⌘P', disabled: true}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true}]},
      {label: 'Mailbox', items: [{label: 'Go to Inbox', act: 'box', arg: 'inbox'}, {label: 'Go to Flagged', act: 'box', arg: 'flagged'}, ...s.boxes.filter(b => b.id !== 'inbox').map(b => ({label: 'Go to ' + b.name, act: 'box', arg: b.id}))]},
      {label: 'Message', items: [{label: 'Reply', shortcut: '⌘R', act: 'reply', disabled: none}, {label: 'Forward', shortcut: '⇧⌘F', act: 'forward', disabled: none}, {label: 'Send', shortcut: '⇧⌘D', act: 'send', disabled: !s.ui.compose}, '-',
        {label: m && m.unread ? 'Mark as Read' : 'Mark as Unread', shortcut: '⇧⌘U', act: 'unread', disabled: none}, {label: m && m.flagged ? 'Remove Flag' : 'Flag', shortcut: '⇧⌘L', act: 'flag', disabled: none}, '-',
        {label: 'Archive', shortcut: '⌃⌘A', act: 'archive', disabled: none}, {label: 'Move to Junk', shortcut: '⇧⌘J', act: 'junk', disabled: none}, {label: 'Delete', shortcut: '⌫', act: 'trash', disabled: none}]},
    ];
  },
  keys: {'Backspace': 'trash', 'Delete': 'trash', 'Meta+n': 'compose', 'Meta+r': 'reply', 'Meta+Shift+f': 'forward', 'Meta+Shift+l': 'flag', 'Meta+Shift+u': 'unread', 'Meta+Shift+d': 'send', 'Meta+Shift+j': 'junk', 'Meta+Control+a': 'archive'},
});
})();
