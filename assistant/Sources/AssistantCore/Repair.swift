import Foundation

/// What the app does with a planner's step before carrying it out: puts right what is not in
/// doubt, says exactly what is missing from a step that cannot be used, and keeps count of
/// steps that have no effect so that the planner cannot go round in circles. None of this
/// changes what the planner is sent, except the lines it reads in "Done so far".
public enum Repair {
    /// The step with an unambiguous slip put right, and what was changed (nil: nothing).
    ///  - `open_app`, `open_url`, `look` or `menu` that names nothing but gives the id of a
    ///    listed control: the model had that control in mind, so it is a click on it;
    ///  - a `menu` whose path was written in `text`;
    ///  - a `key` whose keys were written in `text`;
    ///  - a click whose id is not in the list but that also says its target in words;
    ///  - `open_app` with no app, when the task speaks of exactly one app of this Mac and that
    ///    app is not the one in front: that app.
    public static func step(_ step: PlannedStep, controls: [ListedControl], task: String = "", apps: [String] = [],
                            frontApp: String = "") -> (step: PlannedStep, note: String?) {
        let empty = { (s: String?) in (s ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        let listed = { (id: Int?) in id.map { wanted in controls.contains { $0.id == wanted } } ?? false }
        var s = step
        if step.action == "open_app", empty(step.app), !task.isEmpty {
            let named = AppNames.named(in: task, among: apps)
            if named.count == 1, named[0] != frontApp {
                s.app = named[0]
                return (s, "open_app with no app: the task speaks of \(named[0]) and of no other app")
            }
        }
        switch step.action {
        case "open_app" where empty(step.app), "open_url" where empty(step.url), "look" where empty(step.target):
            if listed(step.id) {
                s.action = "click"
                return (s, "\(step.action) with id \(step.id ?? 0) and nothing to open or find: taken as a click on control \(step.id ?? 0)")
            }
        case "menu" where empty(step.path):
            if !empty(step.text) {
                s.path = step.text
                s.text = nil
                return (s, "the menu's path was in text")
            }
            if listed(step.id) {
                s.action = "click"
                return (s, "menu with id \(step.id ?? 0) and no path: taken as a click on control \(step.id ?? 0)")
            }
        case "key" where Keys.combo(step.keys) == nil:
            let names = Keys.names(from: step.text ?? step.target)
            if Keys.combo(names) != nil {
                s.keys = names
                s.text = nil
                return (s, "the keys were in \(empty(step.text) ? "target" : "text")")
            }
        case "click", "double_click", "right_click":
            if step.id != nil, !listed(step.id), !empty(step.target) {
                s.id = nil
                return (s, "there is no control \(step.id ?? 0) in the list: the target in words is used")
            }
        default: break
        }
        return (step, nil)
    }

    /// Apps where a new item is the usual start: when typing goes nowhere in one of them,
    /// command-N is pressed once and the text is typed again.
    public static let newItemApps: Set<String> = ["Notes", "Reminders", "TextEdit", "Contacts", "Calendar", "Stickies"]

    /// Whether the sentence a planner gave with `done` itself says the task is not done: it
    /// says what it still has to do, asks the user something, or gives up.
    public static func unfinished(_ sentence: String) -> Bool {
        let t = sentence.lowercased().replacingOccurrences(of: "’", with: "'")
        let signs = [#"\b(?:now|next|then),?\s+i(?:'ll|\s+will|\s+need|\s+have|\s+must|\s+should|\s+am\s+going)\b"#,
                     #"\bi\s+(?:still\s+)?need\s+to\b"#, #"\bi\s+(?:will|'ll)\s+(?:now|next)\b"#, #"\bnext\s+step\b"#, #"\bstill\s+(?:need|have)\s+to\b"#,
                     #"\b(?:i'm|i\s+am)\s+sorry\b"#, #"\bsorry,"#, #"\bcould\s+you\b"#, #"\bcan\s+you\s+(?:clarify|tell|confirm|provide)\b"#,
                     #"\bplease\s+(?:clarify|provide|tell|confirm|specify)\b"#, #"\bwhat\s+would\s+you\s+like\b"#, #"\bwould\s+you\s+like\s+me\b"#,
                     #"\b(?:is|are|was)\s+not\s+available\b"#, #"\b(?:isn't|aren't)\s+available\b"#, #"\bnot\s+(?:be\s+)?found\b"#,
                     #"\bi\s+(?:don't|do\s+not|can't|cannot|couldn't|could\s+not)\s+(?:see|find|locate)\b"#,
                     #"\bi\s+(?:can't|cannot|am\s+unable|was\s+unable|couldn't|could\s+not)\b"#, #"\bunable\s+to\b"#, #"\bthere\s+is\s+no\b"#]
        return signs.contains { Commands.match($0, t) != nil }
    }

    /// Exactly what is missing from a step that cannot be carried out, for the planner to
    /// read; nil when the step can be carried out.
    public static func missing(_ step: PlannedStep, controls: [ListedControl]) -> String? {
        guard Planner.problem(step, controls: controls) != nil else { return nil }
        let empty = { (s: String?) in (s ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        let range = controls.isEmpty ? "Controls is empty" : "the ids go from 1 to \(controls.count)"
        if let id = step.id, !controls.contains(where: { $0.id == id }), ["click", "double_click", "right_click", "type"].contains(step.action) {
            return "there is no control \(id) in Controls; \(range)"
        }
        switch step.action {
        case "open_app": return "open_app needs the app's name in app"
        case "open_url": return "open_url needs the address in url"
        case "click", "double_click", "right_click": return "\(step.action) needs the id of a control from Controls"
        case "type": return empty(step.text) ? "type needs the text in text" : "type needs the id of a field from Controls; \(range)"
        case "key": return "key needs keys, like cmd+n or return"
        case "menu": return "menu needs the path, like File > New Window"
        case "look": return "look needs a target in words"
        case "drag": return "drag needs where it starts (id or target) and target_end"
        default: return Planner.problem(step, controls: controls)
        }
    }
}

/// Keeps count of steps that had no effect. A planner's commonest failure is to repeat one.
///  - The very same step, right after it changed nothing, is not carried out again.
///  - After three scrolls in a row, a fourth is not carried out.
///  - Once scrolling (or clicking) has changed nothing twice, no more of that kind is carried
///    out until a step of another kind has had an effect.
/// Each refusal is told to the planner; three in a row end the request.
public struct StepBudget {
    public init() {}

    private var lastKey = ""
    private var lastChanged = true
    private var ineffective: [String: Int] = [:]
    private var scrollsInARow = 0
    public private(set) var refusalsInARow = 0

    /// Clicks of every kind and `look` count as one kind of step.
    static func kind(_ action: String) -> String {
        ["click", "double_click", "right_click", "look"].contains(action) ? "click" : action
    }

    static func key(_ s: PlannedStep) -> String {
        var parts: [String] = [s.action, s.id.map { "\($0)" } ?? ""]
        parts.append(s.target ?? "")
        parts.append(s.targetEnd ?? "")
        parts.append(s.text ?? "")
        parts.append(s.keys.joined(separator: "+"))
        parts.append(s.path ?? "")
        parts.append(s.direction ?? "")
        parts.append(s.app ?? "")
        parts.append(s.url ?? "")
        return parts.joined(separator: "\u{1}")
    }

    /// Why this step is not to be carried out, or nil when it is.
    public mutating func refusal(_ step: PlannedStep) -> String? {
        let kind = StepBudget.kind(step.action)
        var why: String?
        if StepBudget.key(step) == lastKey, !lastChanged {
            why = "the same step changed nothing just before; do something different"
        } else if kind == "scroll", scrollsInARow >= 3 {
            why = "scrolled 3 times in a row; press a control from Controls, use menu or key, or look for what you need"
        } else if kind == "scroll" || kind == "click", let n = ineffective[kind], n >= 2 {
            why = "\(kind == "scroll" ? "scrolling" : "clicking") has changed nothing \(n) times; use a different kind of step (key, menu, type, open_app)"
        }
        if why != nil { refusalsInARow += 1 }
        return why
    }

    /// How a step that was carried out went.
    public mutating func record(_ step: PlannedStep, changed: Bool) {
        let kind = StepBudget.kind(step.action)
        lastKey = StepBudget.key(step)
        lastChanged = changed
        refusalsInARow = 0
        scrollsInARow = kind == "scroll" ? scrollsInARow + 1 : 0
        if !changed {
            ineffective[kind, default: 0] += 1
        } else if kind == "scroll" || kind == "click" {
            ineffective[kind] = 0
        } else {
            ineffective = [:]                       // another kind of step had an effect: both may be tried again
        }
    }
}

/// A sum of numbers with + - * /, worked out the way Calculator does (times and divide first).
public enum Arithmetic {
    public static func value(_ sum: String) -> Double? {
        var numbers: [Double] = [], signs: [Character] = []
        var digits = ""
        for ch in sum where ch != " " {
            if ch.isNumber || ch == "." { digits.append(ch); continue }
            guard "+-*/".contains(ch), let n = Double(digits) else { return nil }
            numbers.append(n)
            signs.append(ch)
            digits = ""
        }
        guard let last = Double(digits), !signs.isEmpty else { return nil }
        numbers.append(last)
        var terms = [numbers[0]], adds: [Character] = []
        for (i, sign) in signs.enumerated() {
            let n = numbers[i + 1]
            switch sign {
            case "*": terms[terms.count - 1] *= n
            case "/":
                guard n != 0 else { return nil }
                terms[terms.count - 1] /= n
            default:
                adds.append(sign)
                terms.append(n)
            }
        }
        var total = terms[0]
        for (i, sign) in adds.enumerated() { total += sign == "+" ? terms[i + 1] : -terms[i + 1] }
        return total
    }

    /// The result as Calculator shows it, plain and with thousands separators.
    public static func shown(_ value: Double) -> [String] {
        let rounded = (value * 1e8).rounded() / 1e8
        var plain = rounded == rounded.rounded() && abs(rounded) < 1e15 ? String(Int(rounded)) : String(rounded)
        if plain.hasSuffix(".0") { plain = String(plain.dropLast(2)) }
        let f = NumberFormatter()
        f.locale = Locale(identifier: "en_US")
        f.numberStyle = .decimal
        f.maximumFractionDigits = 8
        let grouped = f.string(from: NSNumber(value: rounded)) ?? plain
        return plain == grouped ? [plain] : [plain, grouped]
    }

    /// The keys that enter the sum, one press each.
    public static func keys(_ sum: String) -> [[String]] {
        sum.filter { $0 != " " }.map { ch -> [String] in
            switch ch {
            case "+": return ["plus"]
            case "-": return ["minus"]
            case "*": return ["shift", "8"]
            case "/": return ["slash"]
            case ".": return ["period"]
            default: return [String(ch)]
            }
        } + [["="]]
    }
}

/// A request that is one command of the menu bar by its name ("Show the status bar in
/// Finder", "choose View > Show Path Bar"): which of the menu's items it means.
public enum MenuCommand {
    static let filler: Set<String> = ["the", "a", "an", "please", "in", "of", "on", "from", "menu", "choose", "select", "click", "use", "pick", "command",
                                      "item", "option", "app", "then", "and", "to", "go"]

    static func words(_ text: String, without extra: Set<String> = []) -> [String] {
        text.lowercased().replacingOccurrences(of: "…", with: "").split(whereSeparator: { !$0.isLetter && !$0.isNumber }).map(String.init)
            .filter { !filler.contains($0) && !extra.contains($0) }
    }

    /// The index of the item the request names, or nil. An item counts when its title has
    /// at least two words, they stand together in the request, and little else is asked for
    /// (the words left over are at most a third of the request, not counting the app's name
    /// and the names of the menus). `titles`: each item's title with its menu ("View", "Show Path Bar").
    public static func match(request: String, items: [(menu: String, title: String)], app: String) -> Int? {
        var extra = Set(words(app))
        for item in items { extra.formUnion(words(item.menu)) }
        let asked = words(Commands.unquoted(request), without: extra)
        guard asked.count >= 2 else { return nil }
        var best: (index: Int, count: Int)?
        for (i, item) in items.enumerated() {
            let title = words(item.title, without: [])
            guard title.count >= 2, title.count <= asked.count, title.count * 3 >= asked.count * 2 else { continue }
            let found = (0...(asked.count - title.count)).contains { start in Array(asked[start..<(start + title.count)]) == title }
            if found, title.count > (best?.count ?? 0) { best = (i, title.count) }
        }
        return best?.index
    }
}
