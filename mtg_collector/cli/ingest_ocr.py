"""Ingest-ocr command: mtg ingest-ocr <image> --count N"""

import sys
from pathlib import Path

from mtg_collector.db import (
    get_connection,
    init_db,
    CardRepository,
    SetRepository,
    PrintingRepository,
    CollectionRepository,
)
from mtg_collector.db.models import CollectionEntry
from mtg_collector.services.claude import ClaudeVision
from mtg_collector.services.ocr import run_ocr
from mtg_collector.services.scryfall import (
    ScryfallAPI,
    cache_scryfall_data,
    ensure_set_cached,
)
from mtg_collector.utils import normalize_condition, normalize_finish, store_source_image


def _build_scryfall_query(card_info, hints):
    """
    Build a Scryfall search query from extracted card fields + user hints.

    Returns (set_code, collector_number) tuple for direct lookup, or
    (None, query_string) for search API.
    """
    set_code = card_info.get("set_code") or hints.get("set")
    cn = card_info.get("collector_number")

    # Best case: direct lookup by set + CN
    if set_code and cn:
        return set_code.lower(), cn

    # Build a search query from available fields
    parts = []
    name = card_info.get("name")
    if name:
        parts.append(f'!"{name}"')

    if set_code:
        parts.append(f"set:{set_code.lower()}")

    card_type = card_info.get("type")
    if card_type and not name:
        parts.append(f"t:{card_type.lower()}")

    power = card_info.get("power")
    if power is not None and not name:
        parts.append(f"pow:{power}")

    toughness = card_info.get("toughness")
    if toughness is not None and not name:
        parts.append(f"tou:{toughness}")

    artist = card_info.get("artist")
    if artist and not name:
        # Use first word of artist name for robustness
        parts.append(f'a:"{artist.split()[0]}"')

    if hints.get("color") and not name:
        parts.append(f"c:{hints['color'].lower()}")

    if not parts:
        return None, None

    return None, " ".join(parts)


def _resolve_card(card_info, hints, scryfall, printing_repo):
    """
    Resolve a single card from extracted OCR data to a Scryfall card dict.

    Returns the Scryfall card data dict, or None if not found.
    If direct lookup fails, presents candidates to the user for selection.
    """
    set_code, cn_or_query = _build_scryfall_query(card_info, hints)

    # Direct lookup by set + CN
    if set_code and cn_or_query:
        cn_raw = cn_or_query
        cn_stripped = cn_raw.lstrip("0") or "0"

        # Try local cache first
        printing = printing_repo.get_by_set_cn(set_code, cn_stripped)
        if not printing:
            printing = printing_repo.get_by_set_cn(set_code, cn_raw)
        if printing and printing.raw_json:
            return printing.get_scryfall_data()

        # Try Scryfall API
        card_data = scryfall.get_card_by_set_cn(set_code, cn_stripped)
        if not card_data:
            card_data = scryfall.get_card_by_set_cn(set_code, cn_raw)
        if card_data:
            return card_data

    # No direct match — gather candidates and let user pick
    name = card_info.get("name")
    search_set = card_info.get("set_code") or hints.get("set")
    candidates = []

    if name:
        candidates = scryfall.search_card(name, set_code=search_set)

    # Last resort: raw query if we built one
    if not candidates and cn_or_query and not set_code:
        try:
            url = f"{scryfall.BASE_URL}/cards/search"
            params = {"q": cn_or_query, "unique": "prints"}
            response = scryfall._request_with_retry("GET", url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("object") == "list" and data.get("data"):
                candidates = data["data"]
        except Exception:
            pass

    if not candidates:
        return None

    # Single exact match — still confirm with user
    if len(candidates) == 1:
        return candidates[0]

    return _pick_card(card_info, candidates)


def _pick_card(card_info, candidates):
    """Present candidate printings to the user and let them pick one."""
    name = card_info.get("name", "???")
    print()
    print(f"  Multiple matches for '{name}' — pick the correct printing:")
    print()

    for i, c in enumerate(candidates, 1):
        rarity = c.get("rarity", "?")[0].upper()
        set_code = c.get("set", "???").upper()
        cn = c.get("collector_number", "???")
        cname = c.get("name", "???")
        released = c.get("released_at", "")
        set_name = c.get("set_name", "")
        print(f"    {i:3d}. {cname:<30s} {set_code} #{cn:<5s} [{rarity}] {set_name} ({released})")

    print(f"      s = skip this card")
    print()

    while True:
        try:
            choice = input("    Pick #: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n    Skipped.")
            return None

        if choice == "s":
            return None

        try:
            idx = int(choice)
            if 1 <= idx <= len(candidates):
                return candidates[idx - 1]
            print(f"    Enter 1-{len(candidates)} or 's' to skip.")
        except ValueError:
            print("    Invalid input.")


def _review_cards(resolved):
    """Interactive review: let user toggle foil or remove cards before committing."""
    print()
    print("=" * 70)
    print("REVIEW MODE".center(70))
    print("=" * 70)

    while True:
        print()
        for i, r in enumerate(resolved, 1):
            foil_marker = " *FOIL*" if r["foil"] else ""
            rarity = r.get("rarity", "?")[0].upper()
            print(
                f"  {i:3d}. {r['name']:<35s} "
                f"{r['set_code'].upper()} #{r['cn_display']:<5s} "
                f"[{rarity}]{foil_marker}"
            )

        print()
        print("Commands: <number> toggle foil, 'd<number>' remove card, 'a' accept, 'q' quit")

        try:
            choice = input("  > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled.")
            return False

        if choice == "q":
            print("  Cancelled.")
            return False

        if choice == "a":
            return True

        # Delete command: d<number>
        if choice.startswith("d"):
            try:
                idx = int(choice[1:])
                if 1 <= idx <= len(resolved):
                    removed = resolved.pop(idx - 1)
                    print(f"  Removed: {removed['name']}")
                    if not resolved:
                        print("  No cards remaining.")
                        return False
                else:
                    print(f"  Invalid number. Enter 1-{len(resolved)}.")
            except ValueError:
                print("  Invalid input. Use d<number> to remove (e.g. d3).")
            continue

        # Toggle foil
        try:
            idx = int(choice)
            if 1 <= idx <= len(resolved):
                r = resolved[idx - 1]
                r["foil"] = not r["foil"]
                status = "FOIL" if r["foil"] else "nonfoil"
                print(f"  Toggled: {r['name']} -> {status}")
            else:
                print(f"  Invalid number. Enter 1-{len(resolved)}.")
        except ValueError:
            print("  Invalid input.")


def register(subparsers):
    """Register the ingest-ocr subcommand."""
    parser = subparsers.add_parser(
        "ingest-ocr",
        help="Add cards from full card photos using local OCR + Claude text extraction",
        description=(
            "Use local EasyOCR to extract text from card photos, then Claude to "
            "parse the text into structured card data. Works with photos of full "
            "cards (not just corners). Cheaper and faster than ingest-corners."
        ),
    )
    parser.add_argument(
        "image",
        metavar="IMAGE",
        help="Image file showing card(s)",
    )
    parser.add_argument(
        "--count",
        type=int,
        required=True,
        help="Expected number of cards in the image",
    )
    parser.add_argument(
        "--set",
        dest="set_code",
        default=None,
        help="Known set code for all cards (e.g., EOE)",
    )
    parser.add_argument(
        "--color",
        default=None,
        help="Known color identity for all cards (e.g., R, UB)",
    )
    parser.add_argument(
        "--condition",
        default="Near Mint",
        help="Condition for all cards (default: Near Mint)",
    )
    parser.add_argument(
        "--source",
        default="ocr_ingest",
        help="Source identifier for these cards (default: ocr_ingest)",
    )
    parser.set_defaults(func=run)


def run(args):
    """Run the ingest-ocr command."""
    image_path = args.image
    if not Path(image_path).exists():
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    # Step 1: Local OCR
    print(f"Running OCR on: {image_path}")
    ocr_texts = run_ocr(image_path)
    print(f"  Extracted {len(ocr_texts)} text fragment(s)")

    if not ocr_texts:
        print("Error: No text detected in image.")
        sys.exit(1)

    # Step 2: Claude text extraction
    print(f"Sending OCR text to Claude for structured extraction ({args.count} card(s))...")
    claude = ClaudeVision()
    hints = {}
    if args.set_code:
        hints["set"] = args.set_code
    if args.color:
        hints["color"] = args.color

    extracted, usage = claude.extract_cards_from_ocr(ocr_texts, args.count, hints)
    print(f"  Tokens: {usage.input_tokens} in / {usage.output_tokens} out")

    if not extracted:
        print("Error: Claude could not extract any cards from OCR text.")
        sys.exit(1)

    print(f"  Claude identified {len(extracted)} card(s):")
    for i, card in enumerate(extracted, 1):
        name = card.get("name", "???")
        sc = card.get("set_code", "???")
        cn = card.get("collector_number", "???")
        print(f"    {i}. {name} ({sc} #{cn})")
    print()

    # Step 3: Resolve via Scryfall
    scryfall = ScryfallAPI()

    # Normalize set code if provided
    if args.set_code:
        normalized_set = scryfall.normalize_set_code(args.set_code)
        if not normalized_set:
            print(f"Error: Unknown set code '{args.set_code}'")
            sys.exit(1)
        hints["set"] = normalized_set

    # Initialize database
    conn = get_connection(args.db_path)
    init_db(conn)

    card_repo = CardRepository(conn)
    set_repo = SetRepository(conn)
    printing_repo = PrintingRepository(conn)
    collection_repo = CollectionRepository(conn)

    # Cache set if known
    if hints.get("set"):
        ensure_set_cached(scryfall, hints["set"], card_repo, set_repo, printing_repo, conn)

    print("Resolving cards via Scryfall...")
    resolved = []
    failed = []

    for i, card_info in enumerate(extracted, 1):
        name = card_info.get("name", "???")
        card_data = _resolve_card(card_info, hints, scryfall, printing_repo)

        if not card_data:
            print(f"  FAILED: Card {i} ({name}) — not found on Scryfall")
            failed.append(f"Card {i}: {name}")
            continue

        cache_scryfall_data(scryfall, card_repo, set_repo, printing_repo, card_data)

        resolved.append({
            "card_data": card_data,
            "set_code": card_data.get("set", "???"),
            "cn_display": card_data.get("collector_number", "???"),
            "name": card_data.get("name", "Unknown"),
            "rarity": card_data.get("rarity", "unknown"),
            "foil": False,  # Can't detect foil from OCR, default nonfoil
        })

        print(f"  OK: {card_data['name']} ({card_data['set'].upper()} #{card_data['collector_number']})")

    if failed:
        print()
        print(f"WARNING: {len(failed)} card(s) could not be resolved:")
        for f in failed:
            print(f"  - {f}")

    if not resolved:
        print("Error: No cards could be resolved.")
        conn.rollback()
        sys.exit(1)

    # Step 4: Review (always)
    if not _review_cards(resolved):
        conn.rollback()
        sys.exit(0)

    # Step 5: Insert into collection
    condition = normalize_condition(args.condition)
    si = store_source_image(image_path)

    added = 0
    for r in resolved:
        finish = normalize_finish("foil" if r["foil"] else "nonfoil")
        entry = CollectionEntry(
            id=None,
            scryfall_id=r["card_data"]["id"],
            finish=finish,
            condition=condition,
            source=args.source,
            source_image=si,
        )
        entry_id = collection_repo.add(entry)
        print(
            f"  Added (ID: {entry_id}): {r['name']} "
            f"({r['set_code'].upper()} #{r['cn_display']}) [{finish}]"
        )
        added += 1

    conn.commit()
    print()
    print(f"Done! Added {added} card(s) to collection.")
