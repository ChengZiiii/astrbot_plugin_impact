# Tasks

## 1. 机制层
- [x] 1.1 `impact_service_gameplay_support.py` `_format_single_change` 新增 keyword-only 参数 `current_subject: str = ""`，根据是否为空分支拼末尾
- [x] 1.2 抽 `_resolve_target_name(group_id, target_id, is_self)` 到 `ImpactServiceGameplaySupportMixin`（复用 MINE 的 `_mine_target_name` 逻辑）

## 2. 调用层
- [x] 2.1 `impact_service_gameplay.py` `handle_suo` 调用 `_format_single_change` 时按 `is_self` 传 `current_subject`
- [x] 2.2 `impact_service_gameplay.py` `handle_mine` 命中分支调用 `_format_single_change` 时按 `spec.is_self` 传 `current_subject`
- [x] 2.3 删除 `_mine_target_name`（已被 `_resolve_target_name` 取代）

## 3. 测试与验收
- [x] 3.1 `tests/test_handle_suo.py`：补强嗦别人的主语归属断言（如不存在则新建）
- [x] 3.2 `tests/test_handle_mine.py`：补强 `test_other_hit_changes_target_only` 的主语归属断言
- [x] 3.3 跑 `pytest -m "not integration"` 通过
- [x] 3.4 QA `qa_scripts/qa_mining.py` `scenario_other` 加正则断言；嗦的 QA 脚本视情况新建或并入挖矿 QA
- [x] 3.5 QA 跑通后 git commit（询问 sync.bat 由编排器处理）