# D&D 5e SRD Library

A local offline Flask application serving Dungeons & Dragons 5th Edition SRD data from JSON files. The app provides a web UI and a simple REST API for browsing categories, items, searching, and resolving cross-references.

## Features

- Serves SRD category data from `data/2014/` JSON files
- Provides a web interface at `/`
- API endpoints for categories, category items, specific items, search, and item resolution
- Supports adding custom items via API

## Requirements

- Python 3.10+ (or compatible Python 3)
- `Flask`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the application

From the project root:

```bash
python src/dnd_lib/app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## API Endpoints

- `GET /api/categories` — list all available categories
- `GET /api/category/<slug>` — list items in a category
- `GET /api/item/<slug>/<item_index>` — get full item data
- `GET /api/resolve/<item_index>` — resolve an item index to its category and name
- `GET /api/search?q=<query>&category=<slug>` — search across SRD data
- `POST /api/custom/<slug>` — add a custom item to a category

## Data Structure

The app loads JSON files from `data/2014/` using the slug-to-filename mapping in `src/dnd_lib/app.py`.

Example file names:

- `5e-SRD-Classes.json`
- `5e-SRD-Spells.json`
- `5e-SRD-Monsters.json`

## Notes

- The server is run in debug mode by default when launched directly.
- Custom items are persisted back into the JSON files and are marked with `_custom: true`.

## License

Project files are under the repository owner’s license.
