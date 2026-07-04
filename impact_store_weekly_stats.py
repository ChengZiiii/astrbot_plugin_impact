from __future__ import annotations

import sqlite3


WEEKLY_STATS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS weekly_stats (
    week_key TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    week_start_length REAL NOT NULL DEFAULT 0,
    current_length_snapshot REAL NOT NULL DEFAULT 0,
    week_growth_total REAL NOT NULL DEFAULT 0,
    positive_growth_count INTEGER NOT NULL DEFAULT 0,
    negative_growth_count INTEGER NOT NULL DEFAULT 0,
    dajiao_count INTEGER NOT NULL DEFAULT 0,
    suo_count INTEGER NOT NULL DEFAULT 0,
    query_count INTEGER NOT NULL DEFAULT 0,
    pk_count INTEGER NOT NULL DEFAULT 0,
    pk_win_count INTEGER NOT NULL DEFAULT 0,
    pk_lose_count INTEGER NOT NULL DEFAULT 0,
    pk_win_streak_best INTEGER NOT NULL DEFAULT 0,
    pk_lose_streak_best INTEGER NOT NULL DEFAULT 0,
    current_pk_win_streak INTEGER NOT NULL DEFAULT 0,
    current_pk_lose_streak INTEGER NOT NULL DEFAULT 0,
    yinpa_count INTEGER NOT NULL DEFAULT 0,
    inject_out_ml REAL NOT NULL DEFAULT 0,
    inject_in_ml REAL NOT NULL DEFAULT 0,
    total_action_count INTEGER NOT NULL DEFAULT 0,
    last_active_at INTEGER NOT NULL,
    revenge_target_user_id INTEGER,
    last_defeated_at INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (week_key, group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_weekly_stats_group_week
ON weekly_stats (group_id, week_key);
"""


class ImpactStoreWeeklyStatsMixin:
    def _touch_weekly_user_row(self, connection: sqlite3.Connection, week_key: str, group_id: int, user_id: int, current_length: float, now_ts: int) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO weekly_stats(week_key, group_id, user_id, week_start_length, current_length_snapshot, last_active_at) VALUES (?, ?, ?, ?, ?, ?)",
            (week_key, group_id, user_id, current_length, current_length, now_ts),
        )
        connection.execute(
            "UPDATE weekly_stats SET last_active_at = ? WHERE week_key = ? AND group_id = ? AND user_id = ?",
            (now_ts, week_key, group_id, user_id),
        )

    def touch_weekly_user(self, week_key: str, group_id: int, user_id: int, current_length: float) -> None:
        now_ts = self._now_ts()
        with self._connect() as connection:
            self._touch_weekly_user_row(connection, week_key, group_id, user_id, current_length, now_ts)

    def record_weekly_query(self, week_key: str, group_id: int, user_id: int, current_length: float) -> None:
        now_ts = self._now_ts()
        with self._connect() as connection:
            self._touch_weekly_user_row(connection, week_key, group_id, user_id, current_length, now_ts)
            connection.execute(
                "UPDATE weekly_stats SET query_count = query_count + 1, total_action_count = total_action_count + 1, current_length_snapshot = ?, last_active_at = ? WHERE week_key = ? AND group_id = ? AND user_id = ?",
                (current_length, now_ts, week_key, group_id, user_id),
            )

    def record_weekly_single_length_change(self, week_key: str, group_id: int, user_id: int, delta_cm: float, current_length: float, action_column: str | None, increment_total_action: bool) -> None:
        now_ts = self._now_ts()
        updates = ["current_length_snapshot = ?", "week_growth_total = week_growth_total + ?", "last_active_at = ?"]
        params: list[float | int | str] = [current_length, delta_cm, now_ts]
        if delta_cm > 0:
            updates.append("positive_growth_count = positive_growth_count + 1")
        elif delta_cm < 0:
            updates.append("negative_growth_count = negative_growth_count + 1")
        if action_column is not None:
            updates.append(f"{action_column} = {action_column} + 1")
        if increment_total_action:
            updates.append("total_action_count = total_action_count + 1")
        params.extend([week_key, group_id, user_id])
        with self._connect() as connection:
            self._touch_weekly_user_row(connection, week_key, group_id, user_id, current_length, now_ts)
            connection.execute(f"UPDATE weekly_stats SET {', '.join(updates)} WHERE week_key = ? AND group_id = ? AND user_id = ?", params)

    def record_weekly_pk_result(self, week_key: str, group_id: int, winner_id: int, loser_id: int, winner_delta_cm: float, loser_delta_cm: float, winner_current_length: float, loser_current_length: float) -> None:
        now_ts = self._now_ts()
        with self._connect() as connection:
            self._touch_weekly_user_row(connection, week_key, group_id, winner_id, winner_current_length, now_ts)
            self._touch_weekly_user_row(connection, week_key, group_id, loser_id, loser_current_length, now_ts)
            winner_growth_sql = ", positive_growth_count = positive_growth_count + 1" if winner_delta_cm > 0 else ", negative_growth_count = negative_growth_count + 1" if winner_delta_cm < 0 else ""
            loser_growth_sql = ", positive_growth_count = positive_growth_count + 1" if loser_delta_cm > 0 else ", negative_growth_count = negative_growth_count + 1" if loser_delta_cm < 0 else ""
            connection.execute(
                "UPDATE weekly_stats SET current_length_snapshot = ?, week_growth_total = week_growth_total + ?, "
                f"pk_count = pk_count + 1, pk_win_count = pk_win_count + 1{winner_growth_sql}, current_pk_win_streak = current_pk_win_streak + 1, current_pk_lose_streak = 0, pk_win_streak_best = MAX(pk_win_streak_best, current_pk_win_streak + 1), total_action_count = total_action_count + 1, last_active_at = ? WHERE week_key = ? AND group_id = ? AND user_id = ?",
                (winner_current_length, winner_delta_cm, now_ts, week_key, group_id, winner_id),
            )
            connection.execute(
                "UPDATE weekly_stats SET current_length_snapshot = ?, week_growth_total = week_growth_total + ?, "
                f"pk_count = pk_count + 1, pk_lose_count = pk_lose_count + 1{loser_growth_sql}, current_pk_lose_streak = current_pk_lose_streak + 1, current_pk_win_streak = 0, pk_lose_streak_best = MAX(pk_lose_streak_best, current_pk_lose_streak + 1), total_action_count = total_action_count + 1, revenge_target_user_id = ?, last_defeated_at = ?, last_active_at = ? WHERE week_key = ? AND group_id = ? AND user_id = ?",
                (loser_current_length, loser_delta_cm, winner_id, now_ts, now_ts, week_key, group_id, loser_id),
            )

    def record_weekly_yinpa(self, week_key: str, group_id: int, sender_id: int, target_id: int, volume_ml: float, sender_current_length: float, target_current_length: float) -> None:
        now_ts = self._now_ts()
        with self._connect() as connection:
            self._touch_weekly_user_row(connection, week_key, group_id, sender_id, sender_current_length, now_ts)
            self._touch_weekly_user_row(connection, week_key, group_id, target_id, target_current_length, now_ts)
            connection.execute(
                "UPDATE weekly_stats SET yinpa_count = yinpa_count + 1, inject_out_ml = inject_out_ml + ?, total_action_count = total_action_count + 1, current_length_snapshot = ?, last_active_at = ? WHERE week_key = ? AND group_id = ? AND user_id = ?",
                (volume_ml, sender_current_length, now_ts, week_key, group_id, sender_id),
            )
            connection.execute(
                "UPDATE weekly_stats SET inject_in_ml = inject_in_ml + ?, current_length_snapshot = ?, last_active_at = ? WHERE week_key = ? AND group_id = ? AND user_id = ?",
                (volume_ml, target_current_length, now_ts, week_key, group_id, target_id),
            )

    def get_weekly_stats_rows(self, week_key: str, group_id: int) -> list[sqlite3.Row]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM weekly_stats WHERE week_key = ? AND group_id = ? ORDER BY user_id ASC",
                (week_key, group_id),
            ).fetchall()
        return rows

    def get_weekly_user_row(self, week_key: str, group_id: int, user_id: int) -> sqlite3.Row | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM weekly_stats WHERE week_key = ? AND group_id = ? AND user_id = ?",
                (week_key, group_id, user_id),
            ).fetchone()
        return row
