"""Music (a player in the style of macOS Music): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
"""
from ..oracle import Click, Drag, Key, Reveal
from .base import Spec, by_id, cond, only, say, task, unchanged, verdict

SIZE = (1040, 660)
WIN = '.win[data-app="music"] '
N_SONGS = 60
IN_VIEW = 14            # the first rows of the song table that are certainly on screen without scrolling

# Invented for this test set: no real artists, albums or songs.
TITLES = [
    "Paper Lanterns", "Slow Tide Rising", "Glass Orchard", "Borrowed Umbrella", "Northbound Sleeper", "Tangerine Hour", "Static Bloom",
    "Letters to Ivo", "Half a Map", "Salt on the Windowsill", "Midnight Cartographer", "Copper Kettle Blues", "Ferry to Nowhere",
    "Small Hours Waltz", "Quiet Machinery", "Lemon Tree Lane", "The Long Way Round", "Porchlight", "Second Hand Sun", "Velvet Static",
    "Harbour Lights Out", "Marigold Engine", "Counting Pylons", "Blue Thermos", "Winter Greenhouse", "Postcard from Aldermere",
    "Tin Roof Morning", "Signal Fires", "Clockwork Sparrow", "Low Battery Heart", "Driftwood Radio", "Ninth Floor View",
    "Honeycomb Streets", "Last Tram Home", "Unsent Draft", "Foxglove", "Saturday Scaffold", "Moth Season", "Kite Weather",
    "Pocket Atlas", "Cedar and Smoke", "Rented Tuxedo", "Dial Tone Lullaby", "Parallel Parking", "Swimming at Dusk",
    "Hand-Me-Down Stars", "Milk Glass Moon", "Overgrown", "Radio Silence in June", "Tiny Earthquakes", "Violet Ledger",
    "Wool Coat Weather", "Yesterday's Timetable", "Zinc Rooftops", "Apricot Sky", "Backroom Chandelier", "Cinder Path",
    "Double Yellow Lines", "Elevator Daydream", "Fig Season", "Hollow Bell", "Inkwell", "Jasmine at the Depot", "Keys in the Fridge",
    "Laundromat Sonata", "Mineral Springs", "November Bicycle", "Open Late", "Plum Dark Evening", "Quarter Past Maybe",
    "Rosewater Engine", "Sleepwalk to the Sea", "Thimble of Rain", "Understudy", "Vending Machine Light", "Wishbone Avenue",
    "Yellow Raincoat Parade", "Almost Tuesday", "Bright Little Wreck", "Carousel in Fog", "Dandelion Clock", "Eleven Stairs",
    "Fold the Map", "Gull and Anchor", "Hazel Switch", "Icebox Summer", "Jigsaw Sky", "Kerosene Lamp", "Lighter than Linen",
    "Mossy Stone Steps", "Nectarine", "Orbit of Small Things", "Paperweight", "Quince and Clove", "Rust Belt Hymn",
    "Seven Magpies", "Turnstile Heart", "Umbrella Stand", "Varnish and Dust", "Weathervane", "Year of the Heron", "Zero Hour Bakery",
]
ARTISTS = [
    "Odalys Brenner", "Tessaly Vane", "The Quiet Meridians", "Marlowe and the Tin Foxes", "Juno Aldercott", "Kestrel Parade",
    "Sable Hinterland", "Ivo Castellane Trio", "Night Bus to Larkspur", "Paloma Whitlow", "Hollow Pine Choir", "Dario Venn",
    "Copper Tide Ensemble", "Mina Lindqvist", "The Saltmarsh Five", "Wren Halloway", "Glasshouse Weather", "Tobiah Strand",
    "Fenwick Lowe", "Lantern Arcade",
]
ALBUMS = [
    "Maps for the Lost", "Low Tide Diaries", "Greenhouse Sessions", "Postcards Unsent", "The Borrowed Year", "Static and Honey",
    "Night Ferry", "Small Rooms", "Weather for Staying In", "Tin Stars", "Long Shadow Season", "Eleven Lamps", "Off the Timetable",
    "Field Notes", "Kitchen Radio", "Saltwater Arithmetic", "Unfinished Rooms", "Parade Ground", "Soft Machines at Dawn",
    "The Understory", "Borrowed Light", "Second Winter", "Rooftop Almanac", "Harbour Hymnal",
]
PLAYLISTS = ["Morning Run", "Deep Focus", "Road Trip", "Sunday Cooking", "Late Night Drive", "Rainy Day", "Gym Mix", "Dinner Party",
             "Study Session", "Throwbacks", "Chill Evenings", "Commute", "Summer BBQ", "Wind Down", "Housework", "Favourites 2026"]


def default(rng):
    artists = rng.sample(ARTISTS, 9)
    albums = rng.sample(ALBUMS, 14)
    owner = {a: artists[i] if i < len(artists) else rng.choice(artists) for i, a in enumerate(albums)}
    slots = albums * 2 + [rng.choice(albums) for _ in range(N_SONGS - 2 * len(albums))]
    rng.shuffle(slots)
    songs = [{"id": f"s{n}", "title": t, "artist": owner[al], "album": al, "time": f"{rng.randint(2, 5)}:{rng.randint(0, 59):02d}",
              "loved": rng.random() < 0.2} for n, (t, al) in enumerate(zip(rng.sample(TITLES, N_SONGS), slots), 1)]
    songs.sort(key=lambda x: x["title"].lower())          # the library is shown by title, as the Songs view of the real app
    names = rng.sample(PLAYLISTS, rng.randint(5, 6))
    playlists = [{"id": f"p{i}", "name": name, "songs": [x["id"] for x in rng.sample(songs, rng.randint(6, 11))]} for i, name in enumerate(names, 1)]
    return {"songs": songs, "playlists": playlists,
            "player": {"current": rng.choice(songs)["id"] if rng.random() < 0.7 else None, "playing": False, "shuffle": False,
                       "repeat": "off", "volume": rng.randint(30, 80) / 100},
            "ui": {"view": "songs", "sel": None, "search": ""}}


def row(x):
    return WIN + f'.mu-row[data-arg="{x["id"]}"]'


def side(p):
    return WIN + f'.sb-item[data-arg="{p["id"]}"]'


def player(st):
    return st["apps"]["music"]["player"]


def other_song(rng, s, *not_these):
    return rng.choice([x for x in s["songs"] if x["id"] not in not_these])


def set_player(S, playing, exclude=()):
    """Some song (never one of `exclude`) is loaded; `playing` None leaves it to the seed."""
    s = S.apps["music"]
    s["player"]["current"] = other_song(S.rng, s, *exclude)["id"]
    s["player"]["playing"] = S.rng.random() < 0.5 if playing is None else playing
    return by_id(s["songs"], s["player"]["current"])


@task("music.pause", "single")
def pause(S):
    s = S.apps["music"]
    set_player(S, True)
    s["player"]["shuffle"] = S.rng.random() < 0.3
    S.open("music")
    return Spec(request=say(S.rng, "Pause the music.", "Stop the song that's playing for a moment, I need to take a call."),
                steps=[Click(WIN + '.tb-btn[data-act="playpause"]', "Click the pause button in the playback controls at the top of the Music window")],
                check=lambda st, init: verdict(cond(player(st)["playing"] is False, "the music is still playing"),
                                               only(st, init, "music.player.playing")))


@task("music.shuffle_on", "single")
def shuffle_on(S):
    s = S.apps["music"]
    set_player(S, None)
    s["player"]["shuffle"] = False
    s["player"]["repeat"] = S.rng.choice(["off", "off", "all", "one"])
    S.open("music")
    return Spec(request=say(S.rng, "Turn on shuffle in Music.", "Switch shuffle on so my songs come up in a random order."),
                steps=[Click(WIN + '.tb-btn[data-act="shuffle"]', "Click the shuffle button, the crossed arrows at the left end of the playback controls in the Music window")],
                check=lambda st, init: verdict(cond(player(st)["shuffle"] is True, "shuffle is off"),
                                               only(st, init, "music.player.shuffle")))


@task("music.volume", "drag")
def volume(S):
    s = S.apps["music"]
    set_player(S, None)
    now = round(s["player"]["volume"] * 100)
    target = S.rng.choice([t for t in range(20, 81, 5) if abs(t - now) >= 15])
    S.open("music")

    def check(st, init):
        v = player(st)["volume"] * 100
        return verdict(cond(abs(v - target) <= 6.001, f"the volume is at {round(v)}%, not about {target}%"),
                       only(st, init, "music.player.volume"))
    return Spec(request=say(S.rng, f"Set the Music volume to about {target}%.", f"Change the volume in Music to roughly {target} percent."),
                steps=[Drag(WIN + ".mu-vol .knob", WIN + ".mu-track", "the round knob of the volume slider at the top right of the Music window",
                            f"the point {target}% of the way along the volume slider", dst_at=(target / 100, 0.5))],
                check=check)


@task("music.play_song", "scroll")
def play_song(S):
    s = S.apps["music"]
    x = S.rng.choice(s["songs"][30:])
    set_player(S, None, exclude=(x["id"],))
    S.open("music")
    return Spec(request=say(S.rng, f"Play “{x['title']}”.", f"Put on the song “{x['title']}” by {x['artist']}."),
                steps=[Reveal(row(x)), Click(row(x), f"Double-click the song “{x['title']}” in the song list", count=2, at=(0.2, 0.5))],
                check=lambda st, init: verdict(cond(player(st)["current"] == x["id"], "that song is not the current song"),
                                               cond(player(st)["playing"] is True, "nothing is playing"),
                                               only(st, init, "music.player.current", "music.player.playing")))


def song_and_playlist(S):
    """A song among the rows in view and a playlist that does not have it yet."""
    s = S.apps["music"]
    p = S.rng.choice(s["playlists"])
    x = S.rng.choice([x for x in s["songs"][:IN_VIEW] if x["id"] not in p["songs"]])
    return s, x, p


def added(x, p):
    def check(st, init):
        now = by_id(st["apps"]["music"]["playlists"], p["id"])["songs"]
        before = by_id(init["apps"]["music"]["playlists"], p["id"])["songs"]
        return verdict(cond(x["id"] in now, f"“{x['title']}” is not in {p['name']}"),
                       cond(now == before + [x["id"]], f"the songs of {p['name']} changed in another way"),
                       only(st, init, f"music.playlists.{p['id']}.songs"))
    return check


@task("music.add_to_playlist", "menu")
def add_to_playlist(S):
    s, x, p = song_and_playlist(S)
    set_player(S, None)
    S.open("music")
    return Spec(request=say(S.rng, f"Add “{x['title']}” to my {p['name']} playlist.", f"Put the song “{x['title']}” on the playlist called “{p['name']}”."),
                steps=[Click(row(x), f"Right-click the song “{x['title']}” in the song list", button="right", at=(0.2, 0.5)),
                       Click('.menu-item:has(.mi-label:text-is("Add to Playlist"))', "Click “Add to Playlist” in the menu"),
                       Click(f'.menu-item:has(.mi-label:text-is("{p["name"]}"))', f"Click “{p['name']}” in the submenu")],
                check=added(x, p))


@task("music.drag_to_playlist", "drag")
def drag_to_playlist(S):
    s, x, p = song_and_playlist(S)
    set_player(S, None)
    S.open("music")
    return Spec(request=say(S.rng, f"Drag “{x['title']}” onto the {p['name']} playlist.", f"Add the song “{x['title']}” to “{p['name']}” by dragging it there."),
                steps=[Drag(row(x), side(p), f"the song “{x['title']}” in the song list", f"the playlist “{p['name']}” in the sidebar", src_at=(0.2, 0.5))],
                check=added(x, p))


@task("music.next_song", "shortcut")
def next_song(S):
    s = S.apps["music"]
    i = S.rng.randrange(0, 40)
    cur, nxt = s["songs"][i], s["songs"][i + 1]
    s["player"].update(current=cur["id"], playing=True, shuffle=False, repeat=S.rng.choice(["off", "all"]))
    S.open("music")
    return Spec(request=say(S.rng, "Skip to the next song.", "I don't like this one. Play the next track."),
                steps=[Key("cmd+right")],
                check=lambda st, init: verdict(cond(player(st)["current"] == nxt["id"], f"the current song is not the one after “{cur['title']}”"),
                                               cond(player(st)["playing"] is True, "nothing is playing"),
                                               only(st, init, "music.player.current")))


@task("music.play_from_playlist", "chain")
def play_from_playlist(S):
    s = S.apps["music"]
    p = S.rng.choice(s["playlists"])
    far = {x["id"] for x in s["songs"][20:]}                       # not on screen in the library, so the playlist is the way to it
    if not any(i in far for i in p["songs"]):
        p["songs"].append(S.rng.choice(sorted(far)))
    x = by_id(s["songs"], S.rng.choice([i for i in p["songs"] if i in far]))
    set_player(S, None, exclude=(x["id"],))
    S.open("music")
    return Spec(request=say(S.rng, f"Open my {p['name']} playlist and play “{x['title']}” from it.", f"Go to the “{p['name']}” playlist and put on “{x['title']}”."),
                steps=[Click(side(p), f"Click the playlist “{p['name']}” in the sidebar"),
                       Reveal(row(x)),
                       Click(row(x), f"Double-click the song “{x['title']}” in the playlist", count=2, at=(0.2, 0.5))],
                check=lambda st, init: verdict(cond(player(st)["current"] == x["id"], "that song is not the current song"),
                                               cond(player(st)["playing"] is True, "nothing is playing"),
                                               cond(st["apps"]["music"]["ui"]["view"] == p["id"], f"the {p['name']} playlist is not open"),
                                               only(st, init, "music.player.current", "music.player.playing")))


@task("music.already_paused", "already_done")
def already_paused(S):
    s = S.apps["music"]
    set_player(S, False)
    if S.rng.random() < 0.3:
        s["player"]["current"] = None
    S.open("music")
    return Spec(request=say(S.rng, "Make sure the music is paused.", "If a song is playing in Music, pause it."),
                steps=[], kind="already_done", check=unchanged)


@task("music.missing_song", "infeasible")
def missing_song(S):
    s = S.apps["music"]
    have = {x["title"] for x in s["songs"]}
    ghost = S.rng.choice([t for t in TITLES if t not in have])
    artist = S.rng.choice(s["songs"])["artist"]
    set_player(S, None)
    S.open("music")
    return Spec(request=say(S.rng, f"Play the song “{ghost}” from my library.", f"Put on “{ghost}” by {artist}."),
                steps=[], kind="infeasible", check=unchanged)
