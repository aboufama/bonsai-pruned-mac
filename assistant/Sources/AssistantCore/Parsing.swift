import CoreGraphics
import Foundation

/// What a pointing answer turned out to be. Rules as `parse_point` in bench/models.py.
public enum PointAnswer: Equatable {
    case point(CGPoint)          // "[x, y]" on the 0-1000 grid
    case boxCenter(CGPoint)      // four numbers: read as a box and reduced to its centre
    case refusal                 // "[-1,-1]": the model says there is nothing to point at
    case unparseable             // no usable coordinates

    public var point: CGPoint? {
        switch self {
        case .point(let p), .boxCenter(let p): return p
        default: return nil
        }
    }
}

public enum Parsing {
    static func matches(_ pattern: String, _ text: String) -> [[String]] {
        guard let re = try? NSRegularExpression(pattern: pattern, options: [.dotMatchesLineSeparators]) else { return [] }
        let ns = text as NSString
        return re.matches(in: text, range: NSRange(location: 0, length: ns.length)).map { m in
            (0..<m.numberOfRanges).map { m.range(at: $0).location == NSNotFound ? "" : ns.substring(with: m.range(at: $0)) }
        }
    }

    /// The answer without the model's thinking. A thought that was cut off before it closed
    /// leaves nothing: there is no answer after it.
    public static func stripThinking(_ text: String) -> String {
        var t = text
        if let re = try? NSRegularExpression(pattern: "<think>.*?</think>", options: [.dotMatchesLineSeparators]) {
            t = re.stringByReplacingMatches(in: t, range: NSRange(location: 0, length: (t as NSString).length), withTemplate: "")
        }
        if let r = t.range(of: "<think>") { t = String(t[..<r.lowerBound]) }
        if let r = t.range(of: "</think>") { t = String(t[r.upperBound...]) }      // the template opened the thought
        return t.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    static let number = #"(-?\d+(?:\.\d+)?)"#

    public static func parsePoint(_ text: String) -> PointAnswer {
        let t = stripThinking(text)
        func checked(_ x: Double, _ y: Double, box: Bool) -> PointAnswer {
            guard (0...1000).contains(x), (0...1000).contains(y) else { return .unparseable }
            return box ? .boxCenter(CGPoint(x: x, y: y)) : .point(CGPoint(x: x, y: y))
        }
        func values(_ m: [String]) -> [Double] { m.dropFirst().compactMap(Double.init) }

        // the lab's `point` tool call: <parameter=x> 512 </parameter> <parameter=y> 87 </parameter>
        if let m = matches(#"<parameter=x>\s*"# + number + #".*?<parameter=y>\s*"# + number, t).first {
            let v = values(m)
            if v.count == 2 { return v[0] == -1 && v[1] == -1 ? .refusal : checked(v[0], v[1], box: false) }
        }
        let s = #"\s*"#
        let four = #"\["# + s + number + s + "," + s + number + s + "," + s + number + s + "," + s + number + s + #"\]"#
        let pair = #"\["# + s + number + s + "," + s + number + s + #"\]"#
        let box = matches(four, t).first ?? matches(pair + s + "," + s + pair, t).first
        if let m = box {
            let v = values(m)
            if v.count == 4 {
                if v[0] == -1 && v[1] == -1 { return .refusal }
                return checked((v[0] + v[2]) / 2, (v[1] + v[3]) / 2, box: true)
            }
        }
        if let m = matches(pair, t).first {
            let v = values(m)
            if v.count == 2 { return v[0] == -1 && v[1] == -1 ? .refusal : checked(v[0], v[1], box: false) }
        }
        let nums = matches(number, t).compactMap { Double($0[0]) }
        if nums.count == 2 || nums.count == 3 {
            return nums[0] == -1 && nums[1] == -1 ? .refusal : checked(nums[0], nums[1], box: false)
        }
        if nums.count >= 4 {
            if nums[0] == -1 && nums[1] == -1 { return .refusal }
            return checked((nums[0] + nums[2]) / 2, (nums[1] + nums[3]) / 2, box: true)
        }
        return .unparseable
    }

    // MARK: steps

    static let actionNames: [String: Step.Action] = [
        "click": .click, "left_click": .click, "leftclick": .click, "tap": .click, "select": .click, "press_button": .click,
        "double_click": .double_click, "doubleclick": .double_click, "double-click": .double_click,
        "right_click": .right_click, "rightclick": .right_click, "right-click": .right_click,
        "drag": .drag, "left_click_drag": .drag,
        "type": .type, "input": .type, "write": .type, "type_text": .type,
        "key": .key, "press": .key, "hotkey": .key, "keypress": .key,
        "scroll": .scroll, "hscroll": .scroll,
        "done": .done, "terminate": .done, "finish": .done, "finished": .done, "stop": .done, "answer": .done,
    ]

    /// Every JSON object written in `text`, outermost first, found by matching braces.
    static func jsonObjects(in text: String) -> [[String: Any]] {
        var found: [[String: Any]] = []
        let chars = Array(text.utf16)
        var i = 0
        while i < chars.count {
            guard chars[i] == 0x7B else { i += 1; continue }                 // {
            var depth = 0, j = i, inString = false, escaped = false, end = -1
            while j < chars.count {
                let c = chars[j]
                if inString {
                    if escaped { escaped = false } else if c == 0x5C { escaped = true } else if c == 0x22 { inString = false }
                } else if c == 0x22 { inString = true } else if c == 0x7B { depth += 1 } else if c == 0x7D {
                    depth -= 1
                    if depth == 0 { end = j; break }
                }
                j += 1
            }
            if end < 0 { break }
            let piece = String(utf16CodeUnits: Array(chars[i...end]), count: end - i + 1)
            if let d = piece.data(using: .utf8), let obj = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
                found.append(obj)
                i = end + 1
            } else {
                i += 1
            }
        }
        return found
    }

    /// The arguments of a step out of whatever shape the object has.
    static func stepArguments(_ obj: [String: Any]) -> [String: Any]? {
        if let args = obj["arguments"] ?? obj["parameters"] {
            if let d = args as? [String: Any] { return d }
            if let s = args as? String, let d = s.data(using: .utf8),
               let parsed = try? JSONSerialization.jsonObject(with: d) as? [String: Any] { return parsed }
        }
        if let inner = obj["next_step"] as? [String: Any] { return inner }
        if let f = obj["function"] as? [String: Any] { return stepArguments(f) }
        return obj["action"] != nil ? obj : nil
    }

    /// The step in a model answer, read leniently: the API's own `tool_calls`, the Qwen3.5 call
    /// as the chat template writes it (<function=next_step><parameter=...>), or a JSON object
    /// anywhere in the text. Nil when no action can be found.
    public static func parseStep(content: String, toolCalls: [[String: Any]] = []) -> Step? {
        var raw: [String: Any]?
        for call in toolCalls {
            if let args = stepArguments(call), args["action"] != nil { raw = args; break }
        }
        let text = stripThinking(content)
        if raw == nil, let m = matches(#"<function=next_step>(.*?)(?:</function>|$)"#, text).first {
            var args: [String: Any] = [:]
            for p in matches(#"<parameter=([^>\n]+)>(.*?)</parameter>"#, m[1]) {
                var v = p[2]
                if v.hasPrefix("\n") { v.removeFirst() }                     // one newline each side is the template's
                if v.hasSuffix("\n") { v.removeLast() }
                args[p[1].trimmingCharacters(in: .whitespaces)] = v
            }
            if args["action"] != nil { raw = args }
        }
        if raw == nil {
            for obj in jsonObjects(in: text) {
                if let args = stepArguments(obj), args["action"] != nil { raw = args; break }
            }
        }
        guard let raw else { return nil }
        let name = "\(raw["action"] ?? "")".trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            .replacingOccurrences(of: " ", with: "_")
        guard let action = actionNames[name] else { return nil }
        func string(_ k: String) -> String? {
            guard let v = raw[k], !(v is NSNull) else { return nil }
            let s = (v as? String) ?? "\(v)"
            let t = s.trimmingCharacters(in: .whitespacesAndNewlines)
            return t.isEmpty ? nil : t
        }
        var step = Step(action: action, target: string("target"), targetEnd: string("target_end"))
        if let v = raw["text"], !(v is NSNull) { step.text = (v as? String) ?? "\(v)" }     // typed text keeps its newline
        step.keys = Keys.names(from: raw["keys"])
        if let d = string("direction")?.lowercased() { step.direction = d }
        if action == .scroll, step.direction == nil { step.direction = "down" }
        return step
    }
}
