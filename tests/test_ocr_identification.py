"""
Tests for full-card OCR identification via EasyOCR + Claude text extraction.

Given a photo of full cards, verify that the OCR → Claude → Scryfall pipeline
correctly identifies each card by set + collector number.

Test fixtures: tests/fixtures/ocr-*.jpeg + tests/fixtures/ocr-*.json
JSON sidecar format:
{
  "description": "...",
  "set": "eoe",
  "count": 7,
  "cards": [
    {"rarity": "C", "collector_number": "0092", "set": "EOE"},
    ...
  ]
}

To run: pytest tests/test_ocr_identification.py -v

Note: Requires ANTHROPIC_API_KEY and easyocr. These tests cost real API credits.
"""

import json
import os
from pathlib import Path

import pytest


# =============================================================================
# Test Data Discovery
# =============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"

OCR_PHOTOS = []

if FIXTURES_DIR.exists():
    for photo_path in sorted(FIXTURES_DIR.glob("ocr-*.jpeg")):
        json_path = photo_path.with_suffix(".json")
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
            OCR_PHOTOS.append((
                str(photo_path),
                data.get("cards", []),
                data.get("set"),
                data.get("count", len(data.get("cards", []))),
                data.get("description", photo_path.stem),
            ))


# =============================================================================
# Helpers
# =============================================================================

def normalize_cn(cn: str) -> str:
    """Strip leading zeros for comparison."""
    return cn.lstrip("0") or "0"


def card_key(card: dict) -> str:
    """Canonical key: SET#CN (normalized)."""
    return f"{card['set'].upper()}#{normalize_cn(card['collector_number'])}"


def format_card(card: dict) -> str:
    """Human-readable card identifier."""
    return f"{card['rarity']} {card['collector_number']} {card['set']}"


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
@pytest.mark.skipif(
    not OCR_PHOTOS,
    reason="No OCR test fixtures found",
)
class TestOCRIdentification:
    """Test that OCR + Claude + Scryfall correctly identifies cards from full photos."""

    @pytest.mark.parametrize(
        "photo_path,expected_cards,set_code,count,description",
        OCR_PHOTOS,
        ids=[Path(p[0]).stem for p in OCR_PHOTOS],
    )
    def test_ocr_pipeline(self, photo_path, expected_cards, set_code, count, description):
        """Verify the full OCR pipeline resolves to the correct set+CN for each card."""
        from mtg_collector.services.ocr import run_ocr
        from mtg_collector.services.claude import ClaudeVision
        from mtg_collector.services.scryfall import ScryfallAPI
        from mtg_collector.cli.ingest_ocr import _resolve_card

        # Step 1: OCR
        ocr_texts = run_ocr(photo_path)
        assert ocr_texts, "OCR returned no text fragments"

        print(f"\n{'='*70}")
        print(f"Test: {description}")
        print(f"{'='*70}")
        print(f"OCR extracted {len(ocr_texts)} text fragments")

        # Step 2: Claude extraction
        claude = ClaudeVision()
        hints = {}
        if set_code:
            hints["set"] = set_code

        extracted = claude.extract_cards_from_ocr(ocr_texts, count, hints)
        assert extracted, "Claude returned no card extractions"

        print(f"Claude extracted {len(extracted)} card(s):")
        for i, card in enumerate(extracted, 1):
            print(f"  {i}. {card.get('name', '???')} "
                  f"({card.get('set_code', '???')} #{card.get('collector_number', '???')})")

        # Step 3: Resolve via Scryfall
        scryfall = ScryfallAPI()
        if set_code:
            normalized_set = scryfall.normalize_set_code(set_code)
            assert normalized_set, f"Unknown set code: {set_code}"
            hints["set"] = normalized_set

        # Use a stub printing_repo that always returns None (no local cache)
        class NoPrintingRepo:
            def get_by_set_cn(self, set_code, cn):
                return None

        resolved = []
        for card_info in extracted:
            card_data = _resolve_card(card_info, hints, scryfall, NoPrintingRepo())
            if card_data:
                resolved.append({
                    "set": card_data["set"].upper(),
                    "collector_number": card_data["collector_number"],
                    "name": card_data.get("name", "???"),
                    "rarity": card_data.get("rarity", "???"),
                })
            else:
                resolved.append(None)

        print(f"\nResolved {sum(1 for r in resolved if r)} / {len(extracted)} card(s):")
        for i, r in enumerate(resolved, 1):
            if r:
                print(f"  {i}. {r['name']} ({r['set']}#{r['collector_number']})")
            else:
                print(f"  {i}. FAILED TO RESOLVE")

        # Step 4: Compare against expected
        expected_keys = {card_key(c) for c in expected_cards}
        resolved_keys = set()
        for r in resolved:
            if r:
                key = f"{r['set'].upper()}#{normalize_cn(r['collector_number'])}"
                resolved_keys.add(key)

        matched = expected_keys & resolved_keys
        missing = expected_keys - resolved_keys
        extra = resolved_keys - expected_keys

        print(f"\nMatched: {len(matched)}/{len(expected_cards)}")
        if missing:
            print(f"Missing ({len(missing)}):")
            for key in sorted(missing):
                exp = next(c for c in expected_cards if card_key(c) == key)
                print(f"  - {format_card(exp)}")
        if extra:
            print(f"Extra ({len(extra)}):")
            for key in sorted(extra):
                r = next(r for r in resolved if r and
                         f"{r['set'].upper()}#{normalize_cn(r['collector_number'])}" == key)
                print(f"  - {r['name']} ({key})")

        assert not missing, (
            f"Missing cards:\n"
            + "\n".join(f"  - {format_card(next(c for c in expected_cards if card_key(c) == k))}"
                        for k in sorted(missing))
        )
        assert not extra, (
            f"Extra (unexpected) cards:\n"
            + "\n".join(f"  - {k}" for k in sorted(extra))
        )
