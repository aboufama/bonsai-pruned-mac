"""Notes (folders, a list of notes, a plain-text editor): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
"""
import datetime

from ..oracle import Click, Drag, Key, Reveal, Type
from .base import Spec, by_id, cond, norm, only, say, task, unchanged, verdict

SIZE = (980, 640)
WIN = '.win[data-app="notes"] '
LAST_DAY = datetime.date(2026, 11, 1)        # the menu bar clock is between 2 and 12 Nov 2026; seeded notes are older

# Each note: its title (the first line) and the lines under it. Titles are distinct across all pools.
GENERAL = [
    ("Books to read", ["The Overstory", "Piranesi", "A Month in the Country", "Ask Leila for the title of that essay collection"]),
    ("Gift ideas for Mum", ["Linen apron from the market stall", "Refill for her fountain pen", "Tickets for the garden show in May", "Budget: about 60"]),
    ("Car service", ["Booked for Tuesday at 8:30", "Ask about the rattle on the passenger side", "Brake fluid was last changed two years ago", "Quote: 240"]),
    ("Questions for the landlord", ["When will the boiler be serviced?", "Can we repaint the hallway?", "Who pays for the new extractor fan?", "Bike storage in the courtyard"]),
    ("Flat measurements", ["Living room: 4.2 x 3.6 m", "Bedroom window: 118 cm wide", "Alcove by the door: 74 cm", "Ceiling height: 2.55 m"]),
    ("Plants to water", ["Fern: twice a week", "Rubber plant: every ten days", "Basil: daily, a little", "Cactus: once a month at most"]),
    ("Marathon training", ["Mon: rest", "Wed: 8 km easy", "Fri: intervals, 6 x 800 m", "Sun: long run, add 2 km each week"]),
    ("Dentist", ["Check-up on the 19th at 3:40 PM", "Ask about the chipped filling", "Bring the insurance card"]),
    ("Bike repair", ["Rear tyre has a slow puncture", "Chain needs oil", "The shop on Mill Lane closes at 6", "Ask for a quote on new brake pads"]),
    ("Neighbour's cat", ["Feed at 8 and at 6", "Half a tin each time", "Keys are under the blue pot", "Vet: Dr Haddad on Alder Row"]),
    ("Spanish vocabulary", ["la cuenta: the bill", "madrugar: to get up early", "el recado: the errand", "estrenar: to use for the first time"]),
    ("Insurance claim", ["Claim number 5521-08", "Sent photos of the ceiling on the 3rd", "Assessor visits next Thursday", "Keep all receipts"]),
    ("Phone plan", ["Current plan ends in January", "12 GB is not enough", "Compare the 30 GB offers", "Keep the old number"]),
    ("Speech for Oskar", ["Start with the story about the tent", "Thank Renata for organising", "Keep it under three minutes", "End with the toast"]),
    ("Garden notes", ["Tomatoes went in on the 4th", "Slugs got the lettuce again", "Compost bin is nearly full", "Order bulbs before October"]),
    ("Moving checklist", ["Give notice to the landlord", "Book the van for the 28th", "Redirect the post", "Read the meters on the last day"]),
    ("Camera settings", ["Portraits: f/2.8, ISO 200", "Night sky: 20 s, ISO 3200", "Always shoot RAW", "Clean the sensor before the trip"]),
    ("Choir rehearsal", ["Thursdays at 7:30 in the church hall", "Learn the alto line of the second piece", "Concert is on the 14th", "Black folder, not the blue one"]),
    ("Tax paperwork", ["Find the two missing receipts", "Download the bank statement for October", "Deadline is the end of January", "Ask Stefan about the home office rule"]),
    ("Paint colours", ["Hallway: warm white", "Bedroom: sage green, matt", "Two tins were enough last time", "Brushes are in the cellar"]),
    ("Weekend chores", ["Hoover the stairs", "Descale the kettle", "Take the glass to the recycling", "Change the bed sheets"]),
    ("School run rota", ["Mon and Wed: me", "Tue: Bianca", "Thu: Cormac", "Fri: whoever finishes early"]),
    ("Parking permit", ["Renew before the end of the month", "Need proof of address", "Zone C, 85 for the year", "The office is open until 4 on weekdays"]),
    ("Chess openings", ["Italian Game: keep it simple", "Caro-Kann against e4", "Stop moving the queen out early", "Review last week's lost game"]),
    ("Wine we liked", ["The red from the Georgian place", "Dry Riesling with the green label", "Not the orange one again", "Ask Bruno where he buys his"]),
    ("Meter readings", ["Electricity: 48213", "Gas: 9034", "Water: 612", "Read them on the first of the month"]),
    ("Thank-you cards", ["Aunt Ingrid for the blanket", "Kwame for the lift to the airport", "The neighbours for watering the plants", "Buy stamps first"]),
    ("Printer problems", ["Jams on thick paper", "Cyan is nearly empty", "The driver update did not help", "Warranty runs until March"]),
    ("Swimming times", ["Lane swimming: 6:30 to 8:00 on weekdays", "Family hour: Saturday at 10", "Closed on the first Monday of the month", "Bring a coin for the locker"]),
    ("Films to watch", ["The one about the lighthouse keeper", "That documentary on deep-sea cables", "Anything Daria recommends", "Not another three-hour epic"]),
    ("Book club", ["Next pick: the short story collection", "First meeting is on the 8th", "At Renata's place, bring snacks", "Read up to page 120"]),
    ("Running shoes", ["Size 43, wide fit", "The old pair lasted 800 km", "Try the shop near the station", "No more than 120"]),
    ("Balcony plants", ["Lavender in the big pot", "Mint needs its own container", "Geraniums on the railing", "Buy peat-free compost"]),
    ("Broadband", ["Contract ends on the 30th", "Speed drops every evening", "Engineer can come on Wednesday", "Ask for the loyalty discount"]),
    ("Babysitter details", ["Freya, the student from number 12", "Free on Fridays and Saturdays", "12 an hour", "Home by eleven"]),
    ("Piano practice", ["Scales for ten minutes first", "Left hand alone on the second page", "Slow down in bar 24", "Lesson moved to Wednesday at 5"]),
]
THEMES = {
    "Work": [
        ("Standup notes", ["Export bug is fixed and needs review", "Lisbon team joins at 10:15 from Monday", "Demo moved to Thursday", "I owe Tobias the test plan"]),
        ("Quarterly goals", ["Ship the new onboarding flow", "Cut support tickets by a fifth", "Hire one more designer", "Rewrite the pricing page"]),
        ("Interview questions", ["Tell me about a project that went wrong", "How do you decide what not to build?", "What would you change about our product?", "Leave ten minutes for their questions"]),
        ("Offsite agenda", ["9:30 coffee and arrivals", "10:00 review of last quarter", "13:00 lunch by the lake", "14:30 planning in small groups"]),
        ("Feedback for Priya", ["The new header works much better", "Search field is still hard to find", "Footer links are too pale", "Great work on the empty states"]),
        ("Client call with Northwind", ["They want the report monthly, not weekly", "Invoice 4471 is still open", "New contact is Dana Whitfield", "Send the summary by Friday"]),
        ("Expense report", ["Train to Lisbon: 86", "Hotel, two nights: 214", "Two receipts are missing", "Submit before the 25th"]),
        ("Conference talk outline", ["Open with the failed launch", "Three lessons, one slide each", "Live demo only if the wifi holds", "Abstract: 150 words at most"]),
        ("Release checklist", ["Freeze the branch on Wednesday", "Run the full test suite twice", "Update the changelog", "Tell support before it goes live"]),
        ("One-to-one with Marcus", ["Workload is fine for now", "Wants to lead the next project", "Training budget: ask finance", "Next meeting in two weeks"]),
    ],
    "Personal": [
        ("Flat hunting", ["14 Alder Row: bright, but no lift", "Mill Lane: too close to the tracks", "Viewing on Saturday at 11", "Bring a photo ID"]),
        ("Journal, Sunday", ["Slept late for once", "Long walk along the canal with Thea", "Finally called Grandma", "Feeling better about the move"]),
        ("Savings plan", ["Put 300 aside each month", "Close the old account", "Emergency fund: three months of rent", "Review in June"]),
        ("Gym routine", ["Mon: legs", "Wed: back and arms", "Fri: swim, 40 lengths", "Stretch for ten minutes afterwards"]),
        ("Names for the puppy", ["Biscuit", "Juno", "Pepper", "Not Rex, says Halima"]),
        ("Wedding guest list", ["Both sets of cousins", "Samir and his partner", "The choir, all eleven of them", "Ask Dad about Uncle Viktor"]),
        ("Doctor's advice", ["Less coffee after noon", "Walk for half an hour every day", "Blood test again in three months", "Call if the headaches come back"]),
        ("Birthdays", ["Mei: 3 March", "Jonas: 19 June", "Freya: 2 September", "Yusuf: 27 November"]),
        ("Meditation notes", ["Ten minutes before breakfast", "Count breaths up to ten, then start again", "Phone stays in the other room", "Harder on Mondays"]),
        ("Resolutions", ["Read two books a month", "Cook something new every Sunday", "Call home more often", "Learn to swim front crawl properly"]),
    ],
    "Recipes": [
        ("Lentil soup", ["2 cups red lentils", "1 onion, 2 carrots, 3 cloves of garlic", "Cumin, paprika and a bay leaf", "Simmer for 25 minutes, then add lemon"]),
        ("Banana bread", ["3 ripe bananas", "250 g flour, 100 g sugar", "2 eggs, 80 g butter", "50 minutes at 175 degrees"]),
        ("Sunday pancakes", ["200 g flour, 2 eggs, 300 ml milk", "A pinch of salt", "Rest the batter for half an hour", "The first one always sticks"]),
        ("Tomato sauce", ["2 tins of plum tomatoes", "Half an onion and a knob of butter", "45 minutes on a low heat", "Take the onion out at the end"]),
        ("Grandma's apple cake", ["4 sour apples, sliced thin", "200 g flour, 150 g sugar, 3 eggs", "Cinnamon on top", "40 minutes at 180 degrees"]),
        ("Overnight oats", ["50 g oats, 150 ml milk", "A spoon of yoghurt", "Grated apple and a few walnuts", "Leave in the fridge until morning"]),
        ("Roast chicken", ["1.6 kg bird, out of the fridge an hour before", "Lemon and thyme inside", "20 minutes at 220, then an hour at 180", "Rest for 15 minutes"]),
        ("Green curry", ["2 spoons of curry paste", "1 tin of coconut milk", "Aubergine, green beans, Thai basil", "Fish sauce and lime at the end"]),
        ("Focaccia", ["500 g strong flour, 400 ml water", "7 g yeast, 10 g salt", "Fold four times, then overnight in the fridge", "25 minutes at 230 degrees"]),
        ("Granola", ["300 g oats, 100 g mixed nuts", "3 spoons of honey, 2 of oil", "25 minutes at 160, stir halfway", "Add the raisins after baking"]),
    ],
    "Travel": [
        ("Lisbon trip", ["Flight at 07:35 from terminal 2", "Hotel near the river, two nights", "Tram 28 early in the morning", "Custard tarts at the place Rafael mentioned"]),
        ("Packing for the hike", ["Waterproof jacket and gaiters", "Two litres of water each", "Head torch and spare batteries", "Blister plasters"]),
        ("Train times to the coast", ["Out: 08:12 or 09:42, platform 4", "Back: 17:55, the last one is at 20:10", "Change at the junction on Sundays", "Off-peak return is 31"]),
        ("Japan ideas", ["Kyoto in the second week of November", "Rail pass for seven days", "A night in a ryokan with a bath", "Ask Aiko about the mountain temple"]),
        ("Passport renewal", ["Expires in April", "Two photos, no glasses", "Takes about three weeks", "Old passport has to be sent in too"]),
        ("Camping checklist", ["Tent, pegs and the mallet", "Stove and one full gas canister", "Sleeping mats", "Matches in a dry bag"]),
        ("Hotel shortlist", ["Harbour view: 140 a night, breakfast included", "The small one by the market: 95", "Hostel as a backup", "Book by Friday for the free cancellation"]),
        ("Road trip stops", ["Coffee at the bakery in the first village", "Viewpoint after the long tunnel", "Lunch by the reservoir", "Fill up before the pass"]),
        ("Phrases for Italy", ["Un tavolo per due, per favore", "Il conto, per favore", "Dov'è la stazione?", "Posso pagare con la carta?"]),
        ("Travel insurance", ["Policy ends in March", "Covers hiking up to 3000 m", "Excess is 100", "The emergency number is on the card"]),
    ],
    "Ideas": [
        ("App idea: plant diary", ["A photo of each plant once a week", "Reminders based on the season", "Share cuttings with neighbours", "Start with a paper prototype"]),
        ("Story about the lighthouse", ["The keeper finds a letter in a bottle", "It is addressed to her mother", "The second half is told by the sender", "Ending: she never replies"]),
        ("Podcast concept", ["Ten minutes, one object per episode", "Interview the person who repairs it", "Record in the workshop, not a studio", "Working title: Mended"]),
        ("Blog post topics", ["What I learned from a year of cycling to work", "Cheap lenses that are worth it", "How to read a train timetable", "Why I stopped tracking everything"]),
        ("Names for the band", ["Tidewater", "The Slow Ferries", "Copperline", "Anything but Samir's suggestion"]),
        ("Balcony makeover", ["Fold-down table on the left wall", "String lights along the railing", "Herbs in the old wine crate", "A rug that survives rain"]),
        ("Board game rules", ["Each player starts with five cards", "Trade only on your own turn", "The harbour tile is worth double", "Game ends when the deck runs out"]),
        ("Newsletter ideas", ["One recipe, one book, one walk", "Send it on the first Sunday", "Keep it under 400 words", "Ask Wanjiru for an illustration"]),
        ("Bread baking workshop", ["Six people at most", "Everyone takes home a starter", "Two hours on a Saturday morning", "Charge enough to cover the flour"]),
        ("Photo project: doors", ["One door from every street in the neighbourhood", "Same lens, same time of day", "Print them as a grid", "Forty so far"]),
    ],
}
NEW_TEXTS = ["Dentist moved to Thursday at 3", "The parcel is at the corner shop", "Call the bank about the new card", "Bring a charger for Halima",
             "Milk, eggs and coffee filters", "Renata's train arrives at 18:20", "Ask Jonas for the spare key", "Library books are due on Friday",
             "Pay the window cleaner 25", "Book a table for six on Saturday", "The blue folder is in the car", "Water the fern before leaving",
             "Return the drill to Bruno", "Meeting room is 2B, not 3A", "Buy stamps and two envelopes", "Yoga starts at seven this week",
             "Leave the keys with the neighbour", "Bin collection is on Wednesday now"]
EXTRA_LINES = ["Check this again on Friday", "Ask Priya what she thinks", "Remember to bring the receipt", "Updated after the call with Stefan",
               "Still waiting for a reply", "Sort this out before the end of the month", "Tobias has a spare one", "It costs more than expected",
               "Send a photo to Mei", "Try the shop on Mill Lane", "Half of this is done already", "Talk to Elena first", "Not before Tuesday",
               "Keep the old one for now", "Daria knows more about this", "Look at this again in the spring"]
REPLACEMENTS = ["Cancelled, see the email from Dana", "Moved to the shared folder", "Nothing to do here until spring", "All done on Saturday",
                "Postponed until Kwame is back", "See the new plan from Ingrid", "Sorted out by phone on Monday", "Replaced by the list on the fridge",
                "Waiting for the quote from Bruno", "Out of date, ask Marcus for the new version", "Handed over to Elena", "No longer needed"]


def default(rng):
    names = rng.sample(sorted(THEMES), rng.choice([3, 3, 4]))
    folders = [{"id": "f1", "name": "Notes"}] + [{"id": f"f{i + 2}", "name": n} for i, n in enumerate(names)]
    notes, used = [], set()

    def add(folder, title, rest, recent):
        for _ in range(200):
            back = int(rng.random() ** (3.0 if recent else 2.0) * 430)
            d = LAST_DAY - datetime.timedelta(days=back)
            date = f"{d.isoformat()} {rng.randint(7, 22):02d}:{rng.randint(0, 59):02d}"
            if date[:10] not in used:
                break
        used.add(date[:10])
        notes.append({"folder": folder, "body": "\n".join([title] + rest), "date": date, "pinned": False})

    for title, rest in rng.sample(GENERAL, rng.randint(24, 27)):
        add("f1", title, rest, True)
    for f in folders[1:]:
        pool = THEMES[f["name"]]
        for title, rest in rng.sample(pool, rng.randint(3, 8)):
            add(f["id"], title, rest, False)
    rng.shuffle(notes)
    for i, n in enumerate(notes):
        n["id"] = f"n{i + 1}"
    notes = [{"id": n["id"], "folder": n["folder"], "body": n["body"], "date": n["date"], "pinned": n["pinned"]} for n in notes]
    main = [n for n in notes if n["folder"] == "f1"]
    for n in rng.sample(main, rng.choice([2, 2, 3])):
        n["pinned"] = True
    for f in folders[1:]:
        if rng.random() < 0.5:
            rng.choice([n for n in notes if n["folder"] == f["id"]])["pinned"] = True
    s = {"folders": folders, "notes": notes, "next": len(notes) + 1, "ui": {"folder": "f1", "sel": None, "search": ""}}
    s["ui"]["sel"] = shown(s, "f1")[0]["id"]
    return s


# ------------------------------------------------------------------ helpers
def title(n):
    return next((line.strip() for line in n["body"].split("\n") if line.strip()), "New Note")


def shown(s, folder):
    """The notes of a folder in the order of the list column: pinned first, then newest first."""
    notes = sorted((n for n in s["notes"] if n["folder"] == folder), key=lambda n: n["date"], reverse=True)
    return [n for n in notes if n["pinned"]] + [n for n in notes if not n["pinned"]]


def show(s, folder):
    """Start with this folder open and its first note in the editor."""
    s["ui"].update(folder=folder, sel=shown(s, folder)[0]["id"], search="")


def folder_name(s, fid):
    return by_id(s["folders"], fid)["name"]


def note(st, i):
    return by_id(st["apps"]["notes"]["notes"], i)


def row(n):
    return WIN + f'.n-row[data-arg="{n["id"]}"]'


def side(fid):
    return WIN + f'.sb-item[data-arg="{fid}"]'


def text_lines(body):
    return [norm(line) for line in str(body).split("\n") if line.strip()]


def unused_titles(s):
    taken = {norm(title(n)) for n in s["notes"]}
    return [t for t, _ in GENERAL + [x for pool in THEMES.values() for x in pool] if norm(t) not in taken]


TOP = 6          # this many rows of the list are in view whatever the section headers above them


def vary(S, tid):
    """The tasks of one seed would otherwise all make the same picks (same folder, same row, same
    window position), because each starts from the same random state."""
    S.rng.seed(f"{S.seed}/{tid}")


# ------------------------------------------------------------------ tasks
@task("notes.new_note", "typing")
def new_note(S):
    vary(S, "notes.new_note")
    s = S.apps["notes"]
    f = S.rng.choice(s["folders"])
    start = f if S.rng.random() < 0.5 else S.rng.choice([x for x in s["folders"] if x["id"] != f["id"]])
    show(s, start["id"])
    text = S.rng.choice(NEW_TEXTS)
    S.open("notes")

    def check(st, init):
        old = {n["id"] for n in init["apps"]["notes"]["notes"]}
        new = [n for n in st["apps"]["notes"]["notes"] if n["id"] not in old]
        return verdict(cond(len(new) == 1, f"{len(new)} notes were added, not one"),
                       cond(new and norm(new[0]["body"]) == norm(text), f"the new note says “{new[0]['body'] if new else ''}”"),
                       cond(new and new[0]["folder"] == f["id"], f"the new note is not in {f['name']}"),
                       cond(new and not new[0]["pinned"], "the new note is pinned"),
                       only(st, init, "notes.notes.+*", "notes.next"))
    steps = [] if start["id"] == f["id"] else [Click(side(f["id"]), f"Click the folder “{f['name']}” in the sidebar of Notes")]
    steps += [Click(WIN + '.tb-btn[data-act="new"]', "Click the new note button (a pencil on a square) in the Notes toolbar"), Type(text)]
    return Spec(request=say(S.rng, f"Create a new note in my {f['name']} folder that says “{text}”.",
                            f"Make a note in the {f['name']} folder in Notes. It should just say: {text}"),
                steps=steps, check=check)


@task("notes.add_line", "typing")
def add_line(S):
    vary(S, "notes.add_line")
    s = S.apps["notes"]
    f = S.rng.choice(s["folders"])
    show(s, f["id"])
    n = S.rng.choice(shown(s, f["id"])[1:TOP])
    line = S.rng.choice(EXTRA_LINES)
    before = text_lines(n["body"])
    S.open("notes")

    def check(st, init):
        now = text_lines(note(st, n["id"])["body"]) if note(st, n["id"]) else []
        return verdict(cond(now[:len(before)] == before, "the text that was already in the note has changed"),
                       cond(now[len(before):] == [norm(line)], "the new line is not on a line of its own at the end of the note"),
                       only(st, init, f"notes.notes.{n['id']}.body"))
    return Spec(request=say(S.rng, f"Add the line “{line}” at the end of my “{title(n)}” note.",
                            f"In the note called “{title(n)}”, put “{line}” on a new line at the bottom."),
                steps=[Click(row(n), f"Click the note “{title(n)}” in the list of notes"),
                       Click(WIN + ".n-tail", "Click the empty space just below the last line of the note’s text"),
                       Key("enter"), Type(line)],
                check=check)


@task("notes.open_note", "single")
def open_note(S):
    vary(S, "notes.open_note")
    s = S.apps["notes"]
    f = S.rng.choice(s["folders"])
    show(s, f["id"])
    n = S.rng.choice(shown(s, f["id"])[1:TOP])
    S.open("notes")
    return Spec(request=say(S.rng, f"Open my “{title(n)}” note.", f"Show me the note called “{title(n)}”."),
                steps=[Click(row(n), f"Click the note “{title(n)}” in the list of notes")],
                check=lambda st, init: verdict(cond(st["apps"]["notes"]["ui"]["sel"] == n["id"], "that note is not the one open in the editor"),
                                               unchanged(st, init)))


@task("notes.move_note", "drag")
def move_note(S):
    vary(S, "notes.move_note")
    s = S.apps["notes"]
    f = S.rng.choice(s["folders"])
    show(s, f["id"])
    n = S.rng.choice(shown(s, f["id"])[:TOP])
    d = S.rng.choice([x for x in s["folders"] if x["id"] != f["id"]])
    S.open("notes")
    return Spec(request=say(S.rng, f"Move my “{title(n)}” note into the {d['name']} folder.",
                            f"The note “{title(n)}” belongs in {d['name']}. Put it there."),
                steps=[Drag(row(n), side(d["id"]), f"the note “{title(n)}” in the list of notes", f"the folder “{d['name']}” in the sidebar of Notes")],
                check=lambda st, init: verdict(cond(note(st, n["id"]) and note(st, n["id"])["folder"] == d["id"], f"the note is not in {d['name']}"),
                                               only(st, init, f"notes.notes.{n['id']}.folder")))


@task("notes.pin_note", "menu")
def pin_note(S):
    vary(S, "notes.pin_note")
    s = S.apps["notes"]
    f = S.rng.choice(s["folders"])
    show(s, f["id"])
    n = S.rng.choice([x for x in shown(s, f["id"])[:TOP] if not x["pinned"]])
    S.open("notes")
    return Spec(request=say(S.rng, f"Pin my “{title(n)}” note.", f"Pin the note called “{title(n)}” so it stays at the top of the list."),
                steps=[Click(row(n), f"Right-click the note “{title(n)}” in the list of notes", button="right"),
                       Click('.menu-item:has(.mi-label:text-is("Pin Note"))', "Click “Pin Note” in the menu")],
                check=lambda st, init: verdict(cond(note(st, n["id"]) and note(st, n["id"])["pinned"] is True, "the note is not pinned"),
                                               only(st, init, f"notes.notes.{n['id']}.pinned")))


@task("notes.replace_text", "shortcut")
def replace_text(S):
    vary(S, "notes.replace_text")
    s = S.apps["notes"]
    f = S.rng.choice(s["folders"])
    show(s, f["id"])
    n = S.rng.choice(shown(s, f["id"])[1:TOP])
    text = S.rng.choice(REPLACEMENTS)
    S.open("notes")
    return Spec(request=say(S.rng, f"Replace everything in my “{title(n)}” note with “{text}”.",
                            f"Wipe the note called “{title(n)}” and write just this in it: {text}"),
                steps=[Click(row(n), f"Click the note “{title(n)}” in the list of notes"),
                       Click(WIN + ".n-text", "Click on the text of the note in the editor"),
                       Key("cmd+a"), Type(text)],
                check=lambda st, init: verdict(cond(note(st, n["id"]) and norm(note(st, n["id"])["body"]) == norm(text),
                                                    f"the note says “{note(st, n['id'])['body'] if note(st, n['id']) else ''}”"),
                                               only(st, init, f"notes.notes.{n['id']}.body")))


@task("notes.delete_far", "scroll")
def delete_far(S):
    vary(S, "notes.delete_far")
    s = S.apps["notes"]
    show(s, "f1")
    n = S.rng.choice(shown(s, "f1")[14:])
    S.open("notes")
    return Spec(request=say(S.rng, f"Delete my “{title(n)}” note.", f"I don't need the note called “{title(n)}” any more. Delete it."),
                steps=[Reveal(row(n)),
                       Click(row(n), f"Right-click the note “{title(n)}” in the list of notes", button="right"),
                       Click('.menu-item:has(.mi-label:text-is("Delete"))', "Click “Delete” in the menu")],
                check=lambda st, init: verdict(cond(note(st, n["id"]) is None, "the note is still there"),
                                               only(st, init, f"notes.notes.-{n['id']}")))


@task("notes.already_pinned", "already_done")
def already_pinned(S):
    vary(S, "notes.already_pinned")
    s = S.apps["notes"]
    f = S.rng.choice([x for x in s["folders"] if any(n["pinned"] for n in shown(s, x["id"]))])
    show(s, f["id"])
    n = S.rng.choice([x for x in shown(s, f["id"]) if x["pinned"]])
    S.open("notes")
    return Spec(request=say(S.rng, f"Pin my “{title(n)}” note.", f"Make sure the note called “{title(n)}” is pinned."),
                steps=[], kind="already_done", check=unchanged)


@task("notes.missing_note", "infeasible")
def missing_note(S):
    vary(S, "notes.missing_note")
    s = S.apps["notes"]
    f = S.rng.choice(s["folders"])
    show(s, f["id"])
    ghost = S.rng.choice(unused_titles(s))
    S.open("notes")
    return Spec(request=say(S.rng, f"Delete my “{ghost}” note.", f"Find the note called “{ghost}” in Notes and pin it."),
                steps=[], kind="infeasible", check=unchanged)
