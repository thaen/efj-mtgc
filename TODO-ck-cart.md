# Plan: Card Kingdom Add-to-Cart Integration

## Goal
Enable single-click "add to cart" on Card Kingdom from our collection UI.

## Approach: Reverse-engineered CK Cart API (via go-mtgban)

The `go-mtgban` project has documented CK's internal cart endpoints:
- `POST` with `product_id`, `style`, `quantity` → returns cart state
- Requires CK product IDs (not Scryfall IDs or MTGJSON UUIDs)

## Steps

### 1. Map MTGJSON data to CK product IDs
- MTGJSON `purchaseUrls.cardKingdom` URLs contain CK product slugs (e.g. `/mtg/set-name/card-name`)
- We already have these URLs via `get_ck_url()` in pack_generator.py
- Parse the product slug from the URL, or check if MTGJSON stores a CK product ID directly in the `identifiers` block
- If not available in identifiers, we may need to scrape the product page for the numeric product ID

### 2. Proxy the CK cart API through our server
- Add a `/api/ck-cart/add` endpoint to crack_pack_server.py
- Accepts: `scryfall_id`, `finish` (to determine foil vs nonfoil)
- Looks up CK product ID, calls CK's internal cart endpoint
- Returns cart state to frontend
- Need to manage CK session cookies (cart is session-based)

### 3. Frontend: Add "Add to Cart" button
- In the card detail modal, add a "Add to CK Cart" button next to the Card Kingdom link
- On click, POST to our proxy endpoint
- Show success/failure feedback
- Optionally show running cart total

## Risks
- CK's internal API is undocumented and could change without notice
- Session/cookie management adds complexity
- CK product ID mapping may be incomplete
- Could violate CK's ToS

## Alternative: Deck Builder paste
- Less ambitious but more stable
- Add an "Export to CK Deck Builder" button that copies the card list to clipboard in CK's expected format
- User pastes into cardkingdom.com/builder manually
- No API risk, no session management
