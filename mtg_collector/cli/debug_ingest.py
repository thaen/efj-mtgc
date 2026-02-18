"""debug-ingest command: show cached OCR and Claude responses for an image."""

import json
import sys

from mtg_collector.db import get_connection, init_db


def register(subparsers):
    parser = subparsers.add_parser(
        "debug-ingest",
        help="Show cached OCR fragments and Claude response for an ingested image",
    )
    parser.add_argument("--image", required=True, metavar="FILENAME", help="Image filename (basename)")
    parser.set_defaults(func=run)


def run(args):
    conn = get_connection(args.db_path)
    init_db(conn)

    row = conn.execute(
        "SELECT * FROM ingest_cache WHERE image_path LIKE ?",
        (f"%{args.image}",),
    ).fetchone()

    if row is None:
        print(f"Error: No cached entry found for image: {args.image}")
        sys.exit(1)

    print("=" * 70)
    print(f"IMAGE: {row['image_path']}")
    print(f"MD5:   {row['image_md5']}")
    print(f"CACHED AT: {row['created_at']}")

    print()
    print("=" * 70)
    print("OCR FRAGMENTS (raw)")
    print("=" * 70)
    ocr = json.loads(row["ocr_result"])
    for i, f in enumerate(ocr):
        b = f["bbox"]
        print(
            f"  [{i:3d}] conf={f['confidence']:.3f}  "
            f"x={int(b['x'])},y={int(b['y'])} w={int(b['w'])},h={int(b['h'])}  "
            f'"{f["text"]}"'
        )

    print()
    print("=" * 70)
    print("CLAUDE RESPONSE (raw JSON)")
    print("=" * 70)
    if row["claude_result"]:
        print(row["claude_result"])
        print()
        print("--- parsed ---")
        print(json.dumps(json.loads(row["claude_result"]), indent=2))
    else:
        print("(no Claude result cached)")
