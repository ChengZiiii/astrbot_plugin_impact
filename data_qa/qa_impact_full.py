from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT.parent))

from astrbot_plugin_impact.impact_time import get_current_week_key
from impact_qa_support import ImpactHarness, assert_any_contains, assert_reply_count, drain_asyncio


DEFAULT_CONFIG = {
    "default_group_enabled": True,
    "private_chat_enabled": True,
    "rank_min_users": 2,
    "rank_top_count": 3,
    "rank_bottom_count": 2,
    "rank_image_enabled": False,
    "usage_image_enabled": False,
    "media_send_mode": "text_only",
    "djcdtime": 0,
    "pkcdtime": 0,
    "suocdtime": 0,
    "fuckcdtime": 0,
    "yinpa_require_member_api": False,
    "commands_enabled": [
        "dajiao",
        "suo",
        "query",
        "pk",
        "rank",
        "toggle",
        "yinpa",
        "inject",
        "help",
        "weekly_report",
        "last_weekly_report",
        "weekly_rank",
        "weekly_stats",
        "rival",
        "honor",
    ],
}


def assert_any_contains_one_of(replies: list[str], expected_values: tuple[str, ...]) -> None:
    for expected in expected_values:
        if any(expected in reply for reply in replies):
            return
    raise AssertionError(f"expected one of {expected_values!r} in replies: {replies!r}")


async def run_baseline(plugin_dir: Path) -> None:
    harness = ImpactHarness(plugin_dir=plugin_dir, config=DEFAULT_CONFIG, data_subdir="runtime_phase01")
    harness.add_user("10001", "Alice", admin=True)
    harness.add_user("10002", "Bob")
    harness.add_user("10003", "Carol")
    harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob"), ("10003", "Carol")])

    try:
        replies = await harness.send_group("10001", "淫趴介绍", "20001")
        assert_reply_count(replies)
        assert_any_contains(replies, "指令1")

        replies = await harness.send_group("10001", "打胶", "20001")
        assert_reply_count(replies)
        assert_any_contains_one_of(replies, ("创建", "打胶结束"))

        replies = await harness.send_group("10001", "打胶", "20001")
        assert_reply_count(replies)
        assert_any_contains(replies, "打胶结束")

        replies = await harness.send_group("10001", "嗦牛子", "20001")
        assert_reply_count(replies)
        assert_any_contains(replies, "嗦完之后")

        replies = await harness.send_group("10001", "查询", "20001")
        assert_reply_count(replies)
        assert_any_contains(replies, "你现在")

        replies = await harness.send_group("10001", "查询", "20001", at="10002")
        assert_reply_count(replies)
        assert_any_contains_one_of(replies, ("创建", "你现在"))

        replies = await harness.send_group("10003", "打胶", "20001")
        assert_reply_count(replies)

        replies = await harness.send_group("10001", "pk", "20001", at="10002")
        assert_reply_count(replies)
        assert_any_contains(replies, "对决")

        replies = await harness.send_group("10001", "jj排行榜", "20001")
        assert_reply_count(replies)
        assert_any_contains(replies, "排行榜")

        replies = await harness.send_group("10001", "日群友", "20001", at="10002")
        assert_reply_count(replies, minimum=2)
        assert_any_contains(replies, "注入")

        replies = await harness.send_group("10001", "注入查询", "20001", at="10002")
        assert_reply_count(replies)
        assert_any_contains(replies, "当日总被注射量")

        group_one_members = harness.store.get_group_rankings(20001)
        if {entry.user_id for entry in group_one_members} != {10001, 10002, 10003}:
            raise AssertionError(f"unexpected phase0 membership scope: {group_one_members!r}")

        await drain_asyncio()
        print("PASS phase0 baseline legacy commands")

        harness.set_group_members("20002", [("10001", "Alice"), ("10003", "Carol")])

        replies = await harness.send_group("10001", "查询", "20002")
        assert_reply_count(replies)

        group_one_ids = [entry.user_id for entry in harness.store.get_group_rankings(20001)]
        group_two_ids = [entry.user_id for entry in harness.store.get_group_rankings(20002)]
        if set(group_one_ids) != {10001, 10002, 10003}:
            raise AssertionError(f"group one rankings leaked: {group_one_ids!r}")
        if set(group_two_ids) != {10001}:
            raise AssertionError(f"group two rankings leaked: {group_two_ids!r}")

        replies = await harness.send_group("10001", "查询", "20002", at="10003")
        assert_reply_count(replies)
        group_two_after_at = [entry.user_id for entry in harness.store.get_group_rankings(20002)]
        if set(group_two_after_at) != {10001, 10003}:
            raise AssertionError(f"@ target was not registered into group two: {group_two_after_at!r}")

        replies = await harness.send_group("10001", "jj排行榜", "20002")
        assert_reply_count(replies)
        assert_any_contains(replies, "群内第")
        if any("Bob" in reply for reply in replies):
            raise AssertionError(f"group ranking should not include Bob in group two: {replies!r}")

        replies = await harness.send_private("10001", "jj排行榜")
        assert_reply_count(replies)
        assert_any_contains(replies, "你当前")
        assert_any_contains(replies, "全局排名")
        if any("群内" in reply for reply in replies):
            raise AssertionError(f"private rank should not mention group rank: {replies!r}")

        print("PASS phase1 group membership and rank semantics")
    finally:
        await harness.terminate()


async def run_phase_two(plugin_dir: Path) -> None:
    harness = ImpactHarness(plugin_dir=plugin_dir, config=DEFAULT_CONFIG, data_subdir="runtime_phase02")
    harness.add_user("10001", "Alice", admin=True)
    harness.add_user("10002", "Bob")
    harness.add_user("10003", "Carol")
    harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob"), ("10003", "Carol")])

    try:
        with patch("random.random", side_effect=[1.0, 1.0]), patch("random.uniform", return_value=1.0):
            await harness.send_group("10001", "打胶", "20001")

        with patch("random.random", side_effect=[1.0, 1.0]), patch("random.uniform", return_value=1.0):
            await harness.send_group("10001", "嗦牛子", "20001", at="10002")

        replies = await harness.send_group("10001", "查询", "20001")
        assert_reply_count(replies)
        replies = await harness.send_group("10001", "注入查询", "20001", at="10002")
        assert_reply_count(replies)

        with patch("random.random", side_effect=[1.0, 1.0]), patch("random.uniform", return_value=1.0):
            replies = await harness.send_group("10001", "pk", "20001", at="10002")
            assert_reply_count(replies)

        rows = harness.store.get_weekly_stats_rows(get_current_week_key(), 20001)
        stats_by_user = {int(row["user_id"]): row for row in rows}

        alice = stats_by_user[10001]
        bob = stats_by_user[10002]
        if int(alice["dajiao_count"]) != 1 or round(float(alice["week_growth_total"]), 3) != 1.5:
            raise AssertionError(f"unexpected dajiao stats for Alice: {dict(alice)!r}")
        if int(alice["suo_count"]) != 1 or int(alice["total_action_count"]) < 5:
            raise AssertionError(f"unexpected suo/action stats for Alice: {dict(alice)!r}")
        if int(alice["query_count"]) != 2:
            raise AssertionError(f"query and inject query should both count for Alice: {dict(alice)!r}")
        if int(alice["pk_count"]) != 1 or int(alice["pk_win_count"]) != 1:
            raise AssertionError(f"unexpected pk winner stats for Alice: {dict(alice)!r}")
        if int(alice["current_pk_win_streak"]) != 1 or int(alice["pk_win_streak_best"]) != 1:
            raise AssertionError(f"unexpected win streak stats for Alice: {dict(alice)!r}")

        if round(float(bob["week_growth_total"]), 3) != 0.0:
            raise AssertionError(f"unexpected Bob net growth after suo + pk: {dict(bob)!r}")
        if int(bob["pk_count"]) != 1 or int(bob["pk_lose_count"]) != 1:
            raise AssertionError(f"unexpected pk loser stats for Bob: {dict(bob)!r}")
        if int(bob["current_pk_lose_streak"]) != 1 or int(bob["pk_lose_streak_best"]) != 1:
            raise AssertionError(f"unexpected lose streak stats for Bob: {dict(bob)!r}")
        if int(bob["revenge_target_user_id"]) != 10001:
            raise AssertionError(f"Bob revenge target should be Alice: {dict(bob)!r}")

        with patch("random.random", side_effect=[1.0, 1.0]), patch("random.uniform", return_value=1.0):
            replies = await harness.send_group("10003", "pk", "20001", at="10002")
            assert_reply_count(replies)

        rows = harness.store.get_weekly_stats_rows(get_current_week_key(), 20001)
        stats_by_user = {int(row["user_id"]): row for row in rows}
        bob = stats_by_user[10002]
        carol = stats_by_user[10003]
        if int(bob["revenge_target_user_id"]) != 10003:
            raise AssertionError(f"Bob revenge target should update to Carol: {dict(bob)!r}")
        if int(carol["pk_win_count"]) != 1 or int(carol["current_pk_win_streak"]) != 1:
            raise AssertionError(f"Carol should have one PK win: {dict(carol)!r}")

        with patch("random.uniform", return_value=10.0):
            replies = await harness.send_group("10001", "日群友", "20001", at="10002")
            assert_reply_count(replies, minimum=2)

        rows = harness.store.get_weekly_stats_rows(get_current_week_key(), 20001)
        stats_by_user = {int(row["user_id"]): row for row in rows}
        alice = stats_by_user[10001]
        bob = stats_by_user[10002]
        if int(alice["yinpa_count"]) != 1 or round(float(alice["inject_out_ml"]), 3) != 10.0:
            raise AssertionError(f"unexpected yinpa output stats for Alice: {dict(alice)!r}")
        if round(float(bob["inject_in_ml"]), 3) != 10.0:
            raise AssertionError(f"unexpected yinpa input stats for Bob: {dict(bob)!r}")

        print("PASS phase2 weekly stats and revenge semantics")
    finally:
        await harness.terminate()


async def run_phase_three(plugin_dir: Path) -> None:
    harness = ImpactHarness(plugin_dir=plugin_dir, config=DEFAULT_CONFIG, data_subdir="runtime_phase03")
    harness.add_user("10001", "Alice", admin=True)
    harness.add_user("10002", "Bob")
    harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob")])

    try:
        with harness.freeze_time("2026-07-05 10:00:00"):
            replies = await harness.send_group("10001", "查询", "20001")
            assert_reply_count(replies)
            replies = await harness.send_group("10001", "本周周报", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "2026-W27")
            assert_any_contains(replies, "【本群本周周报】")
            assert_any_contains(replies, "长度第一")
            assert_any_contains(replies, "涨得最多")
            assert_any_contains(replies, "干得最猛")
            assert_any_contains(replies, "最倒霉")
            assert_any_contains(replies, "掉得最多")

            hidden_alias_replies = await harness.send_group("10001", "周榜", "20001")
            assert_reply_count(hidden_alias_replies)
            assert_any_contains(hidden_alias_replies, "【本群本周周报】")

        with harness.freeze_time("2026-07-06 10:00:00"):
            proactive_messages = await harness.run_scheduled_weekly_report_once()
            if len(proactive_messages) != 1:
                raise AssertionError(f"expected one proactive weekly report, got {proactive_messages!r}")
            proactive_umo, proactive_text = proactive_messages[0]
            if proactive_umo != "qa:20001:10001":
                raise AssertionError(f"unexpected weekly report destination: {proactive_messages!r}")
            assert_any_contains([proactive_text], "周报")
            assert_any_contains([proactive_text], "2026-W27")
            assert_any_contains([proactive_text], "【本群上周周报】")

            latest_report = harness.store.get_latest_settled_report(20001)
            if latest_report is None:
                raise AssertionError("weekly report should exist after lazy settlement")
            settled_week_key, settled_report = latest_report
            results = harness.store.get_weekly_results(settled_week_key, 20001)
            if not results:
                raise AssertionError("weekly results should be stored together with report")

            replies = await harness.send_group("10001", "查询", "20001")
            assert_reply_count(replies)
            if any("周报" in reply for reply in replies):
                raise AssertionError(f"scheduled settlement should not inject report into normal command reply: {replies!r}")

            replies = await harness.send_group("10001", "本周周报", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, get_current_week_key())
            assert_any_contains(replies, "【本群本周周报】")

            replies = await harness.send_group("10001", "上周周报", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, settled_week_key)
            if not any(settled_report in reply for reply in replies):
                raise AssertionError(f"last weekly report command should return archived report: {replies!r}")

        print("PASS phase3 lazy settlement and weekly report/rank semantics")
    finally:
        await harness.terminate()


async def run_phase_four(plugin_dir: Path) -> None:
    harness = ImpactHarness(plugin_dir=plugin_dir, config=DEFAULT_CONFIG, data_subdir="runtime_phase04")
    harness.add_user("10001", "Alice", admin=True)
    harness.add_user("10002", "Bob")
    harness.add_user("10003", "Carol")
    harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob"), ("10003", "Carol")])

    try:
        with harness.freeze_time("2026-07-05 10:00:00"):
            for _ in range(3):
                with patch("random.random", side_effect=[1.0, 1.0]), patch("random.uniform", return_value=1.0):
                    replies = await harness.send_group("10001", "pk", "20001", at="10002")
                    assert_reply_count(replies)
            with patch("random.uniform", return_value=10.0):
                replies = await harness.send_group("10001", "日群友", "20001", at="10002")
                assert_reply_count(replies, minimum=2)

            replies = await harness.send_group("10001", "我的本周数据", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "我的本周数据")
            assert_any_contains(replies, "PK 场次 / 胜 / 负：3 / 3 / 0")

            replies = await harness.send_group("10002", "恩怨", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "复仇目标：Alice")
            assert_any_contains(replies, "本周宿敌：Alice")
            assert_any_contains(replies, "谁最常针对我：Alice")

            replies = await harness.send_group("10001", "我的宿敌", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "我最常针对谁：Bob")

        settlement_dates = [
            ("2026-06-08 10:00:00", "2026-06-15 10:00:00"),
            ("2026-06-15 10:00:00", "2026-06-22 10:00:00"),
            ("2026-06-22 10:00:00", "2026-06-29 10:00:00"),
            ("2026-06-29 10:00:00", "2026-07-06 10:00:00"),
        ]
        for active_dt, settle_dt in settlement_dates:
            with harness.freeze_time(active_dt):
                replies = await harness.send_group("10001", "查询", "20001")
                assert_reply_count(replies)
            with harness.freeze_time(settle_dt):
                replies = await harness.send_group("10001", "查询", "20001")
                assert_reply_count(replies)

        replies = await harness.send_group("10001", "荣誉墙", "20001")
        assert_reply_count(replies)
        assert_any_contains(replies, "群荣誉墙")
        honor_lines = [line for line in replies[0].splitlines() if line.startswith("2026-W")]
        if len(honor_lines) < 4:
            raise AssertionError(f"honor wall should include recent 4 settled weeks: {replies!r}")

        print("PASS phase4 rivalries, weekly stats view, and honor wall semantics")
    finally:
        await harness.terminate()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baseline QA for astrbot_plugin_impact")
    parser.add_argument(
        "--plugin-dir",
        default=str(PLUGIN_ROOT),
        help="Path to astrbot_plugin_impact root",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    plugin_path = Path(args.plugin_dir).resolve()

    async def main() -> None:
        await run_baseline(plugin_path)
        await run_phase_two(plugin_path)
        await run_phase_three(plugin_path)
        await run_phase_four(plugin_path)

    asyncio.run(main())
