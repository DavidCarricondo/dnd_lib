"""Convert 5etools-format JSON (monsters, spells, equipment, feats) to the SRD format used by this app."""

import re

# ===== Lookup tables =====

SIZE_MAP = {
    "T": "Tiny",
    "S": "Small",
    "M": "Medium",
    "L": "Large",
    "H": "Huge",
    "G": "Gargantuan",
}

ALIGNMENT_MAP = {
    "L": "lawful",
    "N": "neutral",
    "C": "chaotic",
    "G": "good",
    "E": "evil",
    "A": "any alignment",
    "U": "unaligned",
}

ABILITY_FULL = {
    "str": "strength",
    "dex": "dexterity",
    "con": "constitution",
    "int": "intelligence",
    "wis": "wisdom",
    "cha": "charisma",
}

# XP by CR (2014 rules)
CR_XP = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100,
    "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800,
    "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900,
    "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
    "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
    "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000,
    "26": 90000, "27": 105000, "28": 120000, "29": 135000, "30": 155000,
}

# Proficiency bonus by CR
CR_PROF = {
    "0": 2, "1/8": 2, "1/4": 2, "1/2": 2,
    "1": 2, "2": 2, "3": 2, "4": 2,
    "5": 3, "6": 3, "7": 3, "8": 3,
    "9": 4, "10": 4, "11": 4, "12": 4,
    "13": 5, "14": 5, "15": 5, "16": 5,
    "17": 6, "18": 6, "19": 6, "20": 6,
    "21": 7, "22": 7, "23": 7, "24": 7,
    "25": 8, "26": 8, "27": 8, "28": 8,
    "29": 9, "30": 9,
}


def _cr_to_number(cr_str):
    """Convert a CR string like '1/4' to a numeric value."""
    if "/" in cr_str:
        num, den = cr_str.split("/")
        return int(num) / int(den)
    val = float(cr_str)
    return int(val) if val == int(val) else val


# ===== 5etools text tag stripping =====

def _strip_5etools_tags(text):
    """Remove 5etools {@tag content} markup, keeping readable text."""
    # {@atk mw} -> "Melee Weapon Attack:"
    # {@atk rw} -> "Ranged Weapon Attack:"
    # {@atk mw,rw} -> "Melee or Ranged Weapon Attack:"
    # {@atkr m} -> "Melee Attack Roll:"
    def _atk_replace(m):
        code = m.group(1).strip()
        if code == "mw":
            return "Melee Weapon Attack:"
        elif code == "rw":
            return "Ranged Weapon Attack:"
        elif code in ("mw,rw", "rw,mw"):
            return "Melee or Ranged Weapon Attack:"
        return ""

    text = re.sub(r"\{@atkr?\s+([^}]+)\}", _atk_replace, text)

    # {@hit N} -> "+N"
    text = re.sub(r"\{@hit\s+(\d+)\}", r"+\1", text)

    # {@h} -> "Hit: " (5etools hit marker)
    text = re.sub(r"\{@h\}", "Hit: ", text)

    # {@damage XdY+Z} -> "XdY+Z" or just the dice expression
    text = re.sub(r"\{@damage\s+([^}]+)\}", r"\1", text)

    # {@dice XdY} -> "XdY"
    text = re.sub(r"\{@dice\s+([^}]+)\}", r"\1", text)

    # {@dc N} -> "DC N"
    text = re.sub(r"\{@dc\s+(\d+)\}", r"DC \1", text)

    # {@recharge N} -> "(Recharge N-6)" or "(Recharge N)"
    def _recharge(m):
        val = m.group(1)
        if val == "6":
            return "(Recharge 6)"
        return f"(Recharge {val}\u20136)"

    text = re.sub(r"\{@recharge\s+(\d+)\}", _recharge, text)

    # {@condition X|source} -> "X"
    text = re.sub(r"\{@condition\s+([^|}]+)(?:\|[^}]*)?\}", r"\1", text)

    # {@spell X|source} -> "X"
    text = re.sub(r"\{@spell\s+([^|}]+)(?:\|[^}]*)?\}", r"\1", text)

    # {@creature X|source} -> "X"
    text = re.sub(r"\{@creature\s+([^|}]+)(?:\|[^}]*)?\}", r"\1", text)

    # {@item X|source} -> "X"
    text = re.sub(r"\{@item\s+([^|}]+)(?:\|[^}]*)?\}", r"\1", text)

    # {@action X} -> "X"
    text = re.sub(r"\{@action\s+([^|}]+)(?:\|[^}]*)?\}", r"\1", text)

    # {@variantrule X|source|display} -> display or X
    def _variantrule(m):
        parts = m.group(1).split("|")
        # If there's a display text (third pipe-separated value), use it
        if len(parts) >= 3 and parts[2]:
            return parts[2]
        return parts[0]

    text = re.sub(r"\{@variantrule\s+([^}]+)\}", _variantrule, text)

    # {@chance N} -> "N percent"
    text = re.sub(r"\{@chance\s+(\d+)\}", r"\1 percent", text)

    # {@actSave ability} -> "Saving Throw: ABILITY"
    def _act_save(m):
        ab = m.group(1).strip().capitalize()
        return f"Saving Throw: {ab}"

    text = re.sub(r"\{@actSave\s+([^}]+)\}", _act_save, text)

    # {@actSaveFail} -> "Failure:"
    text = re.sub(r"\{@actSaveFail\}", "Failure:", text)

    # {@actSaveSuccess} -> "Success:"
    text = re.sub(r"\{@actSaveSuccess\}", "Success:", text)

    # {@actSaveSuccessOrFail} -> ""
    text = re.sub(r"\{@actSaveSuccessOrFail\}", "", text)

    # Generic fallback: {@tag content} -> content (first pipe segment)
    text = re.sub(r"\{@\w+\s+([^|}]+)(?:\|[^}]*)?\}", r"\1", text)

    return text.strip()


def _entries_to_desc(entries):
    """Convert 5etools entries array to a single description string."""
    parts = []
    for entry in entries:
        if isinstance(entry, str):
            parts.append(_strip_5etools_tags(entry))
        elif isinstance(entry, dict):
            # Nested entries block
            if "entries" in entry:
                sub = _entries_to_desc(entry["entries"])
                name = entry.get("name", "")
                if name:
                    parts.append(f"{name}. {sub}")
                else:
                    parts.append(sub)
    return " ".join(parts)


# ===== Conversion helpers =====

def _convert_size(size_arr):
    """Convert 5etools size array to SRD size string."""
    if not size_arr:
        return "Medium"
    return SIZE_MAP.get(size_arr[0], "Medium")


def _convert_type(type_field):
    """Convert 5etools type to SRD type string and optional subtype."""
    if isinstance(type_field, str):
        return type_field, ""
    if isinstance(type_field, dict):
        main_type = type_field.get("type", "")
        tags = type_field.get("tags", [])
        subtype = ", ".join(tags) if tags else ""
        return main_type, subtype
    return "", ""


def _convert_alignment(align_arr):
    """Convert 5etools alignment codes to SRD alignment string."""
    if not align_arr:
        return "unaligned"
    # Single "A" means any alignment
    if align_arr == ["A"]:
        return "any alignment"
    if align_arr == ["U"]:
        return "unaligned"
    parts = [ALIGNMENT_MAP.get(code, code) for code in align_arr]
    return " ".join(parts)


def _convert_ac(ac_arr):
    """Convert 5etools ac array to SRD armor_class array."""
    result = []
    for entry in ac_arr:
        if isinstance(entry, int):
            result.append({"type": "dex", "value": entry})
        elif isinstance(entry, dict):
            ac_val = entry.get("ac", 0)
            from_list = entry.get("from", [])
            condition = entry.get("condition", "")

            if condition:
                # Conditional AC (e.g., "with mage armor")
                cond_text = _strip_5etools_tags(condition)
                # Try to detect spell-based AC
                if "mage armor" in cond_text.lower():
                    result.append({
                        "type": "spell",
                        "value": ac_val,
                        "spell": {
                            "index": "mage-armor",
                            "name": "Mage Armor",
                            "url": "/api/2014/spells/mage-armor",
                        },
                    })
                else:
                    result.append({"type": "condition", "value": ac_val})
            elif from_list:
                # Determine type from source
                from_text = " ".join(_strip_5etools_tags(f) for f in from_list).lower()
                if "natural armor" in from_text:
                    result.append({"type": "natural", "value": ac_val})
                else:
                    # Armor-based AC
                    armor_items = []
                    for f in from_list:
                        clean = _strip_5etools_tags(f)
                        slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
                        armor_items.append({
                            "index": slug,
                            "name": clean,
                            "url": f"/api/2014/equipment/{slug}",
                        })
                    result.append({"type": "armor", "value": ac_val, "armor": armor_items})
            else:
                result.append({"type": "dex", "value": ac_val})
    return result


def _convert_speed(speed_obj):
    """Convert 5etools speed (numeric values) to SRD speed (with ft. suffix)."""
    if not speed_obj:
        return {}
    result = {}
    for key, val in speed_obj.items():
        if isinstance(val, (int, float)):
            result[key] = f"{val} ft."
        elif isinstance(val, dict):
            # Some speeds have {number, condition} format
            num = val.get("number", 0)
            result[key] = f"{num} ft."
        else:
            result[key] = str(val)
    return result


def _convert_proficiencies(monster):
    """Build the SRD proficiencies array from 5etools save and skill objects."""
    profs = []
    # Saving throws
    saves = monster.get("save", {})
    for abbrev, bonus_str in saves.items():
        val = int(bonus_str.replace("+", ""))
        full_name = ABILITY_FULL.get(abbrev, abbrev).upper()[:3]
        profs.append({
            "value": val,
            "proficiency": {
                "index": f"saving-throw-{abbrev}",
                "name": f"Saving Throw: {full_name.upper()}",
                "url": f"/api/2014/proficiencies/saving-throw-{abbrev}",
            },
        })
    # Skills
    skills = monster.get("skill", {})
    for skill_name, bonus_str in skills.items():
        val = int(bonus_str.replace("+", ""))
        display_name = skill_name.replace("-", " ").title()
        slug = skill_name.lower().replace(" ", "-")
        profs.append({
            "value": val,
            "proficiency": {
                "index": f"skill-{slug}",
                "name": f"Skill: {display_name}",
                "url": f"/api/2014/proficiencies/skill-{slug}",
            },
        })
    return profs


def _convert_resistances(resist_arr):
    """Convert 5etools resist array (may contain objects) to SRD string list."""
    if not resist_arr:
        return []
    result = []
    for entry in resist_arr:
        if isinstance(entry, str):
            result.append(entry)
        elif isinstance(entry, dict):
            # Complex resistance: {resist: [...], note: "...", preNote: "..."}
            damages = entry.get("resist", [])
            note = entry.get("note", "")
            pre_note = entry.get("preNote", "")
            desc = ", ".join(damages)
            if pre_note:
                desc = f"{desc} from {pre_note} attacks"
            if note:
                desc = f"{desc} {note}"
            result.append(desc.strip())
        elif isinstance(entry, list):
            result.append(", ".join(entry))
    return result


def _convert_condition_immunities(cond_arr):
    """Convert 5etools conditionImmune string array to SRD condition objects."""
    if not cond_arr:
        return []
    result = []
    for cond in cond_arr:
        slug = cond.lower().replace(" ", "-")
        result.append({
            "index": slug,
            "name": cond.capitalize(),
            "url": f"/api/2014/conditions/{slug}",
        })
    return result


def _convert_senses(senses_arr, passive):
    """Convert 5etools senses array + passive to SRD senses object."""
    result = {}
    if senses_arr:
        for sense_str in senses_arr:
            # Parse strings like "darkvision 60 ft." or "Blindsight 60 ft."
            lower = sense_str.lower().strip()
            # Try to extract sense name and distance
            match = re.match(r"(\w[\w\s]*?)\s+(\d+\s*ft\.?)", lower)
            if match:
                sense_name = match.group(1).strip().replace(" ", "_")
                distance = match.group(2).strip()
                if not distance.endswith("."):
                    distance += "."
                result[sense_name] = distance
            else:
                # Just store as-is with a key
                key = re.sub(r"[^a-z_]", "_", lower)
                result[key] = sense_str
    result["passive_perception"] = passive if passive else 10
    return result


def _convert_cr(cr_field):
    """Convert 5etools cr (string or object) to numeric CR value and string."""
    if isinstance(cr_field, str):
        return cr_field, _cr_to_number(cr_field)
    elif isinstance(cr_field, dict):
        cr_str = cr_field.get("cr", "0")
        return cr_str, _cr_to_number(cr_str)
    return "0", 0


def _convert_spellcasting(spellcasting_arr):
    """Convert 5etools spellcasting to SRD special_ability with spellcasting."""
    if not spellcasting_arr:
        return []
    abilities = []
    for sc in spellcasting_arr:
        header = _entries_to_desc(sc.get("headerEntries", []))
        footer = _entries_to_desc(sc.get("footerEntries", []))

        # Build the full desc text
        desc_parts = [header] if header else []

        # At-will spells
        will_spells = sc.get("will", [])
        if will_spells:
            cleaned = [_strip_5etools_tags(s) for s in will_spells]
            desc_parts.append(f"- At will: {', '.join(cleaned)}")

        # Daily spells
        daily = sc.get("daily", {})
        for freq, spells in sorted(daily.items()):
            cleaned = [_strip_5etools_tags(s) for s in spells]
            if freq.endswith("e"):
                freq_num = freq[:-1]
                freq_label = f"{freq_num}/day each"
            else:
                freq_label = f"{freq}/day"
            desc_parts.append(f"- {freq_label}: {', '.join(cleaned)}")

        # Leveled spells
        spells_obj = sc.get("spells", {})
        if spells_obj:
            for level_str in sorted(spells_obj.keys(), key=int):
                level_data = spells_obj[level_str]
                spell_list = [_strip_5etools_tags(s) for s in level_data.get("spells", [])]
                slots = level_data.get("slots")
                if int(level_str) == 0:
                    desc_parts.append(f"- Cantrips (at will): {', '.join(spell_list)}")
                else:
                    slot_text = f"{slots} slot{'s' if slots != 1 else ''}" if slots else ""
                    ordinal = _ordinal(int(level_str))
                    desc_parts.append(f"- {ordinal} level ({slot_text}): {', '.join(spell_list)}")

        if footer:
            desc_parts.append(footer)

        full_desc = "\n".join(desc_parts)

        ability = {
            "name": sc.get("name", "Spellcasting"),
            "desc": full_desc,
        }
        abilities.append(ability)
    return abilities


def _ordinal(n):
    """Return ordinal string for a number (1st, 2nd, 3rd, etc.)."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    return f"{n}{suffixes.get(n % 10, 'th')}"


def _convert_traits(trait_arr):
    """Convert 5etools trait array to SRD special_abilities."""
    if not trait_arr:
        return []
    result = []
    for trait in trait_arr:
        name = trait.get("name", "")
        entries = trait.get("entries", [])
        desc = _entries_to_desc(entries)
        result.append({"name": name, "desc": desc})
    return result


def _convert_actions(action_arr):
    """Convert 5etools action array to SRD actions."""
    if not action_arr:
        return []
    result = []
    for action in action_arr:
        name = _strip_5etools_tags(action.get("name", ""))
        entries = action.get("entries", [])
        desc = _entries_to_desc(entries)
        result.append({"name": name, "desc": desc})
    return result


# ===== Main conversion function =====

def convert_5etools_monster(monster):
    """Convert a single 5etools monster dict to SRD format.

    Returns a dict in the same structure as entries in 5e-SRD-Monsters.json.
    """
    name = monster.get("name", "Unknown")
    index = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    type_str, subtype = _convert_type(monster.get("type", ""))
    cr_str, cr_num = _convert_cr(monster.get("cr", "0"))

    # Hit points / dice
    hp_obj = monster.get("hp", {})
    hit_points = hp_obj.get("average", 0) if isinstance(hp_obj, dict) else 0
    formula = hp_obj.get("formula", "") if isinstance(hp_obj, dict) else ""
    # Extract hit dice (the XdY part without the modifier)
    hit_dice_match = re.match(r"(\d+d\d+)", formula)
    hit_dice = hit_dice_match.group(1) if hit_dice_match else ""

    # Build SRD-format monster
    srd = {
        "index": index,
        "name": name,
        "size": _convert_size(monster.get("size", [])),
        "type": type_str,
        "alignment": _convert_alignment(monster.get("alignment", [])),
        "armor_class": _convert_ac(monster.get("ac", [])),
        "hit_points": hit_points,
        "hit_dice": hit_dice,
        "hit_points_roll": formula,
        "speed": _convert_speed(monster.get("speed", {})),
        "strength": monster.get("str", 10),
        "dexterity": monster.get("dex", 10),
        "constitution": monster.get("con", 10),
        "intelligence": monster.get("int", 10),
        "wisdom": monster.get("wis", 10),
        "charisma": monster.get("cha", 10),
        "proficiencies": _convert_proficiencies(monster),
        "damage_vulnerabilities": monster.get("vulnerable", []),
        "damage_resistances": _convert_resistances(monster.get("resist", [])),
        "damage_immunities": monster.get("immune", []),
        "condition_immunities": _convert_condition_immunities(monster.get("conditionImmune", [])),
        "senses": _convert_senses(monster.get("senses", []), monster.get("passive")),
        "languages": ", ".join(monster.get("languages", [])) if isinstance(monster.get("languages"), list) else (monster.get("languages") or ""),
        "challenge_rating": cr_num,
        "proficiency_bonus": CR_PROF.get(cr_str, 2),
        "xp": CR_XP.get(cr_str, 0),
    }

    if subtype:
        srd["subtype"] = subtype

    # Special abilities = traits + spellcasting
    special = _convert_traits(monster.get("trait", []))
    special.extend(_convert_spellcasting(monster.get("spellcasting", [])))
    if special:
        srd["special_abilities"] = special

    # Actions
    actions = _convert_actions(monster.get("action", []))
    if actions:
        srd["actions"] = actions

    # Legendary actions
    legendary = _convert_actions(monster.get("legendary", []))
    if legendary:
        srd["legendary_actions"] = legendary

    # Reactions
    reactions = _convert_actions(monster.get("reaction", []))
    if reactions:
        srd["reactions"] = reactions

    return srd


def convert_5etools_file(monsters_list):
    """Convert a list of 5etools monsters to SRD format.

    Returns a list of SRD-format monster dicts.
    """
    return [convert_5etools_monster(m) for m in monsters_list]


# =====================================================================
# SPELL CONVERSION
# =====================================================================

SCHOOL_MAP = {
    "A": ("abjuration", "Abjuration"),
    "C": ("conjuration", "Conjuration"),
    "D": ("divination", "Divination"),
    "E": ("enchantment", "Enchantment"),
    "V": ("evocation", "Evocation"),
    "I": ("illusion", "Illusion"),
    "N": ("necromancy", "Necromancy"),
    "T": ("transmutation", "Transmutation"),
}


def _convert_spell_range(range_obj):
    """Convert 5etools range object to SRD range string."""
    if not range_obj:
        return "Self"
    rtype = range_obj.get("type", "point")
    dist = range_obj.get("distance", {})
    dist_type = dist.get("type", "")
    amount = dist.get("amount")

    if dist_type == "touch":
        return "Touch"
    elif dist_type == "self":
        return "Self"
    elif dist_type == "sight":
        return "Sight"
    elif dist_type == "unlimited":
        return "Unlimited"
    elif dist_type == "special":
        return "Special"
    elif amount is not None:
        return f"{amount} feet"
    return "Self"


def _convert_spell_components(comp_obj):
    """Convert 5etools components object to SRD components list and material string."""
    if not comp_obj:
        return [], ""
    components = []
    if comp_obj.get("v"):
        components.append("V")
    if comp_obj.get("s"):
        components.append("S")
    material = ""
    if comp_obj.get("m"):
        components.append("M")
        m_val = comp_obj["m"]
        if isinstance(m_val, str):
            material = m_val.capitalize() if m_val[0].islower() else m_val
            if not material.endswith("."):
                material += "."
        elif isinstance(m_val, dict):
            material = m_val.get("text", "")
            if material and material[0].islower():
                material = material.capitalize()
            if material and not material.endswith("."):
                material += "."
    return components, material


def _convert_spell_duration(duration_arr):
    """Convert 5etools duration array to SRD duration string and concentration bool."""
    if not duration_arr:
        return "Instantaneous", False
    dur = duration_arr[0]
    concentration = dur.get("concentration", False)
    dtype = dur.get("type", "instant")

    if dtype == "instant":
        return "Instantaneous", False
    elif dtype == "permanent":
        return "Until dispelled", False
    elif dtype == "special":
        return "Special", concentration
    elif dtype == "timed":
        d = dur.get("duration", {})
        amount = d.get("type", "")
        num = d.get("amount", 1)
        # Pluralize unit
        unit = amount
        if num > 1:
            unit = amount + "s" if not amount.endswith("s") else amount
        time_str = f"{num} {unit}" if num > 1 else f"1 {unit}"
        if concentration:
            return f"Up to {time_str}", True
        return time_str, False
    return "Instantaneous", False


def _convert_spell_casting_time(time_arr):
    """Convert 5etools time array to SRD casting_time string."""
    if not time_arr:
        return "1 action"
    t = time_arr[0]
    number = t.get("number", 1)
    unit = t.get("unit", "action")
    if number == 1:
        return f"1 {unit}"
    return f"{number} {unit}s"


def _convert_spell_classes(classes_obj):
    """Convert 5etools classes object to SRD classes list."""
    if not classes_obj:
        return []
    result = []
    seen = set()
    from_list = classes_obj.get("fromClassList", [])
    for cls in from_list:
        name = cls.get("name", "")
        if name and name not in seen:
            slug = name.lower().replace(" ", "-")
            result.append({
                "index": slug,
                "name": name,
                "url": f"/api/2014/classes/{slug}",
            })
            seen.add(name)
    return result


def convert_5etools_spell(spell):
    """Convert a single 5etools spell dict to SRD format."""
    name = spell.get("name", "Unknown")
    index = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    # School
    school_code = spell.get("school", "")
    school_idx, school_name = SCHOOL_MAP.get(school_code, (school_code.lower(), school_code))

    # Components
    components, material = _convert_spell_components(spell.get("components"))

    # Duration
    duration_str, concentration = _convert_spell_duration(spell.get("duration"))

    # Entries -> desc
    entries = spell.get("entries", [])
    desc = []
    for entry in entries:
        if isinstance(entry, str):
            desc.append(_strip_5etools_tags(entry))
        elif isinstance(entry, dict) and "entries" in entry:
            entry_name = entry.get("name", "")
            sub_text = _entries_to_desc(entry["entries"])
            if entry_name:
                desc.append(f"***{entry_name}.*** {sub_text}")
            else:
                desc.append(sub_text)

    # Higher level
    higher_level = []
    for hl in spell.get("entriesHigherLevel", []):
        if isinstance(hl, dict) and "entries" in hl:
            for e in hl["entries"]:
                if isinstance(e, str):
                    higher_level.append(_strip_5etools_tags(e))

    # Range
    range_str = _convert_spell_range(spell.get("range"))

    # Casting time
    casting_time = _convert_spell_casting_time(spell.get("time"))

    # Ritual
    ritual = bool(spell.get("meta", {}).get("ritual")) if isinstance(spell.get("meta"), dict) else False

    srd = {
        "index": index,
        "name": name,
        "desc": desc,
        "range": range_str,
        "components": components,
        "ritual": ritual,
        "duration": duration_str,
        "concentration": concentration,
        "casting_time": casting_time,
        "level": spell.get("level", 0),
        "school": {
            "index": school_idx,
            "name": school_name,
            "url": f"/api/2014/magic-schools/{school_idx}",
        },
        "classes": _convert_spell_classes(spell.get("classes")),
        "subclasses": [],
    }

    if material:
        srd["material"] = material

    if higher_level:
        srd["higher_level"] = higher_level

    # Saving throw
    saves = spell.get("savingThrow", [])
    if saves:
        abbrev = saves[0][:3].lower()
        srd["dc"] = {
            "dc_type": {
                "index": abbrev,
                "name": abbrev.upper(),
                "url": f"/api/2014/ability-scores/{abbrev}",
            },
            "dc_success": "half",
        }

    # Area of effect from range type
    range_obj = spell.get("range", {})
    if isinstance(range_obj, dict):
        rtype = range_obj.get("type", "")
        dist = range_obj.get("distance", {})
        if rtype in ("sphere", "cone", "cube", "cylinder", "line"):
            srd["area_of_effect"] = {
                "type": rtype,
                "size": dist.get("amount", 0),
            }
        elif rtype == "radius":
            srd["area_of_effect"] = {
                "type": "sphere",
                "size": dist.get("amount", 0),
            }

    # Damage info from damageInflict
    damage_types = spell.get("damageInflict", [])
    if damage_types:
        dtype = damage_types[0]
        srd["damage"] = {
            "damage_type": {
                "index": dtype,
                "name": dtype.capitalize(),
                "url": f"/api/2014/damage-types/{dtype}",
            },
        }

    return srd


def convert_5etools_spells(spells_list):
    """Convert a list of 5etools spells to SRD format."""
    return [convert_5etools_spell(s) for s in spells_list]


# =====================================================================
# EQUIPMENT / ITEM CONVERSION
# =====================================================================

# 5etools item type codes -> SRD equipment_category
ITEM_TYPE_MAP = {
    "G": ("adventuring-gear", "Adventuring Gear"),
    "A": ("armor", "Armor"),
    "LA": ("armor", "Armor"),
    "MA": ("armor", "Armor"),
    "HA": ("armor", "Armor"),
    "S": ("armor", "Armor"),
    "M": ("weapon", "Weapon"),
    "R": ("weapon", "Weapon"),
    "SCF": ("adventuring-gear", "Adventuring Gear"),
    "AT": ("tools", "Tools"),
    "T": ("tools", "Tools"),
    "INS": ("tools", "Tools"),
    "GS": ("tools", "Tools"),
    "P": ("adventuring-gear", "Adventuring Gear"),
    "MNT": ("mounts-and-vehicles", "Mounts and Vehicles"),
    "VEH": ("mounts-and-vehicles", "Mounts and Vehicles"),
    "TAH": ("mounts-and-vehicles", "Mounts and Vehicles"),
    "TG": ("adventuring-gear", "Adventuring Gear"),
    "EXP": ("adventuring-gear", "Adventuring Gear"),
    "$": ("adventuring-gear", "Adventuring Gear"),
}


def _convert_item_cost(value_cp):
    """Convert 5etools value (in copper pieces) to SRD cost object."""
    if not value_cp:
        return None
    # Convert copper to the most appropriate denomination
    if value_cp >= 100 and value_cp % 100 == 0:
        return {"quantity": value_cp // 100, "unit": "gp"}
    elif value_cp >= 10 and value_cp % 10 == 0:
        return {"quantity": value_cp // 10, "unit": "sp"}
    else:
        return {"quantity": value_cp, "unit": "cp"}


def convert_5etools_item(item):
    """Convert a single 5etools equipment/item dict to SRD format."""
    name = item.get("name", "Unknown")
    index = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    item_type = item.get("type", "G")
    cat_idx, cat_name = ITEM_TYPE_MAP.get(item_type, ("adventuring-gear", "Adventuring Gear"))

    srd = {
        "index": index,
        "name": name,
        "equipment_category": {
            "index": cat_idx,
            "name": cat_name,
            "url": f"/api/2014/equipment-categories/{cat_idx}",
        },
    }

    # Gear sub-category
    if cat_idx == "adventuring-gear":
        srd["gear_category"] = {
            "index": "standard-gear",
            "name": "Standard Gear",
            "url": "/api/2014/equipment-categories/standard-gear",
        }

    # Cost (5etools stores value in copper pieces)
    cost = _convert_item_cost(item.get("value"))
    if cost:
        srd["cost"] = cost

    # Weight
    if item.get("weight"):
        srd["weight"] = item["weight"]

    # Description from entries
    entries = item.get("entries", [])
    if entries:
        desc = []
        for entry in entries:
            if isinstance(entry, str):
                desc.append(_strip_5etools_tags(entry))
            elif isinstance(entry, dict) and "entries" in entry:
                desc.append(_entries_to_desc(entry["entries"]))
        if desc:
            srd["desc"] = desc

    return srd


def convert_5etools_items(items_list):
    """Convert a list of 5etools items to SRD format."""
    return [convert_5etools_item(i) for i in items_list]


# =====================================================================
# FEAT CONVERSION
# =====================================================================

def _convert_feat_prerequisites(prereqs):
    """Convert 5etools prerequisite array to SRD prerequisites array."""
    if not prereqs:
        return []
    result = []
    for prereq in prereqs:
        # Ability score prerequisites
        for ability_obj in prereq.get("ability", []):
            for abbrev, min_score in ability_obj.items():
                result.append({
                    "ability_score": {
                        "index": abbrev,
                        "name": abbrev.upper(),
                        "url": f"/api/2014/ability-scores/{abbrev}",
                    },
                    "minimum_score": min_score,
                })
        # Level prerequisite
        if "level" in prereq:
            result.append({"level": prereq["level"]})
        # Race prerequisite
        if "race" in prereq:
            for race in prereq["race"]:
                result.append({"race": race.get("name", "")})
    return result


def _convert_feat_entries(entries):
    """Convert 5etools feat entries to SRD desc list."""
    if not entries:
        return []
    desc = []
    for entry in entries:
        if isinstance(entry, str):
            desc.append(_strip_5etools_tags(entry))
        elif isinstance(entry, dict):
            entry_type = entry.get("type", "")
            if entry_type == "list":
                # Convert list items to bullet-style lines
                items = entry.get("items", [])
                for item in items:
                    if isinstance(item, str):
                        desc.append(f"- {_strip_5etools_tags(item)}")
                    elif isinstance(item, dict) and "entries" in item:
                        desc.append(f"- {_entries_to_desc(item['entries'])}")
            elif "entries" in entry:
                name = entry.get("name", "")
                sub = _entries_to_desc(entry["entries"])
                if name:
                    desc.append(f"{name}. {sub}")
                else:
                    desc.append(sub)
    return desc


def convert_5etools_feat(feat):
    """Convert a single 5etools feat dict to SRD format."""
    name = feat.get("name", "Unknown")
    index = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    srd = {
        "index": index,
        "name": name,
        "desc": _convert_feat_entries(feat.get("entries", [])),
    }

    prereqs = _convert_feat_prerequisites(feat.get("prerequisite", []))
    if prereqs:
        srd["prerequisites"] = prereqs

    return srd


def convert_5etools_feats(feats_list):
    """Convert a list of 5etools feats to SRD format."""
    return [convert_5etools_feat(f) for f in feats_list]
