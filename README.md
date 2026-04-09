# D&D 5e SRD Library

A local offline Flask application serving Dungeons & Dragons 5th Edition SRD data from JSON files. The app provides a web UI styled after classic D&D stat blocks, with a REST API for browsing categories, items, searching, and resolving cross-references.

## Features

- **Offline SRD Browser** — Serves all SRD category data from `data/2014/` JSON files
- **D&D-styled cards** — Stat blocks for monsters, spells, equipment, classes, races, and more
- **Search** — Global search bar with optional category filter
- **Category tabs** — Browse items by category with a collapsible sidebar (toggle with ☰ button)
- **Cross-references** — Clickable links between items open floating popups
- **Multiple cards** — Open several item cards side by side in the main panel
- **Monster spellcasting** — Spells grouped by level with clickable spell links
- **Custom items** — Add custom items to any category; characters use a simplified name/HP/AC form
- **Initiative Tracker** — Right-side panel for combat tracking:
  - Search and add monsters or characters to the initiative table
  - Columns: Initiative, Name, HP, AC, Condition, Notes
  - Click HP to apply damage (subtracted from current HP)
  - Initiative auto-sorts highest first
  - Conditions dropdown with all SRD conditions
  - Panel is resizable by dragging the left edge
- **Dark mode** — Toggle with the 🌙 button; preference saved to localStorage
- **JSON viewer** — View raw JSON for any item card

## Requirements

- Python 3.10+
- Flask

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the application

```bash
python src/dnd_lib/app.py
```

Then open http://127.0.0.1:5000

## API Endpoints

- `GET /api/categories` — list all available categories
- `GET /api/category/<slug>` — list items in a category
- `GET /api/item/<slug>/<item_index>` — get full item data
- `GET /api/resolve/<item_index>` — resolve an item index to its category
- `GET /api/search?q=<query>&category=<slug>` — search across SRD data
- `GET /api/initiative-search?q=<query>` — search monsters and characters for initiative tracker
- `POST /api/custom/<slug>` — add a custom item to a category (JSON body)
- `POST /api/character` — create a character with `{name, hp, ac}`

## Data Structure

The app loads JSON files from `data/2014/`. Categories include Classes, Spells, Monsters, Equipment, Magic Items, Races, Feats, Features, Conditions, Skills, Traits, Characters, and more.

## Notes

- The server runs in debug mode by default when launched directly.
- Custom items are persisted into the JSON files and marked with `_custom: true`.
- Characters are stored in `5e-SRD-Characters.json`.

## License

Project files are under the repository owner’s license.
