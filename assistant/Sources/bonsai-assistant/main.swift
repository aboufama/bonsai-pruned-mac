// bonsai-assistant: with no arguments, the menu-bar app. With arguments, the same requests on
// saved screenshots, without capturing the screen or sending any event:
//
//   bonsai-assistant --models                                   what the server offers
//   bonsai-assistant --point shot.png "the Done button"         one pointing request
//   bonsai-assistant --step shot.png "turn on dark mode"        one next-step request
//   bonsai-assistant --samples ~/Bonsai-demo/samples            every request of hints.json, with hit or miss
//
// Options: --server URL (default LM Studio's), --model ID (default: the first Bonsai the server
// lists), --side 1280|896, --out DIR (write each screenshot with the point drawn on it),
// --one-message (screenshot and question in one message, as measured in the lab; slower),
// --tools (steps as a next_step tool call, for a model trained on steps).
import AppKit
import AssistantCore

let arguments = Array(CommandLine.arguments.dropFirst())

func option(_ name: String) -> String? {
    guard let i = arguments.firstIndex(of: name), i + 1 < arguments.count else { return nil }
    return arguments[i + 1]
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(2)
}

func runCommandLine() async {
    guard let base = LMClient.url(from: option("--server") ?? Settings.shared.server) else { fail("bad --server") }
    let client = LMClient(base: base)
    let side = Int(option("--side") ?? "") ?? 1280
    var listed: [String] = []
    do { listed = try await client.models() } catch { fail("\(error)") }
    if arguments.contains("--models") {
        print(listed.joined(separator: "\n"))
        return
    }
    guard let model = option("--model") ?? listed.first(where: { $0.lowercased().contains("bonsai") }) ?? listed.first else {
        fail("the server lists no model")
    }
    let pipeline = Pipeline(client: client, model: model)
    pipeline.separateImage = !arguments.contains("--one-message")     // --one-message: the lab's layout, a full read per question
    pipeline.plainStepPrompt = arguments.contains("--tools")
    let outDir = option("--out")
    if let outDir { try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true) }
    print("server \(base.absoluteString) · model \(model) · image \(side) px · "
          + (pipeline.separateImage ? "screenshot in its own message" : "screenshot and question in one message"))

    /// One pointing request on a file. `box`: the target as fractions of the image, if known.
    func point(_ path: String, _ instruction: String, box: [Double]? = nil, tag: String) async -> Bool? {
        guard let full = ImageOps.load(path: path) else { fail("cannot read \(path)") }
        let sent = ImageOps.shrunk(full, longSide: side)
        guard let url = ImageOps.dataURL(sent) else { fail("cannot encode \(path)") }
        do {
            let out = try await pipeline.point(imageURL: url, instruction: instruction)
            var line = String(format: "%.2f s", out.chat.seconds) + " (\(out.chat.tokenNote)) · wrote \(out.chat.written.prefix(60))"
            var hit: Bool?
            if let g = out.answer.point {
                let px = Geometry.pixel(grid: g, imageWidth: full.width, imageHeight: full.height)
                line += String(format: " · pixel (%.0f, %.0f) of %d x %d", px.x, px.y, full.width, full.height)
                var rect: CGRect?
                if let box, box.count == 4 {
                    let fx = g.x / 1000, fy = g.y / 1000
                    hit = fx >= box[0] && fx <= box[2] && fy >= box[1] && fy <= box[3]
                    rect = CGRect(x: box[0] * Double(full.width), y: box[1] * Double(full.height),
                                  width: (box[2] - box[0]) * Double(full.width), height: (box[3] - box[1]) * Double(full.height))
                }
                if let outDir, let drawn = ImageOps.annotated(full, at: px, box: rect) {
                    _ = ImageOps.save(drawn, path: "\(outDir)/\(tag).png")
                }
            } else {
                if box != nil { hit = false }
            }
            if let note = out.note { line += " · note: \(note)" }
            print("  \(hit == nil ? "    " : hit! ? "HIT " : "MISS") \"\(instruction)\" · \(line)")
            return hit
        } catch {
            print("  ERROR \"\(instruction)\": \(error)")
            return box == nil ? nil : false
        }
    }

    if let i = arguments.firstIndex(of: "--point"), i + 2 < arguments.count {
        _ = await point(arguments[i + 1], arguments[i + 2], tag: "point")
    } else if let i = arguments.firstIndex(of: "--step"), i + 2 < arguments.count {
        guard let full = ImageOps.load(path: arguments[i + 1]), let url = ImageOps.dataURL(ImageOps.shrunk(full, longSide: side)) else {
            fail("cannot read \(arguments[i + 1])")
        }
        do {
            let out = try await pipeline.nextStep(imageURL: url, goal: arguments[i + 2], history: [])
            print("  \(String(format: "%.2f s", out.chat.seconds)) (\(out.chat.tokenNote)) · wrote \(out.chat.written)")
            if let note = out.note { print("  note: \(note)") }
            print("  step: " + (out.step.map { $0.historyLine + ($0.problem().map { "  [not usable: \($0)]" } ?? "") } ?? "none could be read"))
        } catch {
            print("  ERROR: \(error)")
        }
    } else if let dir = option("--samples") {
        let folder = (dir as NSString).expandingTildeInPath
        guard let data = FileManager.default.contents(atPath: folder + "/hints.json"),
              let hints = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { fail("no hints.json in \(folder)") }
        var hits = 0, scored = 0
        for name in hints.keys.sorted() {
            guard let entry = hints[name] as? [String: Any], let list = entry["hints"] as? [[String: Any]] else { continue }
            print("\(name)  (\(entry["note"] as? String ?? ""))")
            for (k, hint) in list.enumerated() {
                guard let q = hint["q"] as? String else { continue }
                let box = (hint["box"] as? [Any])?.compactMap { ($0 as? NSNumber)?.doubleValue }
                let tag = (name as NSString).deletingPathExtension + "-\(k + 1)"
                if let hit = await point(folder + "/" + name, q, box: box, tag: tag) {
                    scored += 1
                    if hit { hits += 1 }
                }
            }
        }
        print("\(hits) of \(scored) requests with a known target were hit")
    } else {
        fail("usage: bonsai-assistant [--models | --point IMAGE \"what\" | --step IMAGE \"request\" | --samples DIR] [--server URL] [--model ID] [--side N] [--out DIR]")
    }
}

if let i = arguments.firstIndex(of: "--transcribe"), i + 1 < arguments.count {
    // The speech model on a sound file: bonsai-assistant --transcribe request.wav   (no microphone needed)
    Task {
        do {
            let voice = Voice()
            let loadStart = Date()
            try await voice.prepare()
            print(String(format: "WhisperKit %@ loaded in %.1f s from %@", Voice.modelName, Date().timeIntervalSince(loadStart), Voice.localModel() ?? "?"))
            let heard = try await voice.transcribe(file: arguments[i + 1])
            print(String(format: "%.2f s · heard: %@", heard.seconds, heard.text))
            exit(0)
        } catch {
            fail("\(error)")
        }
    }
    dispatchMain()
} else if arguments.isEmpty || arguments == ["--smoke"] {
    let app = NSApplication.shared
    let controller = AppController()
    app.delegate = controller
    app.setActivationPolicy(.accessory)                 // a menu-bar app: no Dock icon, never steals the front
    app.run()
} else {
    Task {
        await runCommandLine()
        exit(0)
    }
    dispatchMain()
}
