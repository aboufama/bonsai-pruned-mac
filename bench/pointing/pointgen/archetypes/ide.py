"""Code editors and IDEs: activity rail, file tree, tabs, code, tool panels, status bar."""
import re

from ..data import BRANCHES, PROJECTS, SHELL
from ..splits import pool
from ..ui import esc, CHEV_D, CHEV_R
from ..vocab import C, P

NAME = "ide"
KIND = "desktop"
VARIANTS = {"vscode": "train", "jetbrains": "train", "sublime": "train", "split_diff": "dev", "notebook": "test"}

C("ide.explorer", "Explorer|File tree|Project files", "files|folder-tree|folders", "browse the folders of this codebase|see the directory structure of the workspace|look through what the repository contains")
C("ide.findall", "Find in files|Search everywhere|Global search", "search-code|file-search-2|folder-search-2", "look for a string across the whole codebase|hunt for a piece of text in every document of the workspace|locate every occurrence of a word in the repository")
C("ide.scm", "Source control|Version control|Pending changes", "git-branch|git-fork|git-compare", "review what I have modified since the last commit|see my uncommitted edits|check which documents differ from the repository")
C("ide.debug", "Run and debug|Debugger|Debugging", "bug-play|bug|bug-off", "step through the program with breakpoints|inspect variables while the program is paused|investigate a crash one statement at a time")
C("ide.ext", "Marketplace|Plugin store|Add-on gallery", "blocks|puzzle|package-plus", "install extra language support for the editor|browse installable packages that extend the editor|get new editor capabilities from third parties")
C("ide.run", "Run file|Start program|Execute script", "play|circle-play|square-play", "launch the code I am working on|see what the current code does when it is launched|kick off the application", n="run|start|execute")
C("ide.stop", "Stop|Terminate|Halt", "square|circle-stop|octagon-x", "kill the process that is currently executing|end the program I launched|abort the active execution")
C("ide.build", "Build|Compile|Make project", "hammer|wrench|package", "turn the sources into a binary|produce the executable output|assemble everything into a runnable artifact")
C("ide.commit", "Commit|Check in|Record changes", "check|git-commit-horizontal|git-commit-vertical", "snapshot my staged work into the repository history|store the staged edits as a new revision|write the staged edits into the history")
C("ide.push", "Push|Publish branch|Upload commits", "arrow-up-from-line|cloud-upload|upload", "send my local revisions to the remote repository|hand my new revisions over to the server|get my local history onto the remote")
C("ide.pull", "Pull|Fetch latest|Update project", "arrow-down-to-line|cloud-download|download", "bring my teammates' newest revisions onto my machine|get the newest remote revisions into my working copy|sync my working copy with what others have sent")
C("ide.stage", "Stage|Stage changes|Add to index", "plus|circle-plus|square-plus", "include {o} in the next revision|mark {o} as ready to be committed|queue {o} for the upcoming snapshot", o="the selected file")
C("ide.unstage", "Unstage|Remove from index|Unstage changes", "minus|circle-minus|square-minus", "take {o} out of the upcoming snapshot|leave {o} out of the next revision after all|pull {o} back from what is about to be committed", o="the selected file")
C("ide.discard", "Discard|Revert file|Undo changes", "undo-2|undo|rotate-ccw", "throw away the edits in {o}|drop my modifications to {o} and restore the committed version|put {o} back to how it is in the repository", o="the selected file")
C("ide.split", "Split editor|Split right|Side by side", "columns-2|square-split-horizontal|panel-right-dashed", "show two documents next to each other|divide the editing area into two columns|view a second document alongside this one")
C("ide.inline", "Inline view|Unified diff|Single column", "rows-2|align-justify|square-split-vertical", "show removed and added lines interleaved in one pane|merge the before and after panes into one|read the comparison as one continuous listing")
C("ide.prevdiff", "Previous change|Previous difference|Earlier hunk", "arrow-up|chevron-up|circle-arrow-up|move-up", "jump to the modified block above this one|go back to the modification before this one|move to the preceding edited block")
C("ide.nextdiff", "Next change|Next difference|Later hunk", "arrow-down|chevron-down|circle-arrow-down", "jump to the modified block below this one|go on to the modification after this one|move to the following edited block")
C("ide.newfile", "New file|Create file|Add file", "file-plus-2|file-pen|file-pen-line", "make an empty document in the tree|start a blank document in the workspace|put an empty document into the codebase")
C("ide.newfolder", "New folder|Create folder|Add directory", "folder-plus|folder-root|folder-open-dot", "make an empty container for documents in the tree|start an empty grouping level in the workspace tree|put one more level into the hierarchy")
C("ide.collapseall", "Collapse all|Fold all|Collapse folders", "list-collapse|copy-minus|square-minus", "close every expanded branch of the tree|shut the opened levels of the hierarchy at once|tidy the tree so only the top level shows")
C("ide.panel", "Toggle panel|Hide bottom panel|Collapse terminal area", "panel-bottom|panel-bottom-close|panel-bottom-open", "get the lower output area out of the way|put away the pane under the code|reclaim the space used by the lower pane", n="panel toggle|hide bottom panel|bottom panel")
C("ide.case", "Match case|Case sensitive|Respect capitalization", "case-sensitive|a-large-small|case-upper", "make the lookup tell capital letters from small ones|treat upper and lower letters as different when looking|only find hits with identical letter casing")
C("ide.word", "Whole word|Entire words only|Match full words", "whole-word|text-cursor|space", "skip hits that are just part of a longer identifier|only find the term when it stands alone|ignore hits inside longer identifiers")
C("ide.regex", "Use regex|Regular expression|Pattern mode", "regex|asterisk|code", "interpret what I type as a wildcard formula|allow wildcards and character classes in the lookup|look things up with a matching formula rather than literal text")
C("ide.findnext", "Find next|Next match|Next occurrence", "arrow-down|chevron-down|circle-arrow-down", "jump to the following hit in the document|go to the hit after this one|move on to where the term appears again")
C("ide.findprev", "Find previous|Previous match|Earlier occurrence", "arrow-up|chevron-up|circle-arrow-up|move-up", "jump to the hit before this one|go back to the preceding hit|return to where the term appeared last")
C("ide.replace1", "Replace next|Swap this match|Substitute one", "replace|arrow-right-left|repeat-1", "exchange only the highlighted hit for the new text|put the new text in place of just this hit|change this single hit to the new text")
C("ide.replaceall", "Replace all|Swap every match|Substitute everywhere", "replace-all|repeat|repeat-2", "exchange each hit in the document for the new text at once|change all hits to the new text in one go|put the new text in place of all hits together")
C("ide.addcell", "Add cell|Insert cell|New block", "plus|circle-plus|square-plus", "put an empty code box below the current one|get a blank code box to type into|append one more code box to the notebook")
C("ide.runcell", "Run cell|Execute cell|Run this block", "play|circle-play|square-play", "evaluate the code in {o}|compute the output of {o}|have the kernel process {o}", o="the current cell")
C("ide.runall", "Run all|Execute everything|Run whole notebook", "fast-forward|chevrons-right|list-video", "evaluate each code box from top to bottom|recompute the entire document in order|have the kernel process the code boxes one after another")
C("ide.restart", "Restart kernel|Reboot kernel|Reset interpreter", "refresh-ccw-dot|rotate-ccw-square|power", "clear the variables and begin with a clean process|wipe the in-memory state of the session|bring the computation engine back to a clean state")
C("ide.cellup", "Move up|Move cell up|Shift up", "arrow-up|chevron-up|circle-arrow-up|move-up", "place {o} above the one before it|swap {o} with the one over it|raise {o} by one position", o="the current cell")
C("ide.celldown", "Move down|Move cell down|Shift down", "arrow-down|chevron-down|circle-arrow-down", "place {o} under the one after it|swap {o} with the one beneath it|lower {o} by one position", o="the current cell")

TOOLWIN = P("ide.tw", [
    ("Problems", "see the list of errors and warnings in my code", "triangle-alert"), ("Output", "read what the build tasks printed", "scroll-text"),
    ("Terminal", "type shell commands without leaving the editor", "square-terminal"), ("Debug Console", "evaluate expressions while the program is paused", "bug"),
    ("Ports", "see which local network sockets are forwarded", "ethernet-port"), ("Test Results", "check which automated checks passed or failed", "flask-conical"),
    ("Git Log", "scroll through past revisions of the repository", "git-graph"), ("TODO", "list the reminder comments left in the code", "list-todo"),
    ("Services", "manage the running containers and servers", "server"), ("Coverage", "see which lines the automated checks exercise", "shield-check"),
    ("Profiler", "measure where the program spends its time", "gauge"), ("Dependencies", "review the third-party packages the code relies on", "package"),
    ("Database", "browse the tables my application talks to", "database"), ("Structure", "see an outline of the classes and functions in this document", "list-tree"),
    ("Bookmarks", "return to lines I marked earlier", "bookmark"), ("Find Results", "revisit the hits from my last lookup", "text-search"),
    ("Call Hierarchy", "see which functions invoke the one under the cursor", "network"), ("Pull Requests", "review proposed merges from my teammates", "git-pull-request"),
    ("AI Assistant", "ask a chatbot about this code", "bot"), ("Endpoints", "list the HTTP routes the application exposes", "globe"),
    ("Timeline", "see how this document evolved revision by revision", "history"), ("Outline", "jump between the symbols defined in this document", "list"),
    ("Run Log", "read what my program printed the last time it was launched", "file-text"), ("Containers", "inspect the images and volumes on this machine", "container"),
    ("Notebook Variables", "inspect the values currently held in memory", "variable"), ("Search Index", "check the progress of symbol indexing", "radar"),
    ("Python Packages", "install or upgrade libraries for the interpreter", "boxes"), ("Merge Conflicts", "resolve places where two revisions collide", "git-merge"),
    ("Local History", "restore an earlier state the editor remembered on its own", "archive-restore"), ("Build Queue", "watch the compile jobs waiting to start", "list-ordered"),
])
GO_ITEMS = P("ide.go", [
    ("Go to line", "jump to a specific row number in this document"), ("Go to symbol", "jump to a function or class by typing its name"),
    ("Go to definition", "see where the identifier under the cursor is declared"), ("Find references", "list every place that uses the identifier under the cursor"),
    ("Next problem", "jump to the following error in this document"), ("Previous problem", "jump to the error before this one"),
    ("Last edit location", "return to the spot where I last typed"), ("Go to bracket", "jump to the matching parenthesis"),
    ("Switch editor group", "move focus to the other half of the editing area"), ("Go to test", "open the automated check that covers this function"),
    ("Recent files", "pick from the documents I had open lately"), ("Go to implementation", "see the concrete code behind this interface"),
    ("Peek definition", "preview a declaration in a small inline box"), ("Go to type", "see the declaration of this value's class"),
    ("Navigate back", "return to where the cursor was before the last jump"),
])
RUN_ITEMS = P("ide.rm", [
    ("Toggle breakpoint", "mark this line so execution pauses on it"), ("Step over", "advance one statement without entering calls"),
    ("Step into", "follow execution inside the function being called"), ("Step out", "finish the current function and pause in its caller"),
    ("Restart session", "begin the debugging run again from the top"), ("Run with coverage", "launch the code while recording which lines execute"),
    ("Edit configurations", "change the arguments and environment used at launch"), ("Attach to process", "hook the debugger onto something already running"),
    ("Run to cursor", "continue execution until it reaches the line I am on"), ("Evaluate expression", "compute a value while the program is paused"),
    ("Add watch", "keep an eye on a variable's value as I step"), ("Clear all breakpoints", "remove every pause marker in the workspace"),
    ("Rerun failed tests", "repeat only the automated checks that did not pass"), ("Profile program", "launch the code while timing every function"),
    ("Open launch file", "see the JSON that defines how the program is launched"),
])


def _pool(name, text):
    items = [x.strip() for x in text.replace("\n", "|").split("|") if x.strip()] if isinstance(text, str) else list(text)
    pool(name, items, "train")   # claim the labels at import time so ownership never depends on run order
    return items


DIRS = _pool("ide.dirs", """src|tests|docs|scripts|public|config|lib|assets|components|api|utils|models|views|migrations|static
templates|cmd|internal|pkg|build|dist|vendor|hooks|styles|services|store|types|bin|tools|examples|benchmarks|locales|fixtures
middleware|routes|controllers|schemas|workers|plugins|layouts|pages|core|common|infra|deploy|proto|generated|e2e|mocks|notebooks""")
LANGS = _pool("ide.langs", [("Python", "py"), ("TypeScript", "ts"), ("Go", "go"), ("Rust", "rs"), ("Ruby", "rb")])
ENCODINGS = _pool("ide.enc", "UTF-8|UTF-16 LE|ISO-8859-1|Windows-1252|ASCII|UTF-8 with BOM|Shift JIS|GB18030|KOI8-R|UTF-32 BE")
INDENTS = _pool("ide.indent", "Spaces: 4|Spaces: 2|Tab Size: 4|Tab Size: 8|Tabs: 2|Spaces: 8|Tab Size: 2|Indent: 4|Indent: 2|Tabs: 4")
EOLS = _pool("ide.eol", "LF|CRLF|Unix (LF)|Windows (CRLF)|Mac (CR)|CR|LF only|Auto EOL|CRLF only|Mixed EOL")
SECTIONS = _pool("ide.secs", "OUTLINE|TIMELINE|OPEN EDITORS|NPM SCRIPTS|DEPENDENCIES|TEST EXPLORER|BREAKPOINTS|WATCH|CALL STACK|REMOTES|STASHES|TAGS|WORKTREES|SNIPPETS|TASKS")
CELL_TYPES = _pool("ide.celltypes", "Code|Markdown|Raw|Heading|SQL|Prompt|Shell|Rich text|Chart|Note")
CONFIGS = _pool("ide.configs", "dev server|unit tests|main|lint|docker compose|migrate|seed db|e2e tests|benchmark|release build|worker|storybook|typecheck|docs|api (debug)")
_pool("branches", BRANCHES)

SNIP = {
    "py": """import os
import json
from dataclasses import dataclass, field

DEFAULT_PORT = 8080

@dataclass
class Config:
    host: str = "localhost"
    port: int = DEFAULT_PORT
    debug: bool = False
    tags: list = field(default_factory=list)

def load(path):
    # read the settings file, falling back to defaults
    with open(path) as f:
        raw = json.load(f)
    return Config(**raw)

def serve(cfg):
    app = create_app(cfg)
    app.router.add("/health", health)
    for name, handler in ROUTES.items():
        app.router.add(name, handler)
    log.info("listening on %s:%d", cfg.host, cfg.port)
    app.run(host=cfg.host, port=cfg.port)

if __name__ == "__main__":
    cfg = load(os.environ.get("APP_CONFIG", "config.json"))
    serve(cfg)
""",
    "ts": """import { Router } from "./router";
import type { Session, User } from "./types";

const MAX_RETRIES = 3;

export async function fetchUser(id: string): Promise<User> {
  const res = await fetch(`/api/users/${id}`);
  if (!res.ok) {
    throw new Error(`request failed: ${res.status}`);
  }
  return res.json();
}

// keeps the session in sync with the auth provider
export function useSession(): Session | null {
  const [session, setSession] = useState<Session | null>(null);
  useEffect(() => {
    const sub = auth.onChange(setSession);
    return () => sub.unsubscribe();
  }, []);
  return session;
}

export const router = new Router({
  base: "/app",
  routes: [home, settings, billing],
  retries: MAX_RETRIES,
});
""",
    "go": """package main

import (
	"context"
	"log"
	"net/http"
	"time"
)

type Server struct {
	addr    string
	timeout time.Duration
	mux     *http.ServeMux
}

// NewServer wires the default routes.
func NewServer(addr string) *Server {
	s := &Server{addr: addr, timeout: 5 * time.Second}
	s.mux = http.NewServeMux()
	s.mux.HandleFunc("/healthz", s.health)
	return s
}

func (s *Server) Run(ctx context.Context) error {
	srv := &http.Server{Addr: s.addr, Handler: s.mux}
	go func() {
		<-ctx.Done()
		srv.Shutdown(context.Background())
	}()
	log.Printf("listening on %s", s.addr)
	return srv.ListenAndServe()
}
""",
    "rs": """use std::collections::HashMap;
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
    pub timeout: Duration,
}

impl Config {
    // builds a config from environment variables
    pub fn from_env() -> Result<Self, ConfigError> {
        let host = std::env::var("APP_HOST").unwrap_or("127.0.0.1".into());
        let port = std::env::var("APP_PORT")?.parse::<u16>()?;
        Ok(Self { host, port, timeout: Duration::from_secs(5) })
    }
}

pub async fn serve(cfg: Config, routes: HashMap<String, Handler>) -> Result<(), Error> {
    let listener = TcpListener::bind((cfg.host.as_str(), cfg.port)).await?;
    tracing::info!("listening on {}:{}", cfg.host, cfg.port);
    loop {
        let (stream, peer) = listener.accept().await?;
        let routes = routes.clone();
        tokio::spawn(async move { handle(stream, peer, routes).await });
    }
}
""",
    "rb": """require "json"
require "logger"

class Config
  attr_reader :host, :port, :debug

  def initialize(host: "localhost", port: 8080, debug: false)
    @host = host
    @port = port
    @debug = debug
  end

  # loads settings from a JSON file
  def self.load(path)
    raw = JSON.parse(File.read(path), symbolize_names: true)
    new(**raw)
  end
end

class Server
  def initialize(config)
    @config = config
    @log = Logger.new($stdout)
  end

  def run
    @log.info("listening on #{@config.host}:#{@config.port}")
    ROUTES.each { |name, handler| mount(name, handler) }
    start(@config.host, @config.port)
  end
end
""",
}
SNIP = {k: v.rstrip("\n").split("\n") for k, v in SNIP.items()}
_KW = (r"\b(import|from|def|class|return|if|else|elif|for|in|with|as|not|and|or|None|True|False|const|let|export|async|await|function|"
       r"type|new|throw|package|func|go|struct|var|range|use|pub|fn|impl|loop|move|require|end|do|self|nil|true|false)\b")
_TOKEN = re.compile(r'(#.*$|//.*$)|("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`[^`]*`)|' + _KW + r"|\b(\d+(?:\.\d+)?)\b|([A-Za-z_]\w*)(?=\()")

CSS = """
.ide-code{font-family:var(--mono);font-size:calc(var(--fs) - .5px);line-height:1.55;white-space:pre;tab-size:4;padding-top:4px}
.ide-ln{display:flex}.ide-no{width:46px;text-align:right;padding-right:14px;color:var(--fg2);flex:none}
.ide-cur{background:var(--bg3)}.ide-add{background:color-mix(in srgb,var(--ok) 20%,transparent)}.ide-del{background:color-mix(in srgb,var(--err) 18%,transparent)}
.ide-nb.tabs{border-bottom:none;flex:1 1 0;min-width:0;overflow:hidden}.ide-cut{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1 1 0}.ide-tr{min-height:calc(var(--rh) - 2px);gap:5px}
.ide-st{font-family:var(--mono);font-size:.85em;width:14px;text-align:center;flex:none}
.ide-term{font-family:var(--mono);font-size:calc(var(--fs) - .5px);line-height:1.5;white-space:pre;padding:6px 10px}
.ide-cell{border:1px solid var(--bd);border-radius:var(--r);background:var(--bg1)}.ide-cell.on{border-left:3px solid var(--ac)}
.sbar.acc .ib{color:inherit}.sbar .ib{height:20px}
.ide-stripe{width:calc(var(--ibs) + 8px);align-items:center;padding:6px 0;gap:4px;background:var(--bg2)}
"""


def _hl(line):
    out, pos = [], 0
    for m in _TOKEN.finditer(line):
        out.append(esc(line[pos:m.start()]))
        kind = "c" if m.group(1) else "s" if m.group(2) else "k" if m.group(3) else "n" if m.group(4) else "f"
        out.append(f'<span style="color:var(--code-{kind})">{esc(m.group(0))}</span>')
        pos = m.end()
    return "".join(out) + esc(line[pos:])


def _refs(ctx, key, options):
    """Ways to refer to an unlabeled control; each split gets its own share of the wordings."""
    return ctx.d.take("ide.ref." + key, options)


def _code(lang, n, start=1, cur=None, marks=None, offset=0, flex=True):
    src, out = SNIP[lang], []
    for i in range(n):
        cls = (" ide-" + marks[i]) if marks and i in marks else (" ide-cur" if i == cur else "")
        out.append(f'<div class="ide-ln{cls}"><span class="ide-no">{start + i}</span><span>{_hl(src[(i + offset) % len(src)])}</span></div>')
    return f'<div class="ide-code{" f1 clip" if flex else ""}">{"".join(out)}</div>'


def _minimap(lang, n):
    src, bars = SNIP[lang], []
    for i in range(n):
        line = src[i % len(src)]
        ind = len(line) - len(line.lstrip())
        bars.append(f'<div style="height:2px;margin:1px 0 1px {4 + ind * 2}px;width:{min(66, len(line.strip()) * 1.2):.0f}px;background:var(--fg2);opacity:.4"></div>')
    return (f'<div class="clip bl rel" style="width:84px;flex:none">{"".join(bars)}'
            f'<div style="position:absolute;left:0;right:0;top:0;height:96px;background:var(--fg2);opacity:.13"></div></div>')


def _tree(ctx, region, files, dirs, st=False):
    rng, rows, files = ctx.rng, [], list(files)
    fico = ctx.deco("file-code", "file-code-2", "file-code-corner", "file-braces", "file-text", "file", "file-json", blank=True)
    dico = ctx.deco("folder", "folder-closed", "folder-open", "folder-dot", "folder-code", blank=True)

    def frow(name, depth, on=False):
        attr = ctx.reg("row", "file", name, region=region, anchor="row")
        mark = rng.choice(["", "", "", "M", "U", "A"]) if st else ""
        tail = f'<span class="sp"></span><span class="ide-st {"ok" if mark == "A" else "wrn"}">{mark}</span>' if mark else ""
        return f'<div class="li ide-tr{" sel" if on else ""}" style="padding-left:{22 + depth * 14}px"{attr}>{fico}<span class="el">{esc(name)}</span>{tail}</div>'

    for i, dname in enumerate(dirs):
        open_ = i < 2 or rng.random() < 0.3
        attr = ctx.reg("row", "folder", dname, region=region, anchor="row")
        rows.append(f'<div class="li ide-tr" style="padding-left:8px"{attr}><span class="mut">{CHEV_D if open_ else CHEV_R}</span>{dico}<span class="el">{esc(dname)}</span></div>')
        if open_:
            for _ in range(rng.randint(2, 4)):
                if len(files) > 3:
                    rows.append(frow(files.pop(), 1, on=i == 0 and rng.random() < 0.4))
    rows += [frow(f, 0) for f in files]
    return "".join(rows)


def _term(n, off=0):
    lines = "".join(f'<div>{esc(SHELL[(i + off) % len(SHELL)]) or "&nbsp;"}</div>' for i in range(n))
    return f'<div class="ide-term f1 clip">{lines}</div>'


def _status(ctx, lang, acc=True):
    rng, d, region = ctx.rng, ctx.d, "the status bar"

    def item(pool_name, items, noun, tail="indicator"):
        got = d.take(pool_name, items, 1)
        if not got:
            return ""
        attr = ctx.reg("button", noun, got[0], region=region, refs=[f"the {got[0]} {tail} in the status bar", f"{got[0]} in the status bar"])
        return f'<div class="si"{attr}>{esc(got[0])}</div>'

    brs = d.take("branches", BRANCHES, 1)
    br = brs[0] if brs else "HEAD"
    battr = ctx.reg("button", "branch", br, region=region, refs=[f"the {br} branch name in the status bar", f"the branch indicator that says {br}"]) if brs else ""
    crefs = _refs(ctx, "counts", ["the error and warning counts in the status bar", "the problem counters in the status bar",
                                  "the errors and warnings indicator in the bottom bar", "the diagnostics counters in the status bar",
                                  "the issue counts at the left of the status bar"])
    cattr = ctx.reg("button", "indicator", crefs[0], ui="icon", region=region, refs=crefs)
    pos = f"Ln {rng.randint(1, 240)}, Col {rng.randint(1, 80)}"
    pattr = ctx.reg("button", "indicator", pos, region=region, refs=_refs(ctx, "pos", [
        "the cursor position indicator in the status bar", "the line and column readout in the status bar", "the Ln/Col indicator in the bottom bar",
        "the caret position readout in the status bar", "the line and column numbers in the status bar"]))
    lattr = ctx.reg("button", "language mode", lang, region=region, refs=[f"the {lang} language mode in the status bar", f"the language indicator that says {lang}"]) if lang else ""
    return (f'<div class="sbar{" acc" if acc else ""}"><div class="si"{battr}>{ctx.deco("git-branch", "git-fork", "git-merge", "git-graph")}{esc(br)}</div>'
            f'{ctx.ibtn("refresh", region, obj="this branch", cls="s")}<div class="si"{cattr}>{ctx.deco("circle-x", "octagon-x", "ban", "circle-alert")}{rng.randint(0, 4)}'
            f'{ctx.deco("triangle-alert", "octagon-alert", "badge-alert", "shield-alert")}{rng.randint(0, 12)}</div><div class="sp"></div>'
            f'<div class="si"{pattr}>{pos}</div>{item("ide.indent", INDENTS, "indicator", "indentation setting")}{item("ide.enc", ENCODINGS, "indicator", "encoding indicator")}'
            f'{item("ide.eol", EOLS, "indicator", "line ending indicator")}<div class="si"{lattr}>{esc(lang or "Plain Text")}</div>{ctx.ibtn("notif", region, cls="s")}</div>')


def _panel(ctx, tabs, h, lines):
    region = "the bottom panel"
    bar = ctx.tabs([(ctx.lab(c), c) for c in tabs], active=min(2, len(tabs) - 1), region=region, cls="ide-nb", noun="tab")
    icons_ = ctx.ibtns(["add", "ide.split", "delete", "|", "ide.panel", "close.panel"], region, cls="s", obj="the terminal")
    return (f'<div class="col bt fn" style="height:{h}px"><div class="row bb" style="padding-right:6px">{bar}{icons_}</div>'
            f'{_term(lines, ctx.rng.randint(0, 20))}</div>')


def _rail(ctx, on=0):
    region = "the activity bar"
    top = "".join(ctx.ibtn(c, region, on=i == on) for i, c in enumerate(["ide.explorer", "ide.findall", "ide.scm", "ide.debug", "ide.ext"]))
    return f'<div class="rail br">{top}<div class="sp"></div>{ctx.ibtn("account", region)}{ctx.ibtn("settings", region)}</div>'


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    langs = d.take("ide.langs", LANGS, 1)
    lang, ext = langs[0] if langs else (None, rng.choice(sorted(SNIP)))
    proj = d.one("projects", PROJECTS).lower()
    stems = d.files("code", 16, ext=False)
    files = [f"{s}.{ext if rng.random() < 0.8 else rng.choice(['json', 'yaml', 'md', 'toml'])}" for s in stems]
    dirs = d.take("ide.dirs", DIRS, rng.randint(5, 8))
    open_files = files[:rng.randint(3, min(6, 2 + W // 420))]
    n_lines = H // 17 + 2
    tw = ctx.avail(TOOLWIN, icon=True)
    rng.shuffle(tw)
    side_w = rng.choice([220, 250, 280]) + (40 if W > 2000 else 0)
    crumb = f'<div class="row px12 mut xs bb" style="height:22px;flex:none">{esc(proj)} › {esc(dirs[0])} › {esc(open_files[0])} › {esc(rng.choice(["serve", "load", "Config", "run"]))}</div>'
    ctx.menus.update({"mb.go": GO_ITEMS, "mb.run": ["ide.run", "ide.debug", "ide.stop", "-", "ide.build", "-"] + RUN_ITEMS,
                      "mb.git": ["ide.commit", "ide.push", "ide.pull", "-", "ide.stage", "ide.discard", "-", "history"]})
    ctx.ctxmenu = ["ide.newfile", "ide.newfolder", "-", "cut", "copy", "paste", "-", "link", "rename", "delete", "-", "ide.findall", "history"]
    ctx.ctxobj = "the selected file"
    menus = ["mb.file", "mb.edit", "mb.select", "mb.view", "mb.go", "mb.run", "mb.terminal", "mb.help"]

    if variant == "vscode":
        region = "the explorer header"
        head = (f'<div class="row px12 fn" style="height:32px"><span class="xs b mut up el">{esc(proj)}</span><div class="sp"></div>'
                f'{ctx.ibtns(["ide.newfile", "ide.newfolder", "refresh", "ide.collapseall"], region, cls="s", obj="the file tree")}{ctx.ibtn("more", region, cls="s", anchor="more", obj="the explorer")}</div>')
        secs = "".join(f'<div class="li bt fn b xs"{ctx.reg("row", "section", s, region="the explorer")}><span class="mut">{CHEV_R}</span>{esc(s)}</div>'
                       for s in d.take("ide.secs", SECTIONS, rng.randint(1, 3)))
        side = f'<div class="side br" style="width:{side_w}px">{head}<div class="col f1 clip">{_tree(ctx, "the file tree", files, dirs, st=True)}</div>{secs}</div>'
        tabs = ctx.tabs(open_files, active=0, region="the editor tabs", cls="box", closable=True)
        tabbar = f'<div class="row bb bg1 fn">{tabs.replace("tabs box", "tabs box ide-nb f1")}{ctx.ibtns(["ide.run", "ide.split"], "the editor toolbar", cls="s")}{ctx.ibtn("more", "the editor toolbar", cls="s", anchor="more", obj="the editor")}</div>'
        editor = f'<div class="row str f1">{_code(ext, n_lines, cur=rng.randint(4, 20))}{_minimap(ext, n_lines)}</div>'
        panel = _panel(ctx, tw[:rng.randint(3, 5)], rng.choice([170, 210, 250]) + (60 if H > 1200 else 0), 14) if rng.random() < 0.8 else ""
        body = f'<div class="row str f1">{_rail(ctx, 0)}{side}<div class="col f1">{tabbar}{crumb}{editor}{panel}</div></div>{_status(ctx, lang)}'
    elif variant == "jetbrains":
        region = "the toolbar"
        pattr = ctx.reg("button", "project switcher", proj, region=region, refs=[f"the {proj} project switcher in the toolbar", f"the project dropdown that says {proj}"])
        cfgs = d.take("ide.configs", CONFIGS, 5)
        cfg = ctx.select("Run configuration", cfgs[0], options=cfgs, region=region, above=False, w=150, cls="soft",
                         refs=[f"the run configuration dropdown showing {cfgs[0]}", f"the dropdown that says {cfgs[0]} in the toolbar"])
        top = (f'<div class="tb"><div class="btn ghost b"{pattr}><span class="av sq" style="width:18px;height:18px;font-size:10px;background:var(--ac)">{esc(proj[0].upper())}</span>'
               f'<span>{esc(proj)}</span>{CHEV_D}</div><div class="vsep"></div>{ctx.ibtns(["ide.pull", "ide.commit", "ide.push", "history"], region, obj="this repository")}<div class="sp"></div>{cfg}'
               f'{ctx.ibtns(["ide.run", "ide.debug", "ide.stop", "ide.build", "|", "ide.findall", "settings", "account"], region)}</div>')
        a = max(1, len(tw) // 3)
        left = "".join(ctx.ibtn(c, "the left tool stripe") for c in ["ide.explorer", "ide.scm"] + tw[:a])
        right = "".join(ctx.ibtn(c, "the right tool stripe") for c in ["notif"] + tw[a:2 * a])
        thead = (f'<div class="row px8 bb fn" style="height:30px"><span class="b sm">Project view</span><div class="sp"></div>'
                 f'{ctx.ibtns(["ide.collapseall", "more", "close.panel"], "the project panel header", cls="s", obj="the project panel")}</div>')
        side = f'<div class="side br" style="width:{side_w}px">{thead}<div class="col f1 clip">{_tree(ctx, "the project tree", files, dirs)}</div></div>'
        tabs = ctx.tabs(open_files, active=1 % len(open_files), region="the editor tabs", closable=True)
        btabs = "".join(f'<div class="row g4 px8 mut sm" style="height:24px"{ctx.reg("tab", "tool window button", ctx.lab(c), cid=c, region="the bottom tool bar")}>'
                        f'{ctx.deco("square-terminal", "terminal", "panel-bottom", "app-window", size=12)}<span>{esc(ctx.lab(c))}</span></div>' for c in tw[2 * a:2 * a + 6])
        pr = "the run panel"
        panel = (f'<div class="col bt fn" style="height:{rng.choice([150, 190, 230])}px"><div class="row bb px8 fn" style="height:28px"><span class="sm mut">Console · {esc(cfgs[-1])}</span><div class="sp"></div>'
                 f'{ctx.ibtns(["refresh", "ide.panel", "close.panel"], pr, cls="s", obj="the console output")}</div>{_term(12, rng.randint(0, 20))}</div>') if rng.random() < 0.6 else ""
        body = (f'{top}<div class="row str f1"><div class="col ide-stripe br fn">{left}</div>{side}<div class="col f1">{tabs}{crumb}'
                f'<div class="row str f1">{_code(ext, n_lines, cur=rng.randint(3, 18), offset=rng.randint(0, 9))}</div>{panel}</div>'
                f'<div class="col ide-stripe bl fn">{right}</div></div><div class="row bt bg2 fn">{btabs}</div>{_status(ctx, lang, acc=False)}')
    elif variant == "sublime":
        tabs = ctx.tabs(open_files, active=len(open_files) - 1, region="the tab bar", cls="box", closable=True)
        region = "the find bar"
        find = (f'<div class="row g4 p6 bt bg1 fn">{ctx.ibtns(["ide.regex", "ide.case", "ide.word"], region, cls="s bdr")}<div class="vsep"></div>'
                f'<div class="f1">{ctx.field("Find what", rng.choice(["cfg.port", "handler", "TODO", "timeout"]), region=region, above=False, cls="mono")}</div>'
                f'{ctx.tbtn("ide.findnext", region, cls="sm")}{ctx.tbtn("ide.findprev", region, cls="sm")}</div>'
                f'<div class="row g4 p6 bg1 fn" style="padding-top:0"><div style="width:calc(var(--ibs)*3 - 2px)"></div><div class="f1">{ctx.field("Replace with", "", region=region, above=False, cls="mono")}</div>'
                f'{ctx.tbtn("ide.replace1", region, cls="sm")}{ctx.tbtn("ide.replaceall", region, cls="sm")}</div>') if rng.random() < 0.75 else ""
        side = (f'<div class="side bl" style="width:{side_w}px"><div class="hd">Folders</div><div class="col f1 clip">{_tree(ctx, "the sidebar", files, dirs)}</div></div>')
        body = (f'<div class="row str f1"><div class="col f1">{tabs}<div class="row str f1">{_code(ext, n_lines, cur=rng.randint(2, 25), offset=rng.randint(0, 6))}{_minimap(ext, n_lines)}</div>{find}</div>{side}</div>'
                f'{_status(ctx, lang, acc=False)}')
    elif variant == "split_diff":
        region = "the changes list"
        ch = files[:rng.randint(6, 10)]
        staged = ch[:rng.randint(1, 3)]

        def row(name, is_staged):
            attr = ctx.reg("row", "file", name, region=region, anchor="row")
            acts = (ctx.ibtn("ide.unstage", region, row=name, obj=name, cls="s") if is_staged else
                    ctx.ibtn("ide.discard", region, row=name, obj=name, cls="s") + ctx.ibtn("ide.stage", region, row=name, obj=name, cls="s"))
            letter = rng.choice(["M", "M", "A", "D", "U"])
            return (f'<div class="li ide-tr{" sel" if name == ch[-1] else ""}"{attr}><span class="nw">{esc(name)}</span><span class="fnt xs ide-cut">{esc(rng.choice(dirs))}</span>'
                    f'{acts}<span class="ide-st {"ok" if letter == "A" else "err" if letter == "D" else "wrn"}">{letter}</span></div>')

        msg = ctx.field("Commit message", "", region="the source control panel", above=False, area=52)
        btn = (f'<div class="row g4">{ctx.tbtn("ide.commit", "the source control panel", cls="pri f1", icon=True)}'
               f'{ctx.ibtns(["ide.pull", "ide.push"], "the source control panel", cls="bdr", obj="this repository")}{ctx.ibtn("more", "the source control panel", cls="bdr", anchor="more", obj="source control")}</div>')
        side = (f'<div class="side br" style="width:{side_w + 60}px"><div class="hd">{esc(proj)} · working tree</div><div class="col g6 p8">{msg}{btn}</div>'
                f'<div class="hd">Staged ({len(staged)})</div>{"".join(row(f, True) for f in staged)}<div class="hd">Unstaged ({len(ch) - len(staged)})</div>'
                f'<div class="col f1 clip">{"".join(row(f, False) for f in ch[len(staged):])}</div></div>')
        cur = ch[-1]
        dh = (f'<div class="row g6 px12 bb bg1 fn" style="height:calc(var(--ch) + 10px)"><span class="m">{esc(cur)}</span><span class="fnt sm">(working tree)</span><div class="sp"></div>'
              f'{ctx.ibtns(["ide.prevdiff", "ide.nextdiff", "|", "ide.inline", "ide.split", "more"], "the diff toolbar", cls="s", obj="this comparison")}</div>')
        k = n_lines
        dels = {i: "del" for i in rng.sample(range(4, min(k, 40)), 4)}
        adds = {i + rng.choice([0, 1]): "add" for i in dels}
        body = (f'<div class="row str f1">{_rail(ctx, 2)}{side}<div class="col f1">{dh}<div class="row str f1">{_code(ext, k, marks=dels)}'
                f'<div class="bl"></div>{_code(ext, k, marks=adds)}</div></div></div>{_status(ctx, lang)}')
    else:  # notebook
        region = "the notebook toolbar"
        stems2 = d.files("sheet", 40, ext=False)
        nbs = [f"{s}.ipynb" for s in stems2[:rng.randint(2, 3)]]
        tabs = ctx.tabs(nbs, active=0, region="the notebook tabs", cls="box", closable=True)
        types = d.take("ide.celltypes", CELL_TYPES, 4)
        krefs = _refs(ctx, "kernel", ["the kernel status indicator", "the kernel name at the right of the toolbar", "the interpreter indicator in the toolbar",
                                      "the kernel picker at the top right", "the kernel name next to the green dot"])
        kattr = ctx.reg("button", "indicator", krefs[0], ui="icon", region=region, refs=krefs)
        tb = (f'<div class="tb plain">{ctx.ibtns(["save", "ide.addcell", "cut", "copy", "paste", "|", "ide.runall", "ide.stop", "ide.restart", "|"], region, obj="the selected cell")}'
              f'{ctx.select("Cell type", types[0], options=types, region=region, above=False, w=120, refs=[f"the cell type dropdown showing {types[0]}"]) if types else ""}<div class="sp"></div>'
              f'<div class="row g6 mut sm"{kattr}><span>{esc(lang or ext)} 3 (kernel)</span><span class="dot" style="background:var(--ok)"></span></div>{ctx.ibtn("settings", region)}</div>')
        nav = "".join(ctx.nav(f, "the file browser", noun="file", deco=("file-text", "file", "notebook", "file-chart-column", "file-spreadsheet"), anchor="row")
                      for f in [f"{s}.{rng.choice(['csv', 'ipynb', 'parquet'])}" for s in stems2[3:]] + d.files("doc", 6) + d.files("image", 5))
        side = f'<div class="side br" style="width:{side_w - 20}px"><div class="p8">{ctx.search("the file browser", cls="soft")}</div><div class="col g2 f1 clip">{nav}</div></div>'
        cells, off = [], 0
        for n in range(1, H // 150 + 3):
            name, cr = f"cell {n}", "the notebook"
            k = rng.randint(3, 8)
            cattr = ctx.reg("row", "cell", name, region=cr, refs=[f"code cell {n}", f"the cell numbered [{n}]"])
            acts = ctx.ibtns(["ide.runcell", "ide.cellup", "ide.celldown", "duplicate", "delete"], cr, cls="s", row=name, obj=name)
            out = rng.choice(["", f'<div class="ide-term mut" style="padding:4px 0 0 58px">{esc(rng.choice(["(1284, 12)", "0.9312", "Done in 4.2s", "<DataFrame: 5 rows x 4 columns>"]))}</div>',
                              f'<div style="padding:6px 0 0 58px;max-width:520px">{ctx.bars(h=90, n=14)}</div>'])
            cells.append(f'<div class="col fn"><div class="row top g8"><span class="mono fnt xs" style="width:50px;text-align:right;padding-top:6px">[{n}]:</span>'
                         f'<div class="ide-cell f1 col{" on" if n == 2 else ""}"{cattr}><div class="row" style="justify-content:flex-end;height:0;position:relative;top:4px;right:4px">{acts}</div>'
                         f'{_code(ext, k, offset=off, flex=False)}</div></div>{out}</div>')
            off += k
        body = (f'{tabs}{tb}<div class="row str f1">{side}<div class="col g12 f1 clip" style="padding:14px 28px 0 6px">{"".join(cells)}</div></div>{_status(ctx, lang, acc=False)}')
        menus = ["mb.file", "mb.edit", "mb.view", "mb.run", "mb.window", "mb.help"]
        open_files = nbs
    return {"title": f"{open_files[0]} — {proj}", "body": f'<div class="col f1">{body}</div>', "menus": menus, "app": "Code", "css": CSS,
            "url": "ide.example.dev/" + proj}
