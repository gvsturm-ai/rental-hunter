"""
SQLite database for tracking seen listings (deduplication).
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_address TEXT UNIQUE NOT NULL,
            original_address TEXT NOT NULL,
            price INTEGER,
            source TEXT NOT NULL,
            url TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_normalized_address
        ON seen_listings(normalized_address)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_source
        ON seen_listings(source)
    """)
    conn.commit()


def is_new_listing(normalized_address: str) -> bool:
    """Check if we've seen this listing before."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM seen_listings WHERE normalized_address = ?",
            (normalized_address,)
        )
        return cursor.fetchone() is None
    finally:
        conn.close()


def mark_as_seen(
    normalized_address: str,
    original_address: str,
    price: Optional[int],
    source: str,
    url: Optional[str]
) -> None:
    """Mark a listing as seen in the database."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    try:
        conn.execute("""
            INSERT INTO seen_listings
            (normalized_address, original_address, price, source, url, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(normalized_address) DO UPDATE SET
                last_seen_at = excluded.last_seen_at,
                price = excluded.price
        """, (normalized_address, original_address, price, source, url, now, now))
        conn.commit()
    finally:
        conn.close()


def get_stats() -> Dict[str, int]:
    """Get database statistics."""
    conn = get_connection()
    try:
        # Total count
        cursor = conn.execute("SELECT COUNT(*) as total FROM seen_listings")
        total = cursor.fetchone()["total"]

        # Count by source
        cursor = conn.execute("""
            SELECT source, COUNT(*) as count
            FROM seen_listings
            GROUP BY source
            ORDER BY count DESC
        """)
        by_source = {row["source"]: row["count"] for row in cursor.fetchall()}

        return {
            "total": total,
            "by_source": by_source
        }
    finally:
        conn.close()


def get_recent_listings(limit: int = 10) -> List[Dict]:
    """Get the most recently seen listings."""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT original_address, price, source, url, first_seen_at
            FROM seen_listings
            ORDER BY first_seen_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def clear_database() -> int:
    """Clear all listings from database. Returns count of deleted rows."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM seen_listings")
        count = cursor.rowcount
        conn.commit()
        return count
    finally:
        conn.close()
