#!/usr/bin/env python3
"""Generate a Scryfall search URL showing all cards in a deck, using owned printings.

Usage:
    uv run python scripts/make_j25/scryfall_deck_url.py "Card Name 1" "Card Name 2" ...

Example (the Zombies pack):
    uv run python scripts/make_j25/scryfall_deck_url.py \
        "Festering Mummy" "Tortured Existence" "Dregscape Zombie" \
        "Shepherd of Rot" "Withered Wretch" "Skirk Ridge Exhumer" \
        "Cadaver Imp" "Cadaverous Knight" "Phyrexian Arena" \
        "Buried Alive" "Soulless One" "Cruel Revival"
"""

import os
import sqlite3
import sys
import urllib.parse
from pathlib import Path


def get_db_path():
    env = os.environ.get("MTGC_DB")
    if env:
        return env
    return str(Path.home() / ".mtgc" / "collection.sqlite")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Scryfall URL for a deck")
    parser.add_argument("cards", nargs="+", help="Card names")
    parser.add_argument("--open", action="store_true", help="Open URL in browser")
    args = parser.parse_args()

    card_names = args.cards
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)

    terms = []
    for name in card_names:
        # Find the owned printing (prefer one in the collection)
        row = conn.execute("""
            SELECT p.set_code, p.collector_number
            FROM collection col
            JOIN printings p ON p.printing_id = col.printing_id
            JOIN cards c ON c.oracle_id = p.oracle_id
            WHERE c.name = ? AND col.status = 'owned'
            LIMIT 1
        """, (name,)).fetchone()

        if not row:
            # Fall back to any printing in the DB
            row = conn.execute("""
                SELECT p.set_code, p.collector_number
                FROM printings p
                JOIN cards c ON c.oracle_id = p.oracle_id
                JOIN sets s ON s.set_code = p.set_code
                WHERE c.name = ? AND s.digital = 0
                ORDER BY s.released_at DESC
                LIMIT 1
            """, (name,)).fetchone()

        if not row:
            print(f"WARNING: Card not found: {name}", file=sys.stderr)
            continue

        set_code, cn = row
        terms.append(f"(s:{set_code.lower()} cn:{cn})")
        print(f"  {name:30s} -> {set_code}/{cn}")

    conn.close()

    if not terms:
        print("No cards found.", file=sys.stderr)
        sys.exit(1)

    query = " or ".join(terms)
    url = f"https://scryfall.com/search?unique=prints&q={urllib.parse.quote(query)}"

    print()
    if len(url) > 8000:
        print(f"WARNING: URL is {len(url)} chars (Scryfall limit ~8000)", file=sys.stderr)

    print(url)

    if args.open:
        import subprocess
        subprocess.run(["open", url])


if __name__ == "__main__":
    main()
