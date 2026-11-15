"""Media editors: video timelines with tool palettes, inspectors, and an audio workstation."""
from ..ui import esc, CHEV_D
from ..vocab import C, P

NAME = "video"
KIND = "desktop"
VARIANTS = {"premiere": "train", "simple_cut": "train", "davinci": "dev", "audio_daw": "test"}

# ---- transport ------------------------------------------------------------------------------
C("vid.play", "Play|Begin playback|Play sequence", "play|circle-play|tv-minimal-play",
  "set the footage rolling|watch the cut from the current position|run the edit from where the marker sits")
C("vid.stop", "Stop|Halt playback|Stop transport|End playback", "square|circle-stop|square-stop",
  "bring the running preview to a standstill|make the moving picture cease|end the run-through that is in progress")
C("vid.rec", "Record|Capture take|Start recording", "circle|circle-dot|disc",
  "lay down a new take from the input|capture fresh audio from the microphone|commit what comes in from the input to a new take")
C("vid.tostart", "Go to start|Jump to beginning|Return to zero", "skip-back|chevron-first|arrow-left-to-line",
  "move the marker all the way to the left|send the playhead to the very first moment|put the position indicator at the head of the timeline")
C("vid.toend", "Go to end|Jump to finish|Skip to last clip", "skip-forward|chevron-last|arrow-right-to-line",
  "move the marker all the way to the right|send the playhead past the final shot|put the position indicator at the tail of the timeline")
C("vid.prevframe", "Back one frame|Previous frame|Frame backward", "step-back|rewind|chevrons-left|chevron-first|arrow-left-to-line",
  "move a single picture earlier|nudge the playhead one image toward the beginning|go one still earlier in the footage")
C("vid.nextframe", "Forward one frame|Next frame|Frame onward", "step-forward|fast-forward|chevrons-right",
  "move a single picture later|nudge the playhead one image toward the finish|go one still later in the footage")
C("vid.loop", "Loop|Cycle range|Repeat playback", "repeat|repeat-2|infinity|refresh-ccw-dot",
  "{enable} running the same stretch over and over|turn {on} continuous replay of the marked region|{enable} going round and round the marked region")
C("vid.metro", "Metronome|Click track|Count click", "metronome|timer|alarm-clock",
  "{enable} the steady tick that keeps me in time|turn {on} the audible beat reference|{enable} the tick-tock guide while performing")
# ---- per-track controls ---------------------------------------------------------------------
C("vid.mute", "Mute|Silence track|Mute track", "volume-x|volume-off|mic-off",
  "make {o} inaudible|stop {o} from being heard|take {o} out of what I hear without deleting it", o="the selected track")
C("vid.solo", "Solo|Isolate track|Solo track", "headphones|headset|ear",
  "hear only {o} and nothing else|listen to {o} by itself|make everything except {o} go quiet", o="the selected track")
C("vid.arm", "Record arm|Arm for recording|Record enable", "mic|mic-vocal|audio-lines|circle-dot|disc",
  "get {o} ready to capture input|prime {o} for capturing a new take|set {o} to listen to the microphone for the next take", o="the selected track")
C("vid.fx", "Add effect|Insert plug-in|Add processor", "plug-zap|plug-2|sparkle|unplug",
  "put a new sound-shaping unit on {o}|load reverb, delay or similar onto {o}|drop another signal-shaping unit into the chain of {o}", o="the selected channel")
# ---- editing tools ---------------------------------------------------------------------------
C("vid.select", "Select clips|Arrow tool|Pick tool", "mouse-pointer-2|mouse-pointer|square-mouse-pointer", n="select|arrow tool|pick tool",
  intents="go back to the ordinary cursor for grabbing shots|switch to the default cursor that picks up shots|get the plain cursor for clicking on things in the timeline")
C("vid.razor", "Razor|Blade tool|Split clip", "slice|scissors|square-scissors",
  "chop a shot into two pieces where I click|divide a piece of footage at a chosen point|slice a shot in two at the cursor")
C("vid.ripple", "Ripple edit|Ripple trim|Rolling trim", "between-horizontal-start|arrow-left-right|fold-horizontal|unfold-horizontal",
  "shorten a shot so everything after it slides along|pull an edit point while later footage shifts to follow|tighten a shot and close the gap automatically")
C("vid.slip", "Slip tool|Slip edit|Slide contents", "arrow-right-left|chevrons-left-right|chevrons-right-left",
  "change which part of the source shows without moving the shot|shift a shot's content inside its fixed slot|move the in and out points of the source together")
C("vid.title", "Title tool|Add caption|Text overlay", "captions|subtitles|letter-text|a-large-small",
  "put lettering over the picture|lay words on top of the footage|add on-screen wording to the video")
C("vid.marker", "Add marker|Mark position|Drop flag", "flag|flag-triangle-right|map-pin|flag-triangle-left|map-pinned",
  "leave a reference point at the current time|tag this moment so I can find it again|pin a reminder at the playhead")
C("vid.snap", "Snap|Snapping|Magnetic timeline", "magnet|grid-2x2-check|crosshair",
  "{enable} shots jumping to nearby edit points as I drag|turn {on} the pull toward cuts while dragging|{enable} automatic sticking of shots to neighbouring edges")
C("vid.import", "Import media|Add footage|Bring in files", "folder-plus|import|file-video",
  "load source material from disk into the project|pull recordings from my computer into the bin|get new source material into this project")
C("vid.keyframe", "Add keyframe|Set keyframe|Keyframe", "diamond|gem|milestone|diamond-plus",
  "pin the current value of {o} at this moment so it can animate|store the value of {o} at the playhead for animation|make {o} begin changing over time from this instant", o="this parameter")
C("vid.reset", "Reset parameter|Revert value|Default value", "undo-dot|iteration-ccw|timer-reset",
  "put {o} back to its factory number|return {o} to where it was before I touched it|zero out my adjustment to {o}", o="this parameter")

SELECTS = P("vid.sel", [
    ("Aspect ratio", "choose between widescreen, square and vertical framing"), ("Playback resolution", "lower the preview quality so it runs smoothly"),
    ("Frame rate", "choose how many pictures per second the project uses"), ("Transition", "pick how one shot changes into the next"),
    ("Composite mode", "choose how this shot mixes with the one below"), ("Timecode format", "switch between drop-frame, feet and plain counters"),
    ("Viewer fit", "choose how much the preview monitor is magnified"), ("Codec", "pick the compression used for delivery"),
    ("Track height", "make the lanes taller or shorter"), ("Bit depth", "choose 16, 24 or 32-bit audio"),
    ("Look preset", "apply a ready-made color treatment"), ("Retime", "choose a faster or slower running rate for the shot"),
    ("Stabilization", "pick the method used to steady shaky footage"), ("Scaling", "decide how a shot of the wrong dimensions is fitted"),
    ("Render quality", "trade preview fidelity for responsiveness"), ("Audio channels", "choose mono, stereo or surround"),
    ("Proxy mode", "switch between lightweight stand-ins and original files"), ("Quantize", "choose the note grid that performances lock to"),
    ("Input source", "pick which interface channel feeds the track"), ("Automation mode", "choose read, write, touch or latch for fader moves"),
])
OPTIONS = {
    "Aspect ratio": ["16:9", "9:16", "1:1", "4:3", "2.39:1"], "Playback resolution": ["Full", "1/2", "1/4", "1/8"], "Frame rate": ["23.976", "24", "25", "29.97", "60"],
    "Transition": ["Cross dissolve", "Dip to black", "Wipe", "Push", "None"], "Composite mode": ["Normal", "Add", "Multiply", "Screen", "Overlay"],
    "Timecode format": ["Timecode", "Frames", "Feet + frames", "Seconds"], "Viewer fit": ["Fit", "25%", "50%", "100%", "200%"], "Codec": ["H.264", "H.265", "ProRes 422", "DNxHR", "AV1"],
    "Track height": ["Mini", "Small", "Medium", "Large"], "Bit depth": ["16-bit", "24-bit", "32-bit float"], "Look preset": ["None", "Warm film", "Teal and orange", "Bleach bypass", "Mono"],
    "Retime": ["25%", "50%", "100%", "200%", "Reverse"], "Stabilization": ["Off", "Perspective", "Similarity", "Translation"], "Scaling": ["Crop", "Fit", "Fill", "Stretch"],
    "Render quality": ["Draft", "Better", "Best"], "Audio channels": ["Mono", "Stereo", "5.1", "Adaptive"], "Proxy mode": ["Original", "Half proxy", "Quarter proxy"],
    "Quantize": ["Off", "1/4", "1/8", "1/16", "1/16 triplet"], "Input source": ["Input 1", "Input 2", "Input 1+2", "Bus A"], "Automation mode": ["Read", "Touch", "Latch", "Write", "Off"],
}
CLIPMENU = P("vid.cm", [
    ("Speed and duration", "make the shot run faster or slower"), ("Detach audio", "separate the sound from its picture"),
    ("Freeze frame", "hold on a single still image"), ("Reverse clip", "make the shot run backwards"),
    ("Nest", "collapse the chosen shots into one container"), ("Replace footage", "swap the source file behind this shot"),
    ("Stabilize", "smooth out camera shake"), ("Color match", "make this shot's look agree with another"),
    ("Normalize loudness", "bring the level to a broadcast standard"), ("Render in place", "bake the effects into a new file"),
    ("Add transition", "fade between this shot and its neighbour"), ("Scale to frame size", "fit the picture to the project dimensions"),
    ("Reveal in bin", "find the source of this shot in the project list"), ("Ripple delete", "take the shot out and close the gap it leaves"),
    ("Match frame", "bring up the source at exactly this image"), ("Add to render queue", "line this up for background output"),
    ("Unlink", "let the sound and picture move independently"), ("Disable", "leave the shot in place but stop it showing"),
    ("Bounce to audio", "print the track to a new sound file"), ("Consolidate", "glue the chosen regions into one"),
    ("Fade in", "ramp the level up at the beginning"), ("Crossfade", "blend the end of one region into the next"),
])
PAGES = ["Media", "Assembly", "Editing", "Fusion", "Color", "Fairlight", "Deliver", "Graphics", "Audio", "Review", "Captions", "Publish",
         "Ingest", "Titles", "Grade", "Mix", "Render", "Library", "Learning", "Motion", "Sound", "Finishing", "Metadata", "Inspector", "Mixer",
         "Media pool", "Effects library", "Edit index", "Sound library", "Scopes", "Project", "Info", "Markers", "Browser", "Arrange", "Piano roll",
         "Sampler", "Devices", "Automation", "Loops", "Transitions", "Generators", "Stickers", "Templates", "Voiceover", "Music", "Stock footage",
         "Presets", "Instruments", "Samples", "Plug-ins", "Clips", "Takes", "Notes", "Lyrics", "Tempo map", "Video", "Image", "Speed", "Animation",
         "Tracking", "Masks", "Keying", "Subtitles", "Chapters", "Queue", "History log", "Shared", "Favorites", "Recents"]
VPROPS = ["Scale", "Position X", "Position Y", "Rotation", "Anchor X", "Opacity", "Crop left", "Crop right", "Speed", "Volume", "Pan", "Pitch",
          "Exposure", "Contrast", "Saturation", "Temperature", "Tint", "Highlights", "Shadows", "Sharpen", "Vignette", "Blur", "Gain", "Fade in length",
          "Fade out length", "Zoom", "Roll", "Feather", "Brightness", "Vibrance", "Hue shift", "Noise reduction", "Smoothness", "Echo", "Reverb", "Bass",
          "Treble", "Stereo width", "Depth", "Threshold", "Ratio", "Attack", "Release", "Dry/wet", "Clarity", "Grain", "Black point", "White point", "Gamma", "Lift"]
CLIP_BASES = ["Interview", "B-roll", "Drone", "Title card", "Lower third", "Logo sting", "Voiceover", "Room tone", "Music bed", "Cutaway",
              "Establishing", "Close-up", "Reaction", "Slate", "Timelapse", "Screen rec", "Product spin", "End card", "Whoosh", "Crowd", "Montage",
              "Kitchen", "Street", "Sunset", "Handheld", "Graphics", "Podium", "Aerial", "Macro", "Gimbal", "Pickup", "Narration", "Foley", "Rain",
              "Applause", "Piano", "Riser", "Car pass", "Ambience", "Tutorial", "Outro", "Blooper", "Studio", "Guest", "Host"]
CLIP_SUFFIX = ["take 1", "take 2", "take 3", "alt", "wide", "tight", "B-cam", "v2", "trim", "slow-mo", "01", "02", "03"]
TRACKS = ["Kick", "Snare", "Hi-hat", "Bass", "Lead vocal", "Backing vocals", "Rhythm guitar", "Lead guitar", "Piano", "Strings", "Synth pad", "Drum bus",
          "Percussion", "Organ", "Brass", "Claps", "Toms", "Overheads", "Room mics", "Acoustic guitar", "Sub bass", "Arp", "FX riser", "Vocal double",
          "Choir", "Cello", "Violin", "Flute", "Sax", "Trumpet", "Rhodes", "Pluck", "Bell", "Shaker", "Tambourine", "Harmonica", "Banjo", "Vocoder",
          "Timpani", "Glockenspiel", "Marimba", "Clav", "Mellotron", "Dialogue", "Narration"]
DAWF = ["Tempo", "Signature", "Key", "Swing", "Count-in", "Pre-roll", "Punch in", "Punch out", "Bars", "Tuning", "Latency", "Buffer", "Sample rate",
        "Locator L", "Locator R", "Nudge", "Grid", "Length", "Transpose", "Velocity"]
PROJECTS = ["Summer campaign cut", "Wedding highlights", "Product launch film", "Podcast episode 41", "Documentary rough cut", "Travel vlog Lisbon",
            "Conference recap", "Music video v3", "Tutorial series", "Trailer 30s", "Album demo", "Short film final", "Showreel 2026", "Interview series", "Game capture"]

CSS = """
.vid-mon{background:#0a0a0c;position:relative;overflow:hidden;container-type:size}
.vid-pic{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:min(94cqw,calc(88cqh * 16 / 9));aspect-ratio:16/9;overflow:hidden}
.vid-pic div{position:absolute}
.vid-tc{font-family:var(--mono);color:var(--ac);white-space:nowrap}
.vid-rul{height:20px;flex:none;position:relative;overflow:hidden;background-color:var(--bg1);background-image:repeating-linear-gradient(90deg,var(--bd2) 0 1px,transparent 1px 12px),repeating-linear-gradient(90deg,var(--fg2) 0 1px,transparent 1px 120px);background-size:auto 5px,auto 10px;background-repeat:repeat-x;background-position:0 100%;border-bottom:1px solid var(--bd);font-size:9.5px;color:var(--fg2)}
.vid-rul span{position:absolute;top:1px;white-space:nowrap}
.vid-lane{position:relative;flex:none;border-bottom:1px solid var(--bd);background:var(--bg1);overflow:hidden}
.vid-clip{position:absolute;top:2px;bottom:2px;border-radius:3px;overflow:hidden;font-size:10.5px;line-height:1.3;color:#fff;padding:1px 5px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.4);display:flex;flex-direction:column}
.vid-clip.sel{box-shadow:inset 0 0 0 2px #fff}
.vid-hd{flex:none;display:flex;align-items:center;gap:2px;padding:0 4px 0 8px;border-bottom:1px solid var(--bd);border-right:1px solid var(--bd);background:var(--bg2);font-size:.92em;white-space:nowrap}
.vid-ph{position:absolute;top:0;bottom:0;width:1px;background:var(--err);z-index:5}
.vid-ph::before{content:"";position:absolute;left:-5px;top:0;border:5px solid transparent;border-top:8px solid var(--err)}
.vid-msr{width:19px;height:17px;border-radius:3px;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;background:var(--bg4);color:var(--fg1);flex:none}
.vid-msr.on{background:var(--warn);color:#111}
.vid-meter{width:5px;border-radius:2px;background:linear-gradient(0deg,#3fb950 0 62%,#d29922 62% 86%,#f85149 86%);align-self:flex-end}
.vid-fader{position:relative;width:24px;flex:none}
.vid-fader::before{content:"";position:absolute;left:10px;top:0;bottom:0;width:4px;border-radius:2px;background:var(--bg4)}
.vid-fader i{position:absolute;left:2px;width:20px;height:11px;border-radius:2px;background:var(--fg1);box-shadow:0 1px 2px rgba(0,0,0,.4)}
.vid-strip{flex:none;display:flex;flex-direction:column;align-items:center;gap:5px;padding:6px 4px;border-right:1px solid var(--bd);font-size:10.5px}
.vid-knob{width:20px;height:20px;border-radius:50%;border:2px solid var(--fg2);position:relative;flex:none}
.vid-knob::after{content:"";position:absolute;left:7px;top:1px;width:2px;height:7px;background:var(--fg)}
.vid-cell{display:flex;flex-direction:column;gap:3px;font-size:.88em;min-width:0}
.vid-film{display:flex;flex:none;border-radius:5px;overflow:hidden;position:relative;box-shadow:inset 0 0 0 1px rgba(0,0,0,.4)}
.vid-film b{position:absolute;left:5px;top:3px;font-size:10.5px;font-weight:600;color:#fff;text-shadow:0 1px 2px #000;white-space:nowrap}
.vid-ptab{display:flex;flex-direction:column;align-items:center;gap:2px;padding:4px 14px;font-size:.85em;color:var(--fg1);white-space:nowrap}
.vid-ptab.on{color:var(--fg);box-shadow:inset 0 2px 0 var(--ac)}
"""
_TONES = ["#3b6fb5", "#3f8f6b", "#8a5fb8", "#b0703a", "#3a8f9c", "#a04a6a", "#6f7f2f", "#5560b8"]


def _wave(rng, n=46):
    d = "".join(f"M{i * 100 / n:.1f} {10 - h:.1f}V{10 + h:.1f}" for i, h in ((i, rng.uniform(0.8, 9)) for i in range(n)))
    return (f'<svg viewBox="0 0 100 20" preserveAspectRatio="none" style="width:100%;flex:1 1 0;min-height:0;display:block">'
            f'<path d="{d}" stroke="rgba(255,255,255,.62)" stroke-width="1" vector-effect="non-scaling-stroke" fill="none"/></svg>')


def _scene(ctx):
    """A stand-in video frame: sky, sun, hills and a lower-third bar."""
    rng, d = ctx.rng, ctx.d
    sky, sky2, land, bar = d.color(), d.color(), rng.choice(["#1d2b24", "#2a2118", "#18222e", "#262026"]), d.color()
    return (f'<div class="vid-pic" style="background:linear-gradient(180deg,{sky},{sky2} 64%,{land} 64%,#0c0c0e)">'
            f'<div style="left:{rng.randint(12, 78)}%;top:{rng.randint(10, 36)}%;width:9%;aspect-ratio:1;border-radius:50%;background:rgba(255,244,214,.9)"></div>'
            f'<div style="left:-8%;bottom:30%;width:{rng.randint(45, 70)}%;height:26%;border-radius:50% 50% 0 0;background:{land}"></div>'
            f'<div style="right:-12%;bottom:32%;width:{rng.randint(40, 62)}%;height:{rng.randint(14, 22)}%;border-radius:50% 50% 0 0;background:{land};opacity:.8"></div>'
            f'<div style="left:7%;bottom:9%;width:34%;height:7%;background:{bar};opacity:.9"></div>'
            f'<div style="left:7%;bottom:17%;width:22%;height:3.5%;background:#fff;opacity:.85"></div></div>')


def _tc(rng):
    return f"{rng.randint(0, 1):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 23):02d}"


def _transport(ctx, region, extra=(), cls=""):
    order = ["vid.tostart", "vid.prevframe", "vid.play", "vid.nextframe", "vid.toend", "vid.loop"]
    if extra:
        order = list(extra) + order
    out = []
    for cid in order:
        kw = {"state": ctx.rng.random() < 0.4} if cid in ("vid.loop", "vid.metro") else {}
        out.append(ctx.ibtn(cid, region, cls=("l " if cid == "vid.play" else "") + cls, on=kw.get("state", False), **kw))
    return "".join(out)


def _monitor(ctx, region, caption, sel=None):
    rng = ctx.rng
    pic = _scene(ctx)
    head = f'<div class="row g8 px8" style="height:calc(var(--rh) + 2px);flex:none"><span class="m sm mut">{esc(caption)}</span><div class="sp"></div>{sel or ""}</div>'
    bar = (f'<div class="row g4 px8 bt" style="height:calc(var(--ibs) + 14px);flex:none"><span class="vid-tc">{_tc(rng)}</span><div class="sp"></div>{_transport(ctx, region)}'
           f'<div class="sp"></div>{ctx.ibtn("vid.marker", region, cls="s")}{ctx.ibtn("fullscreen", region, cls="s")}<span class="vid-tc mut">{_tc(rng)}</span></div>')
    return f'<div class="col f1 br">{head}<div class="vid-mon f1">{pic}</div>{bar}</div>'


def _lane(ctx, names, region, h, audio, tone, noun="clip"):
    """One track lane filled left to right with clips taken from `names` (a list that is consumed)."""
    rng = ctx.rng
    x, out, sel = rng.uniform(0, 6), [], rng.random() < 0.25
    while x < 96 and names:
        w = rng.uniform(9, 24)
        name = names.pop()
        attr = ctx.reg("row", noun, name, region=region, anchor="row")
        body = _wave(rng) if audio else ""
        out.append(f'<div class="vid-clip{" sel" if sel else ""}"{attr} style="left:{x:.1f}%;width:{w:.1f}%;background:{tone}"><span class="el">{esc(name)}</span>{body}</div>')
        sel = False
        x += w + (0 if rng.random() < 0.6 else rng.uniform(1, 7))
    return f'<div class="vid-lane" style="height:{h}px">{"".join(out)}</div>'


def _ruler(rng, step=10):
    marks = "".join(f'<span style="left:calc({k * step}% + 3px)">00:{k * 5:02d}:00</span>' for k in range(0, 100 // step))
    return f'<div class="vid-rul">{marks}</div>'


def _timeline(ctx, region, tracks, lane_h, head_w, clips, bar=""):
    """tracks: list of (name, is_audio, header_html)."""
    rng = ctx.rng
    heads, lanes = [], []
    for i, (name, audio, head) in enumerate(tracks):
        heads.append(f'<div class="vid-hd" style="height:{lane_h}px">{head}</div>')
        lanes.append(_lane(ctx, clips, region, lane_h, audio, _TONES[(i + (4 if audio else 0)) % len(_TONES)]))
    ph = f'<div class="vid-ph" style="left:{rng.uniform(12, 70):.1f}%"></div>'
    return (f'<div class="col f1 clip">{bar}<div class="row str f1 clip"><div class="col fn" style="width:{head_w}px"><div class="vid-hd" style="height:20px"><span class="vid-tc xs">{_tc(rng)}</span></div>'
            f'{"".join(heads)}</div><div class="col f1 rel clip">{_ruler(rng)}{"".join(lanes)}{ph}</div></div></div>')


def _head(ctx, name, audio, region):
    obj = f"the {name} track"
    icons_ = ctx.ibtn("lock", region, row=obj, obj=obj, cls="s")
    if audio:
        icons_ += ctx.ibtn("vid.mute", region, row=obj, obj=obj, cls="s") + ctx.ibtn("vid.solo", region, row=obj, obj=obj, cls="s")
    else:
        icons_ += ctx.ibtn("hide", region, row=obj, obj=obj, cls="s")
    return f'<span class="b" style="width:24px">{esc(name)}</span><div class="sp"></div>{icons_}'


def _msr(ctx, letter, cid, track, region, on=False):
    word = {"M": "mute", "S": "solo", "R": "record arm"}[letter]
    attr = ctx.reg("button", "button", f"{word.capitalize()} {track}", ui="icon", cid=cid, region=region, row=f"the {track} track", obj=f"the {track} track",
                   refs=[f"the {letter} button on the {track} track", f"the {word} button for the {track} track", f"the {track} track's {letter} button"])
    return f'<div class="vid-msr{" on" if on else ""}"{attr}>{letter}</div>'


def _sel(ctx, cid, region, mode="in"):
    label = ctx.lab(cid)
    opts = OPTIONS[label]
    attr = ctx.reg("select", "dropdown", label, cid=cid, region=region, anchor="select")
    tid = ctx.last
    ctx.options[tid] = list(opts)
    val = esc(ctx.rng.choice(opts))
    if mode == "in":
        return (f'<div class="inp fn" {attr} style="height:calc(var(--ch) - 2px);font-size:.92em"><span class="fnt">{esc(label)}</span>'
                f'<span class="nw">{val}</span>{CHEV_D}</div>')
    box = f'<div class="inp f1"{attr} style="height:calc(var(--ch) - 2px)"><span class="el f1">{val}</span>{CHEV_D}</div>'
    return f'<div class="row g8"><span class="mut sm nw" data-o="{tid}" style="width:110px">{esc(label)}</span>{box}</div>'


def _params(ctx, region, names, keyf=True):
    """Inspector rows: caption, slider, value, optional keyframe and reset icons."""
    rng, rows = ctx.rng, []
    for name in names:
        sl = ctx.slider(name, rng.uniform(0.1, 0.9), region=region)
        cap = ctx.own(name, "sm nw")
        tail = ""
        if keyf:
            tail = ctx.ibtn("vid.keyframe", region, row=name, obj=name.lower(), cls="s") + ctx.ibtn("vid.reset", region, row=name, obj=name.lower(), cls="s")
        val = rng.choice([f"{rng.uniform(-100, 100):.1f}", f"{rng.randint(0, 200)}", f"{rng.uniform(0, 2):.2f}"])
        rows.append(f'<div class="row g8" style="height:var(--rh);flex:none"><div style="width:118px;flex:none" class="nw">{cap}</div>{sl}'
                    f'<span class="mono xs mut rt" style="width:44px;flex:none">{val}</span>{tail}</div>')
    return "".join(rows)


def _bin_rows(ctx, region, names, grid=False, cols=3):
    rng, d = ctx.rng, ctx.d
    out = []
    for name in names:
        attr = ctx.reg("row", rng.choice(["clip", "media item"]) if not grid else "thumbnail", name, region=region, anchor="row")
        dur = f"{rng.randint(0, 9):02d}:{rng.randint(0, 59):02d}"
        if grid:
            out.append(f'<div class="vid-cell"{attr}><div class="thumb" style="width:100%;aspect-ratio:16/9;--c1:{d.color()};--c2:#15151a"></div><span class="el">{esc(name)}</span></div>')
        else:
            out.append(f'<div class="li"{attr} style="font-size:.94em"><div class="thumb" style="width:30px;height:18px;border-radius:2px;--c1:{d.color()};--c2:#15151a"></div>'
                       f'<span class="el f1">{esc(name)}</span><span class="mono xs mut">{dur}</span></div>')
    if grid:
        return f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:10px 8px;padding:8px">{"".join(out)}</div>'
    return "".join(out)


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    big = H >= 1000
    proj = d.one("vid.projects", PROJECTS)
    clips = [f"{b} {x}" for b in d.take("vid.clips", CLIP_BASES) for x in rng.sample(CLIP_SUFFIX, 4)]
    rng.shuffle(clips)
    media = d.files("media", 6 + (4 if big else 0)) + d.files("image", 3)
    allp = d.take("vid.pages", PAGES)
    pages, more = allp[:7], allp[7:]
    sels = ctx.pick(SELECTS, 5)
    rng.shuffle(sels)
    props = d.take("vid.props", VPROPS)
    cm = ctx.pick(CLIPMENU, 7)
    ctx.menus.update({"mb.clip": ctx.avail(CLIPMENU)[:12] + ["-", "rename", "duplicate", "delete"],
                      "mb.sequence": ["vid.marker", "vid.snap", "-", "zoomin", "zoomout", "-"] + cm[:5]})
    ctx.ctxmenu = ["cut", "copy", "paste", "-"] + cm + ["-", "rename", "delete"]
    ctx.ctxobj = "the selected clip"
    lane = 34 if H < 900 else (40 if H < 1200 else 46)
    title = f"{proj} — {rng.choice(['Edit', 'Timeline 1', 'Main sequence', 'Rough cut'])}"
    menus = ["mb.file", "mb.edit", "mb.clip", "mb.sequence", "mb.view", "mb.window", "mb.help"]
    tl = "the timeline"

    if variant == "premiere":
        ws = ctx.tabs(pages[:6], active=rng.randint(0, 3), region="the workspace bar", cls="pl")
        top = f'<div class="row bb bg2">{ctx.ibtn("home", "the workspace bar")}{ws}<div class="sp"></div>{ctx.ibtn("vid.import", "the workspace bar")}{ctx.tbtn("export", "the workspace bar", cls="sm pri")}<div style="width:8px"></div></div>'
        bn = "the project bin"
        binbar = (f'<div class="row g2 bt" style="padding:3px 6px;flex:none">{ctx.ibtn("view.list", bn, cls="s", on=True)}{ctx.ibtn("view.grid", bn, cls="s")}{ctx.slider("Thumbnail size", 0.4, region=bn, w=70)}'
                  f'<div class="sp"></div>{ctx.ibtn("search", bn, cls="s", noun="button")}{ctx.ibtn("new", bn, cls="s", obj="a new bin")}{ctx.ibtn("delete", bn, cls="s", obj="the selected media")}</div>')
        bin_ = (f'<div class="side br" style="width:{int(W * 0.24)}px">{ctx.tabs(pages[6:7] + [f"Bin: {proj.split()[0]}"], active=1, region=bn)}'
                f'<div class="p6">{ctx.field("Filter bin", "", ph="Filter bin content", region=bn, above=False, cls="soft")}</div><div class="col f1 clip">{_bin_rows(ctx, bn, media)}</div>{binbar}</div>')
        mons = _monitor(ctx, "the source monitor", "Source: " + media[0], _sel(ctx, sels[0], "the source monitor") if sels else "")
        mons += _monitor(ctx, "the program monitor", "Program", _sel(ctx, sels[1], "the program monitor") if len(sels) > 1 else "") if W >= 1500 else ""
        tp = "the tool palette"
        tools = "".join(ctx.ibtn(c, tp, on=i == 0) for i, c in enumerate(["vid.select", "vid.ripple", "vid.razor", "vid.slip", "vid.title", "vid.marker", "zoomin"]))
        pal = f'<div class="rail br" style="gap:2px;padding:6px 0">{tools}</div>'
        nv, na = (3, 3) if big else (2, 2)
        tracks = [(f"V{i}", False, _head(ctx, f"V{i}", False, tl)) for i in range(nv, 0, -1)] + [(f"A{i}", True, _head(ctx, f"A{i}", True, tl)) for i in range(1, na + 1)]
        tbar = (f'<div class="row g4 px8 bb bg1" style="height:calc(var(--ibs) + 6px);flex:none"><span class="b sm">{esc(proj)}</span><div class="sp"></div>{ctx.ibtn("vid.snap", tl, cls="s", state=True, on=True)}'
                f'{ctx.ibtn("settings", tl, cls="s")}{ctx.ibtn("zoomout", tl, cls="s")}{ctx.slider("Timeline zoom", rng.uniform(0.2, 0.8), region=tl, w=90)}</div>')
        meters = f'<div class="row g2 bl p6" style="flex:none;align-items:stretch"><div class="vid-meter" style="height:{rng.randint(40, 90)}%"></div><div class="vid-meter" style="height:{rng.randint(40, 90)}%"></div></div>'
        low = f'<div class="row str bt" style="height:{20 + (nv + na) * lane + 34}px;flex:none">{pal}{_timeline(ctx, tl, tracks, lane, 118, clips, tbar)}{meters}</div>'
        body = f'<div class="col f1">{top}<div class="row str f1">{bin_}{mons}</div>{low}</div>'
    elif variant == "simple_cut":
        tb = "the toolbar"
        top = (f'<div class="tb" style="height:46px">{ctx.tbtn("vid.import", tb, icon=True)}{ctx.ibtn("undo", tb)}{ctx.ibtn("redo", tb)}<div class="sp"></div><span class="b">{esc(proj)}</span><div class="sp"></div>'
               f'{_sel(ctx, sels[0], tb) if sels else ""}{ctx.ibtn("help", tb)}{ctx.tbtn("share", tb, icon=True)}{ctx.tbtn("export", tb, cls="pri")}</div>')
        lib = "the media library"
        libtabs = ctx.tabs(pages[:3], active=0, region=lib)
        left = f'<div class="side br" style="width:{int(W * 0.22)}px">{libtabs}<div class="p8">{ctx.search(lib, cls="soft")}</div><div class="col f1 clip">{_bin_rows(ctx, lib, media, grid=True, cols=2)}</div></div>'
        adj = "the adjustments panel"
        atabs = ctx.tabs(pages[3:6], active=0, region=adj)
        n = 7 + (5 if big else 0)
        right = (f'<div class="side bl" style="width:{int(W * 0.21)}px">{atabs}<div class="col p12 g4 f1 clip">{_params(ctx, adj, props[:n], keyf=False)}'
                 f'<div class="col g8" style="margin-top:10px">{"".join(_sel(ctx, c, adj, "left") for c in sels[1:4])}</div>'
                 f'<div class="row g8" style="margin-top:12px">{ctx.tbtn("clear", adj, cls="sm")}<div class="sp"></div>{ctx.tbtn("save", adj, cls="sm pri")}</div></div></div>')
        mon = "the preview"
        pic = _scene(ctx)
        bar = (f'<div class="row g6 cen" style="height:50px;flex:none"><span class="vid-tc">{_tc(rng)}</span><div style="width:16px"></div>{_transport(ctx, mon)}<div style="width:16px"></div>'
               f'{ctx.ibtn("vid.mute", mon, obj="the preview sound")}{ctx.slider("Preview volume", rng.uniform(0.3, 0.9), region=mon, w=90)}{ctx.ibtn("fullscreen", mon)}</div>')
        center = f'<div class="col f1"><div class="vid-mon f1">{pic}</div>{bar}</div>'
        st = "the clip strip"
        sbar = (f'<div class="row g4 px12" style="height:38px;flex:none">{ctx.ibtn("vid.razor", st)}{ctx.ibtn("delete", st, obj="the selected clip")}{ctx.ibtn("duplicate", st, obj="the selected clip")}{ctx.ibtn("vid.title", st)}'
                f'{ctx.ibtn("vid.marker", st)}<div class="sp"></div>{ctx.ibtn("vid.snap", st, state=False)}{ctx.ibtn("zoomout", st)}{ctx.slider("Strip zoom", 0.5, region=st, w=110)}{ctx.ibtn("zoomin", st)}</div>')
        film, fh = [], 64 if H < 1000 else 84
        for name in clips[:(6 if W < 1600 else 9)]:
            attr = ctx.reg("row", "clip", name, region=st, anchor="row")
            fw = rng.randint(120, 240)
            c1, c2 = d.color(), d.color()
            frames = "".join(f'<div style="flex:1;background:linear-gradient({a}deg,{c1},{c2});border-right:1px solid rgba(0,0,0,.35)"></div>' for a in (120, 150, 200, 240)[:max(2, fw // 60)])
            film.append(f'<div class="vid-film"{attr} style="width:{fw}px;height:{fh}px">{frames}<b>{esc(name)}</b></div>')
        audio = f'<div class="vid-lane" style="height:30px;border:none;border-radius:5px;margin:0 12px"><div class="vid-clip" style="left:0;width:86%;background:{_TONES[5]}">{_wave(rng, 160)}</div></div>'
        strip = f'<div class="col bt bg1" style="flex:none;padding-bottom:12px">{sbar}<div class="row g4 clip" style="padding:0 12px 8px">{"".join(film)}</div>{audio}</div>'
        body = f'<div class="col f1">{top}<div class="row str f1">{left}{center}{right}</div>{strip}</div>'
        menus = ["mb.file", "mb.edit", "mb.clip", "mb.view", "mb.window", "mb.help"]
    elif variant == "davinci":
        hb = "the top bar"
        togl = "".join(ctx.lbtn(p, hb, cls="ghost sm", icon_html=ctx.deco("panel-left", "layout-panel-left", "gallery-vertical", "panels-top-left", "library", "folder-open", size=14)) for p in pages[:3])
        togr = "".join(ctx.lbtn(p, hb, cls="ghost sm", icon_html=ctx.deco("sliders-vertical", "panel-right", "layout-panel-top", "gauge", "list", "info", size=14)) for p in pages[3:5])
        top = f'<div class="row g4 px8 bb bg2" style="height:calc(var(--ch) + 10px);flex:none">{togl}<div class="sp"></div><span class="b">{esc(proj)}</span><span class="mut sm" style="margin-left:8px">Edited</span><div class="sp"></div>{togr}</div>'
        mp = "the media pool"
        pool = (f'<div class="side br" style="width:{int(W * 0.25)}px"><div class="row g4 p6 bb">{ctx.ibtn("view.grid", mp, cls="s", on=True)}{ctx.ibtn("view.list", mp, cls="s")}{ctx.ibtn("sort", mp, cls="s")}'
                f'<div class="f1">{ctx.search(mp, cls="soft")}</div>{ctx.ibtn("more", mp, cls="s", anchor="more")}</div><div class="col f1 clip">{_bin_rows(ctx, mp, media, grid=True, cols=3 if W >= 1700 else 2)}</div></div>')
        viewer = _monitor(ctx, "the viewer", "Timeline 1", _sel(ctx, sels[0], "the viewer") if sels else "")
        ins = "the inspector"
        itabs = ctx.tabs(pages[5:7] + more[:2], active=0, region=ins)
        n = 6 + (6 if big else 0)
        half = n // 2
        inspector = (f'<div class="side bl" style="width:{int(W * 0.24)}px">{itabs}<div class="col p8 f1 clip"><div class="row" style="height:var(--rh)"><span class="b sm sp">Transform</span>'
                     f'{ctx.toggle("Transform section", True, region=ins)}</div>{_params(ctx, ins, props[:half])}<div class="hsep" style="margin:6px 0"></div>'
                     f'<div class="row" style="height:var(--rh)"><span class="b sm sp">Compositing</span></div>{_params(ctx, ins, props[half:n])}'
                     f'<div class="col g6" style="margin-top:8px">{"".join(_sel(ctx, c, ins, "left") for c in sels[1:4])}</div></div></div>')
        tools = "".join(ctx.ibtn(c, "the timeline toolbar", on=i == 0, cls="s") for i, c in enumerate(["vid.select", "vid.ripple", "vid.razor", "vid.slip", "vid.title"]))
        tbar = (f'<div class="row g2 px8 bb bg1" style="height:calc(var(--ibs) + 6px);flex:none"><span class="vid-tc" style="font-size:1.25em;margin-right:12px">{_tc(rng)}</span>{tools}<div class="vsep"></div>'
                f'{ctx.ibtn("vid.snap", "the timeline toolbar", cls="s", state=True, on=True)}{ctx.ibtn("link", "the timeline toolbar", cls="s", obj="the clip")}{ctx.ibtn("vid.marker", "the timeline toolbar", cls="s")}'
                f'<div class="sp"></div>{ctx.ibtn("zoomout", "the timeline toolbar", cls="s")}{ctx.slider("Lane zoom", rng.uniform(0.2, 0.8), region="the timeline toolbar", w=110)}{ctx.ibtn("zoomin", "the timeline toolbar", cls="s")}'
                f'<div class="vsep"></div>{ctx.deco("volume-2", "volume-1", "volume", "speaker", size=14)}{ctx.slider("Monitor volume", rng.uniform(0.3, 0.9), region="the timeline toolbar", w=70)}</div>')
        nv, na = (3, 4) if big else (2, 2)
        tracks = [(f"V{i}", False, _head(ctx, f"V{i}", False, tl)) for i in range(nv, 0, -1)] + [(f"A{i}", True, _head(ctx, f"A{i}", True, tl)) for i in range(1, na + 1)]
        low = f'<div class="row str bt" style="height:{20 + (nv + na) * lane + 36}px;flex:none">{_timeline(ctx, tl, tracks, lane, 126, clips, tbar)}</div>'
        pb = "the page bar"
        ptabs = []
        for i, p in enumerate(more[2:8]):
            attr = ctx.reg("tab", "page", p, region=pb)
            ico = ctx.deco_any(["film", "scissors", "clapperboard", "sparkles", "palette", "music", "rocket", "image", "layers", "captions", "audio-lines", "wand"], size=18)
            ptabs.append(f'<div class="vid-ptab{" on" if i == 2 else ""}"{attr}>{ico}<span>{esc(p)}</span></div>')
        pagebar = f'<div class="row bt bg2" style="flex:none"><div style="width:12px"></div><span class="mut sm">{esc(rng.choice(["Studio 19", "Cutroom 4", "Editor Pro"]))}</span><div class="sp"></div>{"".join(ptabs)}<div class="sp"></div>{ctx.ibtn("home", pb)}{ctx.ibtn("settings", pb)}<div style="width:8px"></div></div>'
        body = f'<div class="col f1">{top}<div class="row str f1">{pool}{viewer}{inspector}</div>{low}{pagebar}</div>'
        menus = ["mb.file", "mb.edit", "mb.clip", "mb.sequence", "mb.view", "mb.window", "mb.help"]
    else:  # audio_daw
        tr = "the transport bar"
        fields = "".join(_dfield(ctx, n, v, tr) for n, v in zip(d.take("vid.dawf", DAWF, 4), [f"{rng.randint(70, 174)}.00", "4/4", "A min", "1/16", "2 bars", "12 ms"]))
        top = (f'<div class="row g4 px8 bb bg2" style="height:48px;flex:none">{ctx.ibtn("sidebar.toggle", tr)}{ctx.ibtn("undo", tr)}{ctx.ibtn("redo", tr)}<div class="vsep"></div>'
               f'{_transport(ctx, tr, extra=("vid.rec", "vid.stop"))}{ctx.ibtn("vid.metro", tr, state=rng.random() < 0.5)}<div class="vsep"></div>'
               f'<div class="inp mono" style="height:30px;font-size:1.25em;padding:0 12px;color:var(--ac)">{rng.randint(1, 96)}. {rng.randint(1, 4)}. {rng.randint(1, 4)}. {rng.randint(0, 239):03d}</div>{fields}'
               f'<div class="sp"></div>{_sel(ctx, sels[0], tr) if sels else ""}<span class="xs mut">CPU</span><div class="prog" style="width:54px"><div style="width:{rng.randint(8, 70)}%"></div></div>{ctx.ibtn("settings", tr)}</div>')
        tk = "the track list"
        names = d.take("vid.tracks", TRACKS, 7 + (5 if big else 0))
        heads, lanes = [], []
        lh = lane + 8
        for i, name in enumerate(names):
            attr = ctx.reg("row", "track", name, region=tk, anchor="row")
            ico = ctx.deco_any(["drum", "guitar", "piano", "mic-vocal", "keyboard-music", "audio-waveform", "music", "speaker", "radio"], size=14)
            col = _TONES[i % len(_TONES)]
            heads.append(f'<div class="vid-hd" style="height:{lh}px;gap:4px;padding-left:0"><div style="width:5px;align-self:stretch;background:{col}"></div><span class="mut xs" style="width:14px;text-align:right">{i + 1}</span>'
                         f'{ico}<div class="el f1 m"{attr}>{esc(name)}</div>{_msr(ctx, "M", "vid.mute", name, tk, rng.random() < 0.2)}{_msr(ctx, "S", "vid.solo", name, tk, rng.random() < 0.12)}'
                         f'{_msr(ctx, "R", "vid.arm", name, tk)}</div>')
            lanes.append(_lane(ctx, [f"{name} {k}" for k in range(7, 0, -1)], "the arrangement", lh, True, col, noun="region"))
        ph = f'<div class="vid-ph" style="left:{rng.uniform(12, 70):.1f}%"></div>'
        arr = (f'<div class="row str f1 clip"><div class="col fn" style="width:{rng.choice([230, 250, 270])}px"><div class="vid-hd" style="height:20px">{ctx.ibtn("add", tk, cls="s", obj="the track list")}'
               f'<div class="sp"></div>{ctx.ibtn("filter", tk, cls="s")}</div>{"".join(heads)}</div><div class="col f1 rel clip">{_ruler(rng)}{"".join(lanes)}{ph}</div></div>')
        mx = "the mixer"
        strips = []
        fh = 96 if H < 1000 else 150
        for name in names[:max(6, min(len(names), (W - 300) // 62))]:
            fattr = ctx.reg("slider", "fader", f"{name} fader", region=mx, refs=[f"the volume fader for {name} in the mixer", f"the {name} channel fader in the mixer"])
            ftid = ctx.last
            fx = ctx.ibtn("vid.fx", mx, row=f"the {name} channel", obj=f"the {name} channel", cls="s")
            strips.append(f'<div class="vid-strip" style="width:62px">{fx}<div class="vid-knob" style="transform:rotate({rng.randint(-120, 120)}deg)"></div>'
                          f'<div class="row g4" style="height:{fh}px;align-items:stretch"><div class="vid-fader"{fattr}><i style="top:{rng.randint(10, 70)}%"></i></div><div class="vid-meter" style="height:{rng.randint(20, 95)}%"></div></div>'
                          f'<span class="mono xs mut">{rng.uniform(-18, 3):+.1f}</span><span class="el m" data-o="{ftid}" style="max-width:56px">{esc(name)}</span></div>')
        br = "the browser"
        blist = "".join(ctx.nav(p, br, noun="category", deco=("folder", "folder-closed", "folder-open", "library", "folders"), on=i == 1) for i, p in enumerate(pages[:6]))
        browser = f'<div class="side br" style="width:{rng.choice([170, 190])}px"><div class="p6">{ctx.search(br, cls="soft")}</div>{blist}<div class="sp"></div><div class="p6">{ctx.tbtn("vid.import", br, cls="sm")}</div></div>'
        mixer = f'<div class="row str bt bg1 clip" style="flex:none">{"".join(strips)}</div>'
        body = f'<div class="col f1">{top}<div class="row str f1">{browser}<div class="col f1">{arr}{mixer}</div></div></div>'
        menus = ["mb.file", "mb.edit", "mb.clip", "mb.controls", "mb.view", "mb.window", "mb.help"]
        ctx.menus["mb.controls"] = ["vid.play", "vid.stop", "vid.rec", "-", "vid.tostart", "vid.toend", "-", "vid.loop", "vid.metro"]
        ctx.ctxobj = "the selected region"
    return {"title": title, "body": body, "menus": menus, "url": "", "app": rng.choice(["Cutroom", "Reel Studio", "Framewise", "Tracksmith"]), "css": CSS}


def _dfield(ctx, label, value, region):
    attr = ctx.reg("field", "field", label, region=region)
    return (f'<div class="inp fn"{attr} style="height:30px;flex-direction:column;align-items:flex-start;justify-content:center;gap:0;padding:0 8px;line-height:1.1">'
            f'<span class="fnt" style="font-size:9px">{esc(label)}</span><span class="mono sm">{esc(value)}</span></div>')
