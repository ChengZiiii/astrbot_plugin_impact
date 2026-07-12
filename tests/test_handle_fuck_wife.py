import sys
import time
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
# message_components 模块（impact_plugin_handlers 会导入）
sys.modules.setdefault("astrbot.api.message_components", MagicMock())


def _make_mock_interop(peek_result=None, resistance_result=None, record_result=None,
                       lifespan_result=None):
    """Create a mock animewifexI interop facade."""
    mock = MagicMock()
    mock.peek_wife = AsyncMock(return_value=peek_result or {})
    mock.compute_ntr_resistance = AsyncMock(return_value=resistance_result or {})
    mock.record_sex_act = AsyncMock(return_value=record_result or {"ok": True, "new_intimacy": 50})
    # Phase 6: 寿命扣减（默认走默认 mock，调用方按需改）
    if lifespan_result is None:
        lifespan_result = {
            "ok": True, "delta_applied": 0, "new_lifespan": -1,
            "death_occurred": False, "death_announce": "", "damage_announce": "",
            "wid": "", "wife_owner_uid": "", "wife_name": "", "wife_rarity": "",
        }
    mock.apply_lifespan_damage_from_impact = AsyncMock(return_value=lifespan_result)
    return mock


def _patch_interop(mock_interop):
    """Patch sys.modules so lazy import of get_wife_interop returns our mock."""
    mock_module = MagicMock()
    mock_module.get_wife_interop.return_value = mock_interop
    return patch.dict(sys.modules, {
        "data.plugins.astrbot_plugin_animewifexI": MagicMock(),
        "data.plugins.astrbot_plugin_animewifexI.app": MagicMock(),
        "data.plugins.astrbot_plugin_animewifexI.app.interop": mock_module,
    })


def _make_config(**overrides):
    """Create a minimal ImpactConfig-like mock with fuck_wife fields."""
    cfg = MagicMock()
    cfg.fuck_wife_enabled = True
    cfg.fuck_wife_base_possibility = overrides.get("base", 0.25)
    cfg.fuck_wife_cd_time = overrides.get("cd_time", 600)
    cfg.fuck_wife_daily_limit = overrides.get("daily_limit", 5)
    cfg.fuck_wife_volume_min = 1.0
    cfg.fuck_wife_volume_max = 5.0
    cfg.fuck_wife_charm_thresholds = (6.0, 12.0, 18.0, 36.0)
    cfg.fuck_wife_revenge_multiplier = 1.5
    cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)
    cfg.fuck_wife_ntr_notify = True
    cfg.fuck_wife_ntr_target_length_min = -50.0
    cfg.fuck_wife_ntr_target_length_max = 50.0
    cfg.fuck_wife_ntr_target_length_factor_min = 1.5
    cfg.fuck_wife_ntr_target_length_factor_max = 1.0
    cfg.fuck_wife_lifespan_damage_enabled = overrides.get("lifespan_damage_enabled", True)
    cfg.fuck_wife_lifespan_damage_threshold = overrides.get("lifespan_damage_threshold", 30.0)
    cfg.fuck_wife_lifespan_damage_ratio = overrides.get("lifespan_damage_ratio", 0.5)
    cfg.fuck_wife_lifespan_damage_max = overrides.get("lifespan_damage_max", 20)
    return cfg


def _make_service(config=None, store=None):
    """Create an ImpactService with in-memory store and mock config."""
    from astrbot_plugin_impact.impact_store import ImpactStore
    import tempfile

    if config is None:
        config = _make_config()
    if store is None:
        store = ImpactStore(data_dir=Path(tempfile.mkdtemp()))

    from astrbot_plugin_impact.impact_service import ImpactService
    svc = ImpactService(store, config)
    return svc


# ── Tests ──────────────────────────────────────────────────

class TestOwnWifeAlwaysSuccess:
    @pytest.mark.asyncio
    async def test_own_wife_always_success(self):
        peek_result = {
            "wid": "w1", "name": "TestWife", "source": "Test",
            "intimacy": 50, "level": 3, "level_name": "亲密",
            "is_primary": True,
        }
        mock_interop = _make_mock_interop(
            peek_result=peek_result,
            record_result={"ok": True, "new_intimacy": 52, "level": 3, "level_name": "亲密"},
        )

        with _patch_interop(mock_interop):
            svc = _make_service()
            svc._store.ensure_user(1, 10.0)  # seed user with 10cm → charm_tier=2
            res = await svc.handle_fuck_wife(True, "g1", "1", target_uid=None, normalized="日老婆")

        assert res.ok is True
        assert res.success is True
        assert res.is_ntr is False
        assert res.wife_wid == "w1"
        assert res.wife_name == "TestWife"
        assert res.intimacy_gain == 1  # tier2 → tiers[1]=1
        assert res.volume_ml > 0


class TestNtrLockedAutofails:
    @pytest.mark.asyncio
    async def test_ntr_locked_autofails(self):
        peek_result = {
            "wid": "w2", "name": "LockedWife", "source": "Test",
            "intimacy": 100, "level": 5, "level_name": "深爱",
            "is_primary": True,
        }
        resistance_result = {
            "resistance": 0.01, "locked": True, "shielded": True,
            "working": False, "newbie_protected": False,
            "has_charm": False, "target_owner_uid": "u_vic",
            "intimacy": 100, "level": 5,
        }
        mock_interop = _make_mock_interop(
            peek_result=peek_result,
            resistance_result=resistance_result,
        )

        with _patch_interop(mock_interop):
            svc = _make_service()
            res = await svc.handle_fuck_wife(True, "g1", "u_att", target_uid="u_vic", normalized="日老婆 @u_vic")

        assert res.ok is False
        assert res.reason == "target_locked"


class TestNtrSuccessAtHighRoll:
    @pytest.mark.asyncio
    async def test_ntr_success_at_high_roll(self):
        peek_result = {
            "wid": "w3", "name": "TargetWife", "source": "Test",
            "intimacy": 30, "level": 2, "level_name": "友好",
            "is_primary": True,
        }
        resistance_result = {
            "resistance": 1.0, "locked": False, "shielded": False,
            "working": False, "newbie_protected": False,
            "has_charm": False, "target_owner_uid": "u_vic",
            "intimacy": 30, "level": 2,
        }
        mock_interop = _make_mock_interop(
            peek_result=peek_result,
            resistance_result=resistance_result,
            record_result={"ok": True, "new_intimacy": 31, "level": 2, "level_name": "友好"},
        )

        with _patch_interop(mock_interop):
            svc = _make_service()
            # base=0.25, resistance=1.0, roll_seed=0.0 → success (0.0 < 0.25)
            res = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="u_vic",
                normalized="日老婆 @u_vic", roll_seed=0.0,
            )

        assert res.ok is True
        assert res.success is True
        assert res.is_ntr is True


class TestNtrFailAtLowRoll:
    @pytest.mark.asyncio
    async def test_ntr_fail_at_low_roll(self):
        peek_result = {
            "wid": "w3", "name": "TargetWife", "source": "Test",
            "intimacy": 30, "level": 2, "level_name": "友好",
            "is_primary": True,
        }
        resistance_result = {
            "resistance": 1.0, "locked": False, "shielded": False,
            "working": False, "newbie_protected": False,
            "has_charm": False, "target_owner_uid": "u_vic",
            "intimacy": 30, "level": 2,
        }
        mock_interop = _make_mock_interop(
            peek_result=peek_result,
            resistance_result=resistance_result,
        )

        with _patch_interop(mock_interop):
            svc = _make_service()
            # base=0.25, resistance=1.0, roll_seed=0.99 → fail (0.99 >= 0.25)
            res = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="u_vic",
                normalized="日老婆 @u_vic", roll_seed=0.99,
            )

        assert res.ok is True
        assert res.success is False
        assert res.is_ntr is True


class TestCooldownBlocks:
    @pytest.mark.asyncio
    async def test_cooldown_blocks(self):
        mock_interop = _make_mock_interop()

        with _patch_interop(mock_interop):
            svc = _make_service()
            # Set cooldown — sender just used it
            svc._fuck_wife_cd_data["u1"] = time.time()
            res = await svc.handle_fuck_wife(True, "g1", "u1", target_uid=None, normalized="日老婆")

        assert res.ok is False
        assert res.reason == "cooldown"


class TestDailyLimitBlocks:
    @pytest.mark.asyncio
    async def test_daily_limit_blocks(self):
        mock_interop = _make_mock_interop()

        with _patch_interop(mock_interop):
            svc = _make_service(config=_make_config(daily_limit=1))
            # Exhaust daily limit
            svc._store.incr_daily_fuck_wife_count("u1")
            res = await svc.handle_fuck_wife(True, "g1", "u1", target_uid=None, normalized="日老婆")

        assert res.ok is False
        assert res.reason == "daily_limit"


class TestNotEnabled:
    @pytest.mark.asyncio
    async def test_not_enabled(self):
        svc = _make_service()
        res = await svc.handle_fuck_wife(False, "g1", "u1", target_uid=None, normalized="日老婆")
        assert res.ok is False
        assert res.reason == "not_enabled"


class TestNoWife:
    @pytest.mark.asyncio
    async def test_own_wife_no_wife(self):
        mock_interop = _make_mock_interop(peek_result={})

        with _patch_interop(mock_interop):
            svc = _make_service()
            res = await svc.handle_fuck_wife(True, "g1", "u1", target_uid=None, normalized="日老婆")

        assert res.ok is False
        assert res.reason == "no_wife"


# ── Tests for _compute_target_length_factor ──────────────────────


class TestComputeTargetLengthFactor:
    """Pure-function tests for the linear length → factor mapping."""

    def test_min_endpoint_returns_factor_min(self):
        from astrbot_plugin_impact.impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
        f = ImpactServiceGameplaySupportMixin._compute_target_length_factor(
            target_length=-50.0,
            min_length=-50.0, max_length=50.0,
            factor_min=1.5, factor_max=1.0,
        )
        assert f == pytest.approx(1.5)

    def test_max_endpoint_returns_factor_max(self):
        from astrbot_plugin_impact.impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
        f = ImpactServiceGameplaySupportMixin._compute_target_length_factor(
            target_length=50.0,
            min_length=-50.0, max_length=50.0,
            factor_min=1.5, factor_max=1.0,
        )
        assert f == pytest.approx(1.0)

    def test_midpoint_returns_average(self):
        from astrbot_plugin_impact.impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
        f = ImpactServiceGameplaySupportMixin._compute_target_length_factor(
            target_length=0.0,
            min_length=-50.0, max_length=50.0,
            factor_min=1.5, factor_max=1.0,
        )
        assert f == pytest.approx(1.25)

    def test_below_min_clamps_to_factor_min(self):
        from astrbot_plugin_impact.impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
        f = ImpactServiceGameplaySupportMixin._compute_target_length_factor(
            target_length=-100.0,
            min_length=-50.0, max_length=50.0,
            factor_min=1.5, factor_max=1.0,
        )
        assert f == pytest.approx(1.5)

    def test_above_max_clamps_to_factor_max(self):
        from astrbot_plugin_impact.impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
        f = ImpactServiceGameplaySupportMixin._compute_target_length_factor(
            target_length=200.0,
            min_length=-50.0, max_length=50.0,
            factor_min=1.5, factor_max=1.0,
        )
        assert f == pytest.approx(1.0)

    def test_degenerate_range_returns_factor_max(self):
        """When min == max, avoid ZeroDivisionError by returning factor_max."""
        from astrbot_plugin_impact.impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
        f = ImpactServiceGameplaySupportMixin._compute_target_length_factor(
            target_length=10.0,
            min_length=50.0, max_length=50.0,
            factor_min=1.5, factor_max=1.0,
        )
        assert f == pytest.approx(1.0)

    def test_linear_progression(self):
        """Sanity: factor should drop linearly and monotonically as length increases."""
        from astrbot_plugin_impact.impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
        f1 = ImpactServiceGameplaySupportMixin._compute_target_length_factor(-25.0, -50.0, 50.0, 1.5, 1.0)
        f2 = ImpactServiceGameplaySupportMixin._compute_target_length_factor(0.0,   -50.0, 50.0, 1.5, 1.0)
        f3 = ImpactServiceGameplaySupportMixin._compute_target_length_factor(25.0,  -50.0, 50.0, 1.5, 1.0)
        assert f1 == pytest.approx(1.375)
        assert f2 == pytest.approx(1.25)
        assert f3 == pytest.approx(1.125)
        assert f1 > f2 > f3  # monotonic decreasing


# ── Pipeline integration: target length affects NTR success ───────


class TestNtrTargetLengthFactor:
    """Verify target owner's length changes NTR success probability."""

    def _make_cfg(self, **overrides):
        cfg = _make_config(**overrides)
        cfg.fuck_wife_ntr_target_length_min = overrides.get("min_l", -50.0)
        cfg.fuck_wife_ntr_target_length_max = overrides.get("max_l", 50.0)
        cfg.fuck_wife_ntr_target_length_factor_min = overrides.get("factor_min", 1.5)
        cfg.fuck_wife_ntr_target_length_factor_max = overrides.get("factor_max", 1.0)
        return cfg

    def _peek_resistance(self):
        peek = {"wid": "wN", "name": "T", "source": "T", "intimacy": 30, "level": 2,
                "level_name": "f", "is_primary": True}
        resistance = {"resistance": 1.0, "locked": False, "shielded": False, "working": False,
                      "newbie_protected": False, "has_charm": False, "target_owner_uid": "u_vic",
                      "intimacy": 30, "level": 2}
        return peek, resistance

    @pytest.mark.asyncio
    async def test_target_at_min_boosts_prob_to_0_375(self):
        """Target=-50 → factor=1.5 → prob=0.375. roll=0.26 → success."""
        peek, resistance = self._peek_resistance()
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result={"ok": True, "new_intimacy": 31})
        with _patch_interop(mock):
            cfg = self._make_cfg()
            svc = _make_service(config=cfg)
            svc._store.ensure_user(9001, -50.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="9001",
                normalized="日老婆 @9001", roll_seed=0.26,
            )
            assert res.success is True, "roll=0.26 < prob=0.375 should succeed"

    @pytest.mark.asyncio
    async def test_target_at_max_keeps_default_prob(self):
        """Target=+50 → factor=1.0 → prob=0.25. roll=0.26 → fail."""
        peek, resistance = self._peek_resistance()
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance)
        with _patch_interop(mock):
            cfg = self._make_cfg()
            svc = _make_service(config=cfg)
            svc._store.ensure_user(9001, 50.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="9001",
                normalized="日老婆 @9001", roll_seed=0.26,
            )
            assert res.success is False, "roll=0.26 >= prob=0.25 should fail"

    @pytest.mark.asyncio
    async def test_factor_min_one_disables_feature(self):
        """factor_min=1.0 → length has no effect. Target=-50 with roll=0.26 → fail."""
        peek, resistance = self._peek_resistance()
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance)
        with _patch_interop(mock):
            cfg = self._make_cfg(factor_min=1.0)
            svc = _make_service(config=cfg)
            svc._store.ensure_user(9001, -50.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="9001",
                normalized="日老婆 @9001", roll_seed=0.26,
            )
            assert res.success is False, "with factor_min=1.0, prob=0.25, roll=0.26 should fail"

    @pytest.mark.asyncio
    async def test_target_below_min_clamps_to_factor_min(self):
        """Target=-100 with min=-50 → clamped → factor=1.5 → prob=0.375. roll=0.26 → success."""
        peek, resistance = self._peek_resistance()
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result={"ok": True, "new_intimacy": 31})
        with _patch_interop(mock):
            cfg = self._make_cfg()
            svc = _make_service(config=cfg)
            svc._store.ensure_user(9001, -100.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="9001",
                normalized="日老婆 @9001", roll_seed=0.26,
            )
            assert res.success is True

    @pytest.mark.asyncio
    async def test_target_not_in_impact_store_uses_neutral_factor(self):
        """Target owner has never used impact → no row in users table.

        Pre-fix: get_length() raised ValueError, target_owner_length fell
        back to 0.0, length_factor became 1.25 → ALL unknown targets
        silently got +25% NTR bonus → short/long difference disappeared.

        Post-fix: length_factor falls back to 1.0 (neutral). roll=0.26
        against prob=0.25 (base) must fail, same as the no-effect baseline.
        """
        peek, resistance = self._peek_resistance()
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance)
        with _patch_interop(mock):
            cfg = self._make_cfg()
            svc = _make_service(config=cfg)
            # Note: NO ensure_user(9001, ...) — target is unknown to impact.
            res = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="9001",
                normalized="日老婆 @9001", roll_seed=0.26,
            )
            assert res.success is False, (
                "with neutral length_factor=1.0, prob=0.25, roll=0.26 should fail. "
                "If this passes, the fallback is back to inflating the probability."
            )

    @pytest.mark.asyncio
    async def test_target_not_in_impact_store_matches_factor_max_baseline(self):
        """Unknown target (length_factor=1.0) must match a known long target
        (length_factor=1.0) on the same roll. Regression guard against
        the two paths diverging again.
        """
        peek, resistance = self._peek_resistance()
        mock_unknown = _make_mock_interop(peek_result=peek, resistance_result=resistance)
        with _patch_interop(mock_unknown):
            cfg = self._make_cfg()
            svc = _make_service(config=cfg)
            # Don't ensure_user — target unknown
            r_unknown = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="9001",
                normalized="日老婆 @9001", roll_seed=0.42,
            )

        # Now reset and use a known long target (length=+50 → factor=1.0)
        peek, resistance = self._peek_resistance()
        mock_long = _make_mock_interop(peek_result=peek, resistance_result=resistance)
        with _patch_interop(mock_long):
            cfg = self._make_cfg()
            svc = _make_service(config=cfg)
            svc._store.ensure_user(9001, 50.0)
            r_long = await svc.handle_fuck_wife(
                True, "g1", "u_att", target_uid="9001",
                normalized="日老婆 @9001", roll_seed=0.42,
            )

        assert r_unknown.success == r_long.success, (
            f"unknown-target (len_factor=1.0) and known-long-target "
            f"(len_factor=1.0) must behave identically on the same roll. "
            f"Got unknown={r_unknown.success}, long={r_long.success}."
        )


# ==================== Phase 6 / 寿命系统联动测试 ====================


class TestLifespanDamage:
    """Phase 6: animewifexI 寿命系统联动 — 按丁丁尺寸扣减目标老婆寿命"""

    def _make_ntr_setup(self, sender_length=40.0, target_uid="u_victim", wife_name="Saber",
                        wife_rarity="SSR", lifespan_result=None):
        """构造 NTR success 路径的输入。"""
        peek = {
            "wid": "w_v", "name": wife_name, "rarity": wife_rarity,
            "intimacy": 50, "is_primary": True,
        }
        resistance = {
            "resistance": 1.0, "locked": False,
            "target_owner_uid": target_uid,
        }
        record = {"ok": True, "new_intimacy": 45}
        return peek, resistance, record, lifespan_result

    @pytest.mark.asyncio
    async def test_size_below_30_no_lifespan_call(self):
        """sender_length < 30 → 不调 interop lifespan（不扣寿命）"""
        peek, resistance, record, _ = self._make_ntr_setup(sender_length=25.0)
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance, record_result=record)
        cfg = _make_config()
        cfg.fuck_wife_charm_thresholds = (5.0, 15.0, 30.0, 50.0)
        cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)

        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            # 设置 sender 长度 < 30
            svc._store.ensure_user(1, 25.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )

        assert res.success
        # 关键：没调 apply_lifespan_damage_from_impact
        mock.apply_lifespan_damage_from_impact.assert_not_called()
        assert res.lifespan_damage == 0
        assert res.wife_death_occurred is False

    @pytest.mark.asyncio
    async def test_size_50_deducts_10_lifespan(self):
        """size=50 → delta = clamp((50-30)*0.5, 0, 20) = 10"""
        peek, resistance, record, _ = self._make_ntr_setup(sender_length=50.0)
        # lifespan_result 期望：size_delta=10
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance, record_result=record)
        cfg = _make_config()
        cfg.fuck_wife_charm_thresholds = (5.0, 15.0, 30.0, 50.0)
        cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)

        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 50.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )

        assert res.success
        # 调了 lifespan 接口
        mock.apply_lifespan_damage_from_impact.assert_called_once()
        call = mock.apply_lifespan_damage_from_impact.call_args
        # Phase 6.1: impact 用 positional (gid, wid, actor_uid) + kwarg (actor_nick, delta, owner_nick)
        call_args = call.args
        call_kwargs = call.kwargs
        assert call_args[0] == "g1"  # gid
        assert call_args[1] == "w_v"  # wid
        assert call_args[2] == "1"  # actor_uid (positional)
        # delta 参数：30→(50-30)*0.5 = 10
        assert call_kwargs["delta"] == 10
        assert call_kwargs["actor_nick"]  # 必填
        assert res.lifespan_damage == 0  # mock 返回的 delta_applied=0
        assert res.wife_new_lifespan == -1

    @pytest.mark.asyncio
    async def test_size_100_caps_at_20_lifespan(self):
        """size=100 → delta = clamp((100-30)*0.5, 0, 20) = 20（上限）"""
        peek, resistance, record, _ = self._make_ntr_setup(sender_length=100.0)
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance, record_result=record)
        cfg = _make_config()
        cfg.fuck_wife_charm_thresholds = (5.0, 15.0, 30.0, 50.0)
        cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)

        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 100.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )

        assert res.success
        call_kwargs = mock.apply_lifespan_damage_from_impact.call_args.kwargs
        # clamp 到 20
        assert call_kwargs["delta"] == 20
        assert call_kwargs["actor_nick"]

    @pytest.mark.asyncio
    async def test_lifespan_death_announce_propagated(self):
        """animewifexI 返回 death_announce → FuckWifeResult.lifespan_announce 也填上"""
        ls_result = {
            "ok": True, "delta_applied": 50, "new_lifespan": 0,
            "death_occurred": True,
            "death_announce": "💀 Alice 的 [Saber] SSR 实在撑不住了，被 Bob 活活玩死……",
            "damage_announce": "",
        }
        peek, resistance, record, _ = self._make_ntr_setup(
            sender_length=80.0, lifespan_result=ls_result,
        )
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result=record, lifespan_result=ls_result)
        cfg = _make_config()
        cfg.fuck_wife_charm_thresholds = (5.0, 15.0, 30.0, 50.0)
        cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)

        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 80.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )

        assert res.success
        assert res.wife_death_occurred is True
        assert res.wife_new_lifespan == 0
        assert "Saber" in res.lifespan_announce
        assert "Alice" in res.lifespan_announce
        assert "Bob" in res.lifespan_announce

    @pytest.mark.asyncio
    async def test_lifespan_damage_announce_propagated(self):
        """没死但扣了 → 走 damage_announce（lifespan_announce 也填上）"""
        ls_result = {
            "ok": True, "delta_applied": 5, "new_lifespan": 95,
            "death_occurred": False,
            "death_announce": "",
            "damage_announce": "💢 Alice 的 [Saber] SSR 脸色苍白……（寿命 -5）",
        }
        peek, resistance, record, _ = self._make_ntr_setup(
            sender_length=40.0, lifespan_result=ls_result,
        )
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result=record, lifespan_result=ls_result)
        cfg = _make_config()
        cfg.fuck_wife_charm_thresholds = (5.0, 15.0, 30.0, 50.0)
        cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)

        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 40.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )

        assert res.success
        assert res.wife_death_occurred is False
        assert res.lifespan_damage == 5
        assert res.wife_new_lifespan == 95
        # damage_announce 复制到 lifespan_announce（让 _format_fuck_wife_result 统一处理）
        assert "Alice" in res.lifespan_announce
        assert "寿命 -5" in res.lifespan_announce

    @pytest.mark.asyncio
    async def test_self_ri_no_lifespan_call(self):
        """自己 ri 自己 → 走 own-wife 路径，根本不会调 lifespan"""
        peek = {"wid": "w_self", "name": "SelfWife", "rarity": "N",
                "intimacy": 80, "is_primary": True}
        record = {"ok": True, "new_intimacy": 83}
        mock = _make_mock_interop(peek_result=peek, record_result=record)
        cfg = _make_config()
        cfg.fuck_wife_charm_thresholds = (5.0, 15.0, 30.0, 50.0)
        cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)

        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 50.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid=None,
                normalized="日老婆", roll_seed=0.0,
            )

        assert res.success
        assert res.is_ntr is False
        # 自己 ri 自己根本不调 lifespan
        mock.apply_lifespan_damage_from_impact.assert_not_called()
        assert res.lifespan_damage == 0

    @pytest.mark.asyncio
    async def test_ntr_fail_no_lifespan_call(self):
        """NTR 失败 → 不调 lifespan（不扣寿命）"""
        peek = {"wid": "w_v", "name": "Saber", "rarity": "SSR",
                "intimacy": 50, "is_primary": True}
        resistance = {"resistance": 1.0, "locked": False, "target_owner_uid": "u_victim"}
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance)
        cfg = _make_config()
        cfg.fuck_wife_charm_thresholds = (5.0, 15.0, 30.0, 50.0)
        cfg.fuck_wife_intimacy_gain_tiers = (-1, 1, 2, 3, 5)

        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 50.0)
            # roll_seed=0.99 → 大概率失败（prob=1.0；roll > prob = fail）
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.99,
            )

        assert res.success is False
        # 失败不调 lifespan
        mock.apply_lifespan_damage_from_impact.assert_not_called()
        assert res.lifespan_damage == 0


# ==================== Phase 6 / _format_fuck_wife_result 集成测试 ====================


class TestFormatLifespanTail:
    """_format_lifespan_tail 静态方法输出"""

    def test_death_returns_announce(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin
        from astrbot_plugin_impact.impact_models import FuckWifeResult
        res = FuckWifeResult(
            ok=True, success=True, is_ntr=True,
            wife_name="Saber", wife_rarity="SSR",
            owner_name="Alice", sender_length=80.0,
            wife_death_occurred=True,
            lifespan_announce="💀 Alice 的 [Saber] SSR 已离世",
        )
        out = ImpactPluginHandlersMixin._format_lifespan_tail(res)
        assert "💀" in out
        assert "Saber" in out
        assert "Alice" in out

    def test_damage_returns_warning(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin
        from astrbot_plugin_impact.impact_models import FuckWifeResult
        res = FuckWifeResult(
            ok=True, success=True, is_ntr=True,
            wife_name="Saber", wife_rarity="R",
            owner_name="Alice", sender_length=40.0,
            lifespan_damage=10, wife_new_lifespan=90,
            lifespan_announce="💢 Alice 的 [Saber] R 脸色苍白……（寿命 -10）",
        )
        out = ImpactPluginHandlersMixin._format_lifespan_tail(res)
        assert "寿命 -10" in out
        assert "剩 90" in out
        assert "Alice" in out

    def test_no_damage_returns_empty(self):
        from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin
        from astrbot_plugin_impact.impact_models import FuckWifeResult
        res = FuckWifeResult(
            ok=True, success=True, is_ntr=True,
            wife_name="Saber", sender_length=20.0,
            lifespan_damage=0,
        )
        out = ImpactPluginHandlersMixin._format_lifespan_tail(res)
        assert out == ""


# ==================== Phase 6 / 寿命损失公式配置驱动验证 ====================


class TestLifespanDamageFormulaConfigDriven:
    """验证寿命损失换算使用配置值而非硬编码。"""

    def _make_ntr_peek_resistance_record(self, sender_length: float = 50.0, lifespan_result: dict | None = None):
        peek = {
            "wid": "w_v", "name": "Saber", "rarity": "SSR",
            "intimacy": 50, "level": 3, "level_name": "亲密",
            "is_primary": True,
        }
        resistance = {
            "resistance": 1.0, "locked": False, "shielded": False,
            "working": False, "newbie_protected": False,
            "has_charm": False, "target_owner_uid": "u_victim",
            "intimacy": 50, "level": 3,
        }
        record = {"ok": True, "new_intimacy": 48, "level": 3, "level_name": "亲密"}
        if lifespan_result is None:
            lifespan_result = {
                "ok": True, "delta_applied": 0, "new_lifespan": -1,
                "death_occurred": False, "death_announce": "",
                "damage_announce": "", "wid": "w_v",
                "wife_owner_uid": "u_victim",
            }
        return peek, resistance, record, lifespan_result

    @pytest.mark.asyncio
    async def test_default_config_matches_old_hardcode(self):
        """默认配置下（30/0.5/20），size=50 → delta=10，保持向后兼容"""
        peek, resistance, record, ls_result = self._make_ntr_peek_resistance_record(
            sender_length=50.0,
            lifespan_result={
                "ok": True, "delta_applied": 10, "new_lifespan": 90,
                "death_occurred": False,
                "death_announce": "", "damage_announce": "",
                "wid": "w_v", "wife_owner_uid": "u_victim",
            },
        )
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result=record, lifespan_result=ls_result)
        cfg = _make_config()  # 默认配置：threshold=30, ratio=0.5, max=20
        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 50.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )
        assert res.success
        call_kwargs = mock.apply_lifespan_damage_from_impact.call_args.kwargs
        assert call_kwargs["delta"] == 10

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        """threshold=10 → size=20 → delta = (20-10)*0.5 = 5"""
        peek, resistance, record, ls_result = self._make_ntr_peek_resistance_record(
            sender_length=20.0,
            lifespan_result={
                "ok": True, "delta_applied": 5, "new_lifespan": 95,
                "death_occurred": False,
                "death_announce": "", "damage_announce": "",
                "wid": "w_v", "wife_owner_uid": "u_victim",
            },
        )
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result=record, lifespan_result=ls_result)
        cfg = _make_config(lifespan_damage_threshold=10.0)
        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 20.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )
        assert res.success
        call_kwargs = mock.apply_lifespan_damage_from_impact.call_args.kwargs
        assert call_kwargs["delta"] == 5

    @pytest.mark.asyncio
    async def test_custom_ratio(self):
        """ratio=1.0 → size=40 → (40-30)*1.0 = 10"""
        peek, resistance, record, ls_result = self._make_ntr_peek_resistance_record(
            sender_length=40.0,
            lifespan_result={
                "ok": True, "delta_applied": 10, "new_lifespan": 90,
                "death_occurred": False,
                "death_announce": "", "damage_announce": "",
                "wid": "w_v", "wife_owner_uid": "u_victim",
            },
        )
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result=record, lifespan_result=ls_result)
        cfg = _make_config(lifespan_damage_ratio=1.0)
        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 40.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )
        assert res.success
        call_kwargs = mock.apply_lifespan_damage_from_impact.call_args.kwargs
        assert call_kwargs["delta"] == 10

    @pytest.mark.asyncio
    async def test_custom_max(self):
        """max=5 → size=50 → (50-30)*0.5=10 → clamp(10,0,5)=5"""
        peek, resistance, record, ls_result = self._make_ntr_peek_resistance_record(
            sender_length=50.0,
            lifespan_result={
                "ok": True, "delta_applied": 5, "new_lifespan": 95,
                "death_occurred": False,
                "death_announce": "", "damage_announce": "",
                "wid": "w_v", "wife_owner_uid": "u_victim",
            },
        )
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance,
                                  record_result=record, lifespan_result=ls_result)
        cfg = _make_config(lifespan_damage_max=5)
        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 50.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )
        assert res.success
        call_kwargs = mock.apply_lifespan_damage_from_impact.call_args.kwargs
        assert call_kwargs["delta"] == 5

    @pytest.mark.asyncio
    async def test_disabled_no_lifespan_call(self):
        """启用关闭 → size=100 也不调 lifespan"""
        peek, resistance, record, _ = self._make_ntr_peek_resistance_record(sender_length=100.0)
        mock = _make_mock_interop(peek_result=peek, resistance_result=resistance, record_result=record)
        cfg = _make_config(lifespan_damage_enabled=False)
        with _patch_interop(mock):
            svc = _make_service(config=cfg)
            svc._store.ensure_user(1, 100.0)
            res = await svc.handle_fuck_wife(
                True, "g1", "1", target_uid="u_victim",
                normalized="日老婆 @u_victim", roll_seed=0.0,
            )
        assert res.success
        mock.apply_lifespan_damage_from_impact.assert_not_called()
        assert res.lifespan_damage == 0

