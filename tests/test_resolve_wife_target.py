import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

_astrbot_mock = MagicMock()
sys.modules.setdefault("astrbot", _astrbot_mock)
sys.modules.setdefault("astrbot.api", _astrbot_mock.api)
sys.modules.setdefault("astrbot.api.event", _astrbot_mock.api.event)
sys.modules.setdefault("astrbot.api.message_components", _astrbot_mock.api.message_components)

from astrbot_plugin_impact.impact_plugin_handlers import ImpactPluginHandlersMixin


@pytest.fixture
def handler():
    class _Stub(ImpactPluginHandlersMixin):
        pass
    return _Stub()


class TestResolveSelfNoIndex:
    def test_resolve_self_no_index(self, handler):
        owner, index = handler._resolve_wife_target(normalized="日老婆", at_id=None, sender_id=1)
        assert owner == "1"
        assert index is None


class TestResolveSelfWithIndex:
    def test_resolve_self_with_index(self, handler):
        owner, index = handler._resolve_wife_target(normalized="日老婆 2", at_id=None, sender_id=1)
        assert owner == "1"
        assert index == 2


class TestResolveAtTargetWithIndex:
    def test_resolve_at_target_with_index(self, handler):
        owner, index = handler._resolve_wife_target(normalized="日老婆 3", at_id="u_vic", sender_id=1)
        assert owner == "u_vic"
        assert index == 3


class TestResolveAtTargetNoIndex:
    def test_resolve_at_target_no_index(self, handler):
        owner, index = handler._resolve_wife_target(normalized="日老婆", at_id="u_vic", sender_id=1)
        assert owner == "u_vic"
        assert index is None
