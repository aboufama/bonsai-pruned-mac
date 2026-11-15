"""Team chat and messaging apps."""
from ..data import CHANNELS, CHAT, COMPANIES, LOREM, PROJECTS
from ..ui import CHEV_D, esc
from ..vocab import C, P
from .email import FMT as _MAIL_FMT

FMT = [c for c in _MAIL_FMT if not c.endswith(("insert_emoji", "insert_signature"))]   # the composer has its own emoji button

NAME = "chat"
KIND = "either"
VARIANTS = {"slack": "train", "messenger": "train", "discord": "train", "support_inbox": "dev", "irc_compact": "test"}

C("chat.new", "New chat|Start a conversation|Write to someone", "message-circle-plus|message-square-diff|circle-fading-plus", "begin talking with a person I have not messaged yet|open a fresh thread with somebody|pick a person and start talking to them")
C("chat.call", "Start call|Voice call|Ring", "phone|phone-call|phone-outgoing", "talk to {o} out loud over audio|dial {o} for an audio conversation|speak with {o} live without video", o="this person")
C("chat.video", "Video call|Start video|Meet now", "video|webcam|scan-face", "see {o} face to face over the camera|start a live camera conversation with {o}|get {o} on a call with pictures", o="this person")
C("chat.mute", "Mute|Silence|Turn off alerts", "bell-off|bell-minus|volume-off", "stop getting pinged by {o}|keep {o} from making noise|quiet the pings coming from {o}", o="this conversation")
C("chat.members", "Members|Participants|Who is here", "users|user-round-check|book-user", "{show} the roster of everyone in {o}|{show} the list of who belongs to {o}|{show} the column of names in {o}", o="this channel")
C("chat.thread", "Reply in thread|Start thread|Answer in a side thread", "message-square-text|messages-square|message-square-reply", "respond to {o} in a side conversation|branch off a discussion from {o}|answer {o} without cluttering the main flow", o="this message")
C("chat.react", "Add reaction|React|Emoji response", "smile-plus|smile|laugh", "put a smiley on {o}|respond to {o} with a small face symbol|leave a thumbs-up style response on {o}", o="this message")
C("chat.save", "Save for later|Bookmark message|Keep", "bookmark|bookmark-plus|flag|bookmark-check", "set {o} aside so I can come back to it|remember {o} for later reading|store {o} in my to-read pile", o="this message")
C("chat.pinned", "Pinned messages|Pins|Pinned items list", "pin|map-pin|pin-off", "see what has been stuck to the top of {o}|look at the important posts fixed in {o}|check the posts people fastened in {o}", o="this channel")
C("chat.input", "Message|Type a message|Write something", "", "type what I want to say here|enter my next line in this conversation|key in the words I want to post")
C("chat.mention", "Mention someone|Tag a person|At-mention", "at-sign|user-round-plus|contact-round", "notify a specific colleague inside what I am writing|pull a named colleague into what I am writing|call out a teammate by name in my post")
C("chat.emoji", "Emoji|Smileys|Emoticons", "smile|laugh|sticker|meh|annoyed", "pick a little face to put in what I am writing|insert a small pictograph into my text|choose a symbol like a heart or grin for my text")
C("chat.gif", "GIF|Animations|Stickers", "image-play|clapperboard|gift", "send a looping moving picture|pick a short moving image to post|drop in a funny moving image")
C("chat.addchan", "Add channels|Browse channels|Join a channel", "", "find more rooms to join|see which other rooms exist|look for a room I am not in yet")
C("chat.invite", "Invite people|Add teammates|Bring someone in", "user-plus|user-round-plus|users-round|contact-round|handshake", "get more colleagues into {o}|bring a new person into {o}|let another person join {o}", o="this workspace")
C("chat.micmute", "Mute microphone|Mic off|Silence my mic", "mic|mic-off|mic-vocal", "stop others from hearing me|cut my own audio input|make myself inaudible to the room")
C("chat.deafen", "Deafen|Mute speakers|Stop listening", "headphones|headphone-off|ear-off", "stop hearing everyone in the voice room|cut all incoming audio from the room|make the voice room silent for me")
C("chat.screen", "Share screen|Present|Show my screen", "screen-share|monitor-up|cast", "let the others see my display|broadcast what is on my monitor|show the others what I am looking at")
C("chat.status", "Set a status|Update your status|Change availability", "", "tell others whether I am around|let colleagues know I am busy or away|post a short note about what I am doing")
C("chat.resolve", "Mark as solved|Resolve|Close ticket", "circle-check|circle-check-big|check-check", "record that this customer's problem is fixed|finish this request as dealt with|declare this case finished")
C("chat.assign", "Assign to me|Take ticket|Claim", "", "make myself the owner of this request|put this case under my name|pick this request up myself")
C("chat.note", "Internal note|Private note|Staff-only comment", "", "write something only my colleagues will see|leave a remark hidden from the customer|jot a behind-the-scenes remark on this case")
C("chat.macro", "Macros|Canned replies|Saved answers", "zap|book-open-text|file-stack", "insert a prewritten response|reuse a stock answer|drop in boilerplate text for a common question")
NAVS = P("chat.nav", [
    ("Threads", "see the side conversations I follow", "message-square-quote"), ("Mentions", "see where people tagged me", "at-sign"),
    ("Saved items", "see the posts I set aside", "square-bookmark"), ("All unreads", "catch up on everything I have not seen yet", "list-checks"),
    ("Huddles", "join a quick audio hangout", "headset"), ("Canvases", "open the shared long-form documents", "notebook-text"),
    ("Later", "see the reminders I postponed", "clock-arrow-up"), ("Activity", "see reactions and replies to my posts", "activity"),
    ("Directory", "look up everyone in the company", "book-user"), ("Shared files", "browse documents posted in conversations", "paperclip"),
    ("Workflows", "run an automated routine", "workflow"), ("Message requests", "see chats from strangers awaiting approval", "message-circle-question-mark"),
    ("Archived chats", "see conversations I put away", "archive"), ("Communities", "browse the large public groups", "globe"),
    ("Nitro", "see the paid perks", "gem"), ("Friends", "see my contact list and who is online", "users-round"),
    ("Discover", "find public servers to join", "compass"), ("Marketplace", "buy and sell with people nearby", "store"),
    ("Polls", "see the votes in progress", "vote"), ("Scheduled messages", "see posts queued to go out at a set time", "clock-arrow-right"),
])
SECTIONS = ["Customize chat", "Media and files", "Privacy and support", "Chat members", "Shared links", "Notifications and sounds", "Search in conversation",
            "Nicknames", "Change theme", "Quick reaction", "Read receipts", "Disappearing messages", "Block or report", "Encryption", "Export chat"]
TICKET_FIELDS = ["Customer email", "Phone", "Plan", "Order number", "Company", "Country", "Language", "Account ID", "Seats", "Renewal date",
                 "Device", "App version", "Referral source", "Lifetime spend", "Contract tier"]
TICKET_SELECTS = ["Assignee", "Priority", "Status", "Ticket type", "Group", "Channel", "Severity", "Product area", "SLA policy", "Sentiment", "Queue", "Escalation level", "Brand", "Region", "Follow-up"]
TICKET_TABS = ["Open", "Pending", "Solved", "Unassigned", "Mine", "On hold", "Escalated", "Spam", "Snoozed", "Waiting on customer", "Closed", "Urgent", "Bugs", "Billing queue", "Trial users"]
ROLES = ["Admins", "Moderators", "Online", "Offline", "Staff", "Bots", "Contributors", "Guests", "Founders", "Helpers", "Designers", "Engineers", "Newcomers", "Supporters", "Alumni"]

CSS = """
.ch-msg{display:flex;gap:10px;padding:5px 16px;position:relative;flex:none}
.ch-msg.hov{background:var(--bg3)}
.ch-acts{position:absolute;right:16px;top:-14px;display:flex;background:var(--pop);border:1px solid var(--bd);border-radius:var(--r2);box-shadow:0 2px 8px var(--sh);padding:2px}
.ch-day{display:flex;align-items:center;gap:10px;padding:6px 16px;color:var(--fg2);font-size:.85em;flex:none}
.ch-day::before,.ch-day::after{content:"";flex:1;height:1px;background:var(--bd)}
.ch-bub{max-width:62%;padding:7px 12px;border-radius:16px;background:var(--bg3);line-height:1.4}
.ch-bub.me{background:var(--ac);color:var(--acf);align-self:flex-end}
.ch-srv{width:42px;height:42px;border-radius:14px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;flex:none}
.ch-srv.on{border-radius:12px;box-shadow:0 0 0 2px var(--bg2),0 0 0 4px var(--ac)}
.ch-cv{display:flex;align-items:center;gap:10px;padding:8px 10px;margin:0 6px;border-radius:var(--r2);flex:none}
.ch-cv.on{background:var(--acs2)}
.ch-snip{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.ch-irc{font-family:var(--mono);font-size:.94em;line-height:1.55;padding:0 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:none}
.tabs.ch-pills{border-bottom:none;padding:8px 10px;gap:4px}
.tabs.ch-pills .tab{border:none;margin:0;border-radius:999px;height:var(--ch);background:var(--bg3)}
.tabs.ch-pills .tab.on{background:var(--acs2);color:var(--fg)}
.side.dk .btn.ghost{color:var(--sdkm)}
.ch-pres{width:9px;height:9px;border-radius:50%;border:2px solid var(--bg1);margin-left:-9px;align-self:flex-end;flex:none}
"""
DOT = '<span class="dot" style="background:var(--ac)"></span>'
HASH = '<span class="fnt" style="width:var(--is);text-align:center;flex:none;font-weight:600">#</span>'


def _avatar(ctx, me, region, size=26):
    if not ctx.has("account"):
        return ctx.av(me, size)
    attr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=region, anchor="account")
    return f'<div class="row"{attr}>{ctx.av(me, size)}</div>'


def _capbtn(ctx, cid, region, **kw):
    """Round icon button with its name written underneath."""
    b = ctx.ibtn(cid, region, cls="l rnd bdr", anchor=None, **kw)
    return f'<div class="col g4" style="align-items:center">{b}{ctx.own(ctx.lab(cid), "xs mut")}</div>' if b else ""


def _stream(ctx, authors, n, hover=True, region="the message list"):
    """Messages with avatar, name and time; one of them shows its hover actions."""
    rng, d = ctx.rng, ctx.d
    out, hov = [], rng.randrange(max(1, n - 4), n) if hover else -1
    h, m = rng.randint(8, 11), rng.randint(0, 40)
    for i in range(n):
        if i == n // 2:
            out.append(f'<div class="ch-day">{rng.choice(["Today", "Yesterday", "Monday, March 3rd", "Friday"])}</div>')
        a = rng.choice(authors)
        m += rng.randint(1, 9)
        text = rng.choice(CHAT) if rng.random() < 0.7 else rng.choice(LOREM)
        extra = ""
        if rng.random() < 0.12:
            extra = (f'<div class="row g6" style="margin-top:3px"><span class="pill">{ctx.deco("thumbs-up", "heart", "party-popper", "hand-metal", "rocket", size=12)} {rng.randint(1, 9)}</span>'
                     f'<span class="pill">{ctx.deco("eye", "check-check", "flame", "sparkles", "coffee", size=12)} {rng.randint(1, 4)}</span></div>'
                     if rng.random() < 0.5 else f'<div class="row g6 acc sm" style="margin-top:3px">{ctx.av(rng.choice(authors), 16)}<span>{rng.randint(2, 14)} replies</span><span class="mut">Last reply today at {d.time()}</span></div>')
        acts = ""
        if i == hov:
            acts = (f'<div class="ch-acts">{ctx.ibtn("chat.react", "the message actions", cls="s")}{ctx.ibtn("chat.thread", "the message actions", cls="s")}'
                    f'{ctx.ibtn("share", "the message actions", cls="s", obj="this message")}{ctx.ibtn("chat.save", "the message actions", cls="s")}{ctx.ibtn("more", "the message actions", cls="s", obj="this message", anchor="more")}</div>')
        out.append(f'<div class="ch-msg{" hov" if i == hov else ""}">{ctx.av(a, 34, sq=True)}<div class="col f1" style="min-width:0"><div class="row g8"><span class="b">{esc(a)}</span>'
                   f'<span class="xs fnt">{h + m // 60}:{m % 60:02d} AM</span></div><div>{esc(text)}</div>{extra}</div>{acts}</div>')
    return "".join(out)


def _composer(ctx, region, to, fmt=True, send="btn"):
    if not ctx.has("chat.input"):
        return ""
    attr = ctx.reg("field", "box", ctx.lab("chat.input"), cid="chat.input", region=region)
    bar = f'<div class="row g2 px8 bb" style="min-height:calc(var(--ch) + 6px)">{"".join(ctx.ibtn(c, region, cls="s") for c in ctx.pick(FMT, 8, icon=True))}</div>' if fmt else ""
    tools = (ctx.ibtn("attach", region, cls="s", obj="my message") + ctx.ibtn("chat.emoji", region, cls="s") + ctx.ibtn("chat.mention", region, cls="s")
             + ctx.ibtn("chat.gif", region, cls="s"))
    snd = ctx.ibtn("send", region, cls="fill", obj="my message") if send == "icon" else ctx.tbtn("send", region, cls="pri sm", obj="my message")
    return (f'<div class="card col" style="margin:0 16px 14px;flex:none">{bar}<div class="px12" style="padding-top:9px;padding-bottom:9px"{attr}><span class="fnt">{esc(ctx.lab("chat.input"))}…</span></div>'
            f'<div class="row g2 px8" style="padding-bottom:6px">{tools}<div class="sp"></div>{snd}</div></div>')


def _channels(ctx, names, region, sel, noun="channel"):
    rng = ctx.rng
    out = []
    for i, n in enumerate(names):
        cnt = rng.choice([None, None, None, rng.randint(1, 24)])
        tail = f'<span class="bdg" style="margin-left:auto">{cnt}</span>' if cnt else ""
        out.append(ctx.nav(n, region, noun=noun, icon_html=HASH, on=i == sel, tail=tail, cls="b" if cnt else "", anchor="row"))
    return "".join(out)


def _dms(ctx, people, region, noun="conversation"):
    rng = ctx.rng
    out = []
    for p in people:
        col = rng.choice(["var(--ok)", "var(--ok)", "var(--fg2)", "var(--warn)"])
        ico = f'{ctx.av(p, 20)}<span class="ch-pres" style="background:{col}"></span>'
        out.append(ctx.nav(p, region, noun=noun, icon_html=ico, anchor="row", refs=[f"the conversation with {p}", f"{p} in the direct messages", f"the chat with {p}"]))
    return "".join(out)


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    people = d.people(26 + (40 if variant == "irc_compact" else 0))
    me, dms, authors, extra = people[0], people[1:8], people[8:13], people[13:]
    chans = d.take("channels", CHANNELS, rng.randint(6, 10) + (4 if H > 1000 else 0))
    cur = chans[1]
    n_msg = H // 52
    ctx.ctxmenu = ["chat.mute", "chat.pinned", "link", "chat.invite", "-", "fav", "settings", "-", "hide", "delete"]
    ctx.ctxobj = "this conversation"
    team = d.one("company", COMPANIES)
    ctx.menus["mb.go"] = ["back", "forward", "-", "chat.new", "chat.addchan", "chat.invite", "-", "search", "chat.status"]

    if variant == "slack":
        rail = "".join(f'<div class="ch-srv{" on" if i == 0 else ""}" style="background:{d.color()};width:36px;height:36px;border-radius:9px">{esc(t[0])}</div>'
                       for i, t in enumerate(d.take("projects", PROJECTS, rng.randint(2, 4))))
        rail = f'<div class="rail br" style="gap:10px">{rail}{ctx.ibtn("add", "the workspace rail", obj="my workspaces")}<div class="sp"></div>{ctx.ibtn("help", "the workspace rail")}{_avatar(ctx, me, "the workspace rail", 30)}</div>'
        navs = "".join(ctx.navc(c, "the sidebar", noun="section") for c in ctx.pick(NAVS[:11], 4))
        side = (f'<div class="side br{" dk" if rng.random() < 0.5 else ""}" style="width:{rng.choice([230, 250, 270])}px"><div class="row g6 px12 bb" style="height:calc(var(--ch) + 22px)"><span class="b lg el f1">{esc(team)}</span>'
                f'{ctx.ibtn("filter", "the sidebar", cls="s")}{ctx.ibtn("chat.new", "the sidebar", cls="s")}</div><div class="col g2 py8">{navs}</div>'
                f'<div class="hd">Channels</div><div class="col g2">{_channels(ctx, chans, "the sidebar", 1)}</div><div style="padding:2px 8px">{ctx.tbtn("chat.addchan", "the sidebar", cls="ghost sm")}</div>'
                f'<div class="hd">Direct messages</div><div class="col g2">{_dms(ctx, dms, "the sidebar")}</div><div style="padding:2px 8px">{ctx.tbtn("chat.invite", "the sidebar", cls="ghost sm")}</div></div>')
        head = (f'<div class="row g8 px16 bb" style="height:calc(var(--ch) + 22px);flex:none">{HASH}<span class="b lg">{esc(cur)}</span>{ctx.ibtn("fav", "the channel header", cls="s", obj="this channel")}'
                f'<span class="mut sm el f1">{esc(rng.choice(LOREM))}</span>{ctx.tbtn("chat.members", "the channel header", cls="sm", icon=True)}{ctx.ibtn("chat.call", "the channel header", obj="this channel")}'
                f'{ctx.ibtn("chat.pinned", "the channel header")}{ctx.search("the channel header", w=200, cls="soft")}{ctx.ibtn("panel.toggle", "the channel header")}</div>')
        main = f'<div class="col f1 clip">{head}<div class="col f1 clip" style="justify-content:flex-end;padding-top:14px">{_stream(ctx, authors, n_msg)}</div>{_composer(ctx, "the composer", cur)}</div>'
        thread = ""
        if W >= 1600:
            a = authors[0]
            replies = "".join(f'<div class="ch-msg" style="padding:5px 12px">{ctx.av(p, 28, sq=True)}<div class="col f1"><div class="row g8"><span class="b">{esc(p)}</span><span class="xs fnt">{d.time()}</span></div><div>{esc(rng.choice(CHAT))}</div></div></div>'
                              for p in rng.sample(authors, 3))
            box = ""
            if True:
                attr = ctx.reg("field", "box", "Reply to thread", region="the thread panel", refs=["the reply box in the thread panel", "the thread reply field"])
                box = f'<div class="p12"><div class="inp" style="height:calc(var(--ch) + 12px)"{attr}><span class="ph f1">Reply…</span>{ctx.ibtn("send", "the thread panel", cls="s", obj="my thread reply")}</div></div>'
            thread = (f'<div class="side bl" style="width:{rng.choice([340, 380])}px;background:var(--bg)"><div class="row px12 bb" style="height:calc(var(--ch) + 22px)"><span class="b sp">Thread</span>'
                      f'{ctx.ibtn("close.panel", "the thread panel", cls="s", obj="the thread panel")}</div><div class="ch-msg" style="padding:10px 12px">{ctx.av(a, 34, sq=True)}<div class="col"><span class="b">{esc(a)}</span><div>{esc(rng.choice(LOREM))}</div></div></div>'
                      f'<div class="ch-day">3 replies</div>{replies}<div class="sp"></div>{box}</div>')
        body = f'<div class="row str f1">{rail}{side}{main}{thread}</div>'
    elif variant == "messenger":
        convs = []
        for i, p in enumerate(dms + extra[:max(0, H // 60 - 6)]):
            attr = ctx.reg("row", "conversation", p, region="the chat list", anchor="row", refs=[f"the conversation with {p}", f"the chat with {p}", f"{p} in the chat list"])
            unread = rng.random() < 0.25
            convs.append(f'<div class="ch-cv{" on" if i == 0 else ""}"{attr}>{ctx.av(p, 44)}<div class="col f1" style="min-width:0"><span class="el {"b" if unread else "m"}">{esc(p)}</span>'
                         f'<span class="ch-snip sm {"b" if unread else "mut"}">{esc(rng.choice(CHAT))} · {rng.randint(1, 23)}h</span></div>{DOT if unread else ""}</div>')
        tabs = ctx.tabs(d.take("chat.mtabs", ["Inbox", "Communities", "Unread", "Groups", "Requests", "Archived", "Marketplace chats", "Favorites", "Work", "Family", "Calls", "Channels", "Spam folder", "Broadcasts", "Bots"], 3), 0, region="the chat list", cls="ch-pills")
        left = (f'<div class="side br" style="width:{rng.choice([320, 350, 380])}px"><div class="row g6 p12"><span class="xl b sp">Chats</span>{ctx.ibtn("more", "the chat list", cls="rnd bdr", anchor="more")}'
                f'{ctx.ibtn("chat.video", "the chat list", cls="rnd bdr", obj="a group")}{ctx.ibtn("chat.new", "the chat list", cls="rnd bdr")}</div><div class="px12">{ctx.search("the chat list", cls="rnd soft")}</div>{tabs}<div class="col g2 f1 clip">{"".join(convs)}</div></div>')
        other = dms[0]
        head = (f'<div class="row g10 px16 bb" style="height:58px;flex:none">{ctx.av(other, 38)}<div class="col f1"><span class="b">{esc(other)}</span><span class="xs mut">Active {rng.randint(2, 50)}m ago</span></div>'
                f'{ctx.ibtn("chat.call", "the chat header", cls="l", obj=other)}{ctx.ibtn("chat.video", "the chat header", cls="l", obj=other)}{ctx.ibtn("panel.toggle", "the chat header", cls="l")}</div>')
        bubs = []
        for i in range(n_msg):
            mine = rng.random() < 0.45
            t = rng.choice(CHAT)
            bubs.append(f'<div class="row g8" style="flex:none;{"justify-content:flex-end" if mine else ""}">{"" if mine else ctx.av(other, 26)}<div class="ch-bub{" me" if mine else ""}">{esc(t)}</div></div>')
        comp = ""
        if ctx.has("chat.input"):
            attr = ctx.reg("field", "box", ctx.lab("chat.input"), cid="chat.input", region="the composer")
            comp = (f'<div class="row g6 p12" style="flex:none">{ctx.ibtn("add", "the composer", cls="rnd", obj="this chat")}{ctx.ibtn("attach", "the composer", obj="my message")}{ctx.ibtn("chat.gif", "the composer")}'
                    f'<div class="inp rnd soft f1" style="height:calc(var(--ch) + 10px)"{attr}><span class="ph f1">{esc(ctx.lab("chat.input"))}</span></div>{ctx.ibtn("chat.emoji", "the composer")}{ctx.ibtn("send", "the composer", cls="fill rnd", obj="my message")}</div>')
        main = f'<div class="col f1 clip">{head}<div class="col g6 f1 clip p16" style="justify-content:flex-end">{"".join(bubs)}</div>{comp}</div>'
        info = ""
        if W >= 1400:
            acts = (_capbtn(ctx, "account", "the info panel") + _capbtn(ctx, "chat.mute", "the info panel", obj="this chat")
                    + _capbtn(ctx, "chat.pinned", "the info panel", obj="this chat"))
            secs = []
            for sname in d.take("chat.sections", SECTIONS, 5):
                attr = ctx.reg("button", "section", sname, region="the info panel")
                secs.append(f'<div class="row py8 px12 rad"{attr}><span class="m sp">{esc(sname)}</span><span class="mut">{CHEV_D}</span></div>')
            media = "".join(ctx.thumb(74, 74, 6) for _ in range(6))
            info = (f'<div class="side bl p16 g12" style="width:{rng.choice([300, 330])}px;align-items:stretch;background:var(--bg)"><div class="col g6" style="align-items:center">{ctx.av(other, 84)}<span class="b lg">{esc(other)}</span>'
                    f'<span class="xs mut">Active now</span></div><div class="row cen g24">{acts}</div><div class="col">{"".join(secs)}</div><div class="row wrap g6">{media}</div></div>')
        body = f'<div class="row str f1">{left}{main}{info}</div>'
    elif variant == "discord":
        srv = "".join(f'<div class="ch-srv{" on" if i == 1 else ""}" style="background:{d.color()}">{esc(t[:2])}</div>' for i, t in enumerate(d.take("projects", PROJECTS, min(12, H // 70))))
        rail = f'<div class="rail" style="width:70px;gap:8px">{ctx.ibtn("chat.new", "the server rail", cls="l rnd bdr")}<div class="hsep" style="width:32px"></div>{srv}{ctx.ibtn("add", "the server rail", cls="l rnd bdr", obj="my servers")}</div>'
        cats = d.take("chat.cats", ["Information", "Text channels", "Voice channels", "Projects", "Off topic", "Help desk", "Archive", "Events", "Leadership", "Clans", "Regional", "Bots corner", "Showcase", "Staff only", "Partners"], 3)
        split = [chans[:len(chans) // 2], chans[len(chans) // 2:]]
        sect = ""
        for ci, cat in enumerate(cats[:2]):
            ca = ctx.reg("button", "category", cat, region="the channel list")
            sect += (f'<div class="row g4 fnt xs up b" style="padding:12px 8px 4px"{ca}>{CHEV_D}<span class="sp">{esc(cat)}</span></div>'
                     + f'<div class="col g2">{_channels(ctx, split[ci], "the channel list", 1 if ci == 0 else -1)}</div>')
        voice = "".join(ctx.nav(v, "the channel list", noun="voice channel", deco=("volume-2", "volume-1", "audio-lines", "speaker", "mic-vocal", "radio"), anchor="row")
                        for v in d.take("chat.voice", ["Lounge", "Standup room", "Gaming", "Pairing", "Music", "AFK", "Stage", "Study hall", "War room", "Karaoke", "Office hours", "Co-working", "Podcast booth", "Quiet zone", "Late night"], 3))
        user = (f'<div class="row g6 p8 bt bg2">{_avatar(ctx, me, "the user panel", 30)}<div class="col f1" style="min-width:0"><span class="b sm el">{esc(me.split()[0])}</span><span class="xs mut">Online</span></div>'
                f'{ctx.ibtn("chat.micmute", "the user panel", cls="s")}{ctx.ibtn("chat.deafen", "the user panel", cls="s")}{ctx.ibtn("settings", "the user panel", cls="s")}</div>')
        side = (f'<div class="side br" style="width:{rng.choice([230, 240, 250])}px"><div class="row px12 bb" style="height:48px"><span class="b sp el">{esc(team)}</span><span class="mut">{CHEV_D}</span></div>'
                f'<div class="col f1 clip">{sect}<div class="row g4 fnt xs up b" style="padding:12px 8px 4px">{CHEV_D}<span>{esc(cats[2])}</span></div><div class="col g2">{voice}</div></div>{user}</div>')
        head = (f'<div class="row g8 px16 bb" style="height:48px;flex:none">{HASH}<span class="b">{esc(cur)}</span><div class="vsep"></div><span class="mut sm el f1">{esc(rng.choice(LOREM))}</span>'
                f'{ctx.ibtn("chat.thread", "the channel header", func=False)}{ctx.ibtn("chat.mute", "the channel header", obj="this channel")}{ctx.ibtn("chat.pinned", "the channel header")}{ctx.ibtn("chat.members", "the channel header", on=True)}'
                f'{ctx.search("the channel header", w=170, cls="soft")}{ctx.ibtn("notif", "the channel header")}{ctx.ibtn("help", "the channel header")}</div>')
        main = f'<div class="col f1 clip">{head}<div class="col f1 clip" style="justify-content:flex-end;padding-top:14px">{_stream(ctx, authors, n_msg)}</div>{_composer(ctx, "the composer", cur, fmt=False, send="icon")}</div>'
        roles = d.take("chat.roles", ROLES, 3)
        mem, pool = "", list(extra)
        for r in roles:
            mem += f'<div class="hd">{esc(r)} — {rng.randint(2, 40)}</div>'
            for _ in range(max(2, H // 150)):
                if pool:
                    p = pool.pop()
                    attr = ctx.reg("row", "member", p, region="the member list", anchor="row")
                    mem += f'<div class="nav" style="height:calc(var(--rh) + 10px)"{attr}>{ctx.av(p, 28)}<span class="el">{esc(p)}</span></div>'
        members = f'<div class="side bl" style="width:{rng.choice([220, 240])}px">{mem}</div>' if W >= 1360 else ""
        body = f'<div class="row str f1">{rail}{side}{main}{members}</div>'
    elif variant == "support_inbox":
        region = "the ticket queue"
        tabs = ctx.tabs(d.take("ticket.tabs", TICKET_TABS, 3), 0, region=region)
        subs = d.tasks(H // 62 + 2)
        rows = []
        for i, (p, sj) in enumerate(zip(dms + extra, subs)):
            attr = ctx.reg("row", "ticket", sj, region=region, anchor="row", refs=[f"the ticket from {p}", f'the ticket titled "{sj}"', f"{p}'s request in the queue"])
            pr = rng.choice(['<span class="pill r">High</span>', '<span class="pill y">Normal</span>', '<span class="pill">Low</span>'])
            rows.append(f'<div class="ch-cv{" on" if i == 0 else ""}" style="align-items:flex-start;border-radius:0;margin:0;border-bottom:1px solid var(--bd)"{attr}>{ctx.av(p, 30)}<div class="col f1" style="min-width:0;gap:2px">'
                        f'<div class="row g6"><span class="el f1 m">{esc(p)}</span><span class="xs mut nw">{rng.randint(2, 59)}m</span></div><span class="el">{esc(sj)}</span><div class="row g6">{pr}<span class="xs mut">#{rng.randint(1000, 9999)}</span></div></div></div>')
        left = (f'<div class="side br" style="width:{rng.choice([300, 330, 360])}px"><div class="row g6 p8">{ctx.search(region, cls="soft f1")}{ctx.ibtn("filter", region)}{ctx.ibtn("sort", region)}</div>{tabs}<div class="col f1 clip">{"".join(rows)}</div></div>')
        cust = dms[0]
        head = (f'<div class="row g8 px16 bb" style="height:calc(var(--ch) + 26px);flex:none"><div class="col f1" style="min-width:0"><span class="b lg el">{esc(subs[0])}</span><span class="xs mut">via email · opened {d.date()}</span></div>'
                f'{ctx.tbtn("chat.assign", "the ticket header", cls="sm")}{ctx.ibtn("chat.call", "the ticket header", obj="the customer")}{ctx.ibtn("mail.snooze", "the ticket header", obj="this ticket")}'
                f'{ctx.ibtn("more", "the ticket header", anchor="more", obj="this ticket")}{ctx.tbtn("chat.resolve", "the ticket header", cls="pri sm", icon=True)}</div>')
        msgs = _stream(ctx, [cust, me], max(4, n_msg - 5), hover=False)
        modes = ctx.seg([ctx.lab(c) for c in ctx.avail(["mail.reply", "chat.note"])], 0, region="the reply box", noun="tab", cids=ctx.avail(["mail.reply", "chat.note"]))
        box = (f'<div class="card col" style="margin:0 16px 14px;flex:none"><div class="row g8 p8 bb">{modes}<div class="sp"></div>{ctx.tbtn("chat.macro", "the reply box", cls="ghost sm", icon=True, caret=True)}</div>'
               f'<div class="p12 fnt" style="min-height:{72 if H > 850 else 44}px">Write your answer to {esc(cust.split()[0])}…</div><div class="row g2 p8">{"".join(ctx.ibtn(c, "the reply box", cls="s") for c in ctx.pick(FMT, 6, icon=True))}'
               f'{ctx.ibtn("attach", "the reply box", cls="s", obj="my answer")}<div class="sp"></div>{ctx.tbtn("send", "the reply box", cls="pri sm", obj="my answer", caret=True)}</div></div>')
        main = f'<div class="col f1 clip">{head}<div class="col f1 clip" style="justify-content:flex-end;padding-top:12px">{msgs}</div>{box}</div>'
        vals = {"Customer email": d.email_of(cust), "Phone": "+1 555 01" + str(rng.randint(10, 99)), "Plan": "Team (annual)", "Order number": "ORD-" + str(rng.randint(10000, 99999)),
                "Company": team, "Country": rng.choice(["Germany", "Canada", "Japan", "Brazil"]), "Language": "English", "Account ID": "ACC-" + str(rng.randint(1000, 9999)),
                "Seats": str(rng.randint(3, 80)), "Renewal date": d.date(True), "Device": "Laptop, 14-inch", "App version": f"4.{rng.randint(0, 19)}.{rng.randint(0, 9)}",
                "Referral source": "Partner", "Lifetime spend": d.money(200, 9000), "Contract tier": "Enterprise"}
        fields = "".join(ctx.field(f, vals[f], region="the customer panel") for f in d.take("ticket.fields", TICKET_FIELDS, 4))
        sels = "".join(ctx.select(f, rng.choice(["Normal", "Tier 2", authors[0], "Email"]), options=["Low", "Normal", "High", "Urgent"], region="the customer panel")
                       for f in d.take("ticket.selects", TICKET_SELECTS, 2))
        prev = "".join(f'<div class="col py4 bb"><span class="m el">{esc(t)}</span><span class="xs mut">Solved · {d.date(True)}</span></div>' for t in d.tasks(3))
        right = (f'<div class="side bl p12 g10" style="width:{rng.choice([280, 310])}px"><div class="row g10">{ctx.av(cust, 40)}<div class="col"><span class="b">{esc(cust)}</span><span class="xs mut">Customer since {rng.choice([2021, 2022, 2023, 2024])}</span></div></div>'
                 f'{sels}{fields}<div class="hsep"></div><span class="xs mut up b">Previous conversations</span>{prev}</div>')
        body = f'<div class="row str f1">{left}{main}{right}</div>'
    else:  # irc_compact
        tabs = ctx.tabs(chans[:min(len(chans), W // 190)], 1, region="the tab bar", cls="box", closable=True, icon_fn=lambda _: HASH)
        nets = d.take("chat.nets", ["Libera", "OFTC", "EFnet", "Rizon", "Snoonet", "Undernet", "QuakeNet", "IRCnet", "DALnet", "Freenode", "EsperNet", "Hackint", "Tilde", "Pine", "Darkfall"], 2)
        tree = ""
        for ni, net in enumerate(nets):
            na = ctx.reg("nav", "network", net, region="the network tree")
            tree += f'<div class="nav b"{na}><span class="mut" style="display:flex">{CHEV_D}</span><span>{esc(net)}</span></div>'
            if ni == 0:
                tree += "".join(ctx.nav(p, "the network tree", noun="query", pad=18, refs=[f"the private query with {p}", f"{p} in the network tree"]) for p in dms[:4])
        left = f'<div class="side br py8 g2" style="width:{rng.choice([180, 200])}px">{tree}</div>'
        topic = (f'<div class="row g8 px12 bb bg1" style="min-height:calc(var(--ch) + 6px);flex:none"><span class="mono sm el f1">Topic: {esc(rng.choice(LOREM))}</span>{ctx.ibtn("chat.pinned", "the topic bar", cls="s")}'
                 f'{ctx.ibtn("chat.mute", "the topic bar", cls="s", obj="this channel")}{ctx.ibtn("search", "the topic bar", cls="s")}{ctx.ibtn("settings", "the topic bar", cls="s")}</div>')
        nicks = [p.split()[0].lower() + rng.choice(["", "_", "42", "^", "|away"]) for p in authors + extra[:4]]
        lines, hh, mm = [], rng.randint(9, 19), rng.randint(0, 30)
        for i in range(H // 19):
            mm += rng.randint(0, 3)
            hh, mm = hh + mm // 60, mm % 60
            nk = rng.choice(nicks)
            col = ["var(--code-k)", "var(--code-s)", "var(--code-t)", "var(--code-n)", "var(--ac)"][sum(map(ord, nk)) % 5]
            if rng.random() < 0.1:
                lines.append(f'<div class="ch-irc fnt">[{hh:02d}:{mm:02d}] --&gt; {esc(nk)} has joined #{esc(cur)}</div>')
            else:
                lines.append(f'<div class="ch-irc"><span class="fnt">[{hh:02d}:{mm:02d}]</span> <span style="color:{col}">&lt;{esc(nk)}&gt;</span> {esc(rng.choice(CHAT))}</div>')
        inp = ""
        if ctx.has("chat.input"):
            attr = ctx.reg("field", "line", ctx.lab("chat.input"), cid="chat.input", region="the input line")
            inp = (f'<div class="row g8 p8 bt" style="flex:none"><span class="mono b">{esc(me.split()[0].lower())}</span><div class="inp f1 mono"{attr}><span class="ph f1">{esc(ctx.lab("chat.input"))}</span></div>'
                   f'{ctx.ibtn("chat.emoji", "the input line", cls="s")}{ctx.ibtn("attach", "the input line", cls="s", obj="my message")}{ctx.tbtn("send", "the input line", cls="sm", obj="my message")}</div>')
        nl = ""
        for i, full in enumerate(extra[:max(6, H // 26 - 4)]):
            p = full.split()[0].lower() + "_" + full.split()[-1][:3].lower()
            attr = ctx.reg("row", "nick", p, region="the nick list", anchor="row", refs=[f"{p} in the nick list", f"the user {p} in the list on the right"])
            nl += f'<div class="li mono sm" style="min-height:calc(var(--rh) - 2px)"{attr}><span class="{"ok" if i < 2 else "fnt"}" style="width:10px">{"@" if i < 2 else ("+" if i < 5 else "")}</span><span class="el">{esc(p)}</span></div>'
        right = f'<div class="side bl" style="width:{rng.choice([190, 210])}px"><div class="hd">{len(extra) + rng.randint(20, 300)} users</div>{nl}</div>'
        body = f'<div class="col f1">{tabs}<div class="row str f1">{left}<div class="col f1 clip">{topic}<div class="col f1 clip" style="justify-content:flex-end;padding:6px 0">{"".join(lines)}</div>{inp}</div>{right}</div></div>'
    return {"title": f"{team} — #{cur}", "body": body, "css": CSS, "app": rng.choice(["Chatter", "Relay", "Huddle"]),
            "menus": ["mb.file", "mb.edit", "mb.view", "mb.go", "mb.window", "mb.help"], "url": "chat.example.com/client/" + cur}
