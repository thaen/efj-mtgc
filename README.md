# MTG Collection Builder

A CLI + web UI tool for managing Magic: The Gathering card collections. Add cards by reading their corner info from photos (Claude Vision), full card photos (local OCR + Claude), or manual ID entry. Your collection is stored locally in SQLite and can be exported to Moxfield, Archidekt, or Deckbox. Includes a web UI for browsing your collection, cracking virtual booster packs, and image-based card ingestion.

## Features

- **Corner photo ingestion**: Photograph card corners and Claude Vision extracts rarity, collector number, set code, and foil status
- **Full card photo ingestion**: Upload full card images via the web UI — local OCR + Claude identifies card names
- **Manual ID entry**: Add cards directly by rarity/collector-number/set (no API key needed)
- **Bulk Scryfall caching**: Download all card data from Scryfall in 3 API calls for offline browsing
- **Web UI**: Browse collection, crack virtual booster packs, explore sheet layouts, ingest cards from images
- **Card lifecycle tracking**: Track card status (owned → ordered → listed → sold → removed) with audit log
- **Wishlist**: Track cards you want, with priority and price alerts
- **Local caching**: Scryfall data cached in SQLite to minimize API calls
- **Multi-platform import/export**: Moxfield, Archidekt, Deckbox CSV formats
- **Price data**: TCGplayer and CardKingdom prices via MTGJSON

## Quick Start

```bash
# Clone and setup
git clone https://github.com/thaen/efj-mtgc.git
cd efj-mtgc
uv sync

# Initialize database
mtg db init

# Add cards by ID (no API key needed)
mtg ingest-ids --id R 0200 EOE --id C 0075 EOE foil

# Or set your Anthropic API key and add cards from corner photos
export ANTHROPIC_API_KEY="sk-ant-..."
mtg ingest-corners ~/photos/corners.jpg

# Cache all Scryfall data for offline browsing
mtg cache all

# Start the web UI
mtg data fetch          # Download MTGJSON data (for booster packs)
mtg crack-pack-server   # Open http://localhost:8080

# See what you've got
mtg list
mtg stats

# Export to Moxfield
mtg export -f moxfield -o collection.csv
```

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management
- [Anthropic API key](https://console.anthropic.com/) (only needed for `ingest-corners` and OCR ingestion)

## Configuration

**API Key**: Set `ANTHROPIC_API_KEY` environment variable or add to your shell profile. Only required for photo-based ingestion commands.

**Database**: Default location is `~/.mtgc/collection.sqlite`. Override with:
- `--db /path/to/db.sqlite` flag
- `MTGC_DB` environment variable

**Data files**: Stored in `~/.mtgc/` (override with `MTGC_HOME` env):
- `collection.sqlite` — card collection database
- `AllPrintings.json` — MTGJSON card data (for booster simulation)
- `AllPricesToday.json` — MTGJSON price data

## Usage

### Ingest cards by ID

Add cards using their printed rarity letter, collector number, and set code. No Anthropic API key required.

```bash
mtg ingest-ids --id R 0200 EOE                        # Single card
mtg ingest-ids --id R 0200 EOE --id C 0075 EOE        # Multiple cards
mtg ingest-ids --id C 0187 EOE foil                    # Foil card
mtg ingest-ids --id P 0012 SPG --source "promo pack"   # With source tag
mtg ingest-ids --id R 0200 EOE --condition LP          # Set condition
```

Rarity codes: C (common), U (uncommon), R (rare), M (mythic), P (promo), L (land), T (token)

### Ingest cards from corner photos

Photograph the bottom-left corners of your cards. Claude Vision reads the rarity, collector number, set code, and foil status from the printed text.

```bash
mtg ingest-corners photo.jpg                           # Single photo
mtg ingest-corners *.jpg                               # Multiple photos
mtg ingest-corners photo.jpg --review                  # Review before adding
mtg ingest-corners photo.jpg --source "GP Vegas"       # Tag with source
mtg ingest-corners photo.jpg --condition LP            # Set condition
```

### Import/Export

```bash
# Import from other platforms
mtg import cards.csv                      # Auto-detect format
mtg import cards.csv -f moxfield          # Explicit format
mtg import cards.csv --dry-run            # Preview without saving

# Export to other platforms
mtg export -f moxfield -o collection.csv
mtg export -f archidekt -o collection.csv
mtg export -f deckbox -o collection.csv
mtg export -f moxfield --set DMU -o dmu.csv       # Filter by set
mtg export -f moxfield --name "Lightning" -o l.csv # Filter by name
```

### Browse and manage collection

```bash
# List and filter
mtg list                          # All cards (default limit: 50)
mtg list --set DMU                # By set
mtg list --name "Lightning"       # By name (partial match)
mtg list --foil                   # Only foils/etched
mtg list --nonfoil                # Only non-foils
mtg list --condition LP           # By condition
mtg list --source "GP Vegas"      # By source
mtg list --limit 100              # Change result limit
mtg list --offset 50              # Pagination

# View details
mtg show 42                       # Full details for entry #42

# Edit entries
mtg edit 42 --condition LP        # Update condition
mtg edit 42 --finish foil         # Update finish (nonfoil, foil, etched)
mtg edit 42 --price 5.99          # Set purchase price
mtg edit 42 --language Japanese   # Set language
mtg edit 42 --source "trade"      # Set source
mtg edit 42 --notes "SP card"     # Set notes
mtg edit 42 --tags "modern,staple" # Set tags
mtg edit 42 --tradelist 1         # Flag as tradelist (also: --alter, --proxy, --signed, --misprint)
mtg edit 42 --status sold         # Update status (owned/ordered/listed/sold/removed)

# Delete entries
mtg delete 42                     # Remove entry (with confirmation)
mtg delete 42 -y                  # Skip confirmation

# Stats
mtg stats                         # Collection summary
```

### Wishlist

```bash
mtg wishlist add "Lightning Bolt"             # Add by card name
mtg wishlist list                             # List all wishlist entries
mtg wishlist fulfill 1                        # Mark entry as fulfilled
mtg wishlist remove 1                         # Delete entry
```

### Caching and data management

```bash
# Cache all Scryfall card data (bulk download, 3 API calls)
mtg cache all                     # First run: downloads ~300MB, caches ~80k cards
mtg cache all                     # Subsequent: skips cached sets, processes only new ones
mtg cache all --force             # Reprocess all sets

# MTGJSON data (for booster pack simulation and prices)
mtg data fetch                    # Download AllPrintings.json
mtg data fetch-prices             # Download AllPricesToday.json

# Database management
mtg db init                       # Initialize database
mtg db init --force               # Recreate tables
mtg db refresh                    # Re-fetch Scryfall data for cached printings
mtg db refresh --all              # Refresh all printings
```

### Web UI

```bash
mtg crack-pack-server                        # Start on default port 8080
mtg crack-pack-server --port 3000            # Custom port
```

Pages available at `http://localhost:8080`:
- **Collection** (`/collection`) — Browse, filter, and manage your collection with grid/table views, set browsing, and "include unowned" mode
- **Crack-a-Pack** (`/crack`) — Virtual booster pack simulator with price data
- **Explore Sheets** (`/sheets`) — Browse booster sheet layouts by set and product type
- **Card Ingestor** (`/ingestor-ocr`) — Upload card images for OCR-based identification and collection entry

## Data Model

Each physical card you own is stored as a separate row with:

| Field | Description |
|-------|-------------|
| Printing | Scryfall ID linking to specific set/collector number |
| Status | owned, ordered, listed, sold, removed (with audit log) |
| Condition | Near Mint, Lightly Played, Moderately Played, Heavily Played, Damaged |
| Finish | nonfoil, foil, etched |
| Language | Default: English |
| Purchase price | Optional |
| Sale price | Optional (for sold cards) |
| Acquired date | Auto-set on import |
| Source | corner_ingest, manual_id, moxfield_import, etc. |
| Flags | tradelist, alter, proxy, signed, misprint |

## How It Works

1. **Card Identification**: Manual entry (rarity/CN/set), Claude Vision (corner photos), or local OCR + Claude (full card photos)
2. **Scryfall Lookup**: Cards resolved by set code + collector number via Scryfall API
3. **Local Caching**: Full card data cached in SQLite to avoid repeated API calls. `mtg cache all` bulk-caches all ~80k cards from Scryfall's bulk data endpoint.
4. **Collection Storage**: Cards added to your collection with finish, condition, source metadata, and lifecycle status tracking

## Development

```bash
uv sync                   # Install dependencies
uv run pytest             # Run tests (some require ANTHROPIC_API_KEY)
uv run ruff check mtg_collector/  # Lint
```

## License

MIT
