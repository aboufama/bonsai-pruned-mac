// TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
// Music: a player in the style of macOS Music.
// State: {songs: [{id, title, artist, album, time, loved}], playlists: [{id, name, songs: [song ids]}],
//         player: {current, playing, shuffle, repeat: 'off' | 'all' | 'one', volume: 0..1}, ui: {view, sel, search}}
// ui.view is 'songs' | 'recent' | 'artists' | 'albums' | 'album:<name>' | a playlist id.
(() => {
const {esc, icon, w} = TE;
TE.addIcons({
  mu_plist: 'M3.5 6.5h8.5M3.5 11h6M3.5 15.5h4M17.5 16.5V5l3 1.3M17.5 16.5a2.4 2.4 0 1 1-4.8 0a2.4 2.4 0 0 1 4.8 0z',
  mu_album: 'M5 9h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1zM6.5 6h11M8.5 3.2h7',
});
const LIB = [['recent', 'Recently Added', 'clock'], ['artists', 'Artists', 'mic'], ['albums', 'Albums', 'mu_album'], ['songs', 'Songs', 'note']];
const hash = t => { let h = 7; for (const c of String(t)) h = (h * 31 + c.charCodeAt(0)) % 100003; return h; };
const song = (s, id) => s.songs.find(x => x.id === id);
const playlist = (s, id) => s.playlists.find(p => p.id === id);
const albumOf = v => (typeof v === 'string' && v.startsWith('album:') ? v.slice(6) : null);
const secs = t => { const [m, ss] = String(t).split(':'); return (+m) * 60 + (+ss); };
const clock = n => `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`;
const total = L => { const m = Math.round(L.reduce((a, x) => a + secs(x.time), 0) / 60); return m >= 60 ? `${Math.floor(m / 60)} hr ${m % 60} min` : `${m} min`; };
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const art = (name, cls = '', glyph = 0) => { const h = hash(name) % 360; return `<span class="mu-art ${cls}" style="--h:${h};--h2:${(h + 50) % 360}">${glyph ? icon('note', glyph) : ''}</span>`; };
const albums = s => {
  const m = new Map();
  s.songs.forEach(x => { let a = m.get(x.album); if (!a) m.set(x.album, a = {name: x.album, artist: x.artist, n: 0, added: 0}); a.n++; a.added = Math.max(a.added, +x.id.slice(1) || 0); });
  return [...m.values()];
};
// The songs of the table in view, in the order shown.
const listed = s => {
  const u = s.ui, q = u.search.trim().toLowerCase(), p = playlist(s, u.view), al = albumOf(u.view);
  let L = p ? p.songs.map(id => song(s, id)).filter(Boolean) : al ? s.songs.filter(x => x.album === al) : s.songs.slice();
  if (u.view === 'artists') L.sort((a, b) => cmp(a.artist.toLowerCase(), b.artist.toLowerCase()) || cmp(a.album.toLowerCase(), b.album.toLowerCase()));
  return q ? L.filter(x => `${x.title}\n${x.artist}\n${x.album}`.toLowerCase().includes(q)) : L;
};
// Next and Previous follow the playlist in view when the current song is in it, the library otherwise.
const queue = s => { const p = playlist(s, s.ui.view); return p && p.songs.includes(s.player.current) ? p.songs.filter(id => song(s, id)) : s.songs.map(x => x.id); };
const gcd = (a, b) => (b ? gcd(b, a % b) : a);
const stride = n => { if (n < 3) return 1; let k = Math.floor(n * 0.38) + 1; while (gcd(k, n) !== 1) k++; return k; };   // "shuffle" without randomness
const step = (s, d) => {
  const pl = s.player, q = queue(s), n = q.length; if (!n) return;
  const i = q.indexOf(pl.current); if (i < 0) { pl.current = q[0]; return; }
  let j = i + d * (pl.shuffle ? stride(n) : 1);
  if (pl.shuffle || pl.repeat === 'all') j = ((j % n) + n) % n;
  else if (j >= n) { pl.playing = false; return; }
  else if (j < 0) j = 0;
  pl.current = q[j];
};
const addTo = (s, pid, sid) => { const p = playlist(s, pid); if (p && song(s, sid) && !p.songs.includes(sid)) p.songs.push(sid); };

TE.register('music', {
  title: 'Music', size: [1040, 660],
  dock: {bg: 'linear-gradient(#fb6078, #f9233c)', glyph: '<svg width="32" height="32" viewBox="0 0 24 24" fill="#fff"><circle cx="7.6" cy="17.4" r="2.9"/><circle cx="16.9" cy="15.4" r="2.9"/><path d="M9 17.4V6.4l10.4-2.3v11.3h-1.5V7.9L10.5 9.5v7.9z"/></svg>'},
  render(s) {
    const u = s.ui, pl = s.player, cur = song(s, pl.current), p = playlist(s, u.view), al = albumOf(u.view);
    const side = `<div class="sidebar" data-windrag>${w.search(u.search, 'search')}<div class="sb-head">Library</div>` +
      LIB.map(([id, label, ic]) => `<div class="sb-item${u.view === id || (id === 'albums' && al) ? ' sel' : ''}" data-act="view" data-arg="${id}">${icon(ic, 16)}<span>${label}</span></div>`).join('') +
      `<div class="sb-head">Playlists</div>` +
      s.playlists.map(q => `<div class="sb-item${u.view === q.id ? ' sel' : ''}" data-act="view" data-arg="${q.id}" data-drop="${q.id}">${icon('mu_plist', 16)}<span>${esc(q.name)}</span></div>`).join('') + `</div>`;

    let lcd = `<div class="mu-lcd empty">${icon('note', 22)}</div>`;
    if (cur) {
      const len = secs(cur.time), at = Math.round(len * (hash(cur.id) % 55 + 15) / 100);
      lcd = `<div class="mu-lcd">${art(cur.album, 'lcd', 20)}<div class="mu-lcd-t"><b>${esc(cur.title)}</b><span>${esc(cur.artist)} — ${esc(cur.album)}</span></div>` +
        `<em class="mu-t0">${clock(at)}</em><em class="mu-t1">-${clock(len - at)}</em><i class="mu-prog"><i style="width:${(100 * at / len).toFixed(2)}%"></i></i></div>`;
    }
    const bar = `<div class="toolbar mu-bar" data-windrag><span class="tb-btn${pl.shuffle ? ' on' : ''}" data-act="shuffle">${icon('shuffle', 17)}</span>` +
      `<span class="tb-btn" data-act="prev">${icon('prev', 21)}</span><span class="tb-btn mu-pp" data-act="playpause">${icon(pl.playing ? 'pause' : 'play', 25)}</span><span class="tb-btn" data-act="next">${icon('next', 21)}</span>` +
      `<span class="tb-btn${pl.repeat !== 'off' ? ' on' : ''}" data-act="repeat">${icon('repeat', 17)}${pl.repeat === 'one' ? '<em>1</em>' : ''}</span>${lcd}` +
      `<span class="mu-volbox">${icon('speakerlow', 15)}<span class="mu-volwrap">${w.slider(pl.volume, 'volume', '', 'mu-vol')}<i class="mu-track"></i></span>${icon('speaker', 16)}</span></div>`;

    let head, body;
    if (u.view === 'albums' || u.view === 'recent') {
      const q = u.search.trim().toLowerCase();
      let A = albums(s).sort(u.view === 'recent' ? (a, b) => b.added - a.added : (a, b) => cmp(a.name.toLowerCase(), b.name.toLowerCase()));
      if (u.view === 'recent') A = A.slice(0, 8);
      if (q) A = A.filter(a => `${a.name}\n${a.artist}`.toLowerCase().includes(q));
      head = `<div class="mu-hdr"><div><h1>${u.view === 'recent' ? 'Recently Added' : 'Albums'}</h1><div class="sub">${plural(A.length, 'album')}</div></div></div>`;
      body = `<div class="mu-grid scroll" data-scroll="music-${u.view}">` +
        A.map(a => `<div class="mu-tile" data-act="view" data-arg="album:${esc(a.name)}">${art(a.name, 'big', 54)}<b>${esc(a.name)}</b><span>${esc(a.artist)}</span></div>`).join('') +
        (A.length ? '' : `<div class="mu-none">No albums match your search.</div>`) + `</div>`;
    } else {
      const L = listed(s);
      const row = x => `<div class="mu-row${u.sel === x.id ? ' sel' : ''}" data-act="select" data-arg="${x.id}" data-dbl="play" data-ctx="${x.id}" data-drag="${x.id}">` +
        `<span class="mu-c-ind">${pl.current === x.id ? icon(pl.playing ? 'speaker' : 'speakerlow', 13) : ''}</span><span class="mu-c-title">${esc(x.title)}</span><span class="mu-c-time">${esc(x.time)}</span>` +
        `<span class="mu-c-artist">${esc(x.artist)}</span><span class="mu-c-album">${esc(x.album)}</span><span class="mu-c-love${x.loved ? ' on' : ''}" data-act="love" data-arg="${x.id}">${icon(x.loved ? 'heartfill' : 'heart', 13)}</span></div>`;
      const name = p ? p.name : al || (u.view === 'artists' ? 'Artists' : 'Songs');
      const tile = p ? `<span class="mu-mosaic">${[0, 1, 2, 3].map(i => art((L[i] || L[0] || {album: p.name + i}).album)).join('')}</span>` : al ? art(al, 'hdr', 24) : `<span class="mu-art hdr lib">${icon(u.view === 'artists' ? 'mic' : 'note', 24)}</span>`;
      const sub = (al && L[0] ? esc(L[0].artist) + ' · ' : u.view === 'artists' ? plural(new Set(L.map(x => x.artist)).size, 'artist') + ' · ' : '') + plural(L.length, 'song') + (L.length ? ' · ' + total(L) : '');
      head = `<div class="mu-hdr">${tile}<div><h1>${esc(name)}</h1><div class="sub">${sub}</div></div><span class="mu-playbtn${L.length ? '' : ' off'}" data-act="play_all">${icon('play', 13)}Play</span></div>`;
      let rows = '', group = null;
      L.forEach(x => {
        if (u.view === 'artists' && x.artist !== group) { group = x.artist; rows += `<div class="mu-group">${esc(group)}</div>`; }
        rows += row(x);
      });
      body = `<div class="mu-head"><span class="mu-c-ind"></span><span class="mu-c-title">Title</span><span class="mu-c-time">Time</span><span class="mu-c-artist">Artist</span><span class="mu-c-album">Album</span><span class="mu-c-love">${icon('heart', 12)}</span></div>` +
        `<div class="mu-list scroll" data-scroll="music-list-${esc(u.view)}" data-act="clear">${rows || `<div class="mu-none">${u.search.trim() ? 'No songs match your search.' : 'No songs.'}</div>`}</div>`;
    }
    return `<div class="music">${side}<div class="main">${bar}${head}${body}</div></div>`;
  },
  on: {
    view(s, v) { s.ui.view = v; s.ui.sel = null; s.ui.search = ''; },
    search(s, _, text) { s.ui.search = text; return true; },
    select(s, id) { s.ui.sel = id; },
    clear(s) { s.ui.sel = null; },
    play(s, id) { const x = song(s, id || s.ui.sel); if (!x) return; s.player.current = x.id; s.player.playing = true; },
    play_all(s) { const L = listed(s); if (!L.length) return; s.player.current = L[0].id; s.player.playing = true; },
    playpause(s) {
      const pl = s.player;
      if (song(s, pl.current)) { pl.playing = !pl.playing; return; }
      const L = listed(s), first = L[0] || s.songs[0]; if (first) { pl.current = first.id; pl.playing = true; }
    },
    next(s) { step(s, 1); },
    prev(s) { step(s, -1); },
    shuffle(s) { s.player.shuffle = !s.player.shuffle; },
    set_shuffle(s, v) { s.player.shuffle = v === 'on'; },
    repeat(s) { s.player.repeat = {off: 'all', all: 'one', one: 'off'}[s.player.repeat] || 'off'; },
    set_repeat(s, v) { s.player.repeat = v; },
    volume(s, _, v) { s.player.volume = Math.round(v * 100) / 100; },
    love(s, id) { const x = song(s, id || s.ui.sel); if (x) x.loved = !x.loved; },
    add_to(s, pid) { addTo(s, pid, s.ui.sel); },
    remove_from(s, id) { const p = playlist(s, s.ui.view); id = id || s.ui.sel; if (!p) return; p.songs = p.songs.filter(x => x !== id); if (s.ui.sel === id) s.ui.sel = null; },
  },
  drop(s, drag, drop) { addTo(s, drop, drag); },
  context(s, id) {
    const x = song(s, id); if (!x) return [];
    s.ui.sel = id;
    const inList = !!playlist(s, s.ui.view);
    return [{label: 'Play', act: 'play'}, {label: 'Play Next', disabled: true}, '-', {label: x.loved ? 'Unlove' : 'Love', act: 'love'}, '-',
      {label: 'Add to Playlist', items: s.playlists.map(q => ({label: q.name, act: 'add_to', arg: q.id, checked: q.songs.includes(id)}))},
      ...(inList ? [{label: 'Remove from Playlist', act: 'remove_from'}] : [])];
  },
  menus(s) {
    const pl = s.player, x = song(s, s.ui.sel), inList = !!playlist(s, s.ui.view);
    return [
      {label: 'Edit', items: [{label: 'Undo', shortcut: '⌘Z', disabled: true}, '-', {label: 'Cut', shortcut: '⌘X', disabled: true}, {label: 'Copy', shortcut: '⌘C', disabled: true}, {label: 'Paste', shortcut: '⌘V', disabled: true}]},
      {label: 'Song', items: [{label: x && x.loved ? 'Unlove' : 'Love', act: 'love', disabled: !x}, '-',
        {label: 'Add to Playlist', disabled: !x, items: s.playlists.map(q => ({label: q.name, act: 'add_to', arg: q.id, checked: !!x && q.songs.includes(x.id)}))},
        {label: 'Remove from Playlist', act: 'remove_from', disabled: !x || !inList}]},
      {label: 'View', items: LIB.map(([id, label]) => ({label, act: 'view', arg: id, checked: s.ui.view === id}))},
      {label: 'Controls', items: [{label: pl.playing ? 'Pause' : 'Play', shortcut: 'Space', act: 'playpause'}, {label: 'Next', shortcut: '⌘→', act: 'next'}, {label: 'Previous', shortcut: '⌘←', act: 'prev'}, '-',
        {label: 'Shuffle', items: [{label: 'On', act: 'set_shuffle', arg: 'on', checked: pl.shuffle}, {label: 'Off', act: 'set_shuffle', arg: 'off', checked: !pl.shuffle}]},
        {label: 'Repeat', items: [['off', 'Off'], ['all', 'All'], ['one', 'One']].map(([k, label]) => ({label, act: 'set_repeat', arg: k, checked: pl.repeat === k}))}]},
    ];
  },
  keys: {' ': 'playpause', 'Meta+ArrowRight': 'next', 'Meta+ArrowLeft': 'prev', 'Enter': 'play'},
});
})();
