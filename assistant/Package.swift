// swift-tools-version:5.9
// Bonsai assistant: a menu-bar app that asks a local Bonsai model (through an OpenAI-compatible
// server such as LM Studio) where things are on the screen, points at them and carries out steps.
// Builds with the command-line tools alone (no Xcode): see run.sh.
import PackageDescription

let package = Package(
    name: "BonsaiAssistant",
    platforms: [.macOS(.v14)],
    dependencies: [
        // Argmax's open-source SDK: on-device speech (WhisperKit: speech to text; TTSKit: text to speech).
        .package(url: "https://github.com/argmaxinc/argmax-oss-swift.git", from: "0.9.0"),
    ],
    targets: [
        // Everything that needs no screen: units, parsing, prompts, image handling, the server client.
        .target(name: "AssistantCore"),
        // The app: menu bar, hotkey, input bar, overlay, capture, system events, log window.
        .executableTarget(name: "bonsai-assistant", dependencies: [
            "AssistantCore", .product(name: "WhisperKit", package: "argmax-oss-swift"),
        ]),
        // Checks of the core, as a plain program (XCTest is not part of the command-line tools).
        .executableTarget(name: "assistant-tests", dependencies: ["AssistantCore"]),
    ]
)
