"""Concepts: things a user can act on, each with labels, icon glyphs and intent wordings.

    C(id, "Label A|Label B|Label C", "icon-a|icon-b", "intent a|intent b|intent c", o="this file")

Labels, glyphs and intents are dealt out to splits by finalize(): with three or more labels each
split gets its own; with one label the whole concept lives in a single split. An intent is a
verb phrase ("get rid of {o}") and must not contain any of the concept's labels, because
functional instructions may not quote the label. Placeholders: {o} object, {on} on/off,
{enable} enable/disable, {show} show/hide (the last three describe the change a click makes).
"""
from . import icons
from .splits import SPLITS, LABEL_SPLIT, norm, stable_hash, weighted_split, assert_disjoint

CONCEPTS = {}
INTENT_SPLIT = {}
_final = False


class View:
    __slots__ = ("labels", "icons", "intents")

    def __init__(self):
        self.labels, self.icons, self.intents = [], [], []


class Concept:
    __slots__ = ("id", "labels", "icons", "intents", "o", "fam", "views", "names")

    def __init__(self, cid, labels, icon_names, intents, o, fam, names):
        self.id, self.labels, self.icons, self.intents = cid, labels, icon_names, intents
        self.o, self.fam = o, fam or cid
        # how an icon-only control of this concept is called, per label ("My account" -> "account")
        self.names = dict(zip(labels, names)) if names else {}
        self.views = {s: View() for s in SPLITS}


def _split_list(text):
    return [x.strip() for x in text.split("|") if x.strip()] if isinstance(text, str) else list(text)


def C(cid, labels, icon_names="", intents="", o="", fam=None, n=""):
    assert not _final, "define concepts before finalize()"
    assert cid not in CONCEPTS, f"duplicate concept {cid}"
    names = _split_list(n)
    assert not names or len(names) == len(_split_list(labels)), f"{cid}: n= must give one name per label"
    CONCEPTS[cid] = Concept(cid, _split_list(labels), _split_list(icon_names), _split_list(intents), o, fam, names)


def P(prefix, rows, fam=None):
    """A pool of one-label concepts: rows of (label, intent[, icons]). Ids are prefix + slug."""
    ids = []
    for row in rows:
        label, intent = row[0], row[1]
        cid = prefix + "." + "".join(ch if ch.isalnum() else "_" for ch in label.lower())
        C(cid, label, row[2] if len(row) > 2 else "", intent, fam=fam)
        ids.append(cid)
    return ids


def _deal(items, order, get_owner, set_owner, place):
    """Give each item to one split: items already owned stay put, the rest go to the splits in
    `order` that still have none, and anything beyond that goes to train (or the first split)."""
    have = set()
    fresh = []
    items = list(dict.fromkeys(items))   # two aliases of one glyph must not be dealt twice
    for item in items:
        s = get_owner(item)
        if s is None:
            fresh.append(item)
        else:
            place(item, s)
            have.add(s)
    for item in fresh:
        missing = [s for s in order if s not in have]
        s = missing[0] if missing else ("train" if "train" in order else order[0])
        set_owner(item, s)
        place(item, s)
        have.add(s)


def finalize():
    """Deal labels, glyphs and intents out to splits. Idempotent."""
    global _final
    if _final:
        return
    _final = True
    for c in CONCEPTS.values():
        n = len(c.labels)
        off = stable_hash("concept:" + c.id) % 3
        rotated = [SPLITS[(i + off) % 3] for i in range(3)]
        if n == 1:
            order = [weighted_split("concept:" + c.id)]
        elif n == 2:
            order = ["train", ("dev", "test")[off % 2]]
        else:
            order = rotated
        _deal(c.labels, order, lambda x: LABEL_SPLIT.get(norm(x)),
              lambda x, s: LABEL_SPLIT.__setitem__(norm(x), s), lambda x, s: c.views[s].labels.append(x))
        live = [s for s in rotated if c.views[s].labels]
        _deal([icons.canon(x) for x in c.icons], live, icons.ICON_SPLIT.get, icons.ICON_SPLIT.__setitem__,
              lambda x, s: c.views[s].icons.append(x) if s in live and x not in c.views[s].icons else None)
        _deal(c.intents, live, INTENT_SPLIT.get, INTENT_SPLIT.__setitem__,
              lambda x, s: c.views[s].intents.append(x) if s in live else None)


def check():
    """Assert that no label, glyph or intent wording is owned by two splits."""
    labels = {s: {k for k, v in LABEL_SPLIT.items() if v == s} for s in SPLITS}
    glyphs = {s: {k for k, v in icons.ICON_SPLIT.items() if v == s} for s in SPLITS}
    intents = {s: {k for k, v in INTENT_SPLIT.items() if v == s} for s in SPLITS}
    assert_disjoint(labels, "label")
    assert_disjoint(glyphs, "icon glyph")
    assert_disjoint(intents, "intent wording")


def coverage():
    """Rows of (concept id, split, has label, n icons, n intents) for inspection."""
    finalize()
    return [(c.id, s, bool(c.views[s].labels), len(c.views[s].icons), len(c.views[s].intents))
            for c in CONCEPTS.values() for s in SPLITS]


# ---------------------------------------------------------------------------------------------
# Shared concepts. Archetype modules add their own next to the layouts that use them.
# ---------------------------------------------------------------------------------------------

# window controls (drawn by the window chrome, not from the icon set)
C("win.close", "Close|Close window|Exit", "", "shut this window|make this whole window go away|quit out of this window")
C("win.min", "Minimize|Minimize window|Hide window", "", "send this window down to the dock or taskbar|tuck this window away without quitting|shrink this window out of sight for now")
C("win.max", "Maximize|Zoom window|Full size", "", n="maximize|zoom|full size", intents= "make this window fill the whole screen|blow this window up as large as it goes|stretch this window across the entire display")

# menu bar titles: direct instructions only
for _cid, _labels in [
    ("mb.file", "File|Document|Project"), ("mb.edit", "Edit|Modify|Editing"), ("mb.view", "View|Display|Appearance"),
    ("mb.insert", "Insert|Embed|Place"), ("mb.format", "Format|Style|Formatting"), ("mb.tools", "Tools|Utilities|Extras"),
    ("mb.window", "Window|Windows|Workspace"), ("mb.help", "Help|Support|Assistance"), ("mb.go", "Go|Navigate|Jump"),
    ("mb.run", "Run|Execute|Launch"), ("mb.data", "Data|Records|Dataset"), ("mb.select", "Select|Selection|Marquee"),
    ("mb.image", "Image|Picture|Bitmap"), ("mb.layer", "Layer|Layers|Stack"), ("mb.object", "Object|Shape|Element"),
    ("mb.filter", "Effects|Adjust|Enhance"), ("mb.clip", "Clip|Footage|Segment"), ("mb.sequence", "Sequence|Timeline|Montage"),
    ("mb.message", "Message|Mail|Correspondence"), ("mb.terminal", "Terminal|Shell|Console"), ("mb.git", "Git|Source Control|VCS"),
    ("mb.controls", "Controls|Playback|Transport"), ("mb.table", "Table|Grid|Cells"), ("mb.history", "Past states|Recent|Timeline log"),
    ("mb.account", "Account|Profile|Identity"), ("mb.code", "Code|Refactor|Source"), ("mb.debug", "Debug|Diagnose|Inspect"),
    ("mb.text", "Text|Type|Typography"), ("mb.arrange", "Arrange|Align|Layout"), ("mb.plugins", "Plugins|Extensions|Add-ons"),
]:
    C(_cid, _labels)

# app-wide
C("search", "Search|Find|Look up", "search|text-search|scan-search", n="search|find|lookup", intents= "look for something by typing a keyword|type in what I'm trying to locate|hunt for an item by typing its name")
C("settings", "Settings|Preferences|Options", "settings|cog|sliders-horizontal|settings-2", "change how this app is configured|adjust the configuration of this program|customize how this application behaves")
C("help", "Help center|Get help|Documentation", "circle-help|life-buoy|book-open", n="help|support|documentation", intents= "read the instructions for this app|get assistance with using this program|learn how this application works")
C("notif", "Notifications|Alerts|Updates", "bell|bell-ring|bell-dot", "see what happened while I was away|check what I've been pinged about|open the feed of pings and mentions addressed to me")
C("account", "My account|Your profile|Signed-in user", "circle-user|user-round|circle-user-round", n="account|profile|user menu", intents= "manage my personal details|see who I'm signed in as|switch to a different user or sign out")
C("apps", "Apps|Launcher|All apps", "grip|blocks|component", "switch to another product in this suite|jump to a different app from the launcher grid|see the other applications I can open")

# clipboard and history
C("undo", "Undo|Revert last|Step back", "undo-2|undo|rotate-ccw", "take back the last thing I did|reverse my most recent change|cancel out my previous action")
C("redo", "Redo|Reapply|Step forward", "redo-2|redo|rotate-cw", "bring back the change I just reversed|do again what I just took back|restore the action I reversed a moment ago")
C("cut", "Cut|Cut selection|Move to clipboard", "scissors|scissors-line-dashed|square-scissors", "lift {o} out so I can put it somewhere else|take {o} out and hold it on the clipboard|pull {o} out to drop it elsewhere", o="the selection")
C("copy", "Copy|Copy selection|Copy to clipboard", "copy|clipboard-copy|files", "put a duplicate of {o} on the clipboard|grab {o} so I can insert it somewhere else too|take a clipboard duplicate of {o}", o="the selection")
C("paste", "Paste|Paste here|Insert from clipboard", "clipboard-paste|clipboard|clipboard-check", "drop in what I last grabbed to the clipboard|put the clipboard contents here|bring in whatever is on my clipboard")
C("selectall", "Select all|Select everything|Mark all", "", "highlight every item at once|pick up all the items in one go|choose the whole lot in a single step")

# documents and files
C("new", "New|Create new|Start new", "plus|circle-plus|square-plus", "start {o} from scratch|begin {o} with a blank slate|make {o} that is empty", o="a fresh document")
C("open", "Open|Open file|Browse files", "folder-open|folder-search|folder-open-dot", "load an existing file from disk|bring up a file I already have|pick a file from my computer to work on")
C("save", "Save|Save changes|Apply changes", "save|save-all|hard-drive-download", "keep the edits I just made|write my work to disk|make sure my latest edits are not lost")
C("saveas", "Save as|Save a copy|Save under new name", "save-plus|save-pen|file-plus", "store this under a different file name|keep a second version under another name|write this out as a separate new file")
C("export", "Export|Export data|Export as file", "file-output|file-down|folder-output", "get {o} out as a file for another program|produce a file of {o} that other tools can read|turn {o} into a file I can hand to someone", o="this")
C("import", "Import|Import data|Import from file", "file-input|file-up|folder-input", "bring data in from an outside file|load content that was made in another program|pull in records from a file on my computer")
C("print", "Print|Print page|Send to printer", "printer|printer-check", "get a paper version of {o}|make a hard paper version of {o}|put {o} on paper", o="this")
C("share", "Share|Share with others|Invite people", "share-2|share|user-plus", "give other people access to {o}|let a colleague see {o}|send {o} to my teammates so they can open it", o="this")
C("download", "Download|Save to device|Get file", "download|cloud-download|arrow-down-to-line", "fetch {o} onto my computer|pull {o} down to my local disk|get an offline version of {o} onto this machine", o="this")
C("upload", "Upload|Upload files|Add from computer", "upload|cloud-upload|arrow-up-from-line", "send a file from my computer up to here|put a local file onto this service|push something from my disk into this app")
C("rename", "Rename|Change name|Edit name", "pencil-line|text-cursor-input|folder-pen", "give {o} a different title|call {o} something else|change what {o} is called", o="this item")
C("duplicate", "Duplicate|Make a copy|Clone", "copy-plus|book-copy|layers-2", "make an identical twin of {o}|create a second, identical version of {o}|produce another one just like {o}", o="this item")
C("delete", "Delete|Remove|Discard", "trash-2|delete|shredder", "get rid of {o}|throw {o} away|erase {o} for good", o="the selected item")
C("edit", "Edit|Revise|Make changes", "pencil|square-pen|pen", "change the details of {o}|revise {o}|alter what is in {o}", o="this item")
C("add", "Add|Add new|Add item", "plus|circle-plus|square-plus", "put one more entry into {o}|create an additional entry in {o}|append another entry to {o}", o="this list")
C("move", "Move to|Move|Relocate", "folder-input|move|folder-symlink", "put {o} in a different place|shift {o} to another location|file {o} somewhere else", o="this item")
C("info", "Details|Get info|Properties", "info|badge-info|file-search", "see the facts about {o}|look at the metadata for {o}|check the size, dates and other data of {o}", o="this item")

# view
C("zoomin", "Zoom in|Enlarge|Magnify", "zoom-in|circle-plus|plus", "make everything look bigger|get a closer look at the content|increase the magnification")
C("zoomout", "Zoom out|Shrink|Reduce", "zoom-out|circle-minus|minus", "make everything look smaller|see more of the content at once|decrease the magnification")
C("fullscreen", "Full screen|Enter full screen|Fill screen", "maximize|expand|maximize-2", "hide everything else and use the entire display|make the content take over the whole monitor|go distraction-free across the entire display")
C("refresh", "Refresh|Reload|Sync now", "refresh-cw|rotate-cw|refresh-ccw", n="refresh|reload|sync", intents= "fetch the latest version of {o}|update {o} with the newest data|check for anything new in {o}", o="this view")
C("filter", "Filter|Filters|Narrow down", "funnel|list-filter|sliders-horizontal", "show only the entries that match some criteria|limit what's listed to certain conditions|hide the entries I don't care about")
C("sort", "Sort|Sort by|Order by", "arrow-up-down|arrow-down-up|arrow-down-wide-narrow", "change the order the entries appear in|rearrange the entries by a different column|pick which field decides the ordering")
C("view.grid", "Grid view|Tiles|Thumbnails", "layout-grid|grid-2x2|grid-3x3", "show the items as a wall of tiles|display the items as thumbnails in rows and columns|switch to seeing big previews side by side")
C("view.list", "List view|Rows|Detailed list", "list|layout-list|rows-3", "show the items as lines of text, one per line|display the items as a plain stack of lines|switch to a compact one-per-line layout")
C("sidebar.toggle", "Toggle sidebar|Hide sidebar|Collapse side panel", "panel-left|panel-left-close|panel-left-open", n="sidebar toggle|hide sidebar|side panel", intents= "get the side navigation out of the way|fold away the navigation column|reclaim the space used by the left-hand column")
C("panel.toggle", "Toggle inspector|Hide inspector|Collapse details panel", "panel-right|panel-right-close|panel-right-open", n="inspector toggle|hide inspector|details panel", intents= "fold away the right-hand details column|get the right-side pane out of the way|reclaim the space used by the pane on the right")
C("more", "More|More actions|More options", "ellipsis|ellipsis-vertical|circle-ellipsis", "see the extra commands that are tucked away for {o}|reveal the overflow commands for {o}|bring up the additional choices for {o}", o="this")

# navigation
C("back", "Back|Go back|Previous page", "arrow-left|chevron-left|circle-arrow-left", "return to where I was before|go to the place I was just looking at|step to the screen I came from")
C("forward", "Forward|Go forward|Next page", "arrow-right|chevron-right|circle-arrow-right", "go ahead again after having gone backwards|step onward to the screen I backed out of|move ahead to the place I returned from")
C("home", "Home|Start page|Overview", "house|layout-dashboard|compass", "go to the main landing screen|return to the app's starting screen|jump to the top-level screen")
C("up", "Up one level|Parent folder|Enclosing folder", "arrow-up|corner-left-up|folder-up", n="up|parent folder|enclosing folder", intents= "go to the folder that contains this one|climb to the directory above|step out to the containing directory")

# misc actions
C("fav", "Favorite|Star|Add to favorites", "heart|star|bookmark", n="favorite|star|favorites", intents= "mark {o} as one I care about|flag {o} as special so I can find it quickly|keep {o} among my preferred ones", o="this")
C("pin", "Pin|Pin to top|Keep on top", "pin|arrow-up-to-line|chevrons-up", "make {o} stay at the top|keep {o} stuck in place above the rest|fix {o} so it does not scroll away", o="this")
C("link", "Copy link|Get link|Copy URL", "link|link-2", "grab a web address that points to {o}|get an address for {o} I can send to someone|put the URL of {o} on my clipboard", o="this")
C("attach", "Attach|Attach file|Add attachment", "paperclip|file-plus-2|image-plus", "include a file with {o}|add a document from my computer to {o}|tack a file onto {o}", o="this message")
C("send", "Send|Send now|Deliver", "send|send-horizontal|arrow-up", "dispatch {o}|fire off {o}|get {o} on its way to the recipient", o="this message")
C("close.panel", "Close panel|Hide panel|Dismiss panel", "x|circle-x|square-x", "make {o} go away|get {o} off the screen|put {o} away", o="this panel")
C("expand", "Expand|Show more|Unfold", "chevrons-up-down|chevron-down|unfold-vertical", "reveal the hidden part of {o}|open {o} up to see everything in it|unfurl {o} so nothing is hidden", o="this section")
C("collapse", "Collapse|Show less|Fold", "chevrons-down-up|chevron-up|fold-vertical", "tuck {o} away to save space|shrink {o} down to just its heading|roll {o} up so it takes less room", o="this section")
C("clear", "Clear|Clear all|Reset", "eraser|x|circle-x", "wipe out what is entered in {o}|empty {o} and start over|blank out {o}", o="this field")
C("lock", "Lock|Lock editing|Protect", "lock|lock-keyhole|shield", "prevent {o} from being changed|freeze {o} so nobody can alter it|make {o} read-only", o="this")
C("hide", "Hide|Hide item|Conceal", "eye-off|eye-closed|eye", "make {o} invisible without deleting it|stop {o} from showing|take {o} out of sight but keep it", o="this")
C("history", "History|Version history|Revisions", "history|clock|file-clock", "see earlier versions of {o}|look at how {o} changed over time|go through the past states of {o}", o="this document")
C("comment", "Comment|Add comment|Leave a note", "message-square|message-circle|message-square-plus", "write a remark about {o}|leave feedback on {o}|jot a remark for others on {o}", o="this")
C("tagit", "Add tag|Label|Categorize", "tag|tags|bookmark-plus", "attach a keyword to {o}|classify {o} under a category|mark {o} with a keyword so I can group it", o="this")

C("tab.close", "Close tab|Shut tab|Dismiss tab", "", "shut {o}|get {o} out of my open tabs|put {o} away", o="the current tab")

# dialog buttons
C("cancel", "Cancel|Never mind|Abort", "", "back out without doing anything|abandon this and leave things as they were|call this off")
C("ok", "OK|Confirm|Continue", "", "go ahead with what the dialog proposes|accept and proceed|agree and carry on")
C("dlg.close", "Close dialog|Dismiss|Close popup", "x|circle-x|square-x", "make this popup go away without choosing anything|get rid of this dialog box|shut this popup")
C("next", "Next|Next step|Proceed", "", "move on to the following step|advance to the step after this one|go on to the page that comes after this")
C("prev", "Previous|Previous step|Back a step", "", "return to the step before this one|go to the step I just completed|revisit the preceding step")
C("done", "Done|Finish|Complete", "", "wrap this up now that every step is filled in|complete the process|conclude this now that everything is entered")
