# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Card Collection Builder - A Python CLI + web UI tool for managing Magic: The Gathering collections. Cards can be identified via Claude Vision (corner photos), local OCR (full card photos), or manual ID entry. Card data is sourced from Scryfall and stored in SQLite. Includes a web UI for collection browsing, virtual booster pack generation, and image-based card ingestion. Supports import/export to Moxfield, Archidekt, and Deckbox formats.

## Environment
- **Always use `uv`** for all Python operations (not pip/venv/make). Examples:
  - `uv sync` to install deps
  - `uv run pytest ...` to run tests
  - `uv run mtg ...` to run CLI

## Error Handling Philosophy
- **NEVER add fallback logic.** Errors should propagate to the user.
- No fallback content, no silent defaults, no swallowed exceptions.
- As few error paths as possible. Let it crash visibly.

## Commands

```bash
# Setup
uv sync

# Run tests (corner identification tests require ANTHROPIC_API_KEY)
uv run pytest                                # All tests
uv run pytest tests/test_ingest_ids.py -v    # Single test file
uv run pytest tests/test_ingest_ids.py::TestResolveAndAddIds::test_single_card_happy_path -v  # Single test

# Linting
uv run ruff check mtg_collector/

# CLI usage
mtg db init                                            # Initialize database
mtg ingest-ids --id R 0200 EOE --id C 0075 EOE foil   # Add cards by rarity/CN/set
mtg ingest-corners photo.jpg                           # Read card corners via Claude Vision
mtg cache all                                          # Bulk-cache all Scryfall data
mtg list                                               # List collection
mtg export -f moxfield -o out.csv
mtg crack-pack-server                                  # Start web UI on port 8080
```

## Architecture

```
mtg_collector/
├── cli/           # Subcommands, each with register(subparsers) and run(args)
│                  #   ingest_ids, ingest_corners, ingest_ocr, import_cmd, export,
│                  #   list_cmd, show, edit, delete, stats, db_cmd, cache_cmd,
│                  #   data_cmd, crack_pack, crack_pack_server, wishlist
├── db/            # SQLite layer (connection.py, schema.py, models.py with repositories)
├── services/      # claude.py (Vision API), scryfall.py (card data + caching),
│                  #   ocr.py (EasyOCR), pack_generator.py (MTGJSON booster sim)
├── static/        # Web UI: collection.html, crack_pack.html, explore_sheets.html, ingest.html
├── importers/     # CSV parsers for moxfield, archidekt, deckbox
└── exporters/     # CSV writers for moxfield, archidekt, deckbox
```

## Database Schema

Schema version tracked in `schema_version` table with auto-migrations (current: v8).

Core tables with foreign key relationships:
- `cards` (oracle_id PK) → Oracle-level card identity
- `sets` (set_code PK) → Set info + `cards_fetched_at` for cache status
- `printings` (scryfall_id PK) → Specific printings, FK to cards and sets
- `collection` (id PK) → Owned cards, FK to printings (one row per physical card). Status lifecycle: owned/ordered/listed/sold/removed
- `wishlist` (id PK) → Cards user wants, FK to cards (oracle-level) or printings (specific)
- `status_log` → Append-only audit trail of collection status changes
- `ingest_cache` (image_md5 PK) → Cached OCR + Claude results to avoid reprocessing
- `ingest_lineage` → Tracks which collection entry came from which image
- `settings` (key PK) → Global key-value config (e.g. price_sources, image_display)

Default location: `~/.mtgc/collection.sqlite` (override with `--db` or `MTGC_DB` env)

## Data Flow: Card Ingestion

Three ingestion methods, all resolve to the same pipeline:

1. **ingest-ids**: User provides rarity code, collector number, set code, and optional foil flag directly
2. **ingest-corners**: Claude Vision reads card corner text (rarity/CN/set/foil) from photos
3. **ingest-ocr** (web UI ingestor): EasyOCR extracts text, Claude identifies card names, Scryfall resolves

Methods 1 and 2 feed into `resolve_and_add_ids()` which:
1. Looks up printing in local cache, falls back to Scryfall API by set+collector number
2. Caches Scryfall data (card, set, printing) in SQLite
3. Creates collection entry with finish, condition, source metadata

## Web UI (crack_pack_server.py)

Threaded HTTP server serving static HTML pages and JSON APIs. Start with `mtg crack-pack-server`.

Key pages: `/collection` (browse/filter/manage collection), `/crack` (booster pack simulator), `/sheets` (explore booster sheet layouts), `/ingestor-ocr` (image-based card ingestion with SSE streaming).

Key API patterns:
- `/api/collection?[filters]` — aggregated collection with server-side sorting/filtering, include_unowned mode
- `/api/cached-sets` — all sets with cached card lists (for set filter dropdown)
- `/api/set-browse/{set_code}` — all printings in a set with owned/wanted annotations
- `/api/fetch-prices` (POST) — batch price lookup from Scryfall
- `/api/ingest/*` — stateful multi-step OCR ingestion workflow with SSE

## Key Implementation Details

- Scryfall API rate limited to 100ms between requests (via `_rate_limit()`)
- Claude API retries with exponential backoff (3s, 6s, 12s, 24s) but bails immediately on 400 errors
- JSON arrays stored as TEXT in SQLite (colors, finishes, promo_types)
- RARITY_MAP: C (common), U (uncommon), R (rare), M (mythic), P (promo), L (land, treated as common), T (token)
- Tests use a pre-populated `tests/fixtures/scryfall-cache.sqlite` for offline testing
- `mtg cache all` uses Scryfall bulk data endpoint (3 HTTP requests total) to cache all ~80k cards
- Price data comes from MTGJSON AllPricesToday.json (TCGplayer + CardKingdom), cached in memory with 24h TTL

## Web UI Shared Conventions (crack_pack.html)

- **Rarity/set border gradients**: Cards use CSS custom properties `--rarity-color` and `--set-color` with `linear-gradient(to bottom, ...)` to show rarity (top) and guest-set status (bottom). Shared JS helpers `getRarityColor(rarity)` and `getSetColor(cardSetCode, packSetCode)` return the colors. Use these for any new card display (lists, grids, etc.).
- **Badge builder**: `buildCardBadges(card, packSetCode)` returns HTML for SF/CK links with prices, foil, and treatment badges. `buildBadges(card, packSetCode)` wraps it with a zoom badge for the pack grid.
