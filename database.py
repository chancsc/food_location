"""SQLite database operations for the food location store."""

import json
import sqlite3
from typing import Any, Optional


class FoodDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shops (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    shop_name        TEXT    NOT NULL,
                    food_types       TEXT    DEFAULT '[]',
                    location         TEXT,
                    address          TEXT,
                    google_maps_url  TEXT,
                    google_place_id  TEXT,
                    rating           REAL,
                    description      TEXT,
                    source_image     TEXT,
                    raw_extracted    TEXT,
                    created_at       TEXT    DEFAULT (datetime('now')),
                    updated_at       TEXT    DEFAULT (datetime('now'))
                )
            """)

    # ------------------------------------------------------------------ write

    def add_shop(
        self,
        extracted: dict[str, Any],
        google_info: Optional[dict[str, Any]] = None,
        source_image: Optional[str] = None,
    ) -> int:
        food_types = extracted.get("food_types") or []
        if isinstance(food_types, str):
            food_types = [food_types]
        food_types_json = json.dumps(food_types, ensure_ascii=False)

        shop_name   = extracted.get("shop_name", "")
        location    = extracted.get("location") or ""
        address     = extracted.get("address") or ""
        description = extracted.get("description") or ""
        rating           = None
        google_maps_url  = None
        google_place_id  = None

        if google_info:
            rating          = google_info.get("rating")
            google_maps_url = google_info.get("google_maps_url")
            google_place_id = google_info.get("place_id")
            if not address:
                address = google_info.get("address") or ""
            if not location:
                location = google_info.get("location") or ""
            if not description:
                description = google_info.get("description") or ""

        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO shops
                   (shop_name, food_types, location, address,
                    google_maps_url, google_place_id, rating,
                    description, source_image, raw_extracted)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    shop_name, food_types_json, location, address,
                    google_maps_url, google_place_id, rating,
                    description, source_image,
                    json.dumps(extracted, ensure_ascii=False),
                ),
            )
            return cursor.lastrowid

    def update_google_info(self, shop_id: int, google_info: dict[str, Any]) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """UPDATE shops
                   SET google_maps_url = ?, google_place_id = ?, rating = ?,
                       address = COALESCE(NULLIF(address,''), ?),
                       description = COALESCE(NULLIF(description,''), ?),
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (
                    google_info.get("google_maps_url"),
                    google_info.get("place_id"),
                    google_info.get("rating"),
                    google_info.get("address"),
                    google_info.get("description"),
                    shop_id,
                ),
            )
            return cursor.rowcount > 0

    def delete_shop(self, shop_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
            return cursor.rowcount > 0

    # ------------------------------------------------------------------- read

    def get_shop(self, shop_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM shops WHERE id = ?", (shop_id,)
            ).fetchone()
            return dict(row) if row else None

    def search_shops(
        self,
        food_type: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[str] = []

        if food_type:
            conditions.append(
                "(food_types LIKE ? OR shop_name LIKE ? OR description LIKE ?)"
            )
            params.extend([f"%{food_type}%"] * 3)

        if location:
            conditions.append("(location LIKE ? OR address LIKE ?)")
            params.extend([f"%{location}%", f"%{location}%"])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM shops {where} ORDER BY rating DESC, created_at DESC",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def list_shops(self, location: Optional[str] = None) -> list[dict[str, Any]]:
        return self.search_shops(location=location)
