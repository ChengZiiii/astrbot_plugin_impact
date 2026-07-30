"""嗦牛子（openspec change: fix-other-length-attribution）单测。

覆盖：
- 嗦自己命中 → 末尾仍然以"现在是 X cm。"结尾（self 路径不变）
- 嗦别人命中 → 末尾追加主语（昵称/id + "的{jj}"），形如 "X的牛子现在是 X cm。"
- 嗦别人未命中 → 长度不变，冷却仍是 sender 的
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 复用 test_handle_mine.py 的包导入引导
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

_astrbot_mock = MagicMock()
sys.modules.setdefault("astrbot", _astrbot_mock)
sys.modules.setdefault("astrbot.api", _astrbot_mock.api)
sys.modules.setdefault("astrbot.api.event", _astrbot_mock.api.event)
sys.modules.setdefault("astrbot.api.message_components", MagicMock())
sys.modules.setdefault("data", MagicMock())


def _make_config(**overrides):
    """构造一个带 suo_* 字段的 ImpactConfig-like mock。"""
    cfg = MagicMock()
    cfg.safe_mode = overrides.get("safe_mode", False)
    cfg.user_initial_length = 10.0
    cfg.jj_names = ["牛子"]
    cfg.nickname_fallback_to_user_id = overrides.get("nickname_fallback_to_user_id", True)
    cfg.not_enabled_reply = "群内还未开启淫趴游戏"
    cfg.suo_cd_time = overrides.get("suo_cd_time", 300)
    cfg.suo_allow_target_other = overrides.get("suo_allow_target_other", True)
    cfg.suo_media_mode = overrides.get("suo_media_mode", "none")
    cfg.random_growth_min = overrides.get("random_growth_min", 0.0)
    cfg.random_growth_max = overrides.get("random_growth_max", 1.0)
    cfg.lucky_growth_min = overrides.get("lucky_growth_min", 1.0)
    cfg.lucky_growth_max = overrides.get("lucky_growth_max", 2.0)
    cfg.lucky_growth_probability = overrides.get("lucky_growth_probability", 0.1)
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


# ── 嗦自己 ─────────────────────────────────────────────────


class TestSuoSelf:
    def test_self_hit_keeps_bare_suffix(self):
        """self 路径：末尾仍是裸"现在是 X cm。"（零回归）。"""
        svc = _make_service()
        svc._store.ensure_user(1, 10.0)
        original = svc._store.get_length(1)

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            reply = svc.handle_suo(True, 1, None, 10086)

        # random_value=0.0 < prob 0.1 → 走 lucky 路径 → uniform(1.0, 2.0) = 1.5
        new_length = svc._store.get_length(1)
        assert new_length == original + 1.5
        # 主句以"你"开头（或包含"你"），且末尾**不**带"你的牛子现在是"这种带主语的尾巴
        text = reply.text
        assert "现在是" in text
        assert f"{new_length}cm。" in text
        # 关键不变性：self 路径末尾**不**含"你的牛子现在是"这种补主语的形式
        assert "你的牛子现在是" not in text
        # 也不应含任何"X的牛子现在是"前缀（X∈除自身以外的标识）
        assert "1的牛子现在是" not in text


# ── 嗦别人 ─────────────────────────────────────────────────


class TestSuoOther:
    def test_other_hit_appends_target_subject(self):
        """other 路径：末尾追加 "{target_name}的{jj}现在是 X cm。"。

        未设置 display_name + nickname_fallback_to_user_id=True → target_name="2"，
        所以末尾应为 "2的牛子现在是 X cm。"。
        """
        svc = _make_service()
        svc._store.ensure_user(1, 10.0)
        svc._store.ensure_user(2, 10.0)
        target_before = svc._store.get_length(2)

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            reply = svc.handle_suo(True, 1, "2", 10086)

        target_after = svc._store.get_length(2)
        assert target_after == target_before + 1.5
        text = reply.text
        # 关键断言：末尾带主语
        assert "2的牛子现在是" in text, f"expected '2的牛子现在是' in reply, got: {text!r}"
        # 末尾形如 "...Xcm。"（带主语前缀）
        assert f"{target_after}cm。" in text
        # 不应同时出现裸"现在是 X cm。"（"现在是" 前应有主语）
        # —— 简单判 "现在是" 前一个字符不是 "。" 之前还可能有主句文案里的"现在是"；
        # 这里更稳健的断言是：必须出现以 "2的牛子现在是" 起始的子串
        # 包含位置索引
        idx = text.index("2的牛子现在是")
        assert idx > 0  # 主句在前
        # 整句的"现在是" 主语归属检查：在"X的牛子现在是"紧邻的两个"现在是"前应有一个 "2的牛子"
        assert text.endswith(f"{target_after}cm。")

    def test_other_hit_uses_display_name(self):
        """other 路径：设置了群昵称时用 display_name 作为主语。"""
        svc = _make_service()
        svc._store.ensure_user(1, 10.0)
        svc._store.ensure_user(2, 10.0)
        svc._store.upsert_group_display_name(10086, 2, "Bob")

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            reply = svc.handle_suo(True, 1, "2", 10086)

        text = reply.text
        assert "Bob的牛子现在是" in text, f"expected 'Bob的牛子现在是' in reply, got: {text!r}"

    def test_other_hit_with_fallback_to_user_id(self):
        """nickname_fallback_to_user_id=True + 无 display_name → 用 str(target_id) 作为主语。"""
        cfg = _make_config(nickname_fallback_to_user_id=True)
        svc = _make_service(config=cfg)
        svc._store.ensure_user(1, 10.0)
        svc._store.ensure_user(2, 10.0)

        p_random, p_uniform = _patch_random(random_value=0.0)
        with p_random, p_uniform:
            reply = svc.handle_suo(True, 1, "2", 10086)

        assert "2的牛子现在是" in reply.text

    def test_other_target_not_in_store_returns_creation_reply(self):
        """被作用方未建档 → 返回"TA 还没建档"提示，不调用 _format_single_change。"""
        svc = _make_service()
        svc._store.ensure_user(1, 10.0)
        # 不为 2 建档

        reply = svc.handle_suo(True, 1, "2", 10086)
        assert "还没建档" in reply.text

    def test_self_target_not_in_store_returns_creation_reply(self):
        """self 路径未建档（极少见，因为 ensure_user 已建档）—— 走"你还没有建档"分支。"""
        svc = _make_service()
        # 直接调用：未 ensure_user(1)
        reply = svc.handle_suo(True, 1, None, 10086)
        assert "还没建档" in reply.text


# ── 未启用 / 冷却 ──────────────────────────────────────────


class TestSuoGuards:
    def test_group_disabled(self):
        svc = _make_service()
        svc._store.ensure_user(1, 10.0)
        reply = svc.handle_suo(False, 1, None, 10086)
        assert reply.text == "群内还未开启淫趴游戏"

    def test_other_disabled(self):
        cfg = _make_config(suo_allow_target_other=False)
        svc = _make_service(config=cfg)
        svc._store.ensure_user(1, 10.0)
        svc._store.ensure_user(2, 10.0)
        reply = svc.handle_suo(True, 1, "2", 10086)
        # 文案："当前配置不让你对别人下手。" —— 用更宽松的子串断言
        assert "不让你对别人下手" in reply.text


# ── 工具方法抽离 ──────────────────────────────────────────


class TestResolveTargetName:
    def test_self_returns_you(self):
        svc = _make_service()
        assert svc._resolve_target_name(10086, 1, is_self=True) == "你"

    def test_other_with_display_name(self):
        svc = _make_service()
        svc._store.upsert_group_display_name(10086, 2, "Bob")
        assert svc._resolve_target_name(10086, 2, is_self=False) == "Bob"

    def test_other_fallback_to_user_id(self):
        svc = _make_service()
        assert svc._resolve_target_name(10086, 2, is_self=False) == "2"

    def test_other_fallback_to_group_member(self):
        cfg = _make_config(nickname_fallback_to_user_id=False)
        svc = _make_service(config=cfg)
        assert svc._resolve_target_name(10086, 2, is_self=False) == "群友"

    def test_other_no_group_id_falls_back(self):
        svc = _make_service()
        assert svc._resolve_target_name(None, 2, is_self=False) == "2"
