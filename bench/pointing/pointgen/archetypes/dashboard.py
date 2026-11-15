"""Analytics dashboards: KPI boards, chart grids, a report builder and a monitoring wall."""
from ..data import COMPANIES
from ..ui import esc, CHEV_D
from ..vocab import C, P

NAME = "dashboard"
KIND = "either"
VARIANTS = {"kpi_grid": "train", "top_nav": "train", "report_builder": "dev", "monitoring": "test"}

NAV = P("dash.nav", [
    ("Summary", "see the headline numbers at a glance", "gauge|layout-panel-top"),
    ("Audience", "learn who my visitors are", "users|user-round-search"),
    ("Acquisition", "see which channels bring people in", "megaphone|mouse-pointer-click"),
    ("Engagement", "see how actively people use the product", "activity|zap"),
    ("Retention", "see how many people come back over time", "repeat|calendar-check"),
    ("Revenue", "see how much money came in", "circle-dollar-sign|banknote"),
    ("Funnels", "see where people drop off between steps", "chart-bar-decreasing|chart-no-axes-column-decreasing"),
    ("Cohorts", "compare groups of users who joined at the same time", "table-2|chart-scatter"),
    ("Events", "browse the raw tracked actions", "radio|scroll-text"),
    ("Segments", "manage saved groups of users", "chart-pie|shapes"),
    ("Experiments", "check the results of A/B tests", "flask-conical|test-tube"),
    ("Real-time", "watch what is happening on the site this minute", "radar|heart-pulse"),
    ("Conversions", "see how many visits ended in a completed goal", "target|goal"),
    ("Campaigns", "review how my marketing pushes performed", "rocket|megaphone"),
    ("Geography", "see which countries traffic comes from", "map|globe"),
    ("Top pages", "see which URLs get the most views", "panel-top|file-text"),
    ("Referrals", "see which other sites send me visitors", "waypoints|route"),
    ("Search terms", "see what people typed to find the site", "telescope|scan-search"),
    ("Anomalies", "see unusual spikes and dips that were flagged", "triangle-alert|siren"),
    ("Reports", "get to the saved analyses", "file-chart-column|chart-area"),
    ("Dashboards", "browse the other boards I could switch to", "panels-top-left|layout-panel-left"),
    ("Data sources", "manage where the numbers are pulled in from", "database|plug"),
    ("Goals", "set the targets that count as success", "flag|trophy"),
    ("Forecast", "see the projected numbers for the coming weeks", "trending-up|chart-line"),
    ("Benchmarks", "compare my numbers with the industry average", "scale|chart-bar"),
    ("Heatmaps", "see where on the screen people click most", "flame|scan-eye"),
    ("Attribution", "see which touchpoints get credit for sales", "git-fork|workflow"),
    ("Lifetime value", "see how much a typical customer is worth over the years", "hand-coins|piggy-bank"),
    ("Churn", "see how many customers were lost", "user-minus|trending-down"),
    ("Logs", "read the raw lines servers wrote", "terminal|square-terminal"),
    ("Traces", "follow a single request through every service", "network|git-compare-arrows"),
    ("Incidents", "review past outages", "octagon-alert|shield-alert"),
    ("Service map", "see how the services depend on each other", "chart-network|share-2"),
    ("Explore", "run an ad-hoc query against the raw numbers", "compass|binoculars"),
    ("Starred", "get to the boards I marked as important", "star|sparkles"),
])
SELECTS = P("dash.sel", [
    ("Date range", "choose which days the numbers cover"), ("Compare to", "pick an earlier period to set against the current one"),
    ("Granularity", "switch between hourly, daily and weekly points"), ("Segment", "limit the numbers to one group of users"),
    ("Channel", "limit the numbers to one traffic origin"), ("Platform", "limit the numbers to web, iOS or Android"),
    ("Environment", "switch between production and staging figures"), ("Refresh every", "set how often the panels reload on their own"),
    ("Aggregation", "choose between sum, average and percentiles"), ("Breakdown", "split the totals by a chosen attribute"),
    ("Chart type", "switch between bars, lines and areas"), ("Cluster", "pick which group of machines to look at"),
    ("Namespace", "narrow the panels to one logical partition of the cluster"), ("Service", "narrow the panels to a single backend component"),
    ("Interval", "set the width of each time bucket"), ("Attribution model", "choose first-touch, last-touch or linear credit"),
    ("Workspace", "switch to a different property or organization"), ("Sampling", "trade accuracy for speed by reading a fraction of rows"),
    ("Time range", "pick how far back the panels look"), ("Rows shown", "choose how many lines the table lists"),
    ("Metric", "pick which measure the chart plots"), ("Instance", "narrow the panels to a single host"),
    ("Percentile", "choose p50, p95 or p99"), ("Region", "narrow the figures to one geographic area"),
])
OPTIONS = {
    "Date range": ["Last 7 days", "Last 28 days", "This month", "Last quarter", "Year to date"], "Compare to": ["Previous period", "Same period last year", "None"],
    "Granularity": ["Hourly", "Daily", "Weekly", "Monthly"], "Segment": ["All users", "New users", "Returning users", "Paying customers"],
    "Channel": ["All channels", "Organic search", "Paid social", "Email", "Direct"], "Platform": ["All platforms", "Web", "iOS", "Android"],
    "Environment": ["production", "staging", "development"], "Refresh every": ["Off", "5s", "30s", "1m", "5m"], "Aggregation": ["Sum", "Average", "Median", "p95", "Max"],
    "Breakdown": ["None", "Country", "Device", "Plan", "Referrer"], "Chart type": ["Line", "Stacked bars", "Area", "Table"], "Cluster": ["eu-west-1", "us-east-2", "ap-south-1"],
    "Namespace": ["default", "payments", "ingest", "web"], "Service": ["api-gateway", "checkout", "search", "auth"], "Interval": ["auto", "10s", "1m", "5m", "1h"],
    "Attribution model": ["Last touch", "First touch", "Linear", "Time decay"], "Workspace": ["Marketing site", "Mobile app", "Help center"],
    "Sampling": ["100%", "50%", "10%", "1%"], "Time range": ["Last 15 minutes", "Last 1 hour", "Last 6 hours", "Last 24 hours", "Last 7 days"],
    "Rows shown": ["10", "25", "50", "100"], "Metric": ["Sessions", "Users", "Revenue", "Conversion rate"], "Instance": ["All", "node-01", "node-02", "node-03"],
    "Percentile": ["p50", "p90", "p95", "p99"], "Region": ["All regions", "Europe", "North America", "Asia Pacific"],
}
C("dash.addw", "Add widget|Add panel|New chart", "chart-no-axes-column-increasing|grid-2x2-plus|layout-grid-plus",
  "put another visualization on this board|place one more tile on the board|extend the board with an extra graph")
C("dash.schedule", "Schedule report|Email this report|Set up delivery", "calendar-clock|mail-plus|clock-arrow-up",
  "have these numbers sent to my inbox automatically every week|arrange for the figures to arrive by mail on a recurring basis|set a recurring send-out of this board")
C("dash.run", "Run query|Generate|Refresh results", "",
  "recalculate the table with the fields I ticked|crunch the numbers for the current choice of fields|produce the table for the fields that are ticked")
C("dash.tv", "TV mode|Kiosk mode|Cycle view", "tv|tv-minimal|projector",
  "show the board without any menus for a wall screen|strip away the chrome for a lobby display|put the board into wall-display presentation")
C("dash.alert", "Create alert|Add alert rule|Notify me", "bell-plus|alarm-clock-plus|bell-electric",
  "get warned when {o} crosses a limit|be told automatically when {o} goes out of range|set a tripwire on {o}", o="this metric")
C("dash.inspect", "Inspect|View query|Explore data", "code-xml|braces|file-search-2",
  "see the underlying request behind {o}|look at the raw statement that feeds {o}|dig into the source rows of {o}", o="this panel")
C("dash.about", "About this metric|Metric definition|How this is calculated", "lightbulb|message-circle-question-mark|book-open-text", n="about|definition|calculation",
  intents="read an explanation of what {o} measures|find out how {o} is computed|learn what is behind the figure in {o}", o="this panel")
C("dash.expand", "Expand panel|View larger|Enlarge chart", "scaling|fullscreen|square-arrow-out-up-right", n="expand|view larger|enlarge",
  intents="blow {o} up to fill the page|see {o} bigger than the other tiles|give {o} the whole page", o="this panel")
C("dash.addfilter", "Add filter|New condition|Add rule", "", "narrow the figures by one more criterion|put an extra restriction on what is counted|restrict the numbers with another clause")

METRICS = ["Total revenue", "Active users", "Conversion rate", "Avg. order value", "Bounce rate", "New signups", "Page views", "Churn rate", "MRR",
           "Net promoter score", "Avg. session length", "Refund rate", "Cart abandonment", "Support tickets", "Trial conversions", "Returning visitors",
           "Cost per lead", "Click-through rate", "Open rate", "Unique visitors", "Orders", "Gross margin", "Daily active users", "Weekly active users",
           "Error rate", "p95 latency", "Requests per second", "CPU usage", "Memory usage", "Disk I/O", "Queue depth", "Cache hit ratio", "Uptime",
           "Apdex score", "DB connections", "Network in", "Network out", "Pod restarts", "5xx responses", "Throughput", "Time to first byte",
           "Deploy frequency", "Saturation", "GC pause time", "Open incidents", "Replication lag", "Thread count", "Heap in use", "Slow queries",
           "Login failures", "Ad spend", "Leads", "Pipeline value", "Win rate", "Seats in use", "Storage used", "API calls", "Webhook failures",
           "Email deliveries", "Signup to paid", "Sessions per user", "Scroll depth", "Search exits", "Downloads", "Subscribers",
           "Load average", "Swap usage", "Open file handles", "TLS handshakes", "DNS lookups", "Packet loss", "Kafka lag", "Job failures",
           "Cron runs", "Rate-limited calls", "Active websockets", "Cold starts", "Image pulls", "Node count", "Evictions", "Lock waits",
           "Index size", "Dead tuples", "Checkout starts", "Coupon redemptions", "Plan upgrades", "Seat expansions", "Invoice volume",
           "Chargebacks", "NPS responses", "First reply time", "Resolution time", "Backlog size", "App crashes", "ANR rate", "Install rate",
           "Uninstalls", "Push opt-ins", "Feature adoption", "Stickiness"]
DIMS = ["Country", "City", "Device type", "Browser", "Operating system", "Referrer", "Campaign", "Landing page", "Plan", "Signup month", "Age group",
        "Product category", "Payment method", "Sales rep", "Store", "Customer tier", "Coupon", "Day of week", "Hour of day", "App version",
        "Screen size", "Industry", "Company size", "Lead source", "Lifecycle stage", "Account owner", "Shipping method", "Brand", "Team",
        "Traffic medium", "Ad group", "Keyword", "Content type", "Author", "Experiment arm", "Subscription status", "First touch", "Exit page",
        "Connection type", "Locale"]
PLACES = ["Germany", "Brazil", "Japan", "Canada", "Nigeria", "France", "India", "Mexico", "Sweden", "Australia", "Spain", "Kenya", "Poland", "Chile",
          "Vietnam", "Italy", "Egypt", "Norway", "Peru", "Thailand", "Ireland", "Ghana", "Portugal", "Colombia", "Turkey", "Finland", "Morocco",
          "Argentina", "Indonesia", "Austria", "Greece", "Denmark", "Malaysia", "Belgium", "Uruguay", "Singapore", "Czechia", "Jordan", "Iceland", "Fiji",
          "Netherlands", "South Korea", "Philippines", "Hungary", "Tunisia", "Ecuador", "Latvia", "Sri Lanka", "Bolivia", "Senegal", "Croatia", "Qatar",
          "New Zealand", "Romania", "Paraguay", "Estonia", "Nepal", "Panama", "Slovenia", "Rwanda", "Costa Rica", "Bulgaria", "Oman", "Guatemala",
          "Lithuania", "Tanzania", "Luxembourg", "Cambodia", "Serbia", "Jamaica", "Ukraine", "Mongolia", "Malta", "Namibia", "Honduras", "Cyprus",
          "Bahrain", "Zambia", "Slovakia", "Mauritius", "Georgia", "Botswana", "Switzerland", "Taiwan", "Israel", "Pakistan", "Kuwait", "Uganda"]
PATHS = ["/pricing", "/blog/launch-week", "/docs/getting-started", "/signup", "/features/automation", "/customers", "/changelog", "/careers",
         "/integrations/chat", "/docs/api-reference", "/blog/year-in-review", "/contact-sales", "/templates", "/security", "/about", "/enterprise",
         "/docs/webhooks", "/blog/case-study-retail", "/download", "/login", "/partners", "/help/billing", "/features/reports", "/compare",
         "/events/summit", "/docs/sdk/python", "/status", "/press", "/legal/terms", "/community", "/features/mobile", "/blog/how-we-scale",
         "/onboarding/step-2", "/account/upgrade", "/docs/faq", "/newsletter", "/tour", "/demo", "/solutions/agencies", "/resources/ebooks"]
PERIODS = ["Day", "Week", "Month", "Quarter", "Year", "1H", "6H", "24H", "7D", "30D", "90D", "YTD", "All time", "Today", "Yesterday", "Custom",
           "12M", "MTD", "QTD", "1W", "1M", "3M", "6M", "1Y", "5Y", "Max", "Hourly view", "Daily view", "Weekly view", "Monthly view"]
BOARDS = ["Growth overview", "Executive summary", "Product health", "Marketing performance", "Checkout funnel", "API reliability", "Kubernetes cluster",
          "Sales pipeline", "Support operations", "Mobile app usage", "Infrastructure costs", "Onboarding metrics", "Database internals", "Edge network",
          "Weekly business review"]

CSS = """
.dash-pn{background:var(--bg);border:1px solid var(--bd);border-radius:var(--r2);display:flex;flex-direction:column;min-height:0;min-width:0;overflow:hidden}
.dash-dk .dash-pn{background:var(--bg1)}
.dash-ch{display:flex;align-items:center;gap:2px;height:calc(var(--rh) + 6px);padding:0 6px 0 12px;flex:none}
.dash-big{font-size:2em;font-weight:700;letter-spacing:-.02em;line-height:1.15}
.dash-grid{display:grid;gap:12px;align-content:start;grid-auto-rows:max-content}
.dash-log{font-family:var(--mono);font-size:10.5px;line-height:1.55;white-space:nowrap;overflow:hidden;color:var(--fg1);padding:0 12px}
.dash-ax{display:flex;justify-content:space-between;font-size:10px;color:var(--fg2);padding:2px 0 0}
.dash-hb{height:8px;border-radius:4px;background:var(--bg4);overflow:hidden;flex:1}
.dash-hb div{height:100%;background:var(--ac)}
.dash-in{height:calc(var(--ch) - 2px);font-size:.92em}
"""
_LOG = ["level=info msg=\"request completed\" status=200 dur=12ms path=/api/orders", "level=warn msg=\"slow query\" dur=412ms table=invoices",
        "level=info msg=\"cache refresh\" keys=1832", "level=error msg=\"upstream timeout\" svc=search attempt=2", "level=info msg=\"deploy finished\" rev=4f2a91c",
        "level=info msg=\"autoscale\" from=6 to=8 reason=cpu", "level=debug msg=\"heartbeat\" node=node-03", "level=warn msg=\"retrying webhook\" id=wh_8821"]


def _sel(ctx, cid, region, cls=""):
    """Dropdown with its caption inside the box, so the name is always visible."""
    label = ctx.lab(cid)
    opts = OPTIONS[label]
    attr = ctx.reg("select", "dropdown", label, cid=cid, region=region, anchor="select")
    ctx.options[ctx.last] = list(opts)
    return (f'<div class="inp dash-in fn {cls}"{attr}><span class="fnt">{esc(label)}</span><span class="nw m">{esc(ctx.rng.choice(opts))}</span>{CHEV_D}</div>')


def _months(rng, n=6):
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    s = rng.randrange(12)
    return '<div class="dash-ax">' + "".join(f"<span>{names[(s + i) % 12]}</span>" for i in range(n)) + "</div>"


def _value(rng, name):
    low = name.lower()
    if "rate" in low or "ratio" in low or "usage" in low or "margin" in low or "uptime" in low:
        return f"{rng.uniform(0.4, 99):.1f}%"
    if "revenue" in low or "value" in low or "mrr" in low or "spend" in low or "cost" in low:
        return f"${rng.uniform(1.2, 980):.1f}k"
    if "latency" in low or "time" in low or "length" in low or "lag" in low:
        return f"{rng.randint(8, 950)} ms"
    return f"{rng.randint(120, 98000):,}"


def _head(ctx, title, region, btns, noun="chart"):
    """Card header: the title is the card's target; small icon buttons act on that card."""
    attr = ctx.reg("row", noun, title, region=region, anchor="row")
    obj = f"the {title} {noun}"
    tail = "".join(ctx.ibtn(c, region, row=obj, obj=obj, cls="s", anchor="more" if c == "more" else "icon") for c in btns)
    return f'<div class="dash-ch"><span class="m el f1"{attr}>{esc(title)}</span>{tail}</div>'


def _body(ctx, kind, h):
    """Chart area of a card (never contains targets)."""
    rng = ctx.rng
    if kind == "line":
        return f'<div style="padding:0 12px 8px">{ctx.linechart(h=h, series=rng.randint(1, 3))}{_months(rng)}</div>'
    if kind == "bars":
        return f'<div style="padding:0 12px 8px">{ctx.bars(h=h, n=rng.choice([8, 12, 16]), two=rng.random() < 0.4)}{_months(rng)}</div>'
    if kind == "donut":
        legend = "".join(f'<div class="row g6 sm"><span class="dot" style="background:{c}"></span><span class="mut">{n}</span><div class="sp"></div><span>{rng.randint(5, 60)}%</span></div>'
                         for c, n in zip(["var(--ac)", "var(--ok)", "var(--warn)", "var(--bg4)"], ["Direct", "Organic", "Paid", "Other"]))
        return f'<div class="row g16" style="padding:4px 14px 12px">{ctx.donut(min(h, 120))}<div class="col g6 f1">{legend}</div></div>'
    if kind == "stat":
        up = rng.random() < 0.6
        return (f'<div class="col" style="padding:0 12px 10px"><span class="dash-big">{_value(rng, rng.choice(["rate", "time", "count"]))}</span>'
                f'<span class="sm {"ok" if up else "err"}">{"▲" if up else "▼"} {rng.uniform(0.2, 24):.1f}% vs previous</span>{ctx.spark(w=220, h=max(28, h - 70))}</div>')
    if kind == "gauge":
        f = rng.uniform(0.15, 0.95)
        col = "var(--ok)" if f < 0.6 else ("var(--warn)" if f < 0.85 else "var(--err)")
        return (f'<div class="col" style="align-items:center;padding:0 12px 10px"><svg viewBox="0 0 120 72" style="height:{h}px;max-width:100%;display:block"><path d="M10 62a50 50 0 0 1 100 0" fill="none" stroke="var(--bg4)" stroke-width="10" stroke-linecap="round"/>'
                f'<path d="M10 62a50 50 0 0 1 100 0" fill="none" stroke="{col}" stroke-width="10" stroke-linecap="round" stroke-dasharray="{157 * f:.0f} 157"/>'
                f'<text x="60" y="60" text-anchor="middle" font-size="19" font-weight="700" fill="var(--fg)">{f * 100:.0f}%</text></svg></div>')
    if kind == "hbars":
        rows = "".join(f'<div class="row g8 sm"><span class="mut" style="width:74px">{n}</span><div class="dash-hb"><div style="width:{rng.randint(8, 96)}%"></div></div><span style="width:40px" class="rt">{rng.randint(40, 9800):,}</span></div>'
                       for n in rng.sample(["Chrome", "Safari", "Firefox", "Edge", "Android", "iPhone", "Tablet", "Smart TV", "Linux", "Other"], min(6, max(3, h // 26))))
        return f'<div class="col g8" style="padding:2px 14px 12px">{rows}</div>'
    lines = "".join(f"<div>{rng.randint(10, 23)}:{rng.randint(10, 59)}:{rng.randint(10, 59)} {esc(rng.choice(_LOG))}</div>" for _ in range(max(3, h // 17)))
    return f'<div class="dash-log" style="padding-bottom:8px">{lines}</div>'


def _acct(ctx, region, who):
    attr = ctx.reg("button", "avatar", "Account menu", ui="icon", cid="account", region=region, anchor="account")
    return f'<div{attr}>{ctx.av(who, 28)}</div>'


def _navlist(ctx, cids, region, sel=0):
    return "".join(ctx.navc(c, region, on=i == sel, noun="page") for i, c in enumerate(cids))


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    big = H >= 1000
    navs = ctx.pick(NAV, rng.randint(8, 12))
    sels = ctx.pick(SELECTS, 6)
    rng.shuffle(sels)
    metrics = d.take("dash.metrics", METRICS)
    board = d.one("dash.boards", BOARDS)
    me = d.person()
    brand = d.one("company", COMPANIES).split()[0]
    ctx.ctxmenu = ["dash.expand", "dash.inspect", "-", "edit", "duplicate", "share", "download", "-", "dash.alert", "-", "delete"]
    ctx.ctxobj = "this panel"
    ctx.menus["mb.data"] = ["refresh", "import", "export", "-", "dash.schedule", "dash.addfilter", "-", "dash.addw"]
    logo = f'<div class="thumb" style="width:24px;height:24px;border-radius:7px;--c1:var(--ac);--c2:var(--acs2)"></div><span class="b lg">{esc(brand)}</span>'
    ch = 150 if H < 900 else (190 if H < 1200 else 230)
    kinds = ["line", "bars", "donut", "hbars", "line", "bars", "stat", "gauge", "line", "log"]

    if variant == "kpi_grid":
        sb, hd, mn = "the sidebar", "the page header", "the dashboard"
        side = (f'<div class="side br{" dk" if rng.random() < 0.3 else ""}" style="width:{rng.choice([212, 228, 244])}px"><div class="row g8 p12">{logo}</div>'
                f'<div class="p8" style="padding-top:0">{_sel(ctx, sels[0], sb, "w100") if sels else ""}</div><div class="col g2">{_navlist(ctx, navs, sb, rng.randrange(3))}</div><div class="sp"></div>'
                f'<div class="col g2 py8 bt">{ctx.navc("settings", sb, noun="link")}{ctx.navc("help", sb, noun="link")}</div>'
                f'<div class="row g8 p12 bt">{_acct(ctx, sb, me)}<span class="el f1 m">{esc(me)}</span></div></div>')
        head = (f'<div class="row g8" style="flex:none"><span class="xl b">{esc(board)}</span>{ctx.ibtn("fav", hd, obj="this board")}<div class="sp"></div>{ctx.search(hd, w=200, cls="soft")}'
                f'{_sel(ctx, sels[1], hd) if len(sels) > 1 else ""}{ctx.ibtn("refresh", hd, obj="these numbers")}{ctx.tbtn("export", hd, icon=True)}{ctx.tbtn("dash.addw", hd, cls="pri", icon=True)}</div>')
        nk = 4 if W < 1700 else 5
        cards = []
        for name in metrics[:nk]:
            attr = ctx.reg("row", "card", name, region=mn, anchor="row")
            up = rng.random() < 0.6
            cards.append(f'<div class="dash-pn" style="padding:10px 12px"><div class="row"><span class="mut sm el f1"{attr}>{esc(name)}</span>{ctx.ibtn("more", mn, row=f"the {name} card", obj=f"the {name} card", cls="s", anchor="more")}</div>'
                         f'<div class="row g8" style="align-items:flex-end"><span class="dash-big">{_value(rng, name)}</span><span class="pill {"g" if up else "r"}">{"+" if up else "−"}{rng.uniform(0.3, 28):.1f}%</span><div class="sp"></div>{ctx.spark(w=84, h=30)}</div></div>')
        krow = f'<div class="dash-grid" style="grid-template-columns:repeat({nk},1fr);flex:none">{"".join(cards)}</div>'
        per = ctx.seg(d.take("dash.periods", PERIODS, 4), active=1, region=mn)
        main_chart = (f'<div class="dash-pn" style="flex:2">{_head(ctx, metrics[nk], mn, ["dash.about", "dash.expand", "more"])}'
                      f'<div class="row g12 px12" style="flex:none"><span class="dash-big">{_value(rng, metrics[nk])}</span><div class="sp"></div>{per}</div>{_body(ctx, "line", ch)}</div>')
        side_chart = f'<div class="dash-pn" style="flex:1">{_head(ctx, metrics[nk + 1], mn, ["dash.expand", "more"])}{_body(ctx, "donut", ch)}{_body(ctx, "hbars", 90)}</div>'
        rows = []
        for path in d.take("dash.paths", PATHS, 6 + (8 if big else 0)):
            attr = ctx.reg("row", "row", path, region="the pages table", anchor="row", refs=[f"the row for {path}", f"the {path} row in the table"])
            rows.append(f'<div class="tr"{attr}><div class="td f mono sm"><span class="el">{esc(path)}</span></div><div class="td r" style="width:110px">{rng.randint(900, 99000):,}</div>'
                        f'<div class="td r" style="width:110px">{rng.randint(300, 40000):,}</div><div class="td r" style="width:90px">{rng.uniform(18, 82):.1f}%</div>'
                        f'<div class="td" style="width:150px"><div class="dash-hb"><div style="width:{rng.randint(6, 96)}%"></div></div></div></div>')
        thead = ('<div class="tr h"><div class="td f">Path</div><div class="td r" style="width:110px">Views</div><div class="td r" style="width:110px">Visitors</div>'
                 '<div class="td r" style="width:90px">Exit %</div><div class="td" style="width:150px">Share</div></div>')
        table = (f'<div class="dash-pn f1"><div class="dash-ch"><span class="m f1">Most viewed</span>{ctx.tbtn("filter", "the pages table", cls="sm ghost", icon=True)}{ctx.tbtn("sort", "the pages table", cls="sm ghost", icon=True)}</div>'
                 f'{thead}<div class="col f1 clip">{"".join(rows)}</div></div>')
        body = (f'<div class="row str f1">{side}<div class="col f1 clip g12 p16 bg1">{head}{krow}<div class="row str g12" style="flex:none">{main_chart}{side_chart}</div>{table}</div></div>')
    elif variant == "top_nav":
        tn, fb, gr = "the top navigation", "the filter bar", "the chart grid"
        links = "".join(ctx.navc(c, tn, noun="link", icon_html="", on=i == 1) for i, c in enumerate(navs[:6 if W < 1500 else 8]))
        top = (f'<div class="row g8 px16 bb" style="height:52px;flex:none">{logo}<div class="row g2" style="margin-left:14px">{links}</div><div class="sp"></div>{ctx.search(tn, w=210, cls="rnd soft")}'
               f'{ctx.ibtn("notif", tn)}{ctx.ibtn("help", tn)}{ctx.ibtn("settings", tn)}{_acct(ctx, tn, me)}</div>')
        sub = (f'<div class="row g8" style="flex:none"><span class="mut">Boards</span><span class="mut">/</span><span class="lg b">{esc(board)}</span>{ctx.ibtn("fav", "the page header", obj="this board")}<div class="sp"></div>'
               f'{ctx.tbtn("share", "the page header", icon=True)}{ctx.tbtn("dash.schedule", "the page header", icon=True)}{ctx.tbtn("export", "the page header", cls="pri")}</div>')
        filt = (f'<div class="row g8 wrap" style="flex:none">{"".join(_sel(ctx, c, fb) for c in sels[:4])}{ctx.tbtn("dash.addfilter", fb, cls="ghost sm")}<div class="sp"></div>'
                f'{ctx.seg(d.take("dash.periods", PERIODS, 4), active=rng.randrange(4), region=fb)}{ctx.ibtn("refresh", fb, obj="the charts", cls="bdr")}</div>')
        cols = 3 if W >= 1500 else 2
        cards = []
        for i, name in enumerate(metrics[:cols * (4 if big else 3)]):
            btns = rng.sample(["dash.about", "dash.expand", "download", "dash.alert"], rng.randint(1, 3)) + ["more"]
            cards.append(f'<div class="dash-pn">{_head(ctx, name, gr, btns)}{_body(ctx, kinds[i % len(kinds)], ch)}</div>')
        grid = f'<div class="dash-grid f1 clip" style="grid-template-columns:repeat({cols},1fr)">{"".join(cards)}</div>'
        body = f'<div class="col f1">{top}<div class="col f1 clip g12 p16 bg1">{sub}{filt}{grid}</div></div>'
    elif variant == "report_builder":
        fp, rt, tbr = "the fields panel", "the results table", "the report toolbar"
        dims = d.take("dash.dims", DIMS, 7 + (4 if big else 0))
        mets = metrics[:6 + (3 if big else 0)]
        on_d, on_m = dims[:2], mets[:3]
        dchk = "".join(f'<div style="padding:3px 12px">{ctx.check(x, x in on_d, region=fp)}</div>' for x in dims)
        mchk = "".join(f'<div style="padding:3px 12px">{ctx.check(x, x in on_m, region=fp)}</div>' for x in mets)
        left = (f'<div class="side br" style="width:{rng.choice([250, 270, 290])}px"><div class="p8">{ctx.search(fp, cls="soft")}</div><div class="hd">Dimensions</div><div class="col">{dchk}</div>'
                f'<div class="hd">Measures</div><div class="col f1 clip">{mchk}</div><div class="row g8 p12 bt">{ctx.tbtn("clear", fp, obj="the field choices")}<div class="sp"></div>{ctx.tbtn("dash.run", fp, cls="pri")}</div></div>')
        bar = (f'<div class="tb">{ctx.ibtn("sidebar.toggle", tbr)}<span class="b" style="margin:0 8px">{esc(board)}</span><span class="pill">Unsaved</span><div class="sp"></div>{"".join(_sel(ctx, c, tbr) for c in sels[:3])}'
               f'<div class="vsep"></div>{ctx.ibtn("undo", tbr)}{ctx.ibtn("redo", tbr)}{ctx.tbtn("save", tbr)}{ctx.tbtn("dash.schedule", tbr)}{ctx.tbtn("export", tbr, cls="pri")}{_acct(ctx, tbr, me)}</div>')
        chart = f'<div class="dash-pn" style="flex:none">{_head(ctx, "Preview of " + on_m[0], "the preview card", ["dash.inspect", "dash.expand", "more"], noun="card")}{_body(ctx, "bars", ch)}</div>'
        cw = 150
        hcells = "".join(f'<div class="td{" f" if i == 0 else " r"}" style="{"" if i == 0 else f"width:{cw}px"}"{ctx.reg("button", "column header", x, region=rt)}>{esc(x)}{CHEV_D if i == 2 else ""}</div>' for i, x in enumerate(on_d[:1] + on_m))
        rows = []
        for place in d.take("dash.places", PLACES, 9 + (14 if big else 0)):
            attr = ctx.reg("row", "row", place, region=rt, anchor="row")
            vals = "".join(f'<div class="td r" style="width:{cw}px">{_value(rng, m)}</div>' for m in on_m)
            rows.append(f'<div class="tr z"{attr}><div class="td f"><span class="el">{esc(place)}</span></div>{vals}</div>')
        table = f'<div class="dash-pn f1"><div class="tr h">{hcells}</div><div class="col f1 clip">{"".join(rows)}</div></div>'
        body = f'<div class="col f1">{bar}<div class="row str f1">{left}<div class="col f1 clip g12 p16 bg1">{chart}{table}</div></div></div>'
    else:  # monitoring
        rl, tb, vb, gr = "the icon rail", "the top bar", "the variables row", "the panel grid"
        rail_ids = ctx.pick(NAV, 7, icon=True)
        rail = "".join(ctx.ibtn(c, rl, on=i == 1, noun=rng.choice(["button", "icon"])) for i, c in enumerate(rail_ids))
        rail = f'<div class="rail br">{ctx.ibtn("apps", rl)}{ctx.ibtn("search", rl)}{rail}<div class="sp"></div>{ctx.ibtn("help", rl)}{_acct(ctx, rl, me)}</div>'
        top = (f'<div class="row g4 px12 bb" style="height:44px;flex:none"><span class="mut">{esc(brand)}</span><span class="mut">/</span><span class="b">{esc(board)}</span>{ctx.ibtn("fav", tb, obj="this board", cls="s")}'
               f'{ctx.ibtn("share", tb, obj="this board", cls="s")}<div class="sp"></div>{ctx.ibtn("dash.addw", tb)}{ctx.ibtn("save", tb)}{ctx.ibtn("settings", tb)}<div class="vsep"></div>'
               f'{_sel(ctx, sels[0], tb) if sels else ""}{ctx.ibtn("zoomout", tb, cls="bdr")}{ctx.ibtn("refresh", tb, obj="every panel", cls="bdr")}{_sel(ctx, sels[1], tb) if len(sels) > 1 else ""}{ctx.ibtn("dash.tv", tb)}</div>')
        varrow = f'<div class="row g8 px12 py4 wrap" style="flex:none">{"".join(_sel(ctx, c, vb) for c in sels[2:6])}<div class="sp"></div>{ctx.tbtn("dash.addfilter", vb, cls="ghost sm")}</div>'
        cols = 4 if W >= 1900 else (3 if W >= 1400 else 2)
        ph = 96 if H < 900 else (118 if H < 1200 else 150)
        mk = ["stat", "line", "gauge", "line", "bars", "log", "line", "stat", "hbars", "line", "bars", "gauge"]
        panels = []
        for i, name in enumerate(metrics[:cols * (5 if big else 4)]):
            btns = rng.sample(["dash.alert", "dash.inspect", "dash.expand", "dash.about"], rng.randint(2, 3)) + ["more"]
            span = ' style="grid-column:span 2"' if cols > 2 and mk[i % len(mk)] in ("log",) else ""
            panels.append(f'<div class="dash-pn"{span}>{_head(ctx, name, gr, btns, noun="panel")}{_body(ctx, mk[i % len(mk)], ph)}</div>')
        grid = f'<div class="dash-grid f1 clip" style="grid-template-columns:repeat({cols},1fr);gap:8px;padding:4px 12px 12px">{"".join(panels)}</div>'
        body = f'<div class="row str f1 dash-dk">{rail}<div class="col f1 clip">{top}{varrow}{grid}</div></div>'
    return {"title": f"{board} — {brand}", "body": body, "menus": ["mb.file", "mb.edit", "mb.view", "mb.data", "mb.window", "mb.help"],
            "url": f"{brand.lower()}.example.com/boards/{board.lower().replace(' ', '-')}", "app": rng.choice(["Insightly", "Metricbase", "Chartroom"]), "css": CSS}
