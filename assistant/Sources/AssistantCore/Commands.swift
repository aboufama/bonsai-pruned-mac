import Foundation

/// A request that spells its steps out ("click the search field, then type "apple" and press
/// enter", "drag the file to the Trash") needs no planning: each part names what to do and the
/// model only has to find the thing on the screen. This reads such requests into steps. A request
/// it cannot read this way ("turn on dark mode") is left to the model to plan.
public enum Commands {
    static func match(_ pattern: String, _ text: String) -> [String]? {
        guard let re = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]) else { return nil }
        let ns = text as NSString
        guard let m = re.firstMatch(in: text, range: NSRange(location: 0, length: ns.length)) else { return nil }
        return (0..<m.numberOfRanges).map { m.range(at: $0).location == NSNotFound ? "" : ns.substring(with: m.range(at: $0)) }
    }

    static let verbs = "click|double|right|control|type|write|enter|input|press|hit|push|drag|move|scroll|select|choose|pick|open|launch|tap|go to|switch to|close|check|uncheck|toggle|focus"

    /// A question, or a request only to be shown something: answered by pointing, never by acting.
    public static func isQuestion(_ request: String) -> Bool {
        let t = request.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.hasSuffix("?") { return true }
        return match(#"^(?:where|what|which|who|how|why|is|are|does|do|can|could|should|show me|point (?:at|to|out)|find|locate|highlight)\b"#, t) != nil
    }

    /// The parts of a request, split at "then", ";", line ends, sentence ends and at "and"
    /// before another command word. Text inside double quotes is never split.
    public static func clauses(_ request: String) -> [String] {
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
        let pattern = #"\s*,?\s*(?:and\s+)?then\s+|\s*;\s*|\n+|(?<=[.!])\s+(?=\p{L})|\s*,?\s+and\s+(?=(?:"# + verbs + #")\b)|\s*,\s+(?=(?:"# + verbs + #")\b)"#
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
        if let m = match(#"^(?:drag|move)\s+(.+?)\s+(?:over to|on top of|onto|into|to)\s+(.+)$"#, c) {
            return [Step(action: .drag, target: m[1], targetEnd: m[2])]
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
        if let m = match(#"^(?:type|write)\s+(.+?)\s+(?:into|in)\s+(the\s+.+?)"# + submit, c) {
            return [Step(action: .click, target: m[2]), Step(action: .type, text: m[1] + (m[3].isEmpty ? "" : "\n"))]
        }
        // "type in the search bar hello world": where the place ends and the text begins cannot be told; leave it to the model
        if match(#"^(?:type|write)\s+(?:into|inside|in|on)\s+(?:the|my|this|that)\b"#, c) != nil { return nil }
        if let m = match(#"^(?:type|write)\s+(.+?)"# + submit, c) {
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
        if let m = match(#"^(?:click|press|tap|hit|push|select|choose|pick)(?:\s+on)?\s+(.+)$"#, c) {
            return [Step(action: .click, target: m[1])]
        }
        // "open the settings", "close the window": the whole phrase says where to click
        if match(#"^(?:open|launch|go to|switch to|close|check|uncheck|toggle|focus)\s+.+$"#, c) != nil {
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
