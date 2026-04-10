#!/usr/bin/env python3
"""
migrate_customs.py — one-time migration to move _custom items from SRD JSON
files into the gitignored data/custom_items.json store.

Run from the repo root:
    python3 scripts/migrate_customs.py

The script is idempotent: running it more than once will not duplicate items.
SRD files are cleaned of _custom entries in-place, but only when they contain
at least one such entry (no unnecessary file writes).
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "2014"
CUSTOM_ITEMS_FILE = REPO_ROOT / "data" / "custom_items.json"

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


def is_custom(item):
    idx = str(item.get("index", ""))
    return bool(item.get("_custom")) or idx.endswith("_custom")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    # Load existing custom store (or start fresh)
    if CUSTOM_ITEMS_FILE.exists():
        custom_store = load_json(CUSTOM_ITEMS_FILE)
        print(f"Loaded existing custom store: {CUSTOM_ITEMS_FILE}")
    else:
        custom_store = {}
        print("No existing custom store found — will create a new one.")

    total_migrated = 0

    for slug, filename in CATEGORY_MAP.items():
        srd_path = DATA_DIR / f"5e-SRD-{filename}.json"
        if not srd_path.exists():
            continue

        items = load_json(srd_path)
        srd_items = [i for i in items if not is_custom(i)]
        found_customs = [i for i in items if is_custom(i)]

        if not found_customs:
            continue

        # Merge into custom store, skipping duplicates
        existing_indices = {i.get("index") for i in custom_store.get(slug, [])}
        new_customs = [i for i in found_customs if i.get("index") not in existing_indices]

        if new_customs:
            custom_store.setdefault(slug, []).extend(new_customs)
            total_migrated += len(new_customs)
            print(f"  [{slug}] migrated {len(new_customs)} item(s): "
                  + ", ".join(i.get("index", "?") for i in new_customs))

        # Rewrite the SRD file without custom items
        save_json(srd_path, srd_items)
        print(f"  [{slug}] cleaned SRD file ({len(srd_items)} SRD items remain)")

    # Save updated custom store
    save_json(CUSTOM_ITEMS_FILE, custom_store)
    print(f"\nDone. Migrated {total_migrated} custom item(s) to {CUSTOM_ITEMS_FILE}")


if __name__ == "__main__":
    main()
