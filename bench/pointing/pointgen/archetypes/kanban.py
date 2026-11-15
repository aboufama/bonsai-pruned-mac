"""Kanban and issue boards: card columns, swimlanes, a board with a card detail panel, a sprint backlog."""
from ..data import EVENTS, PROJECTS
from ..splits import pool
from ..ui import esc, CHEV_D, CHEV_R
from ..vocab import C, P

NAME = "kanban"
KIND = "either"
VARIANTS = {"columns": "train", "sprint_table": "train", "swimlanes": "dev", "board_with_detail": "test"}

C("kb.addcard", "Add card|New task|Create issue", "plus|circle-plus|square-plus", "put one more work item into {o}|start an additional work item in {o}|append an empty work item to {o}", o="this column")
C("kb.addcol", "Add column|New list|Add stage", "list-plus|between-vertical-end|grid-2x2-plus", "give the board one more vertical lane for cards|extend the board with another step in the process|put an extra lane at the right end of the board")
C("kb.members", "Members|People|Collaborators", "users|users-round|user-round-plus", "see who has access to this board|check which teammates are on this board|manage who can work on this board")
C("kb.automation", "Automation|Rules|Workflows", "zap|bot|workflow|wand", "set up actions that happen by themselves when cards move|create triggers that act on cards without me|make the board do repetitive steps for me")
C("kb.complete", "Complete sprint|Finish sprint|Close sprint", "", "end the running iteration and carry over what is left|wrap up the active iteration|declare the running iteration over")
C("kb.start", "Start sprint|Begin sprint|Kick off sprint", "", "make {o} the active iteration|get {o} under way|launch {o} for the team", o="the planned iteration")
C("kb.create", "Create ticket|New ticket|Open a ticket", "plus|circle-plus|square-plus", "file a fresh piece of work from anywhere|log a work item without picking a column first|raise a fresh piece of work for the team")
C("kb.assign", "Assign|Assign to|Change assignee", "user-plus|user-round-plus|user-check", "pick who is responsible for {o}|hand {o} to a teammate|choose the person who will do {o}", o="this card")
C("kb.due", "Due date|Deadline|Target date", "calendar|calendar-clock|calendar-days", "set when {o} has to be finished|choose the day {o} must be done by|schedule the completion day for {o}", o="this card")
C("kb.checklist", "Checklist|Subtasks|To-do list", "list-checks|list-todo|square-check-big", "break {o} into smaller steps|add steps to tick off inside {o}|track the smaller pieces of {o}", o="this card")
C("kb.archive", "Archive|Archive card|Put away", "archive|archive-x|folder-archive", "take {o} off the board without erasing it|file {o} away out of sight|retire {o} from the board but keep it", o="this card")
C("kb.watch", "Watch|Follow|Subscribe", "eye|bell-plus|bell-ring", "get notified whenever {o} changes|be told about every update to {o}|keep receiving updates about {o}", o="this card")
C("kb.insights", "Insights|Reports|Analytics|Team stats", "chart-column|chart-line|chart-pie|chart-area", "see charts about how the team is progressing|look at velocity and burndown graphs|check statistics about the work on this board")
C("kb.groupby", "Group by|Swimlanes|Lanes by", "rows-3|rows-4|layers|group|rows-2", "choose what the horizontal bands of the board stand for|split the board into bands by a field|change which field the board's bands are based on")
C("kb.status", "Status|Workflow state|Current stage", "", "move {o} to a different step of the process|change which step of the process {o} is in|mark how far along {o} is", o="the open card")
C("kb.prio", "Priority|Urgency|Importance", "", "say how pressing {o} is|rank {o} against the other work|change how soon {o} should be handled", o="the open card")
C("kb.mine", "Only my issues|Assigned to me|Just mine", "", "hide everything that belongs to somebody else|narrow the board to the work I am responsible for|see nothing but the work with my name on it")

NAV = P("kb.nav", [
    ("Roadmap", "see the long-term plan on a timeline", "map"), ("Backlog", "see everything that is not scheduled yet", "list"),
    ("Active sprints", "look at the iteration the team is working on now", "kanban"), ("Issues", "browse every ticket in the project", "circle-dot"),
    ("Components", "see how the project is divided into parts", "component"), ("Releases", "check which versions are planned or shipped", "rocket"),
    ("Project pages", "read the documents attached to this project", "file-text"), ("Code", "browse the linked repositories", "code"),
    ("Deployments", "see what has been rolled out to each environment", "cloud-upload"), ("On-call", "find out who is responsible for incidents right now", "siren"),
    ("Goals", "review the objectives the team is aiming for", "goal"), ("Teams", "see the groups of people working on the project", "users"),
    ("Archived work", "look at tickets that were put away", "archive"), ("Epics", "see the large bodies of work that tickets belong to", "milestone"),
    ("Forms", "manage the intake questionnaires that create tickets", "clipboard-list"), ("Automation rules", "edit the triggers that act on tickets", "zap"),
    ("Project settings", "change how this project is configured", "settings"), ("Time tracking", "see the hours logged against tickets", "timer"),
    ("Dependencies", "view which tickets block others", "git-fork"), ("Changelog", "read the history of what the team shipped", "scroll-text"),
    ("Dashboards", "open the charts summarizing the project", "layout-dashboard"), ("Retrospectives", "read the notes from past iteration reviews", "message-square"),
    ("Capacity", "check how much work each person can take on", "gauge"), ("Feature flags", "see which toggles gate unfinished functionality", "flag"),
    ("Incidents", "review outages and their follow-ups", "triangle-alert"),
])


def _pool(name, text):
    items = [x.strip() for x in text.replace("\n", "|").split("|") if x.strip()] if isinstance(text, str) else list(text)
    pool(name, items, "train")   # claim labels at import so ownership never depends on run order
    return items


COLS = _pool("kb.cols", """Backlog|To do|In progress|In review|Done|Blocked|Ready|QA|Shipped|Icebox|Triage|Next up|Doing|Testing|Deployed
Ideas|Planned|On hold|Design|Research|Staging|Released|Waiting|Today|This week|Later|Selected|Verify|Accepted|Needs info""")
VIEWTABS = _pool("kb.views", "Board|List|Timeline|Calendar|Table view|Gantt|Roadmap view|Summary|Workload|Files|Activity|Docs|Map|Forms view|Overview|Charts|Inbox|Cycle|Sprints|Archive")
EPICS = _pool("kb.epics", """Checkout revamp|Mobile onboarding|Billing v2|Search quality|Design system|Performance|Self-serve SSO|Data export|Partner API
Localization|Accessibility|Growth experiments|Admin console|Notifications hub|Reporting|Security hardening|Trial funnel|Offline mode|Integrations|Tech debt""")
SUBTASKS = _pool("kb.subtasks", """Write acceptance criteria|Add unit tests|Update the changelog|Get design sign-off|Check analytics events|Review copy with legal
Test on Safari|Profile slow queries|Add feature flag|Record a demo|Update API docs|Notify support team|Verify on staging|Add migration script
Check dark mode|Remove dead code|Measure bundle size|Confirm rollback plan|Translate strings|Schedule the release|Audit permissions
Add loading states|Write runbook entry|Backfill old records|Collect beta feedback""")
PRIOS = _pool("kb.prios", "Urgent|High|Medium|Low|Critical|Major|Minor|Trivial|P0|P1|P2|P3|Blocker|Normal|Someday")
GROUPS = _pool("kb.groups", "Assignee|Epic|Priority|Team|Label|Reporter|Component|Release|Issue type|Due week|Project|Customer|Status category|Sprint|Size")
TAGS = ["bug", "feature", "design", "backend", "frontend", "infra", "copy", "research", "ops", "mobile"]

CSS = """
.kb-board{padding:12px;gap:12px;align-items:flex-start}
.kb-col{width:var(--kw,280px);flex:none;background:var(--bg1);border-radius:max(6px,var(--r2));padding:8px;display:flex;flex-direction:column;gap:8px;border:1px solid var(--bd)}
.kb-card{background:var(--bg);border:1px solid var(--bd);border-radius:max(4px,var(--r));padding:8px 10px;display:flex;flex-direction:column;gap:6px;box-shadow:0 1px 2px var(--sh)}
.kb-card.sel{border-color:var(--ac);box-shadow:0 0 0 2px var(--acs2)}
.kb-tag{height:6px;width:34px;border-radius:3px;flex:none}.kb-chip{font-size:.78em;padding:0 6px;border-radius:3px;line-height:1.5;color:#fff;white-space:nowrap}
.kb-lane{background:var(--bg2);border-top:1px solid var(--bd);border-bottom:1px solid var(--bd)}
.kb-cell{width:var(--kw,240px);flex:none;padding:6px;display:flex;flex-direction:column;gap:6px;border-right:1px solid var(--bd);min-height:64px}
.kb-nb.tabs{border-bottom:none;flex:0 1 auto;min-width:0;overflow:hidden}
.kb-cut{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
"""


def _card(ctx, title, key, region, compact=False, sel=False, people=None):
    rng, d = ctx.rng, ctx.d
    attr = ctx.reg("row", "card", title, region=region, anchor="row")
    who = ctx.av(rng.choice(people), 20) if people else ""
    if compact:
        return (f'<div class="kb-card{" sel" if sel else ""}"{attr} style="padding:5px 8px;gap:3px"><span class="sm">{esc(title)}</span>'
                f'<div class="row g6 xs fnt"><span class="mono">{key}</span><div class="sp"></div>{who}</div></div>')
    tags = "".join(f'<span class="kb-chip" style="background:{d.color()}">{t}</span>' for t in rng.sample(TAGS, rng.randint(0, 2)))
    meta = [f'{ctx.deco("calendar", "calendar-days", "clock", size=12)}<span>{d.date()}</span>'] if rng.random() < 0.6 else []
    if rng.random() < 0.5:
        meta.append(f'{ctx.deco("message-square", "message-circle", "messages-square", size=12)}<span>{rng.randint(1, 14)}</span>')
    if rng.random() < 0.35:
        meta.append(f'{ctx.deco("paperclip", "link", "file", size=12)}<span>{rng.randint(1, 5)}</span>')
    if rng.random() < 0.3:
        meta.append(f'{ctx.deco("list-checks", "square-check", "check-check", size=12)}<span>{rng.randint(0, 4)}/{rng.randint(4, 8)}</span>')
    tagrow = f'<div class="row g4 wrap">{tags}</div>' if tags else ""
    metas = "".join(f'<span class="row g2">{m}</span>' for m in meta)
    return (f'<div class="kb-card{" sel" if sel else ""}"{attr}>{tagrow}<span>{esc(title)}</span>'
            f'<div class="row g8 xs mut"><span class="mono fnt">{key}</span>{metas}<div class="sp"></div>{who}</div></div>')


def _avatar(ctx, who, region, size=28):
    """The signed-in user's avatar; a target (and anchor for the account menu) when the split names it."""
    if not ctx.has("account"):
        return ctx.av(who, size)
    attr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=region, anchor="account")
    return f"<span{attr}>{ctx.av(who, size)}</span>"


def _sel(ctx, cid, value, options, region):
    return ctx.select(ctx.lab(cid), value, options=options, region=region, cid=cid) if ctx.has(cid) else ""


def _topbar(ctx, proj, me, region="the board header", tabs=True):
    d, rng = ctx.d, ctx.rng
    vt = ctx.tabs(d.take("kb.views", VIEWTABS, rng.randint(3, 5)), active=0, region=region, cls="kb-nb pl") if tabs else ""
    faces = "".join(f'<span style="margin-left:-6px">{ctx.av(p, 24)}</span>' for p in d.people(4)[1:])
    return (f'<div class="row g8 px12 bb fn" style="height:48px"><div class="thumb" style="width:24px;height:24px;border-radius:6px;--c1:var(--ac);--c2:var(--acs2)"></div>'
            f'<span class="b lg nw">{esc(proj)}</span>{ctx.ibtn("fav", region, cls="s", obj="this board")}{vt}<div class="sp"></div><div class="row" style="padding-left:6px">{faces}</div>'
            f'{ctx.tbtn("share", region, cls="sm", icon=True, obj="this board")}<div class="vsep"></div>{ctx.search(region, w=180, cls="soft")}'
            f'{ctx.ibtns(["filter", "sort", "kb.automation", "kb.insights", "notif"], region, obj="the cards")}{ctx.ibtn("more", region, anchor="more", obj="this board")}{_avatar(ctx, me, region)}</div>')


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    proj = d.one("projects", PROJECTS)
    pre = proj[:3].upper()
    people = d.people(7)
    me = people[0]
    verbs = ["Follow up on", "Close out", "Scope", "Estimate", "Demo", "Sync on", "Unblock", "Verify"] * 6
    titles = (d.tasks(60) + [f"{v} {o.lower()}" for v, o in zip(verbs, d.take("events", EVENTS))]
              + [f"Review {x.lower()}" for x in d.files("doc", 40, ext=False)] + [f"Restock {x}" for x in d.products(40)])
    rng.shuffle(titles)
    keys = iter([f"{pre}-{n}" for n in rng.sample(range(101, 990), 200)])
    cols = d.take("kb.cols", COLS)
    ctx.ctxmenu = ["open", "edit", "-", "kb.assign", "kb.due", "tagit", "kb.checklist", "-", "move", "duplicate", "link", "kb.watch", "-", "kb.archive", "delete"]
    ctx.ctxobj = "this card"
    menus = ["mb.file", "mb.edit", "mb.view", "mb.window", "mb.help"]
    title_i = iter(titles)

    def cards(n, region, **kw):
        out = []
        for _ in range(n):
            t = next(title_i, None)
            if t:
                out.append(_card(ctx, t, next(keys), region, people=people, **kw))
        return "".join(out)

    if variant == "columns":
        kw = rng.choice([264, 280, 300])
        ncol = min(len(cols), max(3, (W - 24) // (kw + 12)))
        chtml = []
        for name in cols[:ncol]:
            row = f"the {name} column"
            hattr = ctx.reg("row", "column", name, region="the board", refs=[f"the header of the {name} column", f"the {name} column title"])
            n = rng.randint(2, max(3, H // 150))
            chtml.append(f'<div class="kb-col"><div class="row g6"><span class="b"{hattr}>{esc(name)}</span><span class="fnt sm">{n}</span><div class="sp"></div>'
                         f'{ctx.ibtn("more", "the board", row=row, cls="s", anchor="more")}</div>{cards(n, "the board")}'
                         f'{ctx.tbtn("kb.addcard", "the board", cls="ghost sm", icon=True, row=row)}</div>')
        body = (f'{_topbar(ctx, proj, me)}<div class="row f1 clip kb-board" style="--kw:{kw}px">{"".join(chtml)}'
                f'{ctx.tbtn("kb.addcol", "the board", cls="ghost", icon=True)}</div>')
    elif variant == "swimlanes":
        rr = "the icon rail"
        rail = f'<div class="rail br">{ctx.ibtns(["home", "search", "notif", "kb.insights", "kb.members"], rr)}<div class="sp"></div>{ctx.ibtns(["help", "settings", "account"], rr)}</div>'
        kw = rng.choice([220, 240, 260])
        ncol = min(len(cols), max(3, (W - 70) // kw))
        groups = d.take("kb.groups", GROUPS, 4)
        tr = "the toolbar"
        gb = ctx.select(ctx.lab("kb.groupby"), groups[0], options=groups, region=tr, cid="kb.groupby", above=False, w=130) if ctx.has("kb.groupby") and groups else ""
        tb = (f'<div class="tb"><span class="b lg nw">{esc(proj)}</span><div class="vsep"></div>{ctx.own(ctx.lab("kb.groupby") + ":", "mut sm") if gb else ""}{gb}{ctx.search(tr, w=200)}'
              f'{ctx.check(ctx.lab("kb.mine"), rng.random() < 0.4, region=tr, cid="kb.mine") if ctx.has("kb.mine") else ""}<div class="sp"></div>'
              f'{ctx.tbtn("filter", tr, icon=True)}{ctx.tbtn("kb.create", tr, cls="pri", icon=True)}{ctx.ibtn("more", tr, anchor="more", obj="this board")}</div>')
        heads = "".join(f'<div class="row g6 px8 br" style="width:{kw}px;height:30px;flex:none"><span class="b sm up"{ctx.reg("row", "column", c, region="the column headers", refs=[f"the {c} column header", f"the heading of the {c} column"])}>{esc(c)}</span>'
                        f'<span class="fnt xs">{rng.randint(1, 6)}/{rng.randint(4, 8)}</span><div class="sp"></div>{ctx.ibtn("kb.addcard", "the column headers", row=f"the {c} column", cls="s")}</div>' for c in cols[:ncol])
        lanes = []
        for who in people[1:1 + max(2, H // 230)]:
            lane = who + "'s lane"
            cells = "".join('<div class="kb-cell">' + cards(rng.randint(0, 3), "the board", compact=True) + "</div>" for _ in range(ncol))
            lattr = ctx.reg("row", "swimlane", who, region="the board", refs=[f"the swimlane header for {who}", f"the lane heading that says {who}"])
            lanes.append(f'<div class="row g6 px8 kb-lane fn" style="height:28px"><span class="mut">{CHEV_D}</span><span class="row g6"{lattr}>{ctx.av(who, 18)}<span class="m sm">{esc(who)}</span></span>'
                         f'<span class="fnt xs">{rng.randint(2, 9)} issues</span><div class="sp"></div>{ctx.ibtn("collapse", "the board", row=lane, obj=lane, cls="s")}</div>'
                         f'<div class="row str fn">{cells}</div>')
        body = f'<div class="row str f1">{rail}<div class="col f1">{tb}<div class="row bb bg1 fn">{heads}</div><div class="col f1 clip" style="--kw:{kw}px">{"".join(lanes)}</div></div></div>'
    elif variant == "board_with_detail":
        pw = min(520, max(380, W // 4))
        kw = rng.choice([230, 250])
        ncol = min(len(cols), max(2, (W - pw - 24) // (kw + 12)))
        chtml, sel_title, sel_tid = [], None, None
        for ci, name in enumerate(cols[:ncol]):
            hattr = ctx.reg("row", "column", name, region="the board", refs=[f"the header of the {name} column", f"the {name} column title"])
            inner = ""
            for k in range(rng.randint(3, max(4, H // 90))):
                t = next(title_i, None)
                if not t:
                    break
                is_sel = ci == 0 and k == 1
                inner += _card(ctx, t, next(keys), "the board", compact=True, sel=is_sel, people=people)
                if is_sel:
                    sel_title, sel_tid = t, ctx.last
            chtml.append(f'<div class="kb-col"><div class="row g6"><span class="b"{hattr}>{esc(name)}</span><div class="sp"></div>{ctx.ibtn("kb.addcard", "the board", row=f"the {name} column", cls="s")}</div>{inner}</div>')
        pr = "the card detail panel"
        obj = "the open card"
        head = (f'<div class="row g4 fn"><span class="mono fnt sm">{next(keys)}</span><div class="sp"></div>{ctx.ibtns(["kb.watch", "link", "attach", "kb.archive"], pr, cls="s", obj=obj)}'
                f'{ctx.ibtn("more", pr, cls="s", anchor="more", obj=obj)}{ctx.ibtn("close.panel", pr, cls="s", obj="the card details")}</div>')
        prios = d.take("kb.prios", PRIOS, 4)
        fields = (f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 12px">{_sel(ctx, "kb.status", cols[0], cols[:ncol + 2], pr)}'
                  f'{_sel(ctx, "kb.assign", people[2], people[:5], pr)}{_sel(ctx, "kb.prio", prios[0] if prios else "—", prios, pr)}'
                  f'{ctx.field(ctx.lab("kb.due"), d.date(True), region=pr, cid="kb.due") if ctx.has("kb.due") else ""}</div>')
        subs = d.take("kb.subtasks", SUBTASKS, rng.randint(4, 6))
        done = rng.randint(1, len(subs) - 1)
        checks = "".join(f'<div class="li fn" style="padding:0">{ctx.check(s, i < done, region="the checklist")}</div>' for i, s in enumerate(subs))
        comments = "".join(f'<div class="row top g8">{ctx.av(p, 26)}<div class="col g2 f1"><div class="row g6"><span class="m">{esc(p)}</span><span class="fnt xs">{d.date()}</span></div><span class="sm mut">{esc(d.sentence())}</span></div></div>'
                           for p in people[3:5])
        reply = (f'<div class="row g8">{ctx.av(me, 26)}<div class="f1">{ctx.field("Write a comment", "", region=pr, above=False)}</div>{ctx.tbtn("send", pr, cls="pri sm", obj="my comment")}</div>')
        panel = (f'<div class="side bl p16 g12" style="width:{pw}px;background:var(--bg)">{head}<span class="xl b" data-o="{sel_tid}">{esc(sel_title)}</span>{fields}'
                 f'<div class="col g4"><span class="b sm">Description</span>{ctx.lines(3)}</div>'
                 f'<div class="col g6"><div class="row g8"><span class="b sm">Steps</span><div class="prog f1"><div style="width:{100 * done // len(subs)}%"></div></div><span class="fnt xs">{done}/{len(subs)}</span></div>{checks}</div>'
                 f'<div class="col g10 f1 clip"><span class="b sm">Discussion</span>{comments}</div>{reply}</div>')
        body = f'{_topbar(ctx, proj, me, tabs=W > 1500)}<div class="row str f1"><div class="row f1 clip kb-board" style="--kw:{kw}px">{"".join(chtml)}</div>{panel}</div>'
    else:  # sprint_table
        tr = "the top bar"
        top = (f'<div class="row g8 px12 bb bg2 fn" style="height:46px">{ctx.ibtn("apps", tr)}<span class="b lg">{esc(proj)}</span><div class="sp"></div>{ctx.search(tr, w=min(420, W // 4), cls="soft")}<div class="sp"></div>'
               f'{ctx.tbtn("kb.create", tr, cls="pri", icon=True)}{ctx.ibtns(["notif", "help", "settings"], tr)}{_avatar(ctx, me, tr)}</div>')
        sr = "the sidebar"
        nav = "".join(ctx.navc(c, sr, on=i == 1, noun="page") for i, c in enumerate(ctx.pick(NAV, H // 60)))
        side = f'<div class="side br" style="width:{rng.choice([210, 230, 250])}px"><div class="hd">{esc(pre)} project</div><div class="col g2 f1 clip">{nav}</div><div class="p8 bt">{ctx.tbtn("kb.members", sr, cls="ghost sm", icon=True)}</div></div>'
        fr = "the filter bar"
        epics = d.take("kb.epics", EPICS, 6)
        faces = "".join('<span style="margin-left:-5px">' + ctx.av(p, 24) + "</span>" for p in people[:5])
        fb = (f'<div class="row g8 px16 fn" style="height:44px">{ctx.field("Filter issues", "", region=fr, above=False, w=200)}<div class="row" style="padding-left:5px">{faces}</div>'
              f'{ctx.select("Epic", "All epics", options=epics, region=fr, above=False, w=130, refs=["the epic filter dropdown", "the dropdown that says All epics"])}'
              f'{ctx.check(ctx.lab("kb.mine"), False, region=fr, cid="kb.mine") if ctx.has("kb.mine") else ""}<div class="sp"></div>{ctx.ibtns(["kb.insights", "sort", "more"], fr, obj="the backlog")}</div>')
        secs, sn = [], rng.randint(12, 60)
        for si in range(max(2, H // 300)):
            sname = f"Sprint {sn + si}"
            sattr = ctx.reg("row", "sprint section", sname, region="the backlog", refs=[f"the {sname} section header", f"the heading that says {sname}"])
            btn = ctx.tbtn("kb.complete", "the backlog", cls="sm") if si == 0 else ctx.tbtn("kb.start", "the backlog", cls="sm", row=sname, obj=sname)
            rows = []
            for k in range(rng.randint(4, 8)):
                t = next(title_i, None)
                if not t:
                    break
                attr = ctx.reg("row", "issue", t, region="the backlog", anchor="row")
                st = rng.choice([("To do", ""), ("In progress", "a"), ("In review", "y"), ("Done", "g")])
                more = ctx.ibtn("more", "the backlog", row=t, cls="s", anchor="more") if k % 3 == 0 else ""
                rows.append(f'<div class="tr px8">{ctx.deco("square-check", "bookmark", "circle-dot", "bug", "zap", blank=True)}<span class="mono fnt sm" style="width:74px;padding-left:8px">{next(keys)}</span>'
                            f'<span class="el f1"{attr}>{esc(t)}</span><span class="pill" style="margin:0 8px">{esc(rng.choice(epics)) if epics else "epic"}</span>'
                            f'<span class="pill {st[1]}" style="width:86px;justify-content:center">{st[0]}</span><span class="bdg" style="margin:0 10px;background:var(--bg4);color:var(--fg1)">{rng.choice([1, 2, 3, 5, 8])}</span>'
                            f'{ctx.av(rng.choice(people), 22)}<span style="width:calc(var(--ibs) - 2px);display:flex;margin-left:6px">{more}</span></div>')
            secs.append(f'<div class="col card fn" style="margin:0 16px 12px"><div class="row g8 px12 bg1 bb" style="height:38px"><span class="mut">{CHEV_D}</span><span class="b"{sattr}>{sname}</span>'
                        f'<span class="fnt sm">{d.date()} – {d.date()} · {len(rows)} issues</span><div class="sp"></div><span class="pill">{rng.randint(0, 9)}</span><span class="pill a">{rng.randint(0, 9)}</span><span class="pill g">{rng.randint(0, 9)}</span>'
                        f'{btn}{ctx.ibtn("more", "the backlog", row=sname, cls="s", anchor="more")}</div>{"".join(rows)}</div>')
        body = f'{top}<div class="row str f1">{side}<div class="col f1 clip">{fb}{"".join(secs)}</div></div>'
    return {"title": f"{proj} — {rng.choice(['Board', 'Tracker', 'Planner'])}", "body": f'<div class="col f1">{body}</div>', "menus": menus, "app": "Tracker", "css": CSS,
            "url": "tracker.example.com/" + proj.lower() + "/board"}
