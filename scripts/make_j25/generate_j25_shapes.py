#!/usr/bin/env python3
"""Generate a random Jumpstart 2025 pack as a list of card shapes.

A "card shape" is a casting cost + card type, e.g. "{2}{W} Creature".

Usage:
    uv run python scripts/generate_j25_shapes.py          # random color
    uv run python scripts/generate_j25_shapes.py W        # white
    uv run python scripts/generate_j25_shapes.py --seed 42 G   # reproducible
"""

import argparse
import random
import sys

# Observed distributions from J25 analysis (weights for random selection)

# 8 lands: 112 decks, 9 lands: 9 decks (excluding Chaos)
LAND_COUNT_WEIGHTS = {8: 112, 9: 9}

# Creature count distribution (for 12-nonland / 11-nonland decks)
CREATURE_COUNT_12 = {8: 76, 7: 25, 6: 9, 5: 2}
CREATURE_COUNT_11 = {7: 8, 8: 1}  # 9-land decks

# Rare/mythic count among non-lands
RM_COUNT_WEIGHTS = {1: 81, 2: 40}

# Uncommon count among non-lands (for 12-nonland decks, most common combos)
U_COUNT_WEIGHTS = {4: 99, 5: 10, 3: 12}

# MV distributions (observed counts across 121 decks, used as weights)
MV_WEIGHTS = {
    1: {0: 18, 1: 36, 2: 49, 3: 16, 4: 2},
    2: {1: 3, 2: 13, 3: 50, 4: 30, 5: 21, 6: 4},
    3: {1: 1, 2: 26, 3: 47, 4: 38, 5: 9},
    4: {0: 2, 1: 43, 2: 55, 3: 19, 4: 2},
    5: {0: 29, 1: 62, 2: 27, 3: 3},
    6: {0: 68, 1: 46, 2: 7},
    7: {0: 96, 1: 19, 2: 6},
}

# Non-creature spell type weights (from observed data)
SPELL_TYPE_WEIGHTS = {
    "Instant": 2.2,
    "Sorcery": 1.0,
    "Enchantment": 0.8,
    "Artifact": 0.4,
}

COLOR_SYMBOLS = {"W": "W", "U": "U", "B": "B", "R": "R", "G": "G"}
COLOR_NAMES = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}

THRIVING_NAMES = {
    "W": "Thriving Heath",
    "U": "Thriving Isle",
    "B": "Thriving Moor",
    "R": "Thriving Bluff",
    "G": "Thriving Grove",
}

BASIC_NAMES = {
    "W": "Plains",
    "U": "Island",
    "B": "Swamp",
    "R": "Mountain",
    "G": "Forest",
}


def weighted_choice(weights_dict):
    """Pick a key from {value: weight} dict."""
    keys = list(weights_dict.keys())
    weights = [weights_dict[k] for k in keys]
    return random.choices(keys, weights=weights, k=1)[0]


def generate_mana_curve(nonland_count):
    """Generate a valid mana curve that sums to nonland_count."""
    for _ in range(1000):
        curve = {}
        curve[0] = 0
        for mv in range(1, 8):
            curve[mv] = weighted_choice(MV_WEIGHTS[mv])

        total = sum(curve.values())
        if total != nonland_count:
            continue

        # Validate constraints
        if curve[2] < 1 or curve[3] < 1:
            continue
        mv23 = curve[2] + curve[3]
        if mv23 < 4 or mv23 > 10:
            continue
        mv5plus = curve[5] + curve[6] + curve[7]
        if mv5plus > 4:
            continue

        return curve

    raise RuntimeError("Failed to generate valid mana curve after 1000 attempts")


def make_mana_cost(mv, color, is_colorless=False):
    """Generate a casting cost string for a given mana value and color."""
    if is_colorless:
        return f"{{{mv}}}"

    c = f"{{{color}}}"

    if mv == 0:
        return "{0}"
    if mv == 1:
        return c

    # Decide number of colored pips: 1 or 2
    # Higher MV cards are more likely to have 1 pip; lower MV more likely 2
    if mv == 2:
        pips = random.choices([1, 2], weights=[75, 25])[0]
    elif mv <= 4:
        pips = random.choices([1, 2], weights=[65, 35])[0]
    else:
        pips = random.choices([1, 2], weights=[80, 20])[0]

    generic = mv - pips
    colored = c * pips

    if generic > 0:
        return f"{{{generic}}}{colored}"
    return colored


def generate_pack(color):
    """Generate a J25 pack as a list of card shape dicts."""
    # Pick land count
    land_count = weighted_choice(LAND_COUNT_WEIGHTS)
    nonland_count = 20 - land_count

    # Pick creature/spell split
    if nonland_count == 12:
        creature_count = weighted_choice(CREATURE_COUNT_12)
    else:
        creature_count = weighted_choice(CREATURE_COUNT_11)
    spell_count = nonland_count - creature_count

    # Pick rarity distribution
    rm_count = weighted_choice(RM_COUNT_WEIGHTS)
    u_count = weighted_choice(U_COUNT_WEIGHTS)
    c_count = nonland_count - rm_count - u_count

    # Clamp if needed
    if c_count < 5:
        u_count = nonland_count - rm_count - 5
        c_count = 5
    if c_count > 8:
        u_count = nonland_count - rm_count - 8
        c_count = 8

    # Generate mana curve
    curve = generate_mana_curve(nonland_count)

    # Assign MVs to cards
    mv_pool = []
    for mv, count in sorted(curve.items()):
        mv_pool.extend([mv] * count)
    random.shuffle(mv_pool)

    # Assign types: first creature_count are creatures, rest are spells
    # But sort so higher-MV cards are more likely creatures (big beaters)
    # Actually keep it random - the data shows no strong MV/type correlation
    cards = []

    # Build rarity pool
    rarities = []
    for _ in range(rm_count):
        rarities.append(random.choice(["rare", "mythic"]) if random.random() < 0.2 else "rare")
    rarities.extend(["uncommon"] * u_count)
    rarities.extend(["common"] * c_count)
    random.shuffle(rarities)

    # Decide which spells are which type
    spell_types = []
    types_pool = list(SPELL_TYPE_WEIGHTS.keys())
    type_weights = list(SPELL_TYPE_WEIGHTS.values())
    for _ in range(spell_count):
        spell_types.append(random.choices(types_pool, weights=type_weights, k=1)[0])

    # Build card list
    for i in range(nonland_count):
        mv = mv_pool[i]
        rarity = rarities[i]

        if i < creature_count:
            card_type = "Creature"
            is_colorless = False
        else:
            card_type = spell_types[i - creature_count]
            # Artifacts can be colorless
            is_colorless = card_type == "Artifact"

        cost = make_mana_cost(mv, color, is_colorless)

        cards.append({
            "cost": cost,
            "type": card_type,
            "rarity": rarity,
            "mv": mv,
        })

    # Sort by MV for readability
    cards.sort(key=lambda c: (c["mv"], c["type"]))

    # Build land list
    land_cards = []
    basic_count = land_count - 1  # 1 Thriving land
    has_extra_nonbasic = random.random() < 0.25  # ~25% of decks have one
    if has_extra_nonbasic:
        basic_count -= 1
        land_cards.append({
            "cost": "",
            "type": "Land (nonbasic)",
            "rarity": random.choice(["common", "uncommon"]),
            "mv": 0,
        })

    land_cards.append({
        "cost": "",
        "type": f"Land ({THRIVING_NAMES[color]})",
        "rarity": "common",
        "mv": 0,
    })
    land_cards.append({
        "cost": "",
        "type": f"Land ({BASIC_NAMES[color]} x{basic_count})",
        "rarity": "common",
        "mv": 0,
    })

    return cards, land_cards


def rarity_code(r):
    return {"common": "C", "uncommon": "U", "rare": "R", "mythic": "M"}[r]


def main():
    parser = argparse.ArgumentParser(description="Generate a J25 pack shape list")
    parser.add_argument("color", nargs="?", choices=["W", "U", "B", "R", "G"],
                        help="Color (W/U/B/R/G). Random if omitted.")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    color = args.color or random.choice(["W", "U", "B", "R", "G"])

    cards, land_cards = generate_pack(color)

    print(f"J25 Pack Shape — {COLOR_NAMES[color]}")
    print(f"{'=' * 40}")
    print()

    creature_count = sum(1 for c in cards if c["type"] == "Creature")
    spell_count = len(cards) - creature_count
    print(f"Spells ({len(cards)} cards: {creature_count} creatures, {spell_count} non-creature)")
    print(f"{'-' * 40}")

    for card in cards:
        rc = rarity_code(card["rarity"])
        print(f"  [{rc}] {card['cost']:12s}  {card['type']}")

    print()
    print(f"Lands")
    print(f"{'-' * 40}")
    for land in land_cards:
        rc = rarity_code(land["rarity"])
        print(f"  [{rc}] {land['type']}")

    # Summary
    print()
    curve_str = "  ".join(
        f"MV{mv}:{sum(1 for c in cards if c['mv'] == mv)}"
        for mv in range(8)
        if sum(1 for c in cards if c['mv'] == mv) > 0
    )
    print(f"Curve: {curve_str}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
