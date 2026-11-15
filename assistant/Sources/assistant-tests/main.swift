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
    check(Commands.plan("open the settings") == [Step(action: .click, target: "open the settings")], "open: the whole phrase is the target")
    check(Commands.plan("Please click the Save button.") == [Step(action: .click, target: "the Save button")], "politeness and a full stop")
    check(Commands.plan("turn on dark mode") == nil && Commands.plan("click Save then make it pretty") == nil, "anything else is left to the model to plan")
    check(Commands.isQuestion("where do I turn on dark mode?") && Commands.isQuestion("show me the search field") && !Commands.isQuestion("click the search field"), "questions are shown, commands are done")
    check(Commands.plan("click the search field")?.allSatisfy { $0.problem() == nil } == true, "the steps are usable as they are")
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

print(failures == 0 ? "all \(checks) checks passed" : "\(failures) of \(checks) checks FAILED")
exit(failures == 0 ? 0 : 1)
