"""OCR benchmark: compare EasyOCR (greedy/beamsearch) and PaddleOCR on card photos."""

import json
import sqlite3
import textwrap
import time
from pathlib import Path

import easyocr
from paddleocr import PaddleOCR

from mtg_collector.services.ocr import _load_image
from mtg_collector.utils import get_mtgc_home

DB = get_mtgc_home() / "collection.sqlite"
IMG_DIR = get_mtgc_home() / "ingest_images"
RAW_DIR = Path(__file__).parent / "ocr_benchmark_raw"

CARDS = [
    ("camera_2026-02-17T13-43-26_238.jpg", "City Pigeon"),
    ("camera_2026-02-17T13-50-57_312.jpg", "Thwip!"),
    ("camera_2026-02-17T13-43-06_233.jpg", "Benalish Hero"),
]

EASYOCR_MODEL_DIR = str(Path(__file__).resolve().parent.parent / "models" / "ocr")

COL = 50
SEP = " │ "


def sort_fragments_spatial(fragments: list[dict]) -> list[dict]:
    """Sort fragments top-to-bottom, left-to-right using bounding boxes."""
    return sorted(fragments, key=lambda f: (f["y"], f["x"]))


def run_easyocr(reader, img, decoder: str) -> tuple[list[dict], float]:
    """Run EasyOCR, return (fragments, elapsed_seconds)."""
    t0 = time.monotonic()
    results = reader.readtext(img, detail=1, decoder=decoder)
    elapsed = time.monotonic() - t0
    fragments = []
    for bbox, text, conf in results:
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        fragments.append({
            "text": text,
            "x": min(xs),
            "y": min(ys),
            "w": max(xs) - min(xs),
            "h": max(ys) - min(ys),
            "confidence": round(float(conf), 3),
        })
    return sort_fragments_spatial(fragments), elapsed


def run_paddle(ocr, img_path: str) -> tuple[list[dict], float]:
    """Run PaddleOCR 2.x, return (fragments, elapsed_seconds)."""
    t0 = time.monotonic()
    results = ocr.ocr(img_path, cls=True)
    elapsed = time.monotonic() - t0
    fragments = []
    for line in results[0]:
        bbox, (text, conf) = line
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        fragments.append({
            "text": text,
            "x": min(xs),
            "y": min(ys),
            "w": max(xs) - min(xs),
            "h": max(ys) - min(ys),
            "confidence": round(float(conf), 3),
        })
    return sort_fragments_spatial(fragments), elapsed


def wrap(text: str, width: int) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width) or [""])
    return lines


def side_by_side(left_title: str, left_lines: list[str], right_title: str, right_lines: list[str]):
    print(f"{'─' * COL}───{'─' * COL}")
    print(f"{left_title:<{COL}}{SEP}{right_title}")
    print(f"{'─' * COL}───{'─' * COL}")
    max_lines = max(len(left_lines), len(right_lines))
    for i in range(max_lines):
        l = left_lines[i] if i < len(left_lines) else ""
        r = right_lines[i] if i < len(right_lines) else ""
        print(f"{l:<{COL}}{SEP}{r}")
    print()


def get_ref_text(conn, card_name: str) -> str:
    row = conn.execute(
        "SELECT name, type_line, mana_cost, oracle_text FROM cards WHERE name = ?",
        (card_name,),
    ).fetchone()
    name, type_line, mana_cost, oracle_text = row
    parts = [name]
    if mana_cost:
        parts.append(mana_cost)
    parts.append(type_line)
    parts.append("")
    parts.append(oracle_text)
    return "\n".join(parts)


def write_raw(engine_name: str, filename: str, fragments: list[dict]):
    path = RAW_DIR / engine_name / filename.replace(".jpg", ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fragments, indent=2))


def main():
    conn = sqlite3.connect(DB)

    print("Initializing EasyOCR...")
    reader = easyocr.Reader(
        ["en"], gpu=False, model_storage_directory=EASYOCR_MODEL_DIR, verbose=False,
    )
    print("Initializing PaddleOCR...")
    paddle = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    engines = [
        ("easyocr_greedy", lambda img, path: run_easyocr(reader, img, "greedy")),
        ("easyocr_beam", lambda img, path: run_easyocr(reader, img, "beamsearch")),
        ("paddleocr", lambda img, path: run_paddle(paddle, path)),
    ]

    timings = []  # (engine, card_name, seconds)

    for filename, card_name in CARDS:
        image_path = IMG_DIR / filename
        img = _load_image(str(image_path))
        ref_text = get_ref_text(conn, card_name)
        right = wrap(ref_text, COL)

        for engine_name, run_fn in engines:
            fragments, elapsed = run_fn(img, str(image_path))
            timings.append((engine_name, card_name, elapsed))
            write_raw(engine_name, filename, fragments)

            ocr_text = "\n".join(f["text"] for f in fragments)
            left = wrap(ocr_text, COL)
            side_by_side(
                f"{engine_name}: {card_name}",
                left,
                f"Scryfall: {card_name}",
                right,
            )

    conn.close()

    # Timing table
    print(f"\n{'═' * 70}")
    print(f"{'ENGINE':<20} {'CARD':<20} {'TIME (s)':>10}")
    print(f"{'─' * 20} {'─' * 20} {'─' * 10}")
    for engine, card, secs in timings:
        print(f"{engine:<20} {card:<20} {secs:>10.2f}")
    print(f"{'─' * 20} {'─' * 20} {'─' * 10}")
    for engine_name in dict.fromkeys(e for e, _, _ in timings):
        avg = sum(s for e, _, s in timings if e == engine_name) / len(CARDS)
        print(f"{engine_name:<20} {'AVERAGE':<20} {avg:>10.2f}")


if __name__ == "__main__":
    main()
