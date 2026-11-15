"""Calendar (day, week and month views of seeded events): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

Dates are ISO strings, times are hours (14.5 is 2:30 PM), weeks start on Monday. At the start the
week view shows about 7 AM to 7 PM: day events lie between 8 AM and 6 PM, evening events start
at 7:30 PM or later and are below the fold.
"""
import datetime
import re

from ..oracle import Click, Drag, Key, Reveal, Type
from .base import Spec, by_id, cond, norm, only, say, task, unchanged, verdict

SIZE = (1060, 680)
WIN = '.win[data-app="calendar"] '
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
COLORS = ["#ff2968", "#ff9500", "#4fc92f", "#1badf8", "#cc73e1", "#a2845e"]
CAL_NAMES = {"work": ["Work", "Office", "Clients"], "home": ["Home", "Personal", "Errands"], "family": ["Family", "Kids"],
             "social": ["Friends", "Social"], "fitness": ["Fitness", "Training"], "school": ["School", "Courses", "Study"]}
# Titles are short (they sit in a narrow column) and none is part of another.
TITLES = {
    "work": {"day": ["Team standup", "Budget review", "Design critique", "Client call", "Sprint planning", "Interview panel", "Roadmap sync",
                     "Vendor demo", "Press briefing", "Payroll cutoff", "Board prep", "Site visit", "Legal review", "Hiring sync",
                     "Sales forecast", "Product demo", "Staff meeting", "Audit check-in"],
             "eve": ["Team dinner", "Late deploy", "Client drinks", "Awards dinner"]},
    "home": {"day": ["Dentist", "Car service", "Haircut", "Plumber visit", "Grocery run", "Vet checkup", "Bank meeting", "Parcel pickup",
                     "Boiler check", "Eye test", "Window cleaner", "Passport office", "Tyre change", "Flat viewing"],
             "eve": ["Laundry night", "Meal prep", "Call landlord", "Pack suitcase"]},
    "family": {"day": ["School run", "Piano lesson", "Swim lesson", "Lunch with Mum", "Nursery visit", "Football club", "Pediatrician",
                       "Zoo trip", "Scout meeting"],
               "eve": ["Parent evening", "Movie night", "Family dinner", "Call Grandad", "School concert"]},
    "social": {"day": ["Coffee with Mei", "Brunch", "Museum trip", "Lunch with Samir", "Farmers market", "Picnic"],
               "eve": ["Book club", "Pub quiz", "Board games", "Dinner with Thea", "Cinema", "Choir practice", "Jazz night", "Karaoke"]},
    "fitness": {"day": ["Yoga class", "Spin class", "Morning run", "Pilates", "Physio session", "Swim laps", "Tennis", "Bike ride"],
                "eve": ["Climbing gym", "Five-a-side", "Evening run", "Boxing class", "Dance class"]},
    "school": {"day": ["Stats lecture", "Lab session", "Study group", "Office hours", "Seminar", "Library shift", "Thesis meeting", "Tutorial"],
               "eve": ["Evening class", "Essay deadline", "Exam revision", "Debate club"]},
}
# Titles that only make sense at some hours: first and last possible start.
HOURS = {"Team standup": (8, 10), "Morning run": (8, 9), "School run": (8, 9), "Farmers market": (8, 11), "Brunch": (10, 12),
         "Lunch with Mum": (12, 13), "Lunch with Samir": (12, 13), "Picnic": (12, 14), "Nursery visit": (8, 12)}
DAY = datetime.timedelta(days=1)


def default(rng):
    today = datetime.date(2026, 11, rng.randint(9, 20))
    monday = today - DAY * today.weekday()
    kinds = ["work", "home", "family"] + rng.sample(["social", "fitness", "school"], rng.choice([1, 2]))
    rng.shuffle(kinds)
    colors = rng.sample(COLORS, len(kinds))
    calendars = [{"id": f"c{i + 1}", "name": rng.choice(CAL_NAMES[k]), "color": colors[i], "shown": True} for i, k in enumerate(kinds)]
    cal_of = {k: c["id"] for k, c in zip(kinds, calendars)}
    pool = {k: {part: rng.sample(TITLES[k][part], len(TITLES[k][part])) for part in ("day", "eve")} for k in kinds}
    events, busy = [], {}

    def put(kind, part, date):
        """One event of this kind on this date, clear of the others of that day; False if it does not fit."""
        slots = busy.setdefault(date, [])
        if not pool[kind][part] or len(slots) >= 4:
            return False
        title = pool[kind][part].pop()
        lo, hi = HOURS.get(title, (8, 16))
        for _ in range(30):
            if part == "eve":
                start, dur = rng.choice([19.5, 20, 20, 20.5, 21]), rng.choice([1, 1, 1.5, 2])
            else:
                start, dur = rng.randint(lo, hi) + rng.choice([0, 0, 0, 0.5]), rng.choice([0.5, 1, 1, 1, 1.5, 2])
                if start + dur > 18:
                    continue
            if all(start >= b or start + dur <= a for a, b in slots):
                slots.append((start, start + dur))
                events.append({"id": f"e{len(events) + 1}", "title": title, "cal": cal_of[kind],
                               "date": date.isoformat(), "start": int(start) if start == int(start) else start, "dur": dur})
                return True
        pool[kind][part].insert(0, title)
        return False

    def fill(first, n_day, n_eve):
        for d in rng.sample(range(7), n_eve):
            for kind in rng.sample(kinds, len(kinds)):
                if put(kind, "eve", first + DAY * d):
                    break
        placed = 0
        for _ in range(400):
            if placed == n_day:
                break
            kind = rng.choices(kinds, [4 if k == "work" else 2 for k in kinds])[0]
            placed += put(kind, "day", first + DAY * rng.randrange(5 if kind in ("work", "school") else 7))

    fill(monday, rng.randint(10, 15), rng.choice([2, 2, 3]))
    fill(monday - 7 * DAY, rng.randint(4, 6), rng.choice([0, 1]))
    fill(monday + 7 * DAY, rng.randint(4, 6), rng.choice([0, 1]))
    return {"today": today.isoformat(), "calendars": calendars, "events": events, "next": 1,
            "ui": {"view": "week", "anchor": today.isoformat(), "sel": None, "edit": None, "draft": "", "search": ""}}


# ------------------------------------------------------------------ helpers
def date_of(iso):
    try:
        return datetime.date.fromisoformat(str(iso))
    except ValueError:
        return None


def monday_of(iso):
    d = date_of(iso)
    return d and (d - DAY * d.weekday()).isoformat()


def week(s):
    """ISO dates of the week on screen at the start, Monday first."""
    first = date_of(monday_of(s["ui"]["anchor"]))
    return [(first + DAY * i).isoformat() for i in range(7)]


def this_week(s):
    days = week(s)
    return [e for e in s["events"] if e["date"] in days]


def day_events(s):
    """Events of the week that are fully in view at the start."""
    return [e for e in this_week(s) if e["start"] >= 8 and e["start"] + e["dur"] <= 18]


def is_free(s, date, start, dur):
    return not any(e["date"] == date and e["start"] < start + dur and start < e["start"] + e["dur"] for e in s["events"])


def clock(h):
    m = round(h * 60)
    return f"{(m // 60) % 12 or 12}{':%02d' % (m % 60) if m % 60 else ''} {'AM' if (m // 60) % 24 < 12 else 'PM'}"


def weekday(iso):
    return WEEKDAYS[date_of(iso).weekday()]


def day_text(iso):
    d = date_of(iso)
    return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"


def ordinal(n):
    return f"{n}{'th' if 10 < n % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def fresh_title(rng, s, parts=("day", "eve")):
    """A title from the pools that is not in the calendar, nor part of a title that is."""
    taken = [e["title"].lower() for e in s["events"]]
    every = sorted(t for k in TITLES.values() for part in parts for t in k[part] if t not in HOURS)
    return rng.choice([t for t in every if not any(t.lower() in x or x in t.lower() for x in taken)])


def block(e):
    return WIN + f'[data-drag="{e["id"]}"]'


def cell(date, hour):
    return WIN + f'.cv-cell[data-drop="{date}@{hour}"]'


def scene(S):
    """The Calendar window in front; the menu bar clock shows the calendar's own today."""
    s = S.apps["calendar"]
    S.open("calendar")
    t = date_of(s["today"])
    hour = re.search(r"\d{1,2}:\d\d\s*[AP]M", S.state["status"].get("clock", ""))
    S.state["status"]["clock"] = f"{WEEKDAYS[t.weekday()][:3]} {t.day} {MONTHS[t.month - 1][:3]}  {hour.group(0) if hour else '9:41 AM'}"
    return s


def app(st):
    return st["apps"]["calendar"]


def event(st, i):
    return by_id(app(st)["events"], i)


# ------------------------------------------------------------------ tasks
@task("calendar.change_week", "single")
def change_week(S):
    s = scene(S)
    step = S.rng.choice([1, 1, -1])
    want = date_of(week(s)[0]) + 7 * DAY * step

    def check(st, init):
        u = app(st)["ui"]
        return verdict(cond(u["view"] == "week", "the calendar is not in week view"),
                       cond(monday_of(u["anchor"]) == want.isoformat(), "the calendar does not show that week"),
                       unchanged(st, init))
    if step > 0:
        request = say(S.rng, "Show me next week in the calendar.", f"Go to the week that starts on Monday {want.day} November.")
        steps = [Click(WIN + '.cv-nav [data-act="next"]', "Click the next arrow (›) to the right of the “Today” button")]
    else:
        request = say(S.rng, "Show me last week in the calendar.", f"Go back to the week that starts on Monday {want.day} November.")
        steps = [Click(WIN + '.cv-nav [data-act="prev"]', "Click the previous arrow (‹) to the left of the “Today” button")]
    return Spec(request=request, steps=steps, check=check)


@task("calendar.hide_calendar", "single")
def hide_calendar(S):
    s = scene(S)
    c = S.rng.choice(s["calendars"])
    return Spec(request=say(S.rng, f"Hide the {c['name']} calendar.", f"I don't want to see my {c['name']} events right now. Turn that calendar off."),
                steps=[Click(WIN + f'.cv-check[data-arg="{c["id"]}"]', f"Click the checkbox next to “{c['name']}” in the sidebar")],
                check=lambda st, init: verdict(cond(by_id(app(st)["calendars"], c["id"])["shown"] is False, f"the {c['name']} calendar is still shown"),
                                               only(st, init, f"calendar.calendars.{c['id']}.shown")))


@task("calendar.month_ahead", "chain")
def month_ahead(S):
    s = scene(S)
    step = S.rng.choice([1, 1, -1])
    want, name = ("2026-12", "December") if step > 0 else ("2026-10", "October")

    def check(st, init):
        u = app(st)["ui"]
        return verdict(cond(u["view"] == "month", "the calendar is not in month view"),
                       cond(str(u["anchor"])[:7] == want, f"the calendar does not show {name}"),
                       unchanged(st, init))
    if step > 0:
        request = say(S.rng, "Switch the calendar to month view and go to next month.", "Show me the whole month, then move on to December.")
        arrow = Click(WIN + '.cv-nav [data-act="next"]', "Click the next arrow (›) to the right of the “Today” button")
    else:
        request = say(S.rng, "Switch the calendar to month view and go back one month.", "Show me the whole month, then go back to October.")
        arrow = Click(WIN + '.cv-nav [data-act="prev"]', "Click the previous arrow (‹) to the left of the “Today” button")
    return Spec(request=request, steps=[Click(WIN + '.seg span:text-is("Month")', "Click “Month” at the top of the Calendar window"), arrow], check=check)


@task("calendar.new_event", "typing")
def new_event(S):
    s = scene(S)
    date, hour = S.rng.choice([(d, h) for d in week(s) for h in range(8, 18) if is_free(s, d, h, 1)])
    title = fresh_title(S.rng, s, ("day",))

    def check(st, init):
        old = {e["id"] for e in app(init)["events"]}
        new = [e for e in app(st)["events"] if e["id"] not in old]
        return verdict(cond(len(new) == 1, "there is not exactly one new event"),
                       cond(new and norm(new[0]["title"]) == norm(title), f"the new event is called “{new[0]['title'] if new else ''}”"),
                       cond(new and new[0]["date"] == date, f"the new event is not on {day_text(date)}"),
                       cond(new and new[0]["start"] == hour, f"the new event does not start at {clock(hour)}"),
                       only(st, init, "calendar.events.+*", "calendar.next"))
    return Spec(request=say(S.rng, f"Add an event called “{title}” on {day_text(date)} at {clock(hour)}.",
                            f"Put “{title}” in my calendar: {clock(hour)} on {weekday(date)} the {ordinal(date_of(date).day)}."),
                steps=[Click(cell(date, hour), f"Double-click the empty {clock(hour)} slot in the {weekday(date)} column", count=2),
                       Type(title), Key("enter")],
                check=check)


@task("calendar.move_event", "drag")
def move_event(S):
    s = scene(S)
    pairs = [(e, d) for e in day_events(s) if e["start"] == int(e["start"]) and e["dur"] <= 1.5
             for d in week(s) if d != e["date"] and is_free(s, d, e["start"], e["dur"])]
    e, date = S.rng.choice(pairs)
    return Spec(request=say(S.rng, f"Move “{e['title']}” to {day_text(date)}, at the same time of day.",
                            f"Reschedule the “{e['title']}” event to {weekday(date)} this week. Keep the time as it is."),
                steps=[Drag(block(e), cell(date, int(e["start"])), f"the event “{e['title']}”",
                            f"the empty {clock(e['start'])} slot in the {weekday(date)} column")],
                check=lambda st, init: verdict(cond(event(st, e["id"]) and event(st, e["id"])["date"] == date, f"the event is not on {day_text(date)}"),
                                               only(st, init, f"calendar.events.{e['id']}.date")))


@task("calendar.change_calendar", "menu")
def change_calendar(S):
    s = scene(S)
    e = S.rng.choice(day_events(s))
    c = S.rng.choice([c for c in s["calendars"] if c["id"] != e["cal"]])
    return Spec(request=say(S.rng, f"Move the “{e['title']}” event to the {c['name']} calendar.",
                            f"“{e['title']}” is in the wrong calendar. It belongs in {c['name']}."),
                steps=[Click(block(e), f"Right-click the event “{e['title']}”", button="right"),
                       Click('.menu-item:has(.mi-label:text-is("Calendar"))', "Click “Calendar” in the menu"),
                       Click(f'.menu + .menu .menu-item:has(.mi-label:text-is("{c["name"]}"))', f"Click “{c['name']}” in the submenu")],
                check=lambda st, init: verdict(cond(event(st, e["id"]) and event(st, e["id"])["cal"] == c["id"], f"the event is not in the {c['name']} calendar"),
                                               only(st, init, f"calendar.events.{e['id']}.cal")))


@task("calendar.delete_event", "shortcut")
def delete_event(S):
    s = scene(S)
    e = S.rng.choice(day_events(s))
    return Spec(request=say(S.rng, f"Delete the “{e['title']}” event.", f"“{e['title']}” on {weekday(e['date'])} is cancelled. Remove it from my calendar."),
                steps=[Click(block(e), f"Click the event “{e['title']}”"), Key("backspace")],
                check=lambda st, init: verdict(cond(event(st, e["id"]) is None, "the event is still in the calendar"),
                                               only(st, init, f"calendar.events.-{e['id']}")))


@task("calendar.delete_evening", "scroll")
def delete_evening(S):
    s = scene(S)
    e = S.rng.choice([e for e in this_week(s) if e["start"] >= 19.5])
    return Spec(request=say(S.rng, f"Delete “{e['title']}” from {weekday(e['date'])} evening.",
                            f"I'm not going to “{e['title']}” on {weekday(e['date'])} night after all. Take it out of the calendar."),
                steps=[Reveal(block(e)), Click(block(e), f"Click the event “{e['title']}”"), Key("backspace")],
                check=lambda st, init: verdict(cond(event(st, e["id"]) is None, "the event is still in the calendar"),
                                               only(st, init, f"calendar.events.-{e['id']}")))


@task("calendar.already_set", "already_done")
def already_set(S):
    s = scene(S)
    if S.rng.random() < 0.5:
        request = say(S.rng, "Show the calendar one week at a time.", "Make sure the calendar is in week view.")
        check = lambda st, init: verdict(cond(app(st)["ui"]["view"] == "week", "the calendar is no longer in week view"), unchanged(st, init))
    else:
        c = S.rng.choice(s["calendars"])
        c["shown"] = False
        request = say(S.rng, f"Make sure the {c['name']} calendar is hidden.", f"The {c['name']} calendar should be switched off. Turn it off if it isn't.")
        check = unchanged
    return Spec(request=request, steps=[], kind="already_done", check=check)


@task("calendar.missing_event", "infeasible")
def missing_event(S):
    s = scene(S)
    ghost = fresh_title(S.rng, s)
    day = weekday(S.rng.choice(week(s)))
    c = S.rng.choice(s["calendars"])
    return Spec(request=say(S.rng, f"Delete the “{ghost}” event on {day}.", f"Move “{ghost}” on {day} to the {c['name']} calendar."),
                steps=[], kind="infeasible", check=unchanged)
