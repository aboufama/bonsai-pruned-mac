"""Design tools: dense icon tool palettes, layer lists, canvases and property panels."""
from ..ui import esc, CHEV_D, CHEV_R
from ..vocab import C, P

NAME = "design"
KIND = "either"
VARIANTS = {"figma": "train", "whiteboard": "train", "illustrator": "dev", "photoshop": "test"}

# ---- tools ----------------------------------------------------------------------------------
C("des.select", "Move tool|Pointer tool|Selection tool", "mouse-pointer-2|mouse-pointer|square-mouse-pointer",
  "switch to the plain arrow for picking up and dragging objects|go back to the default arrow that grabs things on the canvas|get the ordinary arrow for clicking on objects in the artwork")
C("des.hand", "Hand tool|Pan|Grab canvas", "hand|hand-grab|grab|pointer", n="hand tool|pan|grab",
  intents="drag the visible area around to see another part of the drawing|scroll the artwork by dragging it|slide the document around inside the window")
C("des.pen", "Pen tool|Vector path|Bezier pen", "pen-tool|spline|vector-square|spline-pointer",
  "draw a precise curve by placing anchor points|build a shape outline one anchor point at a time|plot smooth curves with control handles")
C("des.pencil", "Pencil|Freehand|Sketch tool", "line-squiggle|signature|pen-line",
  "scribble a rough stroke by dragging|draw loosely like on paper|doodle an irregular stroke with the mouse")
C("des.brush", "Brush|Paintbrush|Paint tool", "brush|paintbrush|paintbrush-vertical",
  "lay down soft strokes of color|apply color with broad strokes|daub color onto the image by dragging")
C("des.eraser", "Eraser|Erase tool|Rubber", "eraser|brush-cleaning|circle-off",
  "rub out parts of the drawing|wipe away pixels I do not want|scrub off part of what I drew")
C("des.text", "Text tool|Type tool|Add text", "type|type-outline|a-large-small|baseline|text-cursor|case-sensitive",
  "put some words onto the canvas|write a caption or heading in the design|place lettering in the artwork")
C("des.rect", "Rectangle|Box shape|Rectangle tool", "square|rectangle-horizontal|squircle",
  "draw a four-sided block|add a figure with four right-angle corners|drag out a boxy block")
C("des.ellipse", "Ellipse|Oval|Circle tool", "circle|circle-dashed|circle-dot",
  "draw a round figure|add a perfectly round or egg-shaped outline|drag out a ring-like figure")
C("des.line", "Line|Straight line|Line tool", "slash|move-diagonal|move-diagonal-2",
  "draw a single stroke between two points|connect two points with a thin rule|add a thin rule from one point to another")
C("des.shapes", "Shapes|Shape library|Polygon", "shapes|hexagon|triangle",
  "insert a ready-made star, arrow or other figure|pick a prebuilt geometric figure to drop in|add a multi-sided figure")
C("des.crop", "Crop|Trim canvas|Crop tool", "crop|proportions|scan",
  "cut away the outer edges of the image|keep only a rectangular part of the picture and discard the rest|chop off the margins of the image")
C("des.frame", "Frame|Artboard|New frame", "frame|layout-template|app-window|panels-top-left",
  "add a blank screen-sized container to design in|create another page-like container on the canvas|set up an empty container sized for a device screen")
C("des.pipette", "Eyedropper|Color picker|Sample color", "pipette|syringe|droplet",
  "pick up a hue from somewhere in the image|grab the exact shade under the cursor|lift a tint from an existing pixel")
C("des.fill", "Fill|Paint bucket|Flood fill", "paint-bucket|paint-roller|spray-can|droplets|paintbrush-vertical",
  "pour a solid shade into an enclosed area|cover a whole region with one shade in a single click|drench a closed area with the current shade")
C("des.gradient", "Gradient|Blend tool|Color ramp", "blend|contrast|rainbow",
  "make a smooth transition from one shade to another|fade one hue gradually into a second one|create a smooth multi-hue fade across the area")
C("des.ruler", "Measure|Ruler|Dimension tool", "ruler|pencil-ruler|ruler-dimension-line",
  "check the distance between two points|find out how many pixels apart two things are|get the length between two spots on the canvas")
C("des.lasso", "Lasso|Freeform select|Lasso tool", "lasso|lasso-select|square-dashed-mouse-pointer",
  "draw an irregular outline around the area I want to work on|rope off an odd-shaped region by tracing around it|trace a loose boundary around part of the image")
C("des.marquee", "Rectangular marquee|Box select|Area select", "square-dashed|mouse-pointer-square-dashed|scan-line",
  "drag out a dotted rectangle around the region I want to work on|mark off a rectangular region with a dotted outline|enclose a rectangular region of the image with marching ants")
C("des.wand", "Magic wand|Auto select|Smart select", "wand|wand-sparkles|sparkles",
  "pick every neighbouring pixel of a similar shade in one click|grab a whole same-colored region automatically|have the app find the edges of an area for me")
C("des.stamp", "Clone stamp|Clone|Stamp tool", "stamp|copy-check|flip-horizontal-2",
  "paint with pixels copied from another part of the image|reproduce texture from one spot onto another by painting|cover a blemish using pixels sampled elsewhere")
C("des.image", "Place image|Insert picture|Add image", "image|images|image-up|file-image",
  "bring a photo from my disk into the design|drop a bitmap from my computer onto the canvas|embed a photo file in the artwork")
C("des.component", "Components|Assets|Symbol library", "component|boxes|blocks|package",
  "browse the reusable building blocks of this file|find a prebuilt reusable element to drop in|look through the shared design pieces")
C("des.sticky", "Sticky note|Note|Post-it", "sticky-note|notebook-pen|notepad-text",
  "stick a small square memo on the board|jot an idea on a little colored square|leave a small paper-like memo on the canvas")
C("des.connector", "Connector|Arrow|Connect shapes", "arrow-up-right|move-up-right|corner-up-right|route|spline",
  "join two boxes with a line that has a pointed end|link two items on the board with a pointing line|draw a pointing line from one item to another")
C("des.present", "Present|Play prototype|Preview", "presentation|monitor-play|square-play|tv-minimal-play",
  "run the design as a clickable demo|see the mockup in action at full size|try out the flow the way a user would experience it")

# ---- arrange --------------------------------------------------------------------------------
_O = "the selected objects"
C("des.al.left", "Align left|Left edges|Align to left", "align-start-vertical|align-horizontal-justify-start|align-horizontal-distribute-start",
  "line up {o} along their left sides|make the left sides of {o} flush|snap {o} to a common left side", o=_O)
C("des.al.hc", "Align horizontal centers|Center horizontally|Align center", "align-center-vertical|align-horizontal-justify-center|separator-vertical",
  "line up {o} on a shared vertical axis through their middles|put the middles of {o} on one vertical axis|stack {o} so their midpoints share one vertical axis", o=_O)
C("des.al.right", "Align right|Right edges|Align to right", "align-end-vertical|align-horizontal-justify-end|align-horizontal-distribute-end",
  "line up {o} along their right sides|make the right sides of {o} flush|snap {o} to a common right side", o=_O)
C("des.al.top", "Align top|Top edges|Align to top", "align-start-horizontal|align-vertical-justify-start|align-vertical-distribute-start",
  "line up {o} along their upper sides|make the upper sides of {o} flush|snap {o} to a common upper side", o=_O)
C("des.al.vc", "Align vertical centers|Center vertically|Align middle", "align-center-horizontal|align-vertical-justify-center|separator-horizontal",
  "line up {o} on a shared horizontal axis through their middles|put the midpoints of {o} on one horizontal axis|arrange {o} so one horizontal axis runs through their midpoints", o=_O)
C("des.al.bottom", "Align bottom|Bottom edges|Align to bottom", "align-end-horizontal|align-vertical-justify-end|align-vertical-distribute-end",
  "line up {o} along their lower sides|make the lower sides of {o} flush|snap {o} to a common lower side", o=_O)
C("des.dist.h", "Distribute horizontally|Horizontal spacing|Space evenly across", "align-horizontal-distribute-center|align-horizontal-space-between|align-horizontal-space-around",
  "put equal gaps between {o} from side to side|even out the side-to-side gaps between {o}|make the left-to-right gaps between {o} identical", o=_O)
C("des.dist.v", "Distribute vertically|Vertical spacing|Space evenly down", "align-vertical-distribute-center|align-vertical-space-between|align-vertical-space-around",
  "put equal gaps between {o} from top to bottom|even out the up-and-down gaps between {o}|make the top-to-bottom gaps between {o} identical", o=_O)
C("des.front", "Bring to front|Move to top of stack|Raise to front", "bring-to-front|layers-arrow-up|chevrons-up",
  "put {o} above everything that overlaps it|make {o} cover the objects it overlaps|lift {o} over all the overlapping objects", o="the selected object")
C("des.back", "Send to back|Move to bottom of stack|Lower to back", "send-to-back|layers-arrow-down|chevrons-down",
  "put {o} underneath everything that overlaps it|tuck {o} behind the objects it overlaps|drop {o} beneath all the overlapping objects", o="the selected object")
C("des.group", "Group|Group selection|Combine into group", "group|combine|square-stack",
  "bundle {o} so they act as one unit|tie {o} together so they behave as a single object|fuse {o} into one unit that travels together", o=_O)
C("des.ungroup", "Ungroup|Break apart|Split group", "ungroup|unlink|split",
  "separate a bundle back into individual objects|release the objects inside this bundle|dissolve the bundle into its separate objects")
C("des.fliph", "Flip horizontal|Mirror horizontally|Flip left to right", "flip-horizontal|unfold-horizontal|square-split-horizontal|flip-horizontal-2",
  "reflect {o} sideways|turn {o} into its side-to-side reflection|reverse {o} from side to side", o="the selected object")
C("des.flipv", "Flip vertical|Mirror vertically|Flip top to bottom", "flip-vertical|flip-vertical-2|square-split-vertical",
  "turn {o} upside down as a reflection|reflect {o} upside down|reverse {o} from head to foot", o="the selected object")
C("des.rot", "Rotate 90°|Rotate clockwise|Quarter turn", "rotate-cw-square|rotate-3d|iteration-cw|rotate-ccw-square",
  "spin {o} by a right angle|swivel {o} by ninety degrees|give {o} a ninety-degree spin", o="the selected object")
C("des.snap", "Snap to grid|Snapping|Magnetic guides", "magnet|grid-2x2-check|crosshair",
  "{enable} objects jumping to the nearest guide line as I drag|turn {on} the pull toward guide lines while dragging|{enable} automatic sticking to nearby edges while dragging")
C("des.mask", "Mask|Add mask|Layer mask", "venetian-mask|circle-dot-dashed|square-dashed-bottom",
  "make part of {o} see-through without erasing anything|conceal areas of {o} non-destructively|cover areas of {o} with a paintable see-through overlay", o="the selected layer")
C("des.newlayer", "New layer|Add layer|Create layer", "layers-plus|diamond-plus|badge-plus",
  "add an empty sheet to the stack to paint on|start another transparent sheet above the current one|insert a blank level into the stacking order")

C("des.prevboard", "Previous artboard|Prior canvas|Earlier sheet", "arrow-big-left|square-chevron-left|circle-chevron-left|square-arrow-left|arrow-big-left-dash",
  "show the drawing surface that comes before this one|flip to the preceding drawing surface of this document|step one drawing surface toward the start of the document")
C("des.nextboard", "Next artboard|Following canvas|Later sheet", "arrow-big-right|square-chevron-right|circle-chevron-right",
  "show the drawing surface that comes after this one|flip to the subsequent drawing surface of this document|step one drawing surface toward the end of the document")

SELECTS = P("des.sel", [
    ("Blend mode", "choose how this layer mixes with the ones beneath it"), ("Font family", "pick a different typeface for the text"),
    ("Font weight", "choose between thin, regular and heavy letterforms"), ("Canvas zoom", "pick a magnification percentage from a list"),
    ("Export format", "choose which file type the artwork is written as"), ("Stroke style", "switch the outline between solid, dashed and dotted"),
    ("Brush preset", "pick a different tip shape for painting"), ("Color profile", "choose between sRGB, Display P3 and CMYK"),
    ("Constraints", "decide how the object pins itself when its container resizes"), ("Stroke position", "put the outline inside, outside or centered on the edge"),
    ("Text style", "apply a saved heading or body typography preset"), ("Grid type", "switch between column, row and square guides"),
    ("Sampling", "choose whether the tool reads one layer or all of them"), ("Units", "switch between pixels, points and millimetres"),
    ("Resampling", "choose the algorithm used when scaling pixels"), ("Cap style", "choose butt, round or square ends for strokes"),
    ("Device preset", "pick a phone, tablet or desktop screen size"), ("Corner type", "switch between rounded, bevelled and sharp corners"),
    ("Easing", "choose how the transition accelerates and slows down"), ("Scale mode", "decide whether strokes and effects grow with the object"),
])
OPTIONS = {
    "Blend mode": ["Normal", "Multiply", "Screen", "Overlay", "Darken", "Lighten", "Color dodge"], "Font family": ["Inter", "Helvetica Neue", "Georgia", "IBM Plex Sans", "Futura"],
    "Font weight": ["Light", "Regular", "Medium", "Semibold", "Bold"], "Canvas zoom": ["50%", "100%", "200%", "Fit to screen", "Fill screen"],
    "Export format": ["PNG", "JPG", "SVG", "PDF", "WebP"], "Stroke style": ["Solid", "Dashed", "Dotted"], "Brush preset": ["Hard round", "Soft round", "Chalk", "Airbrush"],
    "Color profile": ["sRGB", "Display P3", "Adobe RGB", "CMYK"], "Constraints": ["Left", "Right", "Left and right", "Center", "Scale"],
    "Stroke position": ["Inside", "Center", "Outside"], "Text style": ["Heading 1", "Heading 2", "Body", "Caption"], "Grid type": ["Columns", "Rows", "Square grid"],
    "Sampling": ["Current layer", "Current and below", "All layers"], "Units": ["Pixels", "Points", "Millimetres", "Inches"],
    "Resampling": ["Bicubic", "Bilinear", "Nearest neighbour"], "Cap style": ["Butt", "Round", "Square"], "Device preset": ["Phone", "Tablet", "Desktop", "Watch"],
    "Corner type": ["Round", "Bevel", "Miter"], "Easing": ["Linear", "Ease in", "Ease out", "Spring"], "Scale mode": ["Scale strokes", "Keep stroke width"],
}
CHECKS = P("des.opt", [
    ("Anti-alias", "{enable} smoothing of jagged edges"), ("Contiguous", "{enable} limiting the tool to touching pixels only"),
    ("Sample all layers", "{enable} reading pixels from every sheet in the stack"), ("Auto-select", "{enable} picking whatever I click without choosing it in the list first"),
    ("Show transform controls", "{show} the resize handles around the picked object"), ("Clip content", "{enable} hiding whatever spills outside the container"),
    ("Constrain proportions", "{enable} keeping width and height in the same ratio while resizing"), ("Pixel preview", "turn {on} the view that shows how the art rasterizes"),
    ("Scale strokes and effects", "{enable} outlines growing along with the object"), ("Dither", "turn {on} the noise that hides banding in fades"),
    ("Reverse", "{enable} swapping the start and end of the fade"), ("Protect transparency", "{enable} blocking paint on empty pixels"),
    ("Snap to pixel grid", "{enable} keeping edges on whole pixel boundaries"), ("Show layout grid", "{show} the column guides over the page"),
    ("Outline mode", "turn {on} the wireframe-only display"), ("Smart guides", "turn {on} the temporary pink lines that appear while dragging"),
    ("Preserve details", "{enable} keeping fine texture when enlarging"), ("Fix position when scrolling", "{enable} pinning the object while the page moves"),
    ("Absolute position", "{enable} taking the object out of the automatic flow"), ("Tight spacing", "turn {on} the reduced gaps between items"),
])
EFFECTS = P("des.fx", [
    ("Gaussian blur", "soften the whole picture evenly"), ("Unsharp mask", "make edges look crisper"), ("Add noise", "sprinkle random grain over the picture"),
    ("Drop shadow", "put a soft dark offset behind the object"), ("Inner glow", "light up the inside edge of the object"), ("Motion blur", "smear the picture in one direction as if moving"),
    ("Lens correction", "straighten distortion caused by the camera optics"), ("Liquify", "push and pull pixels like wet paint"), ("Emboss", "make the picture look stamped into metal"),
    ("Pixelate", "turn the picture into large square blocks"), ("Levels", "set the black, white and midtone points"), ("Curves", "bend the tonal response with a graph"),
    ("Hue and saturation", "shift the colors around the wheel and change their intensity"), ("Invert colors", "turn the picture into its negative"), ("Posterize", "reduce the picture to a few flat tones"),
    ("Vignette", "darken the corners of the picture"), ("Black and white", "remove all color from the picture"), ("Background blur", "frost whatever sits behind the object"),
])

PROPS = ["X", "Y", "W", "H", "Rotation", "Radius", "Opacity", "Blur", "Spread", "Stroke", "Gap", "Padding", "Min W", "Max W", "Skew", "Scale",
         "Angle", "Offset", "Width", "Height", "Left", "Top", "Tracking", "Leading", "Size", "Weight", "Indent", "Columns", "Gutter", "Margin",
         "Hardness", "Flow", "Tolerance", "Feather", "Smoothing", "Spacing", "Count", "Depth", "Density", "Hue",
         "Saturation", "Lightness", "Alpha", "Red", "Green", "Blue", "Exposure", "Gamma", "Threshold", "Amount", "Jitter", "Taper",
         "Miter", "Dash", "Inset", "Bleed", "Kerning", "Baseline", "Rows", "Order"]
PANELS = ["Layers", "Assets", "Pages", "Properties", "Styles", "Swatches", "Channels", "Paths", "Navigator", "Libraries", "Brushes", "Glyphs", "Symbols",
          "Prototype", "Inspect", "Design", "Variables", "Adjustments", "Character", "Paragraph", "Actions", "Gradients", "Patterns", "Transform",
          "Pathfinder", "Color guide", "Artboards", "Links", "Dev mode", "Annotations"]
LAYERS = ["Header", "Hero image", "Nav bar", "Footer", "Card / Pricing", "CTA button", "Background", "Logo", "Avatar", "Title text", "Subtitle",
          "Icon / Search", "Divider", "Sidebar", "Tab bar", "Status bar", "Illustration", "Overlay", "Shadow", "Mask group", "Input field", "Badge",
          "Tooltip", "Modal", "Grid", "Photo 1", "Photo 2", "Texture", "Highlights", "Color fill 1", "Curves 1", "Sketch", "Line art", "Flats",
          "Shading", "Caption", "Chart", "Map pin", "Toggle", "Stepper", "Thumbnail", "Banner", "Watermark", "Guides", "Notes"]
BOARDS = ["Home", "Login", "Sign up", "Dashboard", "Profile", "Checkout", "Search results", "Onboarding 1", "Onboarding 2", "Empty state", "Settings page",
          "Product detail", "Cart", "Pricing", "Landing", "404 page", "Feed", "Messages", "Order confirmed", "Paywall", "Welcome", "Splash", "Menu", "Filters",
          "Poster A3", "Business card", "Flyer", "Cover"]
PAGES = ["Cover", "Wireframes", "Flows", "Archive", "Playground", "Handoff", "Icons", "Moodboard", "Explorations", "Mobile", "Desktop", "Tablet",
         "Marketing site", "Design system", "Illustrations", "Research", "Final", "Scratch", "Review", "Specs"]
FILES = ["Mobile app redesign", "Marketing site v3", "Brand guidelines", "Checkout flow", "Icon set", "Pitch deck", "Poster series", "Design system",
         "Onboarding revamp", "Dashboard concepts", "Packaging mockup", "Event banner", "Product shots", "Wireframe kit", "Email templates"]

CSS = """
.des-cv{position:relative;overflow:hidden;background:var(--bg3)}
.des-dots{background-image:radial-gradient(var(--bd2) 1px,transparent 1px);background-size:22px 22px;background-color:var(--bg1)}
.des-ab{position:absolute;background:#fff;box-shadow:0 1px 5px rgba(0,0,0,.28);overflow:hidden}
.des-abl{position:absolute;font-size:11px;color:var(--fg1);white-space:nowrap;padding:1px 3px}
.des-o{position:absolute;border-radius:3px}
.des-sel{position:absolute;border:1.5px solid var(--ac)}
.des-sel i{position:absolute;width:7px;height:7px;background:#fff;border:1.5px solid var(--ac)}
.des-rh{flex:none;height:16px;background-color:var(--bg1);background-image:repeating-linear-gradient(90deg,var(--bd2) 0 1px,transparent 1px 10px),repeating-linear-gradient(90deg,var(--fg2) 0 1px,transparent 1px 100px);background-size:auto 5px,auto 11px;background-repeat:repeat-x;background-position:0 100%;border-bottom:1px solid var(--bd)}
.des-rv{flex:none;width:16px;background-color:var(--bg1);background-image:repeating-linear-gradient(0deg,var(--bd2) 0 1px,transparent 1px 10px);background-size:5px auto;background-repeat:repeat-y;background-position:100% 0;border-right:1px solid var(--bd)}
.des-pal{display:grid;gap:2px;padding:5px 4px;background:var(--bg1);align-content:start;flex:none}
.des-ph{display:flex;align-items:center;gap:6px;height:calc(var(--rh) + 2px);padding:0 8px 0 10px;font-weight:600;font-size:.9em;flex:none}
.des-fl{position:absolute;display:flex;align-items:center;gap:2px;padding:4px;background:var(--pop);border:1px solid var(--bd);border-radius:10px;box-shadow:0 6px 22px var(--sh)}
.des-num{height:calc(var(--ch) - 2px);padding:0 6px;gap:6px;font-size:.92em}
.des-num .k{color:var(--fg2);flex:none}
.des-ly{display:flex;align-items:center;gap:6px;height:var(--rh);padding:0 6px;flex:none;white-space:nowrap}
.des-ly.sel{background:var(--acs2)}
.des-th{width:18px;height:14px;border-radius:2px;flex:none;border:1px solid var(--bd2)}
.des-note{position:absolute;padding:8px;font-size:12px;line-height:1.25;color:#222;box-shadow:0 2px 6px rgba(0,0,0,.25);display:flex;align-items:center;text-align:center;justify-content:center}
.des-sw{width:16px;height:16px;border-radius:3px;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.2)}
"""
_HANDLES = "".join(f'<i style="{pos}"></i>' for pos in (
    "left:-4px;top:-4px", "right:-4px;top:-4px", "left:-4px;bottom:-4px", "right:-4px;bottom:-4px",
    "left:calc(50% - 4px);top:-4px", "left:calc(50% - 4px);bottom:-4px", "left:-4px;top:calc(50% - 4px)", "right:-4px;top:calc(50% - 4px)"))


def _tools(ctx, cids, region, active=0, cls="", sep=()):
    out, shown = [], 0
    for cid in cids:
        b = ctx.ibtn(cid, region, cls=cls, on=shown == active)
        if b:
            out.append(b)
            shown += 1
            if shown in sep:
                out.append('<div class="vsep"></div>')
    return "".join(out)


def _num(ctx, label, value, region, w=None):
    attr = ctx.reg("field", "field", label, region=region)
    style = f' style="width:{w}px"' if w else ""
    return f'<div class="inp des-num"{attr}{style}><span class="k">{esc(label)}</span><span class="el f1">{esc(value)}</span></div>'


def _nums(ctx, region, k, cols=2):
    cells = "".join(_num(ctx, *_one_prop(ctx), region) for _ in range(k))
    return f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:6px">{cells}</div>'


def _mock(ctx, dark):
    """Decorative content of an artboard: bars, text lines and blocks (never targets)."""
    rng = ctx.rng
    c1, c2 = ctx.d.color(), ctx.d.color()
    ink = "#e9e9ee" if dark else "#20222a"
    parts = [f'<div class="des-o" style="left:0;top:0;width:100%;height:{rng.randint(7, 12)}%;background:{c1};border-radius:0"></div>']
    y = rng.randint(16, 22)
    for _ in range(rng.randint(3, 5)):
        kind = rng.choice(["text", "text", "img", "cards", "btn"])
        if kind == "text":
            for i in range(rng.randint(2, 3)):
                parts.append(f'<div class="des-o" style="left:8%;top:{y}%;width:{rng.randint(40, 84)}%;height:{2.2 if i else 3.4}%;background:{ink};opacity:{0.75 if not i else 0.28}"></div>')
                y += 5
        elif kind == "img":
            parts.append(f'<div class="des-o" style="left:8%;top:{y}%;width:84%;height:20%;background:linear-gradient(135deg,{c1},{c2})"></div>')
            y += 23
        elif kind == "cards":
            for i in range(3):
                parts.append(f'<div class="des-o" style="left:{8 + i * 29}%;top:{y}%;width:26%;height:13%;background:{ink};opacity:.10"></div>')
            y += 16
        else:
            parts.append(f'<div class="des-o" style="left:8%;top:{y}%;width:{rng.randint(26, 40)}%;height:6%;background:{c2};border-radius:99px"></div>')
            y += 9
        if y > 86:
            break
    return "".join(parts)


def _canvas(ctx, region, n=3, rulers=False, dots=False, extra=""):
    rng = ctx.rng
    names = ctx.d.take("des.boards", BOARDS, n)
    dark = rng.random() < 0.3
    tall = rng.random() < 0.6
    bw = (72 // n) if tall else min(40, 84 // n)
    bh = rng.randint(58, 72) if tall else rng.randint(36, 48)
    x, top = rng.randint(5, 9), rng.randint(12, 18)
    out = []
    pick = rng.randrange(len(names))
    for i, name in enumerate(names):
        attr = ctx.reg("row", rng.choice(["frame", "artboard"]), name, region=region, anchor="row")
        out.append(f'<div class="des-abl"{attr} style="left:{x}%;top:calc({top}% - 18px)">{esc(name)}</div>')
        bg = "#16171c" if dark else "#ffffff"
        out.append(f'<div class="des-ab" style="left:{x}%;top:{top}%;width:{bw}%;height:{bh}%;background:{bg}">{_mock(ctx, dark)}</div>')
        if i == pick:
            sx, sy = x + bw * 0.08, top + bh * rng.uniform(0.3, 0.6)
            out.append(f'<div class="des-sel" style="left:{sx:.1f}%;top:{sy:.1f}%;width:{bw * rng.uniform(0.4, 0.84):.1f}%;height:{bh * rng.uniform(0.1, 0.22):.1f}%">{_HANDLES}</div>')
        x += bw + rng.randint(3, 6)
    cv = f'<div class="des-cv f1{" des-dots" if dots else ""}">{"".join(out)}{extra}</div>'
    if rulers:
        return f'<div class="col f1"><div class="des-rh"></div><div class="row str f1"><div class="des-rv"></div>{cv}</div></div>'
    return cv


def _layers(ctx, region, n, tree=True, thumbs=False):
    rng = ctx.rng
    names = ctx.d.take("des.layers", LAYERS, n)
    kinds = [("type", "baseline", "text-cursor"), ("image", "images", "file-image"), ("square", "rectangle-horizontal", "squircle"),
             ("frame", "layout-template", "app-window"), ("component", "boxes", "blocks"), ("circle", "circle-dashed", "circle-dot")]
    rows, sel, depth = [], rng.randrange(max(1, len(names))), 0
    for i, name in enumerate(names):
        if tree:
            depth = max(0, min(3, depth + rng.choice([-1, 0, 0, 1])))
        attr = ctx.reg("row", "layer", name, region=region, anchor="row")
        obj = f"the {name} layer"
        pre = f'<div class="des-th" style="background:{ctx.d.color()}"></div>' if thumbs else ctx.deco(*rng.choice(kinds), size=13, blank=True)
        eye = ctx.ibtn("hide", region, row=obj, obj=obj, cls="s")
        lock = ctx.ibtn("lock", region, row=obj, obj=obj, cls="s") if rng.random() < 0.55 else ""
        lead = eye if thumbs else ""
        tail = lock if thumbs else lock + eye
        rows.append(f'<div class="des-ly{" sel" if i == sel else ""}"{attr} style="padding-left:{6 + depth * 14}px">{lead}{pre}'
                    f'<span class="el f1">{esc(name)}</span>{tail}</div>')
    return "".join(rows)


def _align_row(ctx, region):
    a = _tools(ctx, ["des.al.left", "des.al.hc", "des.al.right", "des.al.top", "des.al.vc", "des.al.bottom", "des.dist.h", "des.dist.v"], region, active=-1, cls="s")
    return f'<div class="row g2 wrap">{a}</div>'


def _fill_rows(ctx, region, title, k=1):
    rng = ctx.rng
    add = ctx.ibtn("add", region, row=f"the {title.lower()} list", obj=f"the {title.lower()} list", cls="s")
    rows = ""
    for _ in range(k):
        col = ctx.d.color()
        rows += (f'<div class="row g6" style="padding:2px 10px"><div class="des-sw" style="background:{col}"></div><span class="mono sm">{col[1:].upper()}</span>'
                 f'<div class="sp"></div><span class="mut sm">{rng.choice([100, 100, 80, 50, 24])}%</span></div>')
    return f'<div class="bt" style="padding-bottom:6px"><div class="des-ph"><span class="sp">{esc(title)}</span>{add}</div>{rows}</div>'


def _sel(ctx, cid, region, mode="in"):
    """Dropdown whose caption is always visible: inside the box ("in") or to its left ("left")."""
    label = ctx.lab(cid)
    opts = OPTIONS[label]
    attr = ctx.reg("select", "dropdown", label, cid=cid, region=region, anchor="select")
    tid = ctx.last
    ctx.options[tid] = list(opts)
    val = esc(ctx.rng.choice(opts))
    if mode == "in":
        return f'<div class="inp des-num fn"{attr}><span class="k">{esc(label)}</span><span class="nw">{val}</span>{CHEV_D}</div>'
    box = f'<div class="inp des-num f1"{attr}><span class="el f1">{val}</span>{CHEV_D}</div>'
    return f'<div class="row g8"><span class="mut sm nw" data-o="{tid}" style="width:98px">{esc(label)}</span>{box}</div>'


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    big = H >= 1000
    fname = d.one("des.files", FILES)
    ctx.menus.update({
        "mb.object": ["des.group", "des.ungroup", "-", "des.front", "des.back", "-", "des.fliph", "des.flipv", "des.rot", "-", "lock", "hide"],
        "mb.arrange": ["des.al.left", "des.al.hc", "des.al.right", "-", "des.al.top", "des.al.vc", "des.al.bottom", "-", "des.dist.h", "des.dist.v"],
        "mb.layer": ["des.newlayer", "duplicate", "delete", "-", "des.mask", "des.group", "des.ungroup", "-", "des.front", "des.back"],
        "mb.filter": ctx.pick(EFFECTS, 12),
    })
    ctx.ctxmenu = ["copy", "paste", "duplicate", "-", "des.front", "des.back", "-", "des.group", "des.ungroup", "-", "lock", "hide", "rename", "-", "delete"]
    ctx.ctxobj = "the selected layer"
    sels = ctx.pick(SELECTS, 6)
    rng.shuffle(sels)
    checks = ctx.pick(CHECKS, 5)
    panels = d.take("des.panels", PANELS, 6)
    title = f"{fname} — {rng.choice(['Draft', 'Edited', 'v2', 'Shared'])}"
    menus = ["mb.file", "mb.edit", "mb.view", "mb.object", "mb.arrange", "mb.window", "mb.help"]
    people = d.people(4)
    avs = "".join(ctx.av(p, 24) for p in people[:rng.randint(2, 3)])

    if variant == "figma":
        tb, rp, lp = "the toolbar", "the properties panel", "the layers panel"
        tools = _tools(ctx, ["des.select", "des.frame", "des.rect", "des.pen", "des.text", "des.hand", "comment", "des.component"], tb, active=rng.randint(0, 4), sep=(1, 5))
        zoom = _sel(ctx, sels[0], tb) if sels else ""
        acct = ctx.reg("button", "avatar", "Account menu", ui="icon", cid="account", region=tb, anchor="account")
        bar = (f'<div class="tb" style="height:46px">{ctx.ibtn("apps", tb)}<div class="vsep"></div>{tools}<div class="sp"></div>'
               f'<span class="m">{esc(fname)}</span><span class="mut" style="margin-left:4px">{CHEV_D}</span><div class="sp"></div>'
               f'<div class="row" style="gap:2px">{avs}</div>{ctx.tbtn("share", tb, cls="pri")}{ctx.ibtn("des.present", tb)}{zoom}<div{acct}>{ctx.av(people[3], 26)}</div></div>')
        ptabs = ctx.tabs(panels[:2], active=0, region=lp)
        pages = "".join(ctx.nav(p, lp, noun="page", on=i == 0) for i, p in enumerate(d.take("des.pages", PAGES, rng.randint(2, 4))))
        left = (f'<div class="side br" style="width:{rng.choice([232, 248, 264])}px">{ptabs}<div class="des-ph"><span class="sp mut">Page list</span>{ctx.ibtn("add", lp, row="the page list", obj="the list of pages", cls="s")}</div>'
                f'<div class="col" style="flex:none">{pages}</div><div class="hsep" style="margin:6px 0"></div><div class="col f1 clip">{_layers(ctx, lp, 14 + (10 if big else 0))}</div></div>')
        rtabs = ctx.tabs(panels[2:5], active=0, region=rp)
        typ = "".join(f'<div style="padding:3px 10px">{_sel(ctx, c, rp, "left")}</div>' for c in sels[1:4])
        chk = "".join(f'<div style="padding:3px 10px">{ctx.check(ctx.lab(c), rng.random() < 0.5, region=rp, cid=c)}</div>' for c in checks[:2])
        export = f'<div class="bt p8 row g6">{_sel(ctx, sels[4], rp) if len(sels) > 4 else ""}<div class="sp"></div>{ctx.tbtn("export", rp, cls="sm")}</div>'
        right = (f'<div class="side bl" style="width:{rng.choice([248, 264, 280])}px">{rtabs}<div class="p8">{_align_row(ctx, rp)}</div>'
                 f'<div class="bt p8">{_nums(ctx, rp, 6)}</div><div class="bt" style="padding:6px 0">{typ}{chk}</div>{_fill_rows(ctx, rp, "Fills", 2)}{_fill_rows(ctx, rp, "Borders")}'
                 f'{_fill_rows(ctx, rp, "Shadows", 0)}<div class="sp"></div>{export}</div>')
        body = f'<div class="col f1">{bar}<div class="row str f1">{left}{_canvas(ctx, "the canvas", 3 if W >= 1500 else 2)}{right}</div></div>'
    elif variant == "whiteboard":
        tb = "the bottom toolbar"
        tools = _tools(ctx, ["des.select", "des.hand", "des.pencil", "des.sticky", "des.shapes", "des.connector", "des.text", "des.image", "comment", "des.eraser"], tb, active=rng.randint(0, 3), cls="l", sep=(2,))
        notes = []
        cols = ["#ffe66d", "#ffadad", "#a0e7a0", "#9bd0ff", "#e0b3ff", "#ffd29b"]
        texts = d.tasks(12)
        nsec = 3 if W >= 1500 else 2
        secw = 84 // nsec
        for k, name in enumerate(d.take("des.boards", BOARDS, nsec)):
            sattr = ctx.reg("row", "section", name, region="the board", anchor="row")
            sx = 9 + k * (secw + 2)
            notes.append(f'<div class="des-abl b"{sattr} style="left:{sx}%;top:calc(15% - 20px);font-size:12px">{esc(name)}</div>'
                         f'<div style="position:absolute;left:{sx}%;top:15%;width:{secw}%;height:66%;border:1.5px dashed var(--bd2);border-radius:10px;background:var(--bg)"></div>')
        per = 4 if big else 2
        for i, t in enumerate(texts[:nsec * per]):
            attr = ctx.reg("row", "sticky note", t, region="the board", anchor="row", refs=[f'the sticky note that says "{t}"', f'the note reading "{t}"'])
            k, j = i % nsec, i // nsec
            nx = 9 + k * (secw + 2) + 2 + (j % 2) * (secw // 2) + rng.randint(0, 2)
            ny = 19 + (j // 2) * 30 + rng.randint(0, 6)
            notes.append(f'<div class="des-note"{attr} style="left:{nx}%;top:{ny}%;width:120px;height:104px;background:{rng.choice(cols)};transform:rotate({rng.randint(-3, 3)}deg)">{esc(t)}</div>')
        z = "the zoom controls"
        fl_tools = f'<div class="des-fl" style="left:50%;bottom:18px;transform:translateX(-50%)">{tools}</div>'
        fl_title = (f'<div class="des-fl" style="left:14px;top:14px;padding:4px 10px;gap:8px">{ctx.ibtn("home", "the board header")}<span class="b">{esc(fname)}</span>'
                    f'{ctx.ibtn("more", "the board header", anchor="more")}{ctx.ibtn("undo", "the board header")}{ctx.ibtn("redo", "the board header")}</div>')
        acct = ctx.reg("button", "avatar", "Account menu", ui="icon", cid="account", region="the board header", anchor="account")
        fl_right = (f'<div class="des-fl" style="right:14px;top:14px;padding:4px 8px;gap:6px">{avs}{ctx.ibtn("des.present", "the top right bar")}{ctx.ibtn("notif", "the top right bar")}'
                    f'{ctx.tbtn("share", "the top right bar", cls="pri sm")}<div{acct}>{ctx.av(people[3], 26)}</div></div>')
        fl_zoom = (f'<div class="des-fl" style="left:14px;bottom:18px">{ctx.ibtn("zoomout", z, cls="s")}<span class="sm" style="padding:0 6px">{rng.choice([50, 75, 100, 125])}%</span>'
                   f'{ctx.ibtn("zoomin", z, cls="s")}<div class="vsep"></div>{ctx.ibtn("fullscreen", z, cls="s")}</div>')
        fl_help = f'<div class="des-fl" style="right:14px;bottom:18px">{ctx.ibtn("des.snap", "the bottom right corner", state=True, on=True)}{ctx.ibtn("help", "the bottom right corner")}</div>'
        side = "".join(f'<div class="des-fl" style="position:static;flex-direction:column">{ctx.ibtn(c, "the left tool strip")}</div>' for c in ("des.frame", "des.component", "des.ruler", "history") if ctx.has(c, True))
        fl_side = f'<div style="position:absolute;left:14px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:6px">{side}</div>'
        body = f'<div class="col f1"><div class="des-cv des-dots f1">{"".join(notes)}{fl_tools}{fl_title}{fl_right}{fl_zoom}{fl_help}{fl_side}</div></div>'
        menus = []
    elif variant == "illustrator":
        tb, cb, rp = "the tool palette", "the control bar", "the right panels"
        tools = _tools(ctx, ["des.select", "des.pen", "des.pencil", "des.text", "des.line", "des.rect", "des.ellipse", "des.shapes", "des.brush", "des.eraser", "des.rot",
                             "des.gradient", "des.pipette", "des.ruler", "des.crop", "des.hand", "zoomin"], tb, active=rng.randint(0, 5))
        sw = (f'<div style="position:relative;width:30px;height:30px;margin:8px auto"><div class="des-sw" style="position:absolute;right:0;bottom:0;width:19px;height:19px;background:{d.color()}"></div>'
              f'<div class="des-sw" style="position:absolute;left:0;top:0;width:19px;height:19px;background:{d.color()}"></div></div>')
        pal = f'<div class="des-pal br" style="grid-template-columns:auto">{tools}{sw}</div>'
        ctl = (f'<div class="tb">{_sel(ctx, sels[0], cb) if sels else ""}{_num(ctx, *_one_prop(ctx), cb, 86)}{_num(ctx, *_one_prop(ctx), cb, 86)}<div class="vsep"></div>'
               f'{_sel(ctx, sels[1], cb) if len(sels) > 1 else ""}<div class="vsep"></div>{_align_row(ctx, cb)}<div class="vsep"></div>'
               f'{"".join(ctx.check(ctx.lab(c), rng.random() < 0.5, region=cb, cid=c) for c in checks[:2])}<div class="sp"></div>{ctx.ibtn("des.snap", cb, state=False)}{ctx.ibtn("panel.toggle", cb)}</div>')
        dtabs = ctx.tabs([f"{x}.{rng.choice(['ai', 'svg', 'eps'])}" for x in d.files("image", rng.randint(2, 4), ext=False)], active=0, region="the document tabs", cls="box", closable=True)
        t1 = ctx.tabs(panels[:3], active=0, region=rp)
        t2 = ctx.tabs(panels[3:6], active=0, region=rp)
        arr = _tools(ctx, ["des.front", "des.back", "des.group", "des.ungroup", "des.fliph", "des.flipv"], rp, active=-1, cls="s")
        lbar = f'<div class="row g2 bt" style="padding:3px 6px"><span class="xs mut">{rng.randint(3, 9)} Layers</span><div class="sp"></div>{ctx.ibtn("des.mask", rp, cls="s")}{ctx.ibtn("des.newlayer", rp, cls="s")}{ctx.ibtn("delete", rp, cls="s", obj="the selected layer")}</div>'
        right = (f'<div class="side bl" style="width:{rng.choice([270, 290, 310])}px">{t1}<div class="p8 col g8">{_nums(ctx, rp, 6)}<div class="row g2">{arr}</div>'
                 f'{"".join(_sel(ctx, c, rp, "left") for c in sels[2:4])}</div>{_fill_rows(ctx, rp, "Fills and borders", 2)}'
                 f'<div class="bt col f1 clip">{t2}<div class="col f1 clip">{_layers(ctx, rp, 9 + (8 if big else 0), tree=False, thumbs=True)}</div></div>{lbar}</div>')
        sb = "the status bar"
        status = (f'<div class="sbar">{_sbsel(ctx, sels[4], sb) if len(sels) > 4 else ""}<div class="si">{ctx.ibtn("des.prevboard", sb, cls="s")}'
                  f'<span>{rng.randint(1, 3)}</span>{ctx.ibtn("des.nextboard", sb, cls="s")}</div><span>{rng.choice(["Click to pick", "Drag to reposition", "Toggle preview"])}</span><div class="sp"></div>'
                  f'<span>{rng.randint(1, 4)} objects</span><span>CMYK / 8 bit</span></div>')
        body = (f'<div class="col f1">{ctl}<div class="row str f1">{pal}<div class="col f1">{dtabs}{_canvas(ctx, "the canvas", 2, rulers=True)}</div>{right}</div>{status}</div>')
        menus = ["mb.file", "mb.edit", "mb.object", "mb.text", "mb.select", "mb.filter", "mb.view", "mb.window", "mb.help"]
    else:  # photoshop
        tb, ob, rp = "the tool palette", "the options bar", "the right panels"
        tools = _tools(ctx, ["des.select", "des.marquee", "des.lasso", "des.wand", "des.crop", "des.pipette", "des.brush", "des.stamp", "des.eraser", "des.gradient",
                             "des.fill", "des.pencil", "des.pen", "des.text", "des.rect", "des.ellipse", "des.line", "des.shapes", "des.ruler", "des.hand", "zoomin", "zoomout"],
                       tb, active=rng.randint(0, 8), cls="s")
        sw = (f'<div style="position:relative;width:34px;height:34px;margin:8px auto;grid-column:1 / -1"><div class="des-sw" style="position:absolute;right:0;bottom:0;width:21px;height:21px;background:#fff"></div>'
              f'<div class="des-sw" style="position:absolute;left:0;top:0;width:21px;height:21px;background:{d.color()}"></div></div>')
        pal = f'<div class="des-pal br" style="grid-template-columns:auto auto">{tools}{sw}</div>'
        opts = (f'<div class="tb" style="gap:8px">{ctx.ibtn("home", ob, cls="s")}<div class="vsep"></div>{_sel(ctx, sels[0], ob) if sels else ""}{_num(ctx, *_one_prop(ctx), ob, 92)}'
                f'{_num(ctx, *_one_prop(ctx), ob, 92)}{_sel(ctx, sels[1], ob) if len(sels) > 1 else ""}'
                f'{"".join(ctx.check(ctx.lab(c), rng.random() < 0.5, region=ob, cid=c) for c in checks[:3])}<div class="sp"></div>{ctx.search(ob, w=150, cls="soft")}{ctx.ibtn("share", ob)}{ctx.ibtn("panel.toggle", ob)}</div>')
        dtabs = ctx.tabs([f"{x}.{rng.choice(['psd', 'tif', 'png'])} @ {rng.choice([25, 33, 50, 66, 100])}%" for x in d.files("image", rng.randint(2, 4), ext=False)], active=0,
                         region="the document tabs", cls="box", closable=True)
        hue = '<div style="height:10px;border-radius:2px;margin:6px 10px;background:linear-gradient(90deg,#f00,#ff0,#0f0,#0ff,#00f,#f0f,#f00)"></div>'
        sq = f'<div style="height:{90 if big else 64}px;margin:0 10px;border-radius:2px;background:linear-gradient(0deg,#000,transparent),linear-gradient(90deg,#fff,{d.color()})"></div>'
        color = f'<div>{ctx.tabs(panels[:3], active=0, region=rp)}<div style="padding:8px 0 2px">{sq}{hue}</div><div style="padding:2px 10px 8px">{_nums(ctx, rp, 3, cols=3)}</div></div>'
        fx = "".join(ctx.nav(ctx.lab(c), rp, cid=c, noun="adjustment", deco=("sun", "contrast", "droplets", "sun-medium", "sparkle", "circle-dashed")) for c in ctx.pick(EFFECTS, 4 + (3 if big else 0)))
        adj = f'<div class="bt">{ctx.tabs(panels[3:5], active=0, region=rp)}<div class="col py4">{fx}</div></div>'
        lbar = (f'<div class="row g2 bt" style="padding:3px 6px">{ctx.ibtn("link", rp, cls="s", obj="the selected layers")}{ctx.ibtn("des.mask", rp, cls="s")}{ctx.ibtn("des.group", rp, cls="s")}'
                f'<div class="sp"></div>{ctx.ibtn("des.newlayer", rp, cls="s")}{ctx.ibtn("duplicate", rp, cls="s", obj="the selected layer")}{ctx.ibtn("delete", rp, cls="s", obj="the selected layer")}</div>')
        lhead = (f'<div class="row g6" style="padding:6px 8px">{_sel(ctx, sels[2], rp) if len(sels) > 2 else ""}<div class="f1">{_num(ctx, *_one_prop(ctx), rp)}</div></div>')
        lay = f'<div class="bt col f1 clip"><div class="des-ph">{esc(panels[5]) if len(panels) > 5 else "Stack"}</div>{lhead}<div class="col f1 clip">{_layers(ctx, rp, 10 + (9 if big else 0), tree=False, thumbs=True)}</div>{lbar}</div>'
        right = f'<div class="side bl" style="width:{rng.choice([270, 290, 320])}px">{color}{adj}{lay}</div>'
        status = (f'<div class="sbar"><span>{rng.choice([25, 33.3, 50, 66.7, 100])}%</span><span>Doc: {rng.uniform(4, 180):.1f}M/{rng.uniform(190, 900):.1f}M</span>'
                  f'<span>{rng.choice([3840, 4096, 6000])} px × {rng.choice([2160, 2731, 4000])} px ({rng.choice([72, 144, 300])} ppi)</span><div class="sp"></div>{ctx.ibtn("des.snap", "the status bar", cls="s", state=True)}</div>')
        photo = f'<div class="des-ab" style="left:9%;top:8%;width:78%;height:82%;background:linear-gradient({rng.randint(100, 170)}deg,{d.color()},{d.color()} 55%,{d.color()})"></div>'
        marq = f'<div class="des-sel" style="left:{rng.randint(20, 40)}%;top:{rng.randint(20, 40)}%;width:{rng.randint(18, 34)}%;height:{rng.randint(18, 30)}%;border-style:dashed;border-color:#fff"></div>'
        canvas = f'<div class="col f1"><div class="des-rh"></div><div class="row str f1"><div class="des-rv"></div><div class="des-cv f1">{photo}{marq}</div></div></div>'
        body = f'<div class="col f1">{opts}<div class="row str f1">{pal}<div class="col f1">{dtabs}{canvas}</div>{right}</div>{status}</div>'
        menus = ["mb.file", "mb.edit", "mb.image", "mb.layer", "mb.text", "mb.select", "mb.filter", "mb.view", "mb.window", "mb.help"]
    return {"title": title, "body": body, "menus": menus, "url": "design.example.com/file/" + fname.lower().replace(" ", "-"),
            "app": rng.choice(["Studio", "Canvas", "Vectorly", "Pixelform"]), "css": CSS}


def _one_prop(ctx):
    """(label, value) for one numeric field from the split's property names not yet used on this screen."""
    left = getattr(ctx, "_des_props", None)
    if left is None:
        left = ctx._des_props = ctx.d.take("des.props", PROPS)
    rng = ctx.rng
    name = left.pop() if left else f"Value {rng.randint(2, 99)}"
    return name, rng.choice([str(rng.randint(0, 1440)), f"{rng.randint(1, 400)} px", f"{rng.randint(1, 100)}%", f"{rng.randint(0, 359)}°", str(rng.randint(0, 255))])


def _sbsel(ctx, cid, region):
    label = ctx.lab(cid)
    opts = OPTIONS[label]
    attr = ctx.reg("select", "dropdown", label, cid=cid, region=region, anchor="select")
    ctx.options[ctx.last] = list(opts)
    return f'<div class="si"{attr}><span class="fnt">{esc(label)}:</span><span>{esc(ctx.rng.choice(opts))}</span>{CHEV_D}</div>'
