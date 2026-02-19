"""Requeue stuck ingest images: mtg ingest-requeue"""


from mtg_collector.db import get_connection
from mtg_collector.db.schema import init_db


def register(subparsers):
    """Register the ingest-requeue subcommand."""
    parser = subparsers.add_parser(
        "ingest-requeue",
        help="Reset stuck images back to READY_FOR_OCR so the server picks them up",
    )
    parser.add_argument(
        "--errors", action="store_true",
        help="Also reset ERROR images back to READY_FOR_OCR",
    )
    parser.add_argument(
        "--image",
        metavar="ID_OR_FILENAME",
        help="Reset a specific image by ID or filename substring, clearing all its artifacts",
    )
    parser.set_defaults(func=run)


def run(args):
    """Reset stuck or specific images back to READY_FOR_OCR."""
    from mtg_collector.cli.crack_pack_server import _reset_ingest_image
    from mtg_collector.utils import now_iso

    conn = get_connection(args.db_path)
    init_db(conn)

    now = now_iso()

    if args.image:
        target = args.image.strip()
        if target.isdigit():
            rows = conn.execute(
                "SELECT id, filename, md5, status FROM ingest_images WHERE id=?", (int(target),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, filename, md5, status FROM ingest_images WHERE filename LIKE ?",
                (f"%{target}%",),
            ).fetchall()

        if not rows:
            print(f"No image found matching: {target!r}")
            conn.close()
            return

        print(f"Requeuing {len(rows)} image(s):")
        for row in rows:
            print(f"  #{row['id']}  {row['filename']}  (was: {row['status']})")
            removed = _reset_ingest_image(conn, row['id'], row['md5'], now)
            if removed:
                print(f"    Removed {removed} previously ingested collection entry(ies).")

        conn.commit()
        conn.close()
        return

    # --- Default behaviour: reset stuck images ---

    processing = conn.execute(
        "SELECT id, filename, updated_at FROM ingest_images WHERE status='PROCESSING'"
    ).fetchall()
    if processing:
        print(f"Resetting {len(processing)} stuck PROCESSING image(s):")
        for row in processing:
            print(f"  #{row['id']}  {row['filename']}  (last updated: {row['updated_at']})")
        conn.execute(
            "UPDATE ingest_images SET status='READY_FOR_OCR', updated_at=? WHERE status='PROCESSING'",
            (now,),
        )
    else:
        print("No stuck PROCESSING images.")

    if args.errors:
        errors = conn.execute(
            "SELECT id, filename, error_message FROM ingest_images WHERE status='ERROR'"
        ).fetchall()
        if errors:
            print(f"Resetting {len(errors)} ERROR image(s):")
            for row in errors:
                print(f"  #{row['id']}  {row['filename']}  ({(row['error_message'] or '')[:80]})")
            conn.execute(
                "UPDATE ingest_images SET status='READY_FOR_OCR', error_message=NULL, updated_at=? WHERE status='ERROR'",
                (now,),
            )
        else:
            print("No ERROR images.")

    conn.commit()
    conn.close()
