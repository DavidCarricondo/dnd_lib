#!/usr/bin/env python3
"""D&D 5e SRD Library - Local offline application."""

import json
import re
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory


def get_base_path() -> Path:
    """Return project root in dev mode, or PyInstaller extraction dir when frozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # dev: src/dnd_lib/app.py -> three levels up = project root
    return Path(__file__).resolve().parent.parent.parent


def get_asset_path(*parts: str) -> Path:
    """Return path to a bundled asset (static/, templates/) relative to this file."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).joinpath(*parts)
    return Path(__file__).resolve().parent.joinpath(*parts)

_asset_root = get_asset_path()
app = Flask(
    __name__,
    static_folder=str(_asset_root / "static"),
    template_folder=str(_asset_root / "templates"),
)

DATA_DIR = get_base_path() / "data" / "2014"

# Custom items must live in a writable user-data directory, not inside the
# (potentially read-only) bundle.
try:
    from platformdirs import user_data_dir
    _user_data = Path(user_data_dir("dnd_lib", "dnd_lib"))
except ImportError:
    _user_data = Path.home() / ".dnd_lib"

CUSTOM_ITEMS_FILE = _user_data / "custom_items.json"

# Category mapping: URL slug -> filename (without 5e-SRD- prefix and .json suffix)
CATEGORY_MAP = {
    "ability-scores": "Ability-Scores",
    "alignments": "Alignments",
    "backgrounds": "Backgrounds",
    "classes": "Classes",
    "conditions": "Conditions",
    "damage-types": "Damage-Types",
    "equipment-categories": "Equipment-Categories",
    "equipment": "Equipment",
    "feats": "Feats",
    "features": "Features",
    "languages": "Languages",
    "levels": "Levels",
    "magic-items": "Magic-Items",
    "magic-schools": "Magic-Schools",
    "monsters": "Monsters",
    "proficiencies": "Proficiencies",
    "races": "Races",
    "rule-sections": "Rule-Sections",
    "rules": "Rules",
    "skills": "Skills",
    "spells": "Spells",
    "subclasses": "Subclasses",
    "subraces": "Subraces",
    "traits": "Traits",
    "weapon-properties": "Weapon-Properties",
    "characters": "Characters",
}

# Display names for categories
CATEGORY_DISPLAY = {
    "ability-scores": "Ability Scores",
    "alignments": "Alignments",
    "backgrounds": "Backgrounds",
    "classes": "Classes",
    "conditions": "Conditions",
    "damage-types": "Damage Types",
    "equipment-categories": "Equipment Categories",
    "equipment": "Equipment",
    "feats": "Feats",
    "features": "Features",
    "languages": "Languages",
    "levels": "Levels",
    "magic-items": "Magic Items",
    "magic-schools": "Magic Schools",
    "monsters": "Monsters",
    "proficiencies": "Proficiencies",
    "races": "Races",
    "rule-sections": "Rule Sections",
    "rules": "Rules",
    "skills": "Skills",
    "spells": "Spells",
    "subclasses": "Subclasses",
    "subraces": "Subraces",
    "traits": "Traits",
    "weapon-properties": "Weapon Properties",
    "characters": "Characters",
}


def _sanitize_index_name(name):
    """Normalize user-provided names for item indexes."""
    safe_index = re.sub(r"[^a-z0-9-]", "-", name.lower().strip())
    return re.sub(r"-+", "-", safe_index).strip("-")


def _is_custom_item(item):
    """Return True when an item is user-created/customized."""
    idx = str(item.get("index", ""))
    return bool(item.get("_custom")) or idx.endswith("_custom")


def _load_custom_items():
    """Load the custom items store. Returns dict keyed by category slug."""
    if CUSTOM_ITEMS_FILE.exists():
        with open(CUSTOM_ITEMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_custom_items(custom_data):
    """Persist the custom items store to the gitignored custom_items.json file."""
    CUSTOM_ITEMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CUSTOM_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(custom_data, f, indent=2, ensure_ascii=False)


def _migrate_legacy_customs():
    """One-time silent migration: move _custom items from SRD files into
    custom_items.json.  Safe to call on every startup — no-ops when there is
    nothing to migrate."""
    custom_data = _load_custom_items()
    migrated = False
    for slug, filename in CATEGORY_MAP.items():
        filepath = DATA_DIR / f"5e-SRD-{filename}.json"
        if not filepath.exists():
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            items = json.load(f)
        found = [i for i in items if _is_custom_item(i)]
        if not found:
            continue
        # Merge into custom store (skip duplicates)
        existing_indices = {i.get("index") for i in custom_data.get(slug, [])}
        new_items = [i for i in found if i.get("index") not in existing_indices]
        if new_items:
            custom_data.setdefault(slug, []).extend(new_items)
            migrated = True
        # Rewrite SRD file without the custom entries
        clean = [i for i in items if not _is_custom_item(i)]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2, ensure_ascii=False)
    if migrated:
        _save_custom_items(custom_data)


# Run once at import time so any legacy custom items are transparently moved.
# Skip when frozen: SRD files in the bundle are reset on every run so there is
# nothing to migrate and the write would be lost anyway.
if not (getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")):
    _migrate_legacy_customs()


def _load_category(slug):
    """Load all items from a category JSON file, merged with custom items."""
    filename = CATEGORY_MAP.get(slug)
    if not filename:
        return None
    # Load SRD items, stripping any legacy _custom entries saved there previously
    filepath = DATA_DIR / f"5e-SRD-{filename}.json"
    srd_items = []
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        srd_items = [item for item in raw if not _is_custom_item(item)]
    # Append custom items from the gitignored custom store
    custom_data = _load_custom_items()
    custom_items = custom_data.get(slug, [])
    return srd_items + custom_items


def _save_category(slug, data):
    """Save items back to a category JSON file."""
    filename = CATEGORY_MAP.get(slug)
    if not filename:
        return False
    filepath = DATA_DIR / f"5e-SRD-{filename}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True


# Build a reverse lookup: index -> (category_slug, item) for cross-references
def _build_index():
    """Build a global index of all items for cross-reference lookup."""
    index = {}
    for slug in CATEGORY_MAP:
        items = _load_category(slug)
        if items:
            for item in items:
                if "index" in item:
                    index[item["index"]] = {"category": slug, "name": item.get("name", item["index"])}
    return index


GLOBAL_INDEX = None


def _get_global_index():
    global GLOBAL_INDEX
    if GLOBAL_INDEX is None:
        GLOBAL_INDEX = _build_index()
    return GLOBAL_INDEX


def _invalidate_index():
    global GLOBAL_INDEX
    GLOBAL_INDEX = None


@app.route("/")
def index_page():
    # Use the absolute template_folder set at init time so this works both in
    # dev and when running from a PyInstaller bundle.
    return send_from_directory(app.template_folder, "index.html")


@app.route("/api/categories")
def get_categories():
    """Return list of available categories."""
    cats = []
    for slug, display in CATEGORY_DISPLAY.items():
        cats.append({"slug": slug, "name": display})
    return jsonify(cats)


@app.route("/api/category/<slug>/filters")
def get_category_filters(slug):
    """Return available filter options for a category."""
    items = _load_category(slug)
    if items is None:
        return jsonify({"error": "Category not found"}), 404

    filters = {}

    if slug == "spells":
        levels = sorted({item.get("level", 0) for item in items})
        filters["level"] = [
            {"value": lv, "label": "Cantrip" if lv == 0 else f"Level {lv}"}
            for lv in levels
        ]
        classes = set()
        for item in items:
            for cls in item.get("classes", []):
                classes.add(cls.get("name", ""))
        filters["class"] = [
            {"value": c, "label": c} for c in sorted(classes) if c
        ]

    elif slug == "monsters":
        crs = sorted({item.get("challenge_rating", 0) for item in items})
        filters["challenge_rating"] = [
            {"value": cr, "label": str(cr)} for cr in crs
        ]
        types = sorted({item.get("type", "").capitalize() for item in items if item.get("type")})
        filters["type"] = [
            {"value": t, "label": t} for t in types if t
        ]
        sizes = sorted({item.get("size", "") for item in items if item.get("size")})
        filters["size"] = [
            {"value": s, "label": s} for s in sizes if s
        ]

    return jsonify(filters)


@app.route("/api/category/<slug>")
def get_category_items(slug):
    """Return all items in a category."""
    items = _load_category(slug)
    if items is None:
        return jsonify({"error": "Category not found"}), 404

    # Apply filters based on query parameters
    if slug == "spells":
        level_filter = request.args.get("level")
        level_cmp = request.args.get("level_cmp", "eq")
        class_filter = request.args.get("class")
        if level_filter is not None and level_filter != "":
            try:
                level_val = int(level_filter)
                if level_cmp == "gt":
                    items = [i for i in items if i.get("level", 0) > level_val]
                elif level_cmp == "lt":
                    items = [i for i in items if i.get("level", 0) < level_val]
                else:
                    items = [i for i in items if i.get("level") == level_val]
            except ValueError:
                pass
        if class_filter:
            items = [
                i for i in items
                if any(c.get("name", "").lower() == class_filter.lower() for c in i.get("classes", []))
            ]
    elif slug == "monsters":
        cr_filter = request.args.get("challenge_rating")
        cr_cmp = request.args.get("cr_cmp", "eq")
        type_filter = request.args.get("type")
        size_filter = request.args.get("size")
        size_cmp = request.args.get("size_cmp", "eq")
        size_order = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
        if cr_filter is not None and cr_filter != "":
            try:
                cr_val = float(cr_filter)
                if cr_cmp == "gt":
                    items = [i for i in items if i.get("challenge_rating", 0) > cr_val]
                elif cr_cmp == "lt":
                    items = [i for i in items if i.get("challenge_rating", 0) < cr_val]
                else:
                    items = [i for i in items if i.get("challenge_rating") == cr_val]
            except ValueError:
                pass
        if type_filter:
            items = [i for i in items if i.get("type", "").lower() == type_filter.lower()]
        if size_filter:
            try:
                sf_idx = size_order.index(size_filter)
            except ValueError:
                sf_idx = -1
            if sf_idx >= 0 and size_cmp == "gt":
                items = [i for i in items if i.get("size", "") in size_order[sf_idx + 1:]]
            elif sf_idx >= 0 and size_cmp == "lt":
                items = [i for i in items if i.get("size", "") in size_order[:sf_idx]]
            else:
                items = [i for i in items if i.get("size", "").lower() == size_filter.lower()]

    # Return lightweight list (index + name only)
    result = []
    for item in items:
        # Special handling for levels: use "ClassName - Level X"
        if slug == "levels":
            class_name = item.get("class", {}).get("name", "Unknown")
            level = item.get("level", "?")
            display_name = f"{class_name} - Level {level}"
        else:
            display_name = item.get("name", item.get("full_name", "Unknown"))
        
        result.append({
            "index": item.get("index", ""),
            "name": display_name,
            "category": slug,
        })
    return jsonify(result)


@app.route("/api/item/<slug>/<item_index>")
def get_item(slug, item_index):
    """Return full item data."""
    items = _load_category(slug)
    if items is None:
        return jsonify({"error": "Category not found"}), 404
    for item in items:
        if item.get("index") == item_index:
            return jsonify({"item": item, "category": slug})
    return jsonify({"error": "Item not found"}), 404


@app.route("/api/resolve/<item_index>")
def resolve_item(item_index):
    """Resolve an item index to its category for cross-reference navigation."""
    gidx = _get_global_index()
    if item_index in gidx:
        return jsonify(gidx[item_index])
    return jsonify({"error": "Item not found"}), 404


@app.route("/api/search")
def search_items():
    """Search across all categories."""
    query = request.args.get("q", "").strip().lower()
    category_filter = request.args.get("category", "").strip()
    if not query:
        return jsonify([])

    results = []
    slugs = [category_filter] if category_filter and category_filter in CATEGORY_MAP else CATEGORY_MAP.keys()

    for slug in slugs:
        items = _load_category(slug)
        if not items:
            continue
        for item in items:
            name = item.get("name", item.get("full_name", "")).lower()
            idx = item.get("index", "").lower()
            desc_parts = item.get("desc", [])
            desc_text = " ".join(desc_parts).lower() if isinstance(desc_parts, list) else str(desc_parts).lower()

            if query in name or query in idx or query in desc_text:
                results.append({
                    "index": item.get("index", ""),
                    "name": item.get("name", item.get("full_name", "Unknown")),
                    "category": slug,
                    "category_name": CATEGORY_DISPLAY.get(slug, slug),
                })
        if len(results) > 200:
            break

    # Sort: name matches first, then description matches
    results.sort(key=lambda r: (0 if query in r["name"].lower() else 1, r["name"].lower()))
    return jsonify(results[:100])


@app.route("/api/custom/<slug>", methods=["POST"])
def add_custom_item(slug):
    """Add a custom item to a category."""
    if slug not in CATEGORY_MAP:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name", "").strip()
    item_json = data.get("item")

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not item_json or not isinstance(item_json, dict):
        return jsonify({"error": "Valid item JSON object is required"}), 400

    safe_index = _sanitize_index_name(name)
    custom_index = f"{safe_index}_custom"

    custom_data = _load_custom_items()
    slug_customs = custom_data.get(slug, [])

    # Check for duplicates
    for existing in slug_customs:
        if existing.get("index") == custom_index:
            return jsonify({"error": f"Custom item '{custom_index}' already exists"}), 409

    item_json["index"] = custom_index
    item_json["name"] = name
    item_json["_custom"] = True

    slug_customs.append(item_json)
    custom_data[slug] = slug_customs
    _save_custom_items(custom_data)

    _invalidate_index()
    return jsonify({"success": True, "index": custom_index, "item": item_json})


@app.route("/api/custom/<slug>/<item_index>", methods=["PUT"])
def update_custom_item(slug, item_index):
    """Update an existing custom item in a category."""
    if slug not in CATEGORY_MAP:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name", "").strip()
    item_json = data.get("item")

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not item_json or not isinstance(item_json, dict):
        return jsonify({"error": "Valid item JSON object is required"}), 400

    custom_data = _load_custom_items()
    slug_customs = custom_data.get(slug, [])

    item_pos = None
    for i, existing in enumerate(slug_customs):
        if existing.get("index") == item_index:
            item_pos = i
            break

    if item_pos is None:
        return jsonify({"error": "Item not found"}), 404

    safe_index = _sanitize_index_name(name)
    custom_index = f"{safe_index}_custom"

    # Check for duplicates, excluding the current item.
    for i, existing in enumerate(slug_customs):
        if i != item_pos and existing.get("index") == custom_index:
            return jsonify({"error": f"Custom item '{custom_index}' already exists"}), 409

    item_json["index"] = custom_index
    item_json["name"] = name
    item_json["_custom"] = True

    slug_customs[item_pos] = item_json
    custom_data[slug] = slug_customs
    _save_custom_items(custom_data)

    _invalidate_index()
    return jsonify({
        "success": True,
        "index": custom_index,
        "old_index": item_index,
        "item": item_json,
    })


@app.route("/api/custom/<slug>/<item_index>", methods=["DELETE"])
def delete_custom_item(slug, item_index):
    """Delete an existing custom item from a category."""
    if slug not in CATEGORY_MAP:
        return jsonify({"error": "Category not found"}), 404

    custom_data = _load_custom_items()
    slug_customs = custom_data.get(slug, [])

    item_pos = None
    for i, existing in enumerate(slug_customs):
        if existing.get("index") == item_index:
            item_pos = i
            break

    if item_pos is None:
        return jsonify({"error": "Item not found"}), 404

    slug_customs.pop(item_pos)
    custom_data[slug] = slug_customs
    _save_custom_items(custom_data)

    _invalidate_index()
    return jsonify({"success": True, "index": item_index})


@app.route("/api/character", methods=["POST"])
def add_character():
    """Add a character with name, HP, and AC (simplified form, no raw JSON)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name", "").strip()
    hp = data.get("hp")
    ac = data.get("ac")

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if hp is None or not isinstance(hp, (int, float)) or hp < 0:
        return jsonify({"error": "HP must be a non-negative number"}), 400
    if ac is None or not isinstance(ac, (int, float)) or ac < 0:
        return jsonify({"error": "AC must be a non-negative number"}), 400

    hp = int(hp)
    ac = int(ac)

    custom_data = _load_custom_items()
    chars = custom_data.get("characters", [])

    safe_index = _sanitize_index_name(name)
    custom_index = f"{safe_index}_custom"

    for existing in chars:
        if existing.get("index") == custom_index:
            return jsonify({"error": f"Character '{name}' already exists"}), 409

    character = {
        "index": custom_index,
        "name": name,
        "hit_points": hp,
        "armor_class": ac,
        "_custom": True,
    }

    chars.append(character)
    custom_data["characters"] = chars
    _save_custom_items(custom_data)
    _invalidate_index()
    return jsonify({"success": True, "index": custom_index, "item": character})


@app.route("/api/initiative-search")
def initiative_search():
    """Search characters and monsters for adding to initiative tracker."""
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify([])

    results = []
    # Search characters
    chars = _load_category("characters") or []
    for c in chars:
        if query in c.get("name", "").lower():
            results.append({
                "index": c["index"],
                "name": c["name"],
                "type": "character",
                "hp": c.get("hit_points", 0),
                "ac": c.get("armor_class", 0),
            })

    # Search monsters
    monsters = _load_category("monsters") or []
    for m in monsters:
        if query in m.get("name", "").lower() or query in m.get("index", "").lower():
            ac_val = 0
            if m.get("armor_class"):
                ac_val = m["armor_class"][0].get("value", 0) if isinstance(m["armor_class"], list) else m["armor_class"]
            results.append({
                "index": m["index"],
                "name": m["name"],
                "type": "monster",
                "hp": m.get("hit_points", 0),
                "ac": ac_val,
            })

    results.sort(key=lambda r: r["name"].lower())
    return jsonify(results[:50])


@app.route("/api/global-index")
def get_global_index():
    """Return the full global index for client-side cross-reference resolution."""
    return jsonify(_get_global_index())


def run_dev(host: str = "127.0.0.1", port: int = 5000) -> None:
    """Start the Flask development server (debug mode)."""
    app.run(host=host, port=port, debug=True)


def run_production(host: str = "127.0.0.1", port: int = 5000, threads: int = 4) -> None:
    """Start the Waitress production WSGI server."""
    from waitress import serve

    url = f"http://{host}:{port}"
    threading.Timer(1.5, webbrowser.open, args=[url]).start()
    serve(app, host=host, port=port, threads=threads)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="D&D 5e SRD Library")
    parser.add_argument("--dev", action="store_true", help="Run Flask dev server (debug mode)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    args = parser.parse_args()

    print("D&D 5e SRD Library")
    print(f"Data directory: {DATA_DIR}")
    print(f"Custom items: {CUSTOM_ITEMS_FILE}")
    print(f"Starting server at http://{args.host}:{args.port}")

    if args.dev:
        run_dev(host=args.host, port=args.port)
    else:
        run_production(host=args.host, port=args.port)
