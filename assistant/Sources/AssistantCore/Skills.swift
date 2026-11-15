import Foundation

/// Things the assistant can do with the model as a language model, and things that need no
/// model at all. This file only recognises them in what was asked; the app carries them out.

/// A request about the selected text: what to tell the model, and whether the result replaces
/// the selection (a rewrite) or is only shown and spoken (a summary, an explanation).
/// An empty instruction needs no model: the selection is read aloud as it is.
public struct TextSkill: Equatable {
    public let instruction: String
    public let replaces: Bool
    public let caption: String
}

public enum Skills {
    static let selection = #"(?:this|that|it|these|the\s+selection|the\s+selected\s+text|the\s+text|my\s+text|what\s+i\s+selected|the\s+highlighted\s+text)"#
    static let manner = #"((?:more|less|a\s+bit|a\s+little|much)\s+.+|shorter|longer|simpler|clearer|friendlier|politer|nicer|kinder|funnier|warmer|stronger|better|formal|informal|casual|professional|polite|concise|friendly|funny)"#

    /// The selection skill a request asks for, or nil.
    public static func text(_ request: String) -> TextSkill? {
        let c = request.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".!?")))
        if let m = Commands.match("^(?:please\\s+)?translate\\s+(?:" + selection + "\\s+)?(?:to|into)\\s+([\\p{L} ]+)$", c) {
            return TextSkill(instruction: "Translate the text into \(m[1]).", replaces: true, caption: "Translating into \(m[1])")
        }
        if Commands.match("^(?:please\\s+)?(?:fix|correct|check)\\s+(?:the\\s+|my\\s+)?(?:grammar|spelling|typos|mistakes)(?:\\s+(?:in|of)\\s+" + selection + ")?$", c) != nil
            || Commands.match("^(?:please\\s+)?proofread\\s+" + selection + "$", c) != nil {
            return TextSkill(instruction: "Correct the grammar and spelling of the text. Change nothing else.", replaces: true, caption: "Fixing the grammar")
        }
        if Commands.match("^(?:please\\s+)?(?:shorten|condense)\\s+" + selection + "$", c) != nil {
            return TextSkill(instruction: "Make the text shorter. Keep what matters.", replaces: true, caption: "Shortening it")
        }
        if Commands.match("^(?:please\\s+)?(?:rewrite|rephrase|reword|improve|polish)\\s+" + selection + "$", c) != nil {
            return TextSkill(instruction: "Rewrite the text so that it reads clearly and well. Keep its meaning.", replaces: true, caption: "Rewriting it")
        }
        if let m = Commands.match("^(?:please\\s+)?(?:rewrite|rephrase|reword)\\s+" + selection + "(?:\\s+(?:to\\s+be|to\\s+sound|so\\s+it\\s+is|so\\s+it\\s+sounds|as|in\\s+a))?\\s+(.+)$", c)
            ?? Commands.match("^(?:please\\s+)?make\\s+" + selection + "\\s+(?:sound\\s+|read\\s+)?" + manner + "$", c) {
            return TextSkill(instruction: "Rewrite the text in this way: \(m[1]). Keep its meaning.", replaces: true, caption: "Rewriting it, \(m[1])")
        }
        if Commands.match("^(?:please\\s+)?(?:summari[sz]e|sum\\s+up|give\\s+me\\s+a\\s+summary\\s+of)\\s+" + selection + "$", c) != nil {
            return TextSkill(instruction: "Summarise the text in two short sentences.", replaces: false, caption: "Summarising")
        }
        if Commands.match("^(?:please\\s+)?explain\\s+" + selection + "(?:\\s+to\\s+me)?$", c) != nil
            || Commands.match("^what\\s+does\\s+" + selection + "\\s+(?:mean|say)$", c) != nil {
            return TextSkill(instruction: "Explain the text in two short, plain sentences.", replaces: false, caption: "Explaining")
        }
        if Commands.match("^(?:please\\s+)?read\\s+" + selection + "(?:\\s+(?:to\\s+me|aloud|out\\s+loud|out))?$", c) != nil {
            return TextSkill(instruction: "", replaces: false, caption: "Reading it aloud")
        }
        return nil
    }

    /// What the model is asked, for a selection skill.
    public static func prompt(_ skill: TextSkill, text: String) -> String {
        skill.instruction + " Reply with only the result, with no introduction and no quotation marks.\n\nText:\n" + text
    }

    // MARK: no model needed

    /// Requests that are one keyboard shortcut in every Mac app: pressed directly, where a
    /// model tends to go looking for something to click. Only the whole phrase counts.
    public static let shortcuts: [(String, [String])] = [
        (#"^close\s+(?:this\s+|the\s+)?(?:tab|window)$"#, ["cmd", "w"]),
        (#"^(?:open\s+|make\s+)?(?:a\s+)?new\s+tab$"#, ["cmd", "t"]),
        (#"^(?:open\s+|make\s+)?(?:a\s+)?new\s+window$"#, ["cmd", "n"]),
        (#"^(?:reload|refresh)(?:\s+(?:this\s+|the\s+)?page)?$"#, ["cmd", "r"]),
        (#"^go\s+back(?:\s+a\s+page)?$"#, ["cmd", "["]),
        (#"^go\s+forward(?:\s+a\s+page)?$"#, ["cmd", "]"]),
        (#"^undo(?:\s+that|\s+it)?$"#, ["cmd", "z"]),
        (#"^redo(?:\s+that|\s+it)?$"#, ["cmd", "shift", "z"]),
        (#"^select\s+(?:all|everything)$"#, ["cmd", "a"]),
        (#"^copy(?:\s+this|\s+that|\s+it)?$"#, ["cmd", "c"]),
        (#"^paste(?:\s+it|\s+that)?$"#, ["cmd", "v"]),
        (#"^save(?:\s+(?:this|it|the\s+(?:file|document)))?$"#, ["cmd", "s"]),
        (#"^print(?:\s+(?:this|it|the\s+(?:page|document)))?$"#, ["cmd", "p"]),
        (#"^minimi[sz]e(?:\s+(?:this|it|this\s+window|the\s+window))?$"#, ["cmd", "m"]),
        (#"^hide\s+(?:this\s+app|this\s+window|this)$"#, ["cmd", "h"]),
        (#"^zoom\s+in$"#, ["cmd", "plus"]),
        (#"^zoom\s+out$"#, ["cmd", "minus"]),
        (#"^(?:enter|exit|leave|toggle|go)\s+(?:to\s+)?full\s*screen$"#, ["ctrl", "cmd", "f"]),
    ]

    /// A part of a request without the words people put in front ("please", "then", "hey, can
    /// you") or after it ("please", and the question mark of an order said as a question).
    public static func stripped(_ clause: String) -> String {
        var c = clause.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".!")))
        var asked = false
        while let m = Commands.match(#"^(?:please|now|next|first|finally|and|also|then|hey|hi|hello|ok|okay|kindly|just|can you|could you|would you|will you)[,\s]+(.+)$"#, c) {
            if Commands.match(#"^(?:can|could|would|will)\s+you\b"#, c) != nil { asked = true }
            c = m[1]
        }
        if asked { c = c.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".!?"))) }
        if let m = Commands.match(#"^(.+?)[,\s]+(?:please|for\s+me)$"#, c) { c = m[1] }
        return c
    }

    /// A window's own buttons, said any way: "minimize the open window", "minimize Safari",
    /// "close the Notes window", "make this full screen", "full screen Safari". The pointer
    /// goes to the button in the window's corner and presses it; with an app named, that app
    /// comes to the front first. "Close this tab" and "quit Safari" are not window buttons.
    static func windowButton(_ c: String, app: (String) -> String?) -> PlannedStep? {
        let own = #"(?:(?:this|that|the|my|your)\s+)?(?:(?:open|opened|current|front|frontmost|active|top|focused)\s+)?(?:window|app|application|one|it|this|that)"#
        let forms: [(kind: String, verbs: String)] = [
            ("minimize", #"(?:minimi[sz]e)"#),
            ("close", #"(?:close)"#),
            ("zoom", #"(?:full\s*-?\s*screen|make\s+full\s*-?\s*screen)"#),
        ]
        for (kind, verbs) in forms {
            if Commands.match("^" + verbs + "(?:\\s+" + own + ")?$", c) != nil {
                if kind == "close", Commands.match(#"^close$"#, c) != nil { return nil }               // "close" alone says too little
                return PlannedStep(action: "window_button", target: kind)
            }
            if let m = Commands.match("^" + verbs + #"\s+(?:the\s+|my\s+)?(.+?)(?:\s+(?:window|app|application))?$"#, c),
               Commands.match(#"\b(?:tab|tabs|file|document|folder|menu|sidebar|dialog|sheet|popup|pop-up|notification|ad)\b"#, m[1]) == nil,
               let name = app(m[1]) {
                return PlannedStep(action: "window_button", app: name, target: kind)
            }
        }
        // "make this full screen", "put Safari in full screen", "go full screen", "exit full screen"
        if Commands.match("^(?:make|put|set|turn)\\s+" + own + #"\s+(?:to\s+|in\s+|into\s+|on\s+)?full\s*-?\s*screen$"#, c) != nil
            || Commands.match(#"^(?:enter|go|go\s+to|go\s+into)\s+full\s*-?\s*screen(?:\s+mode)?$"#, c) != nil {      // leaving it stays a key: the buttons are hidden there
            return PlannedStep(action: "window_button", target: "zoom")
        }
        if let m = Commands.match(#"^(?:make|put|set|turn)\s+(?:the\s+|my\s+)?(.+?)(?:\s+(?:window|app))?\s+(?:to\s+|in\s+|into\s+|on\s+)?full\s*-?\s*screen$"#, c), let name = app(m[1]) {
            return PlannedStep(action: "window_button", app: name, target: "zoom")
        }
        return nil
    }

    /// A part of a request that is an app and then one shortcut in it:
    /// "open Safari settings" (the app, then command-comma), "open a new Finder window",
    /// "open a new tab in Safari"; and "open a Finder window at Applications" (the folder).
    public static func appSettings(_ clause: String, app: (String) -> String?) -> [PlannedStep]? {
        let c = stripped(clause)
        // a pane of System Settings wins when the request says "settings": "Bluetooth settings"
        // is the pane, not the settings of the app Bluetooth File Exchange
        if let m = Commands.match(#"^(?:open|show|go\s+to|bring\s+up)\s+(?:the\s+)?(.+?)(?:'s)?\s+(?:settings|preferences|prefs)$"#, c),
           Places.pane(m[1]) == nil, let name = app(m[1]), name != "System Settings" {
            return [PlannedStep(action: "open_app", app: name), PlannedStep(action: "key", keys: ["cmd", ","])]
        }
        if let m = Commands.match(#"^(?:open|show)\s+(?:a\s+)?(?:new\s+)?finder\s+window\s+(?:at|in|on|for|showing|to)\s+(.+)$"#, c), let folder = Places.folder(m[1]) {
            return [PlannedStep(action: "reveal", target: folder)]
        }
        let key = { (what: String) in what.lowercased() == "tab" ? ["cmd", "t"] : ["cmd", "n"] }
        if let m = Commands.match(#"^(?:open|make|create|start)\s+(?:a\s+)?new\s+(.+?)\s+(window|tab|document)$"#, c), let name = app(m[1]) {
            return [PlannedStep(action: "open_app", app: name), PlannedStep(action: "key", keys: key(m[2]))]
        }
        if let m = Commands.match(#"^(?:open|make|create|start)\s+(?:a\s+)?new\s+(window|tab|document)\s+in\s+(.+)$"#, c), let name = app(m[2]) {
            return [PlannedStep(action: "open_app", app: name), PlannedStep(action: "key", keys: key(m[1]))]
        }
        return nil
    }

    /// "Open apple.com in Safari", "go to example.com/docs in Chrome", "open YouTube in Brave":
    /// the site, exactly as named, in the browser that is named.
    public static func siteInBrowser(_ clause: String, app: (String) -> String?) -> PlannedStep? {
        let c = stripped(clause)
        guard let m = Commands.match(#"^(?:open|go\s+to|visit|browse\s+to|take\s+me\s+to|show|launch|load|pull\s+up|bring\s+up)\s+(?:the\s+website\s+|the\s+site\s+)?(.+)\s+(?:in|on|with|using)\s+(?:the\s+|my\s+)?(.+?)$"#, c),
              let browser = app(m[2]), Places.browsers.contains(browser),
              let address = Recipes.site(m[1]) ?? Places.site(named: m[1])
                ?? (Commands.match(#"^(?:my\s+|the\s+)?(?:e-?mails?|gmail|inbox|mail)$"#, m[1]) != nil ? "https://mail.google.com" : nil) else { return nil }   // "my email in Brave" is the web mail, not the Mail app
        return PlannedStep(action: "open_url", app: browser, url: address)
    }

    /// Words that end by naming a browser ("lunch on Friday in Safari"): the words before it,
    /// and the browser. Nil when they name none.
    public static func namedBrowser(_ words: String, app: (String) -> String?) -> (rest: String, browser: String)? {
        // the browser is the last thing said: "lunch on Friday in Safari" is cut at the last "in"
        guard let m = Commands.match(#"^(.+)\s+(?:in|on|with|using)\s+(?:the\s+|my\s+)?(.+?)$"#, words.trimmingCharacters(in: .whitespaces)),
              let browser = app(m[2]), Places.browsers.contains(browser) else { return nil }
        return (m[1], browser)
    }

    /// "Bring up the presentation", "show my slides", "start the slideshow": the deck kept for
    /// this (see the app's `Mac.presentation`) is shown, and whatever was in front is hidden.
    static func presentation(_ c: String) -> PlannedStep? {
        let shows = #"(?:bring\s+up|open|show|start|play|pull\s+up|put\s+up|launch|begin|go\s+(?:back\s+)?to|switch\s+to|back\s+to|present)"#
        let deck = #"(?:\p{L}*presentation|slide\s?show|slides|slide|deck|pitch|keynote)"#
        // "pull up the presentation for this hackathon? It's in the Downloads folder", "open the Clicky presentation in my downloads", "open clickypresentation pdf"
        let after = #"(?:\s+(?:pdf|file))?(?:[\s,.?!]+(?:for|of|about|from|in|on|that|it'?s|it\s+is|its)\b.*)?"#
        return Commands.match("^" + shows + "\\s+(?:the\\s+|my\\s+|our\\s+)?(?:[\\p{L}\\p{N}'-]+\\s+){0,2}" + deck + after + "$", c) != nil ? PlannedStep(action: "present") : nil
    }

    /// "Caption the video I just recorded", "put subtitles on my last recording": the newest
    /// recording gets its own words as subtitles on a copy, made on this Mac.
    static func captionedVideo(_ c: String) -> PlannedStep? {
        let which = #"(?:the\s+|my\s+|this\s+|that\s+)?(?:last\s+|latest\s+|new\s+|newest\s+)?(?:video|recording|movie|clip)(?:\s+(?:that\s+)?i\s+just\s+(?:recorded|made|took|shot))?"#
        let forms = ["^(?:caption|subtitle)\\s+" + which + "$",
                     "^(?:add|put|burn|write|make)\\s+(?:the\\s+)?(?:subtitles|captions|closed\\s+captions)\\s+(?:to|on|onto|into|in|for)\\s+" + which + "$"]
        return forms.contains { Commands.match($0, c) != nil } ? PlannedStep(action: "caption_video") : nil
    }

    /// "Play the video on my desktop", "open the comparison video": the newest recording
    /// there (or in Movies, the Desktop or Downloads when no place is said) is opened in
    /// QuickTime Player, made to fill the screen, and played.
    static func playedVideo(_ c: String) -> PlannedStep? {
        // "start recording", "start a recording in Photo Booth", "record a video": that is making one, not playing one
        if Commands.match(#"^(?:start|begin|stop|end|make|take)\s+(?:an?\s+|the\s+)?(?:new\s+|video\s+|screen\s+)?recording\b|\brecord\b"#, c) != nil { return nil }
        guard let m = Commands.match(#"^(?:play|open|show|start|watch|put\s+on)\s+(?:the\s+|my\s+|that\s+)?(?:comparison\s+|demo\s+|newest\s+|latest\s+|last\s+)?(?:video|movie|clip|recording)(?:\s+(?:that\s+is\s+)?(?:on|from|in)\s+(?:the\s+|my\s+)?(desktop|movies|downloads)(?:\s+folder)?)?$"#, c) else { return nil }
        return PlannedStep(action: "play_video", target: m[1].lowercased())
    }

    /// "Write down what you can help me with", "write a note about the trip": the model
    /// writes a few short lines as a language model, and the app opens a new note and types
    /// them. A note whose words are given ("a note that says …") is not this: its text is
    /// typed as it is, by the planner.
    static func writtenNote(_ c: String) -> PlannedStep? {
        let t = Commands.unquoted(c).lowercased()
        guard Commands.match(#"^(?:write|jot|note|list|type|make\s+(?:me\s+)?a\s+(?:note|list)|create\s+a\s+(?:note|list))\b"#, t) != nil,
              c == Commands.unquoted(c).trimmingCharacters(in: .whitespaces) || !c.contains("\"") else { return nil }      // nothing quoted to type
        if Commands.match(#"\byou\s+can\s+(?:help|do)\b|\bwhat\s+you\s+(?:do|are\s+good\s+at)\b|\byour\s+(?:skills|abilities)\b"#, t) != nil {
            return PlannedStep(action: "write_note", target: "abilities")
        }
        if let m = Commands.match(#"^(?:write|jot)\s+down\s+((?:some|a\s+few|three|four|five|ideas|a\s+list|the\s+steps|how|why|what)\b.+)$"#, c)
            ?? Commands.match(#"^(?:write|make|create)\s+(?:me\s+)?a\s+(?:short\s+)?(?:note|list)\s+(?:about|of|on)\s+(.+)$"#, c) {
            return PlannedStep(action: "write_note", target: m[1])
        }
        return nil
    }

    /// What the model is asked to write for such a note.
    public static func notePrompt(_ topic: String) -> String {
        if topic == "abilities" {
            return "You are an assistant that lives on this Mac and works without the internet. In four short lines, tell the person using it what you can do for them. "
                + "One thing per line, each line under ten words and starting with a verb. Choose from what you can really do: open apps and web sites; "
                + "change settings such as dark mode and the volume; put windows side by side; find and click things on the screen; answer questions about the screen; "
                + "rewrite or translate the text they select; make notes, reminders and calendar events; rename and move files. "
                + "No numbering, no bullets, no introduction, nothing after the four lines."
        }
        return "Write four short lines about this: \(topic). One point per line, each line under ten words. No numbering, no bullets, no introduction, nothing after the four lines."
    }

    /// The title such a note gets (its first line).
    public static func noteTitle(_ topic: String) -> String {
        if topic == "abilities" { return "What I can help you with" }
        var t = topic.trimmingCharacters(in: CharacterSet.whitespaces.union(CharacterSet(charactersIn: ".!?")))
        while let m = Commands.match(#"^(?:some|a\s+few|three|four|five|a\s+list\s+of|the)\s+(.+)$"#, t) { t = m[1] }
        return t.prefix(1).uppercased() + t.dropFirst()
    }

    /// What the model wrote, as the lines of a note: its thinking, bullets, numbers and
    /// quotation marks taken off, empty lines dropped, five lines at most.
    public static func noteLines(_ written: String) -> [String] {
        Parsing.stripThinking(written).replacingOccurrences(of: "**", with: "").split(whereSeparator: { $0.isNewline }).map { line -> String in
            var t = line.trimmingCharacters(in: .whitespaces)
            if let m = Commands.match(#"^(?:[-•*·–]+|\d+[.)])\s*(.+)$"#, t) { t = m[1] }
            return t.trimmingCharacters(in: CharacterSet.whitespaces.union(CharacterSet(charactersIn: "\"“”")))
        }.filter { $0.count > 2 }.prefix(5).map { $0 }
    }

    /// The lines used when the model writes nothing that can be used.
    public static let abilityLines = ["Open apps and web sites for you", "Change settings like dark mode and the volume",
                                      "Find and click things on the screen", "Write notes, reminders and calendar events"]

    /// A text in the small pieces it is typed in, so that it can be watched being written.
    public static func typingPieces(_ text: String) -> [String] {
        var pieces: [String] = [], current = ""
        for ch in text {
            current.append(ch)
            if ch == " " || ch == "\n" { pieces.append(current); current = "" }
        }
        if !current.isEmpty { pieces.append(current) }
        return pieces
    }

    /// What a menu holds, said from the list itself: its items in order, eight at most, then
    /// how many more. No model: the list is the answer.
    public static func menuAnswer(title: String, items: [String]) -> String {
        let shown = items.prefix(8).joined(separator: ", ")
        let more = items.count > 8 ? ", and \(items.count - 8) more" : ""
        let menu = title.isEmpty || title == "menu bar" ? (title == "menu bar" ? "The menu bar has" : "This menu has") : "The \(title) menu has"
        return items.isEmpty ? "\(menu) nothing that can be chosen now." : "\(menu): \(shown)\(more)."
    }

    /// A step that needs no model once recognised: a universal shortcut, laying windows out, a
    /// system switch, a folder, a calendar event. Carried out by the app directly.
    public static func direct(_ clause: String, app: (String) -> String?) -> PlannedStep? {
        let c = stripped(clause)
        // a window's own buttons are pressed with the pointer (the shortcut is only the fallback)
        if Commands.match(#"^minimi[sz]e(?:\s+(?:this|it|this\s+window|the\s+window))?$"#, c) != nil { return PlannedStep(action: "window_button", target: "minimize") }
        if Commands.match(#"^close\s+(?:this\s+|the\s+)?window$"#, c) != nil { return PlannedStep(action: "window_button", target: "close") }
        if let button = windowButton(c, app: app) { return button }
        // Wi-Fi on or off, said any way: "turn off my computer wifi", "turn Wi-Fi off", "disable wifi"
        let wifi = #"(?:the\s+|my\s+)?(?:computer'?s?\s+|mac'?s?\s+|laptop'?s?\s+)?wi-?\s?fi(?:\s+connection)?"#
        if let m = Commands.match("^(?:turn|switch|toggle|set|put)\\s+" + wifi + #"\s+(?:back\s+)?(on|off)$"#, c) ?? Commands.match(#"^(?:turn|switch)\s+(?:back\s+)?(on|off)\s+"# + wifi + "$", c) {
            return PlannedStep(action: "wifi", text: m[1].lowercased())
        }
        if Commands.match("^(?:disable|disconnect|kill|shut\\s+off|stop|cut)\\s+" + wifi + "$", c) != nil || Commands.match(#"^(?:go|take\s+me)\s+offline$"#, c) != nil { return PlannedStep(action: "wifi", text: "off") }
        if Commands.match("^(?:enable|connect|start|reconnect)\\s+" + wifi + "$", c) != nil || Commands.match(#"^(?:go|get)\s+(?:back\s+)?online$"#, c) != nil { return PlannedStep(action: "wifi", text: "on") }
        for (pattern, keys) in shortcuts where Commands.match(pattern, c) != nil { return PlannedStep(action: "key", keys: keys) }
        // a folder, by its name or its path
        if let m = Commands.match(#"^(?:open|show|reveal|go\s+to|take\s+me\s+to)\s+(?:the\s+folder\s+|folder\s+)?(.+)$"#, c), let folder = Places.folder(m[1]) {
            return PlannedStep(action: "reveal", target: folder)
        }
        // a pane of System Settings, by its name (each way of saying it is tried in turn)
        let opens = #"(?:open|show|go\s+to|bring\s+up|take\s+me\s+to)"#
        let paneForms = [
            "^" + opens + #"\s+(?:the\s+|my\s+)?(.+?)\s+(?:system\s+)?(?:settings|preferences|prefs)(?:\s+pane)?$"#,
            "^" + opens + #"\s+(?:the\s+)?(.+?)\s+(?:pane\s+|section\s+)?(?:in|of|under)\s+(?:the\s+)?(?:system\s+)?(?:settings|preferences)$"#,
            "^" + opens + #"\s+(?:the\s+)?(?:system\s+)?(?:settings|preferences)\s*(?:>|→|:|,|\bfor\b|\bto\b)\s*(?:the\s+)?(.+?)(?:\s+(?:pane|section|tab))?$"#,
            #"^(?:go\s+to|select|choose)\s+(?:the\s+)?(.+?)(?:\s+(?:pane|section|tab))?$"#,
        ]
        for (i, form) in paneForms.enumerated() {
            guard let m = Commands.match(form, c), let pane = Places.pane(m[1]) else { continue }
            // the last form does not say "settings": there an app of exactly that name wins
            if i == paneForms.count - 1, let name = app(m[1]), name.lowercased() == AppNames.bare(m[1]) { continue }
            return PlannedStep(action: "open_url", url: pane.url)
        }
        if let m = Commands.match(#"^(?:put|place|arrange|tile|show|open)\s+(.+?)\s+and\s+(.+?)\s+side\s+by\s+side$"#, c)
            ?? Commands.match(#"^(?:put|place|move)\s+(.+?)\s+on\s+the\s+left\s+and\s+(.+?)\s+on\s+the\s+right$"#, c)
            ?? Commands.match(#"^(.+?)\s+and\s+(.+?)\s+side\s+by\s+side$"#, c),
           let left = app(m[1]), let right = app(m[2]) {
            return PlannedStep(action: "side_by_side", app: left, target: right)
        }
        let window = #"(?:this\s+window|the\s+window|this|it)"#
        if let m = Commands.match("^(?:move|put|snap|send)\\s+" + window + "\\s+(?:to|on)\\s+the\\s+(left|right)(?:\\s+half|\\s+side)?(?:\\s+of\\s+the\\s+screen)?$", c) {
            return PlannedStep(action: "window", direction: m[1].lowercased())
        }
        if Commands.match("^(?:cent(?:er|re))\\s+" + window + "(?:\\s+on\\s+(?:the\\s+)?screen)?$", c) != nil
            || Commands.match("^(?:move|put)\\s+" + window + "\\s+(?:to|in)\\s+the\\s+(?:cent(?:er|re)|middle)(?:\\s+of\\s+the\\s+screen)?$", c) != nil {
            return PlannedStep(action: "window", direction: "center")
        }
        if Commands.match("^(?:maximi[sz]e|fill\\s+the\\s+screen\\s+with|make\\s+full\\s+size)\\s+" + window + "$", c) != nil
            || Commands.match("^make\\s+" + window + "\\s+(?:fill\\s+the\\s+screen|as\\s+big\\s+as\\s+(?:possible|the\\s+screen)|bigger)$", c) != nil {
            return PlannedStep(action: "window", direction: "full")
        }
        if let look = appearance(c) { return look }
        if screenshot(c) { return PlannedStep(action: "key", keys: ["cmd", "shift", "3"]) }
        if let m = Commands.match(#"^(?:set|turn|put)\s+(?:the\s+)?volume\s+(?:to|at)\s+(\d{1,3})\s*%?$"#, c), let n = Int(m[1]) {
            return PlannedStep(action: "volume", text: "\(min(max(n, 0), 100))")
        }
        if let m = Commands.match(#"^(mute|unmute)(?:\s+(?:the\s+)?(?:sound|volume|mac|computer|audio))?$"#, c) {
            return PlannedStep(action: "volume", text: m[1].lowercased())
        }
        if let m = Commands.match(#"^(?:turn|make)\s+(?:the\s+volume|it|the\s+sound)\s+(up|down|louder|quieter)$"#, c) ?? Commands.match(#"^(?:turn\s+)?(?:the\s+)?volume\s+(up|down)$"#, c)
            ?? Commands.match(#"^turn\s+(up|down)\s+the\s+volume$"#, c) {
            let d = m[1].lowercased()
            return PlannedStep(action: "volume", text: d == "up" || d == "louder" ? "up" : "down")
        }
        if let folder = newFolder(c) { return folder }
        if let show = presentation(c) { return show }
        if let captions = captionedVideo(c) { return captions }
        if let video = playedVideo(c) { return video }
        if let note = writtenNote(c) { return note }
        if let file = fileStep(c) { return file }
        if let dock = dock(c) { return dock }
        if let m = Commands.match(#"^(?:add|create|make|schedule|put)\s+(?:an?\s+)?(?:new\s+)?(?:calendar\s+)?(meeting|event|appointment|call|lunch|dinner)\s*(.*)$"#, c) {
            return PlannedStep(action: "calendar_event", target: m[1].lowercased(), text: m[2])
        }
        return nil
    }

    /// "make a new folder named Taxes inside my Documents folder", "create a folder in Downloads
    /// called Demo", "make a new folder" (on the desktop). The place may be a named folder or a
    /// path; a place that is neither leaves the request to the planner.
    static func newFolder(_ c: String) -> PlannedStep? {
        let make = #"^(?:make|create|add)\s+(?:a\s+|an\s+)?(?:new\s+)?(?:empty\s+)?folder"#
        let at = #"(?:on|in|inside|within|under|at|to)"#
        let called = #"(?:called|named|titled)"#
        var name = "", place = ""
        // the place said first: "On the Desktop, make a new folder named Trip Photos"
        if let m = Commands.match(#"^(?:on|in|inside|within)\s+(?:the\s+|my\s+)?(.+?),?\s+((?:make|create|add)\s+.+)$"#, c),
           let folder = Places.folder(m[1]) ?? Places.folder(m[1] + " folder"),
           let inner = newFolder(m[2]), inner.target == "desktop" {
            return PlannedStep(action: "new_folder", target: folder, text: inner.text)
        }
        if let m = Commands.match(make + "\\s+" + called + #"\s+"?(.+?)"?\s+"# + at + #"\s+(?:of\s+)?(.+)$"#, c) { (name, place) = (m[1], m[2]) }
        else if let m = Commands.match(make + "\\s+" + at + #"\s+(?:of\s+)?(.+?)\s+"# + called + #"\s+"?(.+?)"?$"#, c) { (name, place) = (m[2], m[1]) }
        else if let m = Commands.match(make + "\\s+" + called + #"\s+"?(.+?)"?$"#, c) { name = m[1] }
        else if let m = Commands.match(make + "\\s+" + at + #"\s+(?:of\s+)?(.+)$"#, c) { place = m[1] }
        else if Commands.match(#"^(?:make|create|add)\s+(?:a\s+)?new\s+(?:empty\s+)?folder$"#, c) == nil { return nil }
        var target = "desktop"
        if !place.isEmpty {
            guard let folder = Places.folder(place) ?? Places.folder(place + " folder") else { return nil }
            target = folder
        }
        name = name.trimmingCharacters(in: CharacterSet.whitespaces.union(CharacterSet(charactersIn: "\"'")))
        if name.contains("/") || name.count > 80 { return nil }
        return PlannedStep(action: "new_folder", target: target, text: name.isEmpty ? "New Folder" : name)
    }

    /// Renaming or moving a named file in a named folder: done through the file system and
    /// checked on disk (never over something that is already there). "put the file X inside
    /// it" means the folder a part before made. Anything less definite is left to the planner.
    static func fileStep(_ c: String) -> PlannedStep? {
        let trim = { (s: String) in s.trimmingCharacters(in: CharacterSet.whitespaces.union(CharacterSet(charactersIn: "\"'“”"))) }
        let place = { (s: String) in Places.folder(s) ?? Places.folder(s + " folder") }
        let kind = #"(?:the\s+)?(?:file\s+|folder\s+|document\s+)?(?:called\s+|named\s+)?"#
        if let m = Commands.match("^rename\\s+" + kind + #"(.+?)\s+(?:on|in|inside|from)\s+(?:the\s+|my\s+)?(.+?)\s+(?:to|as)\s+(.+)$"#, c), let folder = place(m[2]) {
            let from = trim(m[1]), to = trim(m[3])
            guard !from.isEmpty, !to.isEmpty, !from.contains("/"), !to.contains("/") else { return nil }
            return PlannedStep(action: "rename_file", app: folder, target: from, text: to)
        }
        if let m = Commands.match("^rename\\s+" + kind + #"(.+?)\s+(?:to|as)\s+(.+?)\s+(?:on|in|inside)\s+(?:the\s+|my\s+)?(.+)$"#, c), let folder = place(m[3]) {
            let from = trim(m[1]), to = trim(m[2])
            guard !from.isEmpty, !to.isEmpty, !from.contains("/"), !to.contains("/") else { return nil }
            return PlannedStep(action: "rename_file", app: folder, target: from, text: to)
        }
        let moves = #"^(?:move|put|drag|place)\s+"#
        let isFile = { (name: String, clause: String) in
            Commands.match(#"\.\p{L}[\p{L}\p{N}]{1,4}$"#, name) != nil || Commands.match(#"\b(?:file|document)\b"#, clause) != nil
        }
        // "Delete notes.txt from the Desktop", "Throw away notes.txt that is on my Desktop": to the Trash
        if let m = Commands.match("^(?:delete|trash|throw\\s+away|bin)\\s+" + kind + #"(.+?)\s+(?:from|on|in|that\s+is\s+(?:on|in))\s+(?:the\s+|my\s+)?(.+)$"#, c),
           let folder = place(m[2]) {
            let name = trim(m[1])
            return isFile(name, c) && !name.contains("/") ? PlannedStep(action: "move_file", app: folder, target: name, text: "Trash") : nil
        }
        if let m = Commands.match(moves + kind + #"(.+?)\s+(?:inside|into|in|to)\s+it$"#, c) {
            let name = trim(m[1])
            return isFile(name, c) && !name.contains("/") ? PlannedStep(action: "move_file", app: "", target: name, text: "it") : nil
        }
        if let m = Commands.match(moves + kind + #"(.+?)\s+(?:on|in|from)\s+(?:the\s+|my\s+)?(.+?)\s+(?:into|inside|in|to)\s+(?:the\s+|my\s+)?(.+?)(?:\s+folder)?$"#, c),
           let folder = place(m[2]) {
            let name = trim(m[1]), to = trim(m[3])
            guard isFile(name, c), !name.contains("/"), !to.isEmpty, !to.contains("/") else { return nil }
            return PlannedStep(action: "move_file", app: folder, target: name, text: to)
        }
        return nil
    }

    /// Arithmetic with Calculator named ("Open Calculator and compute 25 * 4"): the app is
    /// opened and the keys of the sum are pressed, then =. Only whole sums of numbers.
    static func calculation(_ request: String) -> PlannedStep? {
        var t = Commands.unquoted(request).lowercased()
        guard Commands.match(#"\bcalculator\b"#, t) != nil else { return nil }
        for (word, sign) in [("multiplied by", "*"), ("times", "*"), ("×", "*"), ("divided by", "/"), ("÷", "/"), ("plus", "+"), ("minus", "-")] {
            t = t.replacingOccurrences(of: word, with: sign)
        }
        let number = #"\d+(?:\.\d+)?"#
        guard let m = Commands.match("(?<![\\d.])(" + number + "(?:\\s*[-+*/x]\\s*" + number + ")+)(?![\\d.])", t) else { return nil }
        let sum = m[1].replacingOccurrences(of: "x", with: "*").replacingOccurrences(of: " ", with: "")
        return Arithmetic.value(sum) == nil ? nil : PlannedStep(action: "calculate", text: sum)
    }

    /// Dark or light appearance, however it is asked for: any order to switch that names dark
    /// or light mode (or appearance, or theme). Planned instead, a model goes looking in
    /// System Settings and on macOS 26 picks "Dark" under the icon style. Not a question, not
    /// a request about the settings pane, and not text to write somewhere.
    static func appearance(_ c: String) -> PlannedStep? {
        var t = Commands.unquoted(c).lowercased().replacingOccurrences(of: "’", with: "'")
        // "Enable Dark Mode in settings" says where the switch is, not that the pane is wanted
        if let m = Commands.match(#"^(.*?)\s+(?:in|from|using|through|via)\s+(?:the\s+)?(?:system\s+)?(?:settings|preferences)\s*$"#, t) { t = m[1] }
        guard Commands.match(#"\b(?:dark|light|night)\s+(?:mode|appearance|theme|look)\b|\b(?:appearance|theme|look|mode)\s+(?:to|as)\s+(?:dark|light)\b"#, t) != nil else { return nil }
        if Commands.match(#"\b(?:settings|preferences|pane|wallpaper|icons?|widgets?|notes?|write|type|search|google|remind|e-?mail|message|website|about|called|named|saying)\b"#, t) != nil { return nil }
        guard Commands.match(#"^(?:(?:i\s+want|i'd\s+like|i\s+would\s+like|let's|lets)\s+(?:to\s+)?)?(?:turn|switch|set|change|make|use|enable|disable|activate|deactivate|toggle|put|go|give|bring|flip|get|leave|exit|stop|start|apply|try|have|take|move)\b"#, t) != nil,
              t.split(separator: " ").count <= 14 else { return nil }
        let pointed = Commands.match(#"\b(?:to|into|in|on)\s+(?:the\s+)?(dark|light|night)\b"#, t)
        if pointed == nil, Commands.match(#"^(?:toggle|flip)\b"#, t) != nil { return PlannedStep(action: "appearance", text: "toggle") }
        guard var wanted = (pointed ?? Commands.match(#"\b(dark|light|night)\s+(?:mode|appearance|theme|look)\b"#, t))?[1] else { return nil }
        if wanted == "night" { wanted = "dark" }
        let away = Commands.match(#"\b(?:off|disable|deactivate|leave|exit|stop|remove|quit|out\s+of|rid\s+of|no\s+more|don't|do\s+not|without|away\s+from)\b"#, t) != nil
        if away { wanted = wanted == "dark" ? "light" : "dark" }
        return PlannedStep(action: "appearance", text: wanted)
    }

    /// A picture of the whole screen: the system's own shortcut, command-shift-3.
    static func screenshot(_ c: String) -> Bool {
        let whole = #"(?:\s+of\s+(?:the\s+|my\s+)?(?:whole\s+|entire\s+|full\s+)?(?:screen|display|desktop))?"#
        let shot = #"(?:full[\s-]?screen\s+|full\s+|whole[\s-]?screen\s+|entire[\s-]?screen\s+)?(?:screenshot|screen\s+shot|screen\s+capture)"#
        return Commands.match("^(?:take|grab|capture|make|snap)\\s+(?:a\\s+|an\\s+)?" + shot + whole + "$", c) != nil
            || Commands.match(#"^(?:screenshot|capture)\s+(?:the\s+|my\s+)?(?:whole\s+|entire\s+|full\s+)?(?:screen|display|desktop)$"#, c) != nil
            || Commands.match("^(?:press|use|hit|do)\\s+the\\s+(?:keyboard\\s+)?shortcut\\s+(?:that\\s+takes|for|for\\s+taking|to\\s+take)\\s+(?:a\\s+|an\\s+)?" + shot + whole + "$", c) != nil
    }

    /// The Dock's plain settings: hiding, position, size, magnification.
    static func dock(_ c: String) -> PlannedStep? {
        guard c.lowercased().contains("dock") else { return nil }
        if let exact = dockExact(c) { return exact }
        // Said another way ("Move the Dock back to the bottom of the screen", "Enlarge the Dock
        // icons"): an order about the Dock that names a side, a size, hiding or magnification.
        let t = Commands.unquoted(c).lowercased().replacingOccurrences(of: "’", with: "'")
        guard Commands.match(#"^(?:move|put|place|set|position|bring|return|send|pin|change|switch|keep|have|make|enlarge|grow|increase|shrink|reduce|decrease|turn|enable|disable|stop|start|hide|show|magnify|let|get|auto)"#, t) != nil,
              t.split(separator: " ").count <= 14,
              Commands.match(#"\b(?:settings|preferences|pane|add|remove|delete|app|icon\s+of|from\s+the\s+dock|in\s+the\s+dock|to\s+the\s+dock)\b"#, t) == nil else { return nil }
        let step = { (what: String, value: String) in PlannedStep(action: "dock", target: what, text: value) }
        let no = Commands.match(#"\b(?:off|disable|stop|no|never|don't|do\s+not|without|remove)\b"#, t) != nil
        if Commands.match(#"\bmagnif\w*\b"#, t) != nil { return step("magnification", no ? "off" : "on") }
        if Commands.match(#"\b(?:auto[\s-]?hid\w*|hide|hiding|hidden)\b"#, t) != nil {
            let shown = no || Commands.match(#"\b(?:always\s+show|keep\s+showing|visible|stay)\b"#, t) != nil
            return step("autohide", shown ? "off" : "on")
        }
        let sides = ["left", "right", "bottom"].filter { Commands.match("\\b" + $0 + "\\b", t) != nil }
        if sides.count == 1 { return step("position", sides[0]) }
        if Commands.match(#"\b(?:bigger|larger|enlarge|grow|increase|big|large)\b"#, t) != nil { return step("size", "bigger") }
        if Commands.match(#"\b(?:smaller|shrink|reduce|decrease|small|tiny)\b"#, t) != nil { return step("size", "smaller") }
        return nil
    }

    static func dockExact(_ c: String) -> PlannedStep? {
        let step = { (what: String, value: String) in PlannedStep(action: "dock", target: what, text: value) }
        let the = #"(?:the\s+)?"#
        if Commands.match("^(?:turn\\s+on|enable|switch\\s+on)\\s+" + the + #"dock(?:'s)?\s+auto(?:matic)?[\s-]?hid(?:e|ing)$"#, c) != nil
            || Commands.match("^(?:automatically\\s+hide|auto[\\s-]?hide|hide)\\s+" + the + #"dock(?:\s+automatically)?$"#, c) != nil
            || Commands.match("^(?:make|set)\\s+" + the + #"dock\s+(?:to\s+)?(?:auto[\s-]?hide|hide\s+automatically|hide\s+itself)$"#, c) != nil
            || Commands.match(#"^(?:turn\s+on|enable)\s+automatically\s+hide\s+and\s+show\s+the\s+dock$"#, c) != nil { return step("autohide", "on") }
        if Commands.match("^(?:turn\\s+off|disable|switch\\s+off)\\s+" + the + #"dock(?:'s)?\s+auto(?:matic)?[\s-]?hid(?:e|ing)$"#, c) != nil
            || Commands.match("^(?:stop\\s+hiding|always\\s+show|keep\\s+showing|don'?t\\s+hide|show)\\s+" + the + #"dock(?:\s+always|\s+all\s+the\s+time)?$"#, c) != nil
            || Commands.match(#"^(?:turn\s+off|disable)\s+automatically\s+hide\s+and\s+show\s+the\s+dock$"#, c) != nil { return step("autohide", "off") }
        if let m = Commands.match("^(?:move|put|place|set|position)\\s+" + the + #"dock\s+(?:to|on|at)\s+(?:the\s+)?(left|right|bottom)(?:\s+(?:side|edge))?(?:\s+of\s+the\s+screen)?$"#, c)
            ?? Commands.match("^set\\s+" + the + #"dock(?:'s)?\s+position\s+to\s+(?:the\s+)?(left|right|bottom)$"#, c) { return step("position", m[1].lowercased()) }
        if let m = Commands.match("^make\\s+" + the + #"dock\s+(bigger|larger|smaller)$"#, c) { return step("size", m[1].lowercased() == "smaller" ? "smaller" : "bigger") }
        if let m = Commands.match("^set\\s+" + the + #"dock(?:'s)?\s+size\s+to\s+(small|medium|large|\d{1,3})\s*%?$"#, c) { return step("size", m[1].lowercased()) }
        if let m = Commands.match(#"^(?:turn|switch)\s+(on|off)\s+"# + the + #"dock(?:'s)?\s+magnification$"#, c)
            ?? Commands.match("^(?:turn|switch)\\s+" + the + #"dock(?:'s)?\s+magnification\s+(on|off)$"#, c) { return step("magnification", m[1].lowercased()) }
        if let m = Commands.match(#"^(enable|disable)\s+"# + the + #"dock(?:'s)?\s+magnification$"#, c) { return step("magnification", m[1].lowercased() == "enable" ? "on" : "off") }
        return nil
    }

    /// A direct step as a line of "Done so far", for when the planner takes a request over
    /// after a direct route could not finish it.
    public static func doneLine(_ step: PlannedStep) -> String {
        switch step.action {
        case "side_by_side": return "windows of \(step.app ?? "") and \(step.target ?? "") side by side"
        case "window": return "window \(step.direction ?? "")"
        case "appearance": return "dark mode \(step.text == "dark" ? "on" : step.text == "light" ? "off" : "switched")"
        case "volume": return "volume \(step.text ?? "")"
        case "new_folder": return "new folder \"\(step.text ?? "")\" in \(step.target ?? "")"
        case "reveal": return "open folder \(step.target ?? "")"
        case "calendar_event": return "calendar event \(step.target ?? "") \(step.text ?? "")"
        case "dock": return "Dock \(step.target ?? "") \(step.text ?? "")"
        case "rename_file": return "rename \(step.target ?? "") to \(step.text ?? "")" + ((step.app ?? "").isEmpty ? "" : " in \(step.app ?? "")")
        case "move_file": return "move \(step.target ?? "") " + (step.text == "Trash" ? "to the Trash" : "into \(step.text == "it" ? "the folder made before" : step.text ?? "")")
        case "calculate": return "Calculator \(step.text ?? "") ="
        case "wifi": return "Wi-Fi turned \(step.text ?? "off")"
        case "present": return "open the presentation"
        case "window_button": return "\(step.target == "zoom" ? "full screen" : step.target ?? "") the " + ((step.app ?? "").isEmpty ? "window" : "\(step.app ?? "") window")
        case "caption_video": return "subtitles put on the newest recording"
        case "play_video": return "play the video" + ((step.target ?? "").isEmpty ? "" : " in \(step.target ?? "")")
        case "write_note": return "new note \"\(noteTitle(step.target ?? ""))\" written"
        case Recipes.draftEmail: return "email draft to \(step.target ?? "")"
        default: return Planner.doneLine(step, control: nil)
        }
    }

    /// A direct step in a few words, for the person watching and for the log; nil for a step
    /// that is not one of these.
    public static func caption(_ step: PlannedStep) -> String? {
        switch step.action {
        case "side_by_side": return "Putting \(step.app ?? "") and \(step.target ?? "") side by side"
        case "window":
            if step.direction == "full" { return "Making the window fill the screen" }
            return step.direction == "center" ? "Centring the window" : "Moving the window to the \(step.direction ?? "left")"
        case "appearance": return step.text == "toggle" ? "Switching dark mode" : "Switching to \(step.text ?? "dark") mode"
        case "volume":
            switch step.text ?? "" {
            case "mute": return "Muting the sound"
            case "unmute": return "Turning the sound back on"
            case "up": return "Turning the volume up"
            case "down": return "Turning the volume down"
            default: return "Setting the volume to \(step.text ?? "")%"
            }
        case "new_folder": return "Making a folder called \(step.text ?? "New Folder")"
        case "reveal":
            let target = step.target ?? ""
            return target.hasPrefix("~") || target.hasPrefix("/") ? "Opening \(target)" : "Opening the \(target) folder"
        case "calendar_event": return "Making a calendar event"
        case "rename_file": return "Renaming \(step.target ?? "the file")"
        case "move_file": return "Moving \(step.target ?? "the file")"
        case "calculate": return "Working out \(step.text ?? "")"
        case "wifi": return step.text == "on" ? "Turning Wi-Fi on" : "Turning Wi-Fi off"
        case "present": return "Bringing up the presentation"
        case "window_button": return step.target == "close" ? "Closing the window" : step.target == "zoom" ? "Going full screen" : "Minimizing the window"
        case "caption_video": return "Captioning your recording"
        case "play_video": return "Playing the video"
        case "write_note": return "Writing a note"
        case "dock":
            switch step.target ?? "" {
            case "autohide": return step.text == "on" ? "Making the Dock hide itself" : "Keeping the Dock in view"
            case "position": return "Moving the Dock to the \(step.text ?? "bottom")"
            case "magnification": return "Turning Dock magnification \(step.text ?? "on")"
            default: return "Changing the Dock's size"
            }
        default: return nil
        }
    }

    /// A calendar file with one event of an hour, which the Calendar app offers to add when it
    /// is opened. Times are written as local time.
    public static func calendarFile(title: String, start: Date, calendar: Calendar = .current) -> String {
        let f = DateFormatter()
        f.calendar = calendar
        f.timeZone = calendar.timeZone
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyyMMdd'T'HHmmss"
        let end = start.addingTimeInterval(3600)
        let safe = title.replacingOccurrences(of: "\n", with: " ").replacingOccurrences(of: ",", with: "\\,").replacingOccurrences(of: ";", with: "\\;")
        return ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Bonsai assistant//EN", "BEGIN:VEVENT",
                "UID:\(f.string(from: start))-\(title.utf8.reduce(0) { ($0 &* 31 &+ Int($1)) % 1_000_000_007 })@bonsai-assistant", "DTSTAMP:\(f.string(from: start))",
                "DTSTART:\(f.string(from: start))", "DTEND:\(f.string(from: end))", "SUMMARY:\(safe)", "END:VEVENT", "END:VCALENDAR"].joined(separator: "\r\n") + "\r\n"
    }

    /// Whether the words a date was read from really say when: a number, or a word for a day
    /// or a time of day. (A date detector also reads times into words such as "lunch".)
    public static func saysWhen(_ phrase: String) -> Bool {
        Commands.match(#"\d|\b(?:today|tonight|tomorrow|noon|midnight|morning|afternoon|evening|night|next|this|mon|tue|wed|thu|fri|sat|sun)\w*\b"#, phrase) != nil
    }

    /// When an event with no day or time in the request starts: the next full hour.
    public static func nextHour(after now: Date, calendar: Calendar = .current) -> Date {
        let hour = calendar.dateInterval(of: .hour, for: now)?.start ?? now
        return hour.addingTimeInterval(3600)
    }

    /// The title of an event from what followed "meeting" in the request, without its time words.
    public static func eventTitle(kind: String, rest: String, datePhrase: String) -> String {
        var t = rest.trimmingCharacters(in: CharacterSet.whitespaces.union(CharacterSet(charactersIn: ":,-–")))
        if !datePhrase.isEmpty { t = t.replacingOccurrences(of: datePhrase, with: " ", options: .caseInsensitive) }
        for filler in ["to my calendar", "to the calendar", "in my calendar", "in the calendar", "on my calendar"] {
            t = t.replacingOccurrences(of: filler, with: " ", options: .caseInsensitive)
        }
        t = t.trimmingCharacters(in: .whitespaces)
        while let m = Commands.match(#"^(?:called|named|titled|about|for|with|on|at)\s+(.*)$"#, t), m[1] != t { t = m[1].trimmingCharacters(in: .whitespaces) }
        while let m = Commands.match(#"^(.*?)\s+(?:for|at|on|to)$"#, t) { t = m[1].trimmingCharacters(in: .whitespaces) }
        t = t.trimmingCharacters(in: CharacterSet.whitespaces.union(CharacterSet(charactersIn: "\"")))
        let word = kind.prefix(1).uppercased() + kind.dropFirst()
        if t.isEmpty { return word }
        return Commands.match(#"^(?:with)\b"#, rest.trimmingCharacters(in: .whitespaces)) != nil ? "\(word) with \(t)" : t.prefix(1).uppercased() + t.dropFirst()
    }
}

/// Answering a question about the screen in words (and aloud), rather than by pointing.
public enum Answers {
    public static let system = "You are a helpful assistant that can see the user's Mac. Answer the question in one or two short, plain sentences. "
        + "Use the facts and the list of the front window's controls you are given. "
        + "If they do not hold the answer, reply with the single word LOOK and nothing else."

    /// A question that asks where something is, or how to do something: answered by pointing.
    public static func asksWhere(_ question: String) -> Bool {
        Commands.match(#"^(?:where|which\s+(?:one|button|icon|menu|tab|key)|show\s+me|point\s+(?:at|to|out)|find|locate|highlight|how\s+(?:do|can|would|should)\s+(?:i|you|we|one))\b"#,
                       question.trimmingCharacters(in: .whitespaces)) != nil
    }

    /// A request to be told something that is not worded as a question ("explain this error").
    public static func asksToBeTold(_ request: String) -> Bool {
        Commands.match(#"^(?:please\s+)?(?:explain|describe|tell\s+me|read|summari[sz]e)\b"#, request.trimmingCharacters(in: .whitespaces)) != nil
    }

    /// A question about something only a look at the screen can answer (a chart, a picture, an
    /// error on a page): the list of controls is not asked first.
    public static func needsScreen(_ question: String) -> Bool {
        Commands.match(#"\b(?:chart|graph|plot|picture|image|photo|diagram|drawing|map|video|colou?r|error|warning|looking\s+at|on\s+(?:the|my)\s+screen|this\s+(?:page|article|window|screen|say|mean))\b"#, question) != nil
    }

    /// The user message of a question asked from text alone.
    public static func user(facts: String, app: String, window: String, controls: [ListedControl], previous: (question: String, answer: String)?, question: String) -> String {
        var lines = ["Facts: " + facts, "App: " + (app.isEmpty ? "(none)" : app), "Window: " + (window.isEmpty ? "(untitled)" : window), "Controls:"]
        if controls.isEmpty { lines.append("(none listed)") } else { lines.append(contentsOf: controls.map(Planner.line)) }
        lines.append("")
        if let previous {
            lines.append("Earlier question: " + previous.question)
            lines.append("Earlier answer: " + previous.answer)
        }
        lines.append("Question: " + question.trimmingCharacters(in: .whitespacesAndNewlines))
        return lines.joined(separator: "\n")
    }

    /// The question as asked of a screenshot.
    public static func fromScreen(app: String, window: String, previous: (question: String, answer: String)?, question: String) -> String {
        var text = "You are looking at the user's Mac screen. Answer in one or two short, plain sentences, without coordinates."
        if !app.isEmpty { text += "\nThe front app is \(app)" + (window.isEmpty ? "." : "; its window is titled \"\(window)\".") }
        if let previous { text += "\nEarlier question: \(previous.question)\nEarlier answer: \(previous.answer)" }
        return text + "\nQuestion: " + question.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Whether the model said the list does not hold the answer.
    public static func wantsLook(_ reply: String) -> Bool {
        let t = reply.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".!\"'")))
        return t.isEmpty || t.uppercased() == "LOOK" || (t.count < 24 && t.uppercased().contains("LOOK"))
    }

    /// The model's words as they are shown and spoken: no thinking, no emphasis marks, no
    /// quotation marks around the whole; on one line unless `keepLines`.
    public static func clean(_ reply: String, keepLines: Bool = false) -> String {
        var t = Parsing.stripThinking(reply).replacingOccurrences(of: "**", with: "")
        if !keepLines {
            t = t.split(whereSeparator: { $0.isNewline }).map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }.joined(separator: " ")
        }
        t = t.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.count >= 2, let first = t.first, let last = t.last, (first == "\"" && last == "\"") || (first == "“" && last == "”") {
            t = String(t.dropFirst().dropLast()).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        return t
    }

    /// How long an answer stays on screen: long enough to read it.
    public static func readingSeconds(_ text: String) -> Double { min(22, max(6, 3 + Double(text.count) / 13)) }
}

/// Talking back: a question is answered in words. What the Mac knows for certain it says
/// itself (Wi-Fi, the battery, the time); anything else about what is on the screen goes to
/// the planner with the list of controls (the items of a menu or of the Dock when the
/// question is about one), and the sentence it gives with `done` is the answer.
public enum Talk {
    /// Things the Mac can say about itself with no model.
    public enum Fact: Equatable { case wifi, internet, battery, time, date, appearance, volume }

    public static func fact(_ question: String) -> Fact? {
        let t = Commands.unquoted(question).lowercased().replacingOccurrences(of: "’", with: "'")
        let has = { (pattern: String) in Commands.match(pattern, t) != nil }
        if has(#"\b(?:is|are)\b.*\bwi[\s-]?fi\b.*\b(?:on|off|enabled|disabled|turned|working)\b"#) { return .wifi }
        if has(#"\b(?:am\s+i|are\s+we|is\s+(?:the|this|my)\s+(?:mac|computer|laptop))\s+(?:online|offline|connected)\b|\bconnected\s+to\s+the\s+internet\b|\b(?:is\s+there|do\s+i\s+have|do\s+we\s+have)\s+(?:the\s+|an?\s+)?internet\b"#) { return .internet }
        if has(#"\bbattery\b|\bhow\s+much\s+(?:charge|power)\b|\bis\s+(?:it|the\s+mac|my\s+mac|this\s+mac)\s+(?:charging|plugged\s+in)\b"#) { return .battery }
        if has(#"\bwhat\s+time\b|\bwhat(?:'s|\s+is)\s+the\s+time\b"#) { return .time }
        if has(#"\bwhat(?:'s|\s+is)\s+(?:the\s+|today's\s+)?(?:date|day)\b|\bwhat\s+day\b|\bwhat(?:'s|\s+is)\s+today\b"#) { return .date }
        if has(#"\b(?:is|am\s+i\s+in|are\s+we\s+in)\b.*\b(?:dark|light)\s+mode\b"#) { return .appearance }
        if has(#"\b(?:what(?:'s|\s+is)|how\s+(?:high|loud)\s+is)\s+(?:the\s+)?volume\b|\bis\s+(?:the\s+)?(?:sound|volume|mac|computer)\s+(?:muted|on\s+mute)\b|\bhow\s+loud\b"#) { return .volume }
        return nil
    }

    /// The menu a question is about: its name in lower case ("file"); "" for "this menu" or
    /// the menu bar; nil when the question is not about a menu.
    public static func menu(_ question: String) -> String? {
        let t = Commands.unquoted(question).lowercased()
        if let m = Commands.match(#"\b([\p{L}]+)\s+menu\b"#, t) {
            let unnamed: Set<String> = ["this", "the", "that", "a", "my", "current", "open", "which", "what", "main", "any", "each", "every", "whole",
                                        "dropdown", "popup", "context", "in", "on", "of"]
            return unnamed.contains(m[1]) ? "" : m[1]
        }
        return Commands.match(#"\bmenus?\b"#, t) != nil ? "" : nil
    }

    public static func asksDock(_ question: String) -> Bool {
        Commands.match(#"\bdock\b"#, Commands.unquoted(question)) != nil
    }

    /// What to do with the planner's reply to a question.
    public enum Outcome: Equatable {
        case say(String)             // its sentence is the answer
        case look                    // it needs to see the screen: answered from a screenshot
        case point                   // it set off to do something: nothing is done; the thing is pointed at
    }

    public static func outcome(step: PlannedStep?, content: String) -> Outcome {
        if let step {
            if step.action == "done" {
                let text = Answers.clean(step.text ?? "")
                return text.isEmpty ? .look : .say(text)
            }
            return step.action == "look" ? .look : .point
        }
        let text = Answers.clean(content)                 // plain words where a call was expected are an answer too
        if text.isEmpty || text.hasPrefix("{") || text.contains("<function") || text.contains("<tool_call") || text.contains("next_step") { return .look }
        return .say(text)
    }
}

/// A step in a few words for the person watching: "Opening Mail", "Typing in Search". This is
/// only what the box beside the pointer shows; what the planner is told about a finished step
/// is `Planner.doneLine`, which is part of the frozen format.
public enum Captions {
    public static func step(_ step: PlannedStep, control: ListedControl?) -> String {
        if let direct = Skills.caption(step) { return direct }
        var name = control.map { $0.name.isEmpty ? "the \($0.role)" : $0.name } ?? (step.target ?? "")
        if name.count > 34 { name = String(name.prefix(32)) + "…" }
        let on = name.isEmpty ? "" : " \(name)"
        switch step.action {
        case "click": return "Clicking" + on
        case "double_click": return "Double-clicking" + on
        case "right_click": return "Right-clicking" + on
        case "type": return name.isEmpty ? "Typing" : "Typing in \(name)"
        case "key": return "Pressing " + step.keys.joined(separator: "+")
        case "scroll": return "Scrolling \(step.direction ?? "down")"
        case "open_app": return "Opening \(step.app ?? "")"
        case "open_url":
            let url = step.url ?? ""
            if url.lowercased().hasPrefix("mailto:") { return "Opening an email draft" }
            if url.lowercased().hasPrefix(Places.settingsScheme) { return "Opening " + (Places.pane(ofLink: url).map { "\($0.name) settings" } ?? "System Settings") }
            return "Opening a page"
        case "menu": return "Choosing \(step.path ?? "")"
        case "look": return "Looking for \(name.isEmpty ? "it" : name)"
        case "drag": return "Dragging" + on
        case Recipes.draftEmail: return "Drafting an email"
        default: return "Done"
        }
    }
}

/// Which of the server's models the app uses when none was picked in its menu.
public enum ModelChoice {
    /// A model trained to plan steps with next_step (it also points): "planner" or "orch" in its name.
    public static func isPlanner(_ id: String) -> Bool {
        let s = id.lowercased()
        return s.contains("bonsai") && (s.contains("planner") || s.contains("-orch") || s.contains("orchestrat"))
    }

    /// A model trained only to point.
    public static func isPointer(_ id: String) -> Bool {
        let s = id.lowercased()
        return s.contains("bonsai") && !isPlanner(id) && ["point", "tuned", "action"].contains { s.contains($0) }
    }

    /// The planner first, then a pointer, then a Bonsai as shipped; within each the 9B before
    /// the 4B; an MLX pack last (LM Studio's MLX runtime cannot switch thinking off).
    public static func best(of list: [String]) -> String? {
        let lower = { (s: String) in s.lowercased() }
        return list.first { isPlanner($0) && lower($0).contains("9b") } ?? list.first { isPlanner($0) }
            ?? list.first { isPointer($0) && lower($0).contains("9b") } ?? list.first { isPointer($0) && lower($0).contains("4b") } ?? list.first { isPointer($0) }
            ?? list.first { lower($0).contains("bonsai") && lower($0).contains("9b") && !lower($0).contains("mlx") }
            ?? list.first { lower($0).contains("bonsai") } ?? list.first
    }
}

/// What a request becomes.
public enum Route: Equatable {
    case point                       // show where it is
    case answer(screen: Bool)        // say it in words; `screen`: straight from the screenshot
    case text(TextSkill)             // work on the selected text
    case direct([PlannedStep])       // no model: apps, links, windows, switches, folders, events
    case scripted([Step])            // the request spells its clicks and typing out
    case plan                        // the model plans, one step at a time
}

public enum Router {
    /// The whole request as steps that need no planning, when every part of it is one: a
    /// no-model skill (windows, dark mode, the volume, a folder, a calendar event) or one of
    /// the plain recipes (an app, a site, a web search, an email draft). Nil otherwise.
    public static func direct(_ request: String, app: (String) -> String?) -> [PlannedStep]? {
        // "On the Desktop, make a new folder named Trip Photos": the place comes first, and the
        // comma is not where one request ends and the next begins
        let whole = Skills.stripped(request)
        if Commands.match(#"^(?:on|in|inside|within)\s"#, whole) != nil, Commands.clauses(whole).count <= 2, let folder = Skills.newFolder(whole) {
            return [folder]
        }
        if let sum = Skills.calculation(whole) { return [sum] }
        if Commands.clauses(whole).count <= 2, let file = Skills.fileStep(whole) { return [file] }      // a comma inside it is not a break
        var all: [PlannedStep] = []
        for said in Commands.clauses(request) {
            // "Put the Dock on the left side and make it hide automatically": it is the Dock
            var clause = said
            if all.last?.action == "dock", Commands.match(#"\bdock\b"#, clause) == nil, let m = Commands.match(#"^(.*?)\bit\b(.*)$"#, clause) {
                clause = m[1] + "the Dock" + m[2]
            }
            if let steps = Skills.appSettings(clause, app: app) {
                all += steps
            } else if let step = Skills.siteInBrowser(clause, app: app) {
                all.append(step)
            } else if let step = Skills.direct(clause, app: app) {
                all.append(step)
            } else if let steps = Recipes.steps(of: clause, app: app) {
                all += steps
            } else if let m = Commands.match(#"^(?:open|go\s+to|visit|browse\s+to|take\s+me\s+to|show|launch)\s+(.+)$"#, Skills.stripped(clause)),
                      let site = Places.site(named: m[1]) {
                all.append(PlannedStep(action: "open_url", url: site))               // a site by its name, when no app is called that
            } else {
                return nil
            }
        }
        return all.isEmpty ? nil : all
    }

    /// What was said, without the name it was said to ("Clicky, bring up the presentation",
    /// "hey Bonsai open Notes"): with a key held there is no need for a name, but people say one.
    public static func addressed(_ heard: String) -> String {
        let t = heard.trimmingCharacters(in: .whitespacesAndNewlines)
        let name = #"(?:clicky|clickie|clickey|klicky|cliquey|click-y|click\s+e|bonsai|bonzai)"#
        if let m = Commands.match("^(?:(?:hey|hi|ok|okay|yo|so)[,\\s]+)?" + name + "[,.:;!]*\\s+(.+)$", t), m[1].count > 1 { return m[1] }
        return t
    }

    /// The parts a request is carried out in, one after another, each as a request of its own
    /// (so that each can take a direct route): it is cut only where it says one thing comes
    /// after another ("then", "after that", ";"), and only when the whole of it would otherwise
    /// go to the planner. One part: the request as it is.
    public static func parts(_ request: String, app: (String) -> String?) -> [String] {
        guard route(request, app: app) == .plan else { return [request] }
        let parts = Commands.parts(request)
        return parts.count > 1 ? parts : [request]
    }

    /// Whether a later part speaks of something an earlier part made or opened ("put the file
    /// inside it"): such a part is told what was done before it.
    /// `apps`: with the apps of this Mac given, a part that speaks of no app and no place of
    /// its own ("press Return", "another one called Submit report") refers back too.
    public static func refersBack(_ part: String, apps: [String] = []) -> Bool {
        let t = Commands.unquoted(part)
        if Commands.match(#"\b(?:another|one\s+more|also|again|it|them|there|the\s+same|(?:that|this)\s+(?:folder|file|note|window|page|one|app|site|event|reminder|contact|document|tab|list))\b"#, t) != nil {
            return true
        }
        guard !apps.isEmpty else { return false }
        let hasPlace = Commands.match(#"\b(?:desktop|documents|downloads|applications|pictures|movies|trash|folder|file|site|website|page|web)\b|[~/]|\.\p{L}{2,4}\b"#, t) != nil
        return !hasPlace && AppNames.named(in: part, among: apps).isEmpty
    }

    /// What the planner is given as the task for a part that refers back: the part, and the
    /// parts before it in the request's own words.
    public static func task(_ part: String, earlier: [String]) -> String {
        earlier.isEmpty ? part : "\(part) (earlier in the same request: \"\(earlier.joined(separator: ", then "))\")"
    }

    /// One word for how a request is carried out, for a batch run's log.
    public static func kind(_ route: Route) -> String {
        switch route {
        case .point: return "point"
        case .answer: return "answer"
        case .text: return "selected text"
        case .direct: return "direct"
        case .scripted: return "spelled out"
        case .plan: return "planned"
        }
    }

    /// `showOnly`: never act, only point. `app` resolves a name someone might say to an app on this Mac.
    public static func route(_ request: String, showOnly: Bool = false, app: (String) -> String?) -> Route {
        if showOnly { return .point }
        if let steps = direct(request, app: app) { return .direct(steps) }
        if let skill = Skills.text(request) { return .text(skill) }
        if (Commands.isQuestion(request) && !Commands.isPoliteOrder(request)) || Answers.asksToBeTold(request) {
            return Answers.asksWhere(request) ? .point : .answer(screen: Answers.needsScreen(request))
        }
        if let spelled = Commands.plan(request) { return .scripted(spelled) }
        return .plan
    }
}
