import CoreGraphics
import Foundation

/// The planner, format v1 (fixed together with the training side so that a planner trained
/// later sees exactly what the app sends). The model is given the task, the apps on this Mac,
/// the front window's controls as a numbered list, and what has been done so far; it answers
/// with ONE `next_step` call. Most steps need no screenshot at all: apps and links are opened
/// directly, menus are walked through their names, and a control picked by its number is acted
/// on exactly. Only `look` (and a click that names its target in words) reads the screen.

/// One control of the list. Only `id`, `role`, `name` and `value` are shown to the model.
public struct ListedControl: Equatable {
    public let id: Int
    public let role: String          // button, text field, checkbox, radio, popup, link, tab, menu item, menu …
    public let name: String
    public let value: String         // a field's or pop-up's text; "selected" for a ticked checkbox or radio; "" otherwise
    public let frame: CGRect         // on the screen, origin top left

    public init(id: Int, role: String, name: String, value: String = "", frame: CGRect = .zero) {
        self.id = id
        self.role = role
        self.name = name
        self.value = value
        self.frame = frame
    }
}

/// One `next_step` call.
public struct PlannedStep: Equatable {
    public var action: String        // open_app, open_url, click, double_click, right_click, type, key, menu, scroll, drag, look, done
    public var app: String?
    public var url: String?
    public var id: Int?
    public var target: String?
    public var targetEnd: String?
    public var text: String?
    public var keys: [String]
    public var path: String?
    public var direction: String?

    public init(action: String, app: String? = nil, url: String? = nil, id: Int? = nil, target: String? = nil, targetEnd: String? = nil,
                text: String? = nil, keys: [String] = [], path: String? = nil, direction: String? = nil) {
        self.action = action
        self.app = app
        self.url = url
        self.id = id
        self.target = target
        self.targetEnd = targetEnd
        self.text = text
        self.keys = keys
        self.path = path
        self.direction = direction
    }
}

public enum Planner {
    public static let maxSteps = 15
    public static let maxControls = 80
    public static let actions = ["open_app", "open_url", "click", "double_click", "right_click", "type", "key", "menu", "scroll", "drag", "look", "done"]

    /// The fixed system text, word for word as agreed for training.
    public static let system = "You operate a Mac for the user, one step at a time. Reply with exactly one next_step call. "
        + "Prefer open_app, open_url, key and menu over clicking. To press or fill a control from the list, give its id. "
        + "Use look only when the control you need is not in the list. When the task is finished, call done with one sentence for the user."

    /// Added for a server that takes no tools, or a model that wrote no call: the same arguments as JSON.
    public static let asJSON = " Write the next_step call as one JSON object with its arguments and nothing else, for example "
        + "{\"action\":\"open_app\",\"app\":\"Mail\"} or {\"action\":\"click\",\"id\":3} or {\"action\":\"key\",\"keys\":\"cmd+n\"} "
        + "or {\"action\":\"done\",\"text\":\"The draft is open.\"}. Actions: " + actions.joined(separator: ", ") + ". "
        + "Other arguments: app, url, id, target, target_end, text, keys, path (for menu, like File > New Message), direction."

    /// The one tool. It extends the `next_step` of docs/ACTION_FORMAT.md.
    public static let tool: [String: Any] = [
        "type": "function",
        "function": [
            "name": "next_step",
            "description": "The next single step on the Mac.",
            "parameters": [
                "type": "object",
                "required": ["action"],
                "properties": [
                    "action": ["type": "string", "enum": actions, "description": "What to do. `done` ends the task."],
                    "app": ["type": "string", "description": "For open_app: the app's name, from Apps. Optional for open_url: the browser to open it in."],
                    "url": ["type": "string", "description": "For open_url: a web address, or a mailto: link to draft an email."],
                    "id": ["type": "number", "description": "A number from Controls: the control to press, or the field to type into."],
                    "target": ["type": "string", "description": "Plain words: what to click when it has no id, where a drag starts, or for look what to find. "
                               + "Say what kind of thing it is, what it says, where it is and what is beside it, "
                               + "for example \"the Today button in the toolbar, between the two arrow buttons\"."],
                    "target_end": ["type": "string", "description": "For drag: where it ends, in plain words."],
                    "text": ["type": "string", "description": "For type: the text; a final newline presses Return. For done: one sentence for the user."],
                    "keys": ["type": "string", "description": "For key: the keys pressed together, like cmd+n."],
                    "path": ["type": "string", "description": "For menu: the path through the menu bar, like File > New Message."],
                    "direction": ["type": "string", "enum": ["up", "down", "left", "right"], "description": "For scroll."],
                ] as [String: Any],
            ] as [String: Any],
        ] as [String: Any],
    ]

    /// One line of Controls: `[3] button "Today"`, `[4] text field "Search" = "current value"`, `[5] radio "Month" selected`.
    public static func line(_ c: ListedControl) -> String {
        var out = "[\(c.id)] \(c.role)"
        if !c.name.isEmpty { out += " \"\(c.name)\"" }
        if c.value == "selected" { out += " selected" } else if !c.value.isEmpty { out += " = \"\(c.value)\"" }
        return out
    }

    /// The user message, rebuilt for every step.
    public static func user(task: String, apps: [String], frontApp: String, window: String, done: [String], controls: [ListedControl]) -> String {
        var lines: [String] = []
        lines.append("Task: " + task.trimmingCharacters(in: .whitespacesAndNewlines))
        lines.append("Apps: " + apps.joined(separator: ", "))
        lines.append("Front app: " + (frontApp.isEmpty ? "none" : frontApp) + " | Window: " + (window.isEmpty ? "none" : window))
        if done.isEmpty {
            lines.append("Done so far: nothing")
        } else {
            lines.append("Done so far:")
            for (i, step) in done.enumerated() { lines.append("\(i + 1). \(step)") }
        }
        if controls.isEmpty {
            lines.append("Controls: none")
        } else {
            lines.append("Controls:")
            for control in controls.prefix(maxControls) { lines.append(line(control)) }
        }
        return lines.joined(separator: "\n")
    }

    static let alias: [String: String] = ["press": "click", "tap": "click", "select": "click", "left_click": "click", "doubleclick": "double_click",
                                          "rightclick": "right_click", "write": "type", "input": "type", "hotkey": "key", "keys": "key",
                                          "launch": "open_app", "open": "open_app", "open_application": "open_app", "browse": "open_url",
                                          "navigate": "open_url", "goto": "open_url", "find": "look", "see": "look", "finish": "done",
                                          "terminate": "done", "stop": "done", "answer": "done"]

    /// The arguments of a `next_step` call in whatever shape it arrived: the API's `tool_calls`,
    /// the Qwen3.5 call as the chat template writes it, or a JSON object in the text.
    static func arguments(content: String, toolCalls: [[String: Any]]) -> [String: Any]? {
        for call in toolCalls {
            if let args = Parsing.stepArguments(call), args["action"] != nil { return args }
        }
        let text = Parsing.stripThinking(content)
        if let m = Parsing.matches(#"<function=next_step>(.*?)(?:</function>|$)"#, text).first {
            var args: [String: Any] = [:]
            for p in Parsing.matches(#"<parameter=([^>\n]+)>(.*?)</parameter>"#, m[1]) {
                var v = p[2]
                if v.hasPrefix("\n") { v.removeFirst() }
                if v.hasSuffix("\n") { v.removeLast() }
                args[p[1].trimmingCharacters(in: .whitespaces)] = v
            }
            if args["action"] != nil { return args }
        }
        for obj in Parsing.jsonObjects(in: text) {
            if let args = Parsing.stepArguments(obj), args["action"] != nil { return args }
        }
        return nil
    }

    /// The step in a model's answer, read leniently; nil when there is none.
    public static func parse(content: String, toolCalls: [[String: Any]] = []) -> PlannedStep? {
        guard let raw = arguments(content: content, toolCalls: toolCalls) else { return nil }
        var action = "\(raw["action"] ?? "")".trimmingCharacters(in: .whitespacesAndNewlines).lowercased().replacingOccurrences(of: " ", with: "_")
        action = alias[action] ?? action
        guard actions.contains(action) else { return nil }
        func text(_ key: String) -> String? {
            guard let v = raw[key], !(v is NSNull) else { return nil }
            let s = (v as? String) ?? "\(v)"
            return s.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : s
        }
        var step = PlannedStep(action: action)
        step.app = text("app")?.trimmingCharacters(in: .whitespacesAndNewlines)
        step.url = text("url")?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let n = raw["id"] as? Int { step.id = n } else if let d = raw["id"] as? Double { step.id = Int(d) }
        else if let s = text("id"), let n = Int(s.trimmingCharacters(in: CharacterSet(charactersIn: "[] \n"))) { step.id = n }
        step.target = text("target")?.trimmingCharacters(in: .whitespacesAndNewlines)
        step.targetEnd = text("target_end")?.trimmingCharacters(in: .whitespacesAndNewlines)
        step.text = text("text")
        step.keys = Keys.names(from: raw["keys"])
        step.path = text("path")?.trimmingCharacters(in: .whitespacesAndNewlines)
        step.direction = text("direction")?.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        if action == "scroll", !["up", "down", "left", "right"].contains(step.direction ?? "") { step.direction = "down" }
        if action == "open_app", step.app == nil { step.app = step.text ?? step.target }          // a name put in the wrong argument
        if action == "open_url", step.url == nil { step.url = step.text ?? step.target }
        return step
    }

    /// Why a step cannot be carried out, or nil when it can.
    public static func problem(_ step: PlannedStep, controls: [ListedControl]) -> String? {
        let listed = { (id: Int) in controls.contains { $0.id == id } }
        switch step.action {
        case "click", "double_click", "right_click":
            if let id = step.id { return listed(id) ? nil : "there is no control \(id) in the list" }
            return (step.target ?? "").isEmpty ? "\(step.action) with neither an id nor a target" : nil
        case "type":
            if (step.text ?? "").isEmpty { return "type without text" }
            if let id = step.id, !listed(id) { return "there is no control \(id) in the list" }
            return nil
        case "key": return Keys.combo(step.keys) == nil ? "key without usable keys" : nil
        case "open_app": return (step.app ?? "").isEmpty ? "open_app without an app" : nil
        case "open_url": return (step.url ?? "").isEmpty ? "open_url without a url" : nil
        case "menu": return (step.path ?? "").isEmpty ? "menu without a path" : nil
        case "look": return (step.target ?? "").isEmpty ? "look without a target" : nil
        case "drag": return (step.id == nil && (step.target ?? "").isEmpty) || (step.targetEnd ?? "").isEmpty ? "drag needs a start and a target_end" : nil
        default: return nil
        }
    }

    /// The line a finished step leaves in "Done so far" (and in the box beside the pointer).
    public static func doneLine(_ step: PlannedStep, control: ListedControl?) -> String {
        let named = control.map { $0.name.isEmpty ? $0.role : "\"\($0.name)\"" } ?? (step.target.map { "\"\($0)\"" } ?? "")
        switch step.action {
        case "open_app": return "open_app \(step.app ?? "")"
        case "open_url": return "open_url \(step.url ?? "")" + (step.app.map { " in \($0)" } ?? "")
        case "click": return "click \(named)"
        case "double_click": return "double_click \(named)"
        case "right_click": return "right_click \(named)"
        case "type":
            let t = step.text ?? ""
            let shown = t.count <= 60 ? t.trimmingCharacters(in: .newlines) : String(t.prefix(57)) + "..."
            return "type \(Step.quoted(shown))" + (named.isEmpty ? "" : " into \(named)") + (t.hasSuffix("\n") ? " and Return" : "")
        case "key": return "key " + step.keys.joined(separator: "+")
        case "menu": return "menu \(step.path ?? "")"
        case "scroll": return "scroll \(step.direction ?? "down")"
        case "drag": return "drag \(named) to \"\(step.targetEnd ?? "")\""
        case "look": return "look \"\(step.target ?? "")\""
        default: return "done"
        }
    }

    /// What the screen looks like as text, for telling whether a step changed anything.
    public static func signature(app: String, window: String, controls: [ListedControl]) -> String {
        app + "\u{1}" + window + "\u{1}" + controls.map { "\($0.role)|\($0.name)|\($0.value)" }.joined(separator: "\u{2}")
    }
}

/// Plain requests that need no planning at all: open an app, open a site, search the web,
/// draft an email. Each part of the request must match one of these, or the planner is asked.
public enum Recipes {
    /// A request for an email draft: who to, what about. Carried out by the app (the model
    /// writes the few lines; nothing is ever sent).
    public static let draftEmail = "draft_email"

    static func site(_ text: String) -> String? {
        let t = text.trimmingCharacters(in: .whitespaces)
        if Commands.match(#"^https?://\S+$"#, t) != nil { return t }
        if Commands.match(#"^(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|io|ai|dev|edu|gov|app|co|uk|us|me|tv)(?:/\S*)?$"#, t) != nil { return "https://" + t }
        return nil
    }

    static func encoded(_ s: String) -> String {
        s.addingPercentEncoding(withAllowedCharacters: CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-._~"))) ?? s
    }

    /// The steps of one part of a request, or nil when it is not one of the plain ones.
    /// `app` resolves a name the user might say ("Brave", "Chrome", "settings") to an app on this Mac.
    public static func steps(of clause: String, app: (String) -> String?) -> [PlannedStep]? {
        var c = clause.trimmingCharacters(in: CharacterSet.whitespacesAndNewlines.union(CharacterSet(charactersIn: ".!")))
        while let m = Commands.match(#"^(?:please|now|next|first|finally|and|also|can you|could you|then)[,\s]+(.+)$"#, c) { c = m[1] }
        if let m = Commands.match(#"^(?:draft|write|compose|start|prepare)\s+(?:an?\s+)?(?:new\s+)?(?:e-?mail|mail|message)\s+to\s+(.+?)\s+(?:about|regarding|on|re:?|saying|asking|telling)\s+(.+)$"#, c) {
            return [PlannedStep(action: draftEmail, target: m[1], text: m[2])]
        }
        if let m = Commands.match(#"^(?:search(?:\s+the\s+web)?(?:\s+for)?|google|look\s+up)\s+(.+)$"#, c) {
            return [PlannedStep(action: "open_url", url: "https://www.google.com/search?q=" + encoded(m[1]))]
        }
        if let m = Commands.match(#"^(?:open|go\s+to|visit|launch|start|switch\s+to|show)\s+(?:the\s+)?(.+?)(?:\s+app)?$"#, c) {
            if let url = site(m[1]) { return [PlannedStep(action: "open_url", url: url)] }
            if let name = app(m[1]) { return [PlannedStep(action: "open_app", app: name)] }
        }
        return nil
    }

    /// The whole request as plain steps, when every part of it is one; nil otherwise.
    public static func plan(_ request: String, app: (String) -> String?) -> [PlannedStep]? {
        var all: [PlannedStep] = []
        for clause in Commands.clauses(request) {
            guard let s = steps(of: clause, app: app) else { return nil }
            all += s
        }
        return all.isEmpty ? nil : all
    }

    /// The link that opens an email draft: a mailto: link for the Mac's mail app, or Gmail's
    /// compose page when a browser was asked for.
    public static func emailLink(to: String, subject: String, body: String, inBrowser: Bool) -> String {
        inBrowser ? "https://mail.google.com/mail/?view=cm&fs=1&to=\(encoded(to))&su=\(encoded(subject))&body=\(encoded(body))"
                  : "mailto:\(encoded(to))?subject=\(encoded(subject))&body=\(encoded(body))"
    }
}
