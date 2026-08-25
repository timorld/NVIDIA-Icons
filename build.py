"""
Regenerates taskpane.html from template.html + icons/*.svg.

Run this any time you add, remove, or edit SVG files in icons/, then
commit + push both icons/ and taskpane.html.

    python build.py
"""
import json
import os
import re

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


def load_icons():
    entries = []
    svg_paths = {}
    for idx, (subfolder, fn, full_path) in enumerate(find_svgs()):
        name = os.path.splitext(fn)[0]
        with open(full_path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        paths = re.findall(r'<path[^>]*\bd="([^"]+)"', text)
        polygons = re.findall(r'<(?:polygon|polyline)[^>]*\bpoints="([^"]+)"', text)
        d = " ".join(paths + [polygon_to_path_d(p) for p in polygons])
        if not d:
            print(f"  WARNING: no <path d=...> found in {fn}, skipping")
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
