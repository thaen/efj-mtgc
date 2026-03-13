#!/usr/bin/env python3
"""Look up a card's oracle text by name.

Usage:
    uv run python scripts/card_oracle.py "Gravecrawler"
    uv run python scripts/card_oracle.py "Doom Blade"
"""

import os
import sqlite3
import sys
from pathlib import Path


def get_db_path():
    env = os.environ.get("MTGC_DB")
    if env:
        return env
    return str(Path.home() / ".mtgc" / "collection.sqlite")


def main():
    if len(sys.argv) < 2:
        print("Usage: card_oracle.py <card name>", file=sys.stderr)
        sys.exit(1)

    name = " ".join(sys.argv[1:])
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)

    # Exact match first, then LIKE
    row = conn.execute(
        "SELECT name, mana_cost, type_line, oracle_text, colors, cmc FROM cards WHERE name = ?",
        (name,),
    ).fetchone()

    if not row:
        rows = conn.execute(
            "SELECT name, mana_cost, type_line, oracle_text, colors, cmc FROM cards WHERE name LIKE ?",
            (f"%{name}%",),
        ).fetchall()
        if not rows:
            print(f"No card found matching '{name}'")
            sys.exit(1)
        if len(rows) > 10:
            print(f"Too many matches ({len(rows)}). Be more specific.")
            for r in rows[:15]:
                print(f"  {r[0]}")
            sys.exit(1)
        for row in rows:
            _print_card(row)
            print()
        conn.close()
        return

    _print_card(row)
    conn.close()


def _print_card(row):
    name, mana_cost, type_line, oracle_text, colors, cmc = row
    print(f"{name}  {mana_cost or ''}")
    print(f"{type_line}")
    if oracle_text:
        print(f"---")
        print(oracle_text)


if __name__ == "__main__":
    main()
