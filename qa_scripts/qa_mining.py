#!/usr/bin/env python3
"""QA for astrbot_plugin_impact 的挖矿（挖群友/挖矿）玩法。

复用 astrbot-qa 的 Harness（进程内加载真实插件、MockEvent 模拟群聊）。
impact 是 filter.event_message_type 老架构（无 registry），这里 patch
_validate_plugin 放行；消息入口 harness 能找到 handle_all_commands。

运行：python qa_scripts/qa_mining.py    （默认 --no-fresh，不会清掉 data_qa）
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import types

# QA 加载真实插件代码，但插件硬依赖 PIL（仅 avatar_gif 模板用到）。
# 跑挖矿 QA 不需要真正渲染 GIF，先 stub PIL 再加载插件，避免装依赖。
try:
    import PIL  # noqa: F401
except ModuleNotFoundError:
    _pil_image = types.ModuleType("PIL.Image")
    _pil_image.new = lambda *a, **k: None
    _pil_image.open = lambda *a, **k: None
    _pil_draw = types.ModuleType("PIL.ImageDraw")
    _pil_filter = types.ModuleType("PIL.ImageFilter")
    _pil_font = types.ModuleType("PIL.ImageFont")
    _pil = types.ModuleType("PIL")
    _pil.Image = _pil_image
    _pil.ImageDraw = _pil_draw
    _pil.ImageFilter = _pil_filter
    _pil.ImageFont = _pil_font
    sys.modules["PIL"] = _pil
    sys.modules["PIL.Image"] = _pil_image
    sys.modules["PIL.ImageDraw"] = _pil_draw
    sys.modules["PIL.ImageFilter"] = _pil_filter
    sys.modules["PIL.ImageFont"] = _pil_font

_SKILL_ROOT = r"C:\Users\Soren\Desktop\AgentWorkCommon\astrbot_plugins\skills\astrbot-qa"
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)
from references.harness import Harness  # noqa: E402

PLUGIN_DIR = r"C:\Users\Soren\Desktop\AgentWorkCommon\astrbot_plugins\astrbot_plugin_impact"

# impact 没有 registry；放行校验，让 harness 用 handle_all_commands 入口。
Harness._validate_plugin = lambda self: None  # type: ignore[assignment]


def _find_message_handler_impact(self):
    """impact 用 @filter.event_message_type 的 handle_all_commands，不是 registry。"""
    for name in ("handle_all_commands", "on_all_messages", "on_message", "handle_message"):
        fn = getattr(self.plugin, name, None)
        if callable(fn):
            return fn
    return None


Harness._find_message_handler = _find_message_handler_impact  # type: ignore[assignment]

# impact 的 _dispatch 对 group_id 做 int()，但 harness 给的是 "g1"。
# 用一个 QA 子类覆盖 get_group_id，把 "g1" 之类映射成数字串。
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import io  # noqa: E402
if getattr(sys.stdout, "encoding", "") != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import importlib  # noqa: E402
_plugin_parent = os.path.dirname(PLUGIN_DIR)
if _plugin_parent not in sys.path:
    sys.path.insert(0, _plugin_parent)
_plugin_basename = os.path.basename(PLUGIN_DIR)
_main_module = importlib.import_module(f"{_plugin_basename}.main")
ImpactPlugin = _main_module.ImpactPlugin

# harness 的 MockEvent.get_group_id / get_sender_id 返回 "g1"/"u1"，
# 而 impact 内部把它们当数字用（int(...)）。直接在 MockEvent 上 patch。
from references.harness import MockEvent  # noqa: E402


def _mock_get_group_id(self, *a, **k):
    return "1"


def _mock_get_sender_id(self, *a, **k):
    raw = str(self.sender_uid)
    return raw[1:] if raw.startswith("u") else raw


MockEvent.get_group_id = _mock_get_group_id
MockEvent.get_sender_id = _mock_get_sender_id
# impact 的 _extract_at_qq 用 event.get_messages() 找 At 组件
MockEvent.get_messages = lambda self: self.message_obj.message


# impact 内部把 at_id 当数字用；harness 的 At.qq 是 "u1"，需去前缀。
def _qa_extract_at_qq(self, event):
    for component in event.get_messages():
        if getattr(component, "__class__", None) and component.__class__.__name__ == "At":
            for attr in ("qq", "target", "user_id", "id"):
                cand = getattr(component, attr, None)
                if cand:
                    cand = str(cand)
                    return cand[1:] if cand.startswith("u") else cand
    return None


ImpactPluginQA = ImpactPlugin
# 让 harness 用我们的 QA 子类（它加载插件用内部模块名，getattr 找不到）。
_orig_find = Harness._find_plugin_class


def _find_plugin_class_qa(self, module, class_name):
    if class_name == "ImpactPluginQA":
        return ImpactPluginQA
    return _orig_find(self, module, class_name)


Harness._find_plugin_class = _find_plugin_class_qa  # type: ignore[assignment]


# 注意：harness 内部用 importlib.util 重新加载 main.py，
# 加载前对 ImpactPlugin 的 monkeypatch 会被丢弃。
# 因此对插件类的方法 patch 必须在 harness 创建之后（见 main()）。

CONFIG = {
    "default_group_enabled": True,
    "strict_command_match": True,
    "yinpa_allow_random_target": True,
    "yinpa_require_member_api": False,
    "safe_mode": False,
    "mine_cd_time": 300,
    "mine_self_prob": 1.0,
    "mine_self_change_range": (-1.0, 2.0),
    "mine_other_prob": 1.0,
    "mine_other_change_range": (-2.0, 1.0),
    "mine_other_notify": True,
    "mine_fluid_range": (1.0, 20.0),
    "mine_fluid_max_ratio_to_reserve": 1.0,
}

USERS = [
    ("u1", "Alice", True),
    ("u2", "Bob", False),
    ("u3", "Carol", False),
]


def _store(h: Harness):
    return h.plugin._store


def read_length(h: Harness, uid: str) -> float:
    return _store(h).get_length(int(uid[1:] if uid.startswith("u") else uid))


def read_injection(h: Harness, uid: str) -> float:
    return _store(h).get_today_injection(int(uid[1:] if uid.startswith("u") else uid))


def inject(h: Harness, uid: str, ml: float) -> None:
    """直接模拟 yinpa 注入（写入同一个 injections 今日行）。"""
    _store(h).add_injection(int(uid[1:] if uid.startswith("u") else uid), ml)


def reset_users(h: Harness) -> None:
    """每个场景前把三位用户重置到初始长度、清零今日注入、清空挖矿冷却，避免串扰。"""
    for uid, _, _ in USERS:
        i = int(uid[1:] if uid.startswith("u") else uid)
        _store(h).ensure_user(i, h.plugin._impact_config.user_initial_length)
        # 清零今日注入：用 consume 把剩余量挖光
        left = _store(h).get_today_injection(i)
        if left > 0:
            _store(h).consume_today_injection(i, left)
    # 清空挖矿冷却缓存（service 内存状态，reset_users 不重置）
    try:
        h.plugin._service._mine_cd_data.clear()
    except Exception:
        pass


readers = {"length": read_length, "injection": read_injection}


async def scenario_self(h: Harness) -> None:
    h.scenario("挖自己 - 被注入后被挖，命中长度变化且液体清零")
    reset_users(h)
    # 用 store.add_injection 模拟 yinpa 给 u1 注入（写入同一个 injections 今日行）
    inject(h, "u1", 5.0)
    h.assert_that("u1 今日注入 > 0", lambda: h.get_state("u1", "injection") > 0)
    len_before = h.get_state("u1", "length")
    random.seed(0.0)
    await h.send("u1", "挖矿")  # 挖自己
    h.expect_match(r"挖|液体|cm")
    # seed 0.0 → random.uniform(-1.0, 2.0) ≈ +0.262（确定性）
    h.assert_that("挖自己命中：长度变化 ≈ +0.262",
                  lambda: abs(h.get_state("u1", "length") - (len_before + 0.262)) < 1e-3)
    h.assert_that("挖自己后今日注入清零（不为负）",
                  lambda: h.get_state("u1", "injection") == 0.0)


async def scenario_other(h: Harness) -> None:
    h.scenario("挖别人 - 命中：对方长度变化 + @ 通知 + 液体清零")
    reset_users(h)
    inject(h, "u2", 5.0)  # u1 给 u2 注入
    h.assert_that("u2 今日注入 > 0", lambda: h.get_state("u2", "injection") > 0)
    u2_len_before = h.get_state("u2", "length")
    u3_len_before = h.get_state("u3", "length")
    random.seed(0.0)
    await h.send("u3", "挖矿", at="u2")
    h.expect_match(r"挖|液体|cm")
    # fix-other-length-attribution: other 路径末尾必须带主语归属
    # u2 没设 display_name → fallback str(target_id)="2" → 末尾含 "{2}的{jj}现在是"
    # (jj_name 是从 config.jj_names 随机抽的，所以用通配)
    h.expect_match(r"2的.+?现在是")
    # seed 0.0 → random.uniform(-2.0, 1.0) ≈ -0.262（确定性）
    h.assert_that("被挖者 u2 长度变化 ≈ -0.738",
                  lambda: abs(h.get_state("u2", "length") - (u2_len_before - 0.738)) < 1e-3)
    h.assert_that("挖矿者 u3 长度不变（隔离）",
                  lambda: abs(h.get_state("u3", "length") - u3_len_before) < 1e-6)
    h.assert_that("u2 今日注入清零（不为负）",
                  lambda: h.get_state("u2", "injection") == 0.0)


async def scenario_no_fluid(h: Harness) -> None:
    h.scenario("无液体 - 挖不到，长度不变，不通知")
    reset_users(h)  # u1 今日注入为 0
    u2_len_before = h.get_state("u2", "length")
    u1_len_before = h.get_state("u1", "length")
    random.seed(0.0)
    await h.send("u2", "挖矿", at="u1")
    h.expect_match(r"什么|没|掏|空")
    h.assert_that("u1 长度不变", lambda: abs(h.get_state("u1", "length") - u1_len_before) < 1e-6)
    h.assert_that("u2 长度不变", lambda: abs(h.get_state("u2", "length") - u2_len_before) < 1e-6)
    h.assert_that("u1 今日注入仍为 0（不为负）",
                  lambda: h.get_state("u1", "injection") == 0.0)


async def scenario_miss(h: Harness) -> None:
    h.scenario("挖到液体但未命中 - 长度不变，液体仍被挖走")
    reset_users(h)
    inject(h, "u3", 5.0)
    u3_inj = h.get_state("u3", "injection")
    u3_len_before = h.get_state("u3", "length")
    # ImpactConfig 是 frozen dataclass；service._config 也指向同一对象，需同步替换
    import dataclasses  # noqa: E402
    new_cfg = dataclasses.replace(h.plugin._impact_config, mine_self_prob=0.0)
    h.plugin._impact_config = new_cfg
    h.plugin._service._config = new_cfg
    random.seed(0.0)
    await h.send("u3", "挖矿")
    h.assert_that("u3 今日注入已扣减（>0 被挖走）",
                  lambda: h.get_state("u3", "injection") < u3_inj)
    h.assert_that("未命中：u3 长度不变",
                  lambda: abs(h.get_state("u3", "length") - u3_len_before) < 1e-6)
    new_cfg2 = dataclasses.replace(h.plugin._impact_config, mine_self_prob=1.0)
    h.plugin._impact_config = new_cfg2
    h.plugin._service._config = new_cfg2


async def scenario_isolation(h: Harness) -> None:
    h.scenario("隔离性 - 挖 u2 不污染 u1/u3 状态")
    reset_users(h)
    inject(h, "u2", 5.0)  # u1 给 u2 注入
    u1_len_before = h.get_state("u1", "length")
    u1_inj_before = h.get_state("u1", "injection")
    u3_len_before = h.get_state("u3", "length")
    u3_inj_before = h.get_state("u3", "injection")
    random.seed(0.0)
    await h.send("u1", "挖矿", at="u2")
    h.assert_isolation("u1 长度未被污染（挖别人不影响自己）",
                       lambda: h.get_state("u1", "length"), u1_len_before)
    h.assert_isolation("u1 注入未被污染", lambda: h.get_state("u1", "injection"), u1_inj_before)
    h.assert_isolation("u3 长度未被污染", lambda: h.get_state("u3", "length"), u3_len_before)
    h.assert_isolation("u3 注入未被污染", lambda: h.get_state("u3", "injection"), u3_inj_before)


async def scenario_conservation(h: Harness) -> None:
    h.scenario("守恒 - 挖矿只消耗今日注入，不凭空增减总注入")
    reset_users(h)
    total = lambda: (h.get_state("u1", "injection") + h.get_state("u2", "injection")
                     + h.get_state("u3", "injection"))
    inject(h, "u1", 5.0)  # 给 u1 注入
    before = h.snapshot(total)
    random.seed(0.0)
    await h.send("u3", "挖矿", at="u1")  # 挖 u1
    h.assert_that("总今日注入下降（被挖走）", lambda: total() < before)
    h.assert_that("总今日注入不为负", lambda: total() >= 0.0)
    # 复跑一次以满足 L5：守恒断言（液体被挖走不算守恒，但总量非负 + ≤ before 是不变量）
    reset_users(h)
    inject(h, "u1", 5.0)
    before2 = h.snapshot(total)
    random.seed(0.0)
    await h.send("u3", "挖矿", at="u1")
    h.assert_that("挖矿后总量非负", lambda: total() >= 0.0, level="L4")
    h.assert_that("挖矿后总量 ≤ before（不凭空产生）",
                  lambda: total() <= before2, level="L4")


async def main(plugin_dir: str, verbose: int, fresh: bool, seed: int) -> None:
    h = Harness(
        plugin_dir=plugin_dir,
        plugin_class_name="ImpactPluginQA",
        group_id="g1", bot_uid="bot",
        config=CONFIG,
        verbose=verbose,
        seed=seed,
        fresh=fresh,
    )
    for uid, nick, is_admin in USERS:
        h.add_user(uid, nick=nick, admin=is_admin)
    for name, fn in readers.items():
        h.register_state_reader(name, fn)
    # harness 加载时 importlib 重新加载了 main.py，得到的是独立 class 对象，
    # 在此对真实插件类打补丁（_extract_at_qq 去 "u" 前缀，使 at_id 是数字串）。
    def _qa_extract_at_qq_runtime(self, event):
        for component in event.get_messages():
            if getattr(component, "__class__", None) and component.__class__.__name__ == "At":
                for attr in ("qq", "target", "user_id", "id"):
                    cand = getattr(component, attr, None)
                    if cand:
                        cand = str(cand)
                        return cand[1:] if cand.startswith("u") else cand
        return None
    def _qa_extract_at_qq_runtime(self, event):
        # harness 的 At 是 stub 里的 _At；用 isinstance 判定更稳
        try:
            from astrbot.api.message_components import At as _At
        except Exception:
            _At = None
        for component in event.get_messages():
            is_at = (_At is not None and isinstance(component, _At)) or \
                    getattr(component, "__class__", type(component)).__name__.endswith("At")
            if is_at:
                for attr in ("qq", "target", "user_id", "id"):
                    cand = getattr(component, attr, None)
                    if cand:
                        cand = str(cand)
                        return cand[1:] if cand.startswith("u") else cand
        return None
    type(h.plugin)._extract_at_qq = _qa_extract_at_qq_runtime
    # harness 的 MockContext 没 send_message；挖别人命中会主动 @
    if not hasattr(h.plugin.context, "send_message"):
        async def _qa_send_message(*a, **k):
            return None
        h.plugin.context.send_message = _qa_send_message
    h.header("astrbot_plugin_impact - 挖矿玩法 QA")
    # 给所有模拟用户建档（真实流程里 _dispatch 会 register_group_members）
    for uid, _, _ in USERS:
        _store(h).ensure_user(int(uid[1:] if uid.startswith("u") else uid),
                              h.plugin._impact_config.user_initial_length)
    await scenario_self(h)
    await scenario_other(h)
    await scenario_no_fluid(h)
    await scenario_miss(h)
    await scenario_isolation(h)
    await scenario_conservation(h)
    h.report()
    await h.terminate()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="impact 挖矿 QA")
    p.add_argument("--plugin-dir", default=None,
                   help=f"path to plugin root (default: {PLUGIN_DIR})")
    p.add_argument("--verbose", type=int, default=1, choices=[0, 1, 2])
    p.add_argument("--no-fresh", action="store_true", default=True,
                   help="不要清 data_qa（保护其它 QA 资产）")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(
        plugin_dir=os.path.abspath(args.plugin_dir) if args.plugin_dir else PLUGIN_DIR,
        verbose=args.verbose,
        fresh=not args.no_fresh,
        seed=args.seed,
    ))
