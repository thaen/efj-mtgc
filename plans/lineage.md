# Plan: Full card lineage on correct.html

## Goal

The correct.html page currently shows ingest lineage only (the photo a card was identified from). It should show the full story of how a card entered and moved through a user's collection — "lineage" means all information the system has about a card's lifecycle.

## What lineage should include

- **Wishlist**: Was this card on the wishlist before it was acquired? When was it added?
- **Purchase**: Which order was it part of? Seller name, order number, purchase date, price paid. (TCGPlayer / Card Kingdom tracking already exists via `orders` table and `collection.order_id` FK)
- **Ingest source**: How was the card identified?
  - Photo ingestion (ingest2): link to the source image, OCR text, Claude identification, disambiguation choice
  - Corner ingestion: original corner photo
  - Manual ID entry: who entered it and when
  - Order import: parsed from which order file
- **Status history**: The full status lifecycle from `status_log` — ordered, owned, listed, sold, removed — with timestamps
- **Corrections**: Was the card ever corrected/re-identified on the correct page?

## Example narrative

> Wishlisted on 2026-01-15. Purchased from StarCityGames (Order #12345) on 2026-01-20 for $3.50. Identified via photo ingestion from camera_2026-01-20.jpg. Corrected from "Angel of Mercy (6ED)" to "Angel of Mercy (IMA)" on 2026-01-21.

## Data sources

- `wishlist` table — wishlist history (oracle-level or printing-level)
- `orders` table + `collection.order_id` — purchase tracking
- `ingest_lineage` + `ingest_images` — photo ingestion source
- `ingest_cache` — OCR and Claude results for the source image
- `status_log` — append-only audit trail of status changes
- `collection` — source field, created_at, condition, finish

## Open questions

- Should lineage be read-only or should corrections/edits also be possible from this view?
- How to handle cards with no ingest lineage (e.g., imported from CSV)?
- Should the page be renamed from "correct" to "lineage" or keep both functions?
