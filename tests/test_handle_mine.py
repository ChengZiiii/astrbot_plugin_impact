"""挖矿玩法（openspec change: add-mining-feature）单测。

覆盖：
- 挖自己挖到液体命中 → 长度落在 [orig+range]，今日注入被减记
- 挖自己未命中 → 长度不变，但液体已减
- 挖别人命中 → target 变化、sender 不变，且 @ 通知被调用
- 目标今日无注入 → dug==0、长度不变、今日注入不为负
- 冷却内再次挖矿 → 什么都不变
- consume_today_injection 边界：want > available 返回 available 且剩余 = 0
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent dirs to path for package imports
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Mock astrbot module before any plugin imports
_astrbot_mock = MagicMock()
sys.modules.setdefault("astrbot", _astrbot_mock)
sys.modules.setdefault("astrbot.api", _astrbot_mock.api)
sys.modules.setdefault("astrbot.api.event", _astrbot_mock.api.event)
sys.modules.setdefault("astrbot.api.message_components", MagicMock())

# 挖矿不依赖 animewifexI interop，但 import 期间保持安全（与 fuck_wife 测试一致）
sys.modules.setdefault("data", MagicMock())


def _make_config(**overrides):
    """构造一个带 mine_* 字段的 ImpactConfig-like mock。"""
    cfg = MagicMock()
    cfg.safe_mode = overrides.get("safe_mode", False)
    cfg.user_initial_length = 10.0
    cfg.jj_names = ["牛子"]
    cfg.nickname_fallback_to_user_id = True
    cfg.not_enabled_reply = "群内还未开启淫趴游戏"
    cfg.mine_cd_time = overrides.get("mine_cd_time", 300)
    cfg.mine_self_prob = overrides.get("mine_self_prob", 1.0)
    cfg.mine_self_change_range = overrides.get("mine_self_change_range", (-1.0, 2.0))
    cfg.mine_other_prob = overrides.get("mine_other_prob", 1.0)
    cfg.mine_other_change_range = overrides.get("mine_other_change_range", (-2.0, 1.0))
    cfg.mine_other_notify = overrides.get("mine_other_notify", True)
    cfg.mine_fluid_range = overrides.get("mine_fluid_range", (1.0, 20.0))
    cfg.mine_fluid_max_ratio_to_reserve = overrides.get("mine_fluid_max_ratio_to_reserve", 1.0)
    return cfg


def _make_service(config=None, store=None):
    from astrbot_plugin_impact.impact_service import ImpactService
    from astrbot_plugin_impact.impact_store import ImpactStore

    if config is None:
        config = _make_config()
    if store is None:
        store = ImpactStore(data_dir=Path(tempfile.mkdtemp()))
    return ImpactService(store, config)


def _mid_uniform(low, high):
    """确定性的 random.uniform 替身：取区间中点。"""
    return (low + high) / 2


def _patch_random(random_value=0.0, uniform=_mid_uniform):
    """同时定住 gameplay 模块用到的 random.random / random.uniform。"""
    return (
        patch("astrbot_plugin_impact.impact_service_gameplay.random.random", return_value=random_value),
        patch("astrbot_plugin_impact.impact_service_gameplay.random.uniform", side_effect=uniform),
    )


def _spec(target_id, is_self):
    from astrbot_plugin_impact.impact_models import MineTargetSpec

    return MineTargetSpec(vein_type="user", target_id=target_id, is_self=is_self)


# ── 挖自己 ─────────────────────────────────────────────────


class TestMineSelf:
    def test_self_hit_changes_length_within_range(self):
        svc = _make_service(_make_config(mine_self_prob=1.0, mine_self_change_range=(-1.0, 2.0)))
        svc._store.ensure_user(1, 10.0)
        svc._store.add_injection(1, 100.0)
        original = svc._store.get_length(1)

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            result = svc.handle_mine(True, 10086, 1, _spec(1, True), None)
            reply = result.reply

        dug = result.dug
        assert dug > 0
        assert reply is not None
        new_length = svc._store.get_length(1)
        assert original - 1.0 <= new_length <= original + 2.0
        assert new_length != original
        # 液体已被减记
        assert svc._store.get_today_injection(1) == round(100.0 - dug, 3)
        assert str(dug) in reply.text or f"{dug}" in reply.text

    def test_self_miss_keeps_length_but_consumes_fluid(self):
        svc = _make_service(_make_config(mine_self_prob=0.0))
        svc._store.ensure_user(1, 10.0)
        svc._store.add_injection(1, 100.0)
        original = svc._store.get_length(1)

        # random.random() = 0.5 >= prob 0.0 → 未命中
        p_random, p_uniform = _patch_random(random_value=0.5)
        with p_random, p_uniform:
            result = svc.handle_mine(True, 10086, 1, _spec(1, True), None)

        dug = result.dug
        assert dug > 0
        assert result.hit is False
        assert svc._store.get_length(1) == original
        assert svc._store.get_today_injection(1) == round(100.0 - dug, 3)

    def test_no_injection_digs_nothing(self):
        svc = _make_service()
        svc._store.ensure_user(1, 10.0)
        original = svc._store.get_length(1)

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            result = svc.handle_mine(True, 10086, 1, _spec(1, True), None)
            reply = result.reply

        assert result.dug == 0.0
        assert result.hit is False
        assert svc._store.get_length(1) == original
        # 不为负
        assert svc._store.get_today_injection(1) == 0.0
        assert reply.text


# ── 挖别人 ─────────────────────────────────────────────────


class TestMineOther:
    def test_other_hit_changes_target_only(self):
        svc = _make_service(_make_config(mine_other_prob=1.0, mine_other_change_range=(-2.0, 1.0)))
        svc._store.ensure_user(1, 10.0)
        svc._store.ensure_user(2, 10.0)
        svc._store.add_injection(2, 50.0)
        sender_before = svc._store.get_length(1)
        target_before = svc._store.get_length(2)

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            result = svc.handle_mine(True, 10086, 1, _spec(2, False), "2")

        assert result.dug > 0
        assert result.hit is True
        assert svc._store.get_length(1) == sender_before
        target_after = svc._store.get_length(2)
        assert target_after != target_before
        assert target_before - 2.0 <= target_after <= target_before + 1.0

    @pytest.mark.asyncio
    async def test_other_hit_notifies_target(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin

        config = _make_config(mine_other_notify=True)
        svc = _make_service(config)
        store = svc._store
        store.ensure_user(1, 10.0)
        store.ensure_user(2, 10.0)
        store.add_injection(2, 50.0)
        store.save_group_session(10086, "test:GroupMessage:10086")
        store.upsert_group_display_name(10086, 1, "挖矿佬")

        class _Handler(ImpactPluginHandlersMixin):
            def __init__(self):
                self._service = svc
                self._store = store
                self._impact_config = config
                self.context = MagicMock()
                self.context.send_message = AsyncMock()

        handler = _Handler()
        event = MagicMock()

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            reply = await handler._handle_mine(True, 10086, 1, "2", event)

        assert reply.text
        handler.context.send_message.assert_awaited_once()
        umo = handler.context.send_message.await_args.args[0]
        assert umo == "test:GroupMessage:10086"

    @pytest.mark.asyncio
    async def test_notify_disabled_sends_nothing(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin

        config = _make_config(mine_other_notify=False)
        svc = _make_service(config)
        store = svc._store
        store.ensure_user(1, 10.0)
        store.ensure_user(2, 10.0)
        store.add_injection(2, 50.0)
        store.save_group_session(10086, "test:GroupMessage:10086")

        class _Handler(ImpactPluginHandlersMixin):
            def __init__(self):
                self._service = svc
                self._store = store
                self._impact_config = config
                self.context = MagicMock()
                self.context.send_message = AsyncMock()

        handler = _Handler()

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            await handler._handle_mine(True, 10086, 1, "2", MagicMock())

        handler.context.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_fluid_sends_no_notify(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin

        config = _make_config(mine_other_notify=True)
        svc = _make_service(config)
        store = svc._store
        store.ensure_user(1, 10.0)
        store.ensure_user(2, 10.0)
        store.save_group_session(10086, "test:GroupMessage:10086")

        class _Handler(ImpactPluginHandlersMixin):
            def __init__(self):
                self._service = svc
                self._store = store
                self._impact_config = config
                self.context = MagicMock()
                self.context.send_message = AsyncMock()

        handler = _Handler()

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            await handler._handle_mine(True, 10086, 1, "2", MagicMock())

        handler.context.send_message.assert_not_awaited()


# ── 冷却 ───────────────────────────────────────────────────


class TestMineCooldown:
    def test_second_mine_in_cooldown_changes_nothing(self):
        svc = _make_service(_make_config(mine_cd_time=300, mine_self_prob=1.0))
        svc._store.ensure_user(1, 10.0)
        svc._store.add_injection(1, 100.0)

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            svc.handle_mine(True, 10086, 1, _spec(1, True), None)
            length_after_first = svc._store.get_length(1)
            fluid_after_first = svc._store.get_today_injection(1)
            reply = svc.handle_mine(True, 10086, 1, _spec(1, True), None).reply

        assert "秒" in reply.text
        assert svc._store.get_length(1) == length_after_first
        assert svc._store.get_today_injection(1) == fluid_after_first


# ── 目标解析 ───────────────────────────────────────────────


class TestResolveMineTarget:
    def test_no_at_targets_self(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin

        spec = ImpactPluginHandlersMixin._resolve_mine_target(MagicMock(), None, 1)
        assert spec.vein_type == "user"
        assert spec.target_id == 1
        assert spec.is_self is True

    def test_at_targets_other(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin

        spec = ImpactPluginHandlersMixin._resolve_mine_target(MagicMock(), "2", 1)
        assert spec.vein_type == "user"
        assert spec.target_id == 2
        assert spec.is_self is False


# ── 存储层边界 ─────────────────────────────────────────────


class TestConsumeTodayInjection:
    def test_want_greater_than_available_returns_available(self):
        from astrbot_plugin_impact.impact_store import ImpactStore

        store = ImpactStore(data_dir=Path(tempfile.mkdtemp()))
        store.add_injection(1, 7.5)
        dug = store.consume_today_injection(1, 100.0)
        assert dug == 7.5
        assert store.get_today_injection(1) == 0.0

    def test_partial_consume_keeps_remainder(self):
        from astrbot_plugin_impact.impact_store import ImpactStore

        store = ImpactStore(data_dir=Path(tempfile.mkdtemp()))
        store.add_injection(1, 10.0)
        dug = store.consume_today_injection(1, 4.0)
        assert dug == 4.0
        assert store.get_today_injection(1) == 6.0

    def test_no_row_returns_zero(self):
        from astrbot_plugin_impact.impact_store import ImpactStore

        store = ImpactStore(data_dir=Path(tempfile.mkdtemp()))
        assert store.consume_today_injection(999, 10.0) == 0.0
        assert store.get_today_injection(999) == 0.0

    def test_negative_want_returns_zero(self):
        from astrbot_plugin_impact.impact_store import ImpactStore

        store = ImpactStore(data_dir=Path(tempfile.mkdtemp()))
        store.add_injection(1, 5.0)
        assert store.consume_today_injection(1, -3.0) == 0.0
        assert store.get_today_injection(1) == 5.0


# ── 配置解析 ───────────────────────────────────────────────


class TestMineConfig:
    def test_defaults(self):
        from astrbot_plugin_impact.impact_config import DEFAULT_COMMANDS, ImpactConfig

        cfg = ImpactConfig.from_dict({})
        assert cfg.mine_cd_time == 300
        assert cfg.mine_self_prob == 0.7
        assert cfg.mine_self_change_range == (-1.0, 2.0)
        assert cfg.mine_other_prob == 0.5
        assert cfg.mine_other_change_range == (-2.0, 1.0)
        assert cfg.mine_other_notify is True
        assert cfg.mine_fluid_range == (1.0, 20.0)
        assert cfg.mine_fluid_max_ratio_to_reserve == 1.0
        assert "mine" in DEFAULT_COMMANDS
        assert "mine" in cfg.commands_enabled

    def test_overrides(self):
        from astrbot_plugin_impact.impact_config import ImpactConfig

        cfg = ImpactConfig.from_dict({
            "minecdtime": 60,
            "mine_self_prob": 0.1,
            "mine_self_change_range": [-3, 3],
            "mine_other_prob": 0.2,
            "mine_other_change_range": "-5, 5",
            "mine_other_notify": False,
            "mine_fluid_range": [2.0, 4.0],
            "mine_fluid_max_ratio_to_reserve": 0.5,
        })
        assert cfg.mine_cd_time == 60
        assert cfg.mine_self_prob == 0.1
        assert cfg.mine_self_change_range == (-3.0, 3.0)
        assert cfg.mine_other_prob == 0.2
        assert cfg.mine_other_change_range == (-5.0, 5.0)
        assert cfg.mine_other_notify is False
        assert cfg.mine_fluid_range == (2.0, 4.0)
        assert cfg.mine_fluid_max_ratio_to_reserve == 0.5


class TestMineFluidCap:
    def test_ratio_caps_dug_amount(self):
        svc = _make_service(_make_config(
            mine_fluid_range=(100.0, 100.0),
            mine_fluid_max_ratio_to_reserve=0.25,
            mine_self_prob=0.0,
        ))
        svc._store.ensure_user(1, 10.0)
        svc._store.add_injection(1, 40.0)

        p_random, p_uniform = _patch_random(random_value=0.99)
        with p_random, p_uniform:
            result = svc.handle_mine(True, 10086, 1, _spec(1, True), None)

        # want=100，reserve=40，cap=10 → dug=10
        assert result.dug == 10.0
        assert svc._store.get_today_injection(1) == 30.0
