from __future__ import annotations

import sqlite3


RIVALRY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rivalries (
    week_key TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    user_a INTEGER NOT NULL,
    user_b INTEGER NOT NULL,
    pk_times INTEGER NOT NULL DEFAULT 0,
    a_win_count INTEGER NOT NULL DEFAULT 0,
    b_win_count INTEGER NOT NULL DEFAULT 0,
    yinpa_a_to_b INTEGER NOT NULL DEFAULT 0,
    yinpa_b_to_a INTEGER NOT NULL DEFAULT 0,
    last_interaction_at INTEGER NOT NULL,
    PRIMARY KEY (week_key, group_id, user_a, user_b)
);

CREATE INDEX IF NOT EXISTS idx_rivalries_group_week_a
ON rivalries (group_id, week_key, user_a);

CREATE INDEX IF NOT EXISTS idx_rivalries_group_week_b
ON rivalries (group_id, week_key, user_b);
"""


class ImpactStoreRivalryMixin:
    @staticmethod
    def _normalize_rivalry_pair(user_x: int, user_y: int) -> tuple[int, int]:
        return (user_x, user_y) if user_x < user_y else (user_y, user_x)

    def record_rivalry_pk(self, week_key: str, group_id: int, winner_id: int, loser_id: int) -> None:
        now_ts = self._now_ts()
        user_a, user_b = self._normalize_rivalry_pair(winner_id, loser_id)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO rivalries(week_key, group_id, user_a, user_b, last_interaction_at) VALUES (?, ?, ?, ?, ?)",
                (week_key, group_id, user_a, user_b, now_ts),
            )
            win_column = "a_win_count" if winner_id == user_a else "b_win_count"
            connection.execute(
                f"UPDATE rivalries SET pk_times = pk_times + 1, {win_column} = {win_column} + 1, last_interaction_at = ? "
                "WHERE week_key = ? AND group_id = ? AND user_a = ? AND user_b = ?",
                (now_ts, week_key, group_id, user_a, user_b),
            )

    def record_rivalry_yinpa(self, week_key: str, group_id: int, sender_id: int, target_id: int) -> None:
        now_ts = self._now_ts()
        user_a, user_b = self._normalize_rivalry_pair(sender_id, target_id)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO rivalries(week_key, group_id, user_a, user_b, last_interaction_at) VALUES (?, ?, ?, ?, ?)",
                (week_key, group_id, user_a, user_b, now_ts),
            )
            yinpa_column = "yinpa_a_to_b" if sender_id == user_a else "yinpa_b_to_a"
            connection.execute(
                f"UPDATE rivalries SET {yinpa_column} = {yinpa_column} + 1, last_interaction_at = ? "
                "WHERE week_key = ? AND group_id = ? AND user_a = ? AND user_b = ?",
                (now_ts, week_key, group_id, user_a, user_b),
            )

    def get_user_rival_summary(
        self,
        week_key: str,
        group_id: int,
        user_id: int,
        threshold: int,
    ) -> dict[str, object]:
        user_row = self.get_weekly_user_row(week_key, group_id, user_id)
        revenge_target = None if user_row is None else user_row["revenge_target_user_id"]
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM rivalries WHERE week_key = ? AND group_id = ? AND (user_a = ? OR user_b = ?)",
                (week_key, group_id, user_id, user_id),
            ).fetchall()
        rival_ids: list[int] = []
        targeting_me: tuple[int, int] | None = None
        i_target: tuple[int, int] | None = None
        for row in rows:
            opponent_id = int(row["user_b"] if int(row["user_a"]) == user_id else row["user_a"])
            if int(row["pk_times"]) >= threshold:
                rival_ids.append(opponent_id)
            if int(row["user_a"]) == user_id:
                outbound_score = int(row["a_win_count"]) + int(row["yinpa_a_to_b"])
                inbound_score = int(row["b_win_count"]) + int(row["yinpa_b_to_a"])
            else:
                outbound_score = int(row["b_win_count"]) + int(row["yinpa_b_to_a"])
                inbound_score = int(row["a_win_count"]) + int(row["yinpa_a_to_b"])
            if outbound_score > 0 and (i_target is None or outbound_score > i_target[1]):
                i_target = (opponent_id, outbound_score)
            if inbound_score > 0 and (targeting_me is None or inbound_score > targeting_me[1]):
                targeting_me = (opponent_id, inbound_score)
        return {
            "revenge_target": None if revenge_target is None else int(revenge_target),
            "rivals": rival_ids,
            "targeting_me": None if targeting_me is None else targeting_me[0],
            "i_target": None if i_target is None else i_target[0],
        }

    def get_recent_honor_weeks(self, group_id: int, limit_weeks: int) -> list[tuple[str, list[sqlite3.Row]]]:
        with self._connect() as connection:
            week_rows = connection.execute(
                "SELECT DISTINCT week_key FROM weekly_results WHERE group_id = ? ORDER BY week_key DESC LIMIT ?",
                (group_id, limit_weeks),
            ).fetchall()
            output: list[tuple[str, list[sqlite3.Row]]] = []
            for week_row in week_rows:
                week_key = str(week_row["week_key"])
                rows = connection.execute(
                    "SELECT * FROM weekly_results WHERE group_id = ? AND week_key = ? ORDER BY category ASC, rank_no ASC",
                    (group_id, week_key),
                ).fetchall()
                output.append((week_key, rows))
        return output
