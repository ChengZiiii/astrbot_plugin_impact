import pytest
import time
from astrbot_plugin_impact.impact_store import ImpactStore


def test_record_and_query_wife_sex(tmp_path):
    store = ImpactStore(data_dir=tmp_path)
    ts = int(time.time())
    store.record_wife_sex("u1", "g1", "w_abc", "u1", is_ntr=False, success=True, volume_ml=3.0, satisfaction=80, ts=ts)
    vol, cnt = store.get_wife_daily_injection("g1", "w_abc")
    assert vol == 3.0 and cnt == 1
    stats = store.get_wife_stats("g1", "w_abc")
    assert stats["total_count"] == 1 and stats["total_volume"] == 3.0


def test_daily_count_upsert(tmp_path):
    store = ImpactStore(data_dir=tmp_path)
    store.incr_daily_fuck_wife_count("u1")
    store.incr_daily_fuck_wife_count("u1")
    assert store.get_daily_fuck_wife_count("u1") == 2
