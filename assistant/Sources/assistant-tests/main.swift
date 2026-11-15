// Checks of the core, run as a plain program:  swift run assistant-tests   (exit code 1 on a failure)
import AssistantCore
import CoreGraphics
import Foundation

var failures = 0
var checks = 0

func check(_ ok: Bool, _ what: String, file: String = #file, line: Int = #line) {
    checks += 1
    if !ok {
        failures += 1
        print("FAIL line \(line): \(what)")
    }
}

func near(_ a: CGPoint, _ b: CGPoint, _ tol: CGFloat = 0.001) -> Bool { abs(a.x - b.x) <= tol && abs(a.y - b.y) <= tol }

// ---------------------------------------------------------------- units
do {
    // 13" M4 MacBook: 1470 x 956 points, shown to the model as 1280 x 832 pixels (the pixel size must not matter)
    let air = CGRect(x: 0, y: 0, width: 1470, height: 956)
    check(near(Geometry.screenPoint(grid: CGPoint(x: 500, y: 500), region: air), CGPoint(x: 735, y: 478)), "centre of the display")
    check(near(Geometry.screenPoint(grid: CGPoint(x: 0, y: 0), region: air), .zero), "top left")
    check(near(Geometry.screenPoint(grid: CGPoint(x: 1000, y: 1000), region: air), CGPoint(x: 1469, y: 955)), "bottom right stays on the display")
    check(near(Geometry.screenPoint(grid: CGPoint(x: 250, y: 100), region: air), CGPoint(x: 367.5, y: 95.6)), "a quarter across")
    check(near(Geometry.screenPoint(grid: CGPoint(x: -20, y: 1200), region: air), CGPoint(x: 0, y: 955)), "answers outside the grid are pulled in")
    // a zoomed look: the image covers a window of the screen that does not start at the origin
    let window = CGRect(x: 400, y: 300, width: 490, height: 318.667)
    check(near(Geometry.screenPoint(grid: CGPoint(x: 500, y: 500), region: window), CGPoint(x: 645, y: 459.3335)), "centre of a zoom window")
    check(near(Geometry.screenPoint(grid: CGPoint(x: 100, y: 900), region: window), CGPoint(x: 449, y: 586.8003)), "inside a zoom window")
    // there and back
    for g in [CGPoint(x: 3, y: 997), CGPoint(x: 512, y: 87), CGPoint(x: 999, y: 1)] {
        let back = Geometry.gridPoint(screen: Geometry.screenPoint(grid: g, region: air), region: air)
        check(near(back, g, 1), "grid -> screen -> grid for \(g)")
    }
    // pixels of the image that was sent
    check(near(Geometry.pixel(grid: CGPoint(x: 500, y: 250), imageWidth: 1280, imageHeight: 832), CGPoint(x: 640, y: 208)), "pixel of the sent image")
    check(near(Geometry.pixel(grid: CGPoint(x: 500, y: 250), imageWidth: 2940, imageHeight: 1912), CGPoint(x: 1470, y: 478)), "pixel of the full capture")
    // a pixel of the capture and a point of the screen are the same place: 2 pixels per point
    let px = Geometry.pixel(grid: CGPoint(x: 333, y: 777), imageWidth: 2940, imageHeight: 1912)
    let pt = Geometry.screenPoint(grid: CGPoint(x: 333, y: 777), region: air)
    check(near(CGPoint(x: px.x / 2, y: px.y / 2), pt), "pixels / scale == points")

    // shrinking
    check(Geometry.fittedSize(width: 2940, height: 1912, longSide: 1280) == (1280, 832), "2940 x 1912 -> 1280 x 832")
    check(Geometry.fittedSize(width: 2560, height: 1664, longSide: 1280) == (1280, 832), "2560 x 1664 -> 1280 x 832")
    check(Geometry.fittedSize(width: 2940, height: 1912, longSide: 896) == (896, 583), "2940 x 1912 -> 896 x 583")
    check(Geometry.fittedSize(width: 1000, height: 600, longSide: 1280) == (1000, 600), "never enlarged")
    check(Geometry.fittedSize(width: 1080, height: 1920, longSide: 1280) == (720, 1280), "portrait")

    // zoom windows
    let z = Geometry.zoomWindow(around: CGPoint(x: 735, y: 478), in: air, zoom: 3)
    check(near(CGPoint(x: z.midX, y: z.midY), CGPoint(x: 735, y: 478)) && abs(z.width - 490) < 0.001, "zoom window centred")
    let corner = Geometry.zoomWindow(around: CGPoint(x: 5, y: 950), in: air, zoom: 3)
    check(abs(corner.minX) < 0.001 && abs(corner.maxY - 956) < 0.001, "zoom window pushed back inside")
    let pr = Geometry.pixelRect(points: z, displayOrigin: .zero, scale: 2)
    check(pr.minX == 980 && pr.width == 980 && pr.minY == 637 && pr.height == 638, "zoom window in whole pixels: \(pr)")
    let back = Geometry.pointsRect(pixels: pr, displayOrigin: .zero, scale: 2)
    check(near(back.origin, CGPoint(x: 490, y: 318.5)) && back.width == 490 && back.height == 319, "the pixels' own region: \(back)")
    // a second display to the left of the main one has negative coordinates
    let left = CGRect(x: -1920, y: 0, width: 1920, height: 1080)
    check(near(Geometry.screenPoint(grid: CGPoint(x: 500, y: 500), region: left), CGPoint(x: -960, y: 540)), "display with a negative origin")
    check(near(Geometry.appKitPoint(quartz: CGPoint(x: 100, y: 56), mainScreenHeight: 956), CGPoint(x: 100, y: 900)), "Quartz to AppKit")
}

// ---------------------------------------------------------------- the pointer's flight
do {
    let s = CGPoint(x: 100, y: 700), t = CGPoint(x: 900, y: 300)
    let path = Flight.points(from: s, to: t)
    check(near(path.first!, s) && near(path.last!, t), "a flight starts at the cursor and lands on the target")
    var travelled: CGFloat = 0
    for i in 1..<path.count { travelled += hypot(path[i].x - path[i - 1].x, path[i].y - path[i - 1].y) }
    let straight = hypot(t.x - s.x, t.y - s.y)
    check(travelled > straight && travelled < straight * 1.08, "a flight is one gentle arc, a little longer than a straight line and with no loop")
    check(near(Flight.position(on: path, at: 0), s) && near(Flight.position(on: path, at: 1), t), "the ends of the way")
    let half = Flight.position(on: path, at: 0.5)
    check(hypot(half.x - s.x, half.y - s.y) > 150 && hypot(half.x - t.x, half.y - t.y) > 150, "half way is in between")
    check(Flight.eased(0) == 0 && Flight.eased(1) == 1 && abs(Flight.eased(0.5) - 0.5) < 0.001, "easing runs from 0 to 1")
}

// ---------------------------------------------------------------- faces
do {
    check(Faces.face(.listening, beat: 3) == "(o_o)" && Faces.face(.listening, beat: 15) == "(-_-)" && Faces.face(.listening, beat: 16) == "(o_o)", "listening blinks once every sixteen beats")
    check(Faces.face(.thinking, beat: 0) == Faces.face(.thinking, beat: 7) && Faces.face(.thinking, beat: 8) != Faces.face(.thinking, beat: 0), "thinking changes its face every eight beats")
    check((0..<200).allSatisfy { Faces.face(.thinking, beat: $0) == Faces.face(.thinking, beat: $0) && !Faces.words(.thinking, beat: $0).isEmpty }, "the same beat always gives the same face")
    check(Faces.face(.done) == "\\(^o^)/" && Faces.face(.sorry) == "(;_;)" && Faces.face(.lost) == "(?_?)", "a face for done, for sorry and for not catching it")
    let all: [Mood] = [.hello, .listening, .heard, .thinking, .acting, .done, .answer, .lost, .sorry]
    check(all.allSatisfy { m in Faces.face(m).unicodeScalars.allSatisfy { $0.isASCII } }, "every face is plain ASCII")
    check(Faces.move(0) != Faces.move(1) && Faces.move(8) == Faces.move(0) && Faces.move(-1) == Faces.moves.last!, "the thinking moves come round in a fixed order")
    check(Faces.typing("") == "(^_^)" && Faces.typing("click") == "(o_o)" && Faces.typing("clic") == "(o_o)" && Faces.typing("where is it?") == "(o_O)", "the typing face is friendly while it waits and steady once you type")
}

// ---------------------------------------------------------------- pointing answers
do {
    check(Parsing.parsePoint("[512, 87]") == .point(CGPoint(x: 512, y: 87)), "[x, y]")
    check(Parsing.parsePoint(" [512,87]\n") == .point(CGPoint(x: 512, y: 87)), "[x,y] with spaces around")
    check(Parsing.parsePoint("[-1,-1]") == .refusal, "refusal")
    check(Parsing.parsePoint("[100, 200, 300, 400]") == .boxCenter(CGPoint(x: 200, y: 300)), "a box becomes its centre")
    check(Parsing.parsePoint("[100, 200], [300, 400]") == .boxCenter(CGPoint(x: 200, y: 300)), "two corners become the centre")
    check(Parsing.parsePoint("(640, 120)") == .point(CGPoint(x: 640, y: 120)), "round brackets")
    check(Parsing.parsePoint("<think>the 3 buttons at [1, 2]</think>[700, 650]") == .point(CGPoint(x: 700, y: 650)), "thinking is ignored")
    check(Parsing.parsePoint("<think>still thinking about [1, 2]") == .unparseable, "a thought that never ended has no answer")
    check(Parsing.parsePoint("I cannot see it.") == .unparseable, "no numbers")
    check(Parsing.parsePoint("[1500, 20]") == .unparseable, "outside the grid")
    check(Parsing.parsePoint("<tool_call>\n<function=point>\n<parameter=x>\n512\n</parameter>\n<parameter=y>\n87\n</parameter>\n</function>\n</tool_call>")
          == .point(CGPoint(x: 512, y: 87)), "the point tool call")
    check(Parsing.parsePoint("{\"x\": 250.5, \"y\": 40}") == .point(CGPoint(x: 250.5, y: 40)), "JSON x and y")
}

// ---------------------------------------------------------------- steps
do {
    let xml = "<tool_call>\n<function=next_step>\n<parameter=action>\nclick\n</parameter>\n<parameter=target>\nthe \"Done\" button\n</parameter>\n</function>\n</tool_call>"
    check(Parsing.parseStep(content: xml) == Step(action: .click, target: "the \"Done\" button"), "the call as the chat template writes it")

    let drag = "<tool_call>\n<function=next_step>\n<parameter=action>\ndrag\n</parameter>\n<parameter=target>\nthe quality slider\n</parameter>\n<parameter=target_end>\nthe \"Best\" position\n</parameter>\n</function>\n</tool_call>"
    let d = Parsing.parseStep(content: drag)
    check(d?.action == .drag && d?.target == "the quality slider" && d?.targetEnd == "the \"Best\" position", "drag with two targets")

    let api: [[String: Any]] = [["id": "1", "type": "function", "function": ["name": "next_step", "arguments": "{\"action\":\"type\",\"text\":\"hello\\n\",\"target\":\"the search field\"}"]]]
    let t = Parsing.parseStep(content: "", toolCalls: api)
    check(t?.action == .type && t?.text == "hello\n" && t?.target == "the search field", "the API's tool_calls, typed text keeps its newline")

    let fenced = "Here is the step:\n```json\n{\"action\": \"key\", \"keys\": [\"cmd\", \"s\"]}\n```"
    check(Parsing.parseStep(content: fenced)?.keys == ["cmd", "s"], "JSON in a code fence")
    check(Parsing.parseStep(content: "{\"name\": \"next_step\", \"arguments\": {\"action\": \"scroll\", \"direction\": \"Down\"}}")?.direction == "down", "name and arguments")
    check(Parsing.parseStep(content: "{\"action\": \"press\", \"keys\": \"cmd+shift+n\"}")?.keys == ["cmd", "shift", "n"], "keys written as one string")
    check(Parsing.parseStep(content: "{\"action\": \"Double Click\", \"target\": \"the Notes icon\"}")?.action == .double_click, "action names are read leniently")
    let done = Parsing.parseStep(content: "{\"action\": \"done\", \"text\": \"Dark mode is on.\"}")
    check(done?.action == .done && done?.text == "Dark mode is on.", "done with a sentence")
    check(Parsing.parseStep(content: "I would click the button.") == nil, "prose is not a step")
    check(Parsing.parseStep(content: "{\"action\": \"fly\"}") == nil, "an unknown action is not a step")
    check(Parsing.parseStep(content: "{\"note\": \"{}\"} {\"action\": \"click\", \"target\": \"OK\"}")?.target == "OK", "the second object")

    check(Step(action: .click).problem() != nil, "click needs a target")
    check(Step(action: .click, target: "OK").problem() == nil, "click with a target")
    check(Step(action: .drag, target: "a").problem() != nil, "drag needs both ends")
    check(Step(action: .key, keys: ["cmd", "nosuchkey"]).problem() != nil, "unknown key")
    check(Step(action: .type, text: "").problem() != nil, "type needs text")

    check(Step(action: .double_click, target: "the Notes icon").historyLine == "double-click the Notes icon", "history: double-click")
    check(Step(action: .type, target: "the search field", text: "say \"hi\"\n").historyLine == "type \"say \\\"hi\\\"\" in the search field and press Return", "history: type")
    check(Step(action: .key, keys: ["cmd", "s"]).historyLine == "press cmd+s", "history: key")
    check(Step(action: .scroll, direction: "down").historyLine == "scroll down", "history: scroll")
    check(Step(action: .drag, target: "the file", targetEnd: "the Trash").historyLine == "drag the file to the Trash", "history: drag")
}

// ---------------------------------------------------------------- requests that spell out their steps
do {
    check(Commands.plan("press on the calender icon") == [Step(action: .click, target: "the calender icon")], "press on a thing is a click")
    check(Commands.plan("type \"hey its bonsai using my computer\" into the claude input")
          == [Step(action: .click, target: "the claude input"), Step(action: .type, text: "hey its bonsai using my computer")], "typing into a place: click it, then type")
    check(Commands.plan("Click the search field, then type \"apple, then pear\" and press enter")
          == [Step(action: .click, target: "the search field"), Step(action: .type, text: "apple, then pear"), Step(action: .key, keys: ["enter"])],
          "quoted text is not split; press enter is its own step")
    check(Commands.plan("type \"hello\" and press enter") == [Step(action: .type, text: "hello"), Step(action: .key, keys: ["enter"])], "typing, then the key")
    check(Commands.plan("type in the claude input bar \"hello, its the agent\"")
          == [Step(action: .click, target: "the claude input bar"), Step(action: .type, text: "hello, its the agent")], "the place first, then the quoted text")
    check(Commands.plan("type in the search bar hello world") == nil, "place and text run together: left to the model")
    check(Commands.plan("drag the report file to the Trash") == [Step(action: .drag, target: "the report file", targetEnd: "the Trash")], "drag from one thing to another")
    check(Commands.plan("double-click the Notes icon; press cmd+n; type hello world")
          == [Step(action: .double_click, target: "the Notes icon"), Step(action: .key, keys: ["cmd", "n"]), Step(action: .type, text: "hello world")], "three parts")
    check(Commands.plan("press enter") == [Step(action: .key, keys: ["enter"])] && Commands.plan("hit the escape key") == [Step(action: .key, keys: ["escape"])], "keys by name")
    check(Commands.plan("press command and s") == [Step(action: .key, keys: ["command", "s"])], "a combination in words")
    check(Commands.plan("scroll down in the sidebar") == [Step(action: .scroll, target: "the sidebar", direction: "down")], "scroll in a place")
    check(Commands.plan("right click the desktop and click New Folder") == [Step(action: .right_click, target: "the desktop"), Step(action: .click, target: "New Folder")], "and before another command")
    check(Commands.plan("close the Claude window") == [Step(action: .click, target: "close the Claude window")], "close: the whole phrase is the target")
    check(Commands.plan("open the settings") == nil && Commands.plan("Open the Keyboard settings") == nil && Commands.plan("Open a new Finder window") == nil
          && Commands.plan("Open a Finder window at Applications") == nil && Commands.plan("Open Notes and write a note: buy milk") == nil
          && Commands.plan("Open Calendar and make a new event: lunch") == nil && Commands.plan("go to the store page") == nil
          && Commands.plan("write a note about the meeting") == nil, "a request that starts with open, or is a task, is never one click")
    check(Commands.plan("click the search field, then type \"apple\" and press enter") != nil && Commands.plan("type hello into the message box") != nil
          && Commands.plan("write \"hello\" in the search field") != nil, "plain clicks and typing are still read")
    check(Commands.plan("Please click the Save button.") == [Step(action: .click, target: "the Save button")], "politeness and a full stop")
    check(Commands.plan("turn on dark mode") == nil && Commands.plan("click Save then make it pretty") == nil, "anything else is left to the model to plan")
    check(Commands.isQuestion("where do I turn on dark mode?") && Commands.isQuestion("show me the search field") && !Commands.isQuestion("click the search field"), "questions are shown, commands are done")
    check(Commands.plan("click the search field")?.allSatisfy { $0.problem() == nil } == true, "the steps are usable as they are")
}

// ---------------------------------------------------------------- names of controls
do {
    check(Labels.fit(target: "the Today button", name: "Today") == 1, "the Today button is the control named Today")
    check(Labels.fit(target: "Today", name: "") == 0 && Labels.fit(target: "Today", name: "Go to next week") == 0, "an unnamed arrow or another name does not fit")
    check(Labels.fit(target: "Calendar icon in dock", name: "Calendar") > 0 && Labels.fit(target: "Calendar icon in dock", name: "Calendar") < 1, "a name within the target fits, less than a whole match")
    check(Labels.fit(target: "Save", name: "Save As…") > 0 && Labels.fit(target: "Save", name: "Save") > Labels.fit(target: "Save", name: "Save As…"), "the closer name fits better")
    check(Labels.phrase("The Today button") == "today" && Labels.phrase("New Event") == "new event", "phrases are compared without filler words")
}

// ---------------------------------------------------------------- the planner, format v1
do {
    let list = [ListedControl(id: 3, role: "button", name: "Today"), ListedControl(id: 4, role: "text field", name: "Search", value: "current value"),
                ListedControl(id: 5, role: "radio", name: "Month", value: "selected")]
    check(Planner.line(list[0]) == "[3] button \"Today\"" && Planner.line(list[1]) == "[4] text field \"Search\" = \"current value\""
          && Planner.line(list[2]) == "[5] radio \"Month\" selected", "the three kinds of control line")
    let user = Planner.user(task: "open Brave and draft an email", apps: ["Finder", "Brave Browser", "Mail"], frontApp: "Finder", window: "Documents",
                            done: ["open_app Brave Browser", "click \"Compose\""], controls: list)
    check(user == "Task: open Brave and draft an email\nApps: Finder, Brave Browser, Mail\nFront app: Finder | Window: Documents\n"
          + "Done so far:\n1. open_app Brave Browser\n2. click \"Compose\"\nControls:\n[3] button \"Today\"\n[4] text field \"Search\" = \"current value\"\n[5] radio \"Month\" selected", "the user message, line for line")
    check(Planner.user(task: "x", apps: [], frontApp: "", window: "", done: [], controls: []).hasSuffix("Front app: none | Window: none\nDone so far: nothing\nControls: none"), "nothing done, nothing listed")
    check(Planner.system.hasPrefix("You operate a Mac for the user, one step at a time. Reply with exactly one next_step call.") && Planner.system.hasSuffix("call done with one sentence for the user."), "the system text")
    check((try? JSONSerialization.data(withJSONObject: Planner.tool)) != nil, "the tool is valid JSON")

    let call: [[String: Any]] = [["type": "function", "function": ["name": "next_step", "arguments": "{\"action\":\"open_app\",\"app\":\"Brave Browser\"}"]]]
    check(Planner.parse(content: "", toolCalls: call) == PlannedStep(action: "open_app", app: "Brave Browser"), "a call from the API's tool_calls")
    let xml = "<tool_call>\n<function=next_step>\n<parameter=action>\nmenu\n</parameter>\n<parameter=path>\nFile > New Message\n</parameter>\n</function>\n</tool_call>"
    check(Planner.parse(content: xml) == PlannedStep(action: "menu", path: "File > New Message"), "a call as the chat template writes it")
    check(Planner.parse(content: "{\"action\":\"click\",\"id\":3}") == PlannedStep(action: "click", id: 3)
          && Planner.parse(content: "{\"action\":\"type\",\"text\":\"Lunch\\n\",\"id\":\"[4]\"}") == PlannedStep(action: "type", id: 4, text: "Lunch\n"), "JSON, and an id written as [4]")
    check(Planner.parse(content: "{\"action\":\"key\",\"keys\":\"cmd+n\"}")?.keys == ["cmd", "n"] && Planner.parse(content: "{\"action\":\"open\",\"text\":\"Mail\"}") == PlannedStep(action: "open_app", app: "Mail", text: "Mail"), "keys as cmd+n; a name in the wrong argument")
    check(Planner.parse(content: "{\"action\":\"fly\"}") == nil && Planner.parse(content: "no idea") == nil, "anything else is not a step")
    check(Planner.problem(PlannedStep(action: "click", id: 9), controls: list) != nil && Planner.problem(PlannedStep(action: "click", id: 3), controls: list) == nil
          && Planner.problem(PlannedStep(action: "click", target: "the blue arrow"), controls: list) == nil && Planner.problem(PlannedStep(action: "click"), controls: list) != nil, "a click needs a listed id or a target in words")
    check(Planner.doneLine(PlannedStep(action: "open_app", app: "Brave Browser"), control: nil) == "open_app Brave Browser"
          && Planner.doneLine(PlannedStep(action: "click", id: 3), control: list[0]) == "click \"Today\""
          && Planner.doneLine(PlannedStep(action: "type", id: 4, text: "hello"), control: list[1]) == "type \"hello\" into \"Search\""
          && Planner.doneLine(PlannedStep(action: "key", keys: ["cmd", "n"]), control: nil) == "key cmd+n"
          && Planner.doneLine(PlannedStep(action: "menu", path: "File > New Message"), control: nil) == "menu File > New Message", "the lines of Done so far")
    var changed = list
    changed[2] = ListedControl(id: 5, role: "radio", name: "Month")
    check(Planner.signature(app: "Calendar", window: "Calendar", controls: list) != Planner.signature(app: "Calendar", window: "Calendar", controls: changed), "a changed selection is a change")
}

// ---------------------------------------------------------------- plain requests that need no planning
do {
    let apps = ["Brave Browser", "Google Chrome", "Mail", "System Settings", "Calendar"]
    let find = { (said: String) -> String? in
        let s = said.lowercased()
        return apps.first { $0.lowercased() == s } ?? apps.first { $0.lowercased().hasPrefix(s) } ?? (s == "settings" ? "System Settings" : nil)
    }
    check(Recipes.plan("open Brave", app: find) == [PlannedStep(action: "open_app", app: "Brave Browser")], "open an app by the name people say")
    check(Recipes.plan("open the settings app", app: find) == [PlannedStep(action: "open_app", app: "System Settings")], "settings")
    check(Recipes.plan("go to github.com", app: find) == [PlannedStep(action: "open_url", url: "https://github.com")], "open a site")
    check(Recipes.plan("search for ternary neural networks", app: find)?.first?.url == "https://www.google.com/search?q=ternary%20neural%20networks", "search the web")
    check(Recipes.plan("open Brave and draft an email to Sam about the demo on Sunday", app: find)
          == [PlannedStep(action: "open_app", app: "Brave Browser"), PlannedStep(action: Recipes.draftEmail, target: "Sam", text: "the demo on Sunday")], "open a browser, then draft an email")
    check(Recipes.plan("open the report I wrote", app: find) == nil && Recipes.plan("open Brave and book a flight", app: find) == nil, "anything else goes to the planner")
    check(Recipes.emailLink(to: "sam@example.com", subject: "The demo", body: "Hi Sam,\nsee you.", inBrowser: false) == "mailto:sam%40example.com?subject=The%20demo&body=Hi%20Sam%2C%0Asee%20you.", "a mailto link")
    check(Recipes.emailLink(to: "sam@example.com", subject: "Hi", body: "x", inBrowser: true).hasPrefix("https://mail.google.com/mail/?view=cm&fs=1&to=sam%40example.com&su=Hi"), "a compose link for the browser")
}

// ---------------------------------------------------------------- skills
do {
    check(Skills.text("rewrite this more politely")?.instruction == "Rewrite the text in this way: more politely. Keep its meaning." && Skills.text("rewrite this more politely")?.replaces == true, "rewrite the selection")
    check(Skills.text("Translate this to Spanish.")?.instruction == "Translate the text into Spanish." && Skills.text("translate to French")?.replaces == true
          && Skills.text("fix the grammar")?.replaces == true && Skills.text("make this shorter")?.instruction == "Rewrite the text in this way: shorter. Keep its meaning.", "translate, fix the grammar, make it shorter")
    check(Skills.text("summarise this")?.replaces == false && Skills.text("summarize the selection")?.replaces == false && Skills.text("explain this")?.replaces == false, "a summary or an explanation is shown, not pasted")
    check(Skills.text("read this to me")?.instruction == "" && Skills.text("read this aloud")?.replaces == false, "reading the selection aloud needs no model")
    check(Skills.text("click this") == nil && Skills.text("open Mail") == nil && Skills.text("make a new folder") == nil && Skills.text("make it bold") == nil
          && Skills.text("make this window fill the screen") == nil && Skills.text("explain this error") == nil, "other requests are not selection skills")
    check(Skills.prompt(Skills.text("summarise this")!, text: "abc").hasSuffix("Text:\nabc"), "the text follows the instruction")

    let apps = ["Safari", "Notes", "Brave Browser", "Mail", "Calendar", "Home"]
    let find = { (said: String) -> String? in apps.first { $0.lowercased() == said.lowercased() } ?? apps.first { $0.lowercased().hasPrefix(said.lowercased()) } }
    check(Router.direct("put Safari and Notes side by side", app: find) == [PlannedStep(action: "side_by_side", app: "Safari", target: "Notes")]
          && Router.direct("put Mail on the left and Calendar on the right", app: find) == [PlannedStep(action: "side_by_side", app: "Mail", target: "Calendar")]
          && Router.direct("put Safari and Nothing side by side", app: find) == nil, "two apps side by side")
    check(Router.direct("move this window to the left", app: find) == [PlannedStep(action: "window", direction: "left")] && Router.direct("maximize this window", app: find)?.first?.direction == "full"
          && Router.direct("make this bigger", app: find)?.first?.action == "window", "a window to a half, or filling the screen")
    check(Router.direct("turn on dark mode", app: find) == [PlannedStep(action: "appearance", text: "dark")] && Router.direct("turn dark mode off", app: find)?.first?.text == "light"
          && Router.direct("toggle dark mode", app: find)?.first?.text == "toggle" && Router.direct("switch to light mode", app: find)?.first?.text == "light", "dark mode")
    check(Router.direct("set the volume to 30%", app: find) == [PlannedStep(action: "volume", text: "30")] && Router.direct("mute", app: find)?.first?.text == "mute"
          && Router.direct("turn the volume up", app: find)?.first?.text == "up" && Router.direct("set the volume to 300", app: find)?.first?.text == "100", "volume")
    check(Router.direct("make a new folder called Demo on the desktop", app: find) == [PlannedStep(action: "new_folder", target: "desktop", text: "Demo")]
          && Router.direct("create a new folder", app: find)?.first?.text == "New Folder" && Router.direct("open my downloads folder", app: find) == [PlannedStep(action: "reveal", target: "downloads")]
          && Router.direct("open home", app: find) == [PlannedStep(action: "open_app", app: "Home")] && Router.direct("open my home folder", app: find)?.first?.target == "home", "folders")
    check(Router.direct("close this tab", app: find) == [PlannedStep(action: "key", keys: ["cmd", "w"])] && Router.direct("open a new tab", app: find)?.first?.keys == ["cmd", "t"]
          && Router.direct("minimize this window", app: find) == [PlannedStep(action: "window_button", target: "minimize")]
          && Router.direct("close the window", app: find) == [PlannedStep(action: "window_button", target: "close")] && Router.direct("select all", app: find)?.first?.keys == ["cmd", "a"]
          && Router.direct("open Safari and open a new tab", app: find) == [PlannedStep(action: "open_app", app: "Safari"), PlannedStep(action: "key", keys: ["cmd", "t"])]
          && Router.direct("close the Claude window", app: find) == nil && Router.direct("save the report as final", app: find) == nil, "requests that are one shortcut")
    check(Router.direct("minimize the open window", app: find) == [PlannedStep(action: "window_button", target: "minimize")]
          && Router.direct("minimize Safari", app: find) == [PlannedStep(action: "window_button", app: "Safari", target: "minimize")]
          && Router.direct("Could you minimize the Notes window?", app: find) == [PlannedStep(action: "window_button", app: "Notes", target: "minimize")]
          && Router.direct("close the Safari window", app: find) == [PlannedStep(action: "window_button", app: "Safari", target: "close")]
          && Router.direct("close the current window", app: find) == [PlannedStep(action: "window_button", target: "close")]
          && Router.direct("make this full screen", app: find) == [PlannedStep(action: "window_button", target: "zoom")]
          && Router.direct("full screen Safari", app: find) == [PlannedStep(action: "window_button", app: "Safari", target: "zoom")]
          && Router.direct("go full screen", app: find) == [PlannedStep(action: "window_button", target: "zoom")]
          && Router.direct("close this tab", app: find) == [PlannedStep(action: "key", keys: ["cmd", "w"])] && Router.direct("close", app: find) == nil
          && Router.direct("close the report file", app: find) == nil, "a window's own buttons, said any way and for a named app")
    check(Commands.isPoliteOrder("Hey, can you open my photobooth app?") && Commands.isPoliteOrder("Could you open Google Chrome?") && Commands.isPoliteOrder("would you please minimize this")
          && !Commands.isPoliteOrder("Can you see the Trash?") && !Commands.isPoliteOrder("could you tell me what this is?") && !Commands.isPoliteOrder("where is the Trash?")
          && !Commands.isPoliteOrder("open Notes") && !Commands.isPoliteOrder("can you still run without wifi") && !Commands.isPoliteOrder("Can you run without Wi-Fi?")
          && Commands.isPoliteOrder("can you turn off the wifi") && Commands.isPoliteOrder("could you minimize the window") && !Commands.isPoliteOrder("can you hear me?"), "an order said politely is still an order")
    check(Talk.fact("can you still run without wifi") == .offline && Talk.fact("Do you need the internet?") == .offline && Talk.fact("does this work offline?") == .offline
          && Talk.fact("is wifi on?") == .wifi && Talk.fact("turn off wifi") == nil, "a question about running without Wi-Fi is answered, nothing is done")
    check(Router.direct("can you open my email on brave", app: find) == [PlannedStep(action: "open_url", app: "Brave Browser", url: "https://mail.google.com")]
          && AppNames.named(in: "can you check my email on brave", among: ["Mail", "Brave Browser", "Notes"]) == ["Brave Browser"]
          && AppNames.named(in: "send an email to Sam", among: ["Mail", "Brave Browser", "Notes"]) == ["Mail"], "email in a named browser is the web mail, and the browser is the app spoken of")
    check(Router.direct("turn off my computer wifi", app: find) == [PlannedStep(action: "wifi", text: "off")] && Router.direct("Turn Wi-Fi off", app: find) == [PlannedStep(action: "wifi", text: "off")]
          && Router.direct("turn on wifi", app: find) == [PlannedStep(action: "wifi", text: "on")] && Router.direct("disable wi-fi", app: find) == [PlannedStep(action: "wifi", text: "off")]
          && Router.direct("Hey, can you turn off the WiFi please?", app: find) == [PlannedStep(action: "wifi", text: "off")], "Wi-Fi on and off is a tool")
    check(Router.direct("start recording", app: find) == nil && Router.direct("start recording in photobooth", app: find) == nil
          && Router.direct("play the video on my desktop", app: find)?.first?.action == "play_video"
          && AppNames.named(in: "start recording in photobooth", among: ["Photo Booth", "Photos", "Notes"]) == ["Photo Booth"], "starting a recording is not playing a video")
    check(Router.direct("Hey, can you open Safari?", app: find) == [PlannedStep(action: "open_app", app: "Safari")]
          && Router.direct("open Notes please", app: find) == [PlannedStep(action: "open_app", app: "Notes")], "polite words around an order are dropped")
    check(AppNames.resolve("photobooth", names: ["Photo Booth", "Photos", "Safari"]) == "Photo Booth" && AppNames.resolve("my photobooth app", names: ["Photo Booth", "Photos"]) == "Photo Booth"
          && AppNames.resolve("textedit", names: ["TextEdit", "Terminal"]) == "TextEdit" && AppNames.resolve("face time", names: ["FaceTime", "Finder"]) == "FaceTime", "an app's name with its spaces left out or put in")
    check(Skills.shortcuts.allSatisfy { Keys.combo($0.1) != nil }, "every shortcut is a key the app can press")
    check(Router.direct("add a meeting with Sam tomorrow at 3pm", app: find) == [PlannedStep(action: "calendar_event", target: "meeting", text: "with Sam tomorrow at 3pm")], "a calendar event")
    check(Skills.eventTitle(kind: "meeting", rest: "with Sam tomorrow at 3pm", datePhrase: "tomorrow at 3pm") == "Meeting with Sam"
          && Skills.eventTitle(kind: "meeting", rest: "tomorrow at 3pm", datePhrase: "tomorrow at 3pm") == "Meeting"
          && Skills.eventTitle(kind: "event", rest: "called Demo day on Sunday at noon", datePhrase: "Sunday at noon") == "Demo day", "the title of an event")
    var utc = Calendar(identifier: .gregorian)
    utc.timeZone = TimeZone(identifier: "UTC")!
    let ics = Skills.calendarFile(title: "Meeting with Sam", start: Date(timeIntervalSince1970: 1_794_841_200), calendar: utc)
    check(ics.contains("DTSTART:20261116T150000\r\nDTEND:20261116T160000\r\nSUMMARY:Meeting with Sam") && ics.hasPrefix("BEGIN:VCALENDAR") && ics.hasSuffix("END:VCALENDAR\r\n"), "a calendar file of one hour")
    check(Skills.caption(PlannedStep(action: "volume", text: "30")) == "Setting the volume to 30%" && Skills.caption(PlannedStep(action: "side_by_side", app: "Safari", target: "Notes")) == "Putting Safari and Notes side by side"
          && Skills.caption(PlannedStep(action: "open_app", app: "Mail")) == nil, "captions of the direct steps")
    check(Captions.step(PlannedStep(action: "click", id: 3), control: ListedControl(id: 3, role: "button", name: "Today")) == "Clicking Today"
          && Captions.step(PlannedStep(action: "type", id: 2, text: "milk"), control: ListedControl(id: 2, role: "text field", name: "")) == "Typing in the text field"
          && Captions.step(PlannedStep(action: "open_url", url: "mailto:a@b.c"), control: nil) == "Opening an email draft"
          && Captions.step(PlannedStep(action: "look", target: "the Today button in the toolbar, between the two arrow buttons"), control: nil) == "Looking for the Today button in the toolbar,…"
          && Captions.step(PlannedStep(action: "volume", text: "mute"), control: nil) == "Muting the sound", "captions of the steps")

    check(Answers.asksWhere("where is the search field?") && Answers.asksWhere("show me the settings") && Answers.asksWhere("how do I turn on dark mode?")
          && !Answers.asksWhere("is Wi-Fi on?") && !Answers.asksWhere("what's in this menu?"), "where-questions are pointed at, the others are answered")
    check(Answers.wantsLook("LOOK") && Answers.wantsLook(" look. ") && !Answers.wantsLook("Wi-Fi is on.") && !Answers.wantsLook("Look at the top of the window for the toolbar, it holds the buttons."), "LOOK means the list did not hold the answer")
    check(Answers.needsScreen("what does this chart say?") && Answers.needsScreen("what am I looking at?") && Answers.needsScreen("explain this error") && !Answers.needsScreen("is Wi-Fi on?"), "what only a look can answer")
    let q = Answers.user(facts: "Wi-Fi is on.", app: "Finder", window: "Documents", controls: [ListedControl(id: 1, role: "button", name: "Back")],
                         previous: (question: "what is this?", answer: "A Finder window."), question: "and the button?")
    check(q == "Facts: Wi-Fi is on.\nApp: Finder\nWindow: Documents\nControls:\n[1] button \"Back\"\n\nEarlier question: what is this?\nEarlier answer: A Finder window.\nQuestion: and the button?", "a question with the earlier exchange")
    check(Answers.fromScreen(app: "Safari", window: "Sales", previous: nil, question: "what does this chart say?").hasSuffix("The front app is Safari; its window is titled \"Sales\".\nQuestion: what does this chart say?"), "a question asked of the screenshot")
    check(Answers.clean("<think>hm</think>\n\"Wi-Fi is **on**.\"\n") == "Wi-Fi is on." && Answers.clean("a\n\nb", keepLines: true) == "a\n\nb" && Answers.clean("a\n b") == "a b", "an answer as it is shown")
    check(Answers.readingSeconds("ok") == 6 && Answers.readingSeconds(String(repeating: "a", count: 130)) == 13 && Answers.readingSeconds(String(repeating: "a", count: 900)) == 22, "how long an answer stays")

    // the pilot's five requests that were taken as one click: where they go now
    do {
        let route = { (r: String) in Router.route(r, app: find) }
        check(route("Open the Keyboard settings") == .direct([PlannedStep(action: "open_url", url: Places.pane("Keyboard")!.url)])
              && route("Open a new Finder window") == .plan            // no Finder in this list of apps: the planner
              && route("Open a new Safari window") == .direct([PlannedStep(action: "open_app", app: "Safari"), PlannedStep(action: "key", keys: ["cmd", "n"])])
              && route("open a new tab in Safari") == .direct([PlannedStep(action: "open_app", app: "Safari"), PlannedStep(action: "key", keys: ["cmd", "t"])])
              && route("Open a Finder window at Applications") == .direct([PlannedStep(action: "reveal", target: "applications")])
              && route("Open Notes and write a note: buy milk") == .plan && route("Open Calendar and book the dentist") == .plan, "open requests go to a direct route or the planner")
    }

    // folders anywhere, either order; the Dock's plain settings
    check(Router.direct("make a new folder named Taxes inside my Documents folder", app: find) == [PlannedStep(action: "new_folder", target: "documents", text: "Taxes")]
          && Router.direct("create a folder in Downloads called Demo", app: find) == [PlannedStep(action: "new_folder", target: "downloads", text: "Demo")]
          && Router.direct("make a folder called \"Trip photos\" in ~/Pictures/2026", app: find) == [PlannedStep(action: "new_folder", target: "~/Pictures/2026", text: "Trip photos")]
          && Router.direct("make a new folder on the desktop", app: find) == [PlannedStep(action: "new_folder", target: "desktop", text: "New Folder")]
          && Router.direct("make a new folder named Taxes in the garage", app: find) == nil, "a new folder: any place, either order; an unknown place is left to the planner")
    check(Router.direct("turn on Dock auto-hide", app: find) == [PlannedStep(action: "dock", target: "autohide", text: "on")]
          && Router.direct("automatically hide the Dock", app: find)?.first?.text == "on" && Router.direct("stop hiding the Dock", app: find)?.first?.text == "off"
          && Router.direct("move the Dock to the left", app: find) == [PlannedStep(action: "dock", target: "position", text: "left")]
          && Router.direct("put the Dock on the right side of the screen", app: find)?.first?.text == "right"
          && Router.direct("make the Dock bigger", app: find) == [PlannedStep(action: "dock", target: "size", text: "bigger")]
          && Router.direct("set the Dock size to 40%", app: find)?.first?.text == "40"
          && Router.direct("turn off Dock magnification", app: find) == [PlannedStep(action: "dock", target: "magnification", text: "off")]
          && Router.direct("add Safari to the Dock", app: find) == nil, "the Dock's plain settings")
    check(Skills.doneLine(PlannedStep(action: "new_folder", target: "documents", text: "Taxes")) == "new folder \"Taxes\" in documents"
          && Skills.doneLine(PlannedStep(action: "open_app", app: "Calendar")) == "open_app Calendar"
          && Skills.caption(PlannedStep(action: "dock", target: "position", text: "left")) == "Moving the Dock to the left", "a direct step as the planner is told it")

    // a planner's slips put right, what is missing said exactly, and the budget for steps with no effect
    do {
        let list = [ListedControl(id: 1, role: "button", name: "Today"), ListedControl(id: 2, role: "text field", name: "Search")]
        let fixed = Repair.step(PlannedStep(action: "open_app", id: 2), controls: list)
        check(fixed.step == PlannedStep(action: "open_app", id: 2) && fixed.note == nil
              && Repair.step(PlannedStep(action: "open_app", id: 9), controls: list).note == nil
              && Repair.step(PlannedStep(action: "open_app", app: "Mail", id: 2), controls: list).step.action == "open_app", "open_app with an id and no app is a click on that control")
        check(Repair.step(PlannedStep(action: "menu", text: "File > New Window"), controls: list).step == PlannedStep(action: "menu", path: "File > New Window")
              && Repair.step(PlannedStep(action: "key", text: "cmd+n"), controls: list).step.keys == ["cmd", "n"]
              && Repair.step(PlannedStep(action: "click", id: 7, target: "the red button"), controls: list).step == PlannedStep(action: "click", target: "the red button")
              && Repair.step(PlannedStep(action: "click", id: 1), controls: list).note == nil, "a path or keys in the wrong argument; an id that is not listed beside a target in words")
        check(Repair.missing(PlannedStep(action: "open_app"), controls: list) == "open_app needs the app's name in app"
              && Repair.missing(PlannedStep(action: "click", id: 7), controls: list) == "there is no control 7 in Controls; the ids go from 1 to 2"
              && Repair.missing(PlannedStep(action: "type", id: 2), controls: list) == "type needs the text in text"
              && Repair.missing(PlannedStep(action: "click", id: 1), controls: list) == nil && Repair.missing(PlannedStep(action: "done"), controls: list) == nil, "what is missing, said exactly")

        var budget = StepBudget()
        let scroll = PlannedStep(action: "scroll", direction: "down"), click = PlannedStep(action: "click", id: 1)
        check(budget.refusal(scroll) == nil, "a first scroll is carried out")
        budget.record(scroll, changed: false)
        check(budget.refusal(scroll) != nil && budget.refusalsInARow == 1 && budget.refusal(PlannedStep(action: "scroll", direction: "up")) == nil, "the same step right after it changed nothing is refused; another is not")
        budget.record(PlannedStep(action: "scroll", direction: "up"), changed: false)
        check(budget.refusal(PlannedStep(action: "scroll", direction: "left")) != nil && budget.refusal(click) == nil, "scrolling that changed nothing twice: no more scrolling, but a click is fine")
        budget.record(click, changed: true)
        check(budget.refusal(scroll) != nil, "a click that worked does not make scrolling worth trying again")
        budget.record(PlannedStep(action: "key", keys: ["cmd", "f"]), changed: true)
        check(budget.refusal(scroll) == nil, "a step of another kind that had an effect does")
        var run = StepBudget()
        for _ in 0..<3 { run.record(scroll, changed: true) }
        check(run.refusal(scroll) != nil && run.refusal(click) == nil, "three scrolls in a row, even ones that moved: a fourth is refused")
        var twice = StepBudget()
        twice.record(click, changed: false)
        _ = twice.refusal(click); _ = twice.refusal(click)
        check(twice.refusal(click) != nil && twice.refusalsInARow == 3, "three refusals in a row end the request")
    }

    // the window of a second look
    let display = CGRect(x: 0, y: 0, width: 1470, height: 956)
    check(Geometry.squareWindow(around: CGPoint(x: 700, y: 500), in: display, side: 735) == CGRect(x: 332.5, y: 132.5, width: 735, height: 735)
          && Geometry.squareWindow(around: CGPoint(x: 10, y: 950), in: display, side: 735) == CGRect(x: 0, y: 221, width: 735, height: 735)
          && Geometry.squareWindow(around: CGPoint(x: 1465, y: 3), in: display, side: 735) == CGRect(x: 735, y: 0, width: 735, height: 735)
          && Geometry.squareWindow(around: CGPoint(x: 400, y: 100), in: CGRect(x: 0, y: 0, width: 1000, height: 300), side: 500) == CGRect(x: 150, y: 0, width: 500, height: 300), "a square around a point, kept on the screen")
    let cutOut = Geometry.squareWindow(around: CGPoint(x: 10, y: 950), in: display, side: 735)
    let back = Geometry.screenPoint(grid: CGPoint(x: 500, y: 500), region: Geometry.pointsRect(pixels: Geometry.pixelRect(points: cutOut, displayOrigin: .zero, scale: 2), displayOrigin: .zero, scale: 2))
    check(abs(back.x - 367.5) < 0.01 && abs(back.y - 588.5) < 0.01, "an answer on the square maps back to the screen")

    // places: settings panes, folders, sites
    check(Places.pane("Wi-Fi")?.id == "com.apple.wifi-settings-extension" && Places.pane("wifi settings")?.name == "Wi-Fi" && Places.pane("System Settings > Sound")?.name == "Sound"
          && Places.pane("privacy and security")?.name == "Privacy & Security" && Places.pane("the displays pane")?.name == "Displays" && Places.pane("Displays pane")?.name == "Displays"
          && Places.pane("General")?.url == "x-apple.systempreferences:com.apple.systempreferences.GeneralSettings" && Places.pane("Safari") == nil && Places.pane("") == nil, "a settings pane by its name")
    check(["Wi-Fi", "Bluetooth", "Appearance", "Displays", "Sound", "Notifications", "Focus", "Battery", "Keyboard", "General"].allSatisfy { Places.pane($0) != nil }
          && Places.pane(ofLink: "x-apple.systempreferences:com.apple.Sound-Settings.extension")?.name == "Sound", "the ten panes asked for are all known")
    check(Places.folder("downloads") == "downloads" && Places.folder("my Documents folder") == "documents" && Places.folder("Desktop in Finder") == "desktop"
          && Places.folder("music") == nil && Places.folder("music folder") == "music" && Places.folder("home") == nil && Places.folder("home folder") == "home"
          && Places.folder("~/Projects/demo") == "~/Projects/demo" && Places.folder("/Applications/Utilities") == "/Applications/Utilities" && Places.folder("Mail") == nil, "a folder by its name or its path")
    check(Places.site(named: "YouTube") == "https://www.youtube.com" && Places.site(named: "the New York Times website") == "https://www.nytimes.com"
          && Places.site(named: "the acme website") == "https://www.acme.com" && Places.site(named: "acme") == nil && Places.site(named: "two words website") == nil, "a site by its name")
    check(Places.resolve("Sound settings") == .link("x-apple.systempreferences:com.apple.Sound-Settings.extension") && Places.resolve("downloads folder") == .folder("downloads")
          && Places.resolve("youtube") == .link("https://www.youtube.com") && Places.resolve("Nonesuch") == nil, "what an open that names no app may mean")
    check(Router.direct("open Wi-Fi settings", app: find) == [PlannedStep(action: "open_url", url: "x-apple.systempreferences:com.apple.wifi-settings-extension")]
          && Router.direct("open the Sound pane in System Settings", app: find)?.first?.url == Places.pane("Sound")?.url
          && Router.direct("open System Settings > Displays", app: find)?.first?.url == Places.pane("Displays")?.url
          && Router.direct("go to Battery", app: find)?.first?.url == Places.pane("Battery")?.url
          && Router.direct("open Safari settings", app: find) == [PlannedStep(action: "open_app", app: "Safari"), PlannedStep(action: "key", keys: ["cmd", ","])]
          && Keys.combo(["cmd", ","]) != nil, "routes to a settings pane, or to an app's own settings")
    check(Router.direct("go to the Downloads folder in Finder", app: find) == [PlannedStep(action: "reveal", target: "downloads")]
          && Router.direct("open ~/Projects", app: find) == [PlannedStep(action: "reveal", target: "~/Projects")]
          && Router.direct("go to desktop", app: find) == [PlannedStep(action: "reveal", target: "desktop")]
          && Router.direct("open YouTube", app: find) == [PlannedStep(action: "open_url", url: "https://www.youtube.com")]
          && Router.direct("go to the nytimes website", app: find)?.first?.url == "https://www.nytimes.com"
          && Router.direct("open notes", app: find) == [PlannedStep(action: "open_app", app: "Notes")], "routes to a folder, a path, a site by name; an app still wins")
    check(Router.direct("center this window", app: find) == [PlannedStep(action: "window", direction: "center")]
          && Router.direct("move this window to the middle of the screen", app: find)?.first?.direction == "center", "centring a window")
    check(Captions.step(PlannedStep(action: "open_url", url: Places.pane("Sound")!.url), control: nil) == "Opening Sound settings"
          && Captions.step(PlannedStep(action: "reveal", target: "~/Projects"), control: nil) == "Opening ~/Projects", "captions of the places")

    let studio = ["bonsai-2-9b-planner", "bonsai-2-9b-pointer", "ternary-bonsai-2-2b", "ternary-bonsai-2-4b", "ternary-bonsai-2-9b"]
    check(ModelChoice.best(of: studio) == "bonsai-2-9b-planner" && ModelChoice.best(of: Array(studio.dropFirst())) == "bonsai-2-9b-pointer"
          && ModelChoice.best(of: Array(studio.dropFirst(2))) == "ternary-bonsai-2-9b" && ModelChoice.best(of: ["Bonsai-2-9B-orch-v1-u3000-Q2_0.gguf", "x"]) == "Bonsai-2-9B-orch-v1-u3000-Q2_0.gguf"
          && ModelChoice.best(of: ["ternary-bonsai-2-9b-mlx", "ternary-bonsai-2-9b"]) == "ternary-bonsai-2-9b" && ModelChoice.best(of: []) == nil, "the planner before the pointer before a model as shipped")
    check(ModelChoice.isPlanner("bonsai-2-9b-planner") && !ModelChoice.isPointer("bonsai-2-9b-planner") && ModelChoice.isPointer("bonsai-2-9b-pointer")
          && !ModelChoice.isPlanner("ternary-bonsai-2-9b") && !ModelChoice.isPlanner("pytorch-model"), "which model plans and which only points")
    check(Pipeline.planTokens >= 256, "a planning reply has room for a long text to type")

    // what each kind of request becomes (the phrases of docs/DEMO.md, "What to try")
    let route = { (r: String) in Router.route(r, app: find) }
    check(route("where is the search field?") == .point && route("how do I make a new note?") == .point && Router.route("open Mail", showOnly: true, app: find) == .point, "routes: pointing")
    check(route("is Wi-Fi on?") == .answer(screen: false) && route("what's in this menu?") == .answer(screen: false) && route("what does this button do?") == .answer(screen: false)
          && route("what am I looking at?") == .answer(screen: true) && route("what does this chart say?") == .answer(screen: true) && route("explain this error") == .answer(screen: true), "routes: answers in words")
    check(route("rewrite this more politely") == .text(Skills.text("rewrite this more politely")!) && route("summarise this") == .text(Skills.text("summarise this")!)
          && route("translate this to Spanish") == .text(Skills.text("translate this to Spanish")!) && route("fix the grammar") == .text(Skills.text("fix the grammar")!), "routes: the selected text")
    check(route("put Safari and Notes side by side") == .direct([PlannedStep(action: "side_by_side", app: "Safari", target: "Notes")])
          && route("turn on dark mode") == .direct([PlannedStep(action: "appearance", text: "dark")]) && route("can you open Safari") == .direct([PlannedStep(action: "open_app", app: "Safari")])
          && route("open Mail, then set the volume to 20") == .direct([PlannedStep(action: "open_app", app: "Mail"), PlannedStep(action: "volume", text: "20")]), "routes: done directly")
    check(route("click the search field, then type \"apple\" and press enter") == .scripted(Commands.plan("click the search field, then type \"apple\" and press enter")!)
          && route("add milk to my shopping list in Notes") == .plan && route("close this tab") == .direct([PlannedStep(action: "key", keys: ["cmd", "w"])]), "routes: spelled out, planned, or a shortcut")
}

// ---------------------------------------------------------------- keys
do {
    let save = Keys.combo(["cmd", "s"])
    check(save?.keyCode == 1 && save?.command == true && save?.shift == false, "cmd+s")
    check(Keys.combo(["Command", "Shift", "N"])?.keyCode == 45, "names in any case")
    check(Keys.combo(["enter"])?.keyCode == 36 && Keys.combo(["esc"])?.keyCode == 53, "enter and esc")
    check(Keys.combo(["backspace"])?.keyCode == 51 && Keys.combo(["delete"])?.keyCode == 117, "backspace is the Mac's delete key")
    check(Keys.combo(["cmd"]) == nil, "modifiers alone are not a key")
    check(Keys.combo(["a", "b"]) == nil, "two keys at once")
    check(Keys.names(from: "cmd+shift+n") == ["cmd", "shift", "n"], "a combination as one string")
    check(Keys.names(from: ["ctrl", "c"]) == ["ctrl", "c"], "a list")
    check(Keys.names(from: "[\"cmd\", \"w\"]") == ["cmd", "w"], "a list written as text")
}

// ---------------------------------------------------------------- requests
do {
    let p = Prompts.pointing("Point at the Automate button.")
    check(p.hasPrefix("Output the center point of the position corresponding to the following instruction: \nPoint at the Automate button. \n\n"), "pointing prompt, start")
    check(p.hasSuffix("the output should be [-1,-1]."), "pointing prompt, end")
    let msg = Prompts.userMessage(imageURL: "data:image/png;base64,AAAA", text: "hello")
    let parts = msg["content"] as? [[String: Any]] ?? []
    check(parts.count == 2 && parts[0]["type"] as? String == "image_url" && parts[1]["type"] as? String == "text", "the image comes first")
    let body = LMClient.chatBody(model: "m", messages: [msg], tools: [Prompts.nextStepTool], maxTokens: 32, extras: true)
    check(body["temperature"] as? Int == 0 && body["stream"] as? Bool == false && body["max_tokens"] as? Int == 32, "greedy, not streamed")
    check((try? JSONSerialization.data(withJSONObject: body)) != nil, "the request body is valid JSON")
    let req = Prompts.stepRequest(goal: "Turn on dark mode", history: ["click a", "click b", "click c", "click d", "click e"])
    check(req.contains("Instruction: Turn on dark mode") && req.contains("Step 2: click b") && !req.contains("Step 1:") && req.hasSuffix("Step 5: click e"), "the last four steps are shown")
    check(Prompts.stepRequest(goal: "x", history: []).hasSuffix("Previous actions:\nNone"), "no history")
    check(LMClient.url(from: "localhost:1234")?.absoluteString == "http://localhost:1234/v1", "server address without scheme or /v1")
    check(LMClient.url(from: "http://127.0.0.1:8080/v1/")?.absoluteString == "http://127.0.0.1:8080/v1", "server address with /v1/")

    let answer = "{\"model\":\"bonsai\",\"choices\":[{\"finish_reason\":\"stop\",\"message\":{\"role\":\"assistant\",\"content\":\"<think>hm</think>[10, 20]\"}}],\"usage\":{\"prompt_tokens\":1100,\"completion_tokens\":9}}"
    let r = try? LMClient.parseChat(Data(answer.utf8))
    check(r?.content == "[10, 20]" && r?.reasoning == "hm" && r?.promptTokens == 1100 && r?.finishReason == "stop", "reading the server's answer")
}

// ---------------------------------------------------------------- LM Studio's own API, the token
do {
    let listing = """
    {"models":[{"type":"llm","publisher":"aboufama","key":"bonsai-2-9b-pointer","display_name":"Bonsai","format":"gguf",
      "loaded_instances":[{"id":"bonsai-2-9b-pointer","config":{"context_length":8192}}],
      "capabilities":{"vision":true,"trained_for_tool_use":true,"reasoning":{"allowed_options":["off","on"],"default":"on"}}},
     {"type":"llm","key":"ternary-bonsai-2-4b","loaded_instances":[],"capabilities":{"vision":false,"trained_for_tool_use":true}},
     {"type":"embedding","key":"text-embedding-nomic","loaded_instances":[]}]}
    """
    let models = LMClient.parseStudioModels(Data(listing.utf8)) ?? []
    check(models.count == 3 && models[0].key == "bonsai-2-9b-pointer" && models[0].vision == true && models[0].loaded == ["bonsai-2-9b-pointer"], "LM Studio's model list")
    check(models[0].reasoningOptions == ["off", "on"] && models[0].reasoningDefault == "on", "a model's thinking setting")
    check(models[1].vision == false && models[1].loaded.isEmpty && models[1].reasoningOptions.isEmpty && models[2].type == "embedding", "models without vision or thinking")

    let pipeline = Pipeline(client: LMClient(base: URL(string: "http://localhost:1234/v1")!), model: "m")
    let split = pipeline.messages(imageURL: "data:image/png;base64,AAAA", text: "where?")
    check(split.count == 2 && (split[0]["content"] as? [[String: Any]])?.count == 1 && split[1]["content"] as? String == "where?",
          "the screenshot in its own message, the question in the next")
    pipeline.separateImage = false
    check(pipeline.messages(imageURL: "data:image/png;base64,AAAA", text: "where?").count == 1, "the lab's layout: one message")
    let thinkingOff = LMClient.chatBody(model: "m", messages: split, tools: nil, maxTokens: 32, extras: true)
    check(thinkingOff["reasoning_effort"] as? String == "none" && thinkingOff["chat_template_kwargs"] != nil, "thinking switched off both ways")
    check(LMClient.chatBody(model: "m", messages: split, tools: nil, maxTokens: 32, extras: false)["reasoning_effort"] == nil, "and not at all for a server that refuses the switch")

    let client = LMClient(base: URL(string: "http://localhost:1234/v1")!)
    check(client.root.absoluteString == "http://localhost:1234/" && client.isLocal, "the server's root, and that it is this Mac")
    let plain = try? client.request(client.base.appendingPathComponent("models"), body: nil, timeout: 5)
    check(plain != nil && plain?.value(forHTTPHeaderField: "Authorization") == nil, "no token set: no Authorization header")
    client.token = { "example-not-a-real-token" }
    let signed = try? client.request(client.base.appendingPathComponent("chat/completions"), body: ["a": 1], timeout: 5)
    check(signed?.value(forHTTPHeaderField: "Authorization") == "Bearer example-not-a-real-token", "a token is sent as the bearer token")
    client.token = { "" }
    let empty = try? client.request(client.base.appendingPathComponent("models"), body: nil, timeout: 5)
    check(empty?.value(forHTTPHeaderField: "Authorization") == nil, "an empty token sends nothing")
    let cut = "{\"choices\":[{\"finish_reason\":\"stop\",\"message\":{\"content\":\"it is top right</think>[900, 40]\"}}]}"
    let c = try? LMClient.parseChat(Data(cut.utf8))
    check(c?.content == "[900, 40]" && c?.reasoning == "it is top right", "a thought the template opened is not the answer")
}

// ---------------------------------------------------------------- images
do {
    let w = 400, h = 260
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setFillColor(CGColor(red: 0.9, green: 0.9, blue: 0.9, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    let plain = ctx.makeImage()!
    ctx.setFillColor(CGColor(red: 0.1, green: 0.2, blue: 0.8, alpha: 1))
    ctx.fill(CGRect(x: 100, y: 100, width: 80, height: 40))
    let changed = ctx.makeImage()!
    check(ImageOps.differingPixels(plain, plain) == 0, "an image equals itself")
    check(ImageOps.differingPixels(plain, changed) > ImageOps.unchangedBelow, "a new blue rectangle is a change")
    let small = ImageOps.shrunk(changed, longSide: 200)
    check(small.width == 200 && small.height == 130, "shrunk to 200 x 130")
    check(ImageOps.shrunk(changed, longSide: 1280).width == 400, "small images are sent as they are")
    let zoom = ImageOps.zoomed(changed, pixelRect: CGRect(x: 100, y: 60, width: 100, height: 65), longSide: 1024)
    check(zoom?.width == 1024 && zoom?.height == 666, "a zoomed look is enlarged to 1024 px")
    let url = ImageOps.dataURL(small) ?? ""
    check(url.hasPrefix("data:image/png;base64,iVBOR"), "PNG data URL")
    check(ImageOps.annotated(changed, at: CGPoint(x: 140, y: 140)) != nil, "drawing a ring")
}

// ---------------------------------------------------------------- requests in parts; a done that is not done
do {
    let apps = ["Safari", "Notes", "Reminders", "Calendar", "Contacts", "TextEdit", "Finder", "Mail", "System Settings"]
    let app = { (said: String) -> String? in apps.first { $0.lowercased() == said.lowercased() } }
    check(Commands.parts("Open python.org, then write a note saying Water the plants") == ["Open python.org", "write a note saying Water the plants"], "cut at then")
    check(Commands.parts("Go to python.org and afterwards write a note: Water the plants twice a week") == ["Go to python.org", "write a note: Water the plants twice a week"], "cut at and afterwards")
    check(Commands.parts("Search the web for bonsai tree care; add a reminder called Pick up dry cleaning").count == 2, "cut at a semicolon")
    check(Commands.parts("add a contact named Alan Turing. After that, make a note that says Call the dentist").count == 2, "cut at after that")
    check(Commands.parts("Open Notes and write a note about the trip").count == 1, "and alone does not cut")
    check(Commands.parts("Add a reminder called Water plants and a calendar event called Coffee with Maya")
          == ["Add a reminder called Water plants", "Add a calendar event called Coffee with Maya"], "two things made with one verb are two parts")
    check(Commands.parts("type \"first this, then that\" into the search field").count == 1, "quoted text is never cut")
    check(Commands.parts("lengthen the note") == ["lengthen the note"], "then inside a word does not cut")
    check(Router.parts("Open python.org, then write a note saying Water the plants", app: app).count == 2, "a planned request is carried out in parts")
    check(Router.parts("open Safari, then open Notes", app: app).count == 1, "a request that is direct as a whole stays whole")
    check(Router.parts("click the search field, then type \"apple\" and press enter", app: app).count == 1, "a spelled-out request stays whole")
    check(Router.parts("write a note saying hello", app: app) == ["write a note saying hello"], "one part: the request as it is")
    check(Router.route("Open python.org", app: app) == .direct([PlannedStep(action: "open_url", url: "https://python.org")]), "the first part takes the direct route")
    check(Router.refersBack("put the file budget.csv inside it"), "inside it refers back")
    check(Router.refersBack("open that folder"), "that folder refers back")
    check(!Router.refersBack("make a note that says Call the dentist on Monday"), "that says does not refer back")
    check(!Router.refersBack("write \"send it\" in a new note"), "it inside quotes does not count")
    check(Router.kind(.plan) == "planned" && Router.kind(.direct([])) == "direct" && Router.kind(.scripted([])) == "spelled out", "kinds for the log")

    check(Repair.unfinished("I have opened python.org. Now I need to write a note saying Water the plants."), "now I need to")
    check(Repair.unfinished("I'm sorry, I don't see a \"Red\" control in the list. Could you clarify what you'd like me to do?"), "sorry, could you clarify")
    check(Repair.unfinished("The View > Show Path Bar option is not available in Finder."), "is not available")
    check(Repair.unfinished("Safari is open. Next I will type the address."), "next I will")
    check(Repair.unfinished("I couldn’t find the file on the Desktop."), "could not find, with a curly apostrophe")
    check(!Repair.unfinished("The note has been created."), "a plain done")
    check(!Repair.unfinished("Groceries folder created."), "another plain done")
    check(!Repair.unfinished("Dark mode is now on."), "now on is not now I need")
    check(!Repair.unfinished(""), "no sentence")
}

// ---------------------------------------------------------------- names and routing (the real-Mac pilot)
do {
    let names = ["Finder", "Safari", "Notes", "Reminders", "Calendar", "Contacts", "TextEdit", "Mail", "System Settings", "Siri", "Time Machine",
                 "Bluetooth File Exchange", "Screen Sharing", "Terminal", "Calculator", "Stickies", "Google Chrome"]
    let app = { (said: String) -> String? in AppNames.resolve(said, names: names, aliases: ["settings": "System Settings", "chrome": "Google Chrome"]) }
    check(AppNames.bare("the Finder app") == "finder" && AppNames.bare("Finder.app") == "finder" && AppNames.bare("my Calendar application") == "calendar", "a name without the words around it")
    check(app("the Finder app") == "Finder" && app("Finder.app") == "Finder" && app("chrome") == "Google Chrome" && app("the notes app") == "Notes", "the Finder app is Finder")
    check(app("Remiders") == nil && AppNames.resolve("Remiders", names: names, nearest: true) == "Reminders", "a slip of a letter, only where asked for")
    check(AppNames.resolve("Calender app", names: names, nearest: true) == "Calendar", "a slip with app after it")
    check(AppNames.resolve("nots", names: names, nearest: true) == nil && AppNames.resolve("Photoshop", names: names, nearest: true) == nil, "short or unknown names are not guessed")
    check(AppNames.named(in: "Create a contact for Ada Lovelace in Contacts", among: names) == ["Contacts"], "the app a task names")
    check(AppNames.named(in: "Remind me to send invoice", among: names) == ["Reminders"], "remind me means Reminders")
    check(AppNames.named(in: "write \"open Safari\" in a new note", among: names) == ["Notes"], "names in quotation marks do not count")
    check(AppNames.named(in: "Open Safari and Notes", among: names).count == 2, "two apps named")
    check(AppNames.named(in: "Put Chrome and Safari side by side", among: names) == ["Safari"], "only whole names count")
    let list = [ListedControl(id: 1, role: "button", name: "Add"), ListedControl(id: 2, role: "text field", name: "Search")]
    let filled = Repair.step(PlannedStep(action: "open_app", id: 2), controls: list, task: "Create a contact for Ada Lovelace in Contacts", apps: names, frontApp: "Finder")
    check(filled.step.action == "open_app" && filled.step.app == "Contacts" && filled.note != nil, "open_app with no app takes the app the task names")
    check(Repair.step(PlannedStep(action: "open_app", id: 2), controls: list, task: "Create a contact in Contacts", apps: names, frontApp: "Contacts").step.action == "open_app",
          "not when that app is already in front: then it is left as it is, and never becomes a click")
    check(Repair.step(PlannedStep(action: "open_app", id: 1), controls: list, task: "pull up the presentation in my Downloads folder", apps: names + ["Finder"], frontApp: "System Settings").step.app == "Finder"
          && Router.direct("open the clickypresentation", app: { _ in nil }) == [PlannedStep(action: "present")]
          && Router.direct("can you pull up the presentation for this hackathon? It's in the Downloads folder.", app: { _ in nil }) == [PlannedStep(action: "present")],
          "a file or folder with no app named is found in the Finder; the presentation said any way is the presentation")
    check(Repair.step(PlannedStep(action: "open_app"), controls: list, task: "Open Safari and Notes", apps: names, frontApp: "Finder").step.app == nil, "two apps named: nothing is guessed")

    check(Commands.plan("Move the Dock back to the bottom of the screen") == nil, "moving the Dock is not a drag")
    check(Commands.plan("move this window to the left side of the screen") == nil, "moving a window is not a drag")
    check(Commands.plan("Press the shortcut that takes a full screenshot") == nil, "a shortcut to work out is not a click")
    check(Commands.plan("move the file to the Trash") == [Step(action: .drag, target: "the file", targetEnd: "the Trash")], "a file is still dragged")
    check(Commands.plan("drag the Dock divider to the top") != nil, "drag stays a drag")
    check(Commands.plan("press the Send button") == [Step(action: .click, target: "the Send button")] && Commands.plan("press cmd+s") == [Step(action: .key, keys: ["cmd", "s"])], "press still clicks and still presses keys")
    let dock = { (what: String, value: String) in Route.direct([PlannedStep(action: "dock", target: what, text: value)]) }
    check(Router.route("Move the Dock back to the bottom of the screen", app: app) == dock("position", "bottom"), "the Dock back to the bottom, directly")
    check(Router.route("Put the Dock on the right side", app: app) == dock("position", "right"), "the Dock on the right")
    check(Router.route("Enlarge the Dock icons", app: app) == dock("size", "bigger") && Router.route("Shrink the Dock a little", app: app) == dock("size", "smaller"), "the Dock's size, said another way")
    check(Router.route("Turn on magnification for the Dock", app: app) == dock("magnification", "on") && Router.route("Stop the Dock from magnifying", app: app) == dock("magnification", "off"), "magnification, said another way")
    check(Router.route("Make the Dock hide itself when I am not using it", app: app) == dock("autohide", "on") && Router.route("Stop hiding the Dock", app: app) == dock("autohide", "off"), "hiding, said another way")
    check(Router.route("Add Safari to the Dock", app: app) == .plan && Router.route("Remove Notes from the Dock", app: app) == .plan, "other things about the Dock are planned")
    let shot = Route.direct([PlannedStep(action: "key", keys: ["cmd", "shift", "3"])])
    check(Router.route("Press the shortcut that takes a full screenshot", app: app) == shot && Router.route("take a screenshot", app: app) == shot
          && Router.route("Take a screenshot of the whole screen", app: app) == shot, "a picture of the whole screen is command-shift-3")
    check(Router.route("take a screenshot of this window", app: app) == .plan, "a picture of a window is planned")
    check(Keys.combo(["cmd", "shift", "3"]) != nil, "the screenshot keys are known keys")

    let look = { (text: String) in Route.direct([PlannedStep(action: "appearance", text: text)]) }
    for (said, wanted) in [("turn on dark mode", "dark"), ("Turn dark mode off", "light"), ("disable dark mode", "light"), ("switch to light mode", "light"),
                           ("toggle dark mode", "toggle"), ("Make my Mac use the dark appearance", "dark"), ("Set the appearance to Dark", "dark"),
                           ("Take the Mac out of dark mode", "light"), ("go back to light mode", "light"), ("Switch from dark mode to light mode", "light"),
                           ("can you put the Mac in dark mode?", "dark"), ("I want to use the light theme", "light"), ("Change the system appearance to light", "light"),
                           ("stop using dark mode", "light"), ("Turn on night mode", "dark")] {
        check(Router.route(said, app: app) == look(wanted), "dark or light, however it is said: \(said)")
    }
    check(Router.route("is dark mode on?", app: app) == .answer(screen: false), "a question about dark mode is answered")
    check(Router.route("open the dark mode settings", app: app) == .direct([PlannedStep(action: "open_url", url: Places.pane("Appearance")!.url)]), "the settings for it are the pane")
    check(Router.route("write a note about dark mode", app: app) == .direct([PlannedStep(action: "write_note", target: "dark mode")])
          && Router.route("remind me to try dark mode", app: app) == .plan, "writing about dark mode does not switch it")

    let pane = { (name: String) in Route.direct([PlannedStep(action: "open_url", url: Places.pane(name)!.url)]) }
    check(Router.route("open Bluetooth settings", app: app) == pane("Bluetooth") && Router.route("Open Sharing settings", app: app) == pane("Sharing"), "a pane wins over an app of a similar name")
    check(Router.route("open Siri settings", app: app) == pane("Siri") && Router.route("open the Time Machine settings", app: app) == pane("Time Machine"), "a pane wins over an app of the same name when settings is said")
    check(Router.route("open Safari settings", app: app) == .direct([PlannedStep(action: "open_app", app: "Safari"), PlannedStep(action: "key", keys: ["cmd", ","])]), "an app's own settings still open in the app")
    check(Router.route("go to Bluetooth", app: app) == pane("Bluetooth"), "go to Bluetooth is the pane, not Bluetooth File Exchange")
    check(Router.route("go to Siri", app: app) == .direct([PlannedStep(action: "open_app", app: "Siri")]), "without settings, an app of exactly that name wins")
    let energy = Places.pane("Battery")!, saver = Places.pane("Screen Saver")!
    check(Places.shows(energy, title: "Energy") && Places.shows(Places.pane("Wi-Fi")!, title: "Wi\u{2011}Fi") && Places.shows(Places.pane("Control Center")!, title: "Menu Bar"), "titles a pane's window has")
    check(!Places.shows(saver, title: "General") && !Places.shows(saver, title: ""), "General is not the Screen Saver pane")
    check(Places.shows(Places.pane("Apple Account")!, title: "Ada Lovelace"), "the account pane is titled with a name")
    check(Places.moved(saver)?.name == "Wallpaper" && Places.moved(Places.pane("VPN")!)?.name == "Network" && Places.moved(energy) == nil, "where a missing pane's settings are")
    check(Router.route("On the Desktop, make a new folder named Trip Photos", app: app) == .direct([PlannedStep(action: "new_folder", target: "desktop", text: "Trip Photos")]), "the place said first")
    check(Router.route("In Documents, create a folder called Taxes", app: app) == .direct([PlannedStep(action: "new_folder", target: "documents", text: "Taxes")]), "the place said first, another folder")
}

// ---------------------------------------------------------------- talking back
do {
    let app = { (said: String) -> String? in ["Safari", "Notes", "Reminders"].first { $0.lowercased() == said.lowercased() } }
    check(Talk.fact("is Wi-Fi on?") == .wifi && Talk.fact("Is the wifi turned off?") == .wifi, "Wi-Fi on or off is a fact")
    check(Talk.fact("am I online?") == .internet && Talk.fact("is the Mac connected to the internet?") == .internet, "being online is a fact")
    check(Talk.fact("how much battery is left?") == .battery && Talk.fact("what time is it?") == .time && Talk.fact("what's the date today?") == .date, "battery, time and date are facts")
    check(Talk.fact("is dark mode on?") == .appearance && Talk.fact("what's the volume?") == .volume && Talk.fact("is the sound muted?") == .volume, "dark mode and the volume are facts")
    check(Talk.fact("which Wi-Fi network am I on?") == nil && Talk.fact("what can I do in this menu?") == nil && Talk.fact("how many reminders do I have?") == nil, "other questions are not facts")
    check(Talk.menu("what can I do in this menu?") == "" && Talk.menu("what's in the File menu?") == "file" && Talk.menu("What does the View menu have?") == "view", "the menu a question is about")
    check(Talk.menu("which view am I in?") == nil && Talk.menu("what menus are there?") == "", "no menu, and the menu bar")
    check(Talk.asksDock("what's on my Dock?") && !Talk.asksDock("what's on my desk?"), "a question about the Dock")
    check(Talk.outcome(step: PlannedStep(action: "done", text: "You are in Month view."), content: "") == .say("You are in Month view."), "the done sentence is the answer")
    check(Talk.outcome(step: PlannedStep(action: "done", text: " "), content: "") == .look && Talk.outcome(step: PlannedStep(action: "look", target: "the toolbar"), content: "") == .look, "an empty done, or look: a screenshot")
    check(Talk.outcome(step: PlannedStep(action: "click", id: 3), content: "") == .point && Talk.outcome(step: PlannedStep(action: "open_app", app: "Reminders"), content: "") == .point, "an action is not carried out: pointing")
    check(Talk.outcome(step: nil, content: "<think>hm</think>You have three reminders.") == .say("You have three reminders."), "plain words are an answer")
    check(Talk.outcome(step: nil, content: "") == .look && Talk.outcome(step: nil, content: "{\"action\":") == .look, "nothing usable: a screenshot")
    for q in ["what can I do in this menu?", "which view am I in?", "what's on my Dock?", "how many reminders do I have?", "is Wi-Fi on?"] {
        check(Router.route(q, app: app) == .answer(screen: false), "answered in words: \(q)")
    }
    for q in ["where is the Send button?", "show me the search field", "point at the Wi-Fi icon"] {
        check(Router.route(q, app: app) == .point, "answered by pointing: \(q)")
    }
}

// ---------------------------------------------------------------- an event with no day or time; more joined requests
do {
    let app = { (said: String) -> String? in ["Safari", "Notes", "Calendar"].first { $0.lowercased() == said.lowercased() } }
    check(Skills.eventTitle(kind: "event", rest: ": Budget meeting", datePhrase: "") == "Budget meeting", "a title after a colon")
    check(Skills.eventTitle(kind: "event", rest: "called Lunch with Sam", datePhrase: "") == "Lunch with Sam", "a title after called")
    check(Skills.saysWhen("tomorrow at 3pm") && Skills.saysWhen("Friday") && Skills.saysWhen("at 15:00") && !Skills.saysWhen("Lunch") && !Skills.saysWhen("dinner"), "words that say when")
    var utc = Calendar(identifier: .gregorian)
    utc.timeZone = TimeZone(identifier: "UTC")!
    let now = Date(timeIntervalSince1970: 1_800_000_000 + 1234)          // 34 past some hour
    let next = Skills.nextHour(after: now, calendar: utc)
    check(next > now && next.timeIntervalSince(now) <= 3600 && Int(next.timeIntervalSince1970) % 3600 == 0, "the next full hour")
    check(Router.route("Open Calendar and make a new event: Budget meeting", app: app)
          == .direct([PlannedStep(action: "open_app", app: "Calendar"), PlannedStep(action: "calendar_event", target: "event", text: ": Budget meeting")]), "an app and then an event, directly")
    check(Router.route("open Notes and turn on dark mode", app: app)
          == .direct([PlannedStep(action: "open_app", app: "Notes"), PlannedStep(action: "appearance", text: "dark")]), "an app and then a switch, directly")
    check(Router.route("open Safari and take a screenshot", app: app)
          == .direct([PlannedStep(action: "open_app", app: "Safari"), PlannedStep(action: "key", keys: ["cmd", "shift", "3"])]), "an app and then a screenshot, directly")
    check(Router.route("Open Notes and write a note: Buy oat milk and eggs", app: app) == .plan, "an app and then something to plan is planned as a whole")
}

// ---------------------------------------------------------------- panes checked against macOS 26.6
do {
    // identifiers that are the same in /System/Library/ExtensionKit/Extensions of macOS 15.6 and 26.6
    check(Places.pane("Siri")?.id == "com.apple.Siri-Settings.extension" && Places.pane("Time Machine")?.id == "com.apple.Time-Machine-Settings.extension"
          && Places.pane("Trackpad")?.id == "com.apple.Trackpad-Settings.extension", "Siri, Time Machine and Trackpad as on macOS 26.6")
    check(Places.pane("AirDrop")?.name == "AirDrop & Handoff" && Places.pane("family sharing settings")?.name == "Family"
          && Places.pane("Wallet & Apple Pay")?.id == "com.apple.WalletSettingsExtension" && Places.pane("game controllers")?.name == "Game Controllers", "more panes by name")
    check(Places.pane("reset") == nil && Places.pane("transfer or reset")?.name == "Transfer or Reset", "a bare word like reset is not a pane")
    check(Places.shows(Places.pane("Sharing")!, title: "Sharing") && !Places.shows(Places.pane("Sharing")!, title: "General"), "General is not Sharing")
}

// ---------------------------------------------------------------- the last twelve of the real-Mac pilot
do {
    let names = ["Finder", "Safari", "Notes", "Reminders", "Calendar", "Contacts", "TextEdit", "Calculator", "System Settings"]
    let app = { (said: String) -> String? in AppNames.resolve(said, names: names) }
    // parts and what they are told
    check(Router.refersBack("another one called Submit report") && Router.refersBack("press Return", apps: names), "another, or no app and no place: refers back")
    check(!Router.refersBack("write a note that says Call the dentist on Monday", apps: names) && !Router.refersBack("open the Downloads folder", apps: names), "an app or a place of its own: does not")
    check(Router.task("another one called Submit report", earlier: ["Create a reminder called Pick up dry cleaning"])
          == "another one called Submit report (earlier in the same request: \"Create a reminder called Pick up dry cleaning\")", "the task of a part that refers back")
    check(Router.task("write a note", earlier: []) == "write a note", "the task of a part that does not")
    check(AppNames.named(in: "write a note that says Call the dentist on Monday", among: names) == ["Notes"]
          && AppNames.named(in: "Add a calendar event called Coffee with Maya", among: names) == ["Calendar"], "the app a part speaks of")
    check(AppNames.named(in: "Rename the file notes.txt on the Desktop to final-notes.txt", among: names).isEmpty, "a file called notes.txt is not the Notes app")
    // files
    check(Router.route("Rename the file notes.txt on the Desktop to final-notes.txt", app: app)
          == .direct([PlannedStep(action: "rename_file", app: "desktop", target: "notes.txt", text: "final-notes.txt")]), "a rename is direct")
    check(Router.route("Move the file notes.txt on the Desktop into the Invoices folder", app: app)
          == .direct([PlannedStep(action: "move_file", app: "desktop", target: "notes.txt", text: "Invoices")]), "a move is direct")
    check(Router.route("put the file budget.csv inside it", app: app) == .direct([PlannedStep(action: "move_file", app: "", target: "budget.csv", text: "it")]), "inside it is the folder made before")
    check(Commands.plan("drag the file notes.txt on the Desktop into the Invoices folder") == nil && Commands.plan("drag the report to the Trash") != nil, "a file and a folder are never dragged by words; the Trash still is")
    check(Router.route("rename this window", app: app) == .plan && Router.route("move Safari to the left", app: app) != .direct([PlannedStep(action: "move_file")]), "other renames and moves are not file steps")
    let trash = Route.direct([PlannedStep(action: "move_file", app: "desktop", target: "notes.txt", text: "Trash")])
    check(Router.route("Move the file notes.txt on the Desktop to the Trash", app: app) == trash && Router.route("Delete notes.txt from the Desktop", app: app) == trash
          && Router.route("Throw away notes.txt that is on my Desktop", app: app) == trash, "to the Trash, three ways")
    check(Router.route("delete the last paragraph from the document", app: app) != .direct([PlannedStep(action: "move_file")]) && Router.route("Delete the Desktop", app: app) == .plan, "other deletes are not file steps")
    check(Skills.doneLine(PlannedStep(action: "move_file", app: "desktop", target: "notes.txt", text: "Trash")) == "move notes.txt to the Trash", "the line for a file put in the Trash")
    // Calculator
    check(Router.route("Open Calculator and compute 25 * 4", app: app) == .direct([PlannedStep(action: "calculate", text: "25*4")]), "a sum with Calculator named is direct")
    check(Router.route("use the calculator to work out 12.5 plus 7 times 2", app: app) == .direct([PlannedStep(action: "calculate", text: "12.5+7*2")]), "a sum in words")
    check(Router.route("Open Calculator", app: app) == .direct([PlannedStep(action: "open_app", app: "Calculator")]) && Router.route("compute 25 * 4", app: app) != .direct([PlannedStep(action: "calculate", text: "25*4")]), "no sum, or no Calculator: not this route")
    check(Arithmetic.value("25*4") == 100 && Arithmetic.value("2+3*4") == 14 && Arithmetic.value("10/4") == 2.5 && Arithmetic.value("7-10") == -3, "sums, times and divide first")
    check(Arithmetic.value("5/0") == nil && Arithmetic.value("25") == nil && Arithmetic.value("2+") == nil, "what is not a sum")
    check(Arithmetic.shown(100) == ["100"] && Arithmetic.shown(2.5) == ["2.5"] && Arithmetic.shown(12500) == ["12500", "12,500"], "the result as shown")
    check(Arithmetic.keys("25*4") == [["2"], ["5"], ["shift", "8"], ["4"], ["="]] && Arithmetic.keys("1.5+2").allSatisfy { Keys.combo($0) != nil }, "the keys of a sum")
    // menu commands
    let items: [(menu: String, title: String)] = [("File", "New Finder Window"), ("File", "New Folder"), ("View", "Show Path Bar"), ("View", "Show Status Bar"),
                                                   ("View", "Hide Sidebar"), ("Go", "Downloads"), ("Finder", "Empty Trash…")]
    check(MenuCommand.match(request: "Show the status bar in Finder", items: items, app: "Finder") == 3, "a command by its name")
    check(MenuCommand.match(request: "In Finder, choose View > Show Path Bar", items: items, app: "Finder") == 2, "a command by its path")
    check(MenuCommand.match(request: "make a new folder called Taxes and put the reports in it", items: items, app: "Finder") == nil, "a longer request is not one command")
    check(MenuCommand.match(request: "show the toolbar", items: items, app: "Finder") == nil && MenuCommand.match(request: "downloads", items: items, app: "Finder") == nil, "no such command, or one word only")
    // said another way
    check(Router.route("Enable Dark Mode in settings", app: app) == .direct([PlannedStep(action: "appearance", text: "dark")]), "dark mode in settings is the switch")
    check(Router.route("Put the Dock on the left side and make it hide automatically", app: app)
          == .direct([PlannedStep(action: "dock", target: "position", text: "left"), PlannedStep(action: "dock", target: "autohide", text: "on")]), "two Dock settings in one request")
}

// ---------------------------------------------------------------- holding the key to speak
do {
    let down = Date(timeIntervalSince1970: 1_800_000_000)
    check(PushToTalk.release(pressed: down, released: down.addingTimeInterval(0.12)) == .tap, "let go at once: a tap")
    check(PushToTalk.release(pressed: down, released: down.addingTimeInterval(0.34)) == .tap, "just under the limit: still a tap")
    check(PushToTalk.release(pressed: down, released: down.addingTimeInterval(0.35)) == .hold, "at the limit: a hold")
    check(PushToTalk.release(pressed: down, released: down.addingTimeInterval(4)) == .hold, "held while speaking: a hold")
    check(PushToTalk.release(pressed: down, released: down.addingTimeInterval(-1)) == .tap, "a clock that went back is not a hold")
    let rate = 16000.0
    let tone = { (seconds: Double, level: Float) -> [Float] in (0..<Int(seconds * rate)).map { level * Float(sin(Double($0) * 2 * .pi * 220 / rate)) } }
    let hiss = { (seconds: Double) -> [Float] in (0..<Int(seconds * rate)).map { 0.001 * Float(($0 * 7919) % 13 - 6) / 6 } }
    check(PushToTalk.voicedSeconds([]) == 0 && PushToTalk.voicedSeconds([Float](repeating: 0, count: 32000)) == 0, "nothing, and silence: no voice")
    check(abs(PushToTalk.voicedSeconds(tone(1.0, 0.1)) - 1.0) < 0.05, "a second of sound is a second of voice")
    check(PushToTalk.voicedSeconds(hiss(2.0)) == 0, "the hiss of a quiet room is not voice")
    let short = PushToTalk.voicedSeconds(hiss(1.0) + tone(0.2, 0.1) + hiss(1.0)), long = PushToTalk.voicedSeconds(hiss(1.0) + tone(0.8, 0.05) + hiss(1.0))
    check(abs(short - 0.2) < 0.11 && !PushToTalk.caught(voiced: short), "a click of sound in a quiet recording is not a request")
    check(abs(long - 0.8) < 0.11 && PushToTalk.caught(voiced: long), "most of a second of speech is")
    check(PushToTalk.caught(voiced: 0.3) && !PushToTalk.caught(voiced: 0.2), "the least voice that counts")
    check(PushToTalk.level(hiss(0.1)[...]) == 0 && PushToTalk.level([][...]) == 0, "a quiet room shows nothing on the meter")
    check(PushToTalk.level(tone(0.1, 0.05)[...]) > 0.3 && PushToTalk.level(tone(0.1, 0.05)[...]) < PushToTalk.level(tone(0.1, 0.2)[...]) && PushToTalk.level(tone(0.1, 0.6)[...]) == 1, "a voice shows, a louder one more, up to full")
    check(PushToTalk.meter(0) == "▯▯▯▯▯▯▯" && PushToTalk.meter(0.5) == "▮▮▮▮▯▯▯" && PushToTalk.meter(1) == "▮▮▮▮▮▮▮" && PushToTalk.meter(7, cells: 5) == "▮▮▮▮▮", "the meter as a row of bars")
    let clip = tone(0.84, 0.1), wider = PushToTalk.padded(clip, to: 1.84)
    check(wider.count == 29440 && wider[0] == 0 && wider[wider.count - 1] == 0 && Array(wider[8000..<8000 + clip.count]) == clip, "a short clip gets silence before and after, half each")
    check(PushToTalk.padded(tone(2.0, 0.1), to: 1.5).count == 32000, "a clip that is long enough is left as it is")
    check(PushToTalk.clean(" [BLANK_AUDIO] ") == "" && PushToTalk.clean("(music) open Notes ♪") == "open Notes" && PushToTalk.clean("Open  Safari.") == "Open Safari.", "marks for sounds that are not words are dropped")
}

// ---------------------------------------------------------------- a helper that only points
do {
    check(PointerHelper("http://127.0.0.1:1235")?.base.absoluteString == "http://127.0.0.1:1235" && PointerHelper("127.0.0.1:1235/")?.base.absoluteString == "http://127.0.0.1:1235",
          "the helper's address, with or without http and a slash")
    check(PointerHelper("") == nil && PointerHelper("   ") == nil && PointerHelper("ftp://host") == nil, "what is not an address")
    let body = PointerHelper.body(imageURL: "data:image/png;base64,iVBORw0KGgo=", request: "the Today button", looks: 1)
    check(body?["image_b64"] as? String == "iVBORw0KGgo=" && body?["request"] as? String == "the Today button" && body?["looks"] as? Int == 1, "what is sent: the picture, the words, one look")
    check(PointerHelper.body(imageURL: "data:image/jpeg;base64,/9j/4AAQ", request: "x", looks: 2)?["looks"] as? Int == 2
          && PointerHelper.body(imageURL: "data:image/jpeg;base64,/9j/4AAQ", request: "x", looks: 7)?["looks"] as? Int == 2, "two looks when a second look is on")
    check(PointerHelper.body(imageURL: "https://example.com/a.png", request: "x", looks: 1) == nil && PointerHelper.body(imageURL: "data:image/png;base64,", request: "x", looks: 1) == nil,
          "a picture that is not in the message cannot be sent")
    let good = Data("{\"x\": 0.5, \"y\": 0.25, \"seconds\": 0.41, \"read_seconds\": 0.3, \"cached\": true}".utf8)
    check(PointerHelper.read(status: 200, data: good, elapsed: 0.5) == .point(x: 0.5, y: 0.25, seconds: 0.41, readSeconds: 0.3, cached: true), "a good reply is a point")
    check(PointerHelper.read(status: 200, data: Data("{\"x\": 0, \"y\": 1}".utf8), elapsed: 2) == .point(x: 0, y: 1, seconds: 2, readSeconds: 0, cached: false), "the corners count, and the rest may be missing")
    let unusable = { (reply: PointerHelper.Reply) -> Bool in if case .unusable = reply { return true } else { return false } }
    check(unusable(PointerHelper.read(status: 500, data: good, elapsed: 0.5)) && unusable(PointerHelper.read(status: 0, data: good, elapsed: 0.5)), "not a 200: the language model points")
    check(unusable(PointerHelper.read(status: 200, data: good, elapsed: 30.5)), "a reply after 30 s: the language model points")
    check(unusable(PointerHelper.read(status: 200, data: Data("{\"x\": 1.2, \"y\": 0.5}".utf8), elapsed: 1))
          && unusable(PointerHelper.read(status: 200, data: Data("{\"x\": 0.2, \"y\": -0.1}".utf8), elapsed: 1)), "a point outside the picture: the language model points")
    check(unusable(PointerHelper.read(status: 200, data: Data("{\"x\": 0.2}".utf8), elapsed: 1)) && unusable(PointerHelper.read(status: 200, data: Data("oops".utf8), elapsed: 1))
          && unusable(PointerHelper.read(status: 200, data: Data("{\"x\": true, \"y\": 0.5}".utf8), elapsed: 1)), "no x and y, or not JSON: the language model points")
    // the helper's fractions land on the screen where the same place on the model's grid does
    let air = CGRect(x: 0, y: 0, width: 1470, height: 956)
    check(PointerHelper.grid(x: 0.5, y: 0.25) == CGPoint(x: 500, y: 250), "fractions of the picture on the 0 to 1000 grid")
    check(near(Geometry.screenPoint(grid: PointerHelper.grid(x: 0.5, y: 0.5), region: air), CGPoint(x: 735, y: 478))
          && near(Geometry.screenPoint(grid: PointerHelper.grid(x: 1, y: 1), region: air), CGPoint(x: 1469, y: 955)), "and from there to the screen like any answer")
    let window = CGRect(x: 400, y: 300, width: 490, height: 318.667)
    check(near(Geometry.screenPoint(grid: PointerHelper.grid(x: 0.1, y: 0.9), region: window), CGPoint(x: 449, y: 586.8003)), "also in a closer look")
    check(PointerHelper.name == "bonsai-pruned-4b" && PointerHelper.languageModel == "language model", "the two names in the steps file")
    check(PointerHelper.readBody(imageURL: "data:image/png;base64,iVBORw0KGgo=")?["image_b64"] as? String == "iVBORw0KGgo=" && PointerHelper.readBody(imageURL: "nothing") == nil, "what is sent to have a picture read ahead")
    check(PointerHelper.readReply(status: 200, data: Data("{\"read_seconds\": 1.9, \"cached\": false}".utf8), elapsed: 2.1) == .read(seconds: 1.9, cached: false)
          && PointerHelper.readReply(status: 200, data: Data("{\"cached\": true}".utf8), elapsed: 0.05) == .read(seconds: 0.05, cached: true), "a picture read and kept by the helper")
    let notRead = { (reply: PointerHelper.ReadReply) -> Bool in if case .unusable = reply { return true } else { return false } }
    check(notRead(PointerHelper.readReply(status: 404, data: Data("{}".utf8), elapsed: 0.1)) && notRead(PointerHelper.readReply(status: 200, data: Data("no".utf8), elapsed: 0.1))
          && notRead(PointerHelper.readReply(status: 200, data: Data("{}".utf8), elapsed: 31)), "a helper with no /read, a bad reply or a late one: the language model reads ahead")
}

// ---------------------------------------------------------------- the demo-beats check: an address, a menu
do {
    let names = ["Safari", "Google Chrome", "Brave Browser", "Notes", "Mail", "Finder"]
    let app = { (said: String) -> String? in AppNames.resolve(said, names: names, aliases: ["chrome": "Google Chrome", "brave": "Brave Browser"]) }
    let site = { (address: String, browser: String) in Route.direct([PlannedStep(action: "open_url", app: browser, url: address)]) }
    check(Router.route("open apple.com in Safari", app: app) == site("https://apple.com", "Safari"), "open apple.com in Safari: exactly apple.com")
    check(Router.route("open github.com in Brave", app: app) == site("https://github.com", "Brave Browser"), "open github.com in Brave")
    check(Router.route("go to example.com/docs in Chrome", app: app) == site("https://example.com/docs", "Google Chrome"), "go to example.com/docs in Chrome")
    check(Router.route("Open YouTube in Safari", app: app) == site("https://www.youtube.com", "Safari"), "a site by its name, in a browser")
    check(Places.site(named: "apple.com in Safari") == "https://apple.com" && Places.site(named: "the apple.com website") == "https://apple.com", "an address is never made into another address")
    check(Places.site(named: "the nytimes website") == "https://www.nytimes.com" && Places.site(named: "the acme website") == "https://www.acme.com", "names of sites as before")
    let parts = Router.parts("Open apple.com in Safari, then make a note that says Buy a new Mac, then turn on dark mode", app: app)
    check(parts.count == 3 && Router.route(parts[0], app: app) == site("https://apple.com", "Safari"), "the same as the first part of a longer request")
    check(Router.route("open Notes in Safari", app: app) != site("https://www.notes.com", "Safari"), "an app is not turned into a site")
    check(Skills.namedBrowser("lunch on Friday in Safari", app: app)?.rest == "lunch on Friday" && Skills.namedBrowser("lunch on Friday in Safari", app: app)?.browser == "Safari"
          && Skills.namedBrowser("lunch on Friday", app: app) == nil && Skills.namedBrowser("the meeting in Notes", app: app) == nil, "a browser named at the end of the words")
    let view = ["as Icons", "as List", "as Columns", "as Gallery", "Use Stacks", "Sort By", "Clean Up", "Hide Sidebar", "Show Preview", "Hide Toolbar", "Show All Tabs",
                "Show Tab Bar", "Show Path Bar", "Show Status Bar", "Customize Toolbar…", "Show View Options", "Enter Full Screen"]
    check(Skills.menuAnswer(title: "", items: view) == "This menu has: as Icons, as List, as Columns, as Gallery, Use Stacks, Sort By, Clean Up, Hide Sidebar, and 9 more.", "a menu said from its own items")
    check(Skills.menuAnswer(title: "File", items: ["New Window", "Close"]) == "The File menu has: New Window, Close.", "a short menu, by its name")
    check(Skills.menuAnswer(title: "menu bar", items: ["Finder", "File"]) == "The menu bar has: Finder, File." && Skills.menuAnswer(title: "", items: []) == "This menu has nothing that can be chosen now.", "the menu bar, and an empty menu")
}

// ---------------------------------------------------------------- the demo: a name, the presentation, a written note
do {
    let names = ["Safari", "Notes", "Photo Booth", "Keynote", "Preview", "Finder"]
    let app = { (said: String) -> String? in AppNames.resolve(said, names: names) }
    check(Router.addressed("Clicky, bring up the presentation.") == "bring up the presentation." && Router.addressed("Hey Bonsai open Notes") == "open Notes"
          && Router.addressed("okay, Clickie: turn on dark mode") == "turn on dark mode", "the name it is called by is not part of the request")
    check(Router.addressed("click the search field") == "click the search field" && Router.addressed("Bonsai") == "Bonsai" && Router.addressed("open Notes") == "open Notes", "a request with no name is left alone")
    let show = Route.direct([PlannedStep(action: "present")])
    for said in ["bring up the presentation", "Bring up the presentation.", "show my slides", "start the slideshow", "open the deck", "go back to the presentation", "present"] {
        check(Router.route(Router.addressed(said), app: app) == show || said == "present", "the presentation: \(said)")
    }
    check(Router.route("open the presentation notes in Notes", app: app) != show && Router.route("make a presentation about bonsai", app: app) != show, "other things about presentations are not this")
    let abilities = Route.direct([PlannedStep(action: "write_note", target: "abilities")])
    for said in ["Write down what you can help me with.", "write down some things you can help me do", "write some things that you can help me do", "make a note of what you can do for me",
                 "list what you can do"] {
        check(Router.route(said, app: app) == abilities, "a note of what it can do: \(said)")
    }
    check(Router.route("write a note about the trip to Lisbon", app: app) == .direct([PlannedStep(action: "write_note", target: "the trip to Lisbon")]), "a note about something")
    check(Router.route("make a note that says Call the dentist on Monday", app: app) == .plan && Router.route("write a note saying buy milk", app: app) == .plan
          && Router.route("Open Notes and write a note: Buy oat milk and eggs", app: app) == .plan && Router.route("write \"what you can do\" in a new note", app: app) != abilities,
          "a note whose words are given is still typed as it is, by the planner")
    check(Skills.noteLines("<think>four lines</think>1. Open apps and web sites\n- Change settings like dark mode\n\n• \"Find and click things\"\n**Write notes**\n5) extra\n6) more")
          == ["Open apps and web sites", "Change settings like dark mode", "Find and click things", "Write notes", "extra"], "what the model wrote, as the lines of a note")
    check(Skills.noteLines("") == [] && Skills.noteLines("ok") == [], "nothing usable is nothing")
    check(Skills.noteTitle("abilities") == "What I can help you with" && Skills.noteTitle("some ideas for the weekend") == "Ideas for the weekend", "the note's title")
    check(Skills.typingPieces("Open apps\nand sites") == ["Open ", "apps\n", "and ", "sites"] && Skills.typingPieces("") == [], "a text in the pieces it is typed in")
    check(Skills.abilityLines.count == 4 && Skills.notePrompt("abilities").contains("four short lines") && Skills.notePrompt("the trip").contains("the trip"), "what the model is asked to write")
    check(Skills.doneLine(PlannedStep(action: "present")) == "open the presentation" && Skills.caption(PlannedStep(action: "write_note", target: "abilities")) == "Writing a note", "their lines and captions")
}

// ---------------------------------------------------------------- subtitles
do {
    let app = { (said: String) -> String? in ["Notes", "Safari"].first { $0.lowercased() == said.lowercased() } }
    let captions = Route.direct([PlannedStep(action: "caption_video")])
    for said in ["caption the video I just recorded", "Caption my last recording.", "put subtitles on the video", "add captions to my latest video", "subtitle this clip", "make subtitles for the video I just made"] {
        check(Router.route(said, app: app) == captions, "captioning a recording: \(said)")
    }
    check(Router.route("caption this photo", app: app) != captions && Router.route("put the video on the Desktop", app: app) != captions, "other things are not captioning")
    check(Router.route("Play the video on my desktop.", app: app) == .direct([PlannedStep(action: "play_video", target: "desktop")])
          && Router.route("open the comparison video", app: app) == .direct([PlannedStep(action: "play_video", target: "")])
          && Router.route("play the newest recording in Movies", app: app) == .direct([PlannedStep(action: "play_video", target: "movies")]), "playing a video")
    check(Router.route("play some music", app: app) != .direct([PlannedStep(action: "play_video", target: "")]), "music is not a video")
    check(Subtitles.clean("<|0.00|> Hello there.<|1.20|>") == "Hello there." && Subtitles.clean(" [BLANK_AUDIO] ") == "", "marks that are not words are dropped")
    let one = Subtitles.lines([Subtitle(start: 1, end: 3, text: " Open Notes. ")])
    check(one == [Subtitle(start: 1, end: 3, text: "Open Notes.")], "a short stretch is one line")
    let long = Subtitles.lines([Subtitle(start: 0, end: 8, text: "This is my Mac and I am going to give you this whole demo with one key and my voice")])
    check(long.count == 2 && long.allSatisfy { $0.text.count <= 42 } && long[0].start == 0 && abs(long[1].end - 8) < 0.001 && abs(long[0].end - long[1].start) < 0.001,
          "a long stretch is cut into lines that share its time")
    check(long.map(\.text).joined(separator: " ") == "This is my Mac and I am going to give you this whole demo with one key and my voice", "and no word is lost")
    let quick = Subtitles.lines([Subtitle(start: 0, end: 0.2, text: "Hi."), Subtitle(start: 0.5, end: 2, text: "Open Notes.")])
    check(abs(quick[0].end - 0.5) < 0.001 && quick[1].start == 0.5, "a line that would flash by is held until the next begins")
    check(Subtitles.lines([Subtitle(start: 2, end: 2, text: "x"), Subtitle(start: 0, end: 1, text: " [BLANK_AUDIO] ")]).isEmpty, "nothing to show is no line")
    check(Subtitles.stamp(0) == "00:00:00,000" && Subtitles.stamp(62.5) == "00:01:02,500" && Subtitles.stamp(3725.042) == "01:02:05,042", "times as subtitle files write them")
    check(Subtitles.srt([Subtitle(start: 1, end: 3, text: "Open Notes."), Subtitle(start: 3.5, end: 5, text: "Done.")])
          == "1\n00:00:01,000 --> 00:00:03,000\nOpen Notes.\n\n2\n00:00:03,500 --> 00:00:05,000\nDone.\n", "a subtitle file")
}

// ---------------------------------------------------------------- finding a thing by its name (Accessibility first)
do {
    let names = ["Today", "Share", "Search", "New Reminder", "Reminders", "Add List", "Close", "Close", "Send", "Back", "", "Wi-Fi", "Safari", "Trash", "File", "View"]
    check(NameSearch.search("the Today button", in: names) == .one(0) && NameSearch.search("go to today", in: names) == .one(0), "one control named exactly so")
    check(NameSearch.search("where is the share button?", in: names) == .one(1) && NameSearch.search("the Share icon in the toolbar", in: names) == .one(1), "words for the kind of thing and its place are not part of the name")
    check(NameSearch.search("the button that sends", in: names) == .one(8), "sends and Send meet")
    check(NameSearch.search("Wi-Fi", in: names) == .one(11) && NameSearch.search("the wifi switch", in: names) == .none, "a name with a hyphen, word for word")
    check(NameSearch.search("the Trash", in: names) == .one(13) && NameSearch.search("the View menu", in: names) == .one(15), "the Dock's icons and the menus count too")
    check(NameSearch.search("the close button", in: names) == .several([6, 7]), "two of the same name: someone has to choose")
    check(NameSearch.search("the new button", in: names) == .one(3), "one name that holds the word")
    check(NameSearch.search("the reminder list", in: names) == .several([3, 4, 5]), "names that only share a word are candidates")
    check(NameSearch.search("the red circle", in: names) == .none && NameSearch.search("the button", in: names) == .none && NameSearch.search("", in: names) == .none, "no name fits, or nothing was named")
    check(NameSearch.words("Where is the Share button?") == ["share"] && NameSearch.words("the New Reminder button") == ["new", "reminder"], "the words that could be a name")
    check(NameSearch.target(of: "where is the share button?") == "the share button" && NameSearch.target(of: "Show me the search field") == "the search field"
          && NameSearch.target(of: "point at the Wi-Fi icon.") == "the Wi-Fi icon" && NameSearch.target(of: "the Today button") == "the Today button", "what a pointing request is after")
}

print(failures == 0 ? "all \(checks) checks passed" : "\(failures) of \(checks) checks FAILED")
exit(failures == 0 ? 0 : 1)
