"""Music and podcast players."""
from ..data import ARTISTS, PLAYLISTS, SONG_A, SONG_B
from ..splits import pool
from ..ui import esc
from ..vocab import C

NAME = "music"
KIND = "either"
VARIANTS = {"spotify": "train", "itunes": "train", "album_grid": "dev", "podcast": "test"}

C("mus.play", "Play|Resume|Start playback", "play|circle-play|square-play", "get {o} sounding|make {o} begin coming out of the speakers|set {o} going", o="the music")
C("mus.pause", "Pause|Hold|Halt playback", "pause|circle-pause|square-pause", "temporarily stop the sound|freeze the current song where it is|make the music wait for a moment")
C("mus.next", "Next track|Skip|Skip forward", "skip-forward|chevron-last|fast-forward", "jump to the song after this one|move on to whatever is queued after the current song|go ahead to the following song")
C("mus.prev", "Previous track|Skip back|Last song", "skip-back|chevron-first|rewind", "return to the song before this one|go to the song that just finished|jump to the preceding song")
C("mus.shuffle", "Shuffle|Random order|Mix up", "shuffle|dices|arrow-right-left", "turn {on} playing the songs in an unpredictable sequence|turn {on} jumbling the sequence of the songs|turn {on} surprise ordering of the songs")
C("mus.repeat", "Repeat|Loop|Play again", "repeat|repeat-1|repeat-2|iteration-cw|infinity", "turn {on} starting over automatically when the end is reached|turn {on} cycling through the songs endlessly|turn {on} replaying everything once it finishes")
C("mus.like", "Like|I like this|Add to liked songs", "heart|thumbs-up|heart-plus", n="like|like this|liked songs", intents= "tell the app I enjoy {o}|mark {o} as one of my favourites|record that {o} is to my taste", o="this song")
C("mus.queue", "Queue|Up next|Play queue", "list-music|list-video|list-end", "{show} the songs lined up to come after this one|{show} what will be heard after the current song|{show} the upcoming songs in order")
C("mus.lyrics", "Lyrics|Song words|Sing along", "mic-vocal|letter-text|text", "read the words of the song that is on|see the text the vocalist is singing|follow the verses of the current song")
C("mus.devices", "Connect to a device|Speakers and devices|Output", "monitor-speaker|speaker|airplay", "send the sound to a different speaker|choose which gadget the music comes out of|move the audio over to other hardware")
C("mus.volume", "Volume|Loudness|Sound level", "", "make the music louder or quieter|turn the audio up or down|adjust how strong the audio is")
C("mus.mutev", "Mute sound|Silence audio|Sound off", "volume-2|volume-1|volume-x", "cut the audio completely without stopping the song|make the player go quiet while it keeps running|turn the speakers down to nothing in one click")
C("mus.seek", "Seek bar|Progress bar|Scrubber", "", "jump to a different moment of the current song|move to a later point in what is on|scrub through the current recording")
C("mus.mini", "Mini player|Compact player|Picture in picture", "picture-in-picture-2|picture-in-picture|minimize-2", "shrink the player into a tiny floating box|pop the controls out into a small window|collapse the app into a little always-visible strip")
C("mus.addpl", "Add to playlist|Save to playlist|Add to a list", "list-plus|badge-plus|diamond-plus", "put {o} into one of my collections|file {o} under one of my mixes|include {o} in a set of songs I keep", o="this song")
C("mus.unqueue", "Remove from queue|Drop from queue|Take out of the line-up", "list-x|list-minus|square-minus", "stop {o} from coming up later|cancel the upcoming play of {o}|strike {o} off what is about to be heard", o="this song")
C("mus.newpl", "New playlist|Create playlist|Start a mix", "", "make an empty collection of songs|begin a fresh compilation I can fill|set up a blank set of songs to curate")
C("mus.follow", "Follow|Subscribe|Keep up with", "", "be told when {o} releases something|get future releases from {o} automatically|stay informed about {o}", o="this artist")
C("mus.radio", "Go to radio|Start station|Similar music", "radio-tower|radio-receiver|antenna", "hear an endless stream resembling {o}|get non-stop songs in the vein of {o}|let the app choose more songs akin to {o}", o="this song")
C("mus.speed", "Playback speed|Tempo|Rate", "", "make the narration go faster or slower|change how quickly the episode is read out|hear the talk at 1.5 times normal pace")
C("mus.fwd15", "Skip 15 seconds|Jump ahead 15s|Forward 15", "redo-dot|step-forward|chevrons-right", "hop a few seconds ahead in the episode|leap slightly ahead past a dull bit|advance the episode by a quarter of a minute")
C("mus.back15", "Back 15 seconds|Rewind 15s|Replay 15", "undo-dot|step-back|chevrons-left", "hear the last few seconds again|go a quarter of a minute earlier in the episode|repeat what was just said")
C("mus.sleep", "Sleep timer|Stop after a while|Bedtime timer", "moon-star|bed|timer-off", "have the audio switch itself off after a set period|make the player stop on its own once I doze off|schedule the sound to end in half an hour")
C("mus.eq", "Equalizer|EQ|Tone controls", "sliders-vertical|audio-waveform|audio-lines", "boost the bass or treble|shape how low and high frequencies sound|tune the balance of frequencies")
C("mus.n.library", "Your library|My music|Collection", "library|library-big|square-library", "see everything I have saved|browse all the music I own|go to my own stash of albums and songs")
C("mus.n.liked", "Liked songs|Loved tracks|Thumbs up", "heart-pulse|hand-heart|folder-heart", "hear the songs I marked as enjoyable|go to my hand-picked favourites|open the list of songs I approved of")
C("mus.n.artists", "Artists|Performers|Musicians", "user-star|user-round-star|square-user", "browse my music by who made it|list the bands and singers I have|see the creators in my collection")
C("mus.n.albums", "Albums|Records|Releases|Discs", "disc-3|disc-album|album", "browse my music by full-length record|see the long-players I have saved|look through the LPs and EPs I own")
C("mus.n.songs", "Songs|Tracks|All music", "music|music-2|music-4", "list every individual piece I have|see each single recording in one long list|browse piece by piece regardless of record")
C("mus.n.podcasts", "Podcasts|Shows|Spoken word", "podcast|radio|rss|mic", "find talk programmes to listen to|get to the episodic talk programmes|listen to interviews and talk series")
C("mus.n.recent", "Recently added|New in library|Latest additions", "clock-plus|calendar-plus|sparkles", "see what I saved in the last few days|find the music that joined my stash most lately|list my newest acquisitions")
C("mus.n.browse", "Browse|Explore|Discover|Find music", "compass|telescope|globe|radar", "look for new music by genre and mood|find something I have not heard before|wander through charts and new releases")
C("mus.n.downloads", "Downloads|Offline|Saved to device", "circle-arrow-down|folder-down|monitor-down|arrow-down-to-dot", "see what I can hear without internet|list the audio stored on this machine|find what is available with no connection")
TABS = ["Overview", "Top tracks", "Discography", "Related", "About", "Concerts", "Genres", "Decades", "Moods", "Composers", "Compilations", "Live sets",
        "Singles", "New releases", "Charts", "Made for you", "Audiobooks", "Stations", "Videos", "Credits"]
GENRES = ["Alternative", "Ambient", "Blues", "Classical", "Country", "Dance", "Electronic", "Folk", "Hip-Hop", "House", "Indie Pop", "Jazz", "Latin", "Metal",
          "Pop", "Punk", "R&B", "Reggae", "Rock", "Soul", "Soundtrack", "Techno", "World", "Singer-Songwriter", "Lo-fi"]
ALBUM_A = ["Songs for", "Notes from", "Live at", "Return to", "Letters to", "Echoes of", "Tales from", "Nights in", "Postcards from", "Hymns for"]
ALBUM_B = ["the Harbor", "Lisbon", "Room 12", "the Valley", "Tokyo", "the North", "Marseille", "the Attic", "Reykjavik", "Nowhere", "the Lighthouse", "Oaxaca",
           "the Basement", "Glasgow", "the Outskirts", "Kyoto", "the Greenhouse", "Montreal", "the Ferry", "Havana", "the Arcade", "Tbilisi", "the Rooftop",
           "Detroit", "the Foothills", "Lagos", "the Motel", "Bergen", "the Orchard", "Valparaiso", "the Laundromat", "Perth", "the Overpass", "Seoul", "the Dunes"]
EPISODES = ["The four-day week experiment", "How bridges fail", "Inside a seed vault", "Why we forget names", "The last lighthouse keepers", "Mapping the ocean floor",
            "A short history of salt", "What sleep is for", "The city that moved", "Counting birds from space", "The typewriter revival", "Fixing the power grid",
            "Letters never sent", "How vaccines are made", "The people who name colors", "Life on a container ship", "When maps lie", "The quiet economy of libraries",
            "Rebuilding a coral reef", "The math of queues", "Who owns the moon", "A village without cars", "The fonts we trust", "Learning to listen",
            "The archive under the mountain", "Borrowed time zones", "Songs that cross borders", "The glassmakers of the lagoon", "How rumors travel", "A field guide to clouds"]
CHAPTERS = ["Cold open", "Intro and sponsors", "The backstory", "First interview", "A surprising number", "Listener mail", "Counterpoint", "Field recording",
            "What happens next", "Credits", "The turning point", "Second interview", "Fact check", "Recap", "Bonus segment"]

CSS = """
.mu-bar{flex:none;display:flex;align-items:center;gap:16px;padding:0 16px;height:76px;background:var(--bg2);border-top:1px solid var(--bd)}
.mu-play{width:36px;height:36px;border-radius:50%;background:var(--fg);color:var(--bg);display:flex;align-items:center;justify-content:center;flex:none}
.mu-play svg.i{width:18px;height:18px;stroke-width:2.2}
.mu-big{width:52px;height:52px;border-radius:50%;background:var(--ac);color:var(--acf);display:flex;align-items:center;justify-content:center;flex:none}
.mu-big svg.i{width:24px;height:24px;stroke-width:2.2}
.tabs.mu-pills{border-bottom:none;padding:0;gap:4px}
.tabs.mu-pills .tab{border:none;margin:0;border-radius:999px;height:var(--ch);background:var(--bg3)}
.tabs.mu-pills .tab.on{background:var(--acs2);color:var(--fg)}
.mu-card{display:flex;flex-direction:column;gap:6px;padding:10px;border-radius:var(--r2);flex:none}
.mu-lcd{display:flex;flex-direction:column;justify-content:center;gap:3px;background:var(--bg);border:1px solid var(--bd);border-radius:6px;padding:4px 12px;height:50px;min-width:0}
.mu-snip{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.mu-ep{display:flex;gap:14px;padding:12px 14px;border-bottom:1px solid var(--bd);flex:none}
"""


def _avatar(ctx, me, region, size=28):
    if not ctx.has("account"):
        return ctx.av(me, size)
    attr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=region, anchor="account")
    return f'<div class="row"{attr}>{ctx.av(me, size)}</div>'


def _slider(ctx, cid, frac, region, w=None, flex=False):
    if not ctx.has(cid):
        return ""
    attr = ctx.reg("slider", "slider", ctx.lab(cid), cid=cid, region=region, direct=False)
    pct = round(frac * 100)
    style = f"width:{w}px;flex:none" if w else "flex:1"
    return f'<div class="sld"{attr} style="{style}"><div class="fill" style="width:{pct}%"></div><div class="th" style="left:{pct}%"></div></div>'


def _songs(ctx, n):
    rng = ctx.rng
    bs = list(pool("song.b", SONG_B, ctx.split))
    seen, out = set(), []
    while len(out) < n and len(seen) < len(bs) * len(SONG_A):
        t = f"{rng.choice(SONG_A)} {rng.choice(bs)}"
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _albums(ctx, n):
    rng = ctx.rng
    bs = ctx.d.take("album.b", ALBUM_B)
    seen, out = set(), []
    while len(out) < n and len(seen) < len(bs) * len(ALBUM_A):
        t = f"{rng.choice(ALBUM_A)} {rng.choice(bs)}"
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _dur(rng):
    return f"{rng.randint(2, 6)}:{rng.randint(0, 59):02d}"


def _playbtn(ctx, region, cls="mu-play", playing=None, obj=None):
    playing = ctx.rng.random() < 0.5 if playing is None else playing
    cid = "mus.pause" if playing else "mus.play"
    return ctx.ibtn(cid, region, cls=cls, obj=obj).replace('class="ib ' + cls, 'class="' + cls, 1)


def _transport(ctx, region, podcast=False, playing=None):
    side_l = ctx.ibtn("mus.back15", region) if podcast else ctx.ibtn("mus.shuffle", region, state=ctx.rng.random() < 0.5)
    side_r = ctx.ibtn("mus.fwd15", region) if podcast else ctx.ibtn("mus.repeat", region, state=ctx.rng.random() < 0.5)
    return f'<div class="row g8 cen">{side_l}{ctx.ibtn("mus.prev", region)}{_playbtn(ctx, region, playing=playing)}{ctx.ibtn("mus.next", region)}{side_r}</div>'


def _seek(ctx, region, w=None):
    rng = ctx.rng
    f = rng.uniform(0.1, 0.9)
    return (f'<div class="row g8 xs mut" style="{f"width:{w}px" if w else "align-self:stretch"}"><span>{int(f * 4)}:{rng.randint(0, 59):02d}</span>'
            f'{_slider(ctx, "mus.seek", f, region)}<span>{_dur(rng)}</span></div>')


def _playerbar(ctx, song, artist, region="the player bar", W=1440):
    rng = ctx.rng
    left = (f'<div class="row g10" style="width:{min(340, W // 4)}px;min-width:0">{ctx.thumb(52, 52, 4)}<div class="col" style="min-width:0"><span class="m mu-snip">{esc(song)}</span>'
            f'<span class="xs mut mu-snip">{esc(artist)}</span></div>{ctx.ibtn("mus.like", region, cls="s", obj="the current song")}</div>')
    mid = f'<div class="col g4 f1" style="align-items:center;max-width:720px;margin:0 auto">{_transport(ctx, region)}{_seek(ctx, region)}</div>'
    right = (f'<div class="row g4 end" style="width:{min(340, W // 4)}px">{ctx.ibtn("mus.lyrics", region, cls="s")}{ctx.ibtn("mus.queue", region, cls="s", state=False)}{ctx.ibtn("mus.devices", region, cls="s")}'
             f'{ctx.ibtn("mus.mutev", region, cls="s")}{_slider(ctx, "mus.volume", rng.uniform(0.3, 0.9), region, 92)}{ctx.ibtn("mus.mini", region, cls="s")}{ctx.ibtn("fullscreen", region, cls="s")}</div>')
    return f'<div class="mu-bar">{left}{mid}{right}</div>'


def _trackrow(ctx, i, song, artist, album, region, sel=False, thumb=True, dense=False, extra=""):
    rng, d = ctx.rng, ctx.d
    attr = ctx.reg("row", rng.choice(["song", "track"]), song, region=region, anchor="row")
    obj = f"the song {song}"
    like = ctx.ibtn("mus.like", region, row=song, obj=obj, cls="s", anchor=None)
    more = ctx.ibtn("more", region, row=song, obj=obj, cls="s", anchor="more")
    if dense:
        return (f'<div class="tr z{" sel" if sel else ""}"{attr}><div class="td mut r" style="width:44px">{i + 1}</div><div class="td f"><span class="el">{esc(song)}</span></div>'
                f'<div class="td mut r" style="width:58px">{_dur(rng)}</div><div class="td" style="width:21%"><span class="mu-snip">{esc(artist)}</span></div>'
                f'<div class="td" style="width:21%"><span class="mu-snip">{esc(album)}</span></div>{extra}<div class="td mut r" style="width:58px">{rng.randint(0, 240)}</div><div class="td" style="width:34px;padding:0">{like}</div></div>')
    pic = ctx.thumb(34, 34, 3) if thumb else ""
    return (f'<div class="tr{" sel" if sel else ""}" style="min-height:calc(var(--rh) + 20px);border-bottom:none"{attr}><div class="td mut r" style="width:44px">{i + 1}</div>'
            f'<div class="td f">{pic}<div class="col" style="min-width:0"><span class="el {"acc" if sel else ""} m">{esc(song)}</span><span class="mu-snip xs mut">{esc(artist)}</span></div></div>'
            f'<div class="td mut" style="width:24%"><span class="mu-snip">{esc(album)}</span></div><div class="td mut" style="width:120px">{d.date(True)}</div>'
            f'<div class="td" style="width:34px;padding:0">{like}</div><div class="td mut r" style="width:56px">{_dur(rng)}</div><div class="td" style="width:36px;padding:0">{more}</div></div>')


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    me = d.person()
    songs = _songs(ctx, H // 24 + 8)
    artists = d.take("artists", ARTISTS)
    albums = _albums(ctx, 60)
    pls = d.take("playlists", PLAYLISTS, min(14, H // 70))
    now_song, now_artist = songs.pop(), rng.choice(artists)
    ctx.ctxmenu = ["mus.addpl", "mus.queue", "mus.radio", "-", "mus.like", "share", "link", "download", "-", "info", "delete"]
    ctx.ctxobj = "this song"
    ctx.menus["mb.controls"] = ["mus.play", "mus.pause", "mus.next", "mus.prev", "-", "mus.shuffle", "mus.repeat", "-", "mus.eq", "mus.sleep", "mus.mini"]
    sw = rng.choice([220, 240, 260]) + (40 if W > 1900 else 0)
    art = lambda: rng.choice(artists)
    alb = lambda: rng.choice(albums)

    if variant == "spotify":
        region = "the sidebar"
        nav = "".join(ctx.navc(c, region, on=i == 2, noun="link") for i, c in enumerate(ctx.avail(["home", "mus.n.browse", "mus.n.library", "mus.n.liked", "mus.n.podcasts"])))
        plist = "".join(ctx.nav(p, region, noun="playlist", icon_html=ctx.thumb(22, 22, 3), on=i == 0, anchor="row") for i, p in enumerate(pls))
        side = (f'<div class="side br" style="width:{sw}px"><div class="col g2 py8">{nav}</div><div class="row px12" style="padding-top:8px"><span class="hd sp" style="padding:4px 4px">Playlists</span>'
                f'{ctx.ibtn("add", region, cls="s", obj="my playlists", anchor=None)}{ctx.ibtn("sort", region, cls="s", anchor=None)}</div><div class="col g2 f1 clip">{plist}</div>'
                f'<div class="p8 bt">{ctx.tbtn("mus.newpl", region, cls="ghost w100", icon=False)}</div></div>')
        top = (f'<div class="row g8 px16" style="height:56px;flex:none">{ctx.ibtn("back", "the app header", cls="rnd bdr")}{ctx.ibtn("forward", "the app header", cls="rnd bdr")}{ctx.search("the app header", w=min(420, W // 4), cls="rnd soft")}'
               f'<div class="sp"></div>{ctx.ibtn("notif", "the app header")}{ctx.ibtn("settings", "the app header")}{_avatar(ctx, me, "the app header")}</div>')
        hero = (f'<div class="row g16 px16" style="align-items:flex-end;padding-bottom:14px;flex:none">{ctx.thumb(150 if H > 850 else 96, 150 if H > 850 else 96, 6)}<div class="col g6"><span class="xs b up">Playlist</span>'
                f'<span class="b" style="font-size:{34 if H > 850 else 24}px;line-height:1.1">{esc(pls[0])}</span><span class="mut sm">{esc(me)} · {len(songs)} songs, {rng.randint(1, 4)} hr {rng.randint(1, 59)} min</span></div></div>')
        acts = (f'<div class="row g12 px16" style="padding-bottom:10px;flex:none">{_playbtn(ctx, "the playlist header", "mu-big", obj="this playlist")}{ctx.ibtn("mus.shuffle", "the playlist header", cls="l")}'
                f'{ctx.ibtn("download", "the playlist header", cls="l", obj="this playlist")}{ctx.ibtn("share", "the playlist header", cls="l", obj="this playlist")}{ctx.ibtn("more", "the playlist header", cls="l", obj="this playlist", anchor="more")}'
                f'<div class="sp"></div>{ctx.select("Sort order", "Custom order", options=["Custom order", "Title", "Artist", "Recently added", "Duration"], region="the playlist header", above=False, w=150, cls="soft", refs=["the sort order dropdown above the track list", "the dropdown that sets how the songs are ordered"])}</div>')
        hdr = ('<div class="tr h" style="background:none"><div class="td r" style="width:44px">#</div><div class="td f">Title</div><div class="td" style="width:24%">Album</div>'
               '<div class="td" style="width:120px">Date added</div><div class="td" style="width:34px"></div><div class="td r" style="width:56px">Time</div><div class="td" style="width:36px"></div></div>')
        seli = rng.randrange(3, 9)
        rows = "".join(_trackrow(ctx, i, s, art(), alb(), "the track list", i == seli) for i, s in enumerate(songs))
        main = f'<div class="col f1 clip">{top}{hero}{acts}<div class="col f1 clip px8">{hdr}{rows}</div></div>'
        body = f'<div class="col f1"><div class="row str f1">{side}{main}</div>{_playerbar(ctx, now_song, now_artist, W=W)}</div>'
    elif variant == "itunes":
        region = "the player bar"
        lcd = (f'<div class="mu-lcd f1" style="max-width:640px;margin:0 auto"><div class="row g8"><span class="m mu-snip f1 ct">{esc(now_song)} — {esc(now_artist)}</span></div>{_seek(ctx, region)}</div>')
        bar = (f'<div class="row g12 px16 bg2 bb" style="height:64px;flex:none">{_transport(ctx, region)}{ctx.ibtn("mus.mutev", region, cls="s")}{_slider(ctx, "mus.volume", rng.uniform(0.3, 0.9), region, 100)}'
               f'{lcd}{ctx.ibtn("mus.lyrics", region)}{ctx.ibtn("mus.queue", region, state=False)}{ctx.ibtn("mus.devices", region)}{ctx.search(region, w=rng.choice([180, 220]), cls="rnd")}</div>')
        nav = "".join(ctx.navc(c, "the sidebar", on=i == 3, noun="section") for i, c in enumerate(ctx.avail(["mus.n.recent", "mus.n.artists", "mus.n.albums", "mus.n.songs", "mus.n.downloads", "mus.n.podcasts"])))
        plist = "".join(ctx.nav(p, "the sidebar", noun="playlist", deco=("list-music", "music", "list-video", "disc-3", "audio-lines", "headphones"), anchor="row") for p in pls)
        side = (f'<div class="side br" style="width:{sw - 20}px"><div class="hd">Library</div><div class="col g2">{nav}</div><div class="hd">Playlists</div><div class="col g2 f1 clip">{plist}</div>'
                f'<div class="row g4 p8 bt">{ctx.ibtn("add", "the sidebar", cls="s", obj="my playlists", anchor=None)}{ctx.ibtn("mus.eq", "the sidebar", cls="s")}{ctx.ibtn("settings", "the sidebar", cls="s")}</div></div>')
        kb = max(5, min(9, H // 110))

        def browser(title, items, noun, sel, reg):
            rows = f'<div class="li sel b" style="min-height:var(--rh)">All ({rng.randint(12, 240)} {title}s)</div>' if sel < 0 else f'<div class="li mut" style="min-height:var(--rh)">All ({rng.randint(12, 240)} {title}s)</div>'
            for i, it in enumerate(items[:kb]):
                attr = ctx.reg("row", noun, it, region=reg)
                rows += f'<div class="li{" sel" if i == sel else ""}" style="min-height:var(--rh)"{attr}><span class="el">{esc(it)}</span></div>'
            return f'<div class="col f1 br clip"><div class="tr h px8" style="padding-left:10px">{title}</div>{rows}</div>'
        cols = (browser("Genre", d.take("genres", GENRES), "genre", rng.randrange(3), "the genre column") + browser("Artist", artists, "artist", rng.randrange(3), "the artist column")
                + browser("Album", albums, "album", -1, "the album column"))
        hdr = ('<div class="tr h"><div class="td r" style="width:44px"></div><div class="td f">Name</div><div class="td r" style="width:58px">Time</div><div class="td" style="width:21%">Artist</div>'
               '<div class="td" style="width:21%">Album</div><div class="td" style="width:110px">Genre</div><div class="td r" style="width:58px">Plays</div><div class="td" style="width:34px"></div></div>')
        seli = rng.randrange(2, 10)
        gs = d.take("genres", GENRES)
        rows = "".join(_trackrow(ctx, i, s, art(), alb(), "the track list", i == seli, dense=True, extra=f'<div class="td mut" style="width:110px"><span class="mu-snip">{esc(rng.choice(gs))}</span></div>') for i, s in enumerate(songs))
        status = f'<div class="sbar"><div class="sp"></div><span>{rng.randint(200, 9000):,} songs, {rng.randint(2, 40)}.{rng.randint(0, 9)} days, {rng.randint(3, 90)}.{rng.randint(0, 9)} GB</span><div class="sp"></div></div>'
        main = f'<div class="col f1 clip"><div class="row str bb" style="flex:none">{cols}</div>{hdr}<div class="col f1 clip">{rows}</div></div>'
        body = f'<div class="col f1">{bar}<div class="row str f1">{side}{main}</div>{status}</div>'
    elif variant == "album_grid":
        tabs = ctx.tabs(d.take("music.tabs", TABS, 4), 0, region="the top bar", cls="mu-pills")
        top = (f'<div class="row g8 px16 bb" style="height:calc(var(--ch) + 26px);flex:none">{ctx.ibtn("sidebar.toggle", "the top bar")}<div class="f1" style="min-width:0">{tabs}</div>'
               f'{ctx.search("the top bar", w=rng.choice([200, 240]), cls="soft")}{ctx.iseg(["view.grid", "view.list"], 0, region="the top bar")}{ctx.ibtn("mus.eq", "the top bar")}{_avatar(ctx, me, "the top bar")}</div>')
        cw = rng.choice([150, 170, 190])
        cards = []
        for a in albums[:max(8, (W - 340) // (cw + 30) * (H // (cw + 70)) + 4)]:
            attr = ctx.reg("row", "album", a, region="the album grid", anchor="row")
            cards.append(f'<div class="mu-card" style="width:{cw + 20}px"{attr}>{ctx.thumb(cw, cw, 6)}<span class="m" style="line-height:1.25">{esc(a)}</span><span class="xs mut mu-snip">{esc(art())} · {rng.randint(1998, 2026)}</span></div>')
        grid = f'<div class="row wrap top g4 p12 f1 clip" style="align-content:flex-start">{"".join(cards)}</div>'
        q = []
        for i, s in enumerate(songs[:max(6, H // 52 - 3)]):
            attr = ctx.reg("row", "song", s, region="the queue", anchor="row")
            rm = ctx.ibtn("mus.unqueue", "the queue", row=s, obj=f"the song {s}", cls="s", anchor=None)
            q.append(f'<div class="li" style="min-height:48px"{attr}><span class="fnt">{ctx.deco("grip-vertical", "grip", "menu", "equal", "align-justify", size=14)}</span>{ctx.thumb(34, 34, 3)}'
                     f'<div class="col f1" style="min-width:0"><span class="el m">{esc(s)}</span><span class="xs mut mu-snip">{esc(art())}</span></div><span class="xs mut">{_dur(rng)}</span>{rm}</div>')
        queue = (f'<div class="side bl" style="width:{rng.choice([300, 330, 360])}px"><div class="row g6 p12 bb"><span class="b sp">Coming up</span>{ctx.tbtn("clear", "the queue", cls="ghost sm", obj="the queue")}'
                 f'{ctx.ibtn("mus.shuffle", "the queue", cls="s")}</div><div class="col f1 clip">{"".join(q)}</div></div>')
        bar = (f'<div class="row g12 px16 bt bg2" style="height:62px;flex:none">{ctx.thumb(42, 42, 4)}<div class="col" style="width:200px;min-width:0"><span class="m mu-snip">{esc(now_song)}</span><span class="xs mut mu-snip">{esc(now_artist)}</span></div>'
               f'{ctx.ibtn("mus.prev", "the transport bar")}{_playbtn(ctx, "the transport bar")}{ctx.ibtn("mus.next", "the transport bar")}<div class="f1">{_seek(ctx, "the transport bar")}</div>'
               f'{ctx.ibtn("mus.repeat", "the transport bar", cls="s", state=False)}{ctx.ibtn("mus.like", "the transport bar", cls="s", obj="the current song")}{ctx.ibtn("mus.addpl", "the transport bar", cls="s", obj="the current song")}'
               f'{ctx.ibtn("mus.mutev", "the transport bar", cls="s")}{_slider(ctx, "mus.volume", rng.uniform(0.3, 0.9), "the transport bar", 90)}{ctx.ibtn("mus.devices", "the transport bar", cls="s")}</div>')
        body = f'<div class="col f1">{top}<div class="row str f1">{grid}{queue}</div>{bar}</div>'
    else:  # podcast
        nav = "".join(ctx.navc(c, "the sidebar", on=i == 1, noun="section") for i, c in enumerate(ctx.avail(["home", "mus.n.browse", "mus.n.podcasts", "mus.n.recent", "mus.n.downloads", "mus.n.library"])))
        shows = "".join(ctx.nav(p, "the sidebar", noun="show", icon_html=ctx.thumb(22, 22, 4), anchor="row") for p in pls[:6])
        side = (f'<div class="side br" style="width:{sw}px"><div class="p8">{ctx.search("the sidebar", cls="soft")}</div><div class="col g2">{nav}</div><div class="hd">Following</div><div class="col g2 f1 clip">{shows}</div>'
                f'<div class="row g8 p8 bt">{_avatar(ctx, me, "the sidebar")}<span class="el f1 m">{esc(me)}</span>{ctx.ibtn("settings", "the sidebar", cls="s")}</div></div>')
        show = rng.choice(["Field Recordings", "The Long Way Round", "Signal & Noise", "Small Hours", "Curious Minutes"])
        head = (f'<div class="row g16 p16 bb" style="flex:none">{ctx.thumb(120, 120, 8)}<div class="col g6 f1"><span class="xs b up mut">Podcast</span><span class="xxl b">{esc(show)}</span>'
                f'<span class="mut">{rng.choice(["Halfmoon Audio", "Parkside Radio", "Tin Roof Media"])} · Weekly · {rng.randint(40, 380)} episodes</span>'
                f'<div class="row g8" style="margin-top:4px">{ctx.tbtn("mus.follow", "the show header", cls="pri", obj="this show")}{ctx.ibtn("notif", "the show header", cls="bdr")}{ctx.ibtn("share", "the show header", cls="bdr", obj="this show")}'
                f'{ctx.ibtn("more", "the show header", cls="bdr", obj="this show", anchor="more")}<div class="sp"></div>{ctx.select("Episode order", "Newest first", options=["Newest first", "Oldest first", "Unplayed", "Downloaded"], region="the show header", above=False, w=150, refs=["the episode order dropdown", "the dropdown that sorts the episodes"])}</div></div></div>')
        base = d.take("episodes", EPISODES)
        eps = base + [f"{t} (Part 2)" for t in base] + [f"{t} (Live)" for t in base]
        cards = []
        for i, t in enumerate(eps[:H // 96 + 1]):
            attr = ctx.reg("row", "episode", t, region="the episode list", anchor="row")
            obj = f"the episode {t}"
            btns = (ctx.ibtn("mus.play", "the episode list", row=t, obj=obj, cls="bdr rnd", anchor=None) + ctx.ibtn("download", "the episode list", row=t, obj=obj, cls="s", anchor=None)
                    + ctx.ibtn("mus.addpl", "the episode list", row=t, obj=obj, cls="s", anchor=None) + ctx.ibtn("more", "the episode list", row=t, obj=obj, cls="s", anchor="more"))
            cards.append(f'<div class="mu-ep"{attr}><div class="col g4 f1" style="min-width:0"><span class="xs mut">{d.date(True)} · {rng.randint(18, 74)} min{" · Played" if i > 3 and rng.random() < 0.4 else ""}</span>'
                         f'<span class="b lg el">{esc(t)}</span><span class="mu-snip mut">{esc(d.sentence())}</span></div><div class="row g4">{btns}</div></div>')
        main = f'<div class="col f1 clip">{head}<div class="col f1 clip">{"".join(cards)}</div></div>'
        region = "the now playing panel"
        chs = ""
        for i, c in enumerate(d.take("chapters", CHAPTERS, 5)):
            attr = ctx.reg("row", "chapter", c, region=region)
            chs += f'<div class="li{" sel" if i == 1 else ""}"{attr}><span class="xs mut" style="width:38px">{i * 7}:{rng.randint(0, 59):02d}</span><span class="el">{esc(c)}</span></div>'
        speed = ctx.select(ctx.lab("mus.speed"), rng.choice(["1×", "1.2×", "1.5×"]), options=["0.8×", "1×", "1.2×", "1.5×", "2×"], region=region, cid="mus.speed", w=120) if ctx.has("mus.speed") else ""
        pw = rng.choice([300, 330, 360])
        panel = (f'<div class="side bl p16 g12" style="width:{pw}px"><div class="row"><span class="b sp">Now playing</span>{ctx.ibtn("close.panel", region, cls="s", obj="the now playing panel")}</div>{ctx.thumb(pw - 32, min(pw - 32, H // 4), 8)}'
                 f'<div class="col"><span class="b lg">Episode {rng.randint(40, 300)}</span><span class="mut sm">{esc(show)}</span></div>{_seek(ctx, region)}{_transport(ctx, region, podcast=True, playing=True)}'
                 f'<div class="row g8" style="align-items:flex-end">{speed}<div class="sp"></div>{ctx.ibtn("mus.sleep", region, cls="bdr")}{ctx.ibtn("mus.devices", region, cls="bdr")}{ctx.ibtn("mus.queue", region, cls="bdr", state=False)}</div>'
                 f'<div class="row g6">{ctx.ibtn("mus.mutev", region, cls="s")}{_slider(ctx, "mus.volume", rng.uniform(0.3, 0.9), region)}</div><div class="hsep"></div><span class="xs b up mut">Chapters</span><div class="col f1 clip">{chs}</div></div>')
        body = f'<div class="row str f1">{side}{main}{panel}</div>'
    return {"title": f"{now_song} · {now_artist}", "body": body, "css": CSS, "app": rng.choice(["Music", "Tuneful", "Wavelength"]),
            "menus": ["mb.file", "mb.edit", "mb.view", "mb.controls", "mb.account", "mb.window", "mb.help"], "url": "play.example.com/library"}
