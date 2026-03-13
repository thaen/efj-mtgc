#!/usr/bin/env python3
"""Insert the Zombies Jumpstart pack as a hypothetical deck.

Usage:
    uv run python scripts/insert_zombies_deck.py
    uv run python scripts/insert_zombies_deck.py --db /path/to/collection.sqlite
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# The 12 spells chosen for the Zombies Jumpstart pack
DECK_CARDS = [
    # (card_name, zone, quantity)
    ("Festering Mummy", "mainboard", 1),
    ("Tortured Existence", "mainboard", 1),
    ("Dregscape Zombie", "mainboard", 1),
    ("Shepherd of Rot", "mainboard", 1),
    ("Withered Wretch", "mainboard", 1),
    ("Skirk Ridge Exhumer", "mainboard", 1),
    ("Cadaver Imp", "mainboard", 1),
    ("Cadaverous Knight", "mainboard", 1),
    ("Phyrexian Arena", "mainboard", 1),
    ("Buried Alive", "mainboard", 1),
    ("Soulless One", "mainboard", 1),
    ("Cruel Revival", "mainboard", 1),
]


def get_db_path(override=None):
    if override:
        return override
    env = os.environ.get("MTGC_DB")
    if env:
        return env
    return str(Path.home() / ".mtgc" / "collection.sqlite")


def main():
    parser = argparse.ArgumentParser(
        description="Insert Zombies Jumpstart pack as a hypothetical deck"
    )
    parser.add_argument("--db", help="Database path (default: ~/.mtgc/collection.sqlite)")
    args = parser.parse_args()

    db_path = get_db_path(args.db)
    if not Path(db_path).exists():
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    # Resolve card names to oracle_ids
    expected_cards = []
    for card_name, zone, quantity in DECK_CARDS:
        row = conn.execute(
            "SELECT oracle_id FROM cards WHERE name = ?", (card_name,)
        ).fetchone()
        if not row:
            print(f"ERROR: Card not found in database: {card_name}", file=sys.stderr)
            sys.exit(1)
        expected_cards.append({
            "oracle_id": row[0],
            "zone": zone,
            "quantity": quantity,
            "name": card_name,
        })

    # Check for existing deck with same name
    existing = conn.execute(
        "SELECT id FROM decks WHERE name = ?", ("Zombies (Jumpstart)",)
    ).fetchone()
    if existing:
        print(f"ERROR: Deck 'Zombies (Jumpstart)' already exists (id={existing[0]})", file=sys.stderr)
        sys.exit(1)

    # Insert the deck
    from mtg_collector.utils import now_iso
    ts = now_iso()

    conn.execute(
        """INSERT INTO decks (name, description, format, hypothetical,
           origin_set_code, origin_theme, is_precon, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Zombies (Jumpstart)",
            "Generated Jumpstart pack: Zombie tribal with graveyard recursion. "
            "Festering Mummy / Shepherd of Rot / Soulless One as Zombie payoffs, "
            "Tortured Existence / Buried Alive / Cadaver Imp / Cruel Revival for recursion, "
            "Phyrexian Arena for card advantage.",
            "jumpstart",
            1,      # hypothetical
            "J25",  # origin_set_code
            "Zombies",  # origin_theme
            0,      # is_precon (not a real precon)
            ts,
            ts,
        ),
    )
    deck_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Insert expected cards
    for card in expected_cards:
        conn.execute(
            """INSERT INTO deck_expected_cards (deck_id, oracle_id, zone, quantity)
               VALUES (?, ?, ?, ?)""",
            (deck_id, card["oracle_id"], card["zone"], card["quantity"]),
        )

    conn.commit()
    conn.close()

    print(f"Created hypothetical deck: Zombies (Jumpstart) (id={deck_id})")
    print(f"Added {len(expected_cards)} cards:")
    for card in expected_cards:
        print(f"  {card['name']}")


if __name__ == "__main__":
    main()
