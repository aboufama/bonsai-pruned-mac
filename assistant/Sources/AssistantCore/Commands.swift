import Foundation

/// A request that spells its steps out ("click the search field, then type "apple" and press
/// enter", "drag the file to the Trash") needs no planning: each part names what to do and the
/// model only has to find the thing on the screen. This reads such requests into steps. A request
/// it cannot read this way ("turn on dark mode", "open Notes and write a note") is left to the
/// direct routes or to the model to plan: every part must be a plain click, typing, key, scroll
/// or drag, or the whole request is not claimed.
public enum Commands {
    static func match(_ pattern: String, _ text: String) -> [String]? {
        guard let re = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]) else { return nil }
        let ns = text as NSString
        guard let m = re.firstMatch(in: text, range: NSRange(location: 0, length: ns.length)) else { return nil }
        return (0..<m.numberOfRanges).map { m.range(at: $0).location == NSNotFound ? "" : ns.substring(with: m.range(at: $0)) }
    }

    static let verbs = "click|double|right|control|type|write|enter|input|press|hit|push|drag|move|scroll|select|choose|pick|open|launch|tap|go to|switch to|close|check|uncheck|toggle|focus|draft|compose|search|google|visit|start|prepare|make|create|add|schedule|turn|set|put|take|mute|unmute"

    /// A question, or a request only to be shown something: answered by pointing, never by acting.
    public static func isQuestion(_ request: String) -> Bool {
        let t = request.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.hasSuffix("?") { return true }
        return match(#"^(?:where|what|which|who|how|why|is|are|does|do|can|could|should|show me|point (?:at|to|out)|find|locate|highlight)\b"#, t) != nil
    }

    /// "Hey, can you open my Photo Booth app?", "Could you minimize this?": an order said
    /// politely, not a question. "Can you see…", "could you tell me…" stay questions.
    public static func isPoliteOrder(_ request: String) -> Bool {
        var t = request.trimmingCharacters(in: .whitespacesAndNewlines)
        while let m = match(#"^(?:hey|hi|hello|ok|okay|so|um|uh|please|clicky|bonsai)\b[\s,!.:-]*(.+)$"#, t) { t = m[1] }
        guard let m = match(#"^(?:can|could|would|will)\s+you\s+(?:please\s+|kindly\s+|just\s+|quickly\s+)?(\p{L}+)"#, t) else { return false }
        let telling = ["see", "tell", "show", "find", "explain", "describe", "read", "say", "hear", "point", "locate", "help", "check", "confirm", "recommend", "suggest", "think", "guess"]
        return !telling.contains(m[1].lowercased())
    }

    /// The parts of a request, split at "then", ";", line ends, sentence ends and at "and"
    /// before another command word. Text inside double quotes is never split.
    public static func clauses(_ request: String) -> [String] {
        let pattern = #"\s*,?\s*(?:and\s+)?then\s+|\s*;\s*|\n+|(?<=[.!])\s+(?=\p{L})|\s*,?\s+and\s+(?=(?:"# + verbs + #")\b)|\s*,\s+(?=(?:"# + verbs + #")\b)"#
        return split(request, at: pattern)
    }

    /// Only the words that say one thing comes after another: "then", "and then", "after that",
    /// "afterwards", and ";".
    static let sequencers = #"(?:\s*[,.]\s*|\s+)(?:and\s+)?(?:then|after\s+that|afterwards?)\b,?\s+|\s*;\s*"#

    /// A request cut where it says one thing comes after another, and nowhere else: each part
    /// is then carried out as a request of its own. Text inside double quotes is never cut.
    public static func parts(_ request: String) -> [String] {
        split(request, at: sequencers).filter { $0.count > 1 }.flatMap(twoThings)
    }

    /// "Add a reminder called Water plants and a calendar event called Coffee with Maya": two
    /// things to make, said with one verb, are two parts with that verb.
    static func twoThings(_ part: String) -> [String] {
        let thing = #"(?:reminder|calendar\s+event|event|note|contact|meeting|appointment|folder)"#
        guard let m = match("^((?:please\\s+)?(?:add|create|make|set\\s+up|schedule))\\s+(an?\\s+(?:new\\s+)?" + thing + "\\b.*?)\\s+and\\s+(an?\\s+(?:new\\s+)?"
                            + thing + "\\b.+)$", part) else { return [part] }
        return ["\(m[1]) \(m[2])", "\(m[1]) \(m[3])"]
    }

    /// The text without what is inside double quotes (for looking at the words of the request
    /// itself, not at what it wants typed).
    public static func unquoted(_ text: String) -> String {
        var out = "", inside = false
        for ch in text {
            if ch == "\"" || ch == "“" || ch == "”" { inside.toggle(); out.append(" ") } else if !inside { out.append(ch) }
        }
        return out
    }

    /// `request` cut at every match of `pattern`, leaving text inside double quotes whole.
    static func split(_ request: String, at pattern: String) -> [String] {
        var quoted: [String] = []
        var masked = ""
        var inside = false
        var current = ""
        for ch in request {
            let isQuote = ch == "\"" || ch == "“" || ch == "”"
            if isQuote {
                if inside {
                    quoted.append(current)
                    masked += "\u{1}\(quoted.count - 1)\u{2}"
                    current = ""
                }
                inside.toggle()
            } else if inside {
                current.append(ch)
            } else {
                masked.append(ch)
            }
        }
        if inside { masked += current }                                    // an opening quote that never closed
        guard let re = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else { return [request] }
        let ns = masked as NSString
        var parts: [String] = []
        var last = 0
        for m in re.matches(in: masked, range: NSRange(location: 0, length: ns.length)) {
            parts.append(ns.substring(with: NSRange(location: last, length: m.range.location - last)))
            last = m.range.location + m.range.length
        }
        parts.append(ns.substring(from: last))
        return parts.map { part in
            var s = part
            for (i, q) in quoted.enumerated() { s = s.replacingOccurrences(of: "\u{1}\(i)\u{2}", with: "\"\(q)\"") }
            return s.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".!,")))
        }.filter { !$0.isEmpty }
    }

    /// One part of a request as steps (typing into a named place is a click, then the typing);
    /// nil when it is not a plain command.
    public static func steps(of clause: String) -> [Step]? {
        var c = clause.trimmingCharacters(in: .whitespacesAndNewlines)
        while let m = match(#"^(?:please|now|next|first|finally|and|also|can you|could you|then)[,\s]+(.+)$"#, c) { c = m[1] }

        if let m = match(#"^scroll\s+(up|down|left|right)(?:\s+(?:a\s+)?(?:bit|little|lot|more))?(?:\s+(?:in|on|inside|within)\s+(.+))?$"#, c) {
            return [Step(action: .scroll, target: m[2].isEmpty ? nil : m[2], direction: m[1].lowercased())]
        }
        if let m = match(#"^(drag|move)\s+(.+?)\s+(?:over to|on top of|onto|into|to)\s+(.+)$"#, c) {
            // "move the Dock back to the bottom of the screen", "move this window to the left":
            // a setting or a layout, not something to pick up and drop
            let moves = m[1].lowercased() == "move"
            if moves, match(#"\b(?:dock|windows?|cursor|pointer|mouse|menu\s+bar)\b|\bback$"#, m[2]) != nil { return nil }
            if moves, match(#"\b(?:left|right|top|bottom|side|edge|corner|cent(?:er|re)|middle|half)\b.*\b(?:screen|display|desktop)\b"#, m[3]) != nil { return nil }
            // a file and a folder: done through the file system or planned, never dragged by words
            if match(#"\bfile\b|\.\p{L}[\p{L}\p{N}]{1,4}\b"#, m[2]) != nil, match(#"\bfolder\b|\bit\b"#, m[3]) != nil { return nil }
            return [Step(action: .drag, target: m[2], targetEnd: m[3])]
        }
        let submit = #"(\s+and\s+(?:press|hit)\s+(?:enter|return)|\s+and\s+(?:submit|send)(?:\s+it)?)?$"#
        // the place first: type in the claude input bar "hello"
        if let m = match(#"^(?:type|write|enter|input)\s+(?:into|inside|in|on)\s+(.+?)\s*[:,]?\s*"(.*?)""# + submit, c) {
            return [Step(action: .click, target: m[1]), Step(action: .type, text: m[2] + (m[3].isEmpty ? "" : "\n"))]
        }
        if let m = match(#"^(?:type|write|enter|input)\s+(?:in\s+|out\s+)?"(.*?)"(?:\s+(?:into|in|on|to)\s+(.+?))?"# + submit, c) {
            let typing = Step(action: .type, text: m[1] + (m[3].isEmpty ? "" : "\n"))
            return m[2].isEmpty ? [typing] : [Step(action: .click, target: m[2]), typing]
        }
        // Without quotation marks only "type" is taken literally: "write a note about…" is a task.
        if let m = match(#"^type\s+(.+?)\s+(?:into|in)\s+(the\s+.+?)"# + submit, c) {
            return [Step(action: .click, target: m[2]), Step(action: .type, text: m[1] + (m[3].isEmpty ? "" : "\n"))]
        }
        // "type in the search bar hello world": where the place ends and the text begins cannot be told; leave it to the model
        if match(#"^(?:type|write)\s+(?:into|inside|in|on)\s+(?:the|my|this|that)\b"#, c) != nil { return nil }
        if let m = match(#"^type\s+(.+?)"# + submit, c) {
            return [Step(action: .type, text: m[1] + (m[2].isEmpty ? "" : "\n"))]
        }
        if let m = match(#"^(?:press|hit|push|use)\s+(?:the\s+)?(.+?)(?:\s+keys?|\s+shortcut)?$"#, c) {
            let names = m[1].replacingOccurrences(of: " and ", with: " ", options: .caseInsensitive)
                .split(whereSeparator: { $0 == "+" || $0 == " " || $0 == "-" }).map(String.init)
            if !names.isEmpty, Keys.combo(names) != nil { return [Step(action: .key, keys: names.map { $0.lowercased() })] }
        }
        if let m = match(#"^double[\s-]?(?:click|tap)(?:\s+on)?\s+(.+)$"#, c) {
            return [Step(action: .double_click, target: m[1])]
        }
        if let m = match(#"^(?:right|control|secondary)[\s-]?click(?:\s+on)?\s+(.+)$"#, c) {
            return [Step(action: .right_click, target: m[1])]
        }
        if let m = match(#"^(click|press|tap|hit|push|select|choose|pick)(?:\s+on)?\s+(.+)$"#, c) {
            // "press the shortcut that takes a full screenshot": keys to work out, not a thing to click
            if ["press", "hit", "push"].contains(m[1].lowercased()),
               match(#"\b(?:shortcut|hot\s?key|keystroke|key\s+combination|keys?)\b"#, m[2]) != nil { return nil }
            return [Step(action: .click, target: m[2])]
        }
        // "close the window", "check the box": the whole phrase says where to click. Not "open …",
        // "launch …", "go to …": those name an app, a place or a task, never one thing to click
        // (taken as a click they landed on whatever the model thought closest).
        if match(#"^(?:close|check|uncheck|toggle|focus)\s+.+$"#, c) != nil {
            return [Step(action: .click, target: c)]
        }
        return nil
    }

    /// The steps a request spells out, when every part of it is a plain command; nil when the
    /// model has to plan.
    public static func plan(_ request: String) -> [Step]? {
        var all: [Step] = []
        for clause in clauses(request) {
            guard let s = steps(of: clause) else { return nil }
            all += s
        }
        return all.isEmpty ? nil : all
    }
}
