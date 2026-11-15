"""Calendars: month grid, week time-grid, agenda with detail panel, resource scheduler."""
from ..data import COLORS, DAYS, EVENTS, MONTHS
from ..ui import esc
from ..vocab import C

NAME = "calendar"
KIND = "either"
VARIANTS = {"month": "train", "week": "train", "agenda": "dev", "scheduler": "test"}

C("cal.new", "New event|Create event|Add appointment", "calendar-plus|calendar-plus-2|square-plus", "put something on my schedule|block out time for a meeting|reserve a slot in my diary for something")
C("cal.today", "Today|Go to today|Jump to now", "", "bring the current date back into view|return the view to the present day|snap the view to this very day")
C("cal.prev", "Previous period|Earlier|Back one", "chevron-left|arrow-left|circle-chevron-left|square-chevron-left|arrow-big-left", "move the view to the dates before the ones shown|show the preceding stretch of days|page backwards through the dates")
C("cal.next", "Next period|Later|Ahead one", "chevron-right|arrow-right|circle-chevron-right|square-chevron-right|arrow-big-right", "move the view to the dates after the ones shown|show the following stretch of days|page onwards through the dates")
C("cal.v.day", "Day|Daily|1 day", "", "make the big calendar area show a single date hour by hour|zoom the main view in to just one date|show only one date in detail in the main area")
C("cal.v.week", "Week|Weekly|7 days", "", "make the big calendar area show Monday through Sunday side by side|show one whole seven-date stretch at once in the main view|lay out the current seven dates as columns in the main view")
C("cal.v.month", "Month|Monthly|4 weeks", "", "make the big calendar area show about thirty dates in a grid|turn the main view into a whole wall-planner page|zoom the main view out to roughly thirty dates")
C("cal.v.year", "Year|Yearly|12 months", "", "see January through December at a glance|zoom all the way out to the full annual overview|show every season on one screen")
C("cal.v.agenda", "Agenda|Schedule|List of events", "", "see my upcoming commitments as a plain chronological rundown|read what is coming up one line per commitment|show my commitments as text instead of a grid")
C("cal.join", "Join call|Join meeting|Enter video room", "video|webcam|monitor-play", "connect to the online conference for {o}|get into the virtual room for {o}|dial into {o} with my camera", o="this event")
C("cal.guests", "Add guests|Invite attendees|Add participants", "user-plus|user-round-plus|users-round|contact-round|handshake", "include more people in {o}|put additional names on {o}|bring colleagues onto {o}", o="this event")
C("cal.remind", "Add reminder|Set alert|Notify me", "bell-plus|alarm-clock-plus|bell-ring|alarm-clock", "get a nudge shortly before {o} starts|be pinged ahead of {o}|have the app warn me in advance of {o}", o="this event")
C("cal.recur", "Recurring|Repeats|Make it repeat", "", "turn {on} having this happen again at regular intervals|turn {on} automatic copies of this on future dates|turn {on} the weekly recurrence")
C("cal.allday", "All day|All-day event|Whole day", "", "turn {on} lasting from morning to night instead of set hours|turn {on} spanning the entire date with no start hour|turn {on} ignoring clock times for this entry")
C("cal.findtime", "Find a time|Suggest times|Scheduling assistant", "", "see when everybody is free|let the app propose slots that suit all guests|compare the guests' availability")
C("cal.yes", "Yes|Accept|Going", "", "confirm that I will attend {o}|tell the organizer I will be at {o}|say I am coming to {o}", o="this event")
C("cal.no", "No|Decline|Not going", "", "tell the organizer I cannot make {o}|turn down the invitation to {o}|say I will be absent from {o}", o="this event")
C("cal.maybe", "Maybe|Tentative|Not sure", "", "answer that I might attend {o}|leave my attendance at {o} undecided|say I am unsure about making {o}", o="this event")
C("cal.subscribe", "Add calendar|Subscribe to calendar|Connect another calendar", "", "bring in another set of dates such as a colleague's or public holidays|overlay a further source of dates on mine|link one more diary to this view")
C("cal.title", "Title|Event name|What", "", "type what the booking is called|give the new entry a name|enter a short description of the booking")
C("cal.where", "Location|Where|Place", "map-pin|map-pinned|navigation", "say at which address it happens|enter the venue|fill in the meeting spot")
C("cal.f.room", "Room|Space|Resource", "", "choose which of the bookable places to reserve|pick what is being reserved|select the place this reservation is for")
C("cal.f.start", "Start time|Starts|From", "", "set the hour the reservation begins|choose when the reservation kicks off|pick the beginning hour")
C("cal.f.end", "End time|Ends|Until", "", "set the hour the reservation is over|choose when the reservation finishes|pick the finishing hour")
C("cal.book", "Book|Reserve|Confirm booking", "", "finalize the reservation I filled in|lock in the slot with these details|commit the reservation shown in the form")
CALS = ["Personal", "Family", "Birthdays", "Holidays", "Team PTO", "On-call rota", "Gym", "School", "Side project", "Deadlines", "Room bookings",
        "Interviews", "Volunteering", "Kids", "Conferences", "Maintenance", "Social", "Product launches", "Payroll dates", "Training"]
ROOMS = ["Aspen", "Birch", "Cedar", "Dogwood", "Elm", "Fir", "Ginkgo", "Hazel", "Juniper", "Larch", "Maple", "Oak", "Pine room", "Redwood", "Spruce", "Teak",
         "Walnut", "Willow", "Yew", "Studio A", "Studio B", "Lab 1", "Lab 2", "Boardroom", "Focus pod 1", "Focus pod 2", "Phone booth", "Auditorium",
         "Training room", "Rooftop", "Atrium", "Workshop", "Library nook", "Garden room", "Mezzanine", "Alder", "Beech", "Chestnut", "Cypress", "Hemlock",
         "Hickory", "Linden", "Magnolia", "Mulberry", "Olive", "Poplar", "Rowan", "Sequoia", "Sycamore", "Tamarack", "Annex 1", "Annex 2", "Huddle 1", "Huddle 2",
         "Huddle 3", "Project room", "Quiet room", "Media lab", "Maker space", "Seminar hall"]
SCH_FILTERS = ["Building", "Floor", "Capacity", "Equipment", "Room type", "Department", "Availability", "Organizer", "Duration", "Catering",
               "Accessibility", "Video gear", "Whiteboard", "Zone", "Booking status"]
PLACES = ["Room 4", "Video call", "Cafeteria", "HQ 2F", "Main lobby", "Off-site", "Lab", "Downtown office", "Online", "Clinic"]

CSS = """
.ca-cell{border-right:1px solid var(--bd);border-bottom:1px solid var(--bd);padding:3px 4px;display:flex;flex-direction:column;gap:2px;min-width:0;min-height:0;overflow:hidden}
.ca-cell.out{background:var(--bg1);color:var(--fg2)}
.ca-num{font-size:.88em;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none}
.ca-num.now{background:var(--ac);color:var(--acf);font-weight:700}
.ca-chip{display:flex;align-items:center;gap:4px;height:19px;padding:0 5px;border-radius:4px;font-size:.86em;flex:none;min-width:0}
.ca-ev{position:absolute;left:2px;right:6px;border-radius:5px;padding:2px 6px;font-size:.88em;line-height:1.25;overflow:hidden;display:flex;flex-direction:column}
.ca-mini{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;font-size:.84em}
.ca-mini>div{width:22px;height:22px;justify-self:center;display:flex;align-items:center;justify-content:center;border-radius:50%}
.ca-mini .now{background:var(--ac);color:var(--acf);font-weight:700}
.ca-hour{font-size:.8em;color:var(--fg2);text-align:right;padding-right:6px;transform:translateY(-.6em)}
.ca-bk{position:absolute;top:4px;bottom:4px;border-radius:5px;padding:0 8px;display:flex;align-items:center;font-size:.9em;overflow:hidden}
.ca-snip{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
"""


def _ord(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _tint(c, pct=22):
    return f"background:color-mix(in srgb,{c} {pct}%,var(--bg));border-left:3px solid {c}"


def _avatar(ctx, me, region, size=28):
    if not ctx.has("account"):
        return ctx.av(me, size)
    attr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=region, anchor="account")
    return f'<div class="row"{attr}>{ctx.av(me, size)}</div>'


class Events:
    """Hands out event titles; a title may recur on different days and is then told apart by its day."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.pool = ctx.d.take("events", EVENTS)
        self.used = {}

    def take(self, day_key, day_phrase):
        rng = self.ctx.rng
        for _ in range(8):
            t = rng.choice(self.pool)
            if day_key not in self.used.setdefault(t, set()):
                self.used[t].add(day_key)
                return t, day_phrase
        return None, None

    def reg(self, title, day_phrase, region, noun="event"):
        return self.ctx.reg("row", noun, title, region=region, row=day_phrase, anchor="row")


def _mini(ctx, month, today, region="the mini calendar"):
    rng = ctx.rng
    off = rng.randrange(7)
    cells = "".join(f'<div class="fnt">{dname[0]}</div>' for dname in DAYS)
    cells += "".join('<div></div>' for _ in range(off))
    for n in range(1, 31):
        attr = ctx.reg("button", "date", f"{month} {n} in mini calendar", region=region,
                       refs=[f"{month} {n} in the mini calendar", f"the {_ord(n)} in the small month view", f"day {n} in the little calendar in the sidebar"])
        cells += f'<div class="{"now" if n == today else ""}"{attr}>{n}</div>'
    return (f'<div class="col g4 p12"><div class="row"><span class="b sp">{month} 2026</span>{ctx.ibtn("cal.prev", region, cls="s")}{ctx.ibtn("cal.next", region, cls="s")}</div>'
            f'<div class="ca-mini">{cells}</div></div>')


def _callist(ctx, region="the calendar list", n=5):
    rng, d = ctx.rng, ctx.d
    out = ""
    for c in d.take("cals", CALS, n):
        col = d.color()
        on = rng.random() < 0.75
        attr = ctx.reg("checkbox", "checkbox", c, region=region, state=on)
        box = f'<span class="box" style="{"background:" + col + ";" if on else ""}border-color:{col};color:{"#fff" if on else "transparent"}"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></span>'
        out += f'<div class="chk{" on" if on else ""}" style="padding:3px 16px"{attr}>{box}<span>{esc(c)}</span></div>'
    return f'<div class="hd">My calendars</div><div class="col">{out}</div><div style="padding:4px 10px">{ctx.tbtn("cal.subscribe", region, cls="ghost sm")}</div>'


def _toolbar(ctx, title, views, active, region="the calendar toolbar", extra=""):
    rng = ctx.rng
    seg = ctx.seg([ctx.lab(c) for c in views], active, region=region, noun="view", cids=views)
    return (f'<div class="tb" style="gap:8px;padding:6px 12px">{ctx.tbtn("cal.new", region, cls="pri", icon=True)}{ctx.tbtn("cal.today", region)}{ctx.ibtn("cal.prev", region)}{ctx.ibtn("cal.next", region)}'
            f'<span class="b lg nw" style="margin:0 6px">{esc(title)}</span><div class="sp"></div>{extra}{seg}{ctx.search(region, w=rng.choice([170, 200]), cls="soft")}{ctx.ibtn("print", region, obj="this calendar")}{ctx.ibtn("settings", region)}</div>')


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    me = d.person()
    month = rng.choice(MONTHS)
    today = rng.randint(3, 27)
    ev = Events(ctx)
    views = ctx.avail(["cal.v.day", "cal.v.week", "cal.v.month", "cal.v.year", "cal.v.agenda"])
    ctx.ctxmenu = ["edit", "duplicate", "cal.guests", "cal.remind", "-", "copy", "cut", "move", "-", "delete"]
    ctx.ctxobj = "this event"
    ctx.menus["mb.view"] = ["cal.v.day", "cal.v.week", "cal.v.month", "cal.v.year", "cal.v.agenda", "-", "cal.today", "cal.prev", "cal.next", "-", "sidebar.toggle", "fullscreen"]
    sw = rng.choice([220, 236, 250])
    side = f'<div class="side br" style="width:{sw}px">{_mini(ctx, month, today)}<div class="hsep"></div>{_callist(ctx, n=rng.randint(4, 6) + (2 if H > 1000 else 0))}</div>'
    acct = _avatar(ctx, me, "the calendar toolbar") if spec["web"] else ""

    if variant == "month":
        off, weeks = rng.randrange(6), 5
        cell_h = (H - 230) / weeks
        cap = max(1, int((cell_h - 30) // 21))
        head = "".join(f'<div class="ct xs b mut py4 br bb">{dn}</div>' for dn in DAYS)
        cells = ""
        for i in range(weeks * 7):
            n = i - off + 1
            inside = 1 <= n <= 30
            num = n if inside else (n + 30 if n < 1 else n - 30)
            chips = ""
            if inside:
                attr = ctx.reg("button", "day", f"{month} {n} cell", region="the month grid",
                               refs=[f"{month} {n} in the month grid", f"the day cell for {month} {n}", f"the big grid square for the {_ord(n)}"])
                for _ in range(rng.randint(0, min(cap, 4))):
                    t, phrase = ev.take(n, f"the {_ord(n)}")
                    if not t:
                        continue
                    c = rng.choice(COLORS)
                    solid = rng.random() < 0.35
                    style = f"background:{c};color:#fff" if solid else _tint(c)
                    tm = "" if solid else f'<span class="fnt xs nw">{rng.randint(8, 17)}:{rng.choice(["00", "30"])}</span>'
                    chips += f'<div class="ca-chip" style="{style}"{ev.reg(t, phrase, "the month grid")}>{tm}<span class="el">{esc(t)}</span></div>'
                cells += f'<div class="ca-cell"{attr}><span class="ca-num{" now" if n == today else ""}">{num}</span>{chips}</div>'
            else:
                cells += f'<div class="ca-cell out"><span class="ca-num">{num}</span></div>'
        grid = (f'<div class="col f1 clip bl"><div style="display:grid;grid-template-columns:repeat(7,1fr);flex:none">{head}</div>'
                f'<div class="f1" style="display:grid;grid-template-columns:repeat(7,1fr);grid-template-rows:repeat({weeks},1fr);min-height:0">{cells}</div></div>')
        body = f'<div class="col f1">{_toolbar(ctx, f"{month} 2026", views, min(2, len(views) - 1), extra=acct)}<div class="row str f1">{side}{grid}</div></div>'
    elif variant == "week":
        h0, hours = 7, 12
        hh = max(34, (H - 250) // hours)
        start = rng.randint(2, 22)
        cols, heads, allday = "", "", ""
        for i, dn in enumerate(DAYS):
            n = start + i
            is_now = i == 2
            heads += f'<div class="col f1 bl ct py4"><span class="xs mut up">{dn}</span><span class="{"acc b" if is_now else ""} lg">{n}</span></div>'
            blocks, t = "", rng.uniform(0, 2.5)
            while t < hours - 1 and (i < 5 or rng.random() < 0.3):
                dur = rng.choice([0.5, 1, 1, 1.5, 2])
                title, phrase = ev.take(n, f"{dn} the {_ord(n)}")
                if title and t + dur <= hours:
                    c = rng.choice(COLORS)
                    st = h0 + int(t)
                    blocks += (f'<div class="ca-ev" style="top:{t * hh + 1:.0f}px;height:{dur * hh - 2:.0f}px;{_tint(c, 26)}"{ev.reg(title, phrase, "the week grid")}><span class="el m">{esc(title)}</span>'
                               + (f'<span class="xs mut ca-snip">{(st - 1) % 12 + 1}:{"30" if t % 1 else "00"} {"AM" if st < 12 else "PM"} · {rng.choice(PLACES)}</span>' if dur >= 1 else "") + "</div>")
                t += dur + rng.choice([0, 0.5, 1, 1.5, 2.5])
            line = f'<div style="position:absolute;left:0;right:0;top:{rng.uniform(1, hours - 1) * hh:.0f}px;height:2px;background:var(--err)"></div>' if is_now else ""
            cols += (f'<div class="rel f1 bl" style="height:{hours * hh}px;background:repeating-linear-gradient(to bottom,transparent 0,transparent {hh - 1}px,var(--bd) {hh - 1}px,var(--bd) {hh}px)'
                     f'{";background-color:var(--acs)" if is_now else ""}">{blocks}{line}</div>')
            if rng.random() < 0.3:
                title, phrase = ev.take(n, f"{dn} the {_ord(n)}")
                chip = f'<div class="ca-chip" style="background:{rng.choice(COLORS)};color:#fff;margin:2px 4px"{ev.reg(title, phrase, "the all-day row")}><span class="el">{esc(title)}</span></div>' if title else ""
            else:
                chip = ""
            allday += f'<div class="f1 bl" style="min-height:24px;min-width:0">{chip}</div>'
        gutter = "".join(f'<div class="ca-hour" style="height:{hh}px">{(h0 + k - 1) % 12 + 1} {"AM" if h0 + k < 12 else "PM"}</div>' for k in range(hours))
        grid = (f'<div class="col f1 clip"><div class="row str bb" style="flex:none"><div style="width:56px"></div>{heads}</div>'
                f'<div class="row str bb" style="flex:none"><div class="xs fnt rt" style="width:56px;padding:4px 6px">all-day</div>{allday}</div>'
                f'<div class="row top f1 clip" style="padding-top:8px"><div style="width:56px;flex:none">{gutter}</div>{cols}</div></div>')
        right = ""
        if W >= 1500:
            ups = "".join(f'<div class="col py4 bb"><span class="m">{esc(x)}</span><span class="xs mut">{d.time()} · {rng.choice(PLACES)}</span></div>' for x in ["Focus block", "Commute", "Lunch break", "Deep work"][:rng.randint(2, 4)])
            right = (f'<div class="side bl p12 g8" style="width:240px"><div class="row"><span class="b sp">Up next</span>{ctx.ibtn("close.panel", "the side panel", cls="s", obj="the side panel")}</div>{ups}'
                     f'<div class="sp"></div>{ctx.tbtn("cal.findtime", "the side panel", cls="w100")}</div>')
        body = (f'<div class="col f1">{_toolbar(ctx, f"{month} {start}–{start + 6}, 2026", views, min(1, len(views) - 1), extra=acct)}<div class="row str f1">'
                f'{side if rng.random() < 0.7 else ""}{grid}{right}</div></div>')
    elif variant == "agenda":
        rows, n, k = "", today, 0
        focus = None
        while k < H // 34:
            dn = DAYS[n % 7]
            rows += f'<div class="row g8 px16 bg1 bb bt" style="min-height:calc(var(--rh) + 4px);flex:none"><span class="b{" acc" if n == today else ""}">{dn}, {month} {n}</span></div>'
            hr = rng.randint(7, 10)
            for _ in range(rng.randint(1, 4)):
                t, phrase = ev.take(n, f"the {_ord(n)}")
                if not t:
                    continue
                c = rng.choice(COLORS)
                attr = ev.reg(t, phrase, "the agenda list")
                focus = focus or (t, c, f"{dn}, {month} {n}", hr)
                who = "".join(ctx.av(p, 20) for p in d.people(6)[k % 3:k % 3 + rng.randint(1, 3)])
                rows += (f'<div class="tr{" sel" if focus[0] == t and focus[2].endswith(str(n)) else ""}"{attr}><div class="td mut" style="width:130px">{hr}:00 – {hr + 1}:{rng.choice(["00", "30"])}</div>'
                         f'<div class="td f"><span class="dot" style="background:{c}"></span><span class="el m">{esc(t)}</span></div><div class="td mut" style="width:150px"><span class="ca-snip">{rng.choice(PLACES)}</span></div>'
                         f'<div class="td" style="width:90px;gap:2px">{who}</div></div>')
                hr += rng.randint(1, 3)
                k += 1
            n += 1
            k += 1
        t, c, when, hr = focus
        guests = d.people(9)[4:4 + rng.randint(3, 5)]
        glist = "".join(f'<div class="row g8">{ctx.av(p, 24)}<span class="f1 el">{esc(p)}</span><span class="xs {st[1]}">{st[0]}</span></div>'
                        for p in guests for st in [rng.choice([("Accepted", "ok"), ("Declined", "err"), ("Awaiting", "mut"), ("Tentative", "wrn")])])
        region = "the event details"
        rsvp = ctx.seg([ctx.lab(x) for x in ctx.avail(["cal.yes", "cal.no", "cal.maybe"])], 0, region=region, noun="button", cids=ctx.avail(["cal.yes", "cal.no", "cal.maybe"]))
        detail = (f'<div class="side bl" style="width:{rng.choice([340, 380, 420])}px;background:var(--bg)"><div class="row g4 p8 bb">{ctx.ibtn("edit", region, obj="this event")}{ctx.ibtn("duplicate", region, obj="this event")}'
                  f'{ctx.ibtn("delete", region, obj="this event")}{ctx.ibtn("share", region, obj="this event")}{ctx.ibtn("more", region, obj="this event", anchor="more")}<div class="sp"></div>{ctx.ibtn("close.panel", region, obj="the event details")}</div>'
                  f'<div class="col g12 p16 f1 clip"><div class="row g10 top"><span class="dot" style="background:{c};width:14px;height:14px;border-radius:4px;margin-top:6px"></span><div class="col"><span class="xl b">{esc(t)}</span>'
                  f'<span class="mut">{when} · {hr}:00 – {hr + 1}:00</span></div></div>{ctx.tbtn("cal.join", region, cls="pri", icon=True)}'
                  f'<div class="row g8 mut">{ctx.deco("map-pin", "map-pinned", "navigation", "building", "door-open")}<span>{rng.choice(PLACES)}</span></div>'
                  f'<div class="row g8 mut">{ctx.deco("bell", "bell-ring", "alarm-clock", "clock", "timer")}<span>{rng.choice([10, 15, 30])} minutes before</span><div class="sp"></div>{ctx.tbtn("cal.remind", region, cls="ghost sm")}</div>'
                  f'<div class="hsep"></div><div class="row"><span class="b sp">{len(guests)} guests</span>{ctx.tbtn("cal.guests", region, cls="ghost sm", icon=True)}</div><div class="col g8">{glist}</div>'
                  f'<div class="hsep"></div><div class="mut">{esc(d.sentence())}</div><div class="sp"></div><div class="row g8"><span class="m">Going?</span><div class="sp"></div>{rsvp}</div></div></div>')
        main = f'<div class="col f1 clip">{rows}</div>'
        body = f'<div class="col f1">{_toolbar(ctx, f"{month} 2026", views, len(views) - 1, extra=acct)}<div class="row str f1">{side}{main}{detail}</div></div>'
    else:  # scheduler
        region = "the calendar toolbar"
        fl = "".join(ctx.select(f, f, options=["Any", "North wing", "2nd floor", "8+ seats", "Projector"], region="the filter bar", above=False, cls="rnd", w=rng.choice([140, 156]))
                     for f in d.take("sch.filters", SCH_FILTERS, 3))
        rooms = d.take("rooms", ROOMS, H // 46)
        rowh = max(46, min(84, (H - 320) // max(1, len(rooms))))
        h0, hours = 8, 11
        lw, form_w = rng.choice([170, 190]), (rng.choice([300, 330]) if W >= 1400 else 0)
        thead = "".join(f'<div class="f1 bl xs mut px8 py4">{(h0 + k - 1) % 12 + 1}:00 {"AM" if h0 + k < 12 else "PM"}</div>' for k in range(hours))
        lines = ""
        for r in rooms:
            ra = ctx.reg("nav", "room", r, region="the room list", refs=[f"the {r} room in the left column", f"the row header for {r}", f"{r} in the list of rooms"])
            cap = rng.choice([2, 4, 6, 8, 12, 20])
            blocks, t = "", rng.uniform(0, 3)
            while t < hours - 1:
                dur = rng.choice([0.5, 1, 1, 1.5, 2, 3])
                title, phrase = ev.take(r, f"the {r} row")
                if title and t + dur <= hours:
                    blocks += (f'<div class="ca-bk" style="left:{t / hours * 100:.2f}%;width:calc({dur / hours * 100:.2f}% - 3px);{_tint(rng.choice(COLORS), 26)}"'
                               f'{ctx.reg("row", "booking", title, region="the schedule grid", row=r, anchor="row")}><span class="el">{esc(title)}</span></div>')
                t += dur + rng.choice([0, 0.5, 1, 2, 3])
            lines += (f'<div class="row str bb" style="height:{rowh}px;flex:none"><div class="row g8 px12 br bg1" style="width:{lw}px;flex:none"{ra}><div class="col" style="min-width:0"><span class="m el">{esc(r)}</span>'
                      f'<span class="xs mut">{cap} seats</span></div></div><div class="rel f1" style="background:repeating-linear-gradient(to right,transparent 0,transparent calc({100 / hours:.4f}% - 1px),var(--bd) calc({100 / hours:.4f}% - 1px),var(--bd) {100 / hours:.4f}%)">{blocks}</div></div>')
        grid = (f'<div class="col f1 clip"><div class="row str bb bg1" style="flex:none"><div class="px12 py4 xs b mut br" style="width:{lw}px;flex:none">ROOM</div>{thead}</div><div class="col f1 clip">{lines}</div></div>')
        form = ""
        if form_w:
            fr = "the booking form"
            f1 = ctx.field(ctx.lab("cal.title"), "", ph="", region=fr, cid="cal.title") if ctx.has("cal.title") else ""
            f2 = ctx.select(ctx.lab("cal.f.room"), rooms[1], options=rooms[:5], region=fr, cid="cal.f.room") if ctx.has("cal.f.room") else ""
            f3 = ctx.field(ctx.lab("cal.where"), rng.choice(PLACES), region=fr, cid="cal.where") if ctx.has("cal.where") else ""
            t1 = ctx.select(ctx.lab("cal.f.start"), "10:00 AM", options=["9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM"], region=fr, cid="cal.f.start") if ctx.has("cal.f.start") else ""
            t2 = ctx.select(ctx.lab("cal.f.end"), "11:00 AM", options=["10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM"], region=fr, cid="cal.f.end") if ctx.has("cal.f.end") else ""
            times = f'<div class="row g8"><div class="f1">{t1}</div><div class="f1">{t2}</div></div>'
            togs = "".join(ctx.toggle_row(ctx.lab(c), rng.random() < 0.4, region=fr, cid=c, cls="py4") for c in ctx.avail(["cal.allday", "cal.recur"]))
            form = (f'<div class="side bl p16 g12" style="width:{form_w}px;background:var(--bg)"><div class="row"><span class="b lg sp">Booking</span>{ctx.ibtn("close.panel", fr, cls="s", obj="the booking form")}</div>'
                    f'{f1}{f2}{times}{f3}{togs}{ctx.tbtn("cal.guests", fr, cls="ghost", icon=True)}{ctx.tbtn("cal.findtime", fr, cls="ghost")}<div class="sp"></div>'
                    f'<div class="row g8 end">{ctx.tbtn("cancel", fr)}{ctx.tbtn("cal.book", fr, cls="pri")}</div></div>')
        bar = (f'<div class="tb" style="gap:8px;padding:6px 12px">{ctx.tbtn("cal.today", region)}{ctx.ibtn("cal.prev", region)}{ctx.ibtn("cal.next", region)}<span class="b lg nw">{DAYS[today % 7]}, {month} {today}</span>'
               f'<div class="sp"></div>{ctx.seg([ctx.lab(c) for c in views[:3]], 0, region=region, noun="view", cids=views[:3])}{ctx.search(region, w=180, cls="soft")}{ctx.ibtn("filter", region)}{ctx.ibtn("refresh", region, obj="the schedule")}{acct}{ctx.tbtn("cal.new", region, cls="pri", icon=True)}</div>'
               f'<div class="row g8 px12 py8 bb">{fl}<div class="sp"></div><span class="row g6 xs mut"><span class="dot" style="background:var(--ok)"></span>Free<span class="dot" style="background:var(--warn)"></span>Tentative<span class="dot" style="background:var(--err)"></span>Busy</span></div>')
        body = f'<div class="col f1">{bar}<div class="row str f1">{grid}{form}</div></div>'
    return {"title": f"Calendar — {month} 2026", "body": body, "css": CSS, "app": "Calendar",
            "menus": ["mb.file", "mb.edit", "mb.view", "mb.window", "mb.help"], "url": "calendar.example.com/r/" + month.lower()}
