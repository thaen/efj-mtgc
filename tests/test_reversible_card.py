"""Tests for reversible_card layout handling in cache import.

Reversible cards (e.g. ECL shocklands) have oracle_id on card_faces
instead of at the top level. The cache import must pull oracle_id from
card_faces[0] when it's missing at the top level.

To run: uv run pytest tests/test_reversible_card.py -v
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mtg_collector.db import (
    CardRepository,
    PrintingRepository,
    SetRepository,
    get_connection,
    init_db,
)
from mtg_collector.services.bulk_import import ScryfallBulkClient, ensure_set_populated


# -- Fixtures: synthetic reversible_card data matching Scryfall's shape --

REVERSIBLE_ORACLE_ID = "f1750962-a87c-49f6-b731-02ae971ac6ea"

REVERSIBLE_CARD_DATA = {
    "id": "19cba6be-7291-4788-9241-87dad3b68363",
    "name": "Hallowed Fountain // Hallowed Fountain",
    "layout": "reversible_card",
    "set": "ecl",
    "collector_number": "347",
    "lang": "en",
    "cmc": 0.0,
    "type_line": "Land — Plains Island",
    "colors": [],
    "color_identity": ["U", "W"],
    "rarity": "rare",
    "finishes": ["nonfoil", "foil"],
    "card_faces": [
        {
            "oracle_id": REVERSIBLE_ORACLE_ID,
            "name": "Hallowed Fountain",
            "mana_cost": "",
            "type_line": "Land — Plains Island",
            "oracle_text": "({T}: Add {W} or {U}.)\nAs Hallowed Fountain enters, you may pay 2 life. If you don't, it enters tapped.",
            "image_uris": {
                "small": "https://cards.scryfall.io/small/front/1/9/19cba6be.jpg",
                "normal": "https://cards.scryfall.io/normal/front/1/9/19cba6be.jpg",
            },
        },
        {
            "oracle_id": REVERSIBLE_ORACLE_ID,
            "name": "Hallowed Fountain",
            "mana_cost": "",
            "type_line": "Land — Plains Island",
            "oracle_text": "({T}: Add {W} or {U}.)\nAs Hallowed Fountain enters, you may pay 2 life. If you don't, it enters tapped.",
            "image_uris": {
                "small": "https://cards.scryfall.io/small/back/1/9/19cba6be.jpg",
                "normal": "https://cards.scryfall.io/normal/back/1/9/19cba6be.jpg",
            },
        },
    ],
}

# A normal card for comparison
NORMAL_CARD_DATA = {
    "oracle_id": "aaaa-bbbb-cccc-dddd",
    "id": "normal-card-id-1234",
    "name": "Lightning Bolt",
    "layout": "normal",
    "set": "ecl",
    "collector_number": "100",
    "lang": "en",
    "cmc": 1.0,
    "type_line": "Instant",
    "mana_cost": "{R}",
    "colors": ["R"],
    "color_identity": ["R"],
    "rarity": "common",
    "finishes": ["nonfoil"],
    "image_uris": {
        "small": "https://cards.scryfall.io/small/front/bolt.jpg",
        "normal": "https://cards.scryfall.io/normal/front/bolt.jpg",
    },
}


@pytest.fixture
def db():
    """In-memory SQLite database with schema initialized."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    conn = get_connection(tmp.name)
    init_db(conn)
    # Insert the ECL set
    conn.execute(
        "INSERT INTO sets (set_code, set_name, set_type, released_at) VALUES (?, ?, ?, ?)",
        ("ecl", "Lorwyn Eclipsed", "expansion", "2025-09-01"),
    )
    conn.commit()
    yield conn
    conn.close()
    Path(tmp.name).unlink(missing_ok=True)


class TestReversibleCardBulkImport:
    """Test that reversible_card layout cards are imported by cache_all's main loop."""

    def test_resolve_oracle_id_from_faces(self):
        """resolve_reversible_oracle_id should promote oracle_id from card_faces[0]."""
        from mtg_collector.services.bulk_import import resolve_reversible_oracle_id

        card_data = dict(REVERSIBLE_CARD_DATA)
        assert "oracle_id" not in card_data

        resolved = resolve_reversible_oracle_id(card_data)
        assert resolved is True
        assert card_data["oracle_id"] == REVERSIBLE_ORACLE_ID

    def test_resolve_oracle_id_noop_for_normal_cards(self):
        """resolve_reversible_oracle_id is a no-op when oracle_id already present."""
        from mtg_collector.services.bulk_import import resolve_reversible_oracle_id

        card_data = dict(NORMAL_CARD_DATA)
        resolved = resolve_reversible_oracle_id(card_data)
        assert resolved is False
        assert card_data["oracle_id"] == "aaaa-bbbb-cccc-dddd"

    def test_resolve_returns_false_without_faces(self):
        """resolve_reversible_oracle_id returns False for cards with no oracle_id and no faces."""
        from mtg_collector.services.bulk_import import resolve_reversible_oracle_id

        card_data = {"id": "no-oracle", "name": "Token", "set": "ecl"}
        resolved = resolve_reversible_oracle_id(card_data)
        assert resolved is False
        assert "oracle_id" not in card_data

    def test_to_card_model_works_after_resolution(self):
        """to_card_model succeeds on reversible_card data after oracle_id resolution."""
        from mtg_collector.services.bulk_import import resolve_reversible_oracle_id

        api = ScryfallBulkClient()
        card_data = dict(REVERSIBLE_CARD_DATA)
        resolve_reversible_oracle_id(card_data)

        card = api.to_card_model(card_data)
        assert card.oracle_id == REVERSIBLE_ORACLE_ID

    def test_to_printing_model_works_after_resolution(self):
        """to_printing_model succeeds on reversible_card data after oracle_id resolution."""
        from mtg_collector.services.bulk_import import resolve_reversible_oracle_id

        api = ScryfallBulkClient()
        card_data = dict(REVERSIBLE_CARD_DATA)
        resolve_reversible_oracle_id(card_data)

        printing = api.to_printing_model(card_data)
        assert printing.oracle_id == REVERSIBLE_ORACLE_ID
        assert printing.set_code == "ecl"
        assert printing.collector_number == "347"

    def test_normal_card_unaffected(self):
        """Normal cards with top-level oracle_id should work as before."""
        api = ScryfallBulkClient()
        card = api.to_card_model(NORMAL_CARD_DATA)
        assert card.oracle_id == "aaaa-bbbb-cccc-dddd"

        printing = api.to_printing_model(NORMAL_CARD_DATA)
        assert printing.oracle_id == "aaaa-bbbb-cccc-dddd"


class TestReversibleCardEnsureSetPopulated:
    """Test that ensure_set_populated handles reversible cards."""

    def test_ensure_set_populated_imports_reversible_cards(self, db):
        """ensure_set_populated should import reversible cards, not skip them."""
        api = ScryfallBulkClient()
        card_repo = CardRepository(db)
        set_repo = SetRepository(db)
        printing_repo = PrintingRepository(db)

        # Mock the API to return our test data
        api.get_set_cards = MagicMock(return_value=[
            NORMAL_CARD_DATA,
            REVERSIBLE_CARD_DATA,
        ])
        api.get_set = MagicMock(return_value={
            "code": "ecl",
            "name": "Lorwyn Eclipsed",
            "set_type": "expansion",
            "released_at": "2025-09-01",
        })

        result = ensure_set_populated(api, "ecl", card_repo, set_repo, printing_repo, db)
        assert result is True

        # Both cards should be in the database
        normal_printing = printing_repo.get_by_set_cn("ecl", "100")
        assert normal_printing is not None, "Normal card should be imported"

        reversible_printing = printing_repo.get_by_set_cn("ecl", "347")
        assert reversible_printing is not None, "Reversible card should be imported"
        assert reversible_printing.oracle_id == REVERSIBLE_ORACLE_ID
