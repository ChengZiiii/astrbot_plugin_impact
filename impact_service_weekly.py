from __future__ import annotations

from datetime import datetime

from .impact_models import PlainReply, WeeklyResultEntry
from .impact_time import get_current_week_key, get_previous_week_key


class ImpactServiceWeeklyMixin:
    def ensure_weekly_settlement(self, group_id: int, current_week_key: str) -> str | None:
        previous_week_key = get_previous_week_key(current_week_key)
        if self._store.get_weekly_report(previous_week_key, group_id) is not None:
            return None
        self._store.refresh_weekly_length_snapshots(previous_week_key, group_id)
        rows = self._store.get_weekly_stats_rows(previous_week_key, group_id)
        if not rows:
            return None
        results = self._build_weekly_results(rows)
        report_text = self._build_weekly_report(previous_week_key, rows, results)
        self._store.save_weekly_settlement(previous_week_key, group_id, results, report_text)
        return report_text

    def handle_weekly_report(self, group_id: int) -> PlainReply:
        week_key = get_current_week_key()
        self._store.refresh_weekly_length_snapshots(week_key, group_id)
        rows = self._store.get_weekly_stats_rows(week_key, group_id)
        if not rows:
            return PlainReply(f"【本群 {week_key} 周报】\n本周还没有人留下战绩喵")
        results = self._build_weekly_results(rows)
        return PlainReply(self._build_weekly_report(week_key, rows, results))

    def handle_last_weekly_report(self, group_id: int) -> PlainReply:
        report = self._store.get_latest_settled_report(group_id)
        if report is None:
            return PlainReply("本群目前还没有已结算周报喵")
        _, report_text = report
        return PlainReply(report_text)

    def should_run_scheduled_weekly_report(self) -> bool:
        now_value = datetime.now()
        current_week_key = get_current_week_key()
        if now_value.weekday() != 0:
            return False
        if now_value.hour != self._config.weekly_broadcast_hour or now_value.minute != self._config.weekly_broadcast_minute:
            return False
        if self._store.get_state_value("last_weekly_broadcast_week") == current_week_key:
            return False
        return True

    def mark_scheduled_weekly_report_sent(self, current_week_key: str) -> None:
        self._store.set_state_value("last_weekly_broadcast_week", current_week_key)

    def get_scheduled_weekly_report(self, group_id: int, current_week_key: str) -> str | None:
        return self.ensure_weekly_settlement(group_id, current_week_key)

    def handle_weekly_rank(self, group_id: int) -> PlainReply:
        week_key = get_current_week_key()
        self._store.refresh_weekly_length_snapshots(week_key, group_id)
        rows = self._store.get_weekly_stats_rows(week_key, group_id)
        if not rows:
            return PlainReply(f"【本群 {week_key} 周榜】\n本周还没有人留下战绩喵")
        results = self._build_weekly_results(rows)
        return PlainReply(self._build_weekly_rank_text(week_key, rows, results))

    def handle_my_weekly_stats(self, group_id: int, user_id: int) -> PlainReply:
        week_key = get_current_week_key()
        row = self._store.get_weekly_user_row(week_key, group_id, user_id)
        if row is None:
            return PlainReply("你这周在本群还没有周数据喵")
        rankings = self._store.get_group_rankings(group_id)
        rank_no = next(index + 1 for index, item in enumerate(rankings) if item.user_id == user_id)
        current_length = self._store.get_length(user_id)
        lines = [
            f"【我的周数据 {week_key}】",
            f"当前全局长度：{current_length}cm",
            f"当前群内排名：{rank_no}",
            f"本周净增长：{round(float(row['week_growth_total']), 3)}cm",
            f"正增长次数 / 负增长次数：{int(row['positive_growth_count'])} / {int(row['negative_growth_count'])}",
            f"打胶次数：{int(row['dajiao_count'])}",
            f"嗦牛子次数：{int(row['suo_count'])}",
            f"查询次数：{int(row['query_count'])}",
            f"PK 场次 / 胜 / 负：{int(row['pk_count'])} / {int(row['pk_win_count'])} / {int(row['pk_lose_count'])}",
            f"最佳连胜 / 最佳连败：{int(row['pk_win_streak_best'])} / {int(row['pk_lose_streak_best'])}",
            f"当前连胜 / 当前连败：{int(row['current_pk_win_streak'])} / {int(row['current_pk_lose_streak'])}",
            f"注入输出 / 受害总量：{round(float(row['inject_out_ml']), 3)}ml / {round(float(row['inject_in_ml']), 3)}ml",
            f"总交互次数：{int(row['total_action_count'])}",
        ]
        return PlainReply("\n".join(lines))

    def handle_my_rivals(self, group_id: int, user_id: int) -> PlainReply:
        week_key = get_current_week_key()
        summary = self._store.get_user_rival_summary(week_key, group_id, user_id, self._config.weekly_rival_threshold)
        revenge_target = summary["revenge_target"]
        rivals = summary["rivals"]
        targeting_me = summary["targeting_me"]
        i_target = summary["i_target"]
        if revenge_target is None and not rivals and targeting_me is None and i_target is None:
            return PlainReply("你这周还没和谁结下梁子喵")
        lines = [f"【我的恩怨 {week_key}】"]
        lines.append(f"复仇目标：{revenge_target if revenge_target is not None else '暂无'}")
        lines.append(f"本周宿敌：{', '.join(str(item) for item in rivals) if rivals else '暂无'}")
        lines.append(f"谁最常针对我：{targeting_me if targeting_me is not None else '暂无'}")
        lines.append(f"我最常针对谁：{i_target if i_target is not None else '暂无'}")
        return PlainReply("\n".join(lines))

    def handle_honor_wall(self, group_id: int) -> PlainReply:
        honor_weeks = self._store.get_recent_honor_weeks(group_id, self._config.honor_wall_weeks)
        if not honor_weeks:
            return PlainReply("本群目前还没有可展示的荣誉墙喵")
        lines = ["【群荣誉墙】"]
        for week_key, rows in honor_weeks:
            result_map = {(str(row["category"]), int(row["rank_no"])): row for row in rows}
            lines.append(
                f"{week_key} | 牛王 {self._format_honor_user(result_map.get(('length_top', 1)))} | "
                f"成长 {self._format_honor_user(result_map.get(('growth_top', 1)))} | "
                f"恶霸 {self._format_honor_user(result_map.get(('pk_top', 1)))} | "
                f"受害 {self._format_honor_user(result_map.get(('inject_in_top', 1)))}"
            )
        return PlainReply("\n".join(lines))

    def _build_weekly_results(self, rows: list[object]) -> list[WeeklyResultEntry]:
        top_n = self._config.weekly_top_n
        return [
            *self._pick_weekly_results("length_top", rows, lambda row: True, lambda row: (-float(row["current_length_snapshot"]), int(row["user_id"])), top_n, "current_length_snapshot"),
            *self._pick_weekly_results("growth_top", rows, lambda row: float(row["week_growth_total"]) > 0, lambda row: (-float(row["week_growth_total"]), int(row["user_id"])), top_n, "week_growth_total"),
            *self._pick_weekly_results("pk_top", rows, lambda row: int(row["pk_win_count"]) > 0, lambda row: (-int(row["pk_win_count"]), -int(row["pk_count"]), int(row["user_id"])), top_n, "pk_win_count"),
            *self._pick_weekly_results("inject_out_top", rows, lambda row: float(row["inject_out_ml"]) > 0, lambda row: (-float(row["inject_out_ml"]), int(row["user_id"])), top_n, "inject_out_ml"),
            *self._pick_weekly_results("inject_in_top", rows, lambda row: float(row["inject_in_ml"]) > 0, lambda row: (-float(row["inject_in_ml"]), int(row["user_id"])), top_n, "inject_in_ml"),
            *self._pick_weekly_results("worst_shrink", rows, lambda row: float(row["week_growth_total"]) < 0, lambda row: (float(row["week_growth_total"]), int(row["user_id"])), 1, "week_growth_total"),
        ]

    def _pick_weekly_results(self, category: str, rows: list[object], predicate, sort_key, limit: int, metric_field: str) -> list[WeeklyResultEntry]:
        filtered_rows = sorted((row for row in rows if predicate(row)), key=sort_key)[:limit]
        return [
            WeeklyResultEntry(
                category=category,
                rank_no=index,
                user_id=int(row["user_id"]),
                metric_value=float(row[metric_field]),
                title_text=self._weekly_title_map.get(category, {}).get(index),
            )
            for index, row in enumerate(filtered_rows, start=1)
        ]

    def _build_weekly_rank_text(self, week_key: str, rows: list[object], results: list[WeeklyResultEntry]) -> str:
        rows_by_user = {int(row["user_id"]): row for row in rows}
        lines = [f"【本群 {week_key} 周榜】"]
        lines.append(self._format_weekly_result_line("本周牛王", self._find_result(results, "length_top", 1), rows_by_user, "cm"))
        lines.append(self._format_weekly_result_line("本周成长之星", self._find_result(results, "growth_top", 1), rows_by_user, "cm", signed=True, empty_text="暂无成长之星"))
        lines.append(self._format_weekly_result_line("本周决斗恶霸", self._find_result(results, "pk_top", 1), rows_by_user, "胜", pk_mode=True, empty_text="本周没人约架"))
        lines.append(self._format_weekly_result_line("本周注入王", self._find_result(results, "inject_out_top", 1), rows_by_user, "ml", empty_text="本周无人输出"))
        lines.append(self._format_weekly_result_line("本周头号受害者", self._find_result(results, "inject_in_top", 1), rows_by_user, "ml", empty_text="本周无人受害"))
        lines.append(self._format_weekly_result_line("本周最惨选手", self._find_result(results, "worst_shrink", 1), rows_by_user, "cm", signed=True, empty_text="本周无人缩水"))
        return "\n".join(lines)

    def _build_weekly_report(self, week_key: str, rows: list[object], results: list[WeeklyResultEntry]) -> str:
        return self._build_weekly_rank_text(week_key, rows, results).replace("周榜", "周报", 1)

    def _format_weekly_result_line(
        self,
        label: str,
        result: WeeklyResultEntry | None,
        rows_by_user: dict[int, object],
        unit: str,
        signed: bool = False,
        pk_mode: bool = False,
        empty_text: str = "暂无数据",
    ) -> str:
        if result is None:
            return f"{label}：{empty_text}"
        if pk_mode:
            row = rows_by_user[result.user_id]
            return f"{label}：{result.user_id}（{int(row['pk_win_count'])}胜{int(row['pk_lose_count'])}负）"
        metric_value = round(result.metric_value, 3)
        metric_text = f"{metric_value:+g}{unit}" if signed else f"{metric_value:g}{unit}"
        return f"{label}：{result.user_id}（{metric_text}）"

    @staticmethod
    def _find_result(results: list[WeeklyResultEntry], category: str, rank_no: int) -> WeeklyResultEntry | None:
        for result in results:
            if result.category == category and result.rank_no == rank_no:
                return result
        return None

    @staticmethod
    def _format_honor_user(row: object | None) -> str:
        if row is None:
            return "暂无"
        return str(int(row["user_id"]))
