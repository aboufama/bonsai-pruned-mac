"""Single computer-use actions: rendering a case as a chat sample, reading an answer back, scoring it,
and turning recorded pyautogui steps into actions. Two hand-made cases; no GPU, no torch, no data:
    python3 tests/test_actions.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from weightlab import actions, chat

original_supervise = chat.supervise

click = {"id": "hand-click", "image": "screens/a.png", "width": 1200, "height": 800,
         "goal": "Save the document as a PDF",
         "history": ["left_click [40, 12]", 'type "report\\n"'],
         "action": {"name": "left_click", "arguments": {"coordinate": [644.4, 268.8]}}}
drag = {"id": "hand-drag", "image": "/data/b.png", "width": 1200, "height": 800,
        "goal": "Move the photo into the Trips folder", "history": [],
        "action": {"name": "left_click_drag", "arguments": {"start_coordinate": [254.4, 272.0], "coordinate": [768.0, 272.0]}}}

# ---- rendering
s = actions.action_case(click, base="/data/mac/agentnet")
assert s["kind"] == "action_call" and s["category"] == "action:left_click" and s["id"] == "hand-click"
assert [t["function"]["name"] for t in s["tools"]] == ["computer_use"] and s["system"] in chat.SYSTEMS
assert s["target"] == ("<tool_call>\n<function=computer_use>\n<parameter=action>\nleft_click\n</parameter>\n"
                       "<parameter=coordinate>\n[537, 336]\n</parameter>\n</function>\n</tool_call>"), s["target"]
assert "".join(t for t, _ in s["pieces"]) == s["target"]
digits = [(t, band) for t, band in s["pieces"] if band]
assert [t for t, _ in digits] == ["537", "336"]
assert abs(digits[0][1][0] - 525) < 1e-6 and abs(digits[0][1][1] - 549) < 1e-6      # 644.4 px +- 1.2 % of 1200 px, on the grid
assert abs(digits[1][1][0] - 318) < 1e-6 and abs(digits[1][1][1] - 354) < 1e-6      # the same 14.4 px on the 800 px side
assert s["request"] == ("\nPlease generate the next move according to the UI screenshot, instruction and previous actions.\n\n"
                        "Instruction: Save the document as a PDF\n\nPrevious actions:\n"
                        'Step 1: left_click [40, 12]\nStep 2: type "report\\n"'), s["request"]
assert s["item"] == {"id": "hand-click", "path": "/data/mac/agentnet/screens/a.png", "max_side": 1280, "size": (1200, 800)}
assert actions.action_case(click) == actions.action_case(click)                    # deterministic per case

d = actions.action_case(drag)
assert d["target"] == ("<tool_call>\n<function=computer_use>\n<parameter=action>\nleft_click_drag\n</parameter>\n"
                       "<parameter=start_coordinate>\n[212, 340]\n</parameter>\n<parameter=coordinate>\n[640, 340]\n</parameter>\n"
                       "</function>\n</tool_call>"), d["target"]
assert [t for t, band in d["pieces"] if band] == ["212", "340", "640", "340"]
assert d["request"].endswith("Previous actions:\nNone") and d["item"]["path"] == "/data/b.png"
late = dict(click, history=[f"key down" for _ in range(20)], meta={"step": 31})   # 20 of 31 earlier steps were kept
assert actions.action_case(late)["request"].split("Previous actions:\n")[1].split("\n")[0] == "Step 24: key down"
assert actions.action_case(late)["request"].count("Step ") == 8

# ---- the trainers reach action samples through chat.supervise; everything else is passed on
assert getattr(chat.supervise, "_takes_actions", False) and chat.supervise is not original_supervise
import types
try:
    original_supervise(types.SimpleNamespace(processor=types.SimpleNamespace(tokenizer=None)), None, s)
    raise SystemExit("the unpatched chat.supervise accepted an action sample without its screenshot")
except KeyError:
    pass

# ---- reading an answer back and scoring it
for sample, case in ((s, click), (d, drag)):
    got = actions.parse_answer("<think>\n\n</think>\n\n" + sample["target"])
    assert got == {"name": case["action"]["name"], "arguments": actions.on_grid(case["action"]["arguments"], 1200, 800)}, got
    r = actions.score_answer(case, sample["target"])
    assert r["ok"] and r["name_ok"] and max(r["dist"]) < 1, r

call = lambda **a: chat.render_call("computer_use", a)
assert actions.score_answer(click, call(action="left_click", coordinate=[553, 350]))["ok"]             # 19.2 px and 11.2 px off: 22 px
far = actions.score_answer(click, call(action="left_click", coordinate=[562, 336]))                    # 30 px to the right
assert not far["ok"] and far["name_ok"] and far["why"] == "point too far" and far["dist"] == [30.0], far
other = actions.score_answer(click, call(action="double_click", coordinate=[537, 336]))
assert not other["ok"] and not other["name_ok"] and other["why"] == "another action"
assert actions.score_answer(click, '<tool_call>\n{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [537, 336]}}\n</tool_call>')["ok"]
assert actions.score_answer(click, "I would click the Save button.") == {
    "ok": False, "name_ok": False, "parsed": False, "expected": "left_click", "got": None, "dist": [], "why": "no computer_use call"}
assert not actions.score_answer(drag, call(action="left_click_drag", start_coordinate=[212, 340], coordinate=[600, 340]))["ok"]   # end 48 px off
assert not actions.score_answer(drag, call(action="left_click_drag", start_coordinate=[640, 340], coordinate=[212, 340]))["ok"]   # backwards
assert actions.score_answer(drag, call(action="left_click_drag", coordinate=[640, 340]))["why"] == "start_coordinate missing"

typed = dict(click, action={"name": "type", "arguments": {"text": "quarterly report\n"}})
t = actions.action_case(typed)
assert t["target"].endswith("<parameter=text>\nquarterly report\n\n</parameter>\n</function>\n</tool_call>")
assert actions.parse_answer(t["target"])["arguments"]["text"] == "quarterly report\n"                # the final newline survives
assert actions.score_answer(typed, t["target"])["ok"]
assert actions.score_answer(typed, call(action="type", text="quarterly report"))["why"] == "other text"   # typed, not submitted
keyed = dict(click, action={"name": "key", "arguments": {"keys": ["cmd", "shift", "s"]}})
assert actions.action_case(keyed)["target"].count('<parameter=keys>\n["cmd", "shift", "s"]\n</parameter>') == 1
assert actions.score_answer(keyed, call(action="key", keys=["shift", "command", "S"]))["ok"]
assert not actions.score_answer(keyed, call(action="key", keys=["cmd", "s"]))["ok"]
scrolled = dict(click, action={"name": "scroll", "arguments": {"coordinate": [600.0, 400.0], "pixels": -10}})
assert actions.action_case(scrolled)["target"].count("<parameter=coordinate>\n[500, 500]\n</parameter>\n<parameter=pixels>\n-10\n</parameter>") == 1
assert actions.score_answer(scrolled, call(action="scroll", coordinate=[100, 100], pixels=-3))["ok"]   # direction decides
assert not actions.score_answer(scrolled, call(action="scroll", coordinate=[500, 500], pixels=10))["ok"]
done = dict(click, action={"name": "terminate", "arguments": {"status": "success"}})
assert actions.score_answer(done, actions.action_case(done)["target"])["ok"]
assert not actions.score_answer(done, call(action="terminate", status="failure"))["ok"]

total = actions.score_answers([click, click, drag], [s["target"], call(action="left_click", coordinate=[562, 336]), d["target"]])
assert total["n"] == 3 and total["correct"] == 0.6667 and total["name"] == 1.0, total
assert total["by_action"]["left_click"] == {"n": 2, "correct": 0.5, "name": 1.0} and total["why"] == {"point too far": 1}

# ---- the family's two-step drag, if we ever train that form
move, second = actions.family_drag(drag)
assert move["action"] == {"name": "mouse_move", "arguments": {"coordinate": [254.4, 272.0]}}
assert second["action"] == {"name": "left_click_drag", "arguments": {"coordinate": [768.0, 272.0]}} and second["history"] == ["mouse_move [212, 340]"]
assert "<parameter=start_coordinate>" not in actions.action_case(second)["target"]

# ---- recorded steps (AgentNet's pyautogui code, points normalised 0-1) -> actions
one = lambda code: actions.step_actions(code)
assert one("pyautogui.click(x=0.537, y=0.336)") == [{"name": "left_click", "arguments": {"coordinate": [0.537, 0.336]}, "repeat": 1}]
assert one("pyautogui.moveTo(x=0.212, y=0.34)\npyautogui.dragTo(x=0.64, y=0.34, button='left')") == [
    {"name": "left_click_drag", "arguments": {"start_coordinate": [0.212, 0.34], "coordinate": [0.64, 0.34]}, "repeat": 1}]
assert one("pyautogui.write(message='quarterly report')\npyautogui.press('enter')")[0]["arguments"] == {"text": "quarterly report\n"}
assert one("pyautogui.hotkey(['command', 'v'])")[0]["arguments"] == {"keys": ["cmd", "v"]}
assert one("pyautogui.moveTo(x=0.5, y=0.5)\npyautogui.scroll(-10)")[0] == {"name": "scroll", "arguments": {"coordinate": [0.5, 0.5], "pixels": -10}, "repeat": 1}
assert one("pyautogui.moveTo(x=0.5, y=0.5)\npyautogui.hscroll(1)\npyautogui.scroll(-9)")[0]["name"] == "scroll"
assert len(one("pyautogui.moveTo(x=0.5, y=0.5)\npyautogui.hscroll(5)\npyautogui.scroll(-6)")) == 2          # no clear axis: not one action
assert one("pyautogui.press('backspace', presses=3)")[0]["repeat"] == 3
assert one("computer.terminate(status='fail')")[0]["arguments"] == {"status": "failure"}
assert one("computer.tripleClick(x=0.1, y=0.2)")[0]["name"] == "triple_click"
assert len(one("pyautogui.press('backspace')\npyautogui.write(message='x')")) == 2
for bad in ("import os", "os.system('ls')", "pyautogui.click(x=__import__('os').getcwd(), y=0)"):
    try:
        one(bad)
        raise SystemExit(f"accepted {bad!r}")
    except ValueError:
        pass
assert actions.valid_keys(["cmd", "shift", "4"]) and actions.valid_keys(["enter"]) and actions.valid_keys(["f5"])
assert not any(actions.valid_keys(k) for k in (["cv"], ["cmd"], ["cmd", "a", "c"], ["√"], [""], ["D"]))
assert actions._unusable({"name": "left_click", "arguments": {"coordinate": [0.5, 1.0]}}, 1200, 800, True) == "a point on the screen edge"
assert actions._unusable({"name": "left_click_drag", "arguments": {"start_coordinate": [0.5, 0.5], "coordinate": [0.51, 0.5]}}, 1200, 800, True)
assert actions._unusable({"name": "terminate", "arguments": {"status": "success"}}, 1200, 800, False)
assert actions._unusable({"name": "type", "arguments": {"text": "hello\n"}}, 1200, 800, True) is None
assert actions.describe("left_click_drag", {"start_coordinate": [212, 340], "coordinate": [640, 340]}) == "left_click_drag [212, 340] to [640, 340]"
assert actions.describe("key", {"keys": ["cmd", "s"]}) == "key cmd+s" and actions.describe("key", {"keys": ["backspace"]}, 3) == "key backspace x3"

# ---- the tool definition the model is shown
tool = actions.COMPUTER_USE_TOOL["function"]
assert tool["name"] == "computer_use" and tool["parameters"]["required"] == ["action"]
assert set(tool["parameters"]["properties"]) == {"action", "keys", "text", "start_coordinate", "coordinate", "pixels", "time", "status"}
assert all(f"`{a}`" in tool["parameters"]["properties"]["action"]["description"] for a in tool["parameters"]["properties"]["action"]["enum"])
assert "1000x1000" in tool["description"]

# ---- orchestrator steps: the answer says the next step in words, the point stays in the case
step = {"id": "hand-step", "image": "screens/a.png", "width": 1200, "height": 800, "goal": "Save the document as a PDF",
        "history": ['click the "File" menu', 'click "Export To" in the File menu'], "meta": {"step": 6},
        "step": {"action": "click", "target": 'the "PDF" item in the Export To submenu'}, "point": [644.4, 268.8], "point_end": None}
p = actions.step_case(step, base="/data/mac/agentnet")
assert p["kind"] == "step_call" and p["category"] == "step:click" and [t["function"]["name"] for t in p["tools"]] == ["next_step"]
assert p["target"] == ('<tool_call>\n<function=next_step>\n<parameter=action>\nclick\n</parameter>\n<parameter=target>\n'
                       'the "PDF" item in the Export To submenu\n</parameter>\n</function>\n</tool_call>'), p["target"]
assert p["pieces"] == [[p["target"], None]] and "644" not in p["target"] and "537" not in p["target"]     # no point in the answer
assert p["request"].endswith('Previous actions:\nStep 5: click the "File" menu\nStep 6: click "Export To" in the File menu')
assert p["item"]["path"] == "/data/mac/agentnet/screens/a.png"
nxt = lambda **a: chat.render_call("next_step", a)
assert actions.parse_step("<think>\n\n</think>\n\n" + p["target"]) == step["step"] and actions.score_step(step, p["target"])["ok"]
close = actions.score_step(step, nxt(action="click", target="the PDF item in the Export submenu"))
assert close["ok"] and close["target"] == 1.0, close                               # the same content words
vague = actions.score_step(step, nxt(action="click", target="the gear icon in the toolbar"))
assert not vague["ok"] and vague["action_ok"] and vague["target"] == 0.0 and vague["why"] == "another target, by its words"
assert actions.score_step(step, nxt(action="double_click", target=step["step"]["target"]))["why"] == "another action"
assert actions.score_step(step, "Click the PDF item.")["why"] == "no next_step call"
assert actions.step_points(step) == [('the "PDF" item in the Export To submenu', [644.4, 268.8])]
pull = dict(step, step={"action": "drag", "target": "the photo of the beach", "target_end": "the Trips folder in the sidebar"},
            point=[254.4, 272.0], point_end=[768.0, 272.0])
assert actions.step_case(pull)["target"].count("<parameter=target_end>\nthe Trips folder in the sidebar\n</parameter>") == 1
assert actions.step_points(pull) == [("the photo of the beach", [254.4, 272.0]), ("the Trips folder in the sidebar", [768.0, 272.0])]
assert not actions.score_step(pull, nxt(action="drag", target="the photo of the beach", target_end="the Trash"))["ok"]
write = dict(step, step={"action": "type", "target": "the search field", "text": "quarterly report\n"}, point=None)
assert actions.parse_step(actions.step_case(write)["target"]) == write["step"] and actions.step_points(write) == []
assert actions.score_step(write, nxt(action="type", text="quarterly report\n"))["ok"]            # the field is not required
assert actions.score_step(write, nxt(action="type", target="the search field", text="quarterly report"))["why"] == "other text"
press = dict(step, step={"action": "key", "keys": ["cmd", "s"]}, point=None)
assert actions.score_step(press, nxt(action="key", keys=["command", "s"]))["ok"] and not actions.score_step(press, nxt(action="key", keys=["cmd", "p"]))["ok"]
roll = dict(step, step={"action": "scroll", "target": "the list of files", "direction": "down"})
assert actions.score_step(roll, nxt(action="scroll", direction="down"))["ok"] and actions.score_step(roll, nxt(action="scroll", direction="up"))["why"] == "other direction"
end = dict(step, step={"action": "done", "text": "The document is saved as a PDF on the desktop."}, point=None)
assert actions.step_case(end)["target"].count("<parameter=action>\ndone\n</parameter>\n<parameter=text>\nThe document is saved") == 1
assert actions.score_step(end, nxt(action="done", text="Saved."))["ok"]
sums = actions.score_steps([step, step, press], [p["target"], nxt(action="click", target="the gear icon"), nxt(action="key", keys=["cmd", "s"])])
assert sums["n"] == 3 and sums["correct"] == 0.6667 and sums["action"] == 1.0 and sums["mean_target_overlap"] == 0.5, sums

# ---- a short thought: inside the thinking tags before the call when asked for, left out by default
think = dict(step, thought="The Export To submenu is open and lists PDF, the format the task asks for.")
with_thought = actions.step_case(think, thought=True)
assert with_thought["thinking"] and with_thought["target"] == think["thought"] + "\n</think>\n\n" + p["target"]
assert with_thought["pieces"] == [[with_thought["target"], None]]
assert actions.parse_step(with_thought["target"]) == step["step"] and actions.score_step(think, with_thought["target"])["ok"]
assert actions.step_case(think)["target"] == p["target"] and not actions.step_case(think)["thinking"]      # the default
assert not actions.step_case(step, thought=True)["thinking"]                                              # a case without a thought
long = ('I can see that the text "December 1" has been successfully copied to the clipboard from our previous action. '
        "Now we're looking at a completely different application. Looking at our overall progress on the task: 1. "
        "We opened a new tab (completed) 2. We went to the search page (completed) 3. "
        "I notice that Excel appears to be available in the dock on the left side of the screen - I can see what looks like the green icon. "
        "Clicking on the Excel icon in the dock would launch the application, allowing us to create a new spreadsheet where we can paste the deadline we copied earlier today. "
        "After we record this information in Excel, we'll need to return to the browser.")
kept = actions.short_thought(long, "the Excel icon in the dock on the left side of the screen", "record the deadline in Excel")
assert kept == "Excel appears to be available in the dock on the left side of the screen.", kept
assert actions.short_thought("After clicking, the menu opened. This confirms that the previous action worked.", "the Preferences option") is None
assert actions.short_thought("I can see the reply was sent to anna@example.com from the compose window on the screen.", "the compose window") is None
assert actions.short_thought("I notice the Send button next to Maria Lopez in the open chat window.", "the Send button") is None    # a name the task does not give
assert actions.short_thought("I notice the Send button next to Maria Lopez in the open chat window.", "the Send button", "Message Maria Lopez") == (
    "The Send button next to Maria Lopez in the open chat window.")
assert len(actions.short_thought("The search field is empty and active, " + "and very " * 30 + "ready.", "the search field").split()) <= 25

# ---- a recorded action and the dataset's sentence -> a step (verb and purpose removed, values from the recording)
made = lambda name, sentence, **a: actions.step_from({"name": name, "arguments": a}, sentence)
assert made("left_click", "Click the globe icon next to the first citation to access formatting options for that entry.", coordinate=[.1, .2]) == (
    {"action": "click", "target": "the globe icon next to the first citation"}, None)
assert made("left_click", 'Click on "OneDrive for Business" in the dropdown menu to select it.', coordinate=[.1, .2])[0]["target"] == '"OneDrive for Business" in the dropdown menu'
assert made("left_click", "Click to continue.", coordinate=[.1, .2]) == (None, "the description names no target")
assert made("left_click", "Click at coordinates (0.52, 0.31) to continue.", coordinate=[.1, .2])[0] is None
assert made("left_click", 'Type "hello" in the box.', coordinate=[.1, .2]) == (None, "the description starts with another verb")
assert made("left_click_drag", "Drag the quality slider from the left toward the right end of the bar to raise the quality.",
            start_coordinate=[.1, .2], coordinate=[.3, .2])[0] == {"action": "drag", "target": "the quality slider", "target_end": "the right end of the bar"}
assert made("left_click_drag", "Drag the chart upward to reposition it higher on the page.", start_coordinate=[.1, .2], coordinate=[.1, .1])[0] is None
assert made("type", 'Type "abu dha" in the empty "From?" field to begin entering the city.', text="abu dha")[0] == {
    "action": "type", "target": 'the empty "From?" field', "text": "abu dha"}
assert made("type", 'Type "definition" to replace the selected word.', text="definition\n")[0] == {"action": "type", "text": "definition\n"}
assert made("key", "Press Command+C to copy the selected text.", keys=["cmd", "c"])[0] == {"action": "key", "keys": ["cmd", "c"]}
assert made("scroll", "Scroll down slightly in the job preferences form to view the next section.", coordinate=[.5, .5], pixels=-10)[0] == {
    "action": "scroll", "target": "the job preferences form", "direction": "down"}
assert made("scroll", "Scroll down to see more.", coordinate=[.5, .5], pixels=10)[0] is None            # the recording says up
assert made("terminate", "Terminate the task with a success status as both conversation histories have been deleted.", status="success")[0] == {
    "action": "done", "text": "Both conversation histories have been deleted."}
assert made("terminate", "Terminate the task with success status.", status="success")[0] == {"action": "done"}
assert made("triple_click", "Triple-click the paragraph.", coordinate=[.1, .2])[0] is None
assert actions.describe_step(write["step"]) == 'type "quarterly report" in the search field and press Return'
assert actions.describe_step(pull["step"]) == "drag the photo of the beach to the Trips folder in the sidebar"
assert [actions.describe_step(c["step"]) for c in (step, press, roll, end)] == [
    'click the "PDF" item in the Export To submenu', "press cmd+s", "scroll down in the list of files", "done"]
words = actions.NEXT_STEP_TOOL["function"]
assert "Do not give coordinates" in words["description"] and "point at it" in words["description"]
assert words["parameters"]["properties"]["action"]["enum"] == ["open_app", "open_url", "click", "double_click", "right_click", "drag", "type", "key", "scroll", "menu", "look", "done"]   # planner format v1; the first eight of the old list are all in it
assert set(words["parameters"]["properties"]) == {"action", "target", "target_end", "text", "keys", "direction", "app", "url", "id", "path"}

# ---- the optional mix entries are off by default
from weightlab import mixes
assert all("action" not in name and "step" not in name for name, _, _ in mixes.DEFAULT_MIX)
assert mixes.ACTION_MIX[0] == "mac:agentnet:actions:train" and mixes.STEP_MIX[0] == "mac:agentnet:steps:train"
print("ok")
