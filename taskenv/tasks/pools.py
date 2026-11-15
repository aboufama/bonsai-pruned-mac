"""Word pools for seeded start states. Written for this test set; not shared with any generator
used for training.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
"""
FIRST = ["Dana", "Marcus", "Priya", "Tobias", "Elena", "Kwame", "Ingrid", "Rafael", "Mei", "Callum", "Nadia", "Stefan",
         "Aiko", "Bruno", "Halima", "Jonas", "Leila", "Oskar", "Renata", "Samir", "Thea", "Viktor", "Wanjiru", "Yusuf",
         "Bianca", "Cormac", "Daria", "Emeka", "Freya", "Gideon", "Hana", "Ivo"]
LAST = ["Whitfield", "Okafor", "Raman", "Lindqvist", "Marchetti", "Boateng", "Sorensen", "Quintero", "Tanaka", "Ferris",
        "Haddad", "Kowalczyk", "Brandt", "Castellano", "Nwosu", "Albrecht", "Petrov", "Duarte", "Ishikawa", "Mbeki",
        "Hollis", "Varga", "Achterberg", "Salazar", "Thornbury", "Eklund", "Rosales", "Underhill", "Zielinski", "Okonkwo"]
COMPANIES = ["Northwind Supply", "Harbor Dental", "Juniper Labs", "Kestrel Air", "Lumen Bank", "Fennel & Rye", "Tidewater Press",
             "Quarry Fitness", "Orchard Health", "Bluebird Energy", "Copperline Rail", "Meridian Lets", "Saffron Kitchen"]
DOMAINS = ["fastmail.example", "northwind.example", "juniperlabs.example", "postbox.example", "hey-mail.example", "tidewater.example"]

MAIL_TOPICS = [
    ("Q3 budget review", "Could you look over the attached numbers before Thursday? The travel line looks high to me and I would like a second pair of eyes before it goes to finance."),
    ("Lunch on Friday?", "A few of us are going to the noodle place near the station at half past twelve. Let me know if you want me to hold a seat."),
    ("Invoice 4471 overdue", "Our records show that invoice 4471 is still open. Could you confirm when payment will be made, or let me know if there is a problem with it?"),
    ("Your flight itinerary", "Your booking is confirmed. Departure is at 07:35 from terminal 2. Online check-in opens 24 hours before the flight."),
    ("Notes from the kickoff", "Thanks for joining this morning. I wrote up the decisions and the three open questions; they are in the shared folder under Kickoff."),
    ("Apartment viewing Saturday", "The landlord can show the flat at eleven on Saturday. The address is 14 Alder Row, second floor. Bring a photo ID."),
    ("Password reset requested", "We received a request to reset the password of your account. If this was not you, no action is needed."),
    ("Design feedback, round two", "The new header works much better. Two small things: the search field is hard to find and the footer links are too pale."),
    ("Reminder: dentist on the 19th", "This is a reminder of your appointment on the 19th at 3:40 PM. Please arrive ten minutes early."),
    ("Team offsite dates", "We are choosing between the first and the second week of March. Please fill in the poll by Wednesday."),
    ("Re: conference talk proposal", "The committee liked the outline. They ask for a shorter abstract, 150 words at most, by the end of the month."),
    ("Your order has shipped", "Good news: your order is on its way and should arrive within three working days. You can follow it with the tracking link."),
    ("Car service quote", "The full service comes to 240 including the brake fluid change. We have a slot on Tuesday morning if that suits."),
    ("Book club pick for December", "We settled on the short story collection. First meeting is on the 8th at Renata's place."),
    ("Contract draft v3", "I have accepted most of your changes. Clause 7 still needs a decision on the notice period: 30 or 60 days."),
    ("Photos from the hike", "I put the best forty in an album. The one of the ridge at sunrise came out really well."),
    ("Standup moved to 10:15", "Starting Monday the daily standup moves to quarter past ten so the Lisbon team can join."),
    ("Expense report rejected", "The report was sent back because two receipts are missing. Please attach them and submit again."),
    ("Welcome to the newsletter", "Thanks for signing up. You will hear from us once a month with new recipes and nothing else."),
    ("Parent evening next week", "The parent evening is on Wednesday from six to eight. You can book a ten minute slot with each teacher online."),
    ("Quick question about the API", "Does the export endpoint return times in UTC or in the account's time zone? The docs say both in different places."),
    ("Gym membership renewal", "Your membership renews on the first of next month. Reply to this email if you want to change your plan."),
    ("Birthday dinner for Oskar", "It is a surprise, so please do not mention it. Saturday, seven o'clock, the Georgian place on Mill Lane."),
    ("Updated floor plan", "The architect moved the kitchen door as we asked. The new plan is attached; the measurements are on page two."),
    ("Feedback on your application", "Thank you for your patience. We would like to invite you to a second conversation next week."),
    ("Library books due", "Two of the items you borrowed are due back in three days. You can renew them online once."),
]

FILE_NAMES = {
    "pdf": ["lease-agreement", "boarding-pass", "tax-return-2025", "user-manual", "invoice-4471", "conference-programme", "bank-statement-oct",
            "warranty-card", "research-summary", "seating-plan", "insurance-policy", "floor-plan", "recipe-booklet", "train-tickets"],
    "doc": ["cover-letter", "meeting-notes", "project-brief", "speech-draft", "packing-list", "reference-letter", "weekly-report",
            "chapter-one", "interview-questions", "house-rules", "press-release"],
    "sheet": ["budget-2026", "expenses-q3", "guest-list", "inventory", "training-log", "grades", "price-comparison", "mileage", "time-sheet"],
    "image": ["harbour-sunset", "passport-photo", "team-offsite", "kitchen-before", "logo-draft", "whiteboard", "garden-plan", "screenshot-login",
              "ridge-at-sunrise", "receipt-scan", "poster-final"],
    "audio": ["voice-memo-12", "interview-raw", "podcast-intro", "piano-take-3", "lecture-week-4"],
    "zip": ["site-backup", "fonts", "holiday-photos", "source-code", "old-projects"],
    "slides": ["quarterly-review", "pitch-deck", "onboarding", "thesis-defence", "product-roadmap"],
}
EXT = {"pdf": "pdf", "doc": "docx", "sheet": "xlsx", "image": "jpg", "audio": "m4a", "zip": "zip", "slides": "key"}
KIND_LABEL = {"pdf": "PDF document", "doc": "Word document", "sheet": "Spreadsheet", "image": "JPEG image", "audio": "Audio",
              "zip": "ZIP archive", "slides": "Presentation", "folder": "Folder"}
FOLDER_NAMES = ["Projects", "Archive", "Receipts", "Travel", "Taxes", "Work", "School", "Scans", "Recipes", "Invoices", "Photos to sort",
                "Client files", "Manuals", "Personal", "Drafts", "Shared", "Templates", "Old laptop"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def person(rng):
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def people(rng, n):
    """n people with distinct first and last names (so that either identifies them)."""
    firsts, lasts = rng.sample(FIRST, n), rng.sample(LAST, n)
    return [f"{f} {l}" for f, l in zip(firsts, lasts)]


def email_of(name, rng):
    f, l = name.lower().split(" ", 1)
    return rng.choice([f"{f}.{l}", f"{f}", f"{f[0]}{l}", f"{f}{l[0]}"]).replace(" ", "") + "@" + rng.choice(DOMAINS)
