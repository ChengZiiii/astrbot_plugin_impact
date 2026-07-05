from __future__ import annotations

DISPLAY_NAME_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS group_display_names (
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    last_seen_at INTEGER NOT NULL,
    PRIMARY KEY (group_id, user_id)
);
"""


class ImpactStoreDisplayNamesMixin:
    def upsert_group_display_name(self, group_id: int, user_id: int, display_name: str) -> None:
        normalized = display_name.strip()
        if not normalized:
            return
        now_ts = self._now_ts()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO group_display_names(group_id, user_id, display_name, last_seen_at) VALUES (?, ?, ?, ?)",
                (group_id, user_id, normalized, now_ts),
            )

    def get_group_display_name(self, group_id: int, user_id: int) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT display_name FROM group_display_names WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            ).fetchone()
        return None if row is None else str(row["display_name"])

    def get_group_display_names(self, group_id: int, user_ids: list[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        placeholders = ", ".join("?" for _ in user_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT user_id, display_name FROM group_display_names WHERE group_id = ? AND user_id IN ({placeholders})",
                (group_id, *user_ids),
            ).fetchall()
        return {int(row["user_id"]): str(row["display_name"]) for row in rows}
