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


def _make_mock_interop(peek_result=None, resistance_result=None, record_result=None):
    """Create a mock animewifexI interop facade."""
    mock = MagicMock()
    mock.peek_wife = AsyncMock(return_value=peek_result or {})
    mock.compute_ntr_resistance = AsyncMock(return_value=resistance_result or {})
    mock.record_sex_act = AsyncMock(return_value=record_result or {"ok": True, "new_intimacy": 50})
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
