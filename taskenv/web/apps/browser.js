// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Browser: a web browser in the style of Safari, with a small invented web that is drawn from the state (no network).
// State: {tabs: [{id, url, back: [], fwd: []}], active, bookmarks: [{id, title, url}],
//         forms: {booking: {name, email, service, date, slot, reminder, submitted}, newsletter: {email, subscribed}},
//         saved: [job ids], site: {town, clinic, news, company, extras}, next, ui: {address, err}}
// forms.booking.submitted is false, or a copy of the fields at the moment the form was sent.
// ui.address is the text being typed in the address field, or null when the field shows the page's address.
(() => {
const {esc, icon, w} = TE;
TE.addIcons({bw_shield: 'M12 3l7.5 3v5.5c0 4.6-3.2 8-7.5 9.5-4.3-1.5-7.5-4.9-7.5-9.5V6z'});
const START = 'favorites://';
const EMAIL = /^\S+@\S+\.\S+$/;
const hash = t => { let h = 7; for (const c of String(t)) h = (h * 31 + c.charCodeAt(0)) % 100003; return h; };
// An address as typed -> the form the tabs store: "https://host/path", lower case, no "www." and no final slash.
const canon = t => {
  let u = String(t == null ? '' : t).trim().toLowerCase();
  if (!u || u === START) return START;
  u = u.replace(/^[a-z]+:\/*/, '').replace(/^www\./, '').replace(/[\/\s]+$/, '');
  return u ? 'https://' + u : START;
};
const tabOf = s => s.tabs.find(t => t.id === s.active) || s.tabs[0];
const hostOf = url => (url === START ? '' : url.replace(/^https:\/\//, '').split('/')[0]);
const hue = url => hash(hostOf(url)) % 360;
const short = name => String(name).replace(/^The /, '');
const pages = s => {
  const S = s.site, m = {[START]: {kind: 'start', title: 'Start Page'}};
  m[S.clinic.home] = {kind: 'clinic', title: S.clinic.name};
  m[S.clinic.book] = {kind: 'book', title: `Book an appointment | ${S.clinic.name}`};
  m[S.news.home] = {kind: 'news', title: S.news.name};
  m[S.news.article.url] = {kind: 'article', title: `${S.news.article.title} | ${S.news.name}`};
  m[S.company.home] = {kind: 'company', title: S.company.name};
  m[S.company.careers] = {kind: 'careers', title: `Careers | ${S.company.name}`};
  S.company.jobs.forEach(j => { m[j.url] = {kind: 'job', job: j, title: `${j.title} | ${S.company.name}`}; });
  S.extras.forEach(x => { m[x.url] = {kind: 'extra', x, title: x.name}; });
  return m;
};
const pageAt = (s, url) => pages(s)[url] || {kind: 'lost', title: 'Failed to open page'};
const go = (s, url) => { const t = tabOf(s); url = canon(url); if (url !== t.url) { t.back.push(t.url); t.fwd = []; t.url = url; } s.ui.address = null; };

// ------------------------------------------------------------------ pieces of the pages
const link = (url, html, cls = '') => `<a class="${cls}" data-act="link" data-arg="${esc(url)}">${html}</a>`;
const mark = (url, name, kind, cls = '') => (url === START ? `<i class="bw-fav star ${cls}">${icon('starfill', 9)}</i>` : kind === 'lost' ? `<i class="bw-fav lost ${cls}">${icon('globe', 10)}</i>`
  : `<i class="bw-fav ${cls}" style="--h:${hue(url)}">${esc(hostOf(url).charAt(0).toUpperCase())}</i>`);
const frame = (url, cls, inner) => `<div class="bw-site ${cls}" style="--h:${hue(url)}">${inner}</div>`;
const top = (name, home, links, cur) => `<div class="bw-top">${link(home, `<i>${esc(short(name).charAt(0))}</i>${esc(name)}`, 'bw-logo')}<span class="bw-nav">${links.map(([l, u]) => link(u, esc(l), u === cur ? 'on' : '')).join('')}</span></div>`;
const cards = list => `<div class="bw-cards">${list.map(([head, ...lines]) => `<div><b>${esc(head)}</b>${lines.map(t => `<span>${esc(t)}</span>`).join('')}</div>`).join('')}</div>`;
const scene = h => `<svg viewBox="0 0 680 300" preserveAspectRatio="xMidYMid slice" width="100%" height="100%"><defs><linearGradient id="bw-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a9d3f2"/><stop offset="1" stop-color="#fdebd0"/></linearGradient></defs>` +
  `<rect width="680" height="300" fill="url(#bw-sky)"/><circle cx="528" cy="88" r="36" fill="#fff6d6"/>` +
  `<path d="M0 205Q110 150 250 196T500 186T680 166V300H0z" fill="hsl(${h} 30% 66%)"/>` +
  `<g fill="hsl(${h} 30% 38%)"><rect x="92" y="150" width="34" height="70"/><rect x="132" y="128" width="26" height="92"/><rect x="164" y="162" width="44" height="58"/><path d="M214 220v-66l22-20 22 20v66z"/><rect x="266" y="170" width="52" height="50"/><rect x="330" y="140" width="20" height="80"/></g>` +
  `<g fill="#fff0c2"><rect x="100" y="160" width="7" height="9"/><rect x="113" y="160" width="7" height="9"/><rect x="100" y="178" width="7" height="9"/><rect x="140" y="140" width="9" height="11"/><rect x="140" y="160" width="9" height="11"/><rect x="174" y="172" width="9" height="9"/><rect x="190" y="172" width="9" height="9"/><rect x="231" y="166" width="10" height="12"/><rect x="276" y="180" width="9" height="9"/><rect x="298" y="180" width="9" height="9"/></g>` +
  `<path d="M0 246Q160 200 330 240T680 220V300H0z" fill="hsl(${h} 36% 30%)"/></svg>`;
const mast = (s, n) => `<div class="bw-mast">${link(n.home, esc(n.name), 'bw-paper')}<div class="bw-day">${esc(n.date)} · Independent news for ${esc(s.site.town)}</div></div>`;
const foot = name => `<div class="bw-foot">© 2026 ${esc(name)}. All rights reserved.</div>`;
const errOf = (s, form) => (s.ui.err && s.ui.err.form === form ? `<span class="bw-err">${esc(s.ui.err.text)}</span>` : '');

const PAGE = {
  start(s) {
    return `<div class="bw-start"><h2>Favourites</h2><div class="bw-sgrid">` +
      s.bookmarks.map(b => `<div class="bw-sfav" data-act="bookmark" data-arg="${b.id}">${mark(b.url, b.title, '', 'big')}<span>${esc(b.title)}</span></div>`).join('') +
      `</div><h2>Privacy Report</h2><div class="bw-scard">${icon('bw_shield', 26)}<span>In the last seven days, no trackers were allowed to profile you. Your address is hidden from known trackers.</span></div></div>`;
  },
  clinic(s, pg, url) {
    const c = s.site.clinic;
    return frame(url, '', top(c.name, c.home, [['Home', c.home], ['Book an appointment', c.book]], url) +
      `<div class="bw-hero"><h1>${esc(c.tagline)}</h1><p>${esc(c.name)} has looked after people in ${esc(s.site.town)} since ${esc(c.since)}. New patients are welcome, and most weeks we can see you within a few days.</p>${link(c.book, 'Book an appointment', 'bw-cta')}</div>` +
      cards([['Opening hours', c.hours, 'Saturday, 09:00 to 13:00'], ['Find us', c.street, s.site.town], ['Our team', ...c.team]]));
  },
  book(s, pg, url) {
    const c = s.site.clinic, b = s.forms.booking, d = b.submitted;
    const body = d ? `<div class="bw-done"><span class="bw-tick">${icon('check', 22)}</span><h2>Appointment booked</h2><p>Thank you, ${esc(d.name)}. We have sent a confirmation to ${esc(d.email)}.</p>` +
        `<div class="bw-sum"><div><span>Service</span><b>${esc(d.service)}</b></div><div><span>Date</span><b>${esc(d.date)}</b></div><div><span>Time</span><b>${esc(d.slot)}</b></div><div><span>Reminder</span><b>${d.reminder ? 'The day before' : 'None'}</b></div></div>` +
        `<a data-act="book_again">Book another appointment</a></div>`
      : `<div class="bw-form"><div class="bw-two"><label class="bw-f"><span class="bw-l">Full name</span>${w.input(b.name, 'field', 'name', {placeholder: 'Your name', enter: 'book'})}</label>` +
        `<label class="bw-f"><span class="bw-l">Email</span>${w.input(b.email, 'field', 'email', {placeholder: 'name@example.com', enter: 'book'})}</label></div>` +
        `<div class="bw-two"><div class="bw-f"><span class="bw-l">Service</span>${w.select(b.service || 'Choose a service', c.services, 'service')}</div><div class="bw-f"><span class="bw-l">Date</span><div class="bw-dates">` +
        c.dates.map(x => { const [wd, ...rest] = x.split(' '); return `<span class="bw-date${x === b.date ? ' on' : ''}" data-act="date" data-arg="${esc(x)}">${esc(wd)}<b>${esc(rest.join(' '))}</b></span>`; }).join('') + `</div></div></div>` +
        `<div class="bw-f"><span class="bw-l">Time</span><div class="bw-slots">` +
        c.slots.map(x => `<span class="bw-slot${x.taken ? ' taken' : x.t === b.slot ? ' on' : ''}"${x.taken ? '' : ` data-act="slot" data-arg="${esc(x.t)}"`}>${esc(x.t)}</span>`).join('') + `</div></div>` +
        `<span class="bw-rem" data-act="reminder">${w.check(b.reminder, 'reminder')}<span>Send me a reminder the day before</span></span>` +
        `<div class="bw-submit"><span class="bw-go" data-act="book">Book appointment</span>${errOf(s, 'book')}</div></div>`;
    return frame(url, '', top(c.name, c.home, [['Home', c.home], ['Book an appointment', c.book]], url) +
      `<div class="bw-body"><h1>Book an appointment</h1><p class="bw-lead">Choose a service and a time that suits you. We will confirm by email.</p>${body}</div>`);
  },
  news(s, pg, url) {
    const n = s.site.news, a = n.article;
    return frame(url, 'bw-news', mast(s, n) + `<div class="bw-front">${link(a.url, `<span class="bw-pic">${scene(hue(url))}</span>`, 'bw-leadpic')}<div class="bw-lead1"><div class="bw-kick">${esc(a.section)}</div>` +
      `${link(a.url, esc(a.title), 'bw-h')}<p>${esc(a.stand)}</p><div class="bw-meta">By ${esc(a.author)} · ${esc(a.read)}</div></div></div>` +
      `<div class="bw-briefs"><h3>In brief</h3>${n.briefs.map(([k, t]) => `<div><b>${esc(k)}</b><span>${esc(t)}</span></div>`).join('')}</div>` + foot(n.name));
  },
  article(s, pg, url) {
    const n = s.site.news, a = n.article, nl = s.forms.newsletter;
    const initials = a.author.split(' ').map(x => x.charAt(0)).join('').slice(0, 2);
    const box = nl.subscribed ? `<div class="bw-sub done"><span class="bw-tick">${icon('check', 18)}</span><div><b>You are subscribed</b><span>The morning briefing will be sent to ${esc(nl.email)}.</span></div></div>`
      : `<div class="bw-sub"><b>The ${esc(short(n.name))} morning briefing</b><span>The day's local stories in one short email, every weekday at seven. Free, and easy to stop.</span>` +
        `<div class="bw-subrow">${w.input(nl.email, 'nl_email', '', {placeholder: 'Email address', enter: 'subscribe', focus: 'newsletter'})}<span class="bw-subgo" data-act="subscribe">Subscribe</span></div>${errOf(s, 'nl')}</div>`;
    return frame(url, 'bw-news', mast(s, n) + `<div class="bw-art"><div class="bw-kick">${esc(a.section)}</div><h1>${esc(a.title)}</h1><p class="bw-stand">${esc(a.stand)}</p>` +
      `<div class="bw-by"><i>${esc(initials)}</i><span><b>${esc(a.author)}</b>${esc(a.role)} · ${esc(n.date)} · ${esc(a.read)}</span></div><div class="bw-pic">${scene(hue(url))}</div><div class="bw-cap">${esc(a.caption)}</div>` +
      a.paras.map((p, i) => `<p class="bw-p">${esc(p)}</p>` + (i === 3 ? `<div class="bw-quote">${esc(a.quote)}</div>` : '')).join('') + box + `</div>` + foot(n.name));
  },
  company(s, pg, url) {
    const c = s.site.company;
    return frame(url, '', top(c.name, c.home, [['Home', c.home], ['Careers', c.careers]], url) +
      `<div class="bw-hero"><h1>${esc(c.tagline)}</h1><p>${esc(c.about)}</p>${link(c.careers, `See our ${c.jobs.length} open roles`, 'bw-cta')}</div>` +
      cards([['Team', `${c.people} people`], ['Based in', s.site.town], ['Founded', c.since]]));
  },
  careers(s, pg, url) {
    const c = s.site.company;
    return frame(url, '', top(c.name, c.home, [['Home', c.home], ['Careers', c.careers]], url) +
      `<div class="bw-body"><h1>Careers at ${esc(c.name)}</h1><p class="bw-lead">We are ${c.people} people, most of us in ${esc(s.site.town)}. There are ${c.jobs.length} open roles at the moment.</p>` +
      `<div class="bw-jobs"><div class="bw-jhead"><span>Role</span><span>Team</span><span>Location</span><span>Type</span><span></span></div>` +
      c.jobs.map(j => `<div class="bw-job" data-act="link" data-arg="${esc(j.url)}"><b>${esc(j.title)}${s.saved.includes(j.id) ? `<em>${icon('starfill', 10)}Saved</em>` : ''}</b><span>${esc(j.team)}</span><span>${esc(j.place)}</span><span>${esc(j.type)}</span>${icon('right', 13)}</div>`).join('') +
      `</div></div>`);
  },
  job(s, pg, url) {
    const c = s.site.company, j = pg.job, on = s.saved.includes(j.id);
    return frame(url, '', top(c.name, c.home, [['Home', c.home], ['Careers', c.careers]], c.careers) +
      `<div class="bw-body">${link(c.careers, `${icon('left', 12)}All open roles`, 'bw-back')}<div class="bw-jtop"><div><h1>${esc(j.title)}</h1><div class="bw-chips"><span>${esc(j.team)}</span><span>${esc(j.place)}</span><span>${esc(j.type)}</span><span>${esc(j.pay)}</span></div></div>` +
      `<span class="bw-save${on ? ' on' : ''}" data-act="save_job" data-arg="${j.id}">${icon(on ? 'starfill' : 'star', 15)}${on ? 'Saved' : 'Save job'}</span></div>` +
      `<h3>About the role</h3><p>${esc(j.about)}</p><h3>What you will do</h3><ul>${j.duties.map(t => `<li>${esc(t)}</li>`).join('')}</ul><h3>What we are looking for</h3><ul>${j.wants.map(t => `<li>${esc(t)}</li>`).join('')}</ul></div>`);
  },
  extra(s, pg, url) {
    const x = pg.x;
    return frame(url, '', top(x.name, x.url, [], url) + `<div class="bw-hero"><h1>${esc(x.heading)}</h1><p>${esc(x.blurb)}</p></div>` + cards(x.cards));
  },
  lost(s, pg, url) {
    return `<div class="bw-lost"><b>Can't Find the Server</b><span>Browser can't open the page “${esc(url)}” because it can't find the server “${esc(hostOf(url))}”.</span></div>`;
  },
};

TE.register('browser', {
  title: 'Browser', size: [1080, 680],
  dock: {bg: 'linear-gradient(#ffffff, #e4e6ec)', glyph: '<svg width="42" height="42" viewBox="0 0 40 40"><defs><linearGradient id="bw-dock" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#45c6ff"/><stop offset="1" stop-color="#1668ee"/></linearGradient></defs><circle cx="20" cy="20" r="17" fill="url(#bw-dock)"/><circle cx="20" cy="20" r="14.4" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="2.2" stroke-dasharray="0.7 3.07"/><path d="M29.2 10.8L22.4 22.4 17.6 17.6z" fill="#ff4a3d"/><path d="M10.8 29.2l6.8-11.6 4.8 4.8z" fill="#fff"/></svg>'},
  before(s, act) { if (!['field', 'nl_email', 'address'].includes(act)) s.ui.err = null; },
  render(s) {
    const u = s.ui, t = tabOf(s), pg = pageAt(s, t.url);
    const shown = u.address != null ? u.address : t.url === START ? '' : t.url.replace(/^https:\/\//, '');
    const bar = `<div class="toolbar bw-bar" data-windrag><span class="tb-btn${t.back.length ? '' : ' off'}" data-act="back">${icon('left', 18)}</span><span class="tb-btn${t.fwd.length ? '' : ' off'}" data-act="fwd">${icon('right', 18)}</span>` +
      `<div class="bw-addr">${icon(pg.kind === 'start' || pg.kind === 'lost' ? 'search' : 'lock', 12)}<input type="text" spellcheck="false" autocomplete="off" value="${esc(shown)}" placeholder="Search or enter website name" data-input="address" data-enter="go_address" data-esc="address_cancel" data-focus="address" data-act="focus_address">` +
      `<span class="bw-reload" data-act="reload">${icon('reload', 14)}</span></div></div>`;
    const favs = `<div class="bw-favs" data-windrag>${s.bookmarks.map(b => `<span class="bw-bm" data-act="bookmark" data-arg="${b.id}">${esc(b.title)}</span>`).join('')}</div>`;
    const tabs = `<div class="bw-tabs" data-windrag>` + s.tabs.map(x => {
      const p = pageAt(s, x.url);
      return `<div class="bw-tab${x.id === t.id ? ' on' : ''}" data-act="tab" data-arg="${x.id}"><span class="bw-x" data-act="close_tab" data-arg="${x.id}">${icon('x', 9)}</span><span class="bw-tt">${mark(x.url, p.title, p.kind)}<span>${esc(p.title)}</span></span></div>`;
    }).join('') + `<span class="bw-plus" data-act="newtab">${icon('plus', 14)}</span></div>`;
    return `<div class="browser">${bar}${favs}${tabs}<div class="bw-page scroll" data-scroll="${esc(`page:${t.id}:${t.url}`)}">${PAGE[pg.kind](s, pg, t.url)}</div></div>`;
  },
  on: {
    link(s, url) { go(s, url); },
    bookmark(s, id) { const b = s.bookmarks.find(x => x.id === id); if (b) go(s, b.url); },
    back(s) { const t = tabOf(s); if (t.back.length) { t.fwd.push(t.url); t.url = t.back.pop(); } s.ui.address = null; },
    fwd(s) { const t = tabOf(s); if (t.fwd.length) { t.back.push(t.url); t.url = t.fwd.pop(); } s.ui.address = null; },
    reload(s) { s.ui.address = null; },
    address(s, _, text) { s.ui.address = text; },
    focus_address(s, _, v, el) {
      const t = tabOf(s), full = t.url === START ? '' : t.url;
      if (v && v.type === 'click' && s.ui.address != null && s.ui.address !== full) return false;    // text was typed: a click only places the caret
      s.ui.address = full; TE.focus('address', true);
    },
    go_address(s, _, text, el) { if (el && el.blur) el.blur(); go(s, text); },
    address_cancel(s, _, text, el) { if (el && el.blur) el.blur(); s.ui.address = null; },
    newtab(s) { const id = 't' + s.next++; s.tabs.push({id, url: START, back: [], fwd: []}); s.active = id; s.ui.address = ''; TE.focus('address'); },
    tab(s, id) { if (s.tabs.some(t => t.id === id)) s.active = id; s.ui.address = null; },
    close_tab(s, id) {
      id = id || s.active;
      const i = s.tabs.findIndex(t => t.id === id); if (i < 0) return;
      s.tabs.splice(i, 1);
      if (!s.tabs.length) { s.tabs.push({id: 't' + s.next++, url: START, back: [], fwd: []}); TE.close('browser'); }    // the last tab takes the window with it
      if (s.active === id || !s.tabs.some(t => t.id === s.active)) s.active = s.tabs[Math.min(i, s.tabs.length - 1)].id;
      s.ui.address = null;
    },
    add_bookmark(s) {
      const t = tabOf(s), pg = pageAt(s, t.url); if (pg.kind === 'start' || pg.kind === 'lost') return;
      s.bookmarks.push({id: 'b' + s.next++, title: pg.title, url: t.url});
    },
    field(s, k, text) { if (k === 'name' || k === 'email') s.forms.booking[k] = text; },
    service(s, _, v) { if (s.site.clinic.services.includes(v)) s.forms.booking.service = v; },
    date(s, d) { if (s.site.clinic.dates.includes(d)) s.forms.booking.date = d; },
    slot(s, t) { const x = s.site.clinic.slots.find(x => x.t === t); if (x && !x.taken) s.forms.booking.slot = t; },
    reminder(s) { s.forms.booking.reminder = !s.forms.booking.reminder; },
    book(s) {
      const b = s.forms.booking; if (b.submitted) return;
      const name = b.name.trim(), email = b.email.trim();
      const miss = !name ? 'Please enter your name.' : !EMAIL.test(email) ? 'Please enter a valid email address.' : !b.service ? 'Please choose a service.' : !b.slot ? 'Please choose a time.' : '';
      if (miss) { s.ui.err = {form: 'book', text: miss}; return; }
      b.submitted = {name, email, service: b.service, date: b.date, slot: b.slot, reminder: b.reminder};
    },
    book_again(s) { Object.assign(s.forms.booking, {name: '', email: '', service: '', slot: null, reminder: false, submitted: false}); },
    nl_email(s, _, text) { s.forms.newsletter.email = text; },
    subscribe(s) {
      const n = s.forms.newsletter; if (n.subscribed) return;
      const email = n.email.trim();
      if (!EMAIL.test(email)) { s.ui.err = {form: 'nl', text: 'Please enter a valid email address.'}; return; }
      n.email = email; n.subscribed = true;
    },
    save_job(s, id) { const i = s.saved.indexOf(id); if (i >= 0) s.saved.splice(i, 1); else if (s.site.company.jobs.some(j => j.id === id)) s.saved.push(id); },
  },
  menus(s) {
    const t = tabOf(s), pg = pageAt(s, t.url), real = pg.kind !== 'start' && pg.kind !== 'lost';
    return [
      {label: 'File', items: [{label: 'New Tab', shortcut: '⌘T', act: 'newtab'}, {label: 'Open Location…', shortcut: '⌘L', act: 'focus_address'}, '-', {label: 'Close Tab', shortcut: '⌘W', act: 'close_tab'}]},
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true}]},
      {label: 'View', items: [{label: 'Reload Page', shortcut: '⌘R', act: 'reload'}]},
      {label: 'History', items: [{label: 'Back', shortcut: '⌘[', act: 'back', disabled: !t.back.length}, {label: 'Forward', shortcut: '⌘]', act: 'fwd', disabled: !t.fwd.length}, '-', {label: 'Show Start Page', act: 'link', arg: START}]},
      {label: 'Bookmarks', items: [{label: 'Add Bookmark', shortcut: '⌘D', act: 'add_bookmark', disabled: !real}, '-', ...s.bookmarks.map(b => ({label: b.title, act: 'bookmark', arg: b.id}))]},
    ];
  },
  keys: {'Meta+t': 'newtab', 'Meta+w': 'close_tab', 'Meta+l': 'focus_address', 'Meta+d': 'add_bookmark', 'Meta+[': 'back', 'Meta+]': 'fwd', 'Meta+r': 'reload'},
});
})();
