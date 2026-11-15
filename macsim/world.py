"""macsim: seeded desktops for TRAINING. Word pools and scene builders.

Nothing here comes from the test environment (taskenv/): the pools were written for this folder
and `python -m macsim.check_heldout` verifies that no name, title or sentence is shared.

    build(seed, split) -> (state, post)
state is what the shell boots (screen size, appearance, Dock, menu-bar extras, one to three app
windows with their contents); post is a list of things to do in the browser before the picture
is taken (open a menu, right-click an item), so that menus are the page's own.
Train and dev differ in the seed space AND in a layout switch (dev uses window arrangements,
accent colours and wallpapers that train never draws).
"""
import datetime
import random

SCREENS = [(1470, 956, 33), (1440, 900, 24), (1512, 982, 37), (1728, 1117, 37), (1280, 800, 24)]       # points, menu-bar height
ACCENTS = {"train": ["#0a7aff", "#a550a7", "#f74f9e", "#f7821b", "#62ba46"], "dev": ["#ff5257", "#ffc600", "#8c8c8c"]}
WALLS = {"train": [0, 1, 2, 3], "dev": [4, 5]}
FIRST = ["Aoife", "Bastien", "Chiara", "Dmitri", "Esme", "Farid", "Greta", "Hiro", "Imani", "Joaquin", "Katya", "Lorenzo", "Maeve", "Nikolai", "Odette", "Pavel",
         "Quentin", "Rosalind", "Soren", "Tamsin", "Ulises", "Vesna", "Wilhelmina", "Xavier", "Yara", "Zoltan", "Anneli", "Benedikt", "Celeste", "Evander"]
LAST = ["Abernathy", "Bellweather", "Castellanos", "Drummond", "Ekström", "Fairbanks", "Galloway", "Hargreaves", "Iwasaki", "Jovanovic", "Kensington", "Lachance",
        "Montgomery", "Nakamura", "Oyelaran", "Pemberton", "Quenneville", "Rasmussen", "Santangelo", "Thackeray", "Umarov", "Valdivia", "Winterbourne", "Yamamoto", "Zubiri"]
CALS = [("Bindery", "#1badf8"), ("Household", "#63da38"), ("Relatives", "#ff9500"), ("Evening classes", "#cc73e1"), ("Trips", "#ff2968"), ("Rowing", "#34c759"), ("Volunteering", "#a2845e"), ("Side project", "#5ac8fa"), ("Check-ups", "#ff3b30"), ("Choir", "#ffcc00")]
EVENTS = ["Stand-up", "Ledger check-in", "Dentist check-up", "Parent-teacher evening", "Planning poker", "Lunch with Odette", "Flight to Lisbon", "Swim practice", "Reading circle", "1:1 with Pavel", "Mock-up walkthrough", "Vet appointment", "Guitar lesson",
          "Quarterly all-hands", "Car inspection", "Coffee with Hiro", "Pick up dry cleaning", "Yoga", "Board meeting", "Recycling day", "Department away-day", "Call the landlord", "Osteopath", "Warehouse tour", "Release review", "Film society screening", "Barber",
          "Pottery class", "Interview: backend role", "Tax appointment", "Dinner at Tamsin's", "Long run with the club", "Roadmap workshop", "School play", "Client demo", "Farmers' market"]
FOLDERS = ["Invoices 2026", "Kitchen renovation", "Thesis", "Screenshots", "Boat papers", "Client handover", "Contracts", "Scanned letters", "Till slips", "Field recordings", "Presentations", "Anniversary trip", "Tax 2025", "Reading group", "Garden plans", "Old laptop backup", "Typefaces", "Moodboards"]
FILES = [("Q3 forecast", "sheet"), ("Lease agreement", "pdf"), ("standup-minutes", "text"), ("IMG_4821", "image"), ("Passport scan", "pdf"), ("pitch-v7", "pdf"), ("interview-audio", "audio"), ("site-photos", "zip"), ("Holiday budget", "sheet"), ("todo", "text"),
         ("Loft layout", "pdf"), ("logo-final-FINAL", "image"), ("Quartet take 3", "audio"), ("Starter pack", "pdf"), ("screen-recording", "movie"), ("Insurance letter", "pdf"), ("marinades", "text"), ("Team photo", "image"), ("Expenses March", "sheet"),
         ("Podcast episode 12", "audio"), ("backup-2025", "zip"), ("Ferry ticket", "pdf"), ("draft-chapter-3", "text"), ("Panorama", "image"), ("Demo cut", "movie"), ("Mileage log", "sheet"), ("Warranty", "pdf"), ("lyrics", "text")]
EXT = {"sheet": ".numbers", "pdf": ".pdf", "text": ".txt", "image": ".heic", "audio": ".m4a", "zip": ".zip", "movie": ".mov"}
SUBJECTS = [("Your March statement is ready", "Your statement for the period ending 31 March is now available. Sign in to view or download it."), ("Re: Friday handover", "Works for me. I will bring the printed checklist and the spare keys."), ("Invitation: Roadmap workshop", "You are invited to the roadmap workshop on Thursday. Please accept or decline."),
            ("Delivery scheduled for tomorrow", "Your parcel will arrive between 9 and 12. You can change the delivery window until midnight."), ("Minutes from the tenants' meeting", "Attached are the minutes. The vote on the bike shelter passed, 14 to 3."), ("Can you review my draft?", "I have rewritten the introduction. Two pages, should take ten minutes."),
            ("Reset your password", "Someone asked to reset the password for your account. If that was you, use the link below."), ("Weekend plans", "The forecast looks dry on Saturday. Shall we try the coastal path?"), ("Receipt for your payment", "Thank you. We received your payment of 84.50 for order 77120."), ("New sign-in to your account", "We noticed a sign-in from a new device. If this was you, no action is needed."),
            ("Reminder: library books due", "Three items are due back on Monday. You can renew them once online."), ("Itinerary change", "Your connecting flight now departs 40 minutes later. Your seat is unchanged."), ("Photos from Sunday", "I put the best ones in the shared album. The one by the lighthouse is my favourite."), ("Offer letter", "We are delighted to offer you the position. The details are attached."),
            ("Notes for tomorrow's call", "Agenda: timeline, staffing, the open question about hosting."), ("Your subscription renews soon", "Your yearly plan renews on 2 May. No action is needed to continue."), ("Thank you for volunteering", "Your shift on the 14th is confirmed. Please arrive fifteen minutes early."), ("Appointment confirmed", "We look forward to seeing you on Tuesday at 10:20. Bring your insurance card.")]
NOTES = [("Packing list", ["Passport and tickets", "[ ] Charger and adapter", "[x] Rain jacket", "[ ] Sunscreen", "Leave keys with the neighbour"]), ("Ideas for the talk", ["Open with the bridge story", "Three numbers, no more", "End on the question from the workshop"]), ("Presents for Odette", ["[ ] A good bread knife", "[ ] Concert tickets", "[x] The blue scarf"]),
         ("Wi-Fi at the cabin", ["Network: Birchwood", "Router is behind the bookshelf", "Restart it if the light is orange"]), ("Sourdough schedule", ["Feed starter at 8", "Mix at noon", "Fold every 30 minutes, four times", "Bake at 230 for 40 minutes"]), ("Questions for the architect", ["Can the stairs move?", "Cost of the larger window", "Timeline for permits"]),
         ("Reading pile", ["[x] The long winter", "[ ] A field guide to getting lost", "[ ] Salt"]), ("Garage visit", ["Front brake pads", "Ask about the rattle on cold starts", "Next inspection due in October"]), ("Meeting notes 4 March", ["Decided: ship the smaller version first", "Open: who owns the migration", "Meet again after the holidays"]),
         ("Plant watering", ["Maidenhair: every third day", "Fig: when the top is dry", "Aloe: when the pot feels light"]), ("Spanish phrases", ["¿Dónde está la estación?", "La cuenta, por favor", "Me gustaría reservar una mesa"]), ("Viewing shortlist", ["Second floor or higher", "Near the tram", "[ ] Call the agent about the garden flat"])]
REMS = ["Renew the car insurance", "Email the landlord about the boiler", "Post the signed lease", "Book the train to Porto", "Water the fig", "Send the signed form", "Drop the borrowed drill back", "Ring Aunt Greta", "Order printer ink", "Pay the electricity bill", "Pick up the parcel",
        "Clean the bike chain", "Schedule the eye test", "Back up the laptop", "Buy a birthday card", "File the mileage claim", "Cancel the free trial", "Regrout the shower tray", "Find the spare key", "Update the CV", "Take the bins out", "Buy oat milk", "Oil the gate hinge", "Reconfirm the guesthouse"]
LISTS = [("Odd jobs", "#ff9500"), ("Household", "#34c759"), ("Studio", "#0a7aff"), ("Trip to Porto", "#af52de"), ("Shopping", "#ff2d55"), ("Someday", "#8e8e93"), ("Allotment", "#30b0c7"), ("Twins", "#ffcc00")]
SITES = [("Halden Outfitters", "halden-outfitters.example", "#1f3a5f", "shop"), ("The Marrow Review", "marrowreview.example", "#7a1f2b", "article"), ("Lumen Health", "lumenhealth.example", "#0f766e", "form"), ("Kestrelbank", "kestrelbank.example", "#14532d", "form"),
         ("Fieldnotes Weekly", "fieldnotes.example", "#3b2f7a", "article"), ("Tallow & Twine", "tallowtwine.example", "#92400e", "shop"), ("Northgate Transit", "northgate-transit.example", "#1d4ed8", "results"), ("Quill Search", "quill.example", "#111827", "results")]
HEADLINES = ["The quiet return of the night train", "Why the city is planting ten thousand elms", "A small museum with a very large whale", "What the harbour dredging found", "Inside the last typewriter repair shop", "The long argument about the new bridge"]
PARAS = ["It started, as these things do, with a petition and a folding table outside the station.", "Nobody expected the plan to survive its first winter, and yet the numbers kept rising.", "The council's own report puts the cost at a third of the original estimate.",
         "Critics say the timetable is optimistic. Supporters point to the queue at the ticket office.", "By spring, the first carriages had been repainted in the old colours.", "What happens next depends on a vote that has been postponed twice."]
PRODUCTS = ["Canvas daypack", "Wool overshirt", "Trail bottle 750 ml", "Merino socks, 3 pairs", "Rain shell", "Field notebook", "Enamel mug", "Leather key loop", "Beeswax candle", "Waxed apron", "Brass pen", "Cedar soap"]
PANES = [("Wi-Fi", "wifi", "#0a7aff"), ("Bluetooth", "network", "#0a7aff"), ("Network", "globe", "#0a7aff"), ("Battery", "battery.100percent", "#34c759"), ("General", "gear", "#8e8e93"), ("Accessibility", "person.crop.circle", "#0a7aff"), ("Appearance", "eye", "#1c1c1e"),
         ("Control Centre", "switch.2", "#8e8e93"), ("Desktop & Dock", "dock.rectangle", "#1c1c1e"), ("Displays", "display", "#0a7aff"), ("Notifications", "bell", "#ff3b30"), ("Sound", "speaker.wave.2", "#ff2d55"), ("Focus", "moon", "#5856d6"), ("Screen Time", "clock", "#5856d6"),
         ("Lock Screen", "lock", "#1c1c1e"), ("Privacy & Security", "hand.raised", "#0a7aff"), ("Keyboard", "keyboard", "#8e8e93"), ("Trackpad", "hand.point.up", "#8e8e93"), ("Printers & Scanners", "doc.text", "#8e8e93")]
ROWS = {"Wi-Fi": [("switch", "Wi-Fi"), ("switch", "Ask to join networks"), ("switch", "Ask to join hotspots"), ("button", "Details…"), ("button", "Other…")], "Bluetooth": [("switch", "Bluetooth"), ("info", "Magic Trackpad", "Connected"), ("button", "Connect"), ("button", "Advanced…")],
        "Network": [("info", "Wi-Fi", "Connected"), ("switch", "Firewall"), ("switch", "VPN"), ("popup", "Order of services", ["Automatic", "Wi-Fi first", "Ethernet first"])], "Battery": [("popup", "Low Power Mode", ["Never", "Always", "Only on Battery"]), ("switch", "Optimised Battery Charging"), ("switch", "Show battery percentage"), ("button", "Options…")],
        "General": [("info", "Name", "Studio MacBook"), ("switch", "Automatic updates"), ("popup", "Default web browser", ["Safari", "Firefox", "Arc"]), ("button", "Software Update…"), ("button", "Storage…")], "Accessibility": [("switch", "Reduce motion"), ("switch", "Increase contrast"), ("slider", "Pointer size"), ("check", "Shake mouse pointer to locate")],
        "Appearance": [("popup", "Appearance", ["Light", "Dark", "Auto"]), ("popup", "Sidebar icon size", ["Small", "Medium", "Large"]), ("check", "Allow wallpaper tinting in windows"), ("popup", "Show scroll bars", ["Automatically", "When scrolling", "Always"])],
        "Control Centre": [("popup", "Wi-Fi", ["Show in Menu Bar", "Don't Show in Menu Bar"]), ("popup", "Sound", ["Always Show", "Show When Active", "Don't Show"]), ("switch", "Show battery percentage"), ("stepper", "Recent documents", 10)],
        "Desktop & Dock": [("slider", "Size"), ("switch", "Magnification"), ("popup", "Position on screen", ["Left", "Bottom", "Right"]), ("switch", "Automatically hide and show the Dock"), ("check", "Show suggested and recent apps in Dock"), ("stepper", "Recent applications", 3)],
        "Displays": [("slider", "Brightness", "sun.min", "sun.max"), ("switch", "Automatically adjust brightness"), ("switch", "True Tone"), ("popup", "Refresh rate", ["ProMotion", "60 Hertz", "50 Hertz"]), ("button", "Night Shift…")],
        "Notifications": [("popup", "Show previews", ["Always", "When Unlocked", "Never"]), ("switch", "Allow notifications when the display is sleeping"), ("switch", "Allow notifications when the screen is locked"), ("button", "Options…")],
        "Sound": [("popup", "Alert sound", ["Boop", "Breeze", "Crystal", "Pebble"]), ("slider", "Alert volume", "speaker", "speaker.wave.2"), ("switch", "Play sound on startup"), ("slider", "Output volume", "speaker", "speaker.wave.2"), ("check", "Mute")],
        "Focus": [("switch", "Do Not Disturb"), ("switch", "Share across devices"), ("button", "Add Focus…"), ("popup", "Focus status", ["On", "Off"])], "Screen Time": [("switch", "App & Website Activity"), ("stepper", "Daily limit", 2), ("button", "App Limits…"), ("switch", "Share across devices")],
        "Lock Screen": [("popup", "Start Screen Saver when inactive", ["For 5 minutes", "For 20 minutes", "Never"]), ("popup", "Require password after screen saver begins", ["Immediately", "After 5 minutes"]), ("switch", "Show large clock"), ("check", "Show password hints")],
        "Privacy & Security": [("switch", "Location Services"), ("switch", "Share Mac Analytics"), ("popup", "Allow applications from", ["App Store", "App Store & Known Developers"]), ("button", "Advanced…")],
        "Keyboard": [("slider", "Key repeat rate"), ("slider", "Delay until repeat"), ("switch", "Adjust keyboard brightness in low light"), ("popup", "Press fn key to", ["Change Input Source", "Show Emoji & Symbols", "Do Nothing"]), ("button", "Keyboard Shortcuts…")],
        "Trackpad": [("slider", "Tracking speed"), ("popup", "Click", ["Light", "Medium", "Firm"]), ("switch", "Tap to click"), ("switch", "Natural scrolling"), ("check", "Force Click and haptic feedback")],
        "Printers & Scanners": [("popup", "Default printer", ["Last Printer Used", "Studio LaserJet"]), ("popup", "Default paper size", ["A4", "US Letter"]), ("button", "Add Printer, Scanner or Fax…")]}
CHAT = ["Are we still on for tonight?", "Running ten minutes late, sorry!", "Can you send me the address?", "That sounds perfect.", "I left the keys under the mat.", "Did you see the email from the school?", "Haha, classic.", "Let me check and get back to you.",
        "The train is delayed again.", "Thanks for yesterday, it meant a lot.", "Do we need anything from the shop?", "Call me when you land.", "I'll bring dessert.", "Which entrance?", "See you at seven.", "Booked! Table for four.", "Can we move it to Thursday?", "On my way."]
SONGS = ["Paper Kites at Dusk", "Northbound", "Glass Harbour", "Slow Orbit", "Tin Roof Rain", "Marigold", "Radio Bloom", "Low Tide Radio", "Cinder & Salt", "Telegraph Hill", "Velvet Engine", "Three A.M. Tram", "Kite Season", "Ash and Honey", "Harbour Lamp", "Second Summer",
         "Borrowed Time Machine", "Copper Wire", "Paper Boats", "Scenic Detour", "Night Swim", "Ferris Wheel Heart", "Quiet Carriage", "Winter Oranges"]
ARTISTS = ["The Heron Line", "Saffron Vale", "Mirepoix", "Oda Lindqvist Trio", "Greywater Choir", "Juniper & the Tall Ships", "Calloway Brass", "Neon Thistle", "Pale Atlas", "Hollow Fern"]
ALBUMS = ["Field Season", "Salt Maps", "Afterglow Motel", "Small Weather", "The Orchard Tapes", "Night Ferries", "Common Thread", "Beacon Hillside", "Blue Hour Garden", "Tidewrack"]
PLAYLISTS = ["Morning Commute", "Heads-Down Hours", "Stove & Records", "Running 5K", "Road to the Coast", "Motorway at Midnight", "Supper Club", "Drizzle Days"]
ALERTS = [("Are you sure you want to delete “{x}”?", "This item will be deleted immediately. You can't undo this action.", ["Cancel", "Delete"], "Cancel"), ("Do you want to save the changes made to “{x}”?", "Your changes will be lost if you don't save them.", ["Don't Save", "Cancel", "Save"], "Save"),
          ("“{x}” can't be opened.", "The file may be damaged or in a format this app does not read.", ["OK"], "OK"), ("Replace “{x}”?", "An item with the same name already exists in this location.", ["Keep Both", "Stop", "Replace"], "Replace"),
          ("Allow “{app}” to send notifications?", "Notifications may include alerts, sounds and icon badges.", ["Don't Allow", "Allow"], "Allow"), ("Empty the Bin?", "You can't undo this action.", ["Cancel", "Empty Bin"], "Empty Bin"), ("Sign out of this account?", "Data stored only on this Mac will be removed.", ["Cancel", "Sign Out"], "Cancel")]
DOCK_APPS = [("Safari", "safari"), ("Messages", "messages"), ("Mail", "mail"), ("Maps", None), ("Photos", None), ("FaceTime", None), ("Calendar", "calendar"), ("Contacts", None), ("Reminders", "reminders"), ("Notes", "notes"), ("Freeform", None), ("TV", None), ("Music", "music"),
             ("Podcasts", None), ("News", None), ("App Store", None), ("System Settings", "settings"), ("Preview", None), ("Terminal", None), ("Weather", None), ("Books", None), ("Stocks", None), ("Shortcuts", None), ("Calculator", None), ("Clock", None), ("Home", None)]
EXTRAS = [("battery.100percent", "Battery", "show the battery status"), ("wifi", "Wi-Fi", "show Wi-Fi networks"), ("magnifyingglass", "Spotlight", "search this Mac|open Spotlight"), ("switch.2", "Control Centre", "open Control Centre"), ("speaker.wave.2", "Sound", "change the sound output"),
          ("display", "Screen Mirroring", "mirror or extend the display"), ("moon", "Focus", "turn a Focus on or off"), ("person.crop.circle", "User", "switch user"), ("clock.arrow.circlepath", "Time Machine", "back up now"), ("keyboard", "Input menu", "change the keyboard layout")]
NOTE_FOLDERS = ["Cookbook", "Bindery", "Itineraries", "Journal", "House", "Quick Notes", "Scraps", "Coursework"]
NOTE_TAGS = ["cookbook", "todo", "trip", "scraps", "household", "reading"]
GROUPS = ["Flat 3B", "Running club", "Cousins", "Design team"]
QUERIES = ["night trains europe", "sourdough hydration", "bike lanes map", "tide times"]
ACCOUNTS = ["iCloud", "Bindery", "On My Mac"]
APPS = ["calendar", "finder", "mail", "notes", "reminders", "safari", "settings", "messages", "music"]
SIZES = {"calendar": (1000, 640), "finder": (920, 540), "mail": (1060, 620), "notes": (980, 600), "reminders": (860, 580), "safari": (1080, 660), "settings": (820, 600), "messages": (900, 600), "music": (1040, 640)}


def person(r):
    return f"{r.choice(FIRST)} {r.choice(LAST)}"


def calendar(r, today):
    cals = [{"id": f"c{i}", "name": n, "color": c, "on": r.random() < 0.75} for i, (n, c) in enumerate(r.sample(CALS, r.randint(3, 6)))]
    cals[0]["on"] = True
    events, base = [], today - datetime.timedelta(days=today.weekday() + 7)
    for i, t in enumerate(r.sample(EVENTS, r.randint(14, 26))):
        events.append({"id": f"e{i}", "title": t, "cal": r.choice(cals)["id"], "date": (base + datetime.timedelta(days=r.randrange(28))).isoformat(), "start": r.choice([8, 9, 9.5, 10, 11, 12, 13, 14, 15, 16, 17]), "dur": r.choice([0.5, 1, 1, 1.5, 2])})
    shown = [e for e in events if next(c for c in cals if c["id"] == e["cal"])["on"]]
    return {"today": today.isoformat(), "cals": cals, "other": [{"name": "Birthdays", "color": "#8e8e93", "on": r.random() < 0.6}, {"name": "Holidays", "color": "#a2845e", "on": r.random() < 0.6}, {"name": "Siri Suggestions", "color": "#8e8e93", "on": r.random() < 0.3}],
            "events": events, "ui": {"view": r.choice(["Month", "Month", "Week", "Week", "Day", "Year"]), "anchor": (today + datetime.timedelta(days=r.choice([0, 0, 0, -7, 7, 30, -30]))).isoformat(), "side": r.random() < 0.7,
                                    "pop": r.choice(shown)["id"] if shown and r.random() < 0.18 else None, "alert": None, "q": ""}}


def finder(r, user):
    places = [{"id": "airdrop", "name": "AirDrop", "sym": "network"}, {"id": "recents", "name": "Recents", "sym": "clock"}, {"id": "apps", "name": "Applications", "sym": "plus.app"}, {"id": "desktop", "name": "Desktop", "sym": "display"},
              {"id": "docs", "name": "Documents", "sym": "doc"}, {"id": "down", "name": "Downloads", "sym": "arrow.down.circle"}]
    items, n = [], 0
    for root in ("docs", "down", "desktop"):
        for name in r.sample(FOLDERS, r.randint(2, 5)):
            items.append({"id": f"i{n}", "name": name, "kind": "folder", "parent": root, "date": f"{r.randint(1, 28)} {r.choice(['Jan', 'Feb', 'Mar'])} 2026 at {r.randint(8, 19)}:{r.randrange(60):02d}", "size": "--"}); n += 1
        for name, kind in r.sample(FILES, r.randint(5, 12)):
            items.append({"id": f"i{n}", "name": name + EXT[kind], "kind": kind, "parent": root, "date": f"{r.randint(1, 28)} {r.choice(['Nov', 'Dec', 'Jan', 'Feb'])} {r.choice([2025, 2026])} at {r.randint(8, 19)}:{r.randrange(60):02d}",
                          "size": r.choice(["4 KB", "118 KB", "2.3 MB", "640 KB", "14.8 MB", "87 KB", "1.1 GB"])}); n += 1
    path = r.choice(["docs", "docs", "down", "desktop"])
    here = [i for i in items if i["parent"] == path]
    return {"places": places, "cloud": [{"id": "icloud", "name": "iCloud Drive", "sym": "arrow.up.circle"}, {"id": "shared", "name": "Shared", "sym": "folder.and.person"}], "locs": [{"id": "mac", "name": "Studio MacBook", "sym": "display"}, {"id": "net", "name": "Network", "sym": "globe"}],
            "tags": [{"name": n, "color": c} for n, c in r.sample([("Red", "#ff453a"), ("Orange", "#ff9f0a"), ("Yellow", "#ffd60a"), ("Green", "#32d74b"), ("Blue", "#0a84ff"), ("Purple", "#bf5af2"), ("Grey", "#98989d")], r.randint(3, 6))],
            "items": items, "user": user.split()[0].lower(), "free": r.choice(["212.4 GB", "88.71 GB", "1.02 TB", "36.5 GB"]),
            "ui": {"path": path, "view": r.choice(["icons", "list", "list", "columns", "gallery"]), "sel": r.choice(here)["id"] if r.random() < 0.5 else None, "back": ["docs"] if r.random() < 0.5 else [], "fwd": ["down"] if r.random() < 0.2 else [], "alert": None, "q": ""}}


def mail(r, user):
    boxes = [("inbox", "Inbox", "envelope", 0), ("vips", "VIPs", "star", 0), ("flagged", "Flagged", "flag", 0), ("drafts", "Drafts", "doc", 0), ("sent", "Sent", "paperplane", 0), ("today", "Today", "calendar", 1), ("unread", "Unread", "envelope.open", 1),
             ("junk", "Junk", "arrow.up.bin", 2), ("bin", "Bin", "trash", 2), ("archive", "Archive", "archivebox", 2)]
    msgs = []
    for i, (subj, body) in enumerate(r.sample(SUBJECTS, r.randint(8, 14))):
        who = person(r)
        msgs.append({"id": f"m{i}", "box": "inbox" if i < 9 else r.choice(["archive", "sent", "junk"]), "from": who, "subject": subj, "preview": body, "body": f"Hi {user.split()[0]},\n{body}\nBest,\n{who.split()[0]}",
                     "date": r.choice(["09:41", "08:12", "Yesterday", "Yesterday", "Monday", "Sunday", "12/03/2026", "08/03/2026"]), "unread": r.random() < 0.35, "flag": r.random() < 0.2, "hue": r.randrange(360)})
    inbox = [m for m in msgs if m["box"] == "inbox"]
    return {"boxes": [{"id": a, "name": b, "sym": c, "grp": g, "n": sum(1 for m in msgs if m["box"] == a and m["unread"]) if a == "inbox" else 0} for a, b, c, g in boxes], "account": r.choice(ACCOUNTS), "msgs": msgs, "me": user, "sent": [],
            "ui": {"box": "inbox", "sel": r.choice(inbox)["id"] if r.random() < 0.75 else None, "compose": r.random() < 0.1, "draft": {}, "alert": None, "q": ""}}


def notes(r):
    folders = [{"id": f"f{i}", "name": n} for i, n in enumerate(["Notes"] + r.sample(NOTE_FOLDERS, r.randint(2, 5)))]
    ns = [{"id": f"n{i}", "folder": r.choice(folders[:2])["id"] if i else folders[0]["id"], "title": t, "snippet": b[0].replace("[ ] ", "").replace("[x] ", ""), "body": b, "date": r.choice(["09:12", "Yesterday", "Tuesday", "02/03/2026", "19/02/2026"]),
           "long": f"{r.randint(1, 28)} {r.choice(['February', 'March'])} 2026 at {r.randint(8, 21)}:{r.randrange(60):02d}", "pinned": r.random() < 0.15} for i, (t, b) in enumerate(r.sample(NOTES, r.randint(6, 11)))]
    f = folders[0]["id"]
    return {"folders": folders, "notes": ns, "tags": r.sample(NOTE_TAGS, r.randint(2, 4)),
            "ui": {"folder": f, "sel": next(n["id"] for n in ns if n["folder"] == f), "view": r.choice(["list", "list", "list", "gallery"]), "side": r.random() < 0.8, "alert": None, "q": ""}}


def reminders(r):
    lists = [{"id": f"l{i}", "name": n, "color": c} for i, (n, c) in enumerate(r.sample(LISTS, r.randint(3, 6)))]
    items = [{"id": f"r{i}", "list": r.choice(lists)["id"], "title": t, "done": r.random() < 0.18, "flag": r.random() < 0.2, "due": r.choice([None, None, "Today", "Tomorrow", "Friday", "20 Mar"]), "note": r.choice([None, None, None, "before noon", "ask for a receipt"])}
             for i, t in enumerate(r.sample(REMS, r.randint(10, 18)))]
    smart = [{"id": "today", "name": "Today", "sym": "calendar", "color": "#0a7aff", "fn": "show the reminders due today"}, {"id": "sched", "name": "Scheduled", "sym": "calendar.badge.plus", "color": "#ff3b30", "fn": "show reminders that have a date"},
             {"id": "all", "name": "All", "sym": "tray", "color": "#1c1c1e", "fn": "show every reminder"}, {"id": "flagged", "name": "Flagged", "sym": "flag", "color": "#ff9500", "fn": "show the flagged reminders"}, {"id": "done", "name": "Completed", "sym": "checkmark", "color": "#8e8e93", "fn": "show the completed reminders"}]
    return {"smart": smart, "lists": lists, "items": items, "ui": {"list": r.choice([lists[0]["id"], lists[1]["id"], "today", "all"]), "show": r.random() < 0.3, "alert": None, "q": ""}}


def safari(r):
    pages = {}
    for k, (site, host, color, kind) in enumerate(r.sample(SITES, 5)):
        nav = [{"text": t} for t in r.sample(["Home", "About", "Stories", "Stores", "Help", "Contact", "Pricing", "Journal", "Careers", "Sign In"], 4)]
        p = {"site": site, "host": host, "title": site, "color": color, "kind": kind, "nav": nav, "cta": r.choice(["Subscribe", "Sign In", "Get Started", "Donate", "Bag (2)"]), "cta_def": r.random() < 0.5}
        if kind == "article":
            p.update(section=r.choice(["Cities", "Culture", "Science", "Long read"]), h1=r.choice(HEADLINES), by=f"By {person(r)}  ·  {r.randint(4, 14)} min read", paras=r.sample(PARAS, 4), links=[{"text": h} for h in r.sample(HEADLINES, 3)])
        elif kind == "shop":
            p.update(items=[{"name": n, "price": f"€{r.randint(9, 180)}.00", "hue": r.randrange(360)} for n in r.sample(PRODUCTS, 8)])
        elif kind == "results":
            p.update(query=r.choice(QUERIES), results=[{"text": h, "url": f"{r.choice(SITES)[1]} › {r.choice(['guide', 'news', 'archive'])}", "desc": r.choice(PARAS)} for h in r.sample(HEADLINES, 5)])
        else:
            p.update(h1=r.choice(["Sign in", "Create your account", "Book an appointment"]), fields=r.sample(["Email", "Password", "Full name", "Phone", "Member number", "Postcode"], 3), check=r.choice(["Keep me signed in", "Send me updates by email", "I agree to the terms"]),
                     keep=r.random() < 0.5, submit=r.choice(["Continue", "Sign In", "Create Account"]), alt=r.choice(["Cancel", "Forgot password?", "Use a passkey"]))
        pages[f"p{k}"] = p
    keys = list(pages)
    for p in pages.values():                                    # every link leads somewhere
        for l in p["nav"] + p.get("links", []) + p.get("results", []):
            l["page"] = r.choice(keys)
    tabs = [{"id": f"t{i}", "page": k, "back": [r.choice(keys)] if r.random() < 0.6 else [], "fwd": [r.choice(keys)] if r.random() < 0.2 else []} for i, k in enumerate(r.sample(keys, r.randint(1, 4)))]
    return {"tabs": tabs, "active": r.choice(tabs)["id"], "pages": pages, "home": keys[0], "searchPage": next((k for k in keys if pages[k]["kind"] == "results"), keys[0]), "favs": [{"title": pages[k]["site"], "page": k} for k in keys[:4]],
            "reading": r.sample(HEADLINES, 2), "showFavs": r.random() < 0.6, "form": {}, "submitted": None, "ui": {"side": r.random() < 0.2, "addr": None, "alert": None}}


def settings(r, user):
    panes = [{"id": n, "name": n, "sym": s, "color": c, "blurb": f"Options for {n.lower()} on this Mac.", "gap": i in (3, 7, 10, 14, 16)} for i, (n, s, c) in enumerate(PANES)]
    rows = {}
    for n, spec in ROWS.items():
        out = []
        for j, row in enumerate(spec):
            t, label = row[0], row[1]
            d = {"t": t, "k": f"{n}/{j}", "label": label}
            if t in ("switch", "check"):
                d["v"] = r.random() < 0.5
            elif t == "popup":
                d["opts"], d["v"] = row[2], r.choice(row[2])
            elif t == "stepper":
                d["v"] = row[2] + r.randint(0, 4)
            elif t == "slider":
                d["v"] = round(r.uniform(0.1, 0.9), 2)
                if len(row) > 2:
                    d["lo"], d["hi"] = row[2], row[3]
            elif t == "button":
                d["v"] = label
                d["label"] = ""
            else:
                d["v"] = row[2]
            out.append(d)
        cut = r.randint(2, max(2, len(out) - 1))
        rows[n] = [{"title": None, "rows": out[:cut]}, {"title": r.choice([None, "Advanced", "Options"]), "rows": out[cut:]}] if out[cut:] else [{"title": None, "rows": out}]
    return {"panes": panes, "rows": rows, "user": user, "hue": r.randrange(360), "ui": {"pane": r.choice(list(ROWS)), "alert": None, "q": ""}}


def messages(r):
    chats = []
    for i in range(r.randint(5, 9)):
        chats.append({"id": f"h{i}", "name": person(r) if r.random() < 0.8 else r.choice(GROUPS), "time": r.choice(["09:41", "08:02", "Yesterday", "Yesterday", "Sunday", "Friday"]), "unread": r.random() < 0.25, "hue": r.randrange(360),
                      "msgs": [{"me": r.random() < 0.45, "text": t} for t in r.sample(CHAT, r.randint(3, 8))]})
    return {"chats": chats, "ui": {"chat": r.choice(chats)["id"], "draft": "", "alert": None, "q": ""}}


def music(r):
    songs = [{"id": f"s{i}", "title": t, "artist": r.choice(ARTISTS), "album": r.choice(ALBUMS), "time": f"{r.randint(2, 5)}:{r.randrange(60):02d}", "love": r.random() < 0.2, "hue": r.randrange(360)} for i, t in enumerate(r.sample(SONGS, r.randint(12, 20)))]
    pls = [{"id": f"y{i}", "name": n, "songs": [s["id"] for s in r.sample(songs, r.randint(4, 9))]} for i, n in enumerate(r.sample(PLAYLISTS, r.randint(3, 6)))]
    return {"songs": songs, "albums": [{"title": a, "artist": r.choice(ARTISTS), "hue": r.randrange(360)} for a in r.sample(ALBUMS, r.randint(6, 10))], "playlists": pls,
            "player": {"cur": r.choice(songs)["id"], "playing": r.random() < 0.5, "shuffle": r.random() < 0.3, "repeat": r.random() < 0.3, "vol": round(r.uniform(0.2, 0.9), 2), "pos": round(r.random(), 2)},
            "ui": {"view": r.choice(["songs", "songs", "albums", "home", pls[0]["id"]]), "sel": r.choice(songs)["id"] if r.random() < 0.4 else None, "alert": None, "q": ""}}


def build(seed, split="train"):
    r = random.Random(f"macsim/{split}/{seed}")
    look = "dev" if split == "dev" else "train"                      # dev draws accents, wallpapers and window arrangements that train and steps never use
    W, H, mb = r.choice(SCREENS)
    user, today = person(r), datetime.date(2026, 1, 5) + datetime.timedelta(days=r.randrange(360))
    make = {"calendar": lambda: calendar(r, today), "finder": lambda: finder(r, user), "mail": lambda: mail(r, user), "notes": lambda: notes(r), "reminders": lambda: reminders(r), "safari": lambda: safari(r),
            "settings": lambda: settings(r, user), "messages": lambda: messages(r), "music": lambda: music(r)}
    apps = r.sample(APPS, r.choice([1, 2, 2, 3, 3]))
    if r.random() < 0.35 and "calendar" not in apps:                 # Calendar is the app that started this folder: keep it frequent
        apps[0] = "calendar"
    dock_apps = [d for d in DOCK_APPS if d[1] in apps] + r.sample([d for d in DOCK_APPS if d[1] not in apps], r.randint(6, 12))
    dock_apps.sort(key=lambda d: DOCK_APPS.index(d))
    dock = [{"name": "Finder", "app": "finder", "icon": "Finder.png", "cls": "", "running": True}] + [{"name": n, "app": a, "icon": n.replace(" ", "_") + ".png", "running": a in apps or r.random() < 0.15} for n, a in dock_apps] + ["|", {"name": "Bin", "app": None, "icon": "Bin.png", "cls": "bin"}]
    extras = [e for e in EXTRAS if e[1] in ("Battery", "Wi-Fi", "Spotlight", "Control Centre") or r.random() < 0.3]
    r.shuffle(extras)
    state = {"seed": seed, "split": split, "screen": [W, H], "mb": mb, "dark": r.random() < 0.4, "accent": r.choice(ACCENTS[look]), "wallpaper": r.choice(WALLS[look]),
             "status": {"clock": f"{today.strftime('%a')} {today.day} {today.strftime('%b')}  {r.randint(7, 22)}:{r.randrange(60):02d}"},
             "extras": [{"sym": s, "name": n, "fn": f, "spot": n == "Spotlight", "text": "87%" if n == "Battery" and r.random() < 0.4 else ""} for s, n, f in extras],
             "dock": dock, "windows": [], "apps": {a: make[a]() for a in apps}, "events": [],
             "spot_items": [{"name": n, "kind": "Application", "app": a, "icon": n.replace(" ", "_") + ".png"} for n, a in DOCK_APPS] + [{"name": n + EXT[k], "kind": "Document", "sym": "doc.text"} for n, k in r.sample(FILES, 10)] + [{"name": f, "kind": "Folder", "sym": "folder"} for f in r.sample(FOLDERS, 5)],
             "spot": {"open": False, "query": ""}}
    n = len(apps)                                                     # windows: sized for the screen, overlapping, the last one in front
    slots = r.sample([(0, 0), (1, 1), (1, 0), (0, 1)], 3)             # train and steps: towards different corners, so each window shows a good part
    for k, a in enumerate(apps):
        w, h = SIZES[a]
        fit = min(1.0, (W - 40) / w, (H - mb - 110) / h)
        scale = fit * (r.uniform(0.82, 1.0) * (1.0, 0.92, 0.84)[n - 1] if look == "train" else r.uniform(0.72, 0.92))
        w, h = round(w * scale), round(h * scale)
        if look == "dev":                                             # dev: a cascade from the top left that train never uses
            x, y = 12 + k * round((W - w - 24) / max(1, n - 1)) if n > 1 else r.randint(8, max(8, W - w - 8)), mb + 10 + k * 26
        elif n == 1:
            x, y = r.randint(8, max(8, W - w - 8)), r.randint(mb + 6, max(mb + 6, H - 96 - h))
        else:
            fx, fy = [min(1.0, max(0.0, v + r.uniform(-0.18, 0.18))) for v in slots[k]]
            x, y = round(8 + fx * max(0, W - w - 16)), round(mb + 6 + fy * max(0, H - 102 - h - mb))
        state["windows"].append({"app": a, "x": x, "y": y, "w": w, "h": h})
    post, front, roll = [], apps[-1], r.random()
    if roll < 0.16:                                                   # an alert sheet in the front window
        t, text, buttons, d = r.choice(ALERTS)
        x = r.choice(FILES)[0] if "{x}" in t else ""
        state["apps"][front]["ui"]["alert"] = {"title": t.format(x=x, app=front.title()), "text": text, "buttons": buttons, "def": d, "wide": r.random() < 0.4, "icon": {"finder": None, "settings": "System_Settings.png"}.get(front, front.title() + ".png")}
    elif roll < 0.32:                                                 # a pull-down menu from the menu bar
        post.append(("menu", r.randint(-1, 4)))
    elif roll < 0.40 and front in ("finder", "mail"):
        post.append(("context", front))
    elif roll < 0.50 and front == "settings":                        # a pop-up button's menu
        post.append(("popup", front))
    elif roll < 0.47:
        state["spot"] = {"open": True, "query": r.choice(["cal", "no", "mus", "set", "inv", "pho", "rem", "ma", "sa", "te"]), "focus": True}
    return state, post
