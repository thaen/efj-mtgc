#!/usr/bin/env python3
"""Find cards in the local DB matching a card shape (rarity, mana cost, type).

Usage:
    uv run python scripts/find_card_shape.py --cost '{2}{W}' --rarity rare --type Creature
    uv run python scripts/find_card_shape.py -k '{1}{R}' -r common -t Instant
    uv run python scripts/find_card_shape.py -k '{3}' -t Artifact -r uncommon
    uv run python scripts/find_card_shape.py -k '{2}{W}{W}' -t Creature --limit 20

All flags are optional filters — omit any to leave it unconstrained.
At least one filter is required.
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def get_db_path():
    env = os.environ.get("MTGC_DB")
    if env:
        return env
    return str(Path.home() / ".mtgc" / "collection.sqlite")


def build_query(args):
    """Build SQL query and params from CLI args."""
    conditions = []
    params = []

    # Only paper cards from non-digital sets
    conditions.append("s.digital = 0")

    if args.cost:
        conditions.append("c.mana_cost = ?")
        params.append(args.cost)

    if args.rarity:
        conditions.append("p.rarity = ?")
        params.append(args.rarity.lower())

    if args.type:
        type_map = {
            "creature": "Creature",
            "instant": "Instant",
            "sorcery": "Sorcery",
            "enchantment": "Enchantment",
            "artifact": "Artifact",
            "planeswalker": "Planeswalker",
        }
        card_type = type_map.get(args.type.lower(), args.type)
        # Front face contains the type (handles MDFCs/adventures)
        conditions.append(
            "(c.type_line LIKE ? AND c.type_line NOT LIKE '%//%' || ? || '%')"
        )
        params.append(f"%{card_type}%")
        params.append(card_type)

    if args.cmc is not None:
        conditions.append("c.cmc = ?")
        params.append(float(args.cmc))

    if args.color:
        color = args.color.upper()
        if args.type and args.type.lower() == "artifact":
            conditions.append(
                "(c.colors = ? OR c.colors = '[]' OR c.colors IS NULL)"
            )
            params.append(f'["{color}"]')
        else:
            conditions.append("c.colors = ?")
            params.append(f'["{color}"]')

    if args.owned:
        conditions.append(
            "EXISTS (SELECT 1 FROM collection col WHERE col.printing_id = p.printing_id AND col.status = 'owned')"
        )

    where = " AND ".join(conditions)

    query = f"""
        SELECT DISTINCT c.name, c.mana_cost, c.type_line, c.cmc, p.rarity
        FROM cards c
        JOIN printings p ON p.oracle_id = c.oracle_id
        JOIN sets s ON s.set_code = p.set_code
        WHERE {where}
        GROUP BY c.oracle_id
        ORDER BY c.name
    """

    if args.limit:
        query += f" LIMIT {int(args.limit)}"

    return query, params


def main():
    parser = argparse.ArgumentParser(
        description="Find cards matching a card shape"
    )
    parser.add_argument("-k", "--cost", help="Exact mana cost, e.g. '{2}{W}', '{1}{R}{R}', '{3}'")
    parser.add_argument("-r", "--rarity", help="Rarity: common/uncommon/rare/mythic")
    parser.add_argument("-t", "--type", help="Card type: Creature/Instant/Sorcery/Enchantment/Artifact/Planeswalker")
    parser.add_argument("-m", "--cmc", type=int, help="Mana value (CMC) — use instead of --cost for any cost at that MV")
    parser.add_argument("-c", "--color", help="Color: W/U/B/R/G — use instead of --cost for any cost in that color")
    parser.add_argument("-o", "--owned", action="store_true", help="Only show cards in your collection")
    parser.add_argument("--limit", type=int, default=50, help="Max results (default 50)")
    parser.add_argument("--db", help="Database path (default: ~/.mtgc/collection.sqlite)")
    args = parser.parse_args()

    if not any([args.cost, args.rarity, args.type, args.cmc is not None, args.color]):
        parser.error("Provide at least one filter")

    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    query, params = build_query(args)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    # Build filter description
    filters = []
    if args.cost:
        filters.append(args.cost)
    if args.rarity:
        filters.append(args.rarity)
    if args.color:
        color_names = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
        filters.append(color_names.get(args.color.upper(), args.color))
    if args.type:
        filters.append(args.type)
    if args.cmc is not None:
        filters.append(f"MV {args.cmc}")
    desc = " | ".join(filters)

    print(f"Shape: {desc}")
    print(f"Found: {len(rows)} cards")
    print(f"{'=' * 60}")

    for name, mana_cost, type_line, cmc, rarity in rows:
        cost = mana_cost or ""
        r = rarity[0].upper() if rarity else "?"
        print(f"  [{r}] {cost:14s} {name:40s} {type_line}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
