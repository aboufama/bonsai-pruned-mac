"""Terminals with side panels: session managers, split panes, SFTP, SQL consoles, log viewers."""
import re

from ..data import HOSTS, SHELL
from ..splits import pool
from ..ui import esc, CHEV_D, CHEV_R
from ..vocab import C, P

NAME = "terminal"
KIND = "desktop"
VARIANTS = {"tabs_sessions": "train", "tmux_split": "train", "ssh_sftp": "train", "db_console": "dev", "devops_logs": "test"}

C("term.newtab", "New tab|Open tab|Add session tab", "plus|circle-plus|square-plus", "start another shell next to the existing ones|get an additional shell without closing this one|begin one more command-line prompt in this window", n="new tab|open tab|add tab")
C("term.splitv", "Split vertically|New pane right|Divide side by side", "columns-2|square-split-horizontal|panel-right-dashed", "put a second shell to the right of this one|show two shells next to each other|cut the shell area into a left and a right half")
C("term.splith", "Split horizontally|New pane below|Divide top and bottom", "rows-2|square-split-vertical|panel-bottom-dashed", "put a second shell underneath this one|stack two shells one above the other|cut the shell area into an upper and a lower half")
C("term.clear", "Clear screen|Clear output|Wipe scrollback", "brush-cleaning|eraser|list-x", "erase everything printed in the shell so far|empty the text that has piled up in the shell|start with a blank shell without closing it")
C("term.connect", "Connect|Open session|Start connection", "plug|plug-zap|cable|plug-2|log-in", "log in to {o}|get a shell on {o}|reach {o} over the network", o="the selected host")
C("term.disconnect", "Disconnect|Close session|End connection", "unplug|power-off|circle-power", "log out of the remote machine|hang up the link to the server|drop the remote link I am on")
C("term.addhost", "New host|Add server|Add connection", "server-plus|monitor-up|hard-drive-upload", "save the details of another machine I log in to|register one more remote machine in the list|store a remote machine's address for later")
C("term.runsnip", "Run snippet|Insert command|Paste to terminal", "play|circle-play|square-play", "execute {o} in the shell|send {o} to the active shell|fire {o} into the prompt", o="the selected snippet")
C("term.runq", "Run query|Execute SQL|Execute statement", "play|circle-play|square-play", "send what I typed in the editor to the database|get the result rows for what I wrote in the editor|have the database evaluate what is in the editor")
C("term.explain", "Explain plan|Show query plan|Analyze query", "list-tree|workflow|waypoints|chart-gantt|scan-text", "see how the database intends to carry out my SQL|find out which indexes my SQL would use|inspect the strategy the engine picks for my SQL")
C("term.formatq", "Format SQL|Beautify query|Tidy statement", "wand-sparkles|sparkles|align-left|brush-cleaning|broom-sparkles", "re-indent what I typed so it reads cleanly|clean up the layout of the text in the editor|make the editor contents neatly indented")
C("term.txcommit", "Commit transaction|Apply transaction|Confirm writes", "check-check|circle-check|check", "make my pending data modifications permanent|finalize the data modifications I just ran|lock in the pending data modifications")
C("term.rollback", "Roll back|Undo transaction|Revert writes", "undo-2|undo|rotate-ccw", "cancel the data modifications I have not finalized|throw away my pending data modifications|return the data to how it was before my pending statements")
C("term.pause", "Pause stream|Freeze log|Hold output", "pause|circle-pause|square-pause", "stop new lines from scrolling in for a moment|keep the listing still so I can read it|temporarily halt the incoming lines")
C("term.follow", "Follow tail|Live tail|Auto-scroll", "arrow-down-to-line|chevrons-down|circle-arrow-down|arrow-down-from-line|move-down", "keep jumping to the newest line as it arrives|stay pinned to the latest entry|always show the most recent line at the bottom")
C("term.wrap", "Wrap lines|Soft wrap|Fold long lines", "wrap-text|corner-down-left|list-end|corner-down-right", "make wide entries continue on the next row instead of running off|break entries that are too wide for the pane|stop wide entries from being cut at the right edge")
C("term.restart", "Restart service|Reboot service|Bounce service", "rotate-cw|refresh-cw|refresh-ccw", "stop the selected workload and bring it up again|cycle the selected workload|take the selected workload down and back up")
C("term.canceltx", "Cancel transfer|Abort transfer|Stop transfer", "x|circle-x|square-x", "stop {o} from being copied|halt the copying of {o}|give up on moving {o}", o="the active file")
C("term.maxpane", "Maximize pane|Zoom pane|Enlarge pane", "maximize-2|expand|maximize", "let {o} take over the whole window|make {o} fill the entire shell area|blow {o} up to use all the space", o="this pane")

SNIPPETS = P("term.snip", [
    ("Restart nginx", "bounce the web server"), ("Tail app log", "watch the application's output as it is written"),
    ("Disk usage summary", "find out how full each volume is"), ("List listening ports", "see which sockets are accepting connections"),
    ("Flush DNS cache", "make the machine forget resolved hostnames"), ("Show failed units", "list the systemd services that crashed"),
    ("Top memory processes", "find what is eating the most RAM"), ("Rotate logs now", "force old output to be archived immediately"),
    ("Docker prune", "delete unused containers and images"), ("Renew TLS certificate", "get a fresh HTTPS cert for the site"),
    ("Dump database", "export the whole Postgres instance to a backup"), ("Git pull and rebuild", "fetch the newest code and compile it"),
    ("Check open files limit", "see how many descriptors a process may hold"), ("Kernel version", "print which Linux release is installed"),
    ("Recent logins", "see who signed in to this box lately"), ("Purge temp files", "empty the scratch directory"),
    ("Firewall status", "check which inbound traffic is allowed"), ("Sync clock", "correct the system time against an NTP source"),
    ("Kubernetes contexts", "list the clusters my CLI can talk to"), ("Test SMTP relay", "verify outgoing mail is being accepted"),
    ("Reload cron table", "make the scheduler pick up edited jobs"), ("Show routing table", "see where packets for each network are sent"),
    ("Archive home folder", "bundle my user directory into a tarball"), ("Count 5xx responses", "tally server errors in the access log"),
    ("Watch GPU load", "monitor the graphics cards once per second"),
])
COMMANDS = ["sudo systemctl restart nginx", "tail -f /var/log/app/server.log", "df -h --total", "ss -tulpn", "resolvectl flush-caches",
            "systemctl --failed", "ps aux --sort=-%mem | head", "logrotate -f /etc/logrotate.conf", "docker system prune -af",
            "certbot renew --quiet", "pg_dumpall > backup.sql", "git pull && make build", "ulimit -n", "uname -r", "last -n 20",
            "rm -rf /tmp/*", "ufw status verbose", "chronyc makestep", "kubectl config get-contexts", "swaks --to ops@example.com",
            "crontab -l", "ip route show", "tar czf home.tgz ~", "grep -c ' 5[0-9][0-9] ' access.log", "watch -n1 nvidia-smi"]
CMD = dict(zip(SNIPPETS, COMMANDS))


def _pool(name, text):
    items = [x.strip() for x in text.replace("\n", "|").split("|") if x.strip()] if isinstance(text, str) else list(text)
    pool(name, items, "train")   # claim labels at import so ownership never depends on run order
    return items


_pool("hosts", HOSTS)
TABLES = _pool("term.tables", """users|orders|invoices|products|sessions|payments|audit_log|customers|subscriptions|shipments|carts
refunds|coupons|addresses|inventory|suppliers|reviews|tickets|teams|memberships|api_keys|webhooks|events|notifications|plans
line_items|categories|warehouses|returns|tax_rates|employees|departments|projects|timesheets|leads|campaigns|attachments
feature_flags|migrations|password_resets|price_lists|vendors|contracts|page_views|devices|locations|shifts|payouts|ledgers
bundles|ratings|waitlist|referrals|exports|imports|quotas|regions|tags|comments|uploads|consents|budgets|forecasts|incidents
releases|backups|domains|mailboxes|templates""")
SCHEMAS = _pool("term.schemas", "analytics|audit|staging|billing|archive|reporting|warehouse|crm|ops|sandbox|legacy|events_raw|finance|identity|search")
COLS = _pool("term.cols", """id|email|created_at|status|total|customer_id|updated_at|amount|currency|country|plan|quantity|sku
full_name|last_login|is_active|region|discount|tax|shipped_at|priority|owner_id|ip_address|attempts|score|channel|notes
expires_at|unit_price|referrer""")
SQLFILES = _pool("term.sqlfiles", """orders_by_region|churned_users|daily_revenue|slow_queries|top_customers|refund_audit|signup_funnel
inventory_gaps|duplicate_emails|weekly_cohorts|unpaid_invoices|session_lengths|coupon_usage|late_shipments|plan_upgrades
failed_payments|active_teams|tax_summary|stale_carts|api_usage""")
LEVELS = _pool("term.levels", "ERROR|WARN|INFO|DEBUG|TRACE|FATAL|NOTICE|AUDIT|CRITICAL|VERBOSE")
RANGES = _pool("term.ranges", """Last 15 min|Last hour|Last 6 hours|Last 24 hours|Last 7 days|Past 5 min|Past 30 min|Past 3 hours
Past 12 hours|Past 2 days|Today|Yesterday|This week|Live|Custom range""")
ENVS = _pool("term.envs", "production|staging|development|qa|sandbox|canary|preview|eu-west|us-east|demo|integration|perf|dr-site|edge|internal")
TMUXW = _pool("term.tmuxw", "zsh|vim|logs|htop|ssh|psql|node|python|make|tail|git|docker|k9s|nvim|bash|top|irb|redis-cli|watch|man")
RESTABS = _pool("term.restabs", "Results|Messages|Plan|Query history|Chart|Output|Statistics|Notices|Raw|Grid output|Timing|Errors|Schema|Preview|Log")
STATUSES = ["active", "pending", "paid", "failed", "shipped", "trial", "closed", "refunded"]
MSGS = ["request id={h} path=/api/orders status=200 {n}ms", "cache miss key=user:{n} backend=redis", "slow query {n}ms: SELECT * FROM invoices",
        "retrying upstream call attempt={n}", "connection pool exhausted, waiting {n}ms", "job {h} finished in {n}ms", "token refresh for tenant {n}",
        "healthcheck ok latency={n}ms", "rate limit hit client={h}", "deployed revision {h} to 3 replicas", "worker {n} picked up task {h}",
        "payload validation failed field=email", "gc pause {n}ms heap=512MB", "websocket closed code=1006 peer={h}"]

CSS = """
.term-out{font-family:var(--mono);font-size:calc(var(--fs) - .5px);line-height:1.5;white-space:pre;padding:8px 12px}
.term-dk{background:#101216;color:#d6dae0}.term-dk .mut{color:#8b93a1}
.term-ps{color:#3fb950;font-weight:700}.term-kw{color:var(--code-k)}.term-str{color:var(--code-s)}
.term-pane{border:1px solid var(--bd);min-width:0;min-height:0}
.term-cut{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1 1 0}
.term-chip{display:inline-flex;align-items:center;gap:5px;height:calc(var(--ch) - 2px);padding:0 9px;border-radius:999px;border:1px solid var(--bd2);font-size:.9em;white-space:nowrap;flex:none}
.term-chip.on{background:var(--acs2);border-color:var(--ac)}
.term-nb.tabs{border-bottom:none;flex:1 1 0;min-width:0;overflow:hidden}
.term-tmux{flex:none;display:flex;gap:14px;height:20px;padding:0 8px;font-family:var(--mono);font-size:12px;background:#2f7d32;color:#f3fff3;align-items:center;white-space:nowrap}
.term-log{font-family:var(--mono);font-size:calc(var(--fs) - 1px);line-height:1.6;white-space:pre;padding:0 10px}
"""
_SQLKW = re.compile(r"\b(SELECT|FROM|WHERE|JOIN|LEFT|INNER|ON|GROUP BY|ORDER BY|LIMIT|AS|AND|OR|DESC|COUNT|SUM|HAVING|IS|NOT|NULL|INTERVAL|NOW)\b|('[^']*')")


def _out(n, off=0, dark=True):
    rows = []
    for i in range(n):
        line = SHELL[(i + off) % len(SHELL)]
        if line.startswith("$ "):
            rows.append(f'<div><span class="term-ps">$</span> <span class="b">{esc(line[2:])}</span></div>')
        else:
            rows.append(f"<div>{esc(line) or '&nbsp;'}</div>")
    return f'<div class="term-out f1 clip{" term-dk" if dark else ""}">{"".join(rows)}</div>'


def _sql(text):
    out, pos = [], 0
    for m in _SQLKW.finditer(text):
        out.append(esc(text[pos:m.start()]))
        out.append(f'<span class="{"term-kw" if m.group(1) else "term-str"}">{esc(m.group(0))}</span>')
        pos = m.end()
    return "".join(out) + esc(text[pos:])


def _value(rng, d, col, i):
    if col.endswith("_at") or col == "last_login":
        return f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d} {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"
    if col in ("id", "customer_id", "owner_id", "quantity", "attempts", "score"):
        return str(rng.randint(1, 99999) if col.endswith("id") else rng.randint(0, 120))
    if col in ("total", "amount", "discount", "tax", "unit_price"):
        return f"{rng.uniform(1, 2400):.2f}"
    if col == "email":
        return f"user{rng.randint(10, 999)}@example.com"
    if col == "status":
        return rng.choice(STATUSES)
    if col == "is_active":
        return rng.choice(["true", "false"])
    if col == "ip_address":
        return f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    if col == "full_name":
        return d.people(40)[i % 40]
    opts = {"currency": ["EUR", "USD", "GBP", "JPY"], "country": ["DE", "US", "JP", "FR", "BR"], "plan": ["free", "pro", "team"],
            "region": ["emea", "apac", "amer"], "channel": ["web", "api", "organic", "partner"], "priority": ["high", "normal", "low"],
            "sku": [f"SKU-{rng.randint(1000, 9999)}"], "referrer": ["newsletter", "search", "direct", "—"]}
    return rng.choice(opts.get(col, ["—", "n/a", "ok"]))


def _toolbar(ctx, region, extra=()):
    return ('<div class="tb">' + ctx.ibtns(["term.newtab", "term.splitv", "term.splith", "|", "copy", "paste", "term.clear", "|", "zoomin", "zoomout",
                                            "fullscreen", "|"] + list(extra), region, obj="the terminal output")
            + f'<div class="sp"></div>{ctx.search(region, w=200, cls="soft")}{ctx.ibtn("settings", region)}</div>')


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    hosts = d.take("hosts", HOSTS, 14)
    user = rng.choice(["deploy", "admin", "ops", "ubuntu", "root", "ci"])
    n_lines = H // 17 + 2
    dark = rng.random() < 0.65
    side_w = rng.choice([220, 250, 280]) + (40 if W > 2000 else 0)
    ctx.ctxmenu = ["term.connect", "term.newtab", "-", "copy", "duplicate", "rename", "edit", "-", "delete"]
    ctx.ctxobj = "the selected host"
    ctx.menus["mb.terminal"] = ["term.newtab", "term.splitv", "term.splith", "-", "term.clear", "term.connect", "term.disconnect"]
    menus = ["mb.file", "mb.edit", "mb.view", "mb.terminal", "mb.window", "mb.help"]
    title = f"{user}@{hosts[0]}: ~"

    if variant == "tabs_sessions":
        region, rows = "the host list", []
        envs = d.take("term.envs", ENVS, 3)
        for i, h in enumerate(hosts[:H // 30]):
            if i % 5 == 0 and envs:
                rows.append(f'<div class="hd">{esc(envs[(i // 5) % len(envs)])}</div>')
            attr = ctx.reg("row", "host", h, region=region, anchor="row")
            col = rng.choice(["var(--ok)", "var(--ok)", "var(--warn)", "var(--fg2)"])
            rows.append(f'<div class="li{" sel" if i == 0 else ""}"{attr}><span class="dot" style="background:{col}"></span><span class="el f1 mono sm">{esc(h)}</span>'
                        f'{ctx.ibtn("term.connect", region, row=h, obj=h, cls="s")}</div>')
        side = (f'<div class="side br" style="width:{side_w}px"><div class="row g4 p8">{ctx.search(region, cls="soft f1")}{ctx.ibtn("term.addhost", region, cls="bdr")}</div>'
                f'<div class="col f1 clip">{"".join(rows)}</div><div class="row g4 p8 bt">{ctx.ibtns(["import", "export", "settings"], region, cls="s", obj="the host list")}</div></div>')
        tabs = ctx.tabs(hosts[:rng.randint(2, 4)], active=0, region="the session tabs", cls="box term-nb", closable=True)
        sb = (f'<div class="sbar"><span>{esc(user)}@{esc(hosts[0])} · SSH-2.0 · xterm-256color</span><div class="sp"></div><span>{rng.randint(80, 220)}×{rng.randint(24, 60)}</span>'
              f'<span>{rng.randint(8, 190)} ms</span>{ctx.ibtn("term.disconnect", "the status bar", cls="s")}</div>')
        body = (f'<div class="row str f1">{side}<div class="col f1">{_toolbar(ctx, "the toolbar", ["history"])}<div class="row bb bg1 fn">{tabs}'
                f'{ctx.ibtn("term.newtab", "the session tabs", cls="s")}</div>{_out(n_lines, rng.randint(0, 30), dark)}{sb}</div></div>')
    elif variant == "tmux_split":
        region = "the pane headers"

        def pane(i, lines):
            name = f"{user}@{hosts[i]}"
            attr = ctx.reg("row", "pane", name, region=region, refs=[f"the title bar of the {name} pane", f"the pane header that says {name}"])
            acts = ctx.ibtn("term.maxpane", region, row=name, obj=f"the {name} pane", cls="s") + ctx.ibtn("close.panel", region, row=name, obj=f"the {name} pane", cls="s")
            return (f'<div class="col f1 term-pane"><div class="row px8 bg2 bb fn" style="height:24px"><span class="mono sm"{attr}>{esc(name)}</span><div class="sp"></div>{acts}</div>'
                    f'{_out(lines, rng.randint(0, 40), dark)}</div>')

        three = W >= 1440 and rng.random() < 0.7
        right = f'<div class="col f1">{pane(1, n_lines // 2)}{pane(2, n_lines // 2)}</div>' if three else pane(1, n_lines)
        wins = "".join(f'<span{ctx.reg("tab", "window", f"{i}:{w}", region="the tmux status line", refs=[f"the {w} window in the tmux status line", f"window {i}:{w} in the green bar"])}>'
                       f'{i}:{esc(w)}{"*" if i == 1 else ""}</span>' for i, w in enumerate(d.take("term.tmuxw", TMUXW, rng.randint(3, 5))))
        tmux = f'<div class="term-tmux"><span>[{esc(rng.choice(["main", "ops", "dev", "0"]))}]</span>{wins}<div class="sp"></div><span>"{esc(hosts[0])}" {rng.randint(10, 23)}:{rng.randint(10, 59)}</span></div>'
        rs, snips = "the snippets panel", []
        for c in ctx.pick(SNIPPETS, H // 52):
            lab = ctx.lab(c)
            attr = ctx.reg("row", "snippet", lab, cid=c, region=rs, anchor="row")
            rw = f"the {lab} snippet"
            snips.append(f'<div class="col px12 py4 bb fn"{attr}><div class="row g6"><span class="m el f1">{esc(lab)}</span>{ctx.ibtn("term.runsnip", rs, row=rw, cls="s")}'
                         f'{ctx.ibtn("edit", rs, row=rw, cls="s")}</div><div class="row"><span class="mono xs mut term-cut">{esc(CMD[c])}</span></div></div>')
        side = (f'<div class="side bl" style="width:{side_w + 30}px"><div class="row g4 p8"><span class="b f1">Saved commands</span>{ctx.ibtn("add", rs, cls="s", obj="the saved commands")}'
                f'{ctx.ibtn("more", rs, cls="s", anchor="more", obj="the saved commands")}</div><div class="px8" style="padding-bottom:8px">{ctx.search(rs, cls="soft")}</div>'
                f'<div class="col f1 clip">{"".join(snips)}</div></div>')
        body = f'<div class="row str f1"><div class="col f1"><div class="row str f1">{pane(0, n_lines)}{right}</div>{tmux}</div>{side}</div>'
        ctx.ctxmenu, ctx.ctxobj = ["term.runsnip", "-", "copy", "duplicate", "rename", "edit", "pin", "-", "delete"], "the selected snippet"
    elif variant == "ssh_sftp":
        tabs = ctx.tabs(hosts[:rng.randint(2, 3)], active=0, region="the session tabs", cls="box term-nb", closable=True)
        rs = "the file transfer panel"
        path = ctx.field("Remote path", rng.choice(["/var/www/app", "/home/deploy/releases", "/srv/data/exports", "/etc/nginx/conf.d"]), region=rs, above=False, cls="mono")
        rows, files = [], d.mixed_files(H // 26)
        for name in d.files("folder", 3):
            attr = ctx.reg("row", "folder", name, region=rs, anchor="row")
            rows.append(f'<div class="tr"{attr}><div class="td f">{ctx.deco("folder", "folder-closed", "folder-open", "folders", blank=True)}<span class="el">{esc(name)}</span></div>'
                        f'<div class="td mut r" style="width:84px">—</div><div class="td" style="width:36px"></div></div>')
        for name, _ in files[3:]:
            attr = ctx.reg("row", "file", name, region=rs, anchor="row")
            rows.append(f'<div class="tr"{attr}><div class="td f">{ctx.deco("file", "file-text", "file-code", "file-digit", blank=True)}<span class="el">{esc(name)}</span></div>'
                        f'<div class="td mut r" style="width:84px">{d.size()}</div><div class="td" style="width:36px">{ctx.ibtn("download", rs, row=name, obj=f"the remote file {name}", cls="s")}</div></div>')
        queue = []
        for name, _ in files[:3]:
            pct = rng.randint(5, 95)
            queue.append(f'<div class="row g8 px12 fn" style="height:var(--rh)"><span class="el sm" style="width:42%">{esc(name)}</span><div class="prog f1"><div style="width:{pct}%"></div></div>'
                         f'<span class="xs mut" style="width:30px">{pct}%</span>{ctx.ibtn("term.canceltx", rs, row=name, obj=f"the transfer of {name}", cls="s")}</div>')
        side = (f'<div class="side bl" style="width:{side_w + 140}px"><div class="row g4 p8 bb"><div class="f1">{path}</div>{ctx.ibtns(["up", "refresh", "view.list"], rs, obj="the remote folder")}</div>'
                f'<div class="tr h"><div class="td f">Name</div><div class="td r" style="width:84px">Size</div><div class="td" style="width:36px"></div></div><div class="col f1 clip">{"".join(rows)}</div>'
                f'<div class="row g8 px12 bt bg2 fn" style="height:30px"><span class="b sm">Transfers</span><span class="bdg">{len(queue)}</span><div class="sp"></div>{ctx.tbtn("upload", rs, cls="sm", icon=True)}</div>{"".join(queue)}</div>')
        body = (f'<div class="row str f1"><div class="col f1">{_toolbar(ctx, "the toolbar", ["term.disconnect"])}<div class="row bb bg1 fn">{tabs}{ctx.ibtn("term.newtab", "the session tabs", cls="s")}</div>'
                f'{_out(n_lines, rng.randint(0, 30), dark)}</div>{side}</div>')
    elif variant == "db_console":
        region = "the schema tree"
        tables = d.take("term.tables", TABLES, 30)
        conn = ctx.select("Connection", f"{hosts[0]} · postgres", options=hosts[:5], region=region, above=False, refs=["the connection dropdown above the schema tree", "the database connection picker"])
        tico = ctx.deco("table", "table-2", "sheet", "table-properties", "grid-3x3", blank=True)
        trows = "".join(f'<div class="li" style="padding-left:24px"{ctx.reg("row", "table", t, region=region, anchor="row")}>{tico}<span class="el mono sm">{esc(t)}</span>'
                        f'<span class="sp"></span><span class="fnt xs">{rng.randint(1, 900)}k</span></div>' for t in tables)
        more = "".join(f'<div class="li b sm fn"{ctx.reg("row", "schema", sc, region=region)}><span class="mut">{CHEV_R}</span>{esc(sc)}</div>' for sc in d.take("term.schemas", SCHEMAS, 3))
        side = (f'<div class="side br" style="width:{side_w}px"><div class="col g6 p8 bb">{conn}{ctx.search(region, cls="soft")}</div>'
                f'<div class="li b sm"><span class="mut">{CHEV_D}</span>public</div><div class="col f1 clip">{trows}{more}</div></div>')
        files = [f"{s}.sql" for s in d.take("term.sqlfiles", SQLFILES, rng.randint(2, 4))]
        tabs = ctx.tabs(files, active=0, region="the query tabs", cls="box", closable=True)
        cols = d.take("term.cols", COLS, min(10, 3 + W // 260))
        t0 = tables[0]
        sql = [f"SELECT {', '.join('t.' + c for c in cols[:4])},", f"       COUNT(*) AS n, SUM(t.{cols[-1]}) AS total_{cols[-1]}", f"FROM {t0} AS t",
               f"LEFT JOIN {tables[1]} AS j ON j.{t0[:-1]}_id = t.id", f"WHERE t.{cols[1]} IS NOT NULL AND j.kind = 'standard'",
               f"  AND t.{cols[2]} > NOW() - INTERVAL '30 days'", f"GROUP BY {', '.join('t.' + c for c in cols[:4])}", f"ORDER BY n DESC", "LIMIT 500;"]
        ed = "".join(f'<div style="display:flex"><span class="fnt" style="width:40px;text-align:right;padding-right:12px;flex:none">{i + 1}</span><span>{_sql(s)}</span></div>' for i, s in enumerate(sql))
        tr = "the query toolbar"
        tb = (f'<div class="tb plain">{ctx.tbtn("term.runq", tr, cls="pri", icon=True)}{ctx.ibtns(["term.explain", "term.formatq", "|", "term.txcommit", "term.rollback", "|", "save", "history"], tr, obj="this query")}'
              f'<div class="sp"></div>{ctx.select("Row limit", "500 rows", region=tr, above=False, w=110, refs=["the row limit dropdown in the query toolbar"])}{ctx.ibtn("more", tr, anchor="more", obj="this query")}</div>')
        rr = "the results grid"
        rtabs = ctx.tabs(d.take("term.restabs", RESTABS, 3), active=0, region="the results bar", cls="term-nb")
        rbar = (f'<div class="row bt bb bg1 fn" style="padding-right:8px">{rtabs}<span class="mut sm" style="margin-right:10px">{rng.randint(12, 500)} rows · {rng.randint(8, 900)} ms</span>'
                f'{ctx.ibtns(["filter", "export", "copy", "refresh"], "the results bar", cls="s", obj="the result rows")}</div>')
        cw = "flex:1 1 0;min-width:0"
        head = "".join(f'<div class="td mono" style="{cw}"{ctx.reg("columnheader", "column header", c, region=rr, refs=[f"the {c} column header", f"the header of the {c} column"])}>'
                       f'<span class="el">{esc(c)}</span></div>' for c in cols)
        grid = "".join('<div class="tr z">' + "".join(f'<div class="td mono sm" style="{cw}"><span class="term-cut">{esc(_value(rng, d, c, i))}</span></div>' for c in cols) + "</div>"
                       for i in range(H // 26))
        sb = f'<div class="sbar"><span class="dot" style="background:var(--ok)"></span><span>{esc(hosts[0])}:5432 / app_main</span><span>PostgreSQL 16.2</span><div class="sp"></div><span>Tx: {rng.choice(["auto", "manual"])}</span><span>UTF8</span></div>'
        body = (f'<div class="row str f1">{side}<div class="col f1">{tabs}{tb}<div class="mono fn" style="padding:8px 0;line-height:1.55;font-size:calc(var(--fs) - .5px);white-space:pre;min-height:{rng.choice([190, 230, 260])}px">{ed}</div>'
                f'{rbar}<div class="tr h">{head}</div><div class="col f1 clip">{grid}</div>{sb}</div></div>')
        ctx.ctxmenu, ctx.ctxobj = ["open", "copy", "rename", "export", "refresh", "-", "info", "-", "delete"], "the selected table"
        menus, title = ["mb.file", "mb.edit", "mb.view", "mb.data", "mb.tools", "mb.help"], f"{files[0]} — {hosts[0]}"
    else:  # devops_logs
        fr = "the filter bar"
        envs = d.take("term.envs", ENVS, 4)
        chips = ""
        for lv, col in zip(d.take("term.levels", LEVELS, 4), ["var(--err)", "var(--warn)", "var(--ac)", "var(--fg2)"]):
            on = rng.random() < 0.6
            chips += (f'<div class="term-chip{" on" if on else ""}"{ctx.reg("checkbox", "filter chip", lv, region=fr, state=on)}>'
                      f'<span class="dot" style="background:{col}"></span>{esc(lv)}</div>')
        top = (f'<div class="tb">{ctx.select("Environment", envs[0], options=envs, region=fr, above=False, w=140, refs=[f"the environment dropdown showing {envs[0]}"]) if envs else ""}'
               f'{ctx.seg(d.take("term.ranges", RANGES, 4), active=1, region=fr, noun="time range")}{ctx.search(fr, w=min(360, W // 6))}{chips}<div class="sp"></div>'
               f'{ctx.ibtns(["term.pause", "term.follow", "term.wrap", "|", "download", "share", "more"], fr, obj="these logs")}</div>')
        sr, srows = "the service list", []
        for i, h in enumerate(hosts):
            attr = ctx.reg("row", "service", h, region=sr, anchor="row")
            col = rng.choice(["var(--ok)", "var(--ok)", "var(--ok)", "var(--warn)", "var(--err)"])
            srows.append(f'<div class="li{" sel" if i == 1 else ""}"{attr}><span class="dot" style="background:{col}"></span><span class="el f1 mono sm">{esc(h)}</span><span class="fnt xs">{rng.randint(1, 40)}/s</span></div>')
        side = f'<div class="side br" style="width:{side_w}px"><div class="hd">Services ({len(hosts)})</div><div class="col f1 clip">{"".join(srows)}</div></div>'
        lines, lv_all = [], ["INFO", "INFO", "INFO", "DEBUG", "WARN", "ERROR"]
        sel = rng.randint(4, 14)
        for i in range(H // 19 + 2):
            lv = rng.choice(lv_all)
            col = {"ERROR": "var(--err)", "WARN": "var(--warn)", "DEBUG": "var(--fg2)"}.get(lv, "var(--ok)")
            msg = rng.choice(MSGS).format(h=f"{rng.getrandbits(16):04x}", n=rng.randint(2, 900))
            st = ' style="background:var(--acs)"' if i == sel else ""
            lines.append(f'<div{st}><span class="fnt">11:{20 + i * 7 // 60:02d}:{(i * 7) % 60:02d}.{rng.randint(100, 999)}</span>  '
                         f'<span style="color:{col}">[{lv}]</span>  {esc(rng.choice(hosts))}: {esc(msg)}</div>')
        dr = "the details panel"
        kv = "".join(f'<div class="row g8 py4 bb"><span class="mut" style="width:86px">{k}</span><span class="mono sm term-cut">{esc(v)}</span></div>' for k, v in [
            ("timestamp", "2026-03-12T11:21:07.412Z"), ("service", hosts[1]), ("pod", f"{hosts[1]}-7d9f8b-{rng.getrandbits(16):04x}"), ("trace id", f"{rng.getrandbits(64):016x}"),
            ("duration", f"{rng.randint(3, 900)} ms"), ("region", rng.choice(["eu-west-1", "us-east-2"]))])
        aside = (f'<div class="side bl p12 g8" style="width:{side_w + 80}px"><div class="row"><span class="b f1">Entry details</span>{ctx.ibtn("close.panel", dr, cls="s", obj="the details panel")}</div>{kv}'
                 f'<div class="mono xs bg3 rad p8" style="white-space:pre;line-height:1.5">{esc("{")}\n  "level": "warn",\n  "attempt": {rng.randint(1, 5)},\n  "upstream": "{esc(hosts[2])}",\n  "retry_in_ms": {rng.randint(50, 900)}\n{esc("}")}</div>'
                 f'<div class="row g6 wrap">{ctx.tbtn("copy", dr, cls="sm", icon=True, obj="this log entry")}{ctx.tbtn("link", dr, cls="sm", icon=True, obj="this log entry")}</div>'
                 f'<div class="sp"></div>{ctx.tbtn("term.restart", dr, cls="dng", icon=True)}</div>')
        sb = f'<div class="sbar"><span>{rng.randint(1200, 98000):,} events</span><span>{rng.randint(2, 60)} matching filters</span><div class="sp"></div><span>stream lag {rng.randint(40, 900)} ms</span>{ctx.ibtn("notif", "the status bar", cls="s")}</div>'
        body = f'{top}<div class="row str f1">{side}<div class="col f1 clip term-log{" term-dk" if dark else ""}">{"".join(lines)}</div>{aside}</div>{sb}'
        ctx.ctxmenu, ctx.ctxobj = ["open", "term.restart", "-", "copy", "link", "pin", "-", "info"], "the selected service"
        menus, title = ["mb.file", "mb.edit", "mb.view", "mb.tools", "mb.window", "mb.help"], f"Logs — {envs[0] if envs else hosts[0]}"
    return {"title": title, "body": f'<div class="col f1">{body}</div>', "menus": menus, "app": "Terminal", "css": CSS, "url": "console.example.dev"}
