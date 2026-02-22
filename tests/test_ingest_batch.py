"""
Tests for IngestBatchRepository and the v16→v17 schema migration.

Tests:
  1. Schema migration: v16→v17 creates ingest_batches table + batch_id column
  2. IngestBatchRepository CRUD: create, get, get_open, get_or_create_open
  3. At-most-1-open enforcement
  4. State transitions: close, confirm, invalid transitions
  5. list_all ordering and image counts
  6. get_batch_images

To run: uv run pytest tests/test_ingest_batch.py -v
"""

import sqlite3

import pytest

from mtg_collector.db.models import IngestBatchRepository
from mtg_collector.db.schema import SCHEMA_VERSION, get_current_version, init_db


@pytest.fixture
def conn():
    """Create a fresh in-memory database with current schema."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    """IngestBatchRepository on the test connection."""
    return IngestBatchRepository(conn)


# =============================================================================
# Schema migration tests
# =============================================================================

class TestSchemaMigration:
    def test_fresh_install_has_ingest_batches(self, conn):
        """Fresh install should have the ingest_batches table."""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ingest_batches'"
        )
        assert cursor.fetchone() is not None

    def test_fresh_install_has_batch_id_column(self, conn):
        """Fresh install should have batch_id column on ingest_images."""
        cursor = conn.execute("PRAGMA table_info(ingest_images)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "batch_id" in columns

    def test_schema_version_is_current(self, conn):
        """Schema version should be up to date."""
        assert get_current_version(conn) == SCHEMA_VERSION

    def test_migration_from_v17(self):
        """Simulate a v17 database and migrate to v18."""
        from mtg_collector.db.schema import _migrate_v17_to_v18

        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        # Create a minimal v17 schema with just ingest_images (no batch_id)
        c.executescript("""
            CREATE TABLE ingest_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                md5 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'READY_FOR_OCR',
                mode TEXT,
                ocr_result TEXT,
                claude_result TEXT,
                agent_trace TEXT,
                api_usage TEXT,
                scryfall_matches TEXT,
                crops TEXT,
                disambiguated TEXT,
                names_data TEXT,
                names_disambiguated TEXT,
                user_card_edits TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Run migration
        _migrate_v17_to_v18(c)
        c.commit()

        # Verify ingest_batches table exists
        cursor = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ingest_batches'"
        )
        assert cursor.fetchone() is not None

        # Verify batch_id column added
        cursor = c.execute("PRAGMA table_info(ingest_images)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "batch_id" in columns

        c.close()


# =============================================================================
# IngestBatchRepository CRUD tests
# =============================================================================

class TestIngestBatchRepository:
    def test_create_returns_id(self, repo, conn):
        batch_id = repo.create()
        assert isinstance(batch_id, int)
        assert batch_id > 0

    def test_get_returns_batch(self, repo, conn):
        batch_id = repo.create()
        conn.commit()
        batch = repo.get(batch_id)
        assert batch is not None
        assert batch.id == batch_id
        assert batch.status == "open"
        assert batch.opened_at is not None
        assert batch.closed_at is None

    def test_get_nonexistent_returns_none(self, repo):
        assert repo.get(9999) is None

    def test_get_open_returns_open_batch(self, repo, conn):
        batch_id = repo.create()
        conn.commit()
        batch = repo.get_open()
        assert batch is not None
        assert batch.id == batch_id
        assert batch.status == "open"

    def test_get_open_returns_none_when_none_open(self, repo):
        assert repo.get_open() is None

    def test_get_or_create_open_creates_when_none(self, repo, conn):
        batch = repo.get_or_create_open()
        assert batch is not None
        assert batch.status == "open"
        conn.commit()

    def test_get_or_create_open_returns_existing(self, repo, conn):
        batch1 = repo.get_or_create_open()
        conn.commit()
        batch2 = repo.get_or_create_open()
        assert batch1.id == batch2.id


class TestAtMostOneOpen:
    def test_create_raises_if_open_exists(self, repo, conn):
        repo.create()
        conn.commit()
        with pytest.raises(ValueError, match="open batch already exists"):
            repo.create()

    def test_create_succeeds_after_close(self, repo, conn):
        batch_id = repo.create()
        conn.commit()
        repo.close(batch_id)
        conn.commit()
        # Should work now
        batch_id2 = repo.create()
        assert batch_id2 != batch_id


class TestStateTransitions:
    def test_close_open_batch(self, repo, conn):
        batch_id = repo.create()
        conn.commit()
        repo.close(batch_id)
        conn.commit()
        batch = repo.get(batch_id)
        assert batch.status == "closed"
        assert batch.closed_at is not None

    def test_close_non_open_raises(self, repo, conn):
        batch_id = repo.create()
        conn.commit()
        repo.close(batch_id)
        conn.commit()
        with pytest.raises(ValueError, match="not 'open'"):
            repo.close(batch_id)

    def test_close_nonexistent_raises(self, repo):
        with pytest.raises(ValueError, match="not found"):
            repo.close(9999)

    def test_confirm_closed_batch(self, repo, conn):
        batch_id = repo.create()
        conn.commit()
        repo.close(batch_id)
        conn.commit()
        repo.confirm(batch_id)
        conn.commit()
        batch = repo.get(batch_id)
        assert batch.status == "confirmed"

    def test_confirm_open_raises(self, repo, conn):
        batch_id = repo.create()
        conn.commit()
        with pytest.raises(ValueError, match="not 'closed'"):
            repo.confirm(batch_id)

    def test_confirm_nonexistent_raises(self, repo):
        with pytest.raises(ValueError, match="not found"):
            repo.confirm(9999)


class TestListAndImages:
    def test_list_all_empty(self, repo):
        assert repo.list_all() == []

    def test_list_all_ordering(self, repo, conn):
        """Batches are listed by opened_at DESC."""
        b1 = repo.create()
        conn.commit()
        repo.close(b1)
        conn.commit()
        b2 = repo.create()
        conn.commit()

        batches = repo.list_all()
        assert len(batches) == 2
        # Most recent first
        assert batches[0]["id"] == b2
        assert batches[1]["id"] == b1

    def test_list_all_includes_image_count(self, repo, conn):
        from mtg_collector.utils import now_iso

        b1 = repo.create()
        conn.commit()
        ts = now_iso()
        # Add some images to this batch
        conn.execute(
            "INSERT INTO ingest_images (filename, stored_name, md5, status, batch_id, created_at, updated_at) VALUES (?, ?, ?, 'READY_FOR_OCR', ?, ?, ?)",
            ("test1.jpg", "test1.jpg", "abc123", b1, ts, ts),
        )
        conn.execute(
            "INSERT INTO ingest_images (filename, stored_name, md5, status, batch_id, created_at, updated_at) VALUES (?, ?, ?, 'READY_FOR_OCR', ?, ?, ?)",
            ("test2.jpg", "test2.jpg", "def456", b1, ts, ts),
        )
        conn.commit()

        batches = repo.list_all()
        assert batches[0]["image_count"] == 2

    def test_get_batch_images_empty(self, repo, conn):
        b1 = repo.create()
        conn.commit()
        assert repo.get_batch_images(b1) == []

    def test_get_batch_images_returns_images(self, repo, conn):
        from mtg_collector.utils import now_iso

        b1 = repo.create()
        conn.commit()
        ts = now_iso()
        conn.execute(
            "INSERT INTO ingest_images (filename, stored_name, md5, status, batch_id, created_at, updated_at) VALUES (?, ?, ?, 'READY_FOR_OCR', ?, ?, ?)",
            ("test1.jpg", "test1.jpg", "abc123", b1, ts, ts),
        )
        conn.commit()

        images = repo.get_batch_images(b1)
        assert len(images) == 1
        assert images[0]["filename"] == "test1.jpg"
        assert images[0]["batch_id"] == b1

    def test_get_batch_images_only_returns_batch_images(self, repo, conn):
        from mtg_collector.utils import now_iso

        b1 = repo.create()
        conn.commit()
        repo.close(b1)
        conn.commit()
        b2 = repo.create()
        conn.commit()

        ts = now_iso()
        conn.execute(
            "INSERT INTO ingest_images (filename, stored_name, md5, status, batch_id, created_at, updated_at) VALUES (?, ?, ?, 'READY_FOR_OCR', ?, ?, ?)",
            ("b1_img.jpg", "b1_img.jpg", "aaa", b1, ts, ts),
        )
        conn.execute(
            "INSERT INTO ingest_images (filename, stored_name, md5, status, batch_id, created_at, updated_at) VALUES (?, ?, ?, 'READY_FOR_OCR', ?, ?, ?)",
            ("b2_img.jpg", "b2_img.jpg", "bbb", b2, ts, ts),
        )
        conn.commit()

        b1_images = repo.get_batch_images(b1)
        b2_images = repo.get_batch_images(b2)
        assert len(b1_images) == 1
        assert b1_images[0]["filename"] == "b1_img.jpg"
        assert len(b2_images) == 1
        assert b2_images[0]["filename"] == "b2_img.jpg"
