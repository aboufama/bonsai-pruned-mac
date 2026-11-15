// The app: a leaf in the menu bar, a hotkey that opens the input bar, and what a request can
// become: "show me" (point at it), an answer in words, work on the selected text, something
// done directly with no model (apps, windows, dark mode, the volume, folders, a calendar
// event), or "do it" (carried out step by step).
import AppKit
import AssistantCore
import AVFoundation
import Carbon.HIToolbox

final class AppController: NSObject, NSApplicationDelegate, NSMenuDelegate {
    static let maxSteps = 12
    static let zoom: CGFloat = 3              // a second look sees a third of each side
    static let zoomSide = 1024                // and is shown at this many pixels on its longer side

    private enum HotKey {
        static let ask: UInt32 = 1, askToo: UInt32 = 2, escape: UInt32 = 3, ret: UInt32 = 4, enter: UInt32 = 5
        static let talk: UInt32 = 6, talkDo: UInt32 = 7, pointOnly: UInt32 = 8
    }

    private let settings = Settings.shared
    private var statusItem: NSStatusItem!
    private let overlay = Overlay()
    private let bar = InputBar()
    private let log = LogWindow()
    private let client: LMClient
    private let pipeline: Pipeline
    private var models: [String] = []
    private let modelMenu = NSMenu()

    // LM Studio housekeeping
    static let contextLength = 8192            // a 1280 px screenshot is about 1,040 tokens; the step tool adds a few hundred
    private var studio: [StudioModel] = []     // the language models LM Studio has, when the server is LM Studio
    private var isStudio = false
    private var ready = false
    private var modelSees = true               // false: LM Studio lists the model without a vision file
    static let launcher = "the app this was started from (Terminal, or Claude if started in its terminal panel)"
    private var readiness = "LM Studio: checking…"
    private var preparing: Task<Void, Never>?
    private var preparations = 0
    private var startedServer = false          // this app started the server: it stops it on quit
    private var loadedByApp: [String] = []     // instances this app loaded: it unloads them on quit
    private var displaced: [(key: String, context: Int)] = []   // models it unloaded to make room: reloaded on quit
    private var signals: [DispatchSourceSignal] = []
    private var lastOpened: String?            // the app opened last (a browser decides where an email draft goes)
    private var trace: [[String: Any]] = []    // the steps of the request in hand, for a batch run's log
    private var lastEnding = ""
    private var lastSpoken = ""                // what the last request said, or would have said, aloud
    private var stepNote: String?              // something about a step that went through, for the planner and the log
    private var lastCarried = ""               // the action of the step carried out last
    private var lastTyped = ""                 // the text typed last, and where the keyboard was then
    private var lastTypedPlace = ""
    private var moreToCome = false             // another part of the same request follows: nothing is put away yet
    private var carried: [String] = []         // the "Done so far" lines of the part before, for a part that refers back to it
    private var lastExchange: (question: String, answer: String, at: Date)?    // kept a few minutes, for a follow-up question

    // reading ahead, and spoken requests
    private struct Ahead {
        let sent: Sent
        let started: Date
        let read: Task<Double?, Never>          // seconds the read took; nil if it failed
    }
    private var ahead: Ahead?
    private let voice = Voice()
    private var voiceShowOnly = false
    private var listenTimer: Timer?
    // holding the main key to speak
    private var held: Date?                    // when the main key went down, while it is down
    private var holdNumber = 0                 // goes up with every press, tap, release and Esc: what is older is dropped
    private var holdStarting: Task<Void, Never>?
    private var holdProblem: Error?
    private var lastHeard: Voice.Heard?        // what the request in hand was heard as, when it was spoken
    private var lastPointer: String?           // what pointed for the step in hand: the helper, or the language model
    private var session: [[String: Any]] = []  // with --out and no batch: every request of this run, for the steps file
    private var watcher: Timer?
    private var refreshing = false

    /// `--smoke`: start, show each window once, get the server ready, quit after half a minute.
    /// No permission is asked for, the screen is not captured and no event is sent.
    private let smoke = CommandLine.arguments.contains("--smoke")
    private let speaker = AVSpeechSynthesizer()

    private var run: Task<Void, Never>?
    private var runID = 0
    private var confirm: CheckedContinuation<Bool, Never>?

    override init() {
        client = LMClient(base: LMClient.url(from: Settings.shared.server) ?? URL(string: "http://localhost:1234/v1")!)
        pipeline = Pipeline(client: client, model: Settings.shared.model)
        pipeline.pointer = Launch.pointerURL.flatMap { PointerHelper($0) }
        pipeline.plannerSystem = Launch.plannerSystem.text
        super.init()
        // Read from the Keychain when a request is about to be sent. Not with nobody at the
        // keyboard: a locked keychain would ask for its password and wait for ever.
        client.token = { Launch.unattended ? nil : Keychain.token() }
    }

    // MARK: start

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        let image = NSImage(systemSymbolName: "leaf.fill", accessibilityDescription: "Bonsai assistant")
        image?.isTemplate = true
        statusItem.button?.image = image
        let menu = NSMenu()
        menu.delegate = self
        statusItem.menu = menu
        rebuild(menu)

        bar.onSubmit = { [weak self] text, showOnly in self?.ask(text, showOnly: showOnly, keepPointer: true) }
        bar.onCancel = { [weak self] in self?.overlay.retreat() }
        bar.onTyping = { [weak self] typing in self?.overlay.idle(!typing) }       // it locks in when you start typing
        // The main key: held, it listens until it is let go and carries out what was said; tapped, it opens the typing box.
        let first = HotKeys.shared.register(id: HotKey.ask, keyCode: kVK_Space, modifiers: controlKey | optionKey,
                                            released: { [weak self] in self?.mainKeyUp() }) { [weak self] in self?.mainKeyDown() }
        let second = HotKeys.shared.register(id: HotKey.askToo, keyCode: kVK_ANSI_B, modifiers: controlKey | optionKey) { [weak self] in self?.toggleBar() }
        HotKeys.shared.register(id: HotKey.talk, keyCode: kVK_ANSI_V, modifiers: controlKey | optionKey) { [weak self] in self?.toggleVoice(showOnly: false) }
        HotKeys.shared.register(id: HotKey.talkDo, keyCode: kVK_ANSI_V, modifiers: controlKey | optionKey | shiftKey) { [weak self] in self?.toggleVoice(showOnly: true) }

        let screen = Capture.allowed()
        if !screen, !smoke { Capture.ask() }
        let events = Events.allowed(prompt: !smoke)
        if !Launch.unattended { log.show(activate: false) }       // with nobody watching, the log is only the file
        log.add("Bonsai assistant started", [
            Launch.unattended ? "UNATTENDED: nothing is asked of a person, steps never wait, results are not left on screen" : "",
            Launch.plainServer ? "plain server: nothing is started or loaded through LM Studio; the model the server lists is used and taken to see" : "",
            Launch.plannerSystemFile == nil ? "" : "planner system text: \(Launch.plannerSystemNote)",
            Launch.planEverything ? "every request that is not a question is planned by the model (nothing is done directly)" : "",
            settings.secondLook ? "second look: on (a square around a first answer that is not a named control is looked at once more)" : "",
            "server \(client.base.absoluteString) · image \(settings.imageSide) px · API token \(Launch.unattended ? "not used (unattended)" : Keychain.hasToken ? "stored in the Keychain" : "none")",
            "hold control-option-space and speak; tap it to type: \(first ? "ready" : "NOT available"). Let go and what you said is carried out; Esc cancels",
            "typing: Return does it, Command-Return only points (also control-option-B \(second ? "ready" : "NOT available")); Esc stops everything",
            "speak without holding: control-option-V; it stops listening when you stop talking, or press it again",
            "speech is read by Argmax WhisperKit \(Voice.modelName) in \(Voice.folder): "
                + (Voice.localModel() == nil ? "NOT on disk yet (the first use downloads it; never with nobody at the keyboard)" : "on disk, loaded now in the background"),
            Voice.micFile.map { "IN PLACE OF THE MICROPHONE the sound file \($0) is read, whenever the app listens" } ?? "",
            Launch.pointerURL.map { address in
                pipeline.pointer == nil ? "pointer helper: \(address) is not an address; the language model points"
                    : "pointer helper: pointing is asked of \(PointerHelper.name) at \(address) first, and of the language model whenever that fails; planning, answers and rewriting stay with the language model"
            } ?? "",
            "Screen Recording: \(screen ? "allowed" : "NOT allowed yet for \(AppController.launcher); needed for everything")",
            "Accessibility: \(events ? "allowed" : "NOT allowed yet for \(AppController.launcher); needed to click and type")",
            "this log is also written to \(log.path)",
        ])
        installEditMenu()
        for number in [SIGINT, SIGTERM] {                 // Ctrl-C in Terminal quits properly, so things are put back
            signal(number, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: number, queue: .main)
            source.setEventHandler { [weak self] in self?.quitSoon() }
            source.resume()
            signals.append(source)
        }
        prepareSoon()
        if let helper = pipeline.pointer {                                  // is the pointer helper there? asked once
            Task { @MainActor in
                let health = await helper.health()
                self.log.add(health.ok ? "Pointer helper at \(helper.base.absoluteString) answered (\(health.note))"
                                       : "Pointer helper at \(helper.base.absoluteString) did NOT answer (\(health.note)): the language model points until it does")
            }
        }
        // Have the speech model in memory before the key is first held (not for a batch that never listens).
        if let local = Voice.localModel(), !Launch.unattended || Voice.micFile != nil || Launch.voiceFile != nil {
            Task { @MainActor in
                let start = Date()
                do {
                    try await self.voice.prepare()
                    self.log.add("Speech model ready: WhisperKit \(Voice.modelName) loaded in \(self.sec(Date().timeIntervalSince(start))) from \(local) (from disk; nothing was fetched)")
                } catch {
                    self.log.add("SPEECH MODEL NOT LOADED", ["\(error)"])
                }
            }
        }
        scheduleWatcher()
        statusItem.button?.imagePosition = .imageLeading
        Mac.watchNetwork { [weak self] online in self?.networkChanged(online) }
        if smoke { runSmoke() }
        if Launch.batch != nil || Launch.voiceFile != nil {
            runBatch(file: Launch.batch.map { ($0 as NSString).expandingTildeInPath } ?? "",
                     out: ((Launch.out ?? "~/Library/Logs/BonsaiAssistant/batch.json") as NSString).expandingTildeInPath)
        }
    }

    /// What the process ends with: 0 unless a batch says otherwise (see runBatch).
    private var exitCode: Int32 = 0
    func applicationWillTerminate(_ notification: Notification) {
        if exitCode != 0 { exit(exitCode) }
    }

    private func runSmoke() {
        log.add("SMOKE RUN: windows shown once, no capture, no events, quits by itself")
        let frame = NSScreen.screens.first?.frame ?? .zero
        overlay.hover(.listening)
        overlay.say(.thinking, "", thinking: true)
        overlay.point(at: CGPoint(x: frame.width * 0.5, y: frame.height * 0.4), .acting, "start-up check")
        overlay.drag(from: CGPoint(x: frame.width * 0.4, y: frame.height * 0.5), to: CGPoint(x: frame.width * 0.6, y: frame.height * 0.55), "start-up check: a drag")
        bar.show(corner: overlay.boxCorner(size: InputBar.size))
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            self?.bar.hide()
            self?.overlay.hideAll()
            self?.log.add("SMOKE RUN: overlay, pointer, drag line, label and input bar were shown and hidden")
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 40) { [weak self] in
            self?.log.add("SMOKE RUN: quitting; status was: \(self?.readiness ?? "")")
            self?.quitSoon()
        }
    }

    /// Off the network: the leaf in the menu bar says "offline", and a small badge is shown in
    /// the corner whenever the assistant is out. Nothing here needs the network.
    private func networkChanged(_ online: Bool) {
        statusItem.button?.title = online ? "" : " offline"
        overlay.setOffline(!online)
        log.add(online ? "Network: connected" : "Network: OFFLINE (everything here runs on this Mac)")
    }

    /// Quits from the run loop itself. Quitting from inside a block of the main queue would
    /// leave that queue busy while the app waits for the tidying-up that runs on it: a deadlock.
    private func quitSoon() {
        RunLoop.main.perform(inModes: [.common]) { NSApp.terminate(nil) }
        CFRunLoopWakeUp(CFRunLoopGetMain())
    }

    /// Keeps the screen's read current: the screen is read as soon as the model is ready, and
    /// looked at again every `watchSeconds`; it is read again only when it shows something else.
    private func scheduleWatcher() {
        watcher?.invalidate()
        watcher = nil
        let seconds = settings.watchSeconds
        guard seconds > 0 else { return }
        watcher = Timer.scheduledTimer(withTimeInterval: TimeInterval(seconds), repeats: true) { [weak self] _ in self?.refreshAhead() }
        refreshAhead()
    }

    /// An accessory app shows no menu bar, but paste and friends in its dialogs need these items.
    private func installEditMenu() {
        let main = NSMenu()
        let editItem = NSMenuItem()
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        main.addItem(editItem)
        NSApp.mainMenu = main
    }

    // MARK: LM Studio housekeeping: server up, one model loaded, things put back on quit

    private func setReadiness(_ text: String, ready isReady: Bool, _ details: [String] = []) {
        let changed = text != readiness
        readiness = text
        ready = isReady
        statusItem.button?.toolTip = text
        if changed { log.add(text, details) }
    }

    /// Runs the preparation after any that is still running.
    private func prepareSoon() {
        let previous = preparing
        preparations += 1
        let mine = preparations
        preparing = Task { @MainActor [weak self] in
            await previous?.value
            guard let self else { return }
            await self.prepare()
            if self.preparations == mine { self.preparing = nil }
            if self.settings.watchSeconds > 0 { self.refreshAhead() }
            self.fillModelMenu()
        }
    }

    /// The model used when none was picked in the menu (see ModelChoice): the planner 9B, which
    /// plans steps and also points, before a model that only points, before one as shipped; and
    /// only models that can see when the server says which can. A model picked in the menu stays.
    private func chooseDefaultModel(from list: [String], seeing: [String] = []) {
        guard !list.isEmpty else { return }
        if settings.modelChosenByUser, list.contains(settings.model) { return }
        guard let pick = ModelChoice.best(of: seeing.isEmpty ? list : seeing) else { return }
        if pick != settings.model {
            settings.model = pick
            settings.modelChosenByUser = false
        }
    }

    /// Makes the server answer and the chosen model loaded, and says in one line how it went.
    @MainActor private func prepare() async {
        if Launch.plainServer {
            // Any OpenAI-compatible server (llama.cpp's llama-server, …): there is nothing to
            // start or load. The model is the one named at launch, else the one it lists.
            isStudio = false
            studio = []
            modelSees = true
            do {
                models = try await client.models()
                if Launch.model == nil {
                    if models.count == 1 { settings.runModel = models[0] } else { chooseDefaultModel(from: models) }
                }
                setReadiness(models.isEmpty ? "Server: \(client.base.absoluteString) lists no model"
                                            : "Server ready (plain, \(client.base.absoluteString)): \(settings.model)", ready: !models.isEmpty)
            } catch {
                setReadiness("Server: \(error)", ready: false)
            }
            return
        }
        var listed: [StudioModel]?
        do {
            listed = try await client.studioModels()
        } catch let e as LMError where e.kind == .notFound {
            // Not LM Studio (for example PrismML's llama-server): nothing to start or load.
            isStudio = false
            studio = []
            modelSees = true
            do {
                models = try await client.models()
                chooseDefaultModel(from: models)
                setReadiness(models.isEmpty ? "Server: it lists no model" : "Server ready (not LM Studio): \(settings.model)", ready: !models.isEmpty)
            } catch {
                setReadiness("Server: \(error)", ready: false)
            }
            return
        } catch let e as LMError where e.kind == .unreachable {
            guard client.isLocal, StudioCLI.exists else {
                setReadiness("Server: no answer from \(client.base.absoluteString)", ready: false)
                return
            }
            setReadiness("LM Studio: starting the server…", ready: false)
            let code = await StudioCLI.run(["server", "start", "--port", "\(client.base.port ?? 1234)"])
            for _ in 0..<40 where listed == nil {
                listed = try? await client.studioModels()
                if listed == nil { try? await Task.sleep(nanoseconds: 500_000_000) }
            }
            guard listed != nil else {
                setReadiness("LM Studio: the server did not start (lms server start gave \(code)); open LM Studio once and start it there", ready: false)
                return
            }
            startedServer = true
        } catch {
            setReadiness("LM Studio: \(error)", ready: false)
            return
        }
        isStudio = true
        studio = (listed ?? []).filter { $0.type == "llm" }
        models = studio.map(\.key)
        chooseDefaultModel(from: models, seeing: studio.filter { $0.vision == true }.map(\.key))
        guard let entry = studio.first(where: { $0.key == settings.model }) else {
            setReadiness("LM Studio: it has no language model", ready: false)
            return
        }
        if entry.loaded.isEmpty {
            // 16 GB: one model at a time. Free the memory first, and remember what was there.
            for other in studio where other.key != entry.key {
                for id in other.loaded {
                    setReadiness("LM Studio: unloading \(id) to make room…", ready: false)
                    guard (try? await client.studioUnload(id)) != nil else { continue }
                    if let i = loadedByApp.firstIndex(of: id) {
                        loadedByApp.remove(at: i)
                    } else {
                        displaced.append((other.key, other.contextLength ?? AppController.contextLength))
                    }
                }
            }
            setReadiness("LM Studio: loading \(entry.key)…", ready: false)
            do {
                let loaded = try await client.studioLoad(entry.key, contextLength: AppController.contextLength)
                loadedByApp.append(loaded.instance)
                displaced.removeAll { $0.key == entry.key }
                log.add("    loaded in \(sec(loaded.seconds)), context \(AppController.contextLength) tokens")
            } catch {
                setReadiness("LM Studio: \(error)", ready: false)
                return
            }
            if let again = try? await client.studioModels() { studio = again.filter { $0.type == "llm" } }
        }
        pipeline.model = entry.key
        modelSees = entry.vision == true
        var line = "LM Studio: ready, \(entry.key) loaded"
        if entry.vision != true { line += " — NO vision file beside it: answers about the screen will be guesses" }
        setReadiness(line, ready: true, [startedServer ? "the server was started by this app and is stopped on quit" : ""])
    }

    /// A light refresh of the model list for the menu; changes nothing on the server.
    @MainActor private func refreshList() async {
        guard preparing == nil, isStudio, let again = try? await client.studioModels() else { return }
        studio = again.filter { $0.type == "llm" }
        models = studio.map(\.key)
        fillModelMenu()
    }

    /// Waits for a preparation that is running (or starts one) and says whether a request can go.
    @MainActor private func makeReady(id: Int) async -> Bool {
        if !ready || preparing != nil {
            if preparing == nil { prepareSoon() }
            let wait = preparing
            let ticker = Task { @MainActor [weak self] in
                while !Task.isCancelled, let self, self.runID == id {         // Esc ends the waiting display too
                    self.overlay.say(.thinking, "waking the model", thinking: true)
                    try? await Task.sleep(nanoseconds: 300_000_000)
                }
            }
            await wait?.value
            ticker.cancel()
            guard alive(id) else { return false }
            guard ready else {
                lastEnding = "Stopped: the model is not ready (\(readiness))"
                overlay.say(.sorry, "the model isn't ready")
                overlay.trouble(readiness)
                await linger(10, id: id)
                return false
            }
        }
        guard modelSees else {
            let text = "\(settings.model) cannot see the screen: LM Studio has no vision file beside it. Pick another model in the leaf menu."
            lastEnding = "Stopped: the model cannot see"
            overlay.say(.sorry, "this model can't see")
            overlay.trouble(text)
            log.add("NO VISION", [text])
            await linger(10, id: id)
            return false
        }
        pipeline.model = settings.model
        pipeline.plainStepPrompt = settings.plainStepPrompt
        pipeline.separateImage = !settings.labLayout
        return true
    }

    /// On quit, unless "keep loaded" is ticked: unload what this app loaded, reload what it
    /// unloaded to make room, stop the server if this app started it.
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        stop(note: nil)
        let nothing = loadedByApp.isEmpty && displaced.isEmpty && !startedServer
        guard isStudio, !settings.keepLoaded, !nothing else {
            if settings.keepLoaded { log.add("Quit: the model stays loaded and the server keeps running (keep loaded is ticked)") }
            return .terminateNow
        }
        Task { @MainActor in
            await self.preparing?.value
            for id in self.loadedByApp {
                let ok = (try? await self.client.studioUnload(id)) != nil
                self.log.add("Quit: " + (ok ? "unloaded \(id)" : "could not unload \(id)"))
            }
            if self.startedServer {
                let code = await StudioCLI.run(["server", "stop"])
                self.log.add("Quit: stopped the server this app started (lms server stop gave \(code))")
            } else {
                for model in self.displaced {
                    let ok = (try? await self.client.studioLoad(model.key, contextLength: model.context)) != nil
                    self.log.add("Quit: " + (ok ? "loaded \(model.key) again, as it was before" : "could not load \(model.key) again"))
                }
            }
            NSApp.reply(toApplicationShouldTerminate: true)
        }
        return .terminateLater
    }

    // MARK: menu

    func menuNeedsUpdate(_ menu: NSMenu) {
        guard menu === statusItem.menu else { return }
        rebuild(menu)
        Task { @MainActor in await self.refreshList() }
    }

    private func item(_ title: String, _ action: Selector?, on: Bool? = nil, key: String = "",
                      modifiers: NSEvent.ModifierFlags = []) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.keyEquivalentModifierMask = modifiers
        item.target = self
        if let on { item.state = on ? .on : .off }
        return item
    }

    private func submenu(_ title: String, _ items: [NSMenuItem]) -> NSMenuItem {
        let parent = item(title, nil)
        let menu = NSMenu()
        items.forEach { menu.addItem($0) }
        parent.submenu = menu
        return parent
    }

    private let header = MenuHeader()

    /// How things stand, in a few words, for the top of the menu.
    private var shortStatus: (String, MenuHeader.State) {
        let plain = readiness.replacingOccurrences(of: "LM Studio: ", with: "")
        if ready, !modelSees { return ("\(settings.model) has no vision file", .problem) }
        if ready { return ("Ready · \(settings.model)", .ready) }
        return (plain.prefix(1).uppercased() + plain.dropFirst(), preparing != nil ? .busy : .problem)
    }

    /// The leaf's menu: a header, the three things to do, the few settings that matter, and the
    /// rest one level down.
    private func rebuild(_ menu: NSMenu) {
        menu.removeAllItems()
        let top = NSMenuItem()
        let status = shortStatus
        header.set(status.0, status.1)
        top.view = header
        menu.addItem(top)
        menu.addItem(.separator())

        let how = NSMenuItem(title: "Hold control-option-space and speak; tap it to type", action: nil, keyEquivalent: "")
        how.isEnabled = false
        menu.addItem(how)
        menu.addItem(item("Ask…", #selector(toggleBar), key: " ", modifiers: [.control, .option]))
        menu.addItem(item(voice.listening ? "Finish Speaking" : "Speak Instead…", #selector(talkFromMenu), key: "v", modifiers: [.control, .option]))
        menu.addItem(item("Stop", #selector(stopFromMenu), key: "\u{1b}"))
        menu.addItem(.separator())

        let model = item("Model", nil)
        model.submenu = modelMenu
        fillModelMenu()
        menu.addItem(model)
        menu.addItem(submenu("Screenshot Size", [1280, 896].map { side in
            let choice = item(side == 1280 ? "1280 px · more accurate" : "896 px · twice as fast", #selector(pickSize(_:)), on: settings.imageSide == side)
            choice.tag = side
            return choice
        }))
        menu.addItem(submenu("Read the Screen Ahead", [(30, "Every 30 Seconds"), (60, "Every Minute"), (0, "Only When Asked")].map { seconds, title in
            let choice = item(title, #selector(pickWatch(_:)), on: settings.watchSeconds == seconds)
            choice.tag = seconds
            return choice
        }))
        menu.addItem(.separator())

        menu.addItem(item("Speak Answers", #selector(toggleSpeak), on: settings.speak))
        menu.addItem(item("Answer in a Sentence", #selector(toggleSentence), on: settings.sentence))
        menu.addItem(item("Confirm Each Step", #selector(toggleContinuous), on: !settings.continuous))
        menu.addItem(item("Find Controls by Name First", #selector(toggleLabels), on: settings.useLabels))
        menu.addItem(.separator())

        menu.addItem(submenu("Advanced", [
            item("Server Address…", #selector(editServer)),
            item(Keychain.hasToken ? "API Token… (stored)" : "API Token…", #selector(editToken)),
            .separator(),
            item("Snap Clicks to Controls", #selector(toggleSnap), on: settings.snap),
            item("Second Look for Small Targets", #selector(toggleSecondLook), on: settings.secondLook),
            item("Keep Model Loaded on Quit", #selector(toggleKeep), on: settings.keepLoaded),
            item("Lab Prompt Layout", #selector(toggleLab), on: settings.labLayout),
            item("Plan from Screenshots (older)", #selector(togglePlain), on: settings.plainStepPrompt),
            .separator(),
            item("Check Permissions", #selector(checkPermissions)),
        ]))
        menu.addItem(item("Show Log", #selector(showLog)))
        menu.addItem(.separator())
        menu.addItem(item("Quit Bonsai", #selector(quit), key: "q", modifiers: [.command]))
    }

    private func fillModelMenu() {
        modelMenu.removeAllItems()
        if models.isEmpty {
            let none = item(preparing != nil ? "Asking the server…" : "No models found", nil)
            none.isEnabled = false
            modelMenu.addItem(none)
        }
        for id in models {
            var title = id
            if let entry = studio.first(where: { $0.key == id }), entry.vision != true { title += "  ·  no vision" }
            else if ModelChoice.isPlanner(id) { title += "  ·  plans and points" }
            else if ModelChoice.isPointer(id) { title += "  ·  points only" }
            let m = item(title, #selector(pickModel(_:)), on: id == settings.model)
            m.representedObject = id
            modelMenu.addItem(m)
        }
        modelMenu.addItem(.separator())
        modelMenu.addItem(item("Check Again", #selector(refreshFromMenu)))
    }

    @objc private func toggleBar() {
        if bar.isShown {
            bar.hide()
            overlay.retreat()
        } else {
            stop(note: nil)
            overlay.hover(nil)                                   // the arrow comes out; the typing box takes the note's place
            bar.show(corner: overlay.boxCorner(size: InputBar.size))
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.32) { [weak self] in      // once it is out, it idles until you type
                if let self, self.bar.isShown { self.overlay.idle(true) }
            }
            refreshAhead()
        }
    }
    @objc private func talkFromMenu() { toggleVoice(showOnly: false) }
    @objc private func toggleReadAhead() { settings.readAhead.toggle() }
    @objc private func pickWatch(_ sender: NSMenuItem) {
        settings.watchSeconds = sender.tag
        log.add(sender.tag > 0 ? "The screen is read at start and looked at again every \(sender.tag) s; it is read again when it has changed"
                               : "The screen is read only when the bar opens or a request is made")
        scheduleWatcher()
    }
    @objc private func toggleLab() {
        settings.labLayout.toggle()
        log.add(settings.labLayout ? "Prompt layout: screenshot and question in one message (as measured in the lab; no read is reused)"
                                   : "Prompt layout: the screenshot in its own message (its read is reused for further questions)")
    }

    // MARK: reading ahead

    /// Captures the screen and, unless what it shows has already been read, has the server read
    /// it: at start, on the timer, when the bar opens, when listening starts and after a request.
    /// Only with the screenshot in its own message: otherwise the read cannot be reused.
    private func refreshAhead() {
        guard ready, modelSees, settings.readAhead, !settings.labLayout, run == nil, !refreshing, Capture.allowed() else { return }
        refreshing = true
        Task { @MainActor in
            defer { self.refreshing = false }
            guard let now = try? await Capture.mainDisplay() else { return }
            if let early = self.ahead {
                let differing = await Task.detached { ImageOps.differingPixels(early.sent.shot.full, now.full) }.value
                if differing < ImageOps.sameScreenBelow { return }                    // already read, or being read
            }
            guard self.run == nil, let sent = try? await self.look(reuse: now), self.run == nil else { return }
            self.ahead?.read.cancel()
            self.pipeline.model = self.settings.model
            self.pipeline.separateImage = true
            let pipeline = self.pipeline
            let read = Task { () -> Double? in (try? await pipeline.readAhead(imageURL: sent.url))?.seconds }
            self.ahead = Ahead(sent: sent, started: Date(), read: read)
            Task { @MainActor in
                if let seconds = await read.value { self.log.add("screen read ahead in \(self.sec(seconds)); the next request about it takes about a second") }
            }
        }
    }

    /// The first look of a request: the screenshot that was read ahead if the screen still shows
    /// the same thing (waiting for that read to finish), a new capture otherwise.
    @MainActor private func firstLook(id: Int) async throws -> (sent: Sent, note: String?) {
        guard let early = ahead else { return (try await look(), nil) }
        ahead = nil
        let now = try await Capture.mainDisplay()
        let differing = await Task.detached { ImageOps.differingPixels(early.sent.shot.full, now.full) }.value
        guard differing < ImageOps.sameScreenBelow else {
            early.read.cancel()
            return (try await look(reuse: now), "the screen changed since it was read ahead (\(differing) differing pixels): read again")
        }
        let waitStart = Date()
        let seconds = await early.read.value
        let waited = Date().timeIntervalSince(waitStart)
        let lead = waitStart.timeIntervalSince(early.started)
        guard let seconds else { return (early.sent, "the read ahead failed; the screen is read now") }
        return (early.sent, "read ahead: started \(sec(lead)) before the request, took \(sec(seconds)), waited \(sec(waited)) for it")
    }

    // MARK: spoken requests (Argmax WhisperKit)

    /// The main key goes down. With the typing box open it closes it, as it always did.
    /// Otherwise recording starts at once (so that the first word is not lost) and the pointer
    /// comes out with "Listening…"; what the press was is decided when the key is let go.
    private func mainKeyDown() {
        guard held == nil else { return }                                   // the key repeating
        if bar.isShown || voice.listening {
            toggleBar()
            return
        }
        stop(note: nil, keepPointer: true)                                  // as a tap always did: what is running stops
        held = Date()
        holdNumber += 1
        let me = holdNumber
        holdProblem = nil
        voiceShowOnly = false
        overlay.hover(.listening, "Listening…")
        HotKeys.shared.register(id: HotKey.escape, keyCode: kVK_Escape) { [weak self] in self?.cancelHold() }
        listenTimer?.invalidate()
        var upSince: Date?
        listenTimer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30, repeats: true) { [weak self] timer in
            guard let self, let pressed = self.held, self.holdNumber == me else { return timer.invalidate() }
            self.overlay.hover(.listening, "Listening…")                    // stays with the mouse
            // Should the key's release ever go unreported, the hold must still end: when the key
            // has been up for a second by the system's own account, or after 30 s.
            if CGEventSource.keyState(.combinedSessionState, key: CGKeyCode(kVK_Space)) { upSince = nil } else if upSince == nil { upSince = Date() }
            let lost = upSince.map { Date().timeIntervalSince($0) > 1.0 } ?? false
            if lost || Date().timeIntervalSince(pressed) > 30 {
                self.log.add(lost ? "    the key is up, but its release was not reported: taken as let go" : "    held for 30 s: taken as let go")
                self.mainKeyUp()
            }
        }
        holdStarting = Task { @MainActor in
            do {
                try await self.voice.start()
            } catch {
                if self.holdNumber == me { self.holdProblem = error }
            }
            // let go as a tap, or cancelled, before the recording had begun: it is dropped now
            if self.holdNumber != me, self.held == nil { self.voice.cancel() }
        }
    }

    /// The main key is let go: a tap opens the typing box (the recording is dropped); a hold
    /// is a spoken request, read and carried out with no further key.
    private func mainKeyUp() {
        guard let pressed = held else { return }
        held = nil
        listenTimer?.invalidate()
        let me = holdNumber
        let starting = holdStarting
        switch PushToTalk.release(pressed: pressed, released: Date()) {
        case .tap:
            holdNumber += 1
            voice.cancel()
            HotKeys.shared.unregister(id: HotKey.escape)
            toggleBar()
        case .hold:
            Task { @MainActor in
                await starting?.value                                       // the recording has begun, or could not
                guard self.holdNumber == me else { return }                 // cancelled meanwhile
                if let problem = self.holdProblem {
                    self.overlay.say(.sorry, "can't listen")
                    self.overlay.trouble("\(problem)")
                    self.log.add("VOICE ERROR", ["\(problem)"])
                    HotKeys.shared.unregister(id: HotKey.escape)
                    try? await Task.sleep(nanoseconds: 8_000_000_000)
                    if self.holdNumber == me, self.run == nil, !self.bar.isShown { self.overlay.hideAll() }
                    return
                }
                await self.finishHold(me)
            }
        }
    }

    /// Esc while the key is held or while the recording is read: nothing is done.
    private func cancelHold() {
        holdNumber += 1
        held = nil
        listenTimer?.invalidate()
        voice.cancel()
        stop(note: nil)
        log.add("Spoken request cancelled")
    }

    @MainActor private func finishHold(_ me: Int) async {
        overlay.say(.thinking, "hmm")
        do {
            let heard = try await voice.finish()
            guard holdNumber == me else { return }                          // Esc while it was being read
            log.add("VOICE (held)  \"\(heard.text)\"", [
                "Argmax WhisperKit \(Voice.modelName): \(sec(heard.heard)) of sound, \(sec(heard.voiced)) of it voice, read in \(sec(heard.seconds))",
                Voice.micFile.map { "the sound came from the file \($0), in place of the microphone" } ?? "",
                heard.text.isEmpty ? (PushToTalk.caught(voiced: heard.voiced) ? "no words were made out" : "less than \(PushToTalk.voiceSeconds) s of voice: not read, nothing is done") : ""])
            guard !heard.text.isEmpty else {
                overlay.say(.lost, "I did not catch that")
                HotKeys.shared.unregister(id: HotKey.escape)
                try? await Task.sleep(nanoseconds: 2_500_000_000)
                if holdNumber == me, run == nil, !voice.listening, !bar.isShown { overlay.hideAll() }
                return
            }
            overlay.say(.heard, "\"\(heard.text.count > 56 ? String(heard.text.prefix(54)) + "…" : heard.text)\"")
            lastHeard = heard
            ask(heard.text, showOnly: false, keepPointer: true)
        } catch {
            guard holdNumber == me else { return }
            overlay.say(.sorry, "couldn't hear that")
            overlay.trouble("\(error)")
            log.add("VOICE ERROR", ["\(error)"])
            HotKeys.shared.unregister(id: HotKey.escape)
        }
    }

    /// The hotkey: the pointer comes out beside the mouse cursor with a small note, "Listening…".
    /// Listening ends by itself about a second after the speaker stops, or when the hotkey is
    /// pressed again; then what was said is carried out.
    private func toggleVoice(showOnly: Bool) {
        if voice.listening {
            Task { @MainActor in await self.finishVoice() }
            return
        }
        stop(note: nil)
        voiceShowOnly = showOnly
        bar.hide()
        overlay.hover(.thinking, Voice.localModel() == nil ? "getting my ears" : "one sec")
        HotKeys.shared.register(id: HotKey.escape, keyCode: kVK_Escape) { [weak self] in
            self?.listenTimer?.invalidate()
            self?.voice.cancel()
            self?.stop(note: nil)
            self?.log.add("Spoken request cancelled")
        }
        Task { @MainActor in
            do {
                try await self.voice.start()
                let began = Date()
                self.overlay.hover(.listening)
                self.refreshAhead()
                self.listenTimer?.invalidate()
                self.listenTimer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30, repeats: true) { [weak self] timer in
                    guard let self, self.voice.listening else { return timer.invalidate() }
                    self.overlay.hover(.listening)                         // stays with the mouse
                    if self.voice.saidAndQuiet || Date().timeIntervalSince(began) > 25 {
                        timer.invalidate()
                        Task { @MainActor in await self.finishVoice() }
                    }
                }
            } catch {
                self.overlay.say(.sorry, "can't listen")
                self.overlay.trouble("\(error)")
                self.log.add("VOICE ERROR", ["\(error)"])
                HotKeys.shared.unregister(id: HotKey.escape)
                try? await Task.sleep(nanoseconds: 8_000_000_000)
                if !self.voice.listening && self.run == nil { self.overlay.hideAll() }
            }
        }
    }

    @MainActor private func finishVoice() async {
        guard voice.listening else { return }
        listenTimer?.invalidate()
        overlay.say(.thinking, "hmm")
        do {
            let heard = try await voice.finish()
            log.add("VOICE  \"\(heard.text)\"", ["Argmax WhisperKit \(Voice.modelName): \(sec(heard.heard)) of sound read in \(sec(heard.seconds))"])
            guard !heard.text.isEmpty else {
                overlay.say(.lost)
                HotKeys.shared.unregister(id: HotKey.escape)
                try? await Task.sleep(nanoseconds: 2_500_000_000)
                if run == nil, !voice.listening { overlay.hideAll() }
                return
            }
            overlay.say(.heard, "\"\(heard.text.count > 56 ? String(heard.text.prefix(54)) + "…" : heard.text)\"")
            lastHeard = heard
            ask(heard.text, showOnly: voiceShowOnly, keepPointer: true)
        } catch {
            overlay.say(.sorry, "couldn't hear that")
            overlay.trouble("\(error)")
            log.add("VOICE ERROR", ["\(error)"])
            HotKeys.shared.unregister(id: HotKey.escape)
        }
    }
    @objc private func stopFromMenu() { stop(note: "Stopped from the menu") }
    @objc private func pickModel(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String else { return }
        guard id != settings.model || !ready else { return }
        stop(note: "Stopped: the model was changed")
        settings.model = id
        settings.modelChosenByUser = true
        log.add("Model: \(id)")
        ready = false
        prepareSoon()                               // unloads the previous model, loads this one
    }
    @objc private func pickSize(_ sender: NSMenuItem) {
        settings.imageSide = sender.tag
        log.add("Image size: \(sender.tag) px on the longer side")
    }
    @objc private func refreshFromMenu() { prepareSoon() }
    @objc private func toggleKeep() { settings.keepLoaded.toggle() }
    @objc private func toggleLabels() {
        settings.useLabels.toggle()
        log.add(settings.useLabels ? "A target named exactly like one control in the front window is found by that name, without the model"
                                   : "Every target is found by the model (names of controls are not looked up first)")
    }
    @objc private func toggleSecondLook() {
        settings.secondLook.toggle()
        log.add(settings.secondLook ? "Second look: when something looked for is not a control the Mac can name, a square around the first answer is looked at once more (a second read)"
                                    : "Second look: off")
    }
    @objc private func toggleSnap() {
        settings.snap.toggle()
        log.add(settings.snap ? "Clicks go to the control at or beside the model's point" : "Clicks go to the model's bare point")
    }

    /// The token is typed here by the user, stored in the Keychain and nowhere else.
    @objc private func editToken() {
        let stored = Keychain.hasToken
        let alert = NSAlert()
        alert.messageText = "API token"
        alert.informativeText = "Only needed when LM Studio's server is set to require one (Developer > Server Settings > Manage Tokens). "
            + "It is kept in the macOS Keychain, sent with each request, and never written to the log. "
            + (stored ? "A token is stored now." : "No token is stored.")
        let field = NSSecureTextField(frame: CGRect(x: 0, y: 0, width: 320, height: 24))
        field.placeholderString = stored ? "a new token replaces the stored one" : "paste the token"
        alert.accessoryView = field
        alert.addButton(withTitle: "Save")
        alert.addButton(withTitle: "Cancel")
        if stored { alert.addButton(withTitle: "Remove the token") }
        NSApp.activate(ignoringOtherApps: true)
        alert.window.initialFirstResponder = field
        let choice = alert.runModal()
        if choice == .alertFirstButtonReturn {
            let typed = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !typed.isEmpty else { return }
            log.add(Keychain.set(typed) ? "API token stored in the Keychain" : "The API token could not be stored in the Keychain")
        } else if choice == .alertThirdButtonReturn {
            Keychain.set(nil)
            log.add("API token removed from the Keychain")
        } else {
            return
        }
        ready = false
        prepareSoon()
    }
    @objc private func toggleSentence() { settings.sentence.toggle() }
    @objc private func toggleSpeak() { settings.speak.toggle() }
    @objc private func toggleContinuous() {
        settings.continuous.toggle()
        log.add("Do it: " + (settings.continuous ? "steps run without asking (Esc stops)" : "each step waits for Return"))
    }
    @objc private func togglePlain() { settings.plainStepPrompt.toggle() }
    @objc private func showLog() { log.show(activate: true) }
    @objc private func quit() { NSApp.terminate(nil) }

    @objc private func checkPermissions() {
        let screen = Capture.allowed()
        if !screen { Capture.ask() }
        let events = Events.allowed(prompt: true)
        log.add("Permissions", ["Screen Recording: \(screen ? "allowed" : "NOT allowed; after allowing it, quit and start again")",
                                "Accessibility: \(events ? "allowed" : "NOT allowed for \(AppController.launcher); needed to click and type")"])
        log.show(activate: true)
    }

    @objc private func editServer() {
        let alert = NSAlert()
        alert.messageText = "Server address"
        alert.informativeText = "An OpenAI-compatible server. LM Studio's is http://localhost:1234/v1"
        let field = NSTextField(frame: CGRect(x: 0, y: 0, width: 320, height: 24))
        field.stringValue = settings.server
        alert.accessoryView = field
        alert.addButton(withTitle: "Save")
        alert.addButton(withTitle: "Cancel")
        NSApp.activate(ignoringOtherApps: true)
        alert.window.initialFirstResponder = field
        guard alert.runModal() == .alertFirstButtonReturn, let url = LMClient.url(from: field.stringValue) else { return }
        settings.server = url.absoluteString
        client.base = url
        log.add("Server address: \(url.absoluteString)")
        ready = false
        prepareSoon()
    }

    // MARK: starting and stopping a request

    /// A request from the bar or the microphone, sent the way it should go (see Router):
    /// done directly when no model is needed (an app, a site, windows side by side, dark mode,
    /// the volume, a folder, a calendar event); worked on the selected text (rewrite, translate,
    /// summarise); answered in words, or by pointing when it asks where something is; carried
    /// out as spelled ("click …, then type …"); or planned by the model one step at a time.
    /// `showOnly` never acts.
    private func ask(_ request: String, showOnly: Bool, keepPointer: Bool = false) {
        stop(note: nil, keepPointer: keepPointer)
        overlay.say(.thinking, "", thinking: true)                          // out beside the cursor if it is not already
        runID += 1
        let id = runID
        Events.cancelled = false
        moreToCome = false
        carried = []
        lastCarried = ""
        lastTyped = ""
        HotKeys.shared.register(id: HotKey.escape, keyCode: kVK_Escape) { [weak self] in self?.stop(note: "Stopped with Esc") }
        let parts = showOnly ? [request] : Router.parts(request, app: Apps.resolve)
        let heard = lastHeard
        lastHeard = nil
        if Launch.batch == nil, Launch.voiceFile == nil {                   // a batch keeps its own account
            trace = []
            lastEnding = ""
            lastSpoken = ""
        }
        run = Task { @MainActor [weak self] in
            guard let self else { return }
            defer { self.noteForOut(request, heard: heard) }
            guard parts.count > 1 else {
                await self.runOne(request, showOnly: showOnly, id: id)
                return
            }
            // A request that says one thing comes after another: each part is a request of its
            // own, so each can take a direct route, and the next starts only when one ended well.
            self.log.add("REQUEST IN \(parts.count) PARTS  \"\(request)\"", parts.enumerated().map { "\($0.offset + 1). \($0.element)" })
            var endings: [String] = []
            for (i, part) in parts.enumerated() {
                self.moreToCome = i < parts.count - 1
                self.lastEnding = ""
                let from = self.trace.count
                let back = i > 0 && Router.refersBack(part, apps: Apps.list)
                await self.runOne(part, showOnly: false, id: id, already: back ? self.carried : [], earlier: back ? Array(parts[..<i]) : [])
                for k in from..<self.trace.count { self.trace[k]["part"] = i + 1 }
                guard self.alive(id) else {
                    self.moreToCome = false
                    return
                }
                endings.append(self.lastEnding)
                guard self.lastEnding.hasPrefix("Done") || self.lastEnding.hasPrefix("Answered") else {
                    let stopped = "Stopped at part \(i + 1) of \(parts.count) (\(part)): \(self.lastEnding)"
                    self.lastEnding = stopped
                    self.log.add(stopped)
                    if self.moreToCome {                                    // the part did not put things away: do it now
                        self.moreToCome = false
                        await self.linger(6, id: id)
                    }
                    return
                }
            }
            self.lastEnding = "Done, \(parts.count) parts: " + endings.joined(separator: " | ")
            self.log.add(self.lastEnding)
        }
    }

    /// With --out and no batch (the app run by hand, or with a held key on a test rig): each
    /// request as it ends is added to the steps file, in the shape a batch writes.
    private func noteForOut(_ request: String, heard: Voice.Heard?) {
        guard let out = Launch.out, Launch.batch == nil, Launch.voiceFile == nil else { return }
        let ending = lastEnding.isEmpty ? "Stopped" : lastEnding
        var entry: [String: Any] = ["request": request, "model": settings.model, "ending": ending,
                                    "ok": ending.hasPrefix("Done") || ending.hasPrefix("Answered"),
                                    "kind": Router.kind(Router.route(request, app: Apps.resolve)), "steps": trace, "spoken": lastSpoken]
        if let heard {
            entry["heard"] = heard.text
            entry["heard_seconds"] = (heard.seconds * 100).rounded() / 100
            entry["sound_seconds"] = (heard.heard * 100).rounded() / 100
            entry["voiced_seconds"] = heard.voiced
        }
        session.append(entry)
        let path = (out as NSString).expandingTildeInPath
        try? FileManager.default.createDirectory(atPath: (path as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
        if let data = try? JSONSerialization.data(withJSONObject: session, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: URL(fileURLWithPath: path))
        }
    }

    /// One request, or one part of a request, sent the way it should go. `already`: what the
    /// parts before it did, when this part refers back to them.
    @MainActor private func runOne(_ request: String, showOnly: Bool, id: Int, already: [String] = [], earlier: [String] = []) async {
        var route = Router.route(request, showOnly: showOnly, app: Apps.resolve)
        if Launch.planEverything {
            switch route {
            case .direct, .scripted: route = .plan
            default: break
            }
        }
        var needsModel = true                                               // what needs no model does not wait for one
        if case .direct(let steps) = route, !steps.contains(where: { $0.action == Recipes.draftEmail }) { needsModel = false }
        if case .answer = route, Talk.fact(request) != nil { needsModel = false }
        if case .text(let skill) = route, skill.instruction.isEmpty { needsModel = false }
        if needsModel { guard await makeReady(id: id) else { return } }
        switch route {
        case .point: await showMe(request, id: id)
        case .answer(let screen): await answer(request, fromScreen: screen, id: id)
        case .text(let skill): await runTextSkill(request, skill, id: id)
        case .direct(let steps): await runRecipe(request, steps: steps, id: id)
        case .scripted(let steps): await doIt(request, scripted: steps, id: id)
        case .plan:
            if settings.plainStepPrompt {
                await doIt(request, id: id)                                 // the older way: planned from screenshots
            } else {
                // The one app the request speaks of is opened before the planner is asked (a part
                // of a longer request would otherwise carry on in the app of the part before).
                var told = already
                let named = AppNames.named(in: request, among: Apps.list)
                if named.count == 1, NSWorkspace.shared.frontmostApplication?.localizedName != named[0] {
                    stepNote = nil
                    let failure = await carryOut(PlannedStep(action: "open_app", app: named[0]), at: nil)
                    guard alive(id) else { return }
                    log.add("BEFORE PLANNING  \(named[0]) is the one app this speaks of: opened first" + (failure.map { " (FAILED: \($0))" } ?? ""))
                    told.append("open_app \(named[0])" + ((failure ?? stepNote).map { " (\($0))" } ?? ""))
                    trace.append(["step": 0, "tool": "open_app", "line": "open_app \(named[0])", "result": failure ?? "ok", "by": "the app, before planning"])
                    try? await Task.sleep(nanoseconds: 500_000_000)
                }
                // One command of the menu bar asked for by its name is chosen directly, and counts
                // when its title flipped (Show to Hide) or its tick changed.
                if earlier.isEmpty {
                    let chosen = await choseMenuCommand(request, id: id)
                    if chosen.done { return }
                    if let line = chosen.told { told.append(line) }            // chosen, but not seen to take: the planner is told
                }
                guard alive(id) else { return }
                await runPlanner(Router.task(request, earlier: earlier), id: id, already: told)
            }
        }
    }

    /// "Show the status bar in Finder": when the request names one command of the front app's
    /// menu bar, it is chosen through Accessibility. True when that finished the request: the
    /// item's title is gone from its menu (Show became Hide) or its tick changed.
    @MainActor private func choseMenuCommand(_ request: String, id: Int) async -> (done: Bool, told: String?) {
        // only a short request with nothing to type can be one command
        guard request.split(separator: " ").count <= 10, !request.contains("\""), !request.contains("“") else { return (false, nil) }
        let before = await Task.detached { Access.menuCommands() }.value
        let front = NSWorkspace.shared.frontmostApplication?.localizedName ?? ""
        guard let i = MenuCommand.match(request: request, items: before.map { ($0.menu, $0.title) }, app: front) else { return (false, nil) }
        let item = before[i], path = "\(item.menu) > \(item.title)"
        let start = Date()
        overlay.say(.acting, captioned(1, "Choosing \(path)"))
        guard await Task.detached(operation: { Access.menu(path: path) }).value else { return (false, nil) }
        try? await Task.sleep(nanoseconds: 900_000_000)
        guard alive(id) else { return (true, nil) }
        let after = await Task.detached { Access.menuCommands() }.value
        let same = after.first { $0.menu == item.menu && $0.title == item.title }
        let took = Date().timeIntervalSince(start)
        let flipped = same == nil || same?.mark != item.mark
        log.add("DO IT  \"\(request)\"", ["the request names a command of \(front)'s menu bar: menu \(path)",
                                          flipped ? "chosen, and the item changed (its title or its tick): done in \(sec(took))" : "chosen, but the item reads the same: the planner goes on"])
        trace.append(["step": 1, "tool": "menu", "line": "menu \(path)", "result": flipped ? "ok" : "the item reads the same afterwards",
                      "step_seconds": (took * 100).rounded() / 100, "by": "the app, by the command's name"])
        guard flipped else { return (false, "menu \(path)") }
        lastEnding = "Done (1 step)"
        log.add(lastEnding)
        await finished(id: id)
        return (true, nil)
    }

    /// Esc: everything stops at once. Nothing more is asked, shown, spoken or done.
    private func stop(note: String?, keepPointer: Bool = false) {
        let wasRunning = run != nil
        run?.cancel()
        run = nil
        moreToCome = false
        runID += 1
        Events.cancelled = true
        if let waiting = confirm {
            confirm = nil
            waiting.resume(returning: false)
        }
        speaker.stopSpeaking(at: .immediate)
        for id in [HotKey.escape, HotKey.ret, HotKey.enter] { HotKeys.shared.unregister(id: id) }
        listenTimer?.invalidate()
        if !keepPointer { overlay.retreat() }
        if let note, wasRunning { log.add(note) }
    }

    private func alive(_ id: Int) -> Bool { id == runID && !Task.isCancelled }

    /// Leaves the result on screen for a while, then clears it and gives Esc back to other apps.
    @MainActor private func linger(_ seconds: Double, id: Int) async {
        if moreToCome {                                                         // the next part follows: a moment, and nothing is put away
            try? await Task.sleep(nanoseconds: 700_000_000)
            return
        }
        let seconds = Launch.unattended ? min(seconds, 0.8) : seconds          // nobody is reading it
        try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
        guard alive(id) else { return }
        HotKeys.shared.unregister(id: HotKey.escape)
        overlay.retreat()
        run = nil
        if settings.watchSeconds > 0 { refreshAhead() }
    }

    @MainActor private func fail(_ error: Error, id: Int) async {
        if error is CancellationError || !alive(id) { return }
        lastEnding = "Error: \(error)"
        overlay.say(.sorry, "something went wrong")
        overlay.trouble("\(error)")
        log.add("ERROR", ["\(error)"])
        if error is LMError { ready = false }          // look at the server again before the next request
        await linger(9, id: id)
    }

    private func say(_ text: String) {
        lastSpoken = text                                    // kept for a batch's steps file, where nothing is said aloud
        guard settings.speak, !text.isEmpty else { return }
        speaker.speak(AVSpeechUtterance(string: text))
    }

    /// The end of something done: a check mark and a word beside the pointer, and "Done" (or
    /// the model's closing sentence) aloud when answers are spoken.
    @MainActor private func finished(_ text: String = "", id: Int) async {
        let closing = text.trimmingCharacters(in: .whitespacesAndNewlines)
        overlay.say(.done, "✓ " + (closing.isEmpty ? "done" : closing))
        if moreToCome {                                                         // not the end yet: nothing is said aloud
            await linger(0.7, id: id)
            return
        }
        say(closing.isEmpty ? "Done." : closing)
        await lingerSpoken(closing.isEmpty ? 2.6 : Answers.readingSeconds(closing), id: id)
    }

    /// Leaves what was said on screen for the given time, and at least until it has been
    /// spoken to the end (Esc still stops it meanwhile).
    @MainActor private func lingerSpoken(_ seconds: Double, id: Int) async {
        let start = Date()
        try? await Task.sleep(nanoseconds: 300_000_000)
        while alive(id), speaker.isSpeaking { try? await Task.sleep(nanoseconds: 250_000_000) }
        guard alive(id) else { return }
        await linger(max(1.2, seconds - Date().timeIntervalSince(start)), id: id)
    }

    /// The step in hand, in a few words, in the box beside the pointer.
    private func captioned(_ n: Int, _ caption: String) -> String {
        "\(n) · \(caption.count > 52 ? String(caption.prefix(50)) + "…" : caption)"
    }

    private func sec(_ x: Double) -> String { String(format: "%.2f s", x) }
    private func pt(_ p: CGPoint) -> String { String(format: "(%.1f, %.1f)", p.x, p.y) }
    private func grid(_ p: CGPoint) -> String { String(format: "(%.0f, %.0f)", p.x, p.y) }

    // MARK: looking

    private struct Sent {
        let shot: Shot
        let image: CGImage
        let url: String
        let seconds: Double                // shrinking and encoding
        var size: String { "\(image.width) x \(image.height) px" }
    }

    /// Captures the main display (or takes a capture already made) and prepares what is sent.
    @MainActor private func look(reuse: Shot? = nil) async throws -> Sent {
        if !Capture.allowed() { Capture.ask() }
        let shot: Shot
        if let reuse { shot = reuse } else { shot = try await Capture.mainDisplay() }
        let side = settings.imageSide
        let start = Date()
        let prepared: (CGImage, String)? = await Task.detached(priority: .userInitiated) {
            let small = ImageOps.shrunk(shot.full, longSide: side)
            guard let url = ImageOps.dataURL(small) else { return nil }
            return (small, url)
        }.value
        guard let prepared else { throw CaptureError(description: "The screenshot could not be encoded") }
        return Sent(shot: shot, image: prepared.0, url: prepared.1, seconds: Date().timeIntervalSince(start))
    }

    private func screenNote(_ sent: Sent) -> String {
        "image \(sent.size) of a \(Int(sent.shot.region.width)) x \(Int(sent.shot.region.height)) pt display (\(String(format: "%.1f", sent.shot.scale)) px per pt)"
    }

    // MARK: show me

    @MainActor private func showMe(_ request: String, id: Int) async {
        let start = Date()
        overlay.say(.thinking, "", thinking: true)
        do {
            let (sent, aheadNote) = try await firstLook(id: id)
            guard alive(id) else { return }
            let out = try await pipeline.point(imageURL: sent.url, instruction: request, looks: settings.secondLook ? 2 : 1)
            guard alive(id) else { return }
            let total = Date().timeIntervalSince(start)
            var lines = ["model \(pipeline.model) · \(screenNote(sent))",
                         "capture \(sec(sent.shot.seconds)) · shrink and encode \(sec(sent.seconds)) · model \(sec(out.chat.seconds)) (\(out.chat.tokenNote)) · total \(sec(total))",
                         "model wrote: \(out.chat.written)"]
            if let aheadNote { lines.append(aheadNote) }
            if let note = out.note { lines.append("note: \(note)") }

            guard let g = out.answer.point else {
                let refused = out.answer == .refusal
                lines.append(refused ? "the model says it is not on this screen" : "no point could be read from the answer")
                log.add("SHOW ME  \"\(request)\"", lines)
                lastEnding = refused ? "Stopped: the model says it is not on this screen" : "Stopped: no point could be read from the answer"
                trace.append(["step": 1, "tool": "point", "line": request, "result": refused ? "not on this screen" : "no point",
                              "plan_seconds": (out.chat.seconds * 100).rounded() / 100, "pointer": out.pointer])
                overlay.say(.sorry, refused ? "can't see that here" : "not sure where that is")
                if refused { say("I can't find that on this screen.") }
                await linger(8, id: id)
                return
            }
            var p = Geometry.screenPoint(grid: g, region: sent.shot.region)
            lines.append("point: grid \(grid(g)) -> screen \(pt(p)) pt")
            if settings.snap {
                let model = p
                let snapped = await Task.detached { Access.snap(model, target: request) }.value
                if snapped.0 != p { lines.append("the pointer goes to \(snapped.1) at screen \(pt(snapped.0)) pt") }
                p = snapped.0
            }
            log.add("SHOW ME  \"\(request)\"", lines)
            lastEnding = "Done: pointed at screen \(pt(p)) pt"
            trace.append(["step": 1, "tool": "point", "line": request, "result": "ok", "x": (p.x * 10).rounded() / 10, "y": (p.y * 10).rounded() / 10,
                          "plan_seconds": (out.chat.seconds * 100).rounded() / 100, "pointer": out.pointer])
            overlay.point(at: p, .answer, "here!")

            if settings.sentence {
                let answer = try await pipeline.sentence(imageURL: sent.url, request: request)
                guard alive(id) else { return }
                let text = answer.content.trimmingCharacters(in: .whitespacesAndNewlines)
                log.add("    sentence (\(sec(answer.seconds)), \(answer.tokenNote)): \(text.isEmpty ? answer.written : text)")
                if !text.isEmpty {
                    overlay.say(.answer, text)
                    say(text)
                }
            }
            await linger(14, id: id)
        } catch {
            await fail(error, id: id)
        }
    }

    // MARK: answers in words

    /// The last question and its answer, while they are fresh, so that "and the one next to
    /// it?" is understood.
    private var earlier: (question: String, answer: String)? {
        guard let last = lastExchange, !last.question.isEmpty, Date().timeIntervalSince(last.at) < 300 else { return nil }
        return (last.question, last.answer)
    }

    /// Shows an answer in the box beside the pointer, says it aloud when that is switched on,
    /// and keeps it for a follow-up.
    @MainActor private func tell(_ text: String, question: String, id: Int, how: String = "", seconds: Double = 0, tokens: String = "") async {
        lastExchange = (question, text, Date())
        lastEnding = "Answered: \(text)"
        var entry: [String: Any] = ["step": trace.count + 1, "tool": "answer", "line": text, "result": "ok"]
        if !how.isEmpty { entry["how"] = how }
        if seconds > 0 { entry["plan_seconds"] = (seconds * 100).rounded() / 100 }
        if !tokens.isEmpty { entry["tokens"] = tokens }
        trace.append(entry)
        overlay.say(.answer, text)
        say(text)
        if moreToCome, !Launch.unattended {                                     // an answer in the middle of a request: time to read it
            try? await Task.sleep(nanoseconds: UInt64(min(4, Answers.readingSeconds(text)) * 1_000_000_000))
        }
        await lingerSpoken(Answers.readingSeconds(text), id: id)
    }

    /// A question answered in words. First from what the Mac itself knows, with no screenshot:
    /// a few facts (the time, Wi-Fi, the network, dark mode, the volume, the battery), what
    /// the mouse is on, and the front window's controls. From the screenshot when the model
    /// says that is not enough, or straight away when the question is about a picture, a chart
    /// or an error (`fromScreen`).
    @MainActor private func answer(_ question: String, fromScreen: Bool, id: Int) async {
        overlay.say(.thinking, "", thinking: true)
        // What the Mac knows for certain it says itself: no model, no screenshot.
        if let fact = Talk.fact(question) {
            let text = Mac.say(fact)
            log.add("ANSWER  \"\(question)\"", ["from the Mac itself, with no model: \(text)"])
            await tell(text, question: question, id: id, how: "the Mac itself")
            return
        }
        // Anything else about what is on the screen goes to the planner, in its own format: the
        // question as the task and a list of controls (the items of a menu, or of the Dock,
        // when the question is about one). Its `done` sentence is the answer. Nothing is done:
        // if it sets off to act instead, the thing is pointed at; if it wants to look, or the
        // question is about a picture, the answer is read from a screenshot (below).
        var fromScreen = fromScreen
        if !fromScreen, !settings.plainStepPrompt {
            do {
                let listed = await Task.detached { Access.screenList() }.value
                var controls = listed.controls
                var about = "the front window's \(controls.count) controls"
                if let name = Talk.menu(question), let menu = await Task.detached(operation: { Access.menuList(named: name) }).value {
                    controls = menu.controls
                    about = "the \(controls.count) items of the \(menu.title == "menu bar" ? "menu bar" : menu.title + " menu")"
                } else if Talk.asksDock(question), !Apps.dock.isEmpty {
                    controls = Apps.dock.prefix(Planner.maxControls).enumerated().map { ListedControl(id: $0.offset + 1, role: "button", name: $0.element) }
                    about = "the \(controls.count) apps in the Dock"
                }
                let out = try await pipeline.question(user: Planner.user(task: question, apps: Apps.list, frontApp: listed.app, window: listed.window,
                                                                         done: [], controls: controls))
                guard alive(id) else { return }
                let outcome = Talk.outcome(step: out.step, content: out.chat.content)
                var lines = ["model \(pipeline.model) · asked as a task with \(about)",
                             "plan (\(sec(out.chat.seconds)), \(out.chat.tokenNote)): model wrote \(out.chat.written)"]
                switch outcome {
                case .say(let text):
                    log.add("ANSWER  \"\(question)\"", lines)
                    await tell(text, question: question, id: id, how: "the planner", seconds: out.chat.seconds, tokens: out.chat.tokenNote)
                    return
                case .point:
                    lines.append("it set off to act (\(out.step?.action ?? "")): nothing is done, and the question is answered by pointing")
                    log.add("ANSWER  \"\(question)\"", lines)
                    await showMe(question, id: id)
                    return
                case .look:
                    lines.append("it wants to look: answered from a screenshot")
                    log.add("ANSWER  \"\(question)\"", lines)
                    fromScreen = true
                }
            } catch {
                await fail(error, id: id)
                return
            }
        }
        let start = Date()
        do {
            let previous = earlier
            let mouse = NSEvent.mouseLocation
            let at = CGPoint(x: mouse.x, y: (NSScreen.screens.first?.frame.height ?? 0) - mouse.y)
            let listed = await Task.detached { Access.screenList() }.value
            var lines = ["model \(pipeline.model) · front app \(listed.app) · \(listed.controls.count) controls listed"]
            var text = ""
            if !fromScreen {
                let pointed = await Task.detached { Access.underMouse(at) }.value
                let facts = Mac.facts() + (pointed.map { " The mouse pointer is on \($0)." } ?? "")
                let out = try await pipeline.reply(system: Answers.system, user: Answers.user(facts: facts, app: listed.app, window: listed.window,
                                                                                               controls: listed.controls, previous: previous, question: question))
                guard alive(id) else { return }
                text = Answers.clean(out.content)
                lines.append("facts: \(facts)")
                lines.append("from the facts and the list (\(sec(out.seconds)), \(out.tokenNote)): model wrote \(out.written)")
            }
            if fromScreen || Answers.wantsLook(text) {
                overlay.say(.thinking, "looking", thinking: true)
                let (sent, aheadNote) = try await firstLook(id: id)
                guard alive(id) else { return }
                let out = try await pipeline.describe(imageURL: sent.url, text: Answers.fromScreen(app: listed.app, window: listed.window,
                                                                                                   previous: previous, question: question))
                guard alive(id) else { return }
                text = Answers.clean(out.content)
                lines.append("from the screenshot (\(screenNote(sent)); \(sec(out.seconds)), \(out.tokenNote)): model wrote \(out.written)")
                if let aheadNote { lines.append(aheadNote) }
            }
            lines.append("total \(sec(Date().timeIntervalSince(start)))")
            log.add("ANSWER  \"\(question)\"", lines)
            guard !text.isEmpty, !Answers.wantsLook(text) else {
                lastEnding = "Stopped: the model gave no answer"
                overlay.say(.sorry, "not sure about that")
                await linger(6, id: id)
                return
            }
            await tell(text, question: question, id: id)
        } catch {
            await fail(error, id: id)
        }
    }

    // MARK: the selected text: rewrite, translate, fix, summarise, explain, read aloud

    private func press(_ names: [String]) async {
        guard let combo = Keys.combo(names) else { return }
        await Task.detached(priority: .userInitiated) { Events.key(combo) }.value
    }

    /// The selected text by copying it; the clipboard is put back as it was.
    @MainActor private func copySelection() async -> String? {
        let board = NSPasteboard.general
        let saved = Mac.clipboard()
        let before = board.changeCount
        await press(["cmd", "c"])
        for _ in 0..<12 where board.changeCount == before { try? await Task.sleep(nanoseconds: 50_000_000) }
        guard board.changeCount != before else { return nil }
        let text = board.string(forType: .string)
        Mac.restore(saved)
        return text
    }

    /// Puts text where the selection is, by pasting it; the clipboard is put back afterwards.
    @MainActor private func paste(_ text: String) async {
        let saved = Mac.clipboard()
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        await press(["cmd", "v"])
        try? await Task.sleep(nanoseconds: 600_000_000)
        Mac.restore(saved)
    }

    /// Works on the text selected in the front app. A rewrite, a translation or a correction
    /// replaces the selection; a summary or an explanation is shown beside the pointer (and
    /// spoken); "read this to me" needs no model. The selected text itself is never written to
    /// the log, only how long it is.
    @MainActor private func runTextSkill(_ request: String, _ skill: TextSkill, id: Int) async {
        do {
            var selection = await Task.detached { Access.selectedText() }.value
            var how = "read from the app"
            if (selection ?? "").isEmpty, Events.allowed(prompt: false) {
                selection = await copySelection()
                how = "copied, and the clipboard put back"
            }
            guard alive(id) else { return }
            let chosen = (selection ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            guard !chosen.isEmpty else {
                let toScreen = !skill.replaces && !skill.instruction.isEmpty
                log.add("TEXT  \"\(request)\"", ["no text is selected" + (toScreen ? ": answered from the screen instead" : "")])
                if toScreen { return await answer(request, fromScreen: true, id: id) }
                lastEnding = "Stopped: no text is selected"
                overlay.say(.lost, "select some text first")
                await linger(5, id: id)
                return
            }
            if skill.instruction.isEmpty {                                   // read it aloud: the system voice, no model
                log.add("TEXT  \"\(request)\"", ["\(chosen.count) characters selected (\(how)); read aloud with the system voice"])
                lastEnding = "Done: read aloud"
                overlay.say(.answer, "reading it to you")
                speaker.speak(AVSpeechUtterance(string: chosen))
                await lingerSpoken(2, id: id)
                return
            }
            let text = chosen.count > 6000 ? String(chosen.prefix(6000)) : chosen
            overlay.say(.thinking, skill.caption.lowercased(), thinking: true)
            let room = skill.replaces ? min(1500, max(160, text.count / 3 + 80)) : 160
            let out = try await pipeline.write(Skills.prompt(skill, text: text), maxTokens: room)
            guard alive(id) else { return }
            let result = Answers.clean(out.content, keepLines: skill.replaces)
            log.add("TEXT  \"\(request)\"", ["model \(pipeline.model) · \(skill.caption)",
                                              "\(chosen.count) characters selected (\(how))" + (chosen.count > 6000 ? "; the first 6000 were used" : ""),
                                              "the model wrote \(result.count) characters in \(sec(out.seconds)) (\(out.tokenNote))"])
            guard !result.isEmpty else {
                lastEnding = "Stopped: the model wrote nothing"
                overlay.say(.sorry, "nothing came back")
                await linger(6, id: id)
                return
            }
            guard skill.replaces else { return await tell(result, question: request, id: id) }
            guard Events.allowed(prompt: true) else {
                lastEnding = "Stopped: not allowed to paste"
                overlay.say(.sorry, "I'm not allowed to paste yet")
                overlay.trouble("To paste, allow Accessibility for \(AppController.launcher): System Settings > Privacy & Security > Accessibility. Then ask again.")
                await linger(12, id: id)
                return
            }
            if !settings.continuous {
                overlay.say(.acting, "return to paste it, esc to stop")
                guard await waitForReturn(), alive(id) else {
                    if alive(id) { stop(note: "Cancelled before pasting") }
                    return
                }
            }
            await paste(result)
            guard alive(id) else { return }
            lastEnding = "Done: \(skill.caption)"
            log.add("    pasted over the selection; the clipboard was put back")
            await finished(id: id)
        } catch {
            await fail(error, id: id)
        }
    }

    // MARK: do it

    /// Waits for Return (true) or Esc (false). Return is a global hotkey only while this waits,
    /// so the app the step will act on keeps the keyboard.
    @MainActor private func waitForReturn() async -> Bool {
        HotKeys.shared.register(id: HotKey.ret, keyCode: kVK_Return) { [weak self] in self?.answer(true) }
        HotKeys.shared.register(id: HotKey.enter, keyCode: kVK_ANSI_KeypadEnter) { [weak self] in self?.answer(true) }
        let ok = await withCheckedContinuation { (c: CheckedContinuation<Bool, Never>) in confirm = c }
        HotKeys.shared.unregister(id: HotKey.ret)
        HotKeys.shared.unregister(id: HotKey.enter)
        return ok
    }

    private func answer(_ ok: Bool) {
        guard let waiting = confirm else { return }
        confirm = nil
        waiting.resume(returning: ok)
    }

    /// Shows a proposed step and waits for the go-ahead (or, in continuous running, a moment).
    /// `flight`: the seconds the pointer needs to get there; an unasked step waits for it to land.
    @MainActor private func approve(_ title: String, timing: String, flight: Double = 0, id: Int) async -> Bool {
        if settings.continuous {
            try? await Task.sleep(nanoseconds: UInt64((max(flight, 0.5) + 0.45) * 1_000_000_000))
            return alive(id)
        }
        overlay.say(.acting, "return to do it, esc to stop")
        let ok = await waitForReturn()
        return ok && alive(id)
    }

    /// Carries out one step through system events. `p` and `q` are screen points.
    @MainActor private func perform(_ step: Step, at p: CGPoint?, to q: CGPoint?) async {
        // The log window is left out of what the model sees, so a target can lie under it:
        // take it out of the way, or the click would land on the log.
        if let frame = log.frameOnScreen, let height = NSScreen.screens.first?.frame.height {
            let covered = [p, q].compactMap { $0 }.contains { frame.contains(Geometry.appKitPoint(quartz: $0, mainScreenHeight: height)) }
            if covered {
                log.hide()
                log.add("    (the log window was over the target and has been hidden; Show log in the leaf menu brings it back)")
                try? await Task.sleep(nanoseconds: 150_000_000)
            }
        }
        if step.isClick || step.action == .drag { overlay.clickEffect() }
        let combo = Keys.combo(step.keys)
        let pressesEscape = step.action == .key && combo?.keyCode == UInt16(kVK_Escape)
        if pressesEscape { HotKeys.shared.unregister(id: HotKey.escape) }       // or our own Esc would stop us
        await Task.detached(priority: .userInitiated) {
            switch step.action {
            case .click: if let p { Events.click(at: p) }
            case .double_click: if let p { Events.click(at: p, count: 2) }
            case .right_click: if let p { Events.click(at: p, right: true) }
            case .drag: if let p, let q { Events.drag(from: p, to: q) }
            case .type: Events.type(step.text ?? "")
            case .key: if let combo { Events.key(combo) }
            case .scroll: Events.scroll(step.direction ?? "down", at: p)
            case .done: break
            }
        }.value
        if pressesEscape {
            HotKeys.shared.register(id: HotKey.escape, keyCode: kVK_Escape) { [weak self] in self?.stop(note: "Stopped with Esc") }
        }
    }

    /// Asks where a target is on a prepared screenshot; logs the answer; returns the screen point.
    /// With `shot` (the capture the screenshot was made from) and the second look switched on:
    /// when the first answer is not a control the Mac can name, a square around it is cut from
    /// the capture, sent at the usual size with the same request, and that answer is taken.
    @MainActor private func find(_ target: String, url: String, region: CGRect, what: String, shot: Shot? = nil) async throws -> (CGPoint?, Double) {
        let out = try await pipeline.point(imageURL: url, instruction: target, looks: settings.secondLook ? 2 : 1)
        lastPointer = out.pointer
        let p = out.answer.point.map { Geometry.screenPoint(grid: $0, region: region) }
        var line = "    \(what) \"\(target)\" (\(sec(out.chat.seconds)), \(out.chat.tokenNote)): model wrote \(out.chat.written)"
        if let g = out.answer.point, let p { line += " -> grid \(grid(g)) -> screen \(pt(p)) pt" } else { line += " -> NO POINT" }
        var place = p
        var how = ""
        var named = false                                   // the click landed on a control whose name fits the words
        if let p, settings.snap {
            let snapped = await Task.detached { Access.snap(p, target: target) }.value
            place = snapped.0
            named = snapped.1.hasPrefix("the control named")
            how = "the click goes to \(snapped.1)" + (snapped.0 == p ? "" : " at screen \(pt(snapped.0)) pt")
        }
        log.add(line, [out.note.map { "note: \($0)" } ?? "", how])
        var seconds = out.chat.seconds
        // the helper takes its own second look when asked for two: the app's own is for the language model
        guard settings.secondLook, !named, out.pointer == PointerHelper.languageModel, let first = p, let shot else { return (place, seconds) }

        // the second look
        let side = max(shot.region.width, shot.region.height) / 2
        let window = Geometry.squareWindow(around: first, in: shot.region, side: side)
        let pixels = Geometry.pixelRect(points: window, displayOrigin: shot.region.origin, scale: shot.scale)
        let closer = Geometry.pointsRect(pixels: pixels, displayOrigin: shot.region.origin, scale: shot.scale)
        let longSide = settings.imageSide
        let full = shot.full
        let cut: String? = await Task.detached { ImageOps.zoomed(full, pixelRect: pixels, longSide: longSide).flatMap { ImageOps.dataURL($0) } }.value
        guard let cut else { return (place, seconds) }
        overlay.say(.thinking, "looking closer", thinking: true)
        let again = try await pipeline.point(imageURL: cut, instruction: target, helper: false)
        seconds += again.chat.seconds
        var second = "    second look at a \(Int(closer.width)) x \(Int(closer.height)) pt square (\(sec(again.chat.seconds)), \(again.chat.tokenNote)): model wrote \(again.chat.written)"
        guard let g = again.answer.point else {
            log.add(second + " -> NO POINT; the first answer is kept")
            return (place, seconds)
        }
        let q = Geometry.screenPoint(grid: g, region: closer)
        second += " -> screen \(pt(q)) pt, \(Int(hypot(q.x - first.x, q.y - first.y))) pt from the first answer"
        var better = q
        var where_ = ""
        if settings.snap {
            let snapped = await Task.detached { Access.snap(q, target: target) }.value
            better = snapped.0
            where_ = "the click goes to \(snapped.1)" + (snapped.0 == q ? "" : " at screen \(pt(snapped.0)) pt")
        }
        log.add(second, [where_])
        return (better, seconds)
    }

    // MARK: tasks with tools: apps, links, menus, keys, numbered controls

    /// A step's place on screen when it names its target in words: found on a screenshot.
    @MainActor private func place(of target: String, what: String) async throws -> CGPoint? {
        overlay.say(.thinking, "looking for it", thinking: true)
        let sent = try await look()
        return try await find(target, url: sent.url, region: sent.shot.region, what: what, shot: sent.shot).0
    }

    /// One step of a task, kept for the log file of a batch run.
    private func record(_ n: Int, _ step: PlannedStep, line: String, result: String, planSeconds: Double, stepSeconds: Double, tokens: String = "") {
        var entry: [String: Any] = ["step": n, "tool": step.action, "line": line, "result": result,
                                    "plan_seconds": (planSeconds * 100).rounded() / 100, "step_seconds": (stepSeconds * 100).rounded() / 100]
        if !tokens.isEmpty { entry["tokens"] = tokens }
        if let lastPointer { entry["pointer"] = lastPointer }               // a step that had something pointed at
        lastPointer = nil
        trace.append(entry)
    }

    /// Carries out one step. Returns nil when it went through, else why it did not.
    /// `p` and `q`: where on screen, for the steps that have a place.
    @MainActor private func carryOut(_ step: PlannedStep, at p: CGPoint?, to q: CGPoint? = nil) async -> String? {
        defer { lastCarried = step.action }
        switch step.action {
        case "open_app":
            let said = step.app ?? ""
            if let name = Apps.resolve(said) ?? (Places.resolve(said) == nil ? Apps.nearest(said) : nil) {
                let state = await Apps.openInFront(name)
                guard state.opened else { return "\(name) could not be opened" }
                lastOpened = name
                guard state.front else { return "\(name) was opened but did not come to the front" }
                if !state.window, name == "Finder" {                           // the Finder is always running: a window is what was meant
                    await perform(Step(action: .key, keys: ["cmd", "n"]), at: nil, to: nil)
                    try? await Task.sleep(nanoseconds: 900_000_000)
                    stepNote = "a new Finder window was opened"
                } else if !state.window {
                    stepNote = "\(name) is in front but has no window open"
                }
                return nil
            }
            // not an app on this Mac: a settings pane, a folder or a site by its name
            guard let place = Places.resolve(said) else { return "there is no app called \(said)" }
            return await open(place)
        case "open_url":
            let said = (step.url ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            // words where an address should be ("Sound settings", "downloads folder", "youtube")
            if !said.contains("://"), !said.lowercased().hasPrefix("mailto:"), !said.contains(".") || said.hasPrefix("~") || said.hasPrefix("/"),
               let place = Places.resolve(said) {
                return await open(place)
            }
            let browser = step.app.flatMap(Apps.resolve)
            return await Apps.open(link: said, in: browser) ? nil : "that link could not be opened"
        case "menu":
            let path = step.path ?? ""
            return await Task.detached { Access.menu(path: path) }.value ? nil : "there is no menu item \(path)"
        case "side_by_side":
            let left = step.app ?? "", right = step.target ?? ""
            let openedRight = await Apps.openInFront(right).opened
            let openedLeft = await Apps.openInFront(left).opened
            guard openedRight, openedLeft else { return "\(openedLeft ? right : left) could not be opened" }
            try? await Task.sleep(nanoseconds: 400_000_000)
            let area = Mac.usableScreen()
            let half = CGSize(width: area.width / 2, height: area.height)
            return await Task.detached {
                Access.place(app: right, in: CGRect(origin: CGPoint(x: area.midX, y: area.minY), size: half))
                    ?? Access.place(app: left, in: CGRect(origin: area.origin, size: half))
            }.value
        case "window":
            let area = Mac.usableScreen(), side = step.direction ?? "full"
            return await Task.detached { Access.moveFrontWindow(to: side, within: area) }.value
        case "appearance":
            let dark = step.text == "toggle" ? !Mac.isDark : step.text == "dark"
            return await Task.detached { Mac.setAppearance(dark: dark) }.value
        case "volume": return Mac.setVolume(step.text ?? "")
        case "new_folder": return Mac.newFolder(named: step.text ?? "New Folder", in: step.target ?? "desktop")
        case "reveal":
            if let failure = Mac.reveal(step.target ?? "") { return failure }
            return await inFront("Finder") ? nil : "the Finder did not come to the front with the folder"
        case "calendar_event": return await addCalendarEvent(kind: step.target ?? "event", rest: step.text ?? "")
        case "rename_file":
            let name = step.target ?? "", place = step.app ?? "", new = step.text ?? ""
            return await Task.detached { Mac.renameFile(name, in: place, to: new) }.value
        case "move_file":
            let name = step.target ?? "", place = step.app ?? "", into = step.text ?? ""
            return await Task.detached { Mac.moveFile(name, from: place, into: into) }.value
        case "calculate":
            let sum = step.text ?? ""
            guard let value = Arithmetic.value(sum) else { return "\(sum) is not a sum that can be worked out" }
            guard Events.allowed(prompt: true) else { return "Accessibility is not allowed, so keys cannot be pressed" }
            let state = await Apps.openInFront("Calculator")
            guard state.opened, state.front, let pid = NSWorkspace.shared.frontmostApplication?.processIdentifier else { return "Calculator could not be brought to the front" }
            await perform(Step(action: .key, keys: ["escape"]), at: nil, to: nil)          // clear what is there
            for keys in Arithmetic.keys(sum) {
                try? await Task.sleep(nanoseconds: 90_000_000)
                await perform(Step(action: .key, keys: keys), at: nil, to: nil)
            }
            try? await Task.sleep(nanoseconds: 700_000_000)
            let wanted = Arithmetic.shown(value)
            let shows = await Task.detached { wanted.contains { Access.frontWindowSays(pid, $0) } }.value
            if shows { stepNote = "Calculator shows \(wanted[0])" }
            return shows ? nil : "the keys of \(sum) = were pressed, but Calculator does not show \(wanted[0])"
        case "dock":
            let what = step.target ?? "", value = step.text ?? ""
            return await Task.detached { Mac.setDock(what, value) }.value
        case "type":
            if let p {
                await perform(Step(action: .click, target: "the field"), at: p, to: nil)
                try? await Task.sleep(nanoseconds: 250_000_000)
            }
            // A field of one line that already holds something: what is typed replaces it (after
            // a click the typing would be added to its end: "New FolderGroceries"). Not when the
            // step before was typing too and this one goes on where that left off.
            let focus = await Task.detached { Access.focus() }.value
            if let focus, focus.line, !focus.value.isEmpty, !(lastCarried == "type" && p == nil) {
                log.add("    the field already holds \(focus.value.count) character(s): all selected first, so the typing replaces them")
                await perform(Step(action: .key, keys: ["cmd", "a"]), at: nil, to: nil)
                try? await Task.sleep(nanoseconds: 150_000_000)
            }
            // Two types in a row into the same text area are two lines (a title, then the text
            // under it): a line break goes between them.
            let text = step.text ?? ""
            if let focus, focus.role == "AXTextArea", lastCarried == "type", focus.place == lastTypedPlace, !lastTyped.isEmpty,
               !lastTyped.hasSuffix("\n"), let first = text.first, first.isUppercase || first.isNumber {      // not a sentence going on
                log.add("    the step before typed into this text area too: a line break first")
                await perform(Step(action: .key, keys: ["return"]), at: nil, to: nil)
                try? await Task.sleep(nanoseconds: 120_000_000)
            }
            await perform(Step(action: .type, text: step.text), at: nil, to: nil)
            lastTyped = text
            lastTypedPlace = focus?.place ?? ""
        case "key":
            guard Events.allowed(prompt: true) else { return "Accessibility is not allowed, so keys cannot be pressed" }
            await perform(Step(action: .key, keys: step.keys), at: nil, to: nil)
        case "scroll":
            // with no place given, the middle of what scrolls in the front window (a scroll goes
            // to whatever is under the mouse, which may be anywhere)
            var place = p
            if place == nil { place = await Task.detached { Access.scrollPoint() }.value }
            await perform(Step(action: .scroll, direction: step.direction ?? "down"), at: place, to: nil)
        case "drag": await perform(Step(action: .drag, target: "start", targetEnd: "end"), at: p, to: q)
        case "double_click": await perform(Step(action: .double_click, target: "it"), at: p, to: nil)
        case "right_click": await perform(Step(action: .right_click, target: "it"), at: p, to: nil)
        default: await perform(Step(action: .click, target: "it"), at: p, to: nil)
        }
        return nil
    }

    /// Waits until the named app is in front (bringing it forward if it is running but behind).
    @MainActor private func inFront(_ name: String) async -> Bool {
        for _ in 0..<10 {                                                   // it may still be starting
            if NSWorkspace.shared.frontmostApplication?.localizedName == name { return true }
            try? await Task.sleep(nanoseconds: 250_000_000)
        }
        return await Apps.openInFront(name).front
    }

    /// A calendar event, seen through: the file is opened in Calendar, the sheet that asks
    /// which calendar it goes to is confirmed (the default one), and the step only counts when
    /// that sheet is gone. Whether the event can then be seen in the calendar is said too.
    @MainActor private func addCalendarEvent(kind: String, rest: String) async -> String? {
        let file = Mac.calendarFile(kind: kind, rest: rest)
        guard let path = file.path else { return file.problem ?? "the event could not be written" }
        guard await Apps.openInFront("Calendar").opened,
              let calendar = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == "com.apple.iCal" }),
              let bundle = calendar.bundleURL else { return "the Calendar app could not be opened" }
        let pid = calendar.processIdentifier
        let taken: Bool = await withCheckedContinuation { done in
            NSWorkspace.shared.open([URL(fileURLWithPath: path)], withApplicationAt: bundle, configuration: NSWorkspace.OpenConfiguration()) { app, _ in
                done.resume(returning: app != nil)
            }
        }
        guard taken else { return "Calendar did not take the event" }
        var confirmed = false
        for _ in 0..<25 where !confirmed {                                  // up to 5 s for its question to come up
            confirmed = await Task.detached { Access.pressDialogButton(pid, titles: ["OK", "Add", "Import"]) }.value
            if !confirmed { try? await Task.sleep(nanoseconds: 200_000_000) }
        }
        var asking = true
        for _ in 0..<15 where asking {                                      // and up to 3 s for it to go away
            asking = await Task.detached { Access.hasDialog(pid) }.value
            if asking { try? await Task.sleep(nanoseconds: 200_000_000) }
        }
        if asking { return "Calendar is still asking about the event (its sheet is open)" }
        try? await Task.sleep(nanoseconds: 700_000_000)
        let title = file.title
        let showing = await Task.detached { Access.frontWindowSays(pid, title) }.value
        if !confirmed, !showing { return "Calendar did not ask where to put the event, and the event is not showing" }
        stepNote = showing ? "the event \"\(title)\" is showing in Calendar"
                           : "Calendar's question was confirmed; the event \"\(title)\" is not in the part of the calendar that is showing"
        return nil
    }

    /// Opens a settings pane, a site or a folder. Nil when it worked, else why not.
    @MainActor private func open(_ place: Places.Place) async -> String? {
        switch place {
        case .folder(let folder): return Mac.reveal(folder)
        case .link(let link):
            if await Apps.open(link: link, in: nil) {
                guard link.lowercased().hasPrefix(Places.settingsScheme) else { return nil }
                guard await inFront("System Settings") else { return "System Settings did not come to the front" }
                return await settled(on: link)
            }
            if link.lowercased().hasPrefix(Places.settingsScheme) {              // this macOS does not know the pane: at least open Settings
                return await Apps.openInFront("System Settings").opened ? "System Settings was opened, but not at that pane" : "System Settings could not be opened"
            }
            return "that link could not be opened"
        }
    }

    /// System Settings has been sent to a pane by its link: is that the pane it shows? macOS
    /// opens Settings even for a link it does not know (it then stays where it was, or shows
    /// General), and the identifiers differ between versions. When the window's title is not
    /// the pane's, the pane is chosen by its name in the sidebar; when the sidebar has no such
    /// item, the pane is looked for in General's own list; failing that the pane its settings
    /// are kept in is opened (macOS 26.6 has no Screen Saver or VPN pane) and the step says
    /// so without counting as done; and when there is none, the step fails and says so.
    @MainActor private func settled(on link: String, moved: Bool = false) async -> String? {
        guard let pane = Places.pane(ofLink: link),
              let pid = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == "com.apple.systempreferences" })?.processIdentifier
        else { return nil }
        let names = Places.names(of: pane)
        var title = ""
        let showing = { () async -> Bool in
            // The pane needs a moment to come up: up to 2 s while another pane's title is
            // showing, up to 5 s while there is no title yet (Settings is still starting).
            for i in 0..<20 {
                title = await Task.detached { Access.windowTitle(pid) }.value
                if Places.shows(pane, title: title) { return true }
                if i >= 8, !title.isEmpty { break }
                try? await Task.sleep(nanoseconds: 250_000_000)
            }
            return false
        }
        if await showing() { return nil }
        if await Task.detached(operation: { Access.chooseInSidebar(pid, names: names) }).value {
            log.add("    the link did not bring up \(pane.name) (the window says \"\(title)\"): chosen by its name in the sidebar")
            if await showing() { return nil }
        }
        // General lists some panes itself (Sharing, Time Machine, Storage, About): when General
        // is what came up, the pane is chosen there by its name.
        if title == "General", pane.name != "General",
           await Task.detached(operation: { Access.chooseInSidebar(pid, names: names, anywhere: true) }).value {
            log.add("    \(pane.name) chosen by its name in the General pane")
            if await showing() { return nil }
        }
        // No pane of that name here: the pane its settings are kept in is opened, and the step
        // says so instead of counting as done, so the planner goes on from there.
        if !moved, let other = Places.moved(pane), await Apps.open(link: other.url, in: nil) {
            let opened = await settled(on: other.url, moved: true) == nil
            return "this macOS has no \(pane.name) pane" + (opened ? "; \(other.name), where its settings are kept, is open instead" : "")
        }
        // An unknown title with nothing to choose in the sidebar: only "General" (where an
        // unknown link lands) and an empty title are known to be wrong.
        let wrong = title.isEmpty || (title == "General" && pane.name != "General")
        return wrong ? "System Settings has no \(pane.name) pane that could be opened (it shows \"\(title)\")" : nil
    }

    /// Plain requests that need no planning: open an app, open a site, search the web, draft
    /// an email. The model is used only to write the few lines of the draft; nothing is sent.
    @MainActor private func runRecipe(_ request: String, steps: [PlannedStep], id: Int) async {
        log.add("DO IT  \"\(request)\"", ["direct, without the planner: " + steps.map { $0.action }.joined(separator: ", ")])
        var told: [String] = []                            // the steps so far, as the planner would read them
        var handedOver = false                             // the planner took the request over, and says what was done
        defer { if !handedOver { carried = told } }
        do {
            for (i, planned) in steps.enumerated() {
                try Task.checkCancellation()
                let start = Date()
                var step = planned
                var wrote = 0.0
                if step.action == Recipes.draftEmail {
                    let to = step.target ?? "", about = step.text ?? ""
                    overlay.say(.thinking, "writing it", thinking: true)
                    let draft = try await pipeline.write("Write a short, friendly email to \(to) about \(about). Give only the body of the email: "
                                                         + "no subject line, no notes, and sign it with the word Thanks.")
                    guard alive(id) else { return }
                    wrote = draft.seconds
                    let inBrowser = lastOpened.map { Apps.browsers.contains($0) } ?? false
                    let subject = about.prefix(1).uppercased() + about.dropFirst()
                    step = PlannedStep(action: "open_url", app: inBrowser ? lastOpened : nil,
                                       url: Recipes.emailLink(to: to, subject: subject, body: draft.content, inBrowser: inBrowser))
                    log.add("    draft written by the model in \(sec(draft.seconds)) (\(draft.tokenNote))", [draft.content])
                }
                let line = step.action == "open_url" && planned.action == Recipes.draftEmail
                    ? "open_url an email draft to \(planned.target ?? "")" + (step.app.map { " in \($0)" } ?? " in the mail app")
                    : Skills.caption(step) ?? Planner.doneLine(step, control: nil)
                overlay.say(.acting, captioned(i + 1, Captions.step(step, control: nil)))
                stepNote = nil
                let failure = await carryOut(step, at: nil)
                guard alive(id) else { return }
                let took = Date().timeIntervalSince(start)
                log.add("Step \(i + 1) (direct)", ["tool: \(step.action)", "step: \(line)", failure.map { "FAILED: \($0)" } ?? "done in \(sec(took))"])
                record(i + 1, step, line: line, result: failure ?? "ok", planSeconds: wrote, stepSeconds: took)
                let doneLine = planned.action == Recipes.draftEmail ? Skills.doneLine(planned) : Skills.doneLine(step)
                if let failure {
                    // The direct route did not have its effect. Unless nothing can be done at all
                    // (no permission), the planner takes the request over, told what was tried.
                    told.append(doneLine + " (\(failure))")
                    if !failure.contains("Accessibility is not allowed"), !settings.plainStepPrompt, await makeReady(id: id) {
                        log.add("    the direct route did not finish (\(failure)): the planner takes the request over")
                        handedOver = true
                        await runPlanner(request, id: id, already: told)
                        return
                    }
                    guard alive(id) else { return }
                    lastEnding = "Stopped at step \(i + 1): \(failure)"
                    overlay.say(.sorry, failure)
                    log.add(lastEnding)
                    await linger(6, id: id)
                    return
                }
                told.append(doneLine + (stepNote.map { " (\($0))" } ?? ""))
                if let note = stepNote { log.add("    note: \(note)") }
                try await Task.sleep(nanoseconds: 700_000_000)
            }
            lastEnding = "Done (\(steps.count) step\(steps.count == 1 ? "" : "s"))"
            log.add(lastEnding)
            await finished(id: id)
        } catch {
            await fail(error, id: id)
        }
    }

    /// Carries a task out with the model planning (format v1): each turn it is given the task,
    /// the apps on this Mac, what has been done and the front window's controls as a numbered
    /// list, and answers with one next_step call. Apps, links, menus and keys are done directly;
    /// a control picked by number is acted on exactly; only `look`, or a click that names its
    /// target in words, reads a screenshot. After each step the window is listed again: a click
    /// that changed nothing is tried once more, and if it still changed nothing the model is told.
    /// `already`: steps a direct route carried out (or tried) before handing the request over.
    @MainActor private func runPlanner(_ goal: String, id: Int, already: [String] = []) async {
        log.add("DO IT  \"\(goal)\"", ["model \(pipeline.model) · planned with tools, up to \(Planner.maxSteps) steps",
                                      settings.continuous ? "steps run without asking (Esc stops)" : "each step waits for Return"])
        guard Events.allowed(prompt: true) else {
            let text = "To click and type, allow Accessibility for \(AppController.launcher): System Settings > Privacy & Security > Accessibility. Then ask again."
            lastEnding = "Stopped: Accessibility is not allowed, so nothing can be clicked or typed"
            overlay.say(.sorry, "I'm not allowed to click yet")
            overlay.trouble(text)
            log.add("NOT ALLOWED TO ACT", [text])
            await linger(14, id: id)
            return
        }
        var done: [String] = already
        defer { carried = done }
        var askedAgain = false                             // a `done` that said the task was not done has been asked about once
        var unusable = 0
        var ending = "Stopped after \(Planner.maxSteps) steps without the model saying done"
        var closing = ""                                   // the model's sentence with `done`
        var pressedReturn = false                          // the step before pressed Return
        var refusedReturns = 0
        var budget = StepBudget()                          // steps that had no effect are counted against it
        var lastStep: PlannedStep?                         // the step carried out last, and whether it changed anything
        var lastChanged = false
        var madeNew = false                                // command-N has been pressed once for typing that went nowhere
        let signature = { (list: Access.ScreenList) in
            Planner.signature(app: list.app, window: list.window, controls: list.controls) + "\u{1}" + list.detail
        }
        do {
            var screen = await Task.detached { Access.screenList() }.value
            steps: for n in 1...Planner.maxSteps {
                try Task.checkCancellation()
                overlay.say(.thinking, "", thinking: true)
                lastPointer = nil
                let start = Date()
                let listed = screen
                let out = try await pipeline.plan(user: Planner.user(task: goal, apps: Apps.list, frontApp: listed.app, window: listed.window,
                                                                     done: done, controls: listed.controls))
                guard alive(id) else { return }
                var lines = ["front app \(listed.app) · window \"\(listed.window)\" · \(listed.controls.count) controls listed",
                             "plan (\(sec(out.chat.seconds)), \(out.chat.tokenNote)): model wrote \(out.chat.written)"]
                if let note = out.note { lines.append("note: \(note)") }
                // A call that cannot be used as written: what is not in doubt is put right; otherwise
                // the planner is told exactly what was missing. Only three such answers in a row
                // end the request.
                let repaired = out.step.map { Repair.step($0, controls: listed.controls, task: goal, apps: Apps.list, frontApp: listed.app) }
                if let note = repaired?.note { lines.append("put right: \(note)") }
                guard let step = repaired?.step, Repair.missing(step, controls: listed.controls) == nil else {
                    let why = repaired.flatMap { Repair.missing($0.step, controls: listed.controls) } ?? "no next_step call could be read"
                    lines.append("NOT USABLE: \(why)")
                    log.add("Step \(n)", lines)
                    let told = (repaired?.step.action ?? "an answer") + " (not carried out: \(why))"
                    done.append(told)
                    trace.append(["step": n, "tool": repaired?.step.action ?? "none", "line": told, "result": "not usable: \(why)",
                                  "plan_seconds": (out.chat.seconds * 100).rounded() / 100, "tokens": out.chat.tokenNote])
                    unusable += 1
                    if unusable >= 3 {
                        ending = "Stopped: three answers in a row could not be used as steps (see the log)"
                        break steps
                    }
                    continue
                }
                unusable = 0
                let control = step.id.flatMap { wanted in listed.controls.first { $0.id == wanted } }
                let line = Planner.doneLine(step, control: control)
                lines.append("tool: \(step.action) · step: \(line)")
                log.add("Step \(n)", lines)

                if step.action == "done" {
                    let text = (step.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                    // A `done` whose own sentence says more is needed, or that it gave up: asked once
                    // more on the screen as it is now; said again, its sentence is shown as it is,
                    // and nothing claims the request was done.
                    if Repair.unfinished(text) {
                        if !askedAgain {
                            askedAgain = true
                            log.add("    not taken as done: the sentence says the task is not finished; asked once more")
                            try await Task.sleep(nanoseconds: 900_000_000)
                            screen = await Task.detached { Access.screenList() }.value
                            continue
                        }
                        ending = "Not finished: \(text)"
                        record(n, step, line: "done: \(text)", result: "not finished", planSeconds: out.chat.seconds, stepSeconds: 0, tokens: out.chat.tokenNote)
                        closing = text
                        break steps
                    }
                    // Text typed last into a field of one line, and no Return since: the field is
                    // still being edited (an event's title, a new name), so Return is pressed first.
                    var pressed = false
                    var committed: String?
                    if let last = lastStep, last.action == "type", !(last.text ?? "").hasSuffix("\n"), lastChanged {
                        let focus = await Task.detached { Access.focus() }.value
                        if let focus, focus.line, !focus.inWeb, !focus.value.isEmpty {
                            log.add("    before finishing: Return, because the text typed last is still in a field of one line")
                            await perform(Step(action: .key, keys: ["return"]), at: nil, to: nil)
                            try await Task.sleep(nanoseconds: 700_000_000)
                            pressed = true
                        }
                        // A window that commits with a button (a contact being edited: Done): pressed too.
                        if focus?.inWeb != true {
                            committed = await Task.detached { Access.pressCommitButton() }.value
                            if let committed {
                                log.add("    before finishing: the button \(committed) is pressed, so that what was typed is kept")
                                try await Task.sleep(nanoseconds: 700_000_000)
                            }
                        }
                    }
                    ending = "Done" + (text.isEmpty ? "" : ": \(text)") + " (\(n - 1) step\(n == 2 ? "" : "s"))"
                    record(n, step, line: text.isEmpty ? "done" : "done: \(text)", result: "ok", planSeconds: out.chat.seconds, stepSeconds: 0, tokens: out.chat.tokenNote)
                    if pressed { trace[trace.count - 1]["before"] = "key return (the text typed last was still in a field of one line)" }
                    if let committed { trace[trace.count - 1]["committed"] = "button \(committed) pressed, so that what was typed is kept" }
                    closing = text
                    break steps
                }

                // A step that just had no effect is not repeated, and scrolling or clicking that keeps
                // changing nothing is stopped: the planner is told, and must do something else.
                if let why = budget.refusal(step) {
                    log.add("    not carried out: \(why) (the planner is told)")
                    done.append(line + " (not carried out: \(why))")
                    record(n, step, line: line, result: "not carried out: \(why)", planSeconds: out.chat.seconds, stepSeconds: 0, tokens: out.chat.tokenNote)
                    if budget.refusalsInARow >= 3 {
                        ending = "Stopped: the model kept repeating steps that have no effect"
                        break steps
                    }
                    continue
                }

                // Return again right after a step that already pressed it is not pressed (a model
                // that does not see the task is finished would submit twice). The planner is told;
                // if it asks once more, the task is stopped rather than left to go round.
                let isReturn = step.action == "key" && Keys.combo(step.keys) == Keys.combo(["return"])
                if isReturn, pressedReturn {
                    refusedReturns += 1
                    log.add("    not pressed: the step before already pressed Return (the planner is told)")
                    done.append(line + " (not pressed: the step before already pressed Return)")
                    record(n, step, line: line, result: "not pressed: the step before already pressed Return", planSeconds: out.chat.seconds, stepSeconds: 0, tokens: out.chat.tokenNote)
                    if refusedReturns >= 2 {
                        ending = "Stopped: the model kept asking for Return after it had been pressed"
                        break steps
                    }
                    continue
                }

                // where, for the steps that have a place
                var p = control.map { CGPoint(x: $0.frame.midX, y: $0.frame.midY) }
                var q: CGPoint?
                let wordsOnly = ["click", "double_click", "right_click", "look", "drag"].contains(step.action) && control == nil
                if wordsOnly, let target = step.target {
                    p = try await place(of: target, what: "looking for")
                    guard alive(id) else { return }
                    if p == nil {
                        done.append(line + " (not found on the screen)")
                        budget.record(step, changed: false)
                        record(n, step, line: line, result: "not found on the screen", planSeconds: out.chat.seconds, stepSeconds: Date().timeIntervalSince(start), tokens: out.chat.tokenNote)
                        continue
                    }
                }
                if step.action == "drag", let end = step.targetEnd {
                    q = try await place(of: end, what: "looking for the end,")
                    guard alive(id) else { return }
                    if q == nil {
                        done.append(line + " (the end was not found on the screen)")
                        continue
                    }
                }

                let shown = captioned(n, Captions.step(step, control: control))
                var flight = 0.0
                if let p, let q { flight = overlay.drag(from: p, to: q, shown) }
                else if let p { flight = overlay.point(at: p, .acting, shown) } else { overlay.say(.acting, shown) }
                guard await approve(shown, timing: "", flight: flight, id: id) else {
                    if alive(id) { stop(note: "Cancelled at step \(n)") }
                    return
                }
                stepNote = nil
                let failure = await carryOut(step, at: p, to: q)
                guard alive(id) else { return }
                if let failure {
                    done.append(line + " (\(failure))")
                    budget.record(step, changed: false)
                    log.add("    FAILED: \(failure); the planner is told")
                    record(n, step, line: line, result: failure, planSeconds: out.chat.seconds, stepSeconds: Date().timeIntervalSince(start), tokens: out.chat.tokenNote)
                    continue
                }
                done.append(line + (stepNote.map { " (\($0))" } ?? ""))
                if let note = stepNote { log.add("    note: \(note) (the planner is told)") }
                pressedReturn = isReturn || (step.action == "type" && (step.text ?? "").hasSuffix("\n"))
                refusedReturns = 0
                // an opened app has already been waited for; a page or a pane needs a moment
                try await Task.sleep(nanoseconds: step.action == "open_url" ? 1_800_000_000 : 800_000_000)

                // did it have an effect? a click once more if not; typing that went nowhere is
                // given somewhere to go; then the planner is told
                var result = "ok"
                var after = await Task.detached { Access.screenList() }.value
                let before = signature(listed)
                var rescue: String?
                // An app that is in front as asked is not "nothing changed"; asked for twice in a row it is.
                let opensAgain = step.action == "open_app" && lastStep?.action == "open_app" && lastStep?.app == step.app
                if step.action != "open_app" || opensAgain, signature(after) == before {
                    if ["click", "double_click", "right_click", "look"].contains(step.action), p != nil {
                        log.add("    nothing changed: the same step once more")
                        _ = await carryOut(step, at: p, to: q)
                        try await Task.sleep(nanoseconds: 800_000_000)
                        after = await Task.detached { Access.screenList() }.value
                    } else if step.action == "type", control == nil {
                        let areas = after.controls.filter { $0.role == "text area" }
                        if areas.count == 1 {
                            // the window has one place to write: click it, and type again
                            log.add("    nothing changed: the window's one text area is clicked and the text typed again")
                            _ = await carryOut(step, at: CGPoint(x: areas[0].frame.midX, y: areas[0].frame.midY))
                            try await Task.sleep(nanoseconds: 800_000_000)
                            after = await Task.detached { Access.screenList() }.value
                            if signature(after) != before {
                                rescue = "click the text area"
                                done.insert(Planner.doneLine(PlannedStep(action: "click"), control: areas[0]), at: done.count - 1)
                            }
                        } else if Repair.newItemApps.contains(after.app), !madeNew {
                            // an app where a new item is the usual start: command-N once, and type again
                            madeNew = true
                            log.add("    nothing changed: command-N for a new item in \(after.app), and the text typed again")
                            await perform(Step(action: .key, keys: ["cmd", "n"]), at: nil, to: nil)
                            try await Task.sleep(nanoseconds: 1_200_000_000)
                            let fresh = await Task.detached { Access.screenList() }.value
                            _ = await carryOut(step, at: nil)
                            try await Task.sleep(nanoseconds: 800_000_000)
                            after = await Task.detached { Access.screenList() }.value
                            rescue = "key cmd+n"
                            done.insert("key cmd+n", at: done.count - 1)
                            if signature(after) == signature(fresh) {             // the new item did not take the typing either
                                done[done.count - 1] += " (nothing changed)"
                                result = "nothing changed"
                            }
                        }
                    }
                    if result == "ok", signature(after) == before {
                        done[done.count - 1] += " (nothing changed)"
                        result = "nothing changed"
                    }
                }
                guard alive(id) else { return }
                budget.record(step, changed: result == "ok")
                let took = Date().timeIntervalSince(start)
                log.add("    \(result == "ok" ? "done" : "done, but nothing changed (the planner is told)"): \(line)" + (p.map { " at screen \(pt($0)) pt" } ?? "") + " · \(sec(took)) for the step")
                record(n, step, line: line, result: result, planSeconds: out.chat.seconds, stepSeconds: took, tokens: out.chat.tokenNote)
                if let rescue { trace[trace.count - 1]["before"] = rescue + " (by the app: the typing had gone nowhere)" }
                lastStep = step
                lastChanged = result == "ok"
                screen = after
            }
            guard alive(id) else { return }
            lastEnding = ending
            log.add(ending)
            if ending.hasPrefix("Done") {
                if !closing.isEmpty { lastExchange = (goal, closing, Date()) }      // a follow-up question can refer to it
                await finished(closing, id: id)
            } else if ending.hasPrefix("Not finished"), !closing.isEmpty {
                overlay.say(.answer, closing)                                   // the model's own words, with no check mark
                say(closing)
                await lingerSpoken(Answers.readingSeconds(closing), id: id)
            } else {
                overlay.say(.sorry, (ending.count > 58 ? String(ending.prefix(56)) + "…" : ending).lowercased())
                await linger(6, id: id)
            }
        } catch {
            await fail(error, id: id)
        }
    }

    // MARK: a file of requests, one after another (for scoring runs with nobody at the keyboard)

    /// `--batch FILE [--out FILE] [--timeout SECONDS]`: one request per line (lines starting with
    /// # are skipped). Each is carried out as if typed, with nobody at the keyboard: nothing is
    /// asked, each request has a time limit, and the steps of each are written to the out file
    /// as JSON after every request, whether it worked or not. The process then ends with:
    ///   0  every request ended with Done (or an answer)
    ///   1  at least one request stopped, failed or ran out of time
    ///   2  the file of requests could not be read, or holds none
    ///   3  the server never became ready
    ///   4  a permission is missing (Screen Recording or Accessibility)
    private func runBatch(file: String, out: String) {
        Task { @MainActor in
            var results: [[String: Any]] = []
            let write = {
                try? FileManager.default.createDirectory(atPath: (out as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
                if let data = try? JSONSerialization.data(withJSONObject: results, options: [.prettyPrinted, .sortedKeys]) {
                    try? data.write(to: URL(fileURLWithPath: out))
                }
            }
            let end = { (code: Int32, why: String) in
                self.log.add("BATCH: \(why); exit code \(code)")
                FileHandle.standardError.write(("bonsai-assistant: \(why) (exit code \(code))\n").data(using: .utf8)!)
                write()
                self.exitCode = code
                self.quitSoon()
            }
            var requests = file.isEmpty ? [] : ((try? String(contentsOfFile: file, encoding: .utf8)) ?? "").split(whereSeparator: { $0.isNewline })
                .map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty && !$0.hasPrefix("#") }
            // --voice-file: the words of a sound file are the first request, read by the same
            // speech model and the same call as a held key.
            var spoken: Voice.Heard?
            if let sound = Launch.voiceFile {
                do {
                    let heard = try await self.voice.transcribe(file: sound)
                    self.log.add("VOICE (file)  \"\(heard.text)\"", ["\(sound): \(self.sec(heard.heard)) of sound, \(self.sec(heard.voiced)) of it voice, read in \(self.sec(heard.seconds)) by WhisperKit \(Voice.modelName)"])
                    guard !heard.text.isEmpty else {
                        results.append(["request": "", "ok": false, "ending": "Stopped: nothing was heard in \(sound)", "heard": "", "heard_seconds": 0,
                                        "sound_seconds": (heard.heard * 100).rounded() / 100, "voiced_seconds": heard.voiced, "kind": "spoken", "steps": [] as [Any]])
                        return end(1, "nothing was heard in \(sound)")
                    }
                    spoken = heard
                    requests.insert(heard.text, at: 0)
                } catch {
                    return end(2, "the sound file could not be read as speech: \(error)")
                }
            }
            guard !requests.isEmpty else { return end(2, "no requests could be read from \(file)") }
            if let problem = Launch.plannerSystem.problem { return end(2, problem) }       // never measure the wrong wording silently
            let limit = max(10, Launch.timeout ?? 180)
            self.log.add("BATCH: \(requests.count) request(s) from \(file); steps go to \(out); \(Int(limit)) s allowed for each")

            if !Launch.skipPermissionCheck {
                var missing: [String] = []
                if !Capture.allowed() { missing.append("Screen Recording") }
                if !Events.allowed(prompt: false) { missing.append("Accessibility") }
                if !missing.isEmpty {
                    return end(4, "not allowed: " + missing.joined(separator: " and ")
                               + ". macOS asks the program that started this one (see the README); --skip-permission-check goes on regardless")
                }
            }
            await self.preparing?.value
            for _ in 0..<30 where !self.ready {                       // a server that is still starting: up to 90 s more
                try? await Task.sleep(nanoseconds: 3_000_000_000)
                self.prepareSoon()
                await self.preparing?.value
            }
            guard self.ready else { return end(3, "the server is not ready: \(self.readiness)") }

            var failed = 0
            for (number, request) in requests.enumerated() {
                self.trace = []
                self.lastEnding = ""
                self.lastSpoken = ""
                let start = Date()
                var route = Router.route(request, app: Apps.resolve)
                if Launch.planEverything {
                    switch route {
                    case .direct, .scripted: route = .plan
                    default: break
                    }
                }
                self.ask(request, showOnly: false)
                let running = self.run
                var timedOut = false
                let watch = Task { @MainActor in
                    try? await Task.sleep(nanoseconds: UInt64(limit * 1_000_000_000))
                    guard !Task.isCancelled else { return }
                    timedOut = true
                    self.stop(note: "Stopped: over the time limit of \(Int(limit)) s")
                }
                await running?.value
                watch.cancel()
                if timedOut { self.lastEnding = "Stopped: over the time limit of \(Int(limit)) s" }
                if self.lastEnding.isEmpty { self.lastEnding = "Stopped: the request ended without saying how" }
                let ok = self.lastEnding.hasPrefix("Done") || self.lastEnding.hasPrefix("Answered")
                if !ok { failed += 1 }
                // one word for the whole request, as before; a request carried out in parts also lists them
                let parts = Router.parts(request, app: Apps.resolve)
                var kind = Router.kind(route)
                var entry: [String: Any] = [:]
                if parts.count > 1 {
                    let kinds = parts.map { Router.kind(Launch.planEverything ? .plan : Router.route($0, app: Apps.resolve)) }
                    kind = kinds.allSatisfy { $0 == "direct" } ? "direct" : kinds.contains("planned") ? "planned" : kinds.first { $0 != "direct" } ?? "direct"
                    entry["parts"] = zip(parts, kinds).map { ["request": $0.0, "kind": $0.1] }
                }
                entry.merge(["request": request, "model": self.settings.model, "ending": self.lastEnding, "ok": ok, "timed_out": timedOut,
                             "kind": kind, "seconds": (Date().timeIntervalSince(start) * 10).rounded() / 10, "steps": self.trace,
                             "planner_system": Launch.plannerSystemNote, "spoken": self.lastSpoken]) { $1 }
                if number == 0, let spoken {                            // the request that was spoken
                    entry["heard"] = spoken.text
                    entry["heard_seconds"] = (spoken.seconds * 100).rounded() / 100
                    entry["sound_seconds"] = (spoken.heard * 100).rounded() / 100
                    entry["voiced_seconds"] = spoken.voiced
                }
                results.append(entry)
                write()
                self.overlay.hideAll()
                try? await Task.sleep(nanoseconds: 1_500_000_000)
            }
            end(failed == 0 ? 0 : 1, "finished: \(requests.count - failed) of \(requests.count) request(s) ended well; steps written to \(out)")
        }
    }

    /// The screenshot a step works on: the one read ahead for the first look, a new one after.
    @MainActor private func stepLook(first: Bool, carried: Shot?, id: Int) async throws -> (Sent, String?) {
        if first { return try await firstLook(id: id) }
        return (try await look(reuse: carried), nil)
    }

    /// Carries a request out step by step. `scripted`: the steps the request itself spells out;
    /// without them the model is asked for the next step on every new screen.
    @MainActor private func doIt(_ goal: String, scripted: [Step]? = nil, id: Int) async {
        log.add("DO IT  \"\(goal)\"", [
            "model \(pipeline.model) · " + (scripted.map { "\($0.count) step(s) as asked: " + $0.map(\.historyLine).joined(separator: "; ") }
                                           ?? "the model plans, up to \(AppController.maxSteps) steps"),
            settings.continuous ? "steps run without asking (Esc stops)" : "each step waits for Return"])
        guard Events.allowed(prompt: true) else {
            let text = "To click and type, allow Accessibility for \(AppController.launcher): System Settings > Privacy & Security > Accessibility. Then ask again."
            lastEnding = "Stopped: Accessibility is not allowed, so nothing can be clicked or typed"
            overlay.say(.sorry, "I'm not allowed to click yet")
            overlay.trouble(text)
            log.add("NOT ALLOWED TO ACT", [text])
            await linger(14, id: id)
            return
        }
        var history: [String] = []
        var unusable = 0
        var carried: Shot?
        var queue = scripted
        var looked = false
        var ending = "Stopped after \(AppController.maxSteps) steps without the model saying done"
        var closing = ""
        do {
            steps: for n in 1...AppController.maxSteps {
                try Task.checkCancellation()
                lastPointer = nil
                let start = Date()
                var sent: Sent?
                var asked = 0.0
                var labelled: CGPoint?                  // found by the control's own name, without the model
                let step: Step
                if var rest = queue {
                    guard !rest.isEmpty else {
                        ending = "Done (\(n - 1) step\(n == 2 ? "" : "s"))"
                        break steps
                    }
                    step = rest.removeFirst()
                    queue = rest
                    var lines = ["step: \(step.historyLine)"]
                    if settings.useLabels, step.isClick, let target = step.target,
                       let hit = await Task.detached(operation: { Access.find(named: target) }).value {
                        labelled = hit.center
                        lines.append("found by label: the \(hit.role) named \"\(hit.name)\" at screen \(pt(hit.center)) pt; the screen was not read")
                    } else if step.isClick || step.action == .drag || (step.action == .scroll && step.target != nil) {
                        overlay.say(.thinking, "", thinking: true)
                        let look = try await stepLook(first: !looked, carried: carried, id: id)
                        looked = true
                        carried = nil
                        guard alive(id) else { return }
                        sent = look.0
                        lines.append("\(screenNote(look.0)) · capture \(sec(look.0.shot.seconds)) · shrink and encode \(sec(look.0.seconds))")
                        if let note = look.1 { lines.append(note) }
                    }
                    log.add("Step \(n) (as asked)", lines)
                } else {
                    overlay.say(.thinking, "", thinking: true)
                    let look = try await stepLook(first: !looked, carried: carried, id: id)
                    looked = true
                    carried = nil
                    sent = look.0
                    let out = try await pipeline.nextStep(imageURL: look.0.url, goal: goal, history: history)
                    guard alive(id) else { return }
                    asked = out.chat.seconds
                    var lines = ["\(screenNote(look.0)) · capture \(sec(look.0.shot.seconds)) · shrink and encode \(sec(look.0.seconds))",
                                 "step request (\(sec(out.chat.seconds)), \(out.chat.tokenNote)): model wrote \(out.chat.written)"]
                    if let note = look.1 { lines.append(note) }
                    if let note = out.note { lines.append("note: \(note)") }

                    guard let planned = out.step, planned.problem() == nil else {
                        lines.append("NOT USABLE as a step: " + (out.step?.problem() ?? "no action could be read"))
                        log.add("Step \(n)", lines)
                        unusable += 1
                        if unusable >= 2 {
                            ending = "Stopped: the model's answers could not be used as steps (see the log)"
                            break steps
                        }
                        try await Task.sleep(nanoseconds: 800_000_000)
                        continue
                    }
                    step = planned
                    lines.append("step: \(step.historyLine)")
                    log.add("Step \(n)", lines)

                    if step.action == .done {
                        let text = (step.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                        ending = "Done" + (text.isEmpty ? "" : ": \(text)") + " (\(n - 1) step\(n == 2 ? "" : "s"))"
                        closing = text
                        break steps
                    }
                }

                // where: a second request on the same screenshot, with the pointing prompt
                var p: CGPoint?, q: CGPoint?
                var pointing = 0.0
                if let labelled {
                    p = labelled
                } else if let sent, step.isClick || step.action == .drag || (step.action == .scroll && step.target != nil) {
                    let found = try await find(step.target ?? "", url: sent.url, region: sent.shot.region, what: "pointing at")
                    (p, pointing) = found
                    if step.action == .drag, let end = step.targetEnd {
                        let foundEnd = try await find(end, url: sent.url, region: sent.shot.region, what: "pointing at the end")
                        q = foundEnd.0
                        pointing += foundEnd.1
                    }
                    guard alive(id) else { return }
                    if (step.isClick && p == nil) || (step.action == .drag && (p == nil || q == nil)) {
                        ending = "Stopped at step \(n): the model could not point at \(step.target ?? "the target")"
                        break steps
                    }
                }

                let title = "Step \(n): \(step.historyLine)"
                let timing = (asked > 0 ? "step \(sec(asked)) · " : "") + (pointing > 0 ? "pointing \(sec(pointing)) · " : "") + "total \(sec(Date().timeIntervalSince(start)))"
                var flight = 0.0
                if step.action == .drag, let p, let q {
                    flight = overlay.drag(from: p, to: q, step.historyLine)
                } else if let p {
                    flight = overlay.point(at: p, .acting, step.historyLine)
                }
                guard await approve(title, timing: timing, flight: flight, id: id) else {
                    if alive(id) { stop(note: "Cancelled at step \(n)") }
                    return
                }
                guard Events.allowed(prompt: true) else {
                    ending = "Accessibility is not allowed for \(AppController.launcher): allow it in System Settings > Privacy & Security > Accessibility, then ask again"
                    break steps
                }
                if p == nil { overlay.say(.acting, step.historyLine) }
                await perform(step, at: p, to: q)
                guard alive(id) else { return }
                history.append(step.historyLine)
                log.add("    done: \(step.historyLine)" + (p.map { " at screen \(pt($0)) pt" } ?? ""))
                var entry: [String: Any] = ["step": n, "tool": step.action.rawValue, "line": step.historyLine, "result": "ok",
                                            "plan_seconds": ((asked + pointing) * 100).rounded() / 100, "step_seconds": (Date().timeIntervalSince(start) * 100).rounded() / 100]
                if let lastPointer { entry["pointer"] = lastPointer }
                lastPointer = nil
                trace.append(entry)
                try await Task.sleep(nanoseconds: 900_000_000)                    // let the screen settle
                if !step.isClick { carried = nil }

                // After a click that changed nothing: one zoomed second look around the first point.
                // Not before typing: a click that only puts the caret in a field changes almost nothing.
                if step.isClick, let first = p, let target = step.target, let sent, queue?.first?.action != .type {
                    let after = try await Capture.mainDisplay()
                    let differing = await Task.detached { ImageOps.differingPixels(sent.shot.full, after.full) }.value
                    guard alive(id) else { return }
                    if differing >= ImageOps.unchangedBelow {
                        carried = after                                           // it is the next step's screenshot
                        continue
                    }
                    log.add("    the screen did not change after the click (\(differing) differing pixels): zoomed second look")
                    if !history.isEmpty { history[history.count - 1] += " (nothing changed on the screen)" }
                    let window = Geometry.zoomWindow(around: first, in: after.region, zoom: AppController.zoom)
                    let pixels = Geometry.pixelRect(points: window, displayOrigin: after.region.origin, scale: after.scale)
                    let region = Geometry.pointsRect(pixels: pixels, displayOrigin: after.region.origin, scale: after.scale)
                    let url: String? = await Task.detached {
                        ImageOps.zoomed(after.full, pixelRect: pixels, longSide: AppController.zoomSide).flatMap { ImageOps.dataURL($0) }
                    }.value
                    guard let url else { continue }
                    overlay.say(.thinking, "looking closer", thinking: true)
                    let (second, seconds) = try await find(target, url: url, region: region, what: "second look at")
                    guard alive(id) else { return }
                    guard let second, hypot(second.x - first.x, second.y - first.y) >= 3 else {
                        log.add("    the second look gives the same place; going on")
                        continue
                    }
                    let hop = overlay.point(at: second, .acting, step.historyLine)
                    guard await approve("Step \(n), second look: \(step.historyLine)", timing: "pointing \(sec(seconds))", flight: hop, id: id) else {
                        if alive(id) { stop(note: "Cancelled at step \(n), second look") }
                        return
                    }
                    await perform(step, at: second, to: nil)
                    guard alive(id) else { return }
                    log.add("    done again at screen \(pt(second)) pt")
                    try await Task.sleep(nanoseconds: 900_000_000)
                }
            }
            guard alive(id) else { return }
            lastEnding = ending
            log.add(ending)
            if ending.hasPrefix("Done") {
                await finished(closing, id: id)
            } else {
                overlay.say(.sorry, (ending.count > 58 ? String(ending.prefix(56)) + "…" : ending).lowercased())
                await linger(6, id: id)
            }
        } catch {
            await fail(error, id: id)
        }
    }
}
