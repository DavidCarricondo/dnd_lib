#!/usr/bin/env python3
"""D&D 5e SRD Library - Local offline application."""

import json
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static", template_folder="templates")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "2014"

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


def _load_category(slug):
    """Load all items from a category JSON file."""
    filename = CATEGORY_MAP.get(slug)
    if not filename:
        return None
    filepath = DATA_DIR / f"5e-SRD-{filename}.json"
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


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
    return send_from_directory("templates", "index.html")


@app.route("/api/categories")
def get_categories():
    """Return list of available categories."""
    cats = []
    for slug, display in CATEGORY_DISPLAY.items():
        cats.append({"slug": slug, "name": display})
    return jsonify(cats)


@app.route("/api/category/<slug>")
def get_category_items(slug):
    """Return all items in a category."""
    items = _load_category(slug)
    if items is None:
        return jsonify({"error": "Category not found"}), 404
    # Return lightweight list (index + name only)
    result = []
    for item in items:
        result.append({
            "index": item.get("index", ""),
            "name": item.get("name", item.get("full_name", "Unknown")),
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
    items = _load_category(slug)
    if items is None:
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

    # Sanitize name for index
    safe_index = _sanitize_index_name(name)
    custom_index = f"{safe_index}_custom"

    # Check for duplicates
    for existing in items:
        if existing.get("index") == custom_index:
            return jsonify({"error": f"Custom item '{custom_index}' already exists"}), 409

    # Set the index and name
    item_json["index"] = custom_index
    item_json["name"] = name
    item_json["_custom"] = True

    items.append(item_json)
    if not _save_category(slug, items):
        return jsonify({"error": "Failed to save"}), 500

    _invalidate_index()
    return jsonify({"success": True, "index": custom_index, "item": item_json})


@app.route("/api/custom/<slug>/<item_index>", methods=["PUT"])
def update_custom_item(slug, item_index):
    """Update an existing custom item in a category."""
    items = _load_category(slug)
    if items is None:
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

    item_pos = None
    for i, existing in enumerate(items):
        if existing.get("index") == item_index:
            item_pos = i
            break

    if item_pos is None:
        return jsonify({"error": "Item not found"}), 404
    if not _is_custom_item(items[item_pos]):
        return jsonify({"error": "Only custom items can be edited"}), 403

    safe_index = _sanitize_index_name(name)
    custom_index = f"{safe_index}_custom"

    # Check for duplicates, excluding the current item.
    for i, existing in enumerate(items):
        if i != item_pos and existing.get("index") == custom_index:
            return jsonify({"error": f"Custom item '{custom_index}' already exists"}), 409

    item_json["index"] = custom_index
    item_json["name"] = name
    item_json["_custom"] = True

    items[item_pos] = item_json
    if not _save_category(slug, items):
        return jsonify({"error": "Failed to save"}), 500

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
    items = _load_category(slug)
    if items is None:
        return jsonify({"error": "Category not found"}), 404

    item_pos = None
    for i, existing in enumerate(items):
        if existing.get("index") == item_index:
            item_pos = i
            break

    if item_pos is None:
        return jsonify({"error": "Item not found"}), 404
    if not _is_custom_item(items[item_pos]):
        return jsonify({"error": "Only custom items can be deleted"}), 403

    items.pop(item_pos)
    if not _save_category(slug, items):
        return jsonify({"error": "Failed to save"}), 500

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

    items = _load_category("characters")
    if items is None:
        items = []

    safe_index = _sanitize_index_name(name)
    custom_index = f"{safe_index}_custom"

    for existing in items:
        if existing.get("index") == custom_index:
            return jsonify({"error": f"Character '{name}' already exists"}), 409

    character = {
        "index": custom_index,
        "name": name,
        "hit_points": hp,
        "armor_class": ac,
        "_custom": True,
    }

    items.append(character)
    _save_category("characters", items)
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


if __name__ == "__main__":
    print("D&D 5e SRD Library")
    print(f"Data directory: {DATA_DIR}")
    print("Starting server at http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
