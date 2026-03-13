# Make J25: Generate Jumpstart Packs from Owned Cards

You (Claude) are the intended user of these scripts. You have poor memory between
conversations, so read this entire file before doing anything.

## What This Does

These scripts generate custom Jumpstart 2025-style 20-card packs using cards the
user actually owns. The process is: generate a pack "shape" (casting costs + types +
rarities), then fill each slot with a real card that fits the shape AND a chosen theme.

## The J25 Pack Formula

Every J25 pack follows this formula (derived from analyzing all 121 real J25 decks):

- **20 cards total**: 8-9 lands + 11-12 non-land spells
- **Lands**: 1 Thriving land (color-matched) + 6-7 basics + 0-1 special non-basic
- **Mono-colored** (all colored spells share one color; colorless artifacts OK)
- **Rarity**: 1-2 rare/mythic, 3-5 uncommon, rest common (among non-lands)
- **Creatures**: 5-8 creature-typed cards (usually 7-8)
- **Non-creature spells**: 3-7 (usually 4)
- **Curve**: MV 0 always empty. MV 2 and MV 3 always have at least 1 card each.
  MV 2+3 combined is 4-10 (usually 6-7). MV 5+ combined is 0-4.
- **Singletons**: all non-basic non-land cards appear once (one known exception)
- **No foils**

The sole exception to mono-color is the "Chaos" deck (5-color cascade).

## The Scripts

### 1. `generate_j25_shapes.py` — Generate a pack shape

Emits a list of card "shapes" (casting cost + type + rarity) for a random pack.

```bash
uv run python scripts/make_j25/generate_j25_shapes.py B          # black pack
uv run python scripts/make_j25/generate_j25_shapes.py W --seed 7 # reproducible
uv run python scripts/make_j25/generate_j25_shapes.py            # random color
```

Output looks like:
```
  [C] {B}           Creature
  [U] {1}{B}        Creature
  [R] {1}{B}{B}     Enchantment
  ...
```

### 2. `find_card_shape.py` — Find cards matching a shape

Query the local DB for cards fitting a shape. **Use `-o` to filter to owned cards.**

```bash
# Exact mana cost (preferred — matches the shape output):
uv run python scripts/make_j25/find_card_shape.py -k '{2}{B}' -r common -t Creature -o

# If exact cost returns 0 results, loosen to CMC + color:
uv run python scripts/make_j25/find_card_shape.py -m 3 -c B -r common -t Creature -o

# Flags:
#   -k / --cost    Exact mana cost string, e.g. '{1}{B}{B}'
#   -r / --rarity  common / uncommon / rare / mythic
#   -t / --type    Creature / Instant / Sorcery / Enchantment / Artifact / Planeswalker
#   -m / --cmc     Mana value (looser than --cost)
#   -c / --color   Color letter (looser than --cost)
#   -o / --owned   IMPORTANT: only show cards the user owns
#   --limit N      Max results (default 50)
```

### 3. `card_oracle.py` — Read a card's oracle text

```bash
uv run python scripts/make_j25/card_oracle.py "Soulless One"
```

### 4. `validate_j25_decks.py` — Validate real J25 decks

Runs the formula against all 121 J25 decks in AllPrintings.json. You probably don't
need this unless the formula is being updated.

```bash
uv run python scripts/make_j25/validate_j25_decks.py
```

### 5. `scryfall_deck_url.py` — View the deck on Scryfall

Generates a Scryfall search URL showing all cards in the deck, using the exact
printings the user owns. Prefers owned collection copies; falls back to most recent
paper printing.

```bash
uv run python scripts/make_j25/scryfall_deck_url.py \
    "Festering Mummy" "Tortured Existence" "Dregscape Zombie" \
    "Shepherd of Rot" "Withered Wretch" "Skirk Ridge Exhumer" \
    "Cadaver Imp" "Cadaverous Knight" "Phyrexian Arena" \
    "Buried Alive" "Soulless One" "Cruel Revival"

# Add --open to launch in the default browser:
uv run python scripts/make_j25/scryfall_deck_url.py --open "Card 1" "Card 2" ...
```

### 6. `insert_zombies_deck.py` — Example: insert a finished pack

Example script that inserts a completed pack as a hypothetical deck. Use this as a
template for new packs — copy it, rename it, change the card list and metadata.

```bash
uv run python scripts/make_j25/insert_zombies_deck.py
```

## How to Build a Pack (Step by Step)

YOU MUST FOLLOW THESE STEPS IN ORDER. Do not skip ahead.

### Step 1: Generate a shape

```bash
uv run python scripts/make_j25/generate_j25_shapes.py <COLOR>
```

If the shape looks bad (e.g. rare slot at MV 1 and the user has no owned rares there),
regenerate with a different `--seed`.

### Step 2: Choose a theme

Pick a creature type or mechanical theme that works in the chosen color. Easy themes:
- **Black**: Zombies, Vampires, Graveyard, Sacrifice
- **White**: Angels, Lifegain, Soldiers, Enchantments
- **Red**: Goblins, Burn, Dragons, Warriors
- **Green**: Elves, Beasts, Ramp, Dinosaurs
- **Blue**: Wizards, Flying, Card Draw, Bounce

### Step 3: Fill each slot, ONE AT A TIME

For each shape in the output, do this:

1. Run `find_card_shape.py` with the exact cost, rarity, type, and `-o`:
   ```bash
   uv run python scripts/make_j25/find_card_shape.py -k '{2}{B}' -r common -t Creature -o
   ```

2. If zero results, loosen the cost (try `-m` and `-c` instead of `-k`).
   A minor cost deviation (e.g. `{4}{B}` instead of `{3}{B}{B}`) is acceptable.

3. Scan the results for cards matching the theme (by name/type line).

4. For promising candidates, read the oracle text:
   ```bash
   uv run python scripts/make_j25/card_oracle.py "Card Name"
   ```

5. Pick the card. Move to the next slot.

**DO NOT** try to fill multiple slots at once. One card at a time. There are only
11-12 spell slots — it goes fast.

### Step 4: Preview on Scryfall

Pass all chosen card names to see the owned printings on Scryfall:

```bash
uv run python scripts/make_j25/scryfall_deck_url.py "Card 1" "Card 2" ...
```

Open the URL to visually verify the deck looks right.

### Step 5: Write an insert script

Copy `insert_zombies_deck.py` as a template. Change:
- `DECK_CARDS` list (the 12 card names)
- Deck name, description, origin_theme
- The description should summarize the theme and key synergies

### Step 6: Run the insert script

```bash
uv run python scripts/make_j25/insert_<theme>_deck.py
```

This creates a hypothetical deck visible in the web UI. The user can later toggle it
to a physical deck and assign real collection cards to it.
