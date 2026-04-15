/* ===== D&D 5e SRD Library - Frontend Logic ===== */

let globalIndex = {};
let currentCategory = null;
let currentRefItem = null; // For the floating popup "Open as Card"
let openCards = [];
let customModalState = { mode: "create", slug: null, originalIndex: null };

// ===== INITIALIZATION =====
document.addEventListener("DOMContentLoaded", async () => {
    await loadCategories();
    await loadGlobalIndex();
    setupSearchHandlers();
    loadDarkMode();
    setupInitiativeResize();
});

async function loadCategories() {
    const res = await fetch("/api/categories");
    const categories = await res.json();
    const tabsEl = document.getElementById("category-tabs");
    const filterEl = document.getElementById("search-category-filter");

    categories.forEach(cat => {
        // Tab button
        const btn = document.createElement("button");
        btn.className = "tab-btn";
        btn.textContent = cat.name;
        btn.dataset.slug = cat.slug;
        btn.addEventListener("click", () => selectCategory(cat.slug, cat.name));
        tabsEl.appendChild(btn);

        // Filter option
        const opt = document.createElement("option");
        opt.value = cat.slug;
        opt.textContent = cat.name;
        filterEl.appendChild(opt);
    });
}

async function loadGlobalIndex() {
    const res = await fetch("/api/global-index");
    globalIndex = await res.json();
}

// ===== SEARCH =====
function setupSearchHandlers() {
    const input = document.getElementById("search-input");
    const btn = document.getElementById("search-btn");
    const resultsEl = document.getElementById("search-results");

    let debounceTimer;

    input.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => performSearch(), 300);
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            clearTimeout(debounceTimer);
            performSearch();
        }
        if (e.key === "Escape") {
            resultsEl.classList.add("hidden");
        }
    });

    btn.addEventListener("click", () => performSearch());

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".search-container") && !e.target.closest(".search-results")) {
            resultsEl.classList.add("hidden");
        }
    });
}

async function performSearch() {
    const query = document.getElementById("search-input").value.trim();
    const category = document.getElementById("search-category-filter").value;
    const resultsEl = document.getElementById("search-results");

    if (!query) {
        resultsEl.classList.add("hidden");
        return;
    }

    const params = new URLSearchParams({ q: query });
    if (category) params.set("category", category);

    const res = await fetch(`/api/search?${params}`);
    const results = await res.json();

    resultsEl.innerHTML = "";
    if (results.length === 0) {
        resultsEl.innerHTML = '<div class="search-result-item"><span class="search-result-name">No results found</span></div>';
    } else {
        results.forEach(r => {
            const div = document.createElement("div");
            div.className = "search-result-item";
            div.innerHTML = `
                <span class="search-result-name">${escapeHtml(r.name)}</span>
                <span class="search-result-category">${escapeHtml(r.category_name)}</span>
            `;
            div.addEventListener("click", () => {
                openItemCard(r.category, r.index);
                resultsEl.classList.add("hidden");
                document.getElementById("search-input").value = "";
            });
            resultsEl.appendChild(div);
        });
    }
    resultsEl.classList.remove("hidden");
}

// ===== CATEGORY SELECTION =====
async function selectCategory(slug, name) {
    currentCategory = slug;

    // Update active tab
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.slug === slug);
    });

    // Show add button
    document.getElementById("add-custom-btn").classList.remove("hidden");
    document.getElementById("add-custom-btn").onclick = () => openCustomModal(slug);

    // Load items
    document.getElementById("sidebar-title").textContent = name;
    const listEl = document.getElementById("sidebar-list");
    listEl.innerHTML = '<div class="loading">Loading...</div>';

    const res = await fetch(`/api/category/${slug}`);
    const items = await res.json();

    renderSidebarItems(items, slug);
    await loadFilters(slug);
}

function renderSidebarItems(items, slug) {
    const listEl = document.getElementById("sidebar-list");
    listEl.innerHTML = "";
    items.forEach(item => {
        const div = document.createElement("div");
        const isCustom = item.index.endsWith("_custom");
        div.className = `sidebar-item${isCustom ? " custom-item" : ""}`;
        div.innerHTML = escapeHtml(item.name) + (isCustom ? '<span class="custom-badge">CUSTOM</span>' : "");
        div.addEventListener("click", () => openItemCard(slug, item.index));
        listEl.appendChild(div);
    });
}

// ===== ITEM CARDS =====
async function openItemCard(category, index) {
    // Don't open duplicates
    if (openCards.find(c => c.category === category && c.index === index)) return;

    const res = await fetch(`/api/item/${category}/${index}`);
    if (!res.ok) return;
    const data = await res.json();

    const cardId = `card-${category}-${index}`;
    openCards.push({ category, index, id: cardId, data: data.item });

    // Hide placeholder
    const placeholder = document.getElementById("cards-placeholder");
    if (placeholder) placeholder.style.display = "none";

    const cardsArea = document.getElementById("cards-area");
    const cardEl = document.createElement("div");
    cardEl.className = "item-card";
    cardEl.id = cardId;
    cardEl.innerHTML = renderCard(data.item, category, cardId);
    cardsArea.appendChild(cardEl);
}

function closeCard(cardId) {
    const el = document.getElementById(cardId);
    if (el) el.remove();
    openCards = openCards.filter(c => c.id !== cardId);

    if (openCards.length === 0) {
        const placeholder = document.getElementById("cards-placeholder");
        if (placeholder) placeholder.style.display = "flex";
    }
}

function showCardJson(cardId) {
    const card = openCards.find(c => c.id === cardId);
    if (!card) return;
    document.getElementById("json-modal-title").textContent = `JSON: ${card.data.name || card.index}`;
    document.getElementById("json-modal-body").textContent = JSON.stringify(card.data, null, 2);
    document.getElementById("json-modal").classList.remove("hidden");
    document.getElementById("json-modal-overlay").classList.remove("hidden");
}

function closeJsonModal() {
    document.getElementById("json-modal").classList.add("hidden");
    document.getElementById("json-modal-overlay").classList.add("hidden");
}

function copyJson() {
    const text = document.getElementById("json-modal-body").textContent;
    navigator.clipboard.writeText(text).catch(() => {});
}

// ===== CARD RENDERING =====
function renderCard(item, category, cardId) {
    const index = item.index || "";
    const isCustom = Boolean(item._custom) || index.endsWith("_custom");
    let html = `<div class="card-top-bar"></div>`;
    html += `<div class="card-header">`;
    html += `<div>`;
    html += `<div class="card-title">${escapeHtml(item.name || item.full_name || item.index)}</div>`;
    html += renderSubtitle(item, category);
    html += `</div>`;
    html += `<div class="card-actions">`;
    if (isCustom) {
        html += `<button class="card-btn" title="Edit custom item" onclick="editCustomItem('${escapeAttr(category)}', '${escapeAttr(index)}')">✎</button>`;
        html += `<button class="card-btn" title="Delete custom item" onclick="deleteCustomItem('${escapeAttr(category)}', '${escapeAttr(index)}', '${escapeAttr(cardId)}')">🗑</button>`;
    } else {
        html += `<button class="card-btn" title="Copy to custom" onclick="copyItemToCustom('${escapeAttr(category)}', '${escapeAttr(index)}')">⧉</button>`;
    }
    html += `<button class="card-btn" title="Show JSON" onclick="showCardJson('${cardId}')">{ }</button>`;
    html += `<button class="card-btn close-btn" title="Close" onclick="closeCard('${cardId}')">&times;</button>`;
    html += `</div></div>`;
    html += `<div class="card-separator"></div>`;
    html += `<div class="card-body">`;

    // Render based on category
    switch (category) {
        case "spells": html += renderSpell(item); break;
        case "monsters": html += renderMonster(item); break;
        case "equipment": html += renderEquipment(item); break;
        case "magic-items": html += renderMagicItem(item); break;
        case "classes": html += renderClass(item); break;
        case "races": html += renderRace(item); break;
        case "feats": html += renderFeat(item); break;
        case "features": html += renderFeature(item); break;
        case "backgrounds": html += renderBackground(item); break;
        case "conditions": html += renderCondition(item); break;
        case "skills": html += renderSkill(item); break;
        case "traits": html += renderTrait(item); break;
        case "ability-scores": html += renderAbilityScore(item); break;
        case "subclasses": html += renderSubclass(item); break;
        case "subraces": html += renderSubrace(item); break;
        case "characters": html += renderCharacter(item); break;
        default: html += renderGeneric(item); break;
    }

    html += `</div>`;
    return html;
}

function renderSubtitle(item, category) {
    let sub = "";
    switch (category) {
        case "spells": {
            const lvl = item.level === 0 ? "Cantrip" : `Level ${item.level}`;
            const school = item.school ? item.school.name : "";
            sub = `${school} ${lvl}`;
            if (item.ritual) sub += " (ritual)";
            break;
        }
        case "monsters": {
            sub = `${item.size || ""} ${item.type || ""}`;
            if (item.alignment) sub += `, ${item.alignment}`;
            break;
        }
        case "equipment": {
            const ecat = item.equipment_category ? item.equipment_category.name : "";
            if (item.weapon_category) sub = `${item.weapon_category} ${item.category_range || "Weapon"}`;
            else if (item.armor_category) sub = `${item.armor_category} Armor`;
            else sub = ecat;
            break;
        }
        case "magic-items": {
            const rarity = item.rarity ? item.rarity.name : "";
            const ecat = item.equipment_category ? item.equipment_category.name : "Wondrous Item";
            sub = `${ecat}, ${rarity}`;
            break;
        }
        case "features": {
            const cls = item.class ? item.class.name : "";
            sub = cls ? `${cls}, Level ${item.level || "?"}` : "";
            break;
        }
        case "traits": {
            const races = (item.races || []).map(r => r.name).join(", ");
            sub = races ? `Racial Trait (${races})` : "Racial Trait";
            break;
        }
        default: break;
    }
    return sub ? `<div class="card-subtitle">${escapeHtml(sub)}</div>` : "";
}

// ---- Spell ----
function renderSpell(s) {
    let h = "";
    h += propLine("Casting Time", s.casting_time);
    h += propLine("Range", s.range);
    h += propLine("Components", (s.components || []).join(", ") + (s.material ? ` (${s.material})` : ""));
    h += propLine("Duration", s.duration + (s.concentration ? " (Concentration)" : ""));
    h += `<div class="card-separator"></div>`;
    h += renderDesc(s.desc);
    if (s.higher_level && s.higher_level.length) {
        h += `<div class="card-section-title">At Higher Levels</div>`;
        h += renderDesc(s.higher_level);
    }
    if (s.damage) {
        if (s.damage.damage_type) {
            h += propLine("Damage Type", refLink(s.damage.damage_type));
        }
        if (s.damage.damage_at_slot_level) {
            h += `<div class="card-section-title">Damage by Slot Level</div>`;
            h += renderKeyValueTable("Slot Level", "Damage", s.damage.damage_at_slot_level);
        }
        if (s.damage.damage_at_character_level) {
            h += `<div class="card-section-title">Damage by Character Level</div>`;
            h += renderKeyValueTable("Character Level", "Damage", s.damage.damage_at_character_level);
        }
    }
    if (s.dc) {
        h += propLine("Save", refLink(s.dc.dc_type) + ` (${s.dc.dc_success || "half"})`);
    }
    if (s.area_of_effect) {
        h += propLine("Area", `${s.area_of_effect.size} ft ${s.area_of_effect.type}`);
    }
    h += `<div class="card-separator" style="margin-top:8px"></div>`;
    h += `<div class="tag-list" style="margin-top:8px">`;
    if (s.classes) s.classes.forEach(c => { h += refTag(c); });
    if (s.subclasses) s.subclasses.forEach(c => { h += refTag(c); });
    h += `</div>`;
    return h;
}

// ---- Monster ----
function renderMonster(m) {
    let h = "";
    // AC, HP, Speed
    const ac = (m.armor_class || []).map(a => `${a.value}${a.type && a.type !== "dex" ? ` (${a.type})` : ""}`).join(", ");
    h += propLine("Armor Class", ac);
    h += propLine("Hit Points", `${m.hit_points} (${m.hit_dice || m.hit_points_roll || ""})`);
    const speeds = m.speed ? Object.entries(m.speed).map(([k, v]) => `${k} ${v}`).join(", ") : "";
    h += propLine("Speed", speeds);
    h += `<div class="card-separator"></div>`;

    // Ability scores
    h += `<div class="stat-block">`;
    ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"].forEach(ab => {
        const val = m[ab] || 10;
        const mod = Math.floor((val - 10) / 2);
        const modStr = mod >= 0 ? `+${mod}` : `${mod}`;
        h += `<div class="stat-item">
            <span class="stat-label">${ab.substring(0, 3).toUpperCase()}</span>
            <span class="stat-value">${val}</span>
            <span class="stat-mod">(${modStr})</span>
        </div>`;
    });
    h += `</div>`;
    h += `<div class="card-separator"></div>`;

    // Proficiencies (saving throws, skills)
    if (m.proficiencies && m.proficiencies.length) {
        const saves = m.proficiencies.filter(p => p.proficiency.index.startsWith("saving-throw-"));
        const skills = m.proficiencies.filter(p => p.proficiency.index.startsWith("skill-"));
        if (saves.length) {
            h += propLine("Saving Throws", saves.map(p => `${p.proficiency.name.replace("Saving Throw: ", "")} +${p.value}`).join(", "));
        }
        if (skills.length) {
            h += propLine("Skills", skills.map(p => `${p.proficiency.name.replace("Skill: ", "")} +${p.value}`).join(", "));
        }
    }

    if (m.damage_vulnerabilities && m.damage_vulnerabilities.length) h += propLine("Vulnerabilities", m.damage_vulnerabilities.join(", "));
    if (m.damage_resistances && m.damage_resistances.length) h += propLine("Resistances", m.damage_resistances.join(", "));
    if (m.damage_immunities && m.damage_immunities.length) h += propLine("Immunities", m.damage_immunities.join(", "));
    if (m.condition_immunities && m.condition_immunities.length) {
        h += propLine("Condition Immunities", m.condition_immunities.map(c => conditionRefLink(c)).join(", "));
    }

    if (m.senses) {
        const senseStr = Object.entries(m.senses).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(", ");
        h += propLine("Senses", senseStr);
    }
    h += propLine("Languages", m.languages || "—");
    h += propLine("Challenge", `${m.challenge_rating} (${(m.xp || 0).toLocaleString()} XP)`);
    if (m.proficiency_bonus) h += propLine("Proficiency Bonus", `+${m.proficiency_bonus}`);

    h += `<div class="card-separator"></div>`;

    // Special Abilities
    if (m.special_abilities && m.special_abilities.length) {
        m.special_abilities.forEach(a => {
            if (a.spellcasting && a.spellcasting.spells && a.spellcasting.spells.length) {
                h += renderSpellcasting(a);
            } else if (isTextSpellcastingAbility(a)) {
                h += renderSpellcastingFromDesc(a);
            } else {
                h += `<div class="feature-block"><span class="feature-name">${escapeHtml(a.name)}.</span> ${processDesc(a.desc)}</div>`;
            }
        });
    }

    // Actions
    if (m.actions && m.actions.length) {
        h += `<div class="card-section-title">Actions</div>`;
        m.actions.forEach(a => {
            h += `<div class="feature-block"><span class="feature-name">${escapeHtml(a.name)}.</span> ${processDesc(a.desc)}</div>`;
        });
    }

    // Legendary Actions
    if (m.legendary_actions && m.legendary_actions.length) {
        h += `<div class="card-section-title">Legendary Actions</div>`;
        m.legendary_actions.forEach(a => {
            h += `<div class="feature-block"><span class="feature-name">${escapeHtml(a.name)}.</span> ${processDesc(a.desc)}</div>`;
        });
    }

    // Reactions
    if (m.reactions && m.reactions.length) {
        h += `<div class="card-section-title">Reactions</div>`;
        m.reactions.forEach(a => {
            h += `<div class="feature-block"><span class="feature-name">${escapeHtml(a.name)}.</span> ${processDesc(a.desc)}</div>`;
        });
    }

    return h;
}

// ---- Spellcasting (Monster) ----
function renderSpellcasting(ability) {
    const sc = ability.spellcasting;
    let h = `<div class="feature-block spellcasting-block">`;

    // Header line from desc, take only the first paragraph (before the spell list)
    const descText = ability.desc || "";
    const introPart = descText.split(/\n/)[0];
    h += `<span class="feature-name">${escapeHtml(ability.name)}.</span> ${processDesc(introPart)}`;

    // Group spells by level
    const spells = sc.spells || [];
    const byLevel = {};
    spells.forEach(sp => {
        const lvl = sp.level || 0;
        if (!byLevel[lvl]) byLevel[lvl] = [];
        byLevel[lvl].push(sp);
    });

    const levelNames = {
        0: "Cantrips (at will)",
        1: "1st level",
        2: "2nd level",
        3: "3rd level",
        4: "4th level",
        5: "5th level",
        6: "6th level",
        7: "7th level",
        8: "8th level",
        9: "9th level",
    };

    const slots = sc.slots || {};
    const sortedLevels = Object.keys(byLevel).map(Number).sort((a, b) => a - b);

    h += `<div class="spell-list-block">`;
    sortedLevels.forEach(lvl => {
        const name = levelNames[lvl] || `Level ${lvl}`;
        let slotInfo = "";
        if (lvl > 0 && slots[String(lvl)]) {
            const n = slots[String(lvl)];
            slotInfo = ` (${n} slot${n > 1 ? "s" : ""})`;
        }
        const spellLinks = byLevel[lvl].map(sp => {
            const idx = sp.url ? sp.url.split("/").pop() : sp.name.toLowerCase().replace(/ /g, "-");
            return `<span class="ref-link" onclick="showRefPopup('${escapeAttr(idx)}')">${escapeHtml(sp.name)}</span>`;
        }).join(", ");
        h += `<div class="spell-level-row"><span class="spell-level-label">${escapeHtml(name)}${slotInfo}:</span> ${spellLinks}</div>`;
    });
    h += `</div></div>`;
    return h;
}

function isTextSpellcastingAbility(ability) {
    if (!ability || !ability.desc) return false;
    const name = String(ability.name || "").toLowerCase();
    const desc = String(ability.desc || "");
    return name.includes("spellcasting") && /(^|\n)\s*[-*]\s+.+?:/im.test(desc);
}

function renderSpellcastingFromDesc(ability) {
    const descText = String(ability.desc || "");
    const lines = descText.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const introLines = [];
    const listLines = [];

    lines.forEach(line => {
        if (/^[-*]\s+/.test(line)) {
            listLines.push(line.replace(/^[-*]\s+/, ""));
        } else {
            introLines.push(line);
        }
    });

    let h = `<div class="feature-block spellcasting-block">`;
    const introPart = introLines.join(" ");
    h += `<span class="feature-name">${escapeHtml(ability.name || "Spellcasting")}.</span> ${processDesc(introPart)}`;
    h += `<div class="spell-list-block">`;

    listLines.forEach(line => {
        const colonIdx = line.indexOf(":");
        if (colonIdx === -1) {
            h += `<div class="spell-level-row">${processDesc(line)}</div>`;
            return;
        }

        const label = line.slice(0, colonIdx).trim();
        const spellPart = line.slice(colonIdx + 1).trim();
        const spellLinks = spellPart
            .split(",")
            .map(token => token.trim())
            .filter(Boolean)
            .map(token => renderSpellToken(token))
            .join(", ");

        h += `<div class="spell-level-row"><span class="spell-level-label">${escapeHtml(label)}:</span> ${spellLinks}</div>`;
    });

    h += `</div></div>`;
    return h;
}

function renderSpellToken(token) {
    const match = token.match(/^(.+?)\s*\(([^)]+)\)\s*$/);
    const spellName = match ? match[1].trim() : token;
    const note = match ? ` (${match[2]})` : "";

    const idx = spellName
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, "")
        .trim()
        .replace(/\s+/g, "-");

    if (idx && globalIndex[idx]) {
        return `<span class="ref-link" onclick="showRefPopup('${escapeAttr(idx)}')">${escapeHtml(spellName)}</span>${escapeHtml(note)}`;
    }
    return `${escapeHtml(spellName)}${escapeHtml(note)}`;
}

function conditionRefLink(condition) {
    if (!condition) return "";
    if (typeof condition === "object") return refLink(condition);

    const raw = String(condition).trim();
    if (!raw) return "";

    const normalized = raw.toLowerCase();
    const slug = normalized
        .replace(/[^a-z0-9\s-]/g, "")
        .trim()
        .replace(/\s+/g, "-");
    const candidates = [normalized, slug];
    const resolvedIndex = candidates.find(idx => idx && globalIndex[idx]);

    if (resolvedIndex) {
        return `<span class="ref-link" onclick="showRefPopup('${escapeAttr(resolvedIndex)}')">${escapeHtml(raw)}</span>`;
    }
    return escapeHtml(raw);
}

// ---- Equipment ----
function renderEquipment(e) {
    let h = "";
    if (e.equipment_category) h += propLine("Category", refLink(e.equipment_category));
    if (e.cost) h += propLine("Cost", `${e.cost.quantity} ${e.cost.unit}`);
    if (e.weight) h += propLine("Weight", `${e.weight} lb.`);

    if (e.damage) {
        h += propLine("Damage", `${e.damage.damage_dice} ${e.damage.damage_type ? refLink(e.damage.damage_type) : ""}`);
    }
    if (e.two_handed_damage) {
        h += propLine("Two-Handed", `${e.two_handed_damage.damage_dice} ${e.two_handed_damage.damage_type ? refLink(e.two_handed_damage.damage_type) : ""}`);
    }
    if (e.range) {
        h += propLine("Range", `${e.range.normal}${e.range.long ? `/${e.range.long}` : ""} ft.`);
    }
    if (e.throw_range) {
        h += propLine("Throw Range", `${e.throw_range.normal}/${e.throw_range.long} ft.`);
    }
    if (e.armor_class) {
        let acStr = `${e.armor_class.base}`;
        if (e.armor_class.dex_bonus) acStr += " + Dex";
        if (e.armor_class.max_bonus) acStr += ` (max ${e.armor_class.max_bonus})`;
        h += propLine("Armor Class", acStr);
    }
    if (e.str_minimum) h += propLine("Str Minimum", e.str_minimum);
    if (e.stealth_disadvantage) h += propLine("Stealth", "Disadvantage");
    if (e.speed) h += propLine("Speed", `${e.speed.quantity} ${e.speed.unit}`);

    if (e.properties && e.properties.length) {
        h += `<div class="tag-list" style="margin-top:8px">`;
        e.properties.forEach(p => { h += refTag(p); });
        h += `</div>`;
    }

    h += renderDesc(e.desc);
    if (e.contents && e.contents.length) {
        h += `<div class="card-section-title">Contents</div>`;
        e.contents.forEach(c => {
            h += `<div>${refLink(c.item)} (×${c.quantity})</div>`;
        });
    }
    return h;
}

// ---- Magic Item ----
function renderMagicItem(mi) {
    let h = "";
    if (mi.rarity) {
        const rarityClass = "rarity-" + (mi.rarity.name || "").toLowerCase().replace(/ /g, "-");
        h += `<div class="property-line"><span class="label">Rarity: </span><span class="value ${rarityClass}">${escapeHtml(mi.rarity.name)}</span></div>`;
    }
    h += renderDesc(mi.desc);
    if (mi.variants && mi.variants.length) {
        h += `<div class="card-section-title">Variants</div>`;
        h += `<div class="tag-list">`;
        mi.variants.forEach(v => { h += refTag(v); });
        h += `</div>`;
    }
    return h;
}

// ---- Class ----
function renderClass(c) {
    let h = "";
    h += propLine("Hit Die", `d${c.hit_die}`);

    if (c.saving_throws && c.saving_throws.length) {
        h += propLine("Saving Throws", c.saving_throws.map(s => refLink(s)).join(", "));
    }

    if (c.proficiencies && c.proficiencies.length) {
        h += `<div class="card-section-title">Proficiencies</div>`;
        h += `<div class="tag-list">`;
        c.proficiencies.forEach(p => { h += refTag(p); });
        h += `</div>`;
    }

    if (c.proficiency_choices && c.proficiency_choices.length) {
        c.proficiency_choices.forEach(pc => {
            h += `<div class="card-section-title">Choose ${pc.choose}</div>`;
            if (pc.from && pc.from.options) {
                h += `<div class="tag-list">`;
                pc.from.options.forEach(opt => {
                    const item = opt.item || opt;
                    if (item.name) h += refTag(item);
                });
                h += `</div>`;
            }
        });
    }

    if (c.starting_equipment && c.starting_equipment.length) {
        h += `<div class="card-section-title">Starting Equipment</div>`;
        c.starting_equipment.forEach(se => {
            h += `<div>${refLink(se.equipment)} ×${se.quantity}</div>`;
        });
    }

    return h;
}

// ---- Race ----
function renderRace(r) {
    let h = "";
    h += propLine("Speed", `${r.speed} ft.`);
    h += propLine("Size", r.size);

    if (r.ability_bonuses && r.ability_bonuses.length) {
        h += propLine("Ability Bonuses", r.ability_bonuses.map(ab =>
            `${refLink(ab.ability_score)} +${ab.bonus}`
        ).join(", "));
    }

    if (r.alignment) h += `<div class="card-desc"><p><strong>Alignment.</strong> ${processDesc(r.alignment)}</p></div>`;
    if (r.age) h += `<div class="card-desc"><p><strong>Age.</strong> ${processDesc(r.age)}</p></div>`;
    if (r.size_description) h += `<div class="card-desc"><p><strong>Size.</strong> ${processDesc(r.size_description)}</p></div>`;

    if (r.languages && r.languages.length) {
        h += propLine("Languages", r.languages.map(l => refLink(l)).join(", "));
    }
    if (r.language_desc) h += `<div class="card-desc"><p>${processDesc(r.language_desc)}</p></div>`;

    if (r.traits && r.traits.length) {
        h += `<div class="card-section-title">Traits</div>`;
        h += `<div class="tag-list">`;
        r.traits.forEach(t => { h += refTag(t); });
        h += `</div>`;
    }

    if (r.subraces && r.subraces.length) {
        h += `<div class="card-section-title">Subraces</div>`;
        h += `<div class="tag-list">`;
        r.subraces.forEach(s => { h += refTag(s); });
        h += `</div>`;
    }

    return h;
}

// ---- Feat ----
function renderFeat(f) {
    let h = "";
    if (f.prerequisites && f.prerequisites.length) {
        h += propLine("Prerequisites", f.prerequisites.map(p => {
            if (p.ability_score) return `${refLink(p.ability_score)} ${p.minimum_score}+`;
            return JSON.stringify(p);
        }).join(", "));
    }
    h += renderDesc(f.desc);
    return h;
}

// ---- Feature ----
function renderFeature(f) {
    let h = "";
    if (f.class) h += propLine("Class", refLink(f.class));
    if (f.subclass) h += propLine("Subclass", refLink(f.subclass));
    if (f.level) h += propLine("Level", f.level);
    h += `<div class="card-separator"></div>`;
    h += renderDesc(f.desc);
    return h;
}

// ---- Background ----
function renderBackground(b) {
    let h = "";
    if (b.starting_proficiencies && b.starting_proficiencies.length) {
        h += propLine("Proficiencies", b.starting_proficiencies.map(p => refLink(p)).join(", "));
    }
    if (b.starting_equipment && b.starting_equipment.length) {
        h += `<div class="card-section-title">Starting Equipment</div>`;
        b.starting_equipment.forEach(se => {
            h += `<div>${refLink(se.equipment)} ×${se.quantity}</div>`;
        });
    }
    if (b.feature) {
        h += `<div class="card-section-title">${escapeHtml(b.feature.name)}</div>`;
        h += renderDesc(b.feature.desc);
    }
    return h;
}

// ---- Condition ----
function renderCondition(c) {
    return renderDesc(c.desc);
}

// ---- Skill ----
function renderSkill(s) {
    let h = "";
    if (s.ability_score) h += propLine("Ability", refLink(s.ability_score));
    h += renderDesc(s.desc);
    return h;
}

// ---- Trait ----
function renderTrait(t) {
    let h = "";
    if (t.races && t.races.length) {
        h += propLine("Races", t.races.map(r => refLink(r)).join(", "));
    }
    if (t.subraces && t.subraces.length) {
        h += propLine("Subraces", t.subraces.map(r => refLink(r)).join(", "));
    }
    if (t.proficiencies && t.proficiencies.length) {
        h += propLine("Proficiencies", t.proficiencies.map(p => refLink(p)).join(", "));
    }
    h += renderDesc(t.desc);
    return h;
}

// ---- Ability Score ----
function renderAbilityScore(a) {
    let h = "";
    h += propLine("Full Name", a.full_name || a.name);
    h += renderDesc(a.desc);
    if (a.skills && a.skills.length) {
        h += `<div class="card-section-title">Related Skills</div>`;
        h += `<div class="tag-list">`;
        a.skills.forEach(s => { h += refTag(s); });
        h += `</div>`;
    }
    return h;
}

// ---- Subclass ----
function renderSubclass(s) {
    let h = "";
    if (s.class) h += propLine("Class", refLink(s.class));
    if (s.subclass_flavor) h += propLine("Flavor", s.subclass_flavor);
    h += renderDesc(s.desc);
    if (s.spells && s.spells.length) {
        h += `<div class="card-section-title">Spells</div>`;
        h += `<div class="tag-list">`;
        s.spells.forEach(sp => {
            if (sp.spell) h += refTag(sp.spell);
        });
        h += `</div>`;
    }
    return h;
}

// ---- Subrace ----
function renderSubrace(s) {
    let h = "";
    if (s.race) h += propLine("Race", refLink(s.race));
    h += renderDesc(s.desc);
    if (s.ability_bonuses && s.ability_bonuses.length) {
        h += propLine("Ability Bonuses", s.ability_bonuses.map(ab =>
            `${refLink(ab.ability_score)} +${ab.bonus}`
        ).join(", "));
    }
    if (s.racial_traits && s.racial_traits.length) {
        h += `<div class="card-section-title">Traits</div>`;
        h += `<div class="tag-list">`;
        s.racial_traits.forEach(t => { h += refTag(t); });
        h += `</div>`;
    }
    return h;
}

// ---- Character ----
function renderCharacter(c) {
    let h = "";
    h += propLine("Hit Points", c.hit_points);
    h += propLine("Armor Class", c.armor_class);
    return h;
}

// ---- Generic fallback ----
function renderGeneric(item) {
    let h = "";
    if (item.desc) h += renderDesc(item.desc);

    // Show any reference fields
    const skipKeys = new Set(["index", "name", "full_name", "url", "desc", "_custom"]);
    for (const [key, val] of Object.entries(item)) {
        if (skipKeys.has(key)) continue;
        if (val && typeof val === "object" && val.name && val.index) {
            h += propLine(formatKey(key), refLink(val));
        } else if (Array.isArray(val) && val.length && val[0] && typeof val[0] === "object" && val[0].name) {
            h += propLine(formatKey(key), val.map(v => v.index ? refLink(v) : escapeHtml(v.name)).join(", "));
        } else if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
            h += propLine(formatKey(key), String(val));
        }
    }
    return h;
}

// ===== CROSS-REFERENCE POPUP =====
async function showRefPopup(index) {
    // Resolve the index to find its category
    const res = await fetch(`/api/resolve/${encodeURIComponent(index)}`);
    if (!res.ok) return;
    const info = await res.json();
    if (info.error) return;

    // Fetch full item
    const itemRes = await fetch(`/api/item/${info.category}/${encodeURIComponent(index)}`);
    if (!itemRes.ok) return;
    const data = await itemRes.json();

    currentRefItem = { category: info.category, index: index };

    document.getElementById("ref-popup-title").textContent = data.item.name || index;
    const body = document.getElementById("ref-popup-body");
    body.innerHTML = "";

    // Render a mini version of the card
    const miniHtml = renderCardBody(data.item, info.category);
    body.innerHTML = miniHtml;

    document.getElementById("ref-popup").classList.remove("hidden");
    document.getElementById("ref-popup-overlay").classList.remove("hidden");
}

function renderCardBody(item, category) {
    // Reuse the category-specific renderers
    switch (category) {
        case "spells": return renderSpell(item);
        case "monsters": return renderMonster(item);
        case "equipment": return renderEquipment(item);
        case "magic-items": return renderMagicItem(item);
        case "classes": return renderClass(item);
        case "races": return renderRace(item);
        case "feats": return renderFeat(item);
        case "features": return renderFeature(item);
        case "backgrounds": return renderBackground(item);
        case "conditions": return renderCondition(item);
        case "skills": return renderSkill(item);
        case "traits": return renderTrait(item);
        case "ability-scores": return renderAbilityScore(item);
        case "subclasses": return renderSubclass(item);
        case "subraces": return renderSubrace(item);
        case "characters": return renderCharacter(item);
        default: return renderGeneric(item);
    }
}

function closeRefPopup() {
    document.getElementById("ref-popup").classList.add("hidden");
    document.getElementById("ref-popup-overlay").classList.add("hidden");
    currentRefItem = null;
}

function openRefAsCard() {
    if (currentRefItem) {
        openItemCard(currentRefItem.category, currentRefItem.index);
    }
    closeRefPopup();
}

// ===== CUSTOM ITEM MODAL =====
function openCustomModal(slug) {
    // For characters, use the character modal instead
    if (slug === "characters") {
        openCharacterModal();
        return;
    }
    openCustomModalWithState({
        mode: "create",
        slug,
        name: "",
        itemJson: {},
        originalIndex: null,
    });
}

function openCustomModalWithState({ mode, slug, name, itemJson, originalIndex }) {
    customModalState = { mode, slug, originalIndex };
    document.getElementById("custom-modal").dataset.slug = slug;
    document.getElementById("custom-name").value = name || "";
    document.getElementById("custom-json").value = JSON.stringify(itemJson || {}, null, 2);
    document.getElementById("custom-error").classList.add("hidden");

    const titleEl = document.getElementById("custom-modal-title");
    const saveBtn = document.getElementById("custom-save-btn");
    if (mode === "edit") {
        titleEl.textContent = "Edit Custom Item";
        saveBtn.textContent = "Save Changes";
    } else if (mode === "copy") {
        titleEl.textContent = "Copy as Custom Item";
        saveBtn.textContent = "Save Copy";
    } else {
        titleEl.textContent = "Add Custom Item";
        saveBtn.textContent = "Save Item";
    }

    document.getElementById("custom-modal").classList.remove("hidden");
    document.getElementById("custom-modal-overlay").classList.remove("hidden");
}

function getEditableItemJson(item) {
    const editable = JSON.parse(JSON.stringify(item || {}));
    delete editable.index;
    delete editable.name;
    delete editable._custom;
    return editable;
}

async function copyItemToCustom(slug, index) {
    const res = await fetch(`/api/item/${slug}/${encodeURIComponent(index)}`);
    if (!res.ok) return;

    const data = await res.json();
    const baseName = data.item.name || data.item.full_name || index;
    openCustomModalWithState({
        mode: "copy",
        slug,
        name: `${baseName} (Copy)`,
        itemJson: getEditableItemJson(data.item),
        originalIndex: null,
    });
}

async function editCustomItem(slug, index) {
    let item = null;
    const card = openCards.find(c => c.category === slug && c.index === index);
    if (card) {
        item = card.data;
    } else {
        const res = await fetch(`/api/item/${slug}/${encodeURIComponent(index)}`);
        if (!res.ok) return;
        const data = await res.json();
        item = data.item;
    }

    openCustomModalWithState({
        mode: "edit",
        slug,
        name: item.name || "",
        itemJson: getEditableItemJson(item),
        originalIndex: index,
    });
}

async function deleteCustomItem(slug, index, cardId) {
    const ok = window.confirm("Delete this custom item? This cannot be undone.");
    if (!ok) return;

    const res = await fetch(`/api/custom/${slug}/${encodeURIComponent(index)}`, {
        method: "DELETE",
    });
    const data = await res.json();
    if (!res.ok) {
        window.alert(data.error || "Failed to delete custom item.");
        return;
    }

    closeCard(cardId);
    await loadGlobalIndex();
    if (currentCategory === slug) {
        const catName = document.querySelector(`.tab-btn[data-slug="${slug}"]`)?.textContent || slug;
        await selectCategory(slug, catName);
    }
}

function closeCustomModal() {
    document.getElementById("custom-modal").classList.add("hidden");
    document.getElementById("custom-modal-overlay").classList.add("hidden");
    customModalState = { mode: "create", slug: null, originalIndex: null };
}

async function saveCustomItem() {
    const slug = customModalState.slug || document.getElementById("custom-modal").dataset.slug;
    const name = document.getElementById("custom-name").value.trim();
    const jsonStr = document.getElementById("custom-json").value.trim();
    const errorEl = document.getElementById("custom-error");

    if (!name) {
        errorEl.textContent = "Please enter a name.";
        errorEl.classList.remove("hidden");
        return;
    }

    let itemJson;
    try {
        itemJson = JSON.parse(jsonStr);
        if (typeof itemJson !== "object" || Array.isArray(itemJson)) throw new Error();
    } catch {
        errorEl.textContent = "Invalid JSON. Please enter a valid JSON object.";
        errorEl.classList.remove("hidden");
        return;
    }

    const isEdit = customModalState.mode === "edit";
    const endpoint = isEdit
        ? `/api/custom/${slug}/${encodeURIComponent(customModalState.originalIndex)}`
        : `/api/custom/${slug}`;
    const method = isEdit ? "PUT" : "POST";

    const res = await fetch(endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, item: itemJson }),
    });

    const data = await res.json();
    if (!res.ok) {
        errorEl.textContent = data.error || "Failed to save.";
        errorEl.classList.remove("hidden");
        return;
    }

    const previousIndex = customModalState.originalIndex;
    closeCustomModal();

    const staleCards = openCards.filter(c => c.category === slug && (c.index === previousIndex || c.index === data.index));
    staleCards.forEach(c => closeCard(c.id));

    // Refresh the global index and category list
    await loadGlobalIndex();
    if (currentCategory === slug) {
        const catName = document.querySelector(`.tab-btn[data-slug="${slug}"]`)?.textContent || slug;
        await selectCategory(slug, catName);
    }
    // Open the new item
    openItemCard(slug, data.index);
}

// ===== UTILITY FUNCTIONS =====
function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

function propLine(label, value) {
    if (!value && value !== 0) return "";
    return `<div class="property-line"><span class="label">${escapeHtml(label)}: </span><span class="value">${value}</span></div>`;
}

function renderDesc(desc) {
    if (!desc) return "";
    if (typeof desc === "string") return `<div class="card-desc"><p>${processDesc(desc)}</p></div>`;
    if (Array.isArray(desc)) {
        return `<div class="card-desc">${desc.map(d => `<p>${processDesc(d)}</p>`).join("")}</div>`;
    }
    return "";
}

function processDesc(text) {
    if (!text) return "";
    // Escape HTML first
    let safe = escapeHtml(text);
    // Bold markdown-like patterns: **text**
    safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Italic: *text*
    safe = safe.replace(/\*(.+?)\*/g, "<em>$1</em>");
    return safe;
}

function refLink(ref) {
    if (!ref) return "";
    if (typeof ref === "string") return escapeHtml(ref);
    const name = escapeHtml(ref.name || ref.index || "");
    const index = ref.index;
    if (index && globalIndex[index]) {
        return `<span class="ref-link" onclick="showRefPopup('${escapeAttr(index)}')">${name}</span>`;
    }
    return name;
}

function refTag(ref) {
    if (!ref) return "";
    const name = escapeHtml(ref.name || ref.index || "");
    const index = ref.index;
    if (index && globalIndex[index]) {
        return `<span class="tag" onclick="showRefPopup('${escapeAttr(index)}')">${name}</span>`;
    }
    return `<span class="tag">${name}</span>`;
}

function escapeAttr(str) {
    return String(str).replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

function formatKey(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function renderKeyValueTable(keyLabel, valLabel, obj) {
    let h = `<table class="card-table"><tr><th>${escapeHtml(keyLabel)}</th><th>${escapeHtml(valLabel)}</th></tr>`;
    for (const [k, v] of Object.entries(obj)) {
        h += `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(String(v))}</td></tr>`;
    }
    h += `</table>`;
    return h;
}

// ===== DARK MODE =====
function toggleDarkMode() {
    const isDark = document.body.classList.toggle("dark-mode");
    localStorage.setItem("dnd-dark-mode", isDark ? "1" : "0");
    document.getElementById("dark-mode-btn").textContent = isDark ? "☀️" : "🌙";
}

function loadDarkMode() {
    const saved = localStorage.getItem("dnd-dark-mode");
    if (saved === "1") {
        document.body.classList.add("dark-mode");
        document.getElementById("dark-mode-btn").textContent = "☀️";
    }
}

// ===== SIDEBAR TOGGLE =====
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const btn = document.getElementById("sidebar-toggle-btn");
    sidebar.classList.toggle("collapsed");
    btn.classList.toggle("sidebar-hidden");
}

// ===== INITIATIVE PANEL RESIZE =====
function setupInitiativeResize() {
    const handle = document.getElementById("init-resize-handle");
    if (!handle) return;

    let startX, startWidth;

    handle.addEventListener("mousedown", (e) => {
        e.preventDefault();
        const panel = document.getElementById("initiative-panel");
        startX = e.clientX;
        startWidth = panel.offsetWidth;
        handle.classList.add("dragging");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";

        function onMouseMove(e) {
            const dx = startX - e.clientX; // dragging left increases width
            const mainContent = document.querySelector(".main-content");
            const maxWidth = mainContent.offsetWidth - 440; // leave room for at least one card
            let newWidth = startWidth + dx;
            if (newWidth < 380) newWidth = 380;
            if (newWidth > maxWidth) newWidth = maxWidth;
            panel.style.width = newWidth + "px";
        }

        function onMouseUp() {
            handle.classList.remove("dragging");
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
        }

        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
    });
}

// ===== INITIATIVE TRACKER =====
let initiativeRows = [];
let hpEditRowId = null;
let initIdCounter = 0;

// Conditions from the SRD
const CONDITIONS = [
    "", "Blinded", "Charmed", "Deafened", "Exhaustion",
    "Frightened", "Grappled", "Incapacitated", "Invisible",
    "Paralyzed", "Petrified", "Poisoned", "Prone",
    "Restrained", "Stunned", "Unconscious"
];

function toggleInitiativePanel() {
    const panel = document.getElementById("initiative-panel");
    const btn = document.getElementById("initiative-toggle-btn");
    panel.classList.toggle("hidden");
    btn.classList.toggle("active");
    setupInitiativeSearch();
}

function setupInitiativeSearch() {
    const input = document.getElementById("init-search");
    if (input._bound) return;
    input._bound = true;

    let debounce;
    input.addEventListener("input", () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => searchInitiativeItems(), 250);
    });
    input.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            document.getElementById("init-search-results").classList.add("hidden");
        }
    });
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".initiative-controls")) {
            document.getElementById("init-search-results").classList.add("hidden");
        }
    });
}

async function searchInitiativeItems() {
    const query = document.getElementById("init-search").value.trim();
    const resultsEl = document.getElementById("init-search-results");

    if (!query) {
        resultsEl.classList.add("hidden");
        return;
    }

    const res = await fetch(`/api/initiative-search?q=${encodeURIComponent(query)}`);
    const results = await res.json();

    resultsEl.innerHTML = "";
    if (results.length === 0) {
        resultsEl.innerHTML = '<div class="init-search-item"><span>No results</span></div>';
    } else {
        results.forEach(r => {
            const div = document.createElement("div");
            div.className = "init-search-item";
            div.innerHTML = `
                <span>${escapeHtml(r.name)} <small>(HP: ${r.hp}, AC: ${r.ac})</small></span>
                <span class="init-type-badge ${r.type}">${r.type}</span>
            `;
            div.addEventListener("click", () => {
                addToInitiative(r.name, r.hp, r.ac, r.type, r.index);
                resultsEl.classList.add("hidden");
                document.getElementById("init-search").value = "";
            });
            resultsEl.appendChild(div);
        });
    }
    resultsEl.classList.remove("hidden");
}

function addToInitiative(name, hp, ac, type, itemIndex) {
    initIdCounter++;
    const row = {
        id: initIdCounter,
        initiative: 0,
        name: name,
        currentHp: hp,
        maxHp: hp,
        ac: ac,
        condition: "",
        notes: "",
        type: type,
        itemIndex: itemIndex || null,
    };
    initiativeRows.push(row);
    renderInitiativeTable();
}

function renderInitiativeTable() {
    const tbody = document.getElementById("initiative-body");
    tbody.innerHTML = "";

    // Sort by initiative descending (highest first)
    const sorted = [...initiativeRows].sort((a, b) => b.initiative - a.initiative);

    sorted.forEach(row => {
        const tr = document.createElement("tr");

        // Initiative
        const tdInit = document.createElement("td");
        const initInp = document.createElement("input");
        initInp.type = "number";
        initInp.className = "init-input";
        initInp.value = row.initiative;
        initInp.addEventListener("change", (e) => {
            row.initiative = parseInt(e.target.value) || 0;
            renderInitiativeTable();
        });
        tdInit.appendChild(initInp);

        // Name
        const tdName = document.createElement("td");
        const nameSpan = document.createElement("span");
        nameSpan.className = `init-name is-${row.type}`;
        nameSpan.textContent = row.name;
        if (row.itemIndex) {
            const category = row.type === "character" ? "characters" : "monsters";
            nameSpan.classList.add("init-name-link");
            nameSpan.title = "Open item card";
            nameSpan.addEventListener("click", () => openItemCard(category, row.itemIndex));
        }
        tdName.appendChild(nameSpan);

        // HP
        const tdHp = document.createElement("td");
        const hpSpan = document.createElement("span");
        hpSpan.className = "hp-cell";
        if (row.currentHp <= 0) hpSpan.classList.add("dead");
        else if (row.currentHp <= row.maxHp / 2) hpSpan.classList.add("bloodied");
        hpSpan.textContent = `${row.currentHp}/${row.maxHp}`;
        hpSpan.addEventListener("click", () => openHpModal(row.id));
        tdHp.appendChild(hpSpan);

        // AC
        const tdAc = document.createElement("td");
        tdAc.textContent = row.ac;
        tdAc.style.textAlign = "center";

        // Condition
        const tdCond = document.createElement("td");
        const condSel = document.createElement("select");
        condSel.className = "init-condition-select";
        CONDITIONS.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c;
            opt.textContent = c || "—";
            if (c === row.condition) opt.selected = true;
            condSel.appendChild(opt);
        });
        condSel.addEventListener("change", (e) => { row.condition = e.target.value; });
        tdCond.appendChild(condSel);

        // Notes
        const tdNotes = document.createElement("td");
        tdNotes.className = "init-notes-cell";
        const notesInp = document.createElement("input");
        notesInp.type = "text";
        notesInp.className = "init-notes-input";
        notesInp.value = row.notes;
        notesInp.placeholder = "...";
        const notesTooltip = document.createElement("div");
        notesTooltip.className = "notes-tooltip" + (row.notes ? " has-content" : "");
        notesTooltip.textContent = row.notes;
        notesInp.addEventListener("input", (e) => {
            row.notes = e.target.value;
            notesTooltip.textContent = row.notes;
            notesTooltip.classList.toggle("has-content", !!row.notes);
        });
        tdNotes.appendChild(notesInp);
        tdNotes.appendChild(notesTooltip);

        // Delete
        const tdDel = document.createElement("td");
        const delBtn = document.createElement("button");
        delBtn.className = "init-del-btn";
        delBtn.textContent = "✕";
        delBtn.title = "Remove";
        delBtn.addEventListener("click", () => {
            initiativeRows = initiativeRows.filter(r => r.id !== row.id);
            renderInitiativeTable();
        });
        tdDel.appendChild(delBtn);

        tr.append(tdInit, tdName, tdHp, tdAc, tdCond, tdNotes, tdDel);
        tbody.appendChild(tr);
    });
}

function clearInitiative() {
    initiativeRows = [];
    initIdCounter = 0;
    renderInitiativeTable();
}

// ===== HP MODAL =====
function openHpModal(rowId) {
    hpEditRowId = rowId;
    const row = initiativeRows.find(r => r.id === rowId);
    if (!row) return;
    document.getElementById("hp-modal-title").textContent = `${row.name} — ${row.currentHp}/${row.maxHp} HP`;
    document.getElementById("hp-value").value = "";
    document.getElementById("hp-modal").classList.remove("hidden");
    document.getElementById("hp-modal-overlay").classList.remove("hidden");
    setTimeout(() => document.getElementById("hp-value").focus(), 100);
}

function closeHpModal() {
    document.getElementById("hp-modal").classList.add("hidden");
    document.getElementById("hp-modal-overlay").classList.add("hidden");
    hpEditRowId = null;
}

function applyHpChange() {
    const val = parseInt(document.getElementById("hp-value").value);
    if (isNaN(val)) { closeHpModal(); return; }

    const row = initiativeRows.find(r => r.id === hpEditRowId);
    if (!row) { closeHpModal(); return; }

    row.currentHp = row.currentHp - val;
    if (row.currentHp < 0) row.currentHp = 0;

    closeHpModal();
    renderInitiativeTable();
}

// Keyboard shortcut: Enter in HP modal
document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && hpEditRowId !== null && !document.getElementById("hp-modal").classList.contains("hidden")) {
        e.preventDefault();
        applyHpChange();
    }
});

// ===== CHARACTER MODAL =====
function openCharacterModal() {
    document.getElementById("char-name").value = "";
    document.getElementById("char-hp").value = "";
    document.getElementById("char-ac").value = "";
    document.getElementById("char-error").classList.add("hidden");
    document.getElementById("char-modal").classList.remove("hidden");
    document.getElementById("char-modal-overlay").classList.remove("hidden");
    setTimeout(() => document.getElementById("char-name").focus(), 100);
}

function closeCharacterModal() {
    document.getElementById("char-modal").classList.add("hidden");
    document.getElementById("char-modal-overlay").classList.add("hidden");
}

async function saveCharacter() {
    const name = document.getElementById("char-name").value.trim();
    const hp = parseInt(document.getElementById("char-hp").value);
    const ac = parseInt(document.getElementById("char-ac").value);
    const errorEl = document.getElementById("char-error");

    if (!name) {
        errorEl.textContent = "Name is required.";
        errorEl.classList.remove("hidden");
        return;
    }
    if (isNaN(hp) || hp < 0) {
        errorEl.textContent = "HP must be a non-negative number.";
        errorEl.classList.remove("hidden");
        return;
    }
    if (isNaN(ac) || ac < 0) {
        errorEl.textContent = "AC must be a non-negative number.";
        errorEl.classList.remove("hidden");
        return;
    }

    const res = await fetch("/api/character", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, hp, ac }),
    });

    const data = await res.json();
    if (!res.ok) {
        errorEl.textContent = data.error || "Failed to create character.";
        errorEl.classList.remove("hidden");
        return;
    }

    closeCharacterModal();
    // Add directly to initiative
    addToInitiative(name, hp, ac, "character", data.index);
    // Refresh global index
    await loadGlobalIndex();
}

// ===== FILTER SYSTEM =====
let _currentFilters = {};
let _currentFilterMeta = null;

async function loadFilters(slug) {
    const bar = document.getElementById('filter-bar');
    bar.innerHTML = '';
    bar.classList.remove('active');
    _currentFilters = {};
    _currentFilterMeta = null;

    if (slug !== 'spells' && slug !== 'monsters') return;

    try {
        const resp = await fetch(`/api/category/${slug}/filters`);
        if (!resp.ok) return;
        const meta = await resp.json();
        if (!meta || Object.keys(meta).length === 0) return;
        _currentFilterMeta = meta;
        renderFilterBar(slug, meta);
    } catch (e) {
        console.error('Failed to load filters', e);
    }
}

function renderFilterBar(slug, meta) {
    const bar = document.getElementById('filter-bar');
    bar.innerHTML = '';

    const filterLabels = {
        level: 'Spell Level',
        'class': 'Class',
        challenge_rating: 'Challenge Rating',
        type: 'Type',
        size: 'Size',
    };

    // Keys that support comparison operators
    const comparableKeys = { level: 'level_cmp', challenge_rating: 'cr_cmp', size: 'size_cmp' };

    for (const [key, options] of Object.entries(meta)) {
        const row = document.createElement('div');
        row.className = 'filter-row';

        const label = document.createElement('label');
        label.textContent = filterLabels[key] || key;
        label.setAttribute('for', `filter-${key}`);
        row.appendChild(label);

        const isComparable = key in comparableKeys;

        const select = document.createElement('select');
        select.id = `filter-${key}`;
        select.dataset.filterKey = key;

        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = 'All';
        select.appendChild(defaultOpt);

        for (const opt of options) {
            const o = document.createElement('option');
            o.value = opt.value;
            o.textContent = opt.label;
            select.appendChild(o);
        }

        select.addEventListener('change', () => {
            _currentFilters[key] = select.value;
            applyFilters(slug);
        });

        if (isComparable) {
            const cmpKey = comparableKeys[key];
            const wrapper = document.createElement('div');
            wrapper.className = 'filter-selects';

            const cmpSelect = document.createElement('select');
            cmpSelect.id = `filter-${cmpKey}`;
            cmpSelect.className = 'filter-cmp';
            cmpSelect.dataset.filterKey = cmpKey;
            [{v:'eq',l:'='},{v:'lt',l:'<'},{v:'gt',l:'>'}].forEach(op => {
                const o = document.createElement('option');
                o.value = op.v;
                o.textContent = op.l;
                cmpSelect.appendChild(o);
            });
            cmpSelect.addEventListener('change', () => {
                _currentFilters[cmpKey] = cmpSelect.value;
                applyFilters(slug);
            });

            select.className = 'filter-value';
            wrapper.appendChild(cmpSelect);
            wrapper.appendChild(select);
            row.appendChild(wrapper);
        } else {
            row.appendChild(select);
        }

        bar.appendChild(row);
    }

    const resetBtn = document.createElement('button');
    resetBtn.className = 'filter-reset';
    resetBtn.textContent = 'Reset filters';
    resetBtn.addEventListener('click', () => {
        _currentFilters = {};
        bar.querySelectorAll('select').forEach(s => s.value = '');
        applyFilters(slug);
    });
    bar.appendChild(resetBtn);

    bar.classList.add('active');
}

async function applyFilters(slug) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(_currentFilters)) {
        if (v !== '' && v !== undefined) params.set(k, v);
    }
    const url = `/api/category/${slug}?${params.toString()}`;
    try {
        const resp = await fetch(url);
        if (!resp.ok) return;
        const items = await resp.json();
        renderSidebarItems(items, slug);
    } catch (e) {
        console.error('Filter apply failed', e);
    }
}
