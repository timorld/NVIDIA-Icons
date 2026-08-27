"""
Regenerates taskpane.html from template.html + icons/*.svg.

Run this any time you add, remove, or edit SVG files in icons/, then
commit + push both icons/ and taskpane.html.

    python build.py
"""
import json
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(HERE, "icons")
TEMPLATE_PATH = os.path.join(HERE, "template.html")
OUTPUT_PATH = os.path.join(HERE, "taskpane.html")

# Rough keyword -> category buckets, checked in order against the icon name.
# Anything that matches nothing falls into "general".
CATEGORY_RULES = [
    ("ai-ml", ["ai-", "-ai", "machine-learning", "neural", "deep-learning", "llm", "genai", "gpt", "nim", "agent"]),
    ("robotics", ["robot", "humanoid", "drone", "autonomous"]),
    ("hardware", ["gpu", "cpu", "chip", "server", "rack", "soc", "nic", "ram", "motherboard", "dpu"]),
    ("networking", ["network", "wifi", "router", "switch", "5g", "telecom", "satellite", "bluetooth", "ethernet"]),
    ("security", ["security", "lock", "shield", "firewall", "surveillance", "cctv"]),
    ("healthcare", ["medical", "health", "hospital", "doctor", "surgery", "dna", "genom", "xray", "ekg"]),
    ("energy", ["energy", "solar", "wind", "power", "nuclear", "oil", "renewable"]),
    ("finance", ["finance", "money", "cost", "invest", "trading", "stock"]),
    ("automotive", ["car", "vehicle", "automotive", "truck", "suv", "tractor"]),
    ("science", ["science", "chemistry", "physics", "molecul", "quantum", "microscope", "lab-"]),
    ("cloud-data", ["cloud", "database", "data-", "-data", "storage", "disk"]),
    ("education", ["school", "university", "education", "book", "graduation", "learning"]),
    ("devices", ["laptop", "phone", "tablet", "watch", "headset", "mouse", "webcam", "monitor", "display", "tv"]),
    ("people", ["person", "people", "team", "user", "profile", "hand", "handshake"]),
    ("buildings", ["building", "office", "factory", "city", "farm", "house"]),
]


def guess_category(name):
    for category, keywords in CATEGORY_RULES:
        if any(k in name for k in keywords):
            return category
    return "general"


def display_name(name):
    n = name
    if n.startswith("m48-"):
        n = n[4:]
    words = n.split("-")
    return " ".join(w.upper() if w in ("ai", "vr", "ar", "cpu", "gpu", "5g", "nic", "soc", "rag") else w.capitalize()
                     for w in words)


def find_svgs():
    """Yields (relative_subfolder_or_None, filename, full_path), sorted for
    deterministic output. Files directly in icons/ have subfolder=None;
    files in icons/<subfolder>/... use the top-level subfolder name."""
    results = []
    for entry in sorted(os.listdir(ICONS_DIR)):
        full = os.path.join(ICONS_DIR, entry)
        if os.path.isdir(full):
            for root, _, files in os.walk(full):
                for fn in sorted(files):
                    if fn.lower().endswith(".svg"):
                        results.append((entry, fn, os.path.join(root, fn)))
        elif entry.lower().endswith(".svg"):
            results.append((None, entry, full))
    return results


def polygon_to_path_d(points):
    # "points" is a flat list of numbers (space and/or comma separated),
    # taken two at a time as (x, y) pairs.
    nums = re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", points)
    coords = [f"{nums[i]},{nums[i + 1]}" for i in range(0, len(nums) - 1, 2)]
    if not coords:
        return ""
    return "M " + " L ".join(coords) + " Z"


def get_attr(attrs, name, default=0.0):
    v = attrs.get(name)
    try:
        return float(v) if v is not None else default
    except ValueError:
        return default


def rect_to_path_d(attrs):
    # Corner rounding (rx/ry) is ignored — not used by this icon set, and a
    # sharp-cornered rect is a harmless approximation if one shows up.
    x, y = get_attr(attrs, "x"), get_attr(attrs, "y")
    w, h = get_attr(attrs, "width"), get_attr(attrs, "height")
    if w <= 0 or h <= 0:
        return ""
    return f"M {x},{y} H {x + w} V {y + h} H {x} Z"


def circle_to_path_d(attrs):
    cx, cy, r = get_attr(attrs, "cx"), get_attr(attrs, "cy"), get_attr(attrs, "r")
    if r <= 0:
        return ""
    return (f"M {cx - r},{cy} A {r},{r} 0 1,0 {cx + r},{cy} "
            f"A {r},{r} 0 1,0 {cx - r},{cy} Z")


def ellipse_to_path_d(attrs):
    cx, cy = get_attr(attrs, "cx"), get_attr(attrs, "cy")
    rx, ry = get_attr(attrs, "rx"), get_attr(attrs, "ry")
    if rx <= 0 or ry <= 0:
        return ""
    return (f"M {cx - rx},{cy} A {rx},{ry} 0 1,0 {cx + rx},{cy} "
            f"A {rx},{ry} 0 1,0 {cx - rx},{cy} Z")


def parse_css_classes(svg_text):
    """Maps a CSS class name (from a <style> block, e.g. '.cls-5 { opacity: 0; }')
    to its declared properties, so hidden helper shapes can be recognized."""
    classes = {}
    style_match = re.search(r"<style[^>]*>(.*?)</style>", svg_text, re.S)
    if not style_match:
        return classes
    for rule in re.finditer(r"\.([\w-]+)\s*\{([^}]*)\}", style_match.group(1)):
        cls_name, body = rule.group(1), rule.group(2)
        props = {}
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            k, v = decl.split(":", 1)
            props[k.strip()] = v.strip()
        classes[cls_name] = props
    return classes


def props_are_hidden(props):
    if not props:
        return False
    return (props.get("opacity", "").strip() == "0"
            or props.get("display", "").strip() == "none"
            or props.get("visibility", "").strip() == "hidden")


def element_is_hidden(el, class_styles):
    """True if this element's own class/style (not ancestors) hides it."""
    inline = {}
    for decl in el.get("style", "").split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            inline[k.strip()] = v.strip()
    if props_are_hidden(inline):
        return True
    for cls in el.get("class", "").split():
        if props_are_hidden(class_styles.get(cls)):
            return True
    return False


def local_tag(tag):
    return tag.rsplit("}", 1)[-1]


def extract_shapes(svg_text):
    """Walks the real SVG DOM (not a flat regex scan) so that shapes hidden
    via an ancestor's opacity:0/display:none/visibility:hidden — a common
    pattern for leftover artboard/helper rects in these exports — are
    correctly excluded, and shapes inside <defs>/<clipPath> (never directly
    rendered) are too. Returns a list of path 'd' strings."""
    class_styles = parse_css_classes(svg_text)
    root = ET.fromstring(svg_text)
    d_parts = []

    def walk(el, hidden):
        tag = local_tag(el.tag)
        if tag in ("defs", "clipPath"):
            return  # never rendered directly
        hidden = hidden or element_is_hidden(el, class_styles)
        if not hidden:
            if tag == "path" and el.get("d"):
                d_parts.append(el.get("d"))
            elif tag in ("polygon", "polyline") and el.get("points"):
                d = polygon_to_path_d(el.get("points"))
                if d:
                    d_parts.append(d)
            elif tag == "rect":
                d = rect_to_path_d(el.attrib)
                if d:
                    d_parts.append(d)
            elif tag == "circle":
                d = circle_to_path_d(el.attrib)
                if d:
                    d_parts.append(d)
            elif tag == "ellipse":
                d = ellipse_to_path_d(el.attrib)
                if d:
                    d_parts.append(d)
        for child in el:
            walk(child, hidden)

    walk(root, False)
    return d_parts


def load_icons():
    entries = []
    svg_paths = {}
    for idx, (subfolder, fn, full_path) in enumerate(find_svgs()):
        name = os.path.splitext(fn)[0]
        with open(full_path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        try:
            d_parts = extract_shapes(text)
        except ET.ParseError as e:
            print(f"  WARNING: {fn} is not well-formed XML ({e}), skipping")
            continue
        d = " ".join(d_parts)
        if not d:
            print(f"  WARNING: no visible shapes found in {fn}, skipping")
            continue
        key = f"p{idx}"
        svg_paths[key] = d
        # Icons placed in a subfolder (e.g. icons/custom/) get that folder's
        # name as their category, so they show up as their own filter in the
        # picker instead of being mixed into the keyword-guessed buckets.
        category = subfolder.lower().replace(" ", "-") if subfolder else guess_category(name)
        entries.append({
            "name": name,
            "displayName": display_name(name),
            "category": category,
            "svgPathKey": key,
        })
    return entries, svg_paths


def main():
    icons, svg_paths = load_icons()
    print(f"Loaded {len(icons)} icons from {ICONS_DIR}")

    template = open(TEMPLATE_PATH, encoding="utf-8").read()
    m_icons = re.search(r"const icons = (\[.*?\]);\n", template, re.S)
    m_paths = re.search(r"const svgPaths = (\{.*?\});\n", template, re.S)
    if not m_icons or not m_paths:
        raise SystemExit("Could not find 'const icons =' / 'const svgPaths =' in template.html")

    icons_json = json.dumps(icons, separators=(",", ":"))
    paths_json = json.dumps(svg_paths, separators=(",", ":"))

    out = (
        template[: m_icons.start(1)]
        + icons_json
        + template[m_icons.end(1): m_paths.start(1)]
        + paths_json
        + template[m_paths.end(1):]
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(out)

    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
