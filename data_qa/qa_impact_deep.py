from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT.parent))

from astrbot_plugin_impact.impact_time import get_current_week_key
from impact_qa_support import ImpactHarness, assert_any_contains, assert_reply_count
from qa_impact_full import DEFAULT_CONFIG, run_baseline, run_phase_four, run_phase_three, run_phase_two


LOG_PATH = PLUGIN_ROOT / "data_qa" / "qa_run.log"


class _Tee:
    def __init__(self, *streams) -> None:
        self._streams = streams

    def write(self, data: str) -> None:
        for stream in self._streams:
            stream.write(data)
            stream.flush()

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


def assert_no_reply(replies: list[str]) -> None:
    if replies:
        raise AssertionError(f"expected no replies, got {replies!r}")


def log_case(title: str, replies: list[str]) -> None:
    print(f"CASE {title}")
    for reply in replies:
        print(f"  -> {reply}")


async def run_deep_edges(plugin_dir: Path) -> None:
    harness = ImpactHarness(plugin_dir=plugin_dir, config=DEFAULT_CONFIG, data_subdir="runtime_phase06")
    harness.add_user("10001", "Alice", admin=True)
    harness.add_user("10002", "Bob")
    harness.add_user("10003", "Carol")
    harness.add_user("10004", "Dave")
    harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob"), ("10003", "Carol")])
    harness.set_group_members("20002", [("10001", "Alice"), ("10004", "Dave")])

    try:
        replies = await harness.send_private("10001", "周报")
        assert_reply_count(replies)
        assert_any_contains(replies, "群聊查看")
        log_case("私聊周报拦截", replies)

        cooldown_config = dict(DEFAULT_CONFIG)
        cooldown_config["djcdtime"] = 60
        cooldown_harness = ImpactHarness(plugin_dir=plugin_dir, config=cooldown_config, data_subdir="runtime_phase06_cooldown")
        cooldown_harness.add_user("10001", "Alice", admin=True)
        cooldown_harness.set_group_members("20001", [("10001", "Alice")])
        try:
            with cooldown_harness.freeze_time("2026-07-05 10:00:00"):
                replies = await cooldown_harness.send_group("10001", "打胶", "20001")
                assert_reply_count(replies)
                log_case("打胶冷却-首次", replies)
                replies = await cooldown_harness.send_group("10001", "打胶", "20001")
                assert_any_contains(replies, "请等待")
                log_case("打胶冷却-立即重试", replies)
            with cooldown_harness.freeze_time("2026-07-05 10:01:01"):
                replies = await cooldown_harness.send_group("10001", "打胶", "20001")
                assert_reply_count(replies)
                log_case("打胶冷却-过冷却后", replies)
        finally:
            await cooldown_harness.terminate()

        with harness.freeze_time("2026-07-03 10:00:00"):
            with patch("random.uniform", return_value=5.0):
                replies = await harness.send_group("10001", "日群友", "20001", at="10002")
                assert_reply_count(replies, minimum=2)
        with harness.freeze_time("2026-07-04 10:00:00"):
            with patch("random.uniform", return_value=7.0):
                replies = await harness.send_group("10001", "日群友", "20001", at="10002")
                assert_reply_count(replies, minimum=2)
                log_case("日群友@目标", replies)
            replies = await harness.send_group("10001", "注入查询 历史", "20001", at="10002")
            assert_reply_count(replies)
            assert_any_contains(replies, "历史总被注射量为12.0ml")
            log_case("注入查询历史", replies)

        replies = await harness.send_group("10001", "查询", "20001")
        assert_reply_count(replies)
        replies = await harness.send_group("10003", "查询", "20001")
        assert_reply_count(replies)
        replies = await harness.send_group("10001", "查询", "20002")
        assert_reply_count(replies)
        if set(entry.user_id for entry in harness.store.get_group_rankings(20001)) != {10001, 10002, 10003}:
            raise AssertionError("group 20001 membership scope mismatch")
        if set(entry.user_id for entry in harness.store.get_group_rankings(20002)) != {10001}:
            raise AssertionError("group 20002 membership scope mismatch")

        with harness.freeze_time("2026-07-05 10:00:00"):
            for _ in range(2):
                with patch("random.random", side_effect=[1.0, 1.0]), patch("random.uniform", return_value=1.0):
                    replies = await harness.send_group("10001", "pk", "20001", at="10002")
                    assert_reply_count(replies)
            replies = await harness.send_group("10002", "恩怨", "20001")
            assert_any_contains(replies, "本周宿敌：暂无")
            with patch("random.random", side_effect=[1.0, 1.0]), patch("random.uniform", return_value=1.0):
                replies = await harness.send_group("10001", "pk", "20001", at="10002")
                assert_reply_count(replies)
            replies = await harness.send_group("10002", "恩怨", "20001")
            assert_any_contains(replies, "本周宿敌：10001")

        empty_harness = ImpactHarness(plugin_dir=plugin_dir, config=DEFAULT_CONFIG, data_subdir="runtime_phase06_empty")
        empty_harness.add_user("10001", "Alice", admin=True)
        empty_harness.set_group_members("30001", [("10001", "Alice")])
        try:
            replies = await empty_harness.send_group("10001", "本周周报", "30001")
            assert_any_contains(replies, "这周还没闹出什么动静")
            replies = await empty_harness.send_group("10001", "上周周报", "30001")
            assert_any_contains(replies, "还没有能翻的上周周报")
        finally:
            await empty_harness.terminate()

        readme_text = (plugin_dir / "README.md").read_text(encoding="utf-8")
        schema = json.loads((plugin_dir / "_conf_schema.json").read_text(encoding="utf-8"))
        for command_text in ("本周周报", "上周周报", "牛子排行", "我的本周数据", "我的恩怨簿", "群荣誉墙"):
            if command_text not in readme_text:
                raise AssertionError(f"README missing command text: {command_text}")
        for config_key in ("weekly_rival_threshold", "honor_wall_weeks", "weekly_top_n"):
            if config_key not in schema:
                raise AssertionError(f"schema missing config key: {config_key}")

        nickname_harness = ImpactHarness(plugin_dir=plugin_dir, config=DEFAULT_CONFIG, data_subdir="runtime_phase13_names")
        nickname_harness.add_user("10001", "Alice", admin=True)
        nickname_harness.add_user("10002", "Bob")
        nickname_harness.set_group_members("20001", [("10001", "阿杰"), ("10002", "小白")])
        try:
            with nickname_harness.freeze_time("2026-07-05 10:00:00"):
                await nickname_harness.send_group("10001", "查询", "20001")
                await nickname_harness.send_group("10002", "查询", "20001")
                replies = await nickname_harness.send_group("10001", "本周周报", "20001")
                assert_any_contains(replies, "阿杰")
                assert_any_contains(replies, "小白")
                if any("10001" in reply or "10002" in reply for reply in replies):
                    raise AssertionError(f"weekly report leaked raw ids: {replies!r}")
        finally:
            await nickname_harness.terminate()

        replies = await harness.send_private("10001", "jj排行榜")
        assert_any_contains(replies, "全局排名")
        if any("群内排名" in reply for reply in replies):
            raise AssertionError(f"private rank should stay global-only: {replies!r}")
        log_case("私聊排行榜", replies)

        replies = await harness.send_group("10001", "周榜", "20001")
        assert_any_contains(replies, get_current_week_key())
        log_case("周榜文本", replies)

        with harness.freeze_time("2026-07-06 10:00:00"):
            await harness.send_group("10001", "查询", "20001")
        with harness.freeze_time("2026-07-13 10:00:00"):
            proactive = await harness.run_scheduled_weekly_report_once()
            if len(proactive) != 1:
                raise AssertionError(f"expected exactly one proactive weekly report, got {proactive!r}")
            proactive_umo, proactive_text = proactive[0]
            if not proactive_umo.startswith("qa:20001:"):
                raise AssertionError(f"unexpected proactive destination: {proactive!r}")
            if "周报" not in proactive_text or "2026-W28" not in proactive_text:
                raise AssertionError(f"unexpected proactive report body: {proactive!r}")
            print("CASE 周一定时播报")
            print(f"  -> {proactive_umo}")
            print(f"  -> {proactive_text}")

            proactive = await harness.run_scheduled_weekly_report_once()
            if proactive:
                raise AssertionError(f"scheduled weekly report should be idempotent within same monday window: {proactive!r}")
            print("CASE 周一定时播报幂等")
            print("  -> (no proactive message on second run)")

        custom_time_config = dict(DEFAULT_CONFIG)
        custom_time_config["weekly_broadcast_hour"] = 9
        custom_time_config["weekly_broadcast_minute"] = 30
        custom_time_harness = ImpactHarness(plugin_dir=plugin_dir, config=custom_time_config, data_subdir="runtime_phase12_broadcast_time")
        custom_time_harness.add_user("10001", "Alice", admin=True)
        custom_time_harness.set_group_members("20001", [("10001", "Alice")])
        try:
            with custom_time_harness.freeze_time("2026-07-06 10:00:00"):
                await custom_time_harness.send_group("10001", "查询", "20001")
            with custom_time_harness.freeze_time("2026-07-13 09:29:00"):
                proactive = await custom_time_harness.run_scheduled_weekly_report_once()
                if proactive:
                    raise AssertionError(f"custom broadcast should not trigger before configured minute: {proactive!r}")
            with custom_time_harness.freeze_time("2026-07-13 09:30:00"):
                proactive = await custom_time_harness.run_scheduled_weekly_report_once()
                if len(proactive) != 1:
                    raise AssertionError(f"custom broadcast should trigger at configured time: {proactive!r}")
                print("CASE 自定义播报时间")
                print(f"  -> {proactive[0][0]}")
                print(f"  -> {proactive[0][1]}")
        finally:
            await custom_time_harness.terminate()

        toggle_config = dict(DEFAULT_CONFIG)
        toggle_config["admin_only_toggle"] = True
        toggle_config["default_group_enabled"] = False
        toggle_harness = ImpactHarness(plugin_dir=plugin_dir, config=toggle_config, data_subdir="runtime_phase07_toggle")
        toggle_harness.add_user("10001", "Alice", admin=True)
        toggle_harness.add_user("10002", "Bob")
        toggle_harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob")])
        try:
            replies = await toggle_harness.send_group("10002", "开启淫趴", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "只有管理员或群主")
            log_case("非管理员切换开关", replies)

            replies = await toggle_harness.send_group("10001", "开启淫趴", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "功能已开启")
            log_case("管理员切换开关", replies)

            replies = await toggle_harness.send_group("10002", "查询", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "目前长度")
            log_case("开启后普通命令可用", replies)
        finally:
            await toggle_harness.terminate()

        gate_config = dict(DEFAULT_CONFIG)
        gate_config["enabled_groups"] = ["20001"]
        gate_config["disabled_groups"] = ["20002"]
        gate_harness = ImpactHarness(plugin_dir=plugin_dir, config=gate_config, data_subdir="runtime_phase08_gate")
        gate_harness.add_user("10001", "Alice", admin=True)
        gate_harness.set_group_members("20001", [("10001", "Alice")])
        gate_harness.set_group_members("20002", [("10001", "Alice")])
        gate_harness.set_group_members("20003", [("10001", "Alice")])
        try:
            replies = await gate_harness.send_group("10001", "查询", "20002")
            assert_reply_count(replies)
            assert_any_contains(replies, "黑名单禁用")
            log_case("群黑名单拦截", replies)

            replies = await gate_harness.send_group("10001", "查询", "20003")
            assert_reply_count(replies)
            assert_any_contains(replies, "不在插件白名单")
            log_case("群白名单拦截", replies)

            replies = await gate_harness.send_group("10001", "查询", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "目前长度")
            log_case("群白名单放行", replies)
        finally:
            await gate_harness.terminate()

        disabled_command_config = dict(DEFAULT_CONFIG)
        disabled_command_config["commands_enabled"] = ["query"]
        disabled_harness = ImpactHarness(plugin_dir=plugin_dir, config=disabled_command_config, data_subdir="runtime_phase09_commands")
        disabled_harness.add_user("10001", "Alice", admin=True)
        disabled_harness.set_group_members("20001", [("10001", "Alice")])
        try:
            replies = await disabled_harness.send_group("10001", "周报", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "已被插件配置禁用")
            print("CASE 禁用周报命令")
            print(f"  -> {replies[0]}")

            replies = await disabled_harness.send_group("10001", "查询", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "目前长度")
            log_case("保留查询命令", replies)
        finally:
            await disabled_harness.terminate()

        legacy_command_config = dict(DEFAULT_CONFIG)
        legacy_command_config["commands_enabled"] = [
            "dajiao",
            "suo",
            "query",
            "pk",
            "rank",
            "toggle",
            "yinpa",
            "inject",
            "help",
        ]
        legacy_harness = ImpactHarness(plugin_dir=plugin_dir, config=legacy_command_config, data_subdir="runtime_phase09_legacy_commands")
        legacy_harness.add_user("10001", "Alice", admin=True)
        legacy_harness.set_group_members("20001", [("10001", "Alice")])
        try:
            replies = await legacy_harness.send_group("10001", "周报", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "周报")
            log_case("旧配置兼容周报命令", replies)
        finally:
            await legacy_harness.terminate()

        image_config = dict(DEFAULT_CONFIG)
        image_config["rank_image_enabled"] = True
        image_config["usage_image_enabled"] = True
        image_harness = ImpactHarness(plugin_dir=plugin_dir, config=image_config, data_subdir="runtime_phase10_images")
        image_harness.add_user("10001", "Alice", admin=True)
        image_harness.add_user("10002", "Bob")
        image_harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob")])
        try:
            replies = await image_harness.send_group("10001", "淫趴介绍", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "[image:")
            log_case("帮助图片输出", replies)

            await image_harness.send_group("10001", "查询", "20001")
            await image_harness.send_group("10002", "查询", "20001")
            replies = await image_harness.send_group("10001", "jj排行榜", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "[image:")
            assert_any_contains(replies, "群内排名")
            log_case("排行榜图片输出", replies)
        finally:
            await image_harness.terminate()

        yinpa_config = dict(DEFAULT_CONFIG)
        yinpa_config["yinpa_allow_random_target"] = False
        yinpa_config["yinpa_allow_admin_target"] = False
        yinpa_harness = ImpactHarness(plugin_dir=plugin_dir, config=yinpa_config, data_subdir="runtime_phase11_yinpa")
        yinpa_harness.add_user("10001", "Alice", admin=True)
        yinpa_harness.add_user("10002", "Bob")
        yinpa_harness.add_user("10003", "Carol")
        yinpa_harness.set_group_members("20001", [("10001", "Alice"), ("10002", "Bob"), ("10003", "Carol")])
        yinpa_harness._bot.set_group_members(
            "20001",
            [
                {"user_id": 10001, "card": "Alice", "nickname": "Alice", "role": "owner"},
                {"user_id": 10002, "card": "Bob", "nickname": "Bob", "role": "member"},
                {"user_id": 10003, "card": "Carol", "nickname": "Carol", "role": "admin"},
            ],
        )
        try:
            replies = await yinpa_harness.send_group("10002", "日群友", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "没找到合适的目标")
            log_case("禁用随机群友目标", replies)

            replies = await yinpa_harness.send_group("10002", "日管理", "20001")
            assert_reply_count(replies)
            assert_any_contains(replies, "没找到合适的目标")
            log_case("禁用管理目标", replies)
        finally:
            await yinpa_harness.terminate()

        print("PASS phase6 deep coverage and consistency checks")
    finally:
        await harness.terminate()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deep QA for astrbot_plugin_impact")
    parser.add_argument("--plugin-dir", default=str(PLUGIN_ROOT), help="Path to astrbot_plugin_impact root")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    plugin_path = Path(args.plugin_dir).resolve()

    async def main() -> None:
        await run_baseline(plugin_path)
        await run_phase_two(plugin_path)
        await run_phase_three(plugin_path)
        await run_phase_four(plugin_path)
        await run_deep_edges(plugin_path)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", encoding="utf-8") as log_file:
        tee = _Tee(sys.stdout, log_file)
        with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
            asyncio.run(main())
