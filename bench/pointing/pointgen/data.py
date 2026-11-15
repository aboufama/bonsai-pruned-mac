"""Seeded fake content. Lists are dealt out to splits by position (see splits.pool), so a
person, file stem, project or channel name that can be a target in one split never appears as
a target in another. Free text that is never a target (message bodies, code, logs) is shared."""
from .splits import pool

FIRST = """Maya Daniel Priya Tomás Aiko Jonas Fatima Lucas Ingrid Mateo Chloe Arjun Sofia Henrik Naomi Elias
Camille Oskar Leila Victor Hana Felix Amara Julian Noor Rafael Elena Kofi Signe Marco Yuki Anton Zara Pavel
Isla Dmitri Carmen Nikolai Thandi Emil Rosa Ibrahim Greta Samir Lena Hugo Meera Caleb Freya Andre Bianca Omar
Tessa Kenji Paula Stefan Nadia Owen Mira Lars Dalia Simon Vera Tariq Alma Bruno Ines Callum Jia Mikael Rhea
Dario Esme Farid Lotte Gideon Suki Ronan Petra Waleed Anouk Idris Maren Cyrus Linnea Joaquin Odette""".split()

LAST = """Okafor Lindqvist Ramirez Tanaka Novak Haddad Fischer Moreau Castillo Bergstrom Iyer Petrov Nakamura
Sandoval Keller Abubakar Rossi Johansson Delgado Whitfield Kowalski Mbeki Laurent Yilmaz Hartmann Suzuki Vargas
Eriksen Chaudhry Bianchi Thorne Papadakis Mendoza Vogel Achterberg Osei Lemaire Dvorak Ishikawa Calloway
Strand Farouk Marchetti Sorensen Banerjee Quintero Halvorsen Adeyemi Renard Kaplan Ueda Montoya Brandt Sato
Zielinski Amani Fontaine Ostrowski Reyes Lindgren Demir Aldana Winther Morales Engel Hoshino Barros Stavros
Nilsen Khoury Pellegrini Voss Ortega Madsen Tiwari Beaumont Kimura Salazar Ekström Rahimi Conti Holm""".split()

COMPANIES = """Northwind Labs|Halcyon Freight|Brightline Studio|Kestrel Analytics|Juniper & Pine|Meridian Health
Atlas Robotics|Cobalt Systems|Fernway Travel|Lumen Foods|Quarry Capital|Saffron Media|Tidewater Energy
Verdant Supply|Ironbark Software|Paloma Design|Redwood Legal|Skylark Aviation|Orchard Retail|Pinnacle Logistics
Bluebird Education|Granite Works|Harbor Insurance|Opaline Cosmetics|Riverbend Realty|Summit Outdoor
Thistle & Co|Umbra Security|Wavecrest Marine|Zephyr Motors|Cinder Coffee|Driftwood Hotels|Ember Games
Foxglove Pharma|Glacier Data|Hawthorne Press|Indigo Telecom|Larkspur Films|Maplewood Bank|Nimbus Cloud""".replace("\n", "|").split("|")

PROJECTS = """Apollo|Borealis|Catalyst|Dovetail|Evergreen|Firefly|Gemini|Horizon|Icarus|Jetstream|Keystone|Lighthouse
Monarch|Nebula|Odyssey|Pathfinder|Quicksilver|Rosetta|Sandbox|Trailhead|Uplink|Vanguard|Wildfire|Xenon|Yardstick
Zenith|Aurora|Beacon|Cascade|Daybreak|Element|Foundry|Gravity|Harvest|Ignite|Juno|Kite|Lattice|Momentum|Nova
Onyx|Prism|Quartz|Relay|Signal|Tempo|Unity|Vertex|Willow|Yonder""".replace("\n", "|").split("|")

CHANNELS = """general|random|design|engineering|marketing|support|announcements|product|sales|ops|frontend|backend
mobile|data|qa|releases|incidents|standup|onboarding|hiring|finance|legal|research|growth|infra|security|docs
feedback|launch|partners|billing|analytics|brand|events|facilities|it-help|leadership|social|watercooler|wins
customers|roadmap|bugs|deploys|oncall|content|community|payments|platform|localization""".replace("\n", "|").split("|")

# file stems by kind; extensions are shared
STEMS = {
    "doc": """Meeting notes|Project brief|Quarterly report|Onboarding guide|Release plan|Style guide|Travel policy
Vendor contract|Board memo|Press release|User research|Launch checklist|Risk register|Design review|Offer letter
Team charter|Retrospective|Budget narrative|Roadmap draft|Security policy|Interview notes|Case study
Product spec|Support playbook|Hiring plan|Annual summary|Workshop agenda|Change log|Pricing proposal
Partner agreement|Incident report|Training manual|Survey results|Brand story|Field notes|Grant application
Status update|Customer letter|Scope of work|Handover notes""",
    "sheet": """Budget 2026|Sales pipeline|Inventory count|Expense claims|Headcount plan|Revenue forecast|Payroll summary
Campaign results|Price list|Timesheet March|Order history|Supplier scores|Churn analysis|Cost breakdown
Shipping rates|Lead tracker|Asset register|Test results|Survey data|Commission table|Cash flow|Margin model
Tax worksheet|Capacity plan|Usage metrics|Invoice log|Stock levels|Bonus pool|Travel costs|Renewals tracker""",
    "image": """hero-banner|team-photo|logo-dark|product-shot|office-map|icon-set|screenshot-login|cover-art
wireframe-home|mood-board|booth-layout|headshot-ceo|pattern-tile|launch-poster|map-overlay|chart-export
avatar-default|storefront|packaging-front|texture-paper|sketch-v2|billboard-mock|badge-gold|sunset-pier
floor-plan|label-draft|mascot-wave|banner-sale|diagram-flow|thumbnail-01""",
    "code": """main|utils|config|server|router|models|schema|auth|client|index|helpers|worker|parser|cache|logger
session|middleware|pipeline|scheduler|storage|validators|handlers|constants|migrate|settings|tokens|events
queue|metrics|renderer|adapter|registry|bootstrap|commands|fixtures|payments|search|uploads|webhooks|theme""",
    "media": """interview-take3|b-roll-harbor|intro-sting|voiceover-final|drone-coast|podcast-ep12|jingle-short
timelapse-city|keynote-rec|ambient-rain|product-demo|crowd-wide|outro-music|testimonial-anna|street-walk
title-card|drum-loop|sunrise-ridge|screen-capture|foley-steps|closing-shot|bass-stem|wedding-toast
factory-tour|logo-reveal|narration-b|cafe-ambience|unboxing-clip|skyline-pan|whoosh-fx""",
    "folder": """Documents|Downloads|Pictures|Projects|Archive|Invoices|Contracts|Templates|Shared with me|Screenshots
Music|Videos|Desktop|Backups|Clients|Marketing|Receipts|Presentations|Research|Personal|Drafts|Design assets
Recordings|Source|Exports|Reports|Legal|Taxes|Travel|Fonts|Scans|Reference|Meeting recordings|Old versions
Brand kit|Finance|HR|Photos 2025|Renders|Datasets|Notebooks|Books|Manuals|Wallpapers|Inbox scans""",
}
STEMS = {k: v.replace("\n", "|").split("|") for k, v in STEMS.items()}
EXT = {
    "doc": ["docx", "pdf", "txt", "md", "pages", "rtf"], "sheet": ["xlsx", "csv", "numbers", "ods"],
    "image": ["png", "jpg", "svg", "psd", "webp", "tiff"], "code": ["py", "ts", "js", "go", "rs", "json", "yaml", "css", "tsx", "rb"],
    "media": ["mp4", "mov", "wav", "mp3", "mkv", "aiff"],
}

TASKS_VERB = "Fix|Update|Review|Draft|Refactor|Design|Test|Migrate|Document|Investigate|Prepare|Ship|Audit|Polish|Remove|Plan".split("|")
TASKS_OBJ = """login redirect|onboarding email|pricing page|search index|export to CSV|dark mode colors|invoice template
password reset flow|API rate limits|mobile nav menu|checkout errors|release notes|billing webhooks|user roles
landing page copy|database backups|image uploads|notification settings|signup funnel|error tracking|audit log
cookie banner|team invites|data retention policy|keyboard shortcuts|loading states|support macros|SSO setup
push notifications|empty states|report scheduler|two-factor prompts|map clustering|font loading|referral codes
cache headers|profile editor|trial expiry emails|chart tooltips|file previews|usage dashboard|tax settings
webhook retries|address autocomplete|calendar sync|tag filters|import wizard|session timeouts|PDF receipts
legacy endpoints|feature flags""".replace("\n", "|").split("|")

SUBJECTS = """Q3 planning kickoff|Invoice overdue reminder|Your flight itinerary|Welcome to the team|Contract for review
Weekly metrics digest|Lunch on Thursday?|Security alert: new sign-in|Feedback on the proposal|Offsite agenda
Renewal quote attached|Design handoff notes|Password expires soon|Candidate debrief|Updated floor plan
Server maintenance window|Expense report approved|Customer escalation|Podcast recording slot|Your order has shipped
Minutes from Monday|Budget sign-off needed|New comment on your doc|Trip reimbursement|Photos from the launch
Reminder: benefits enrollment|Draft press release|Parking permit renewal|Bug bash results|Interview schedule
Vendor onboarding forms|Team dinner RSVP|Quarterly tax filing|Shipping delay notice|Workshop materials
Beta invite inside|Lease agreement copy|Conference tickets|Survey closes Friday|Payroll correction
Kickoff recording|Reference check|Roadmap questions|Holiday schedule|Printer is back online|Thank you note
Timesheet missing|Venue options|Contract countersigned|Storage almost full""".replace("\n", "|").split("|")

SONG_A = "Midnight|Paper|Electric|Golden|Quiet|Neon|Velvet|Hollow|Summer|Crystal|Broken|Silver|Distant|Wild|Slow|Burning|Northern|Lonely|Faded|Bright".split("|")
SONG_B = """Harbor|Satellites|Avenue|Gardens|Thunder|Mirrors|Tides|Lanterns|Arcade|Horizon|Static|Orchard|Carousel
Embers|Rooftops|Signals|Meadow|Engines|Postcards|Fireflies|Canyons|Machines|Lullaby|Daydream|Boulevard|Monsoon
Skyline|Compass|Lighthouse|Parade|Cathedral|Wildflowers|Telegraph|Undertow|Snowfall|Voltage|Marigold|Railways
Honeycomb|Afterglow""".replace("\n", "|").split("|")
ARTISTS = """The Paper Kites Club|Luna Vale|Cedar & Smoke|Atlas Drive|Mono Coast|Velvet Harbor|Juno Park|Static Bloom
Night Ferry|Rosa Lund|Glass Animals Trio|Hollow Pines|Echo Lake|Kid Cascade|Marble Arch|Soft Machine Shop
Tallis Grey|Orange Grove|Blue Motel|Neon Fields|Winter Camp|Polar Youth|Saint Navy|The Lowlands|Copper Sun
Violet Hours|Minor Fall|Great Divide|Low Tide Radio|Honey Dusk|Sister Signal|Arcadia Row|Field Notes
Dawn Chorus|Pale Kings|Silver Arrows|Ocean Parkway|Desert Hearts|Red Ivy|City Lakes""".replace("\n", "|").split("|")
PLAYLISTS = """Morning Focus|Road Trip|Deep Work|Dinner Jazz|Workout Mix|Rainy Day|Throwbacks|Chill Evening|New Finds
Party Starters|Acoustic Covers|Late Night Drive|Study Beats|Sunday Brunch|Running 5K|Indie Mix|Sleep Sounds
Coding Flow|Summer Hits|Coffeehouse|Feel Good|Classical Essentials|Lo-fi Loop|Liked Songs|Discover Weekly
Top of 2025|Yoga Flow|Family Road Mix|Piano Calm|90s Rewind|Soul Kitchen|Desert Sunset|Bass Therapy
Wedding Dance|Nordic Folk|Film Scores|Garage Days|Latin Heat|Quiet Storm|Synth Odyssey""".replace("\n", "|").split("|")

PRODUCT_A = "Classic|Trail|Urban|Alpine|Coastal|Vintage|Compact|Premium|Everyday|Studio|Travel|Heritage|Summit|Harbor|Nomad|Metro|Field|Aero|Terra|Loft".split("|")
PRODUCT_B = """Backpack|Water Bottle|Desk Lamp|Running Shoes|Wool Sweater|Coffee Grinder|Notebook Set|Rain Jacket
Bluetooth Speaker|Yoga Mat|Ceramic Mug|Leather Wallet|Sunglasses|Tote Bag|Wireless Charger|Throw Blanket
Standing Desk|Chef Knife|Hiking Boots|Scented Candle|Phone Case|Keyboard|Duffel Bag|Beanie|Travel Pillow
Cutting Board|Monitor Arm|Thermos|Sneakers|Linen Shirt|Camp Stove|Bike Helmet|Tea Kettle|Wall Clock
Planter Pot|Weekender|Card Holder|Desk Mat|Earbuds|Umbrella""".replace("\n", "|").split("|")

EVENTS = """Team standup|Design review|1:1 with manager|Sprint planning|Dentist appointment|Lunch with client|Budget review
Product demo|Yoga class|Board meeting|Interview panel|Flight to Denver|Quarterly all-hands|Code review session
School pickup|Marketing sync|Vendor call|Coffee chat|Release retro|Gym session|Customer onboarding|Roadmap workshop
Book club|Legal check-in|Performance review|Site visit|Podcast recording|Car service|Team offsite|Investor update
Parent-teacher meeting|UX research session|Payroll cutoff|Security training|Birthday dinner|Hackathon kickoff
Contract signing|Press briefing|Town hall|Volunteer shift|Piano lesson|Architecture forum|Sales pipeline review
Inventory audit|Webinar rehearsal|Doctor checkup|Mentoring hour|Photo shoot|Tax appointment|Farewell lunch""".replace("\n", "|").split("|")

HOSTS = """web-prod-01|db-primary|staging-api|build-runner-3|cache-eu-west|bastion|worker-queue-2|analytics-etl|mail-relay
lb-frontend|k8s-node-07|backup-vault|dev-sandbox|search-indexer|metrics-store|vpn-gateway|ci-agent-5|log-shipper
edge-proxy-ams|auth-service|media-encoder|gpu-train-1|replica-us-east|payments-core|feature-flags|geo-lookup
cron-box|artifact-store|docs-site|qa-grid-4|redis-sessions|kafka-broker-2|nat-gateway|image-resizer|ml-inference
storage-cold|report-builder|sms-gateway|test-runner-9|billing-db""".replace("\n", "|").split("|")

BRANCHES = """main|develop|release/2.4|feature/login-v2|fix/cache-headers|chore/deps|feature/dark-mode|hotfix/payment
feature/search|refactor/router|release/3.0|fix/upload-size|feature/export|staging|experiment/rag|docs/readme
fix/timezones|feature/sso|perf/queries|feature/onboarding""".replace("\n", "|").split("|")

LOREM = """Thanks for the quick turnaround on this. I had a look at the latest draft and left a few comments inline.
Can we move the review to Thursday afternoon? The numbers for the second quarter are still coming in.
I spoke with the vendor this morning and they confirmed the delivery window for next week.
Attaching the revised version with the changes we discussed. Let me know if anything looks off.
Just a reminder that the deadline is end of day Friday. Please flag any blockers before then.
The client asked whether we can include the extended warranty in the same quote.
Here is the summary from yesterday's call, along with the action items for each team.
We are seeing a small regression in the staging build. I will dig into the logs after lunch.
Great work on the demo today. The feedback from the leadership team was very positive.
Could you double-check the totals on page three? I think the tax line is missing.
I'll be out of office on Monday but reachable by phone for anything urgent.
The new onboarding flow is ready for testing. Credentials are in the shared vault.""".split("\n")

CHAT = """sounds good, pushing the fix now|did anyone look at the flaky test?|lgtm, merging after CI passes
can we sync at 3?|the staging deploy is done|who owns the billing dashboard?|nice, that worked on my machine too
I'll take the first pass at the doc|customer says it's still happening on Safari|coffee run, anyone want anything?
reverted for now, will investigate tomorrow|updated the ticket with repro steps|thanks for covering yesterday
the designs are in the shared folder|running about five minutes late|can you resend the invite?
done, let me know if the numbers look right|we should probably add a test for that|good catch
shipping this behind a flag first|is the meeting room booked?|I have a draft ready for review
ok, restarting the worker|looks like a cache issue|let's revisit after the release""".replace("\n", "|").split("|")

SHELL = """$ git status|On branch main|Your branch is up to date with 'origin/main'.||nothing to commit, working tree clean
$ make test|pytest -q tests/|........................................................ [ 62%]|.................................. [100%]
90 passed in 4.21s|$ docker ps --format '{{.Names}}\\t{{.Status}}'|api        Up 3 hours|worker     Up 3 hours
postgres   Up 2 days|redis      Up 2 days|$ kubectl get pods -n prod|NAME                      READY   STATUS    RESTARTS   AGE
api-7d9f8b6c4-2xkqp       1/1     Running   0          3h12m|api-7d9f8b6c4-9m4tz       1/1     Running   0          3h12m
worker-5c6b7d8f9-hj2lw    1/1     Running   2          26h|$ tail -n 5 /var/log/app/server.log
[INFO] request id=8f21 path=/api/orders status=200 12ms|[INFO] request id=8f22 path=/api/users/42 status=200 8ms
[WARN] slow query 412ms: SELECT * FROM invoices WHERE status = 'open'|[INFO] cache hit ratio 0.93
[INFO] request id=8f23 path=/healthz status=200 1ms|$ df -h /data|Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme1n1    916G  512G  358G  59% /data|$ ssh deploy@staging 'systemctl status api'|● api.service - API server
   Active: active (running) since Tue 09:14:02 UTC; 3h ago|$ npm run build|> build|> vite build
vite v6.2.0 building for production...|✓ 412 modules transformed.|dist/assets/index-4f2a.js   182.44 kB │ gzip: 58.10 kB
✓ built in 3.82s|$ """.split("|")
SHELL = [x for line in SHELL for x in line.split("\n")]

MONTHS = "January February March April May June July August September October November December".split()
DAYS = "Mon Tue Wed Thu Fri Sat Sun".split()
COLORS = ["#e5484d", "#f76b15", "#ffb224", "#46a758", "#12a594", "#0091ff", "#3e63dd", "#6e56cf", "#8e4ec6", "#d6409f", "#e93d82", "#978365"]


class Data:
    """Content source bound to one screen's random stream and split."""

    def __init__(self, rng, split):
        self.rng, self.split = rng, split

    def take(self, name, items, k=None):
        """k distinct items (or all, shuffled) from the split's share of a list."""
        mine = list(pool(name, items, self.split))
        self.rng.shuffle(mine)
        return mine if k is None else mine[:k]

    def one(self, name, items):
        return self.rng.choice(pool(name, items, self.split))

    def people(self, k):
        firsts = self.take("first", FIRST)
        lasts = self.take("last", LAST)
        out = []
        for i in range(k):
            out.append(f"{firsts[i % len(firsts)]} {lasts[(i * 7 + i // len(lasts)) % len(lasts)]}")
        return out

    def person(self):
        return self.people(1)[0]

    def files(self, kind, k, ext=True):
        stems = self.take("stem." + kind, STEMS[kind], k)
        if kind == "folder" or not ext:
            return stems
        return [f"{s}.{self.rng.choice(EXT[kind])}" for s in stems]

    def mixed_files(self, k):
        kinds = ["doc", "sheet", "image", "code", "media"]
        out = []
        per = {kind: self.files(kind, k) for kind in kinds}
        for i in range(k):
            kind = self.rng.choice(kinds)
            if per[kind]:
                out.append((per[kind].pop(), kind))
        return out

    def tasks(self, k):
        objs = self.take("task.obj", TASKS_OBJ, k)
        return [f"{self.rng.choice(TASKS_VERB)} {o}" for o in objs]

    def songs(self, k):
        bs = self.take("song.b", SONG_B, k)
        return [f"{self.rng.choice(SONG_A)} {b}" for b in bs]

    def products(self, k):
        bs = self.take("product.b", PRODUCT_B, k)
        return [f"{self.rng.choice(PRODUCT_A)} {b}" for b in bs]

    def email_of(self, name):
        first, last = name.lower().split(" ", 1)
        dom = self.rng.choice(["example.com", "mail.test", "corp.example", "studio.example"])
        return f"{first}.{last.replace(' ', '')}@{dom}".replace("á", "a").replace("ö", "o")

    def money(self, lo=5, hi=2500):
        return f"${self.rng.uniform(lo, hi):,.2f}"

    def date(self, year=False):
        m = self.rng.choice(MONTHS)[:3]
        d = self.rng.randint(1, 28)
        return f"{m} {d}, {self.rng.choice([2025, 2026])}" if year else f"{m} {d}"

    def time(self):
        h = self.rng.randint(1, 12)
        return f"{h}:{self.rng.choice(['00', '05', '12', '15', '24', '30', '41', '45', '52'])} {self.rng.choice(['AM', 'PM'])}"

    def size(self):
        return self.rng.choice([f"{self.rng.randint(1, 990)} KB", f"{self.rng.uniform(1, 99):.1f} MB", f"{self.rng.uniform(1, 9):.2f} GB"])

    def sentence(self):
        return self.rng.choice(LOREM)

    def color(self):
        return self.rng.choice(COLORS)
