# efj notes

* normalize set_code?
* indexes on set_code, is_full_art, maybe some others
* open question 3: uh, 1.5gb is nothing.

# DB Plan: Migrate MTGJSON Data into SQLite

## Problem

AllPrintings.json (~1.5 GB) and AllPricesToday.json (~500 MB) are loaded into memory and scanned repeatedly to build ad-hoc indexes. Every new lookup pattern means another dict built from a full scan. The collection API does SQL for card data, then loops through results doing JSON dict lookups for prices and CK URLs. This is slow at startup, wastes memory, and makes queries that should be simple JOINs into awkward two-phase operations.

## Goals

1. All card/printing/price/URL data queryable via SQL JOINs
2. Collection queries don't need post-hoc Python loops for prices or links
3. Prices updatable independently (daily) without re-importing all card data
4. User collection data stays cleanly separated from external reference data
5. Pack generation still works (booster sheet weights, slot definitions)

## New Tables

### `mtgjson_printings` — one row per MTGJSON card (immutable reference data)

Imported from AllPrintings.json. This is the MTGJSON view of a printing, complementing the Scryfall-sourced `printings` table.

```sql
CREATE TABLE mtgjson_printings (
    uuid            TEXT PRIMARY KEY,   -- MTGJSON UUID
    scryfall_id     TEXT,               -- links to printings.scryfall_id
    name            TEXT NOT NULL,
    set_code        TEXT NOT NULL,      -- uppercase
    number          TEXT NOT NULL,      -- collector number
    rarity          TEXT,
    border_color    TEXT,
    is_full_art     INTEGER DEFAULT 0,
    frame_effects   TEXT,               -- JSON array
    ck_url          TEXT,               -- purchaseUrls.cardKingdom
    ck_url_foil     TEXT,               -- purchaseUrls.cardKingdomFoil
    tcg_url         TEXT,               -- purchaseUrls.tcgplayer
    imported_at     TEXT NOT NULL        -- ISO 8601
);
CREATE INDEX idx_mtgjson_scryfall ON mtgjson_printings(scryfall_id);
CREATE INDEX idx_mtgjson_set ON mtgjson_printings(set_code);
```

### `mtgjson_booster_sheets` — booster slot definitions

```sql
CREATE TABLE mtgjson_booster_sheets (
    id          INTEGER PRIMARY KEY,
    set_code    TEXT NOT NULL,       -- uppercase
    product     TEXT NOT NULL,       -- "play", "draft", "collector", etc.
    sheet_name  TEXT NOT NULL,       -- "common", "uncommon", "rare_mythic", etc.
    is_foil     INTEGER DEFAULT 0,
    uuid        TEXT NOT NULL,       -- MTGJSON card UUID
    weight      INTEGER NOT NULL,    -- card weight within this sheet
    FOREIGN KEY (uuid) REFERENCES mtgjson_printings(uuid)
);
CREATE INDEX idx_booster_set_product ON mtgjson_booster_sheets(set_code, product);
```

### `mtgjson_booster_configs` — booster variant definitions

```sql
CREATE TABLE mtgjson_booster_configs (
    id          INTEGER PRIMARY KEY,
    set_code    TEXT NOT NULL,
    product     TEXT NOT NULL,
    variant_weight INTEGER NOT NULL,    -- weight for this variant
    sheet_name  TEXT NOT NULL,          -- which sheet
    card_count  INTEGER NOT NULL,       -- how many cards from this sheet
    source_set  TEXT                    -- from sourceSetCodes (NULL = same set)
);
CREATE INDEX idx_config_set_product ON mtgjson_booster_configs(set_code, product);
```

### `prices` — latest prices only (refreshed daily)

```sql
CREATE TABLE prices (
    uuid        TEXT NOT NULL,       -- MTGJSON UUID
    provider    TEXT NOT NULL,       -- "cardkingdom", "tcgplayer"
    finish      TEXT NOT NULL,       -- "normal", "foil"
    price       TEXT NOT NULL,       -- price as string (preserves original precision)
    price_date  TEXT NOT NULL,       -- date of this price point
    PRIMARY KEY (uuid, provider, finish),
    FOREIGN KEY (uuid) REFERENCES mtgjson_printings(uuid)
);
```

Only the latest price per (uuid, provider, finish) is stored. History is not needed — AllPricesToday.json has a few days of trailing data, but we only use `max(date)`.

## Data Separation

```
External reference data (replaceable, re-importable):
├── mtgjson_printings      — card metadata from MTGJSON
├── mtgjson_booster_sheets — booster weights
├── mtgjson_booster_configs — booster structures
└── prices                 — daily price snapshots

Scryfall cache (on-demand, append-only):
├── cards      — oracle-level identity
├── sets       — set metadata
└── printings  — printing details + raw_json

User data (precious, never auto-modified):
├── collection      — owned cards
├── ingest_cache    — OCR/Claude results
├── ingest_lineage  — provenance tracking
└── settings        — preferences
```

External reference tables can be dropped and re-imported at any time with no data loss. User data is never touched by the import process.

## Commands

### `mtg data import` (new)

Run after `mtg data fetch`. Reads AllPrintings.json and populates `mtgjson_printings`, `mtgjson_booster_sheets`, `mtgjson_booster_configs`.

- Drops and recreates the three tables (idempotent full replace)
- Streams the JSON to avoid loading the full file into a Python dict if possible (though with 1.5GB it may just need the memory during import)
- Reports progress: set count, card count, time elapsed

### `mtg data import-prices` (new)

Run after `mtg data fetch-prices`. Reads AllPricesToday.json and populates `prices`.

- Drops and recreates the `prices` table (idempotent full replace)
- For each (uuid, provider, finish), stores only the latest date's price
- Fast: just extract latest price per key, no historical accumulation

### Modified: `mtg data fetch` / `mtg data fetch-prices`

After downloading, automatically run the corresponding import step. The JSON files can be kept or deleted after import — keeping them costs disk but allows re-import without re-download.

## Query Changes

### Collection API (`/api/collection`)

Before:
```python
# SQL query for card data
# Then loop: for each card, look up uuid in Python dict, then price in another dict
uuid = self.generator.get_uuid_for_scryfall_id(card["scryfall_id"])
card["ck_price"] = _get_ck_price(uuid, foil)
card["ck_url"] = self.generator.get_ck_url(card["scryfall_id"], foil)
```

After:
```sql
SELECT ...,
    mp.ck_url, mp.ck_url_foil,
    pr_ck.price AS ck_price,
    pr_tcg.price AS tcg_price
FROM collection c
JOIN printings p ON c.scryfall_id = p.scryfall_id
JOIN cards card ON p.oracle_id = card.oracle_id
JOIN sets s ON p.set_code = s.set_code
LEFT JOIN mtgjson_printings mp ON p.scryfall_id = mp.scryfall_id
LEFT JOIN prices pr_ck ON mp.uuid = pr_ck.uuid
    AND pr_ck.provider = 'cardkingdom'
    AND pr_ck.finish = CASE WHEN c.finish IN ('foil','etched') THEN 'foil' ELSE 'normal' END
LEFT JOIN prices pr_tcg ON mp.uuid = pr_tcg.uuid
    AND pr_tcg.provider = 'tcgplayer'
    AND pr_tcg.finish = CASE WHEN c.finish IN ('foil','etched') THEN 'foil' ELSE 'normal' END
```

No more Python loops. No more in-memory price dicts. No more Scryfall bulk price API calls.

### Pack Generation

PackGenerator switches from scanning AllPrintings.json in memory to SQL queries:
- `generate_pack(set_code, product)`: query `mtgjson_booster_configs` for structure, `mtgjson_booster_sheets` for weighted random selection, `mtgjson_printings` for card data
- Sheet data for the grid view: same tables, no in-memory card indexes

### Sheets / Explore

Same pattern — SQL queries with JOINs replace in-memory dict scans.

## Migration Path

1. Add new tables to schema.py (schema version bump)
2. Implement `mtg data import` and `mtg data import-prices` commands
3. Update `mtg data fetch` / `fetch-prices` to auto-import after download
4. Update collection API to use SQL JOINs for prices/URLs
5. Update PackGenerator to query SQLite instead of loading AllPrintings.json
6. Update crack_pack_server.py price lookups to use `prices` table
7. Remove in-memory index building code (`_scryfall_to_uuid`, `_scryfall_to_card`, `_card_indexes`, `_prices_data`)
8. Remove or deprecate AllPrintings.json loading in PackGenerator.__init__

Steps 1-3 can land first (additive, nothing breaks). Steps 4-7 can land together as one migration. Step 8 is cleanup.

## What This Doesn't Change

- Scryfall on-demand caching still works as-is (the `cards`/`sets`/`printings` tables stay)
- Scryfall remains the authority for card metadata during ingestion
- The two data sources coexist: MTGJSON for prices/URLs/boosters, Scryfall for card identity/images
- `ingest_cache` and `ingest_lineage` unchanged
- All existing CLI commands work the same

## Open Questions

- **Delete JSON after import?** Keeping them allows re-import without re-download, but wastes ~2GB disk. Could offer `--keep-json` flag, default to delete.
- **Merge `mtgjson_printings` into `printings`?** They share `scryfall_id` and overlap on some fields (name, set, rarity). Merging would simplify JOINs but mix Scryfall-sourced and MTGJSON-sourced data in one table. Keeping them separate is cleaner and lets either be rebuilt independently.
- **Stream the JSON import?** Python's `json.load()` on a 1.5GB file will use significant memory. Could use `ijson` for streaming, but adds a dependency. Probably fine to just load it — it's a one-time import step, not a per-request cost.
