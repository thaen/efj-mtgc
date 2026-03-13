#!/usr/bin/env python3
"""Validate Jumpstart 2025 decks against the identified pack formula.

J25 Pack Formula (derived from analysis of all 121 decks in MTGJSON):

UNIVERSAL RULES (all 121 decks):
  1.  Exactly 20 cards total
  2.  All cards in mainBoard (no commander, no sideboard)
  3.  No foil cards
  4.  8 or 9 lands
  5.  11 or 12 non-land cards (= 20 - lands)
  6.  1-2 rare/mythic among non-land cards
  7.  3-5 uncommon among non-land cards
  8.  Remaining non-lands are common (5-8)
  9.  All non-basic, non-land cards are singletons (count=1)

CREATURE / SPELL SPLIT:
  10. 5-8 creature-typed cards (including Artifact/Enchantment Creatures)
      - 8 creatures is dominant (77 decks), 7 (33), 6 (9), 5 (2)
  11. 3-7 non-creature spells
      - 4 spells is dominant (84 decks), 5 (25), 6 (9), 7 (2), 3 (1)
  12. For 9-land decks: almost always 7 creatures + 4 spells

MANA CURVE (non-land cards):
  13. MV 0: always 0 cards
  14. MV 1: 0-4 cards (0 in 18 decks, usually 1-2)
  15. MV 2: 1-6 cards (always at least 1, usually 3-4)
  16. MV 3: 1-5 cards (always at least 1, usually 3-4)
  17. MV 4: 0-4 cards (usually 1-2)
  18. MV 5: 0-3 cards (0 in 29 decks, usually 0-1)
  19. MV 6: 0-2 cards (0 in 68 decks)
  20. MV 7+: 0-2 cards (0 in 96 decks)
  21. MV 2+3 combined: 4-10 cards (usually 6-7, the core of the curve)
  22. MV 5+ combined: 0-4 cards (usually 1-2; Chaos is sole exception at 6)

MONO-COLOR RULES (120 of 121 decks; "Chaos" is the sole exception):
  23. All colored spells share exactly one color (colorless cards allowed)
  24. Exactly 1 Thriving land matching the deck's color
  25. All basic lands match the deck's color
  26. 0-1 additional non-basic, non-Thriving lands

CHAOS EXCEPTION (1 deck):
  - Multicolored (all 5 colors)
  - No Thriving land; uses 2 color-fixing lands (Ash Barrens, Terramorphic Expanse)
  - Mixed basic lands
"""

import json
import sys
from pathlib import Path

THRIVING_MAP = {
    "Thriving Heath": "W",
    "Thriving Isle": "U",
    "Thriving Moor": "B",
    "Thriving Bluff": "R",
    "Thriving Grove": "G",
}

COLOR_TO_BASIC = {
    "W": "Plains",
    "U": "Island",
    "B": "Swamp",
    "R": "Mountain",
    "G": "Forest",
}


def validate_deck(deck, cards_by_uuid):
    """Validate a single J25 deck. Returns list of failure strings (empty = pass)."""
    name = deck["name"]
    failures = []

    main = deck.get("mainBoard", [])
    commander = deck.get("commander", [])
    sideboard = deck.get("sideBoard", [])

    # Rule 2: no commander or sideboard
    if commander:
        failures.append(f"Has {len(commander)} commander entries")
    if sideboard:
        failures.append(f"Has {len(sideboard)} sideboard entries")

    # Categorize cards
    total = sum(e["count"] for e in main)
    lands = []
    nonlands = []

    for entry in main:
        card = cards_by_uuid.get(entry["uuid"], {})
        types = card.get("types", [])
        info = {
            "name": card.get("name", "?"),
            "count": entry["count"],
            "rarity": card.get("rarity", "?"),
            "types": types,
            "supertypes": card.get("supertypes", []),
            "colors": card.get("colors", []),
            "mana_value": int(card.get("manaValue", 0)),
            "is_foil": entry.get("isFoil", False),
        }
        if "Land" in types:
            lands.append(info)
        else:
            nonlands.append(info)

    # Rule 1: exactly 20 cards
    if total != 20:
        failures.append(f"Total cards = {total}, expected 20")

    # Rule 3: no foils
    for entry in main:
        if entry.get("isFoil", False):
            card = cards_by_uuid.get(entry["uuid"], {})
            failures.append(f"Foil card: {card.get('name', '?')}")

    land_count = sum(l["count"] for l in lands)
    nonland_count = sum(nl["count"] for nl in nonlands)

    # Rule 4: 8 or 9 lands
    if land_count not in (8, 9):
        failures.append(f"Land count = {land_count}, expected 8-9")

    # Rule 5: 11 or 12 non-lands
    if nonland_count not in (11, 12):
        failures.append(f"Non-land count = {nonland_count}, expected 11-12")

    # Rule 6: 1-2 rare/mythic among non-lands
    rm_count = sum(
        nl["count"] for nl in nonlands if nl["rarity"] in ("rare", "mythic")
    )
    if rm_count not in (1, 2):
        failures.append(f"Rare/mythic non-land count = {rm_count}, expected 1-2")

    # Rule 7: 3-5 uncommon among non-lands
    u_count = sum(nl["count"] for nl in nonlands if nl["rarity"] == "uncommon")
    if u_count not in (3, 4, 5):
        failures.append(f"Uncommon non-land count = {u_count}, expected 3-5")

    # Rule 8: common count check (5-8)
    c_count = sum(nl["count"] for nl in nonlands if nl["rarity"] == "common")
    if c_count not in range(5, 9):
        failures.append(f"Common non-land count = {c_count}, expected 5-8")

    # Rule 9: all non-basic, non-land cards are singletons
    for nl in nonlands:
        if nl["count"] > 1:
            failures.append(
                f"Non-singleton non-land: {nl['name']} x{nl['count']}"
            )

    # --- Creature / spell split ---

    creature_count = sum(
        nl["count"] for nl in nonlands if "Creature" in nl["types"]
    )
    spell_count = nonland_count - creature_count

    # Rule 10: 5-8 creatures
    if creature_count not in range(5, 9):
        failures.append(
            f"Creature count = {creature_count}, expected 5-8"
        )

    # Rule 11: 3-7 non-creature spells
    if spell_count not in range(3, 8):
        failures.append(
            f"Non-creature spell count = {spell_count}, expected 3-7"
        )

    # --- Mana curve ---

    curve = {}
    for mv_bucket in range(8):  # 0-6 individual, 7 = 7+
        curve[mv_bucket] = 0
    for nl in nonlands:
        mv = min(nl["mana_value"], 7)
        curve[mv] += nl["count"]

    # Rule 13: MV 0 always empty
    if curve[0] != 0:
        failures.append(f"MV 0 count = {curve[0]}, expected 0")

    # Rule 14: MV 1 range 0-4
    if curve[1] > 4:
        failures.append(f"MV 1 count = {curve[1]}, expected 0-4")

    # Rule 15: MV 2 at least 1, max 6
    if curve[2] < 1 or curve[2] > 6:
        failures.append(f"MV 2 count = {curve[2]}, expected 1-6")

    # Rule 16: MV 3 at least 1, max 5
    if curve[3] < 1 or curve[3] > 5:
        failures.append(f"MV 3 count = {curve[3]}, expected 1-5")

    # Rule 17: MV 4 range 0-4
    if curve[4] > 4:
        failures.append(f"MV 4 count = {curve[4]}, expected 0-4")

    # Rule 18: MV 5 range 0-3
    if curve[5] > 3:
        failures.append(f"MV 5 count = {curve[5]}, expected 0-3")

    # Rule 19: MV 6 range 0-2
    if curve[6] > 2:
        failures.append(f"MV 6 count = {curve[6]}, expected 0-2")

    # Rule 20: MV 7+ range 0-2
    if curve[7] > 2:
        failures.append(f"MV 7+ count = {curve[7]}, expected 0-2")

    # Rule 21: MV 2+3 combined 4-10
    mv23 = curve[2] + curve[3]
    if mv23 < 4 or mv23 > 10:
        failures.append(f"MV 2+3 combined = {mv23}, expected 4-10")

    # Rule 22: MV 5+ combined 0-4 (Chaos exception at 6)
    mv5plus = curve[5] + curve[6] + curve[7]
    is_chaos = name == "Chaos"
    if not is_chaos and mv5plus > 4:
        failures.append(f"MV 5+ combined = {mv5plus}, expected 0-4")

    # --- Mono-color rules ---

    spell_colors = set()
    for nl in nonlands:
        spell_colors.update(nl["colors"])

    if not is_chaos:
        # Rule 23: mono-colored
        if len(spell_colors) > 1:
            failures.append(
                f"Multi-colored spells: {sorted(spell_colors)} (not Chaos)"
            )
        elif len(spell_colors) == 0:
            failures.append("No colored spells found")

        deck_color = list(spell_colors)[0] if len(spell_colors) == 1 else None

        if deck_color:
            # Rule 24: exactly 1 Thriving land
            thriving = [l for l in lands if l["name"] in THRIVING_MAP]
            if len(thriving) != 1:
                failures.append(
                    f"Thriving land count = {len(thriving)}, expected 1"
                )
            elif THRIVING_MAP[thriving[0]["name"]] != deck_color:
                failures.append(
                    f"Thriving land {thriving[0]['name']} doesn't match "
                    f"deck color {deck_color}"
                )

            # Rule 25: basics match deck color
            expected_basic = COLOR_TO_BASIC[deck_color]
            for l in lands:
                if "Basic" in l["supertypes"]:
                    if l["name"] != expected_basic:
                        failures.append(
                            f"Wrong basic land: {l['name']} in {deck_color} deck"
                        )

            # Rule 26: 0-1 non-basic non-Thriving lands
            extra_nonbasics = [
                l
                for l in lands
                if "Basic" not in l["supertypes"]
                and l["name"] not in THRIVING_MAP
            ]
            if len(extra_nonbasics) > 1:
                names = [l["name"] for l in extra_nonbasics]
                failures.append(
                    f"Too many extra non-basic lands: {names} (expected 0-1)"
                )

    return failures


def main():
    allprintings = Path.home() / ".mtgc" / "AllPrintings.json"
    if not allprintings.exists():
        print(f"ERROR: {allprintings} not found. Run 'mtg data fetch' first.")
        sys.exit(1)

    print(f"Loading {allprintings}...")
    with open(allprintings) as f:
        data = json.load(f)

    j25 = data["data"].get("J25")
    if not j25:
        print("ERROR: J25 set not found in AllPrintings.json")
        sys.exit(1)

    decks = j25["decks"]
    cards_by_uuid = {c["uuid"]: c for c in j25["cards"]}

    print(f"Validating {len(decks)} J25 decks...\n")

    total_pass = 0
    total_fail = 0

    for deck in decks:
        failures = validate_deck(deck, cards_by_uuid)
        if failures:
            total_fail += 1
            print(f"FAIL: {deck['name']}")
            for f in failures:
                print(f"  - {f}")
        else:
            total_pass += 1

    print(f"\n{'='*50}")
    print(f"Results: {total_pass} passed, {total_fail} failed out of {len(decks)}")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
