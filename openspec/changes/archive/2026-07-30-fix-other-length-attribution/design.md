# Design: 修复 SUO/MINE other 路径长度归属歧义

## 数据 / 接口

无 schema 变化、无新配置项。**纯文案增强**，向后兼容。

## 改动点

### 1. `_format_single_change`（`impact_service_gameplay_support.py:116-121`）

当前签名：
```python
def _format_single_change(self, growth_pool, shrink_pool, delta_cm, current_length, is_critical, **extra_fmt):
    critical_prefix = "暴击。" if is_critical else ""
    jj = self._jj_name()
    if delta_cm >= 0:
        return critical_prefix + pick(growth_pool).format(delta=round(delta_cm, 3), jj=jj, **extra_fmt) + f"现在是{current_length}cm。"
    return critical_prefix + pick(shrink_pool).format(delta=round(abs(delta_cm), 3), jj=jj, **extra_fmt) + f"现在是{current_length}cm。"
```

新签名（仅追加**可选**关键字参数，向后兼容）：
```python
def _format_single_change(self, growth_pool, shrink_pool, delta_cm, current_length, is_critical,
                          *, current_subject: str = "", **extra_fmt):
    critical_prefix = "暴击。" if is_critical else ""
    jj = self._jj_name()
    suffix = f"{current_subject}现在是{current_length}cm。" if current_subject else f"现在是{current_length}cm。"
    if delta_cm >= 0:
        return critical_prefix + pick(growth_pool).format(delta=round(delta_cm, 3), jj=jj, **extra_fmt) + suffix
    return critical_prefix + pick(shrink_pool).format(delta=round(abs(delta_cm), 3), jj=jj, **extra_fmt) + suffix
```

注意：原代码 `**extra_fmt` 是位置关键字，但 `current_subject` 单独显式取出（用 keyword-only），避免与 `extra_fmt` 冲突（如未来文案池误用 `current_subject` 占位）。

### 2. `handle_suo`（`impact_service_gameplay.py:81-86`）

新增 `target_name` 解析（self 时为 "你"，other 时为被作用方的群昵称或 fallback）。当前 SUO 路径未计算 target_name，需新增类似 `_mine_target_name` 的逻辑（group_id+target_id → display_name fallback）。

`target_id = sender_id if at_id is None else int(at_id)` 已有，`is_self = (target_id == sender_id)`。

调用 `_format_single_change` 处：
```python
return PlainReply(self._format_single_change(
    self._cs(SUO_GROWTH, SUO_GROWTH_SAFE),
    self._cs(SUO_SHRINK, SUO_SHRINK_SAFE),
    delta_cm, current_length, is_critical,
    current_subject=("" if is_self else f"{target_name}的{jj}"),
), ...)
```

`target_name` 解析辅助方法：抽到 `ImpactServiceGameplaySupportMixin` 上做 `_resolve_target_name(group_id, target_id, is_self)`，MINE 的 `_mine_target_name` 也可复用（统一化）。

### 3. `handle_mine`（`impact_service_gameplay.py:283-307`）

`_mine_target_name` 已存在（返回 "你" for self，返回昵称或 fallback for other）。当前 `handle_mine` 命中分支调用 `_format_single_change` 时直接传入 `name=target_name`（已被文案池内的 `MINE_OTHER_*` 池使用）。**只要在 `_format_single_change` 调用处加 `current_subject` 参数即可**：

```python
text = self._format_single_change(
    growth_pool, shrink_pool, delta_cm, current_length, False,
    fluid=dug, name=target_name,
    current_subject=("" if spec.is_self else f"{target_name}的{self._jj_name()}"),
)
```

注：`target_name` 对 self 是 "你"，但 self 路径下 `current_subject=""`，所以 self 末尾不带"你的牛子"前缀（主句已含"你的{jj}"）；other 路径末尾追加"{target_name}的{jj}现在是 X cm"。

### 4. 共享 target_name 解析

为避免 SUO / MINE 各自实现一份，把 `_mine_target_name` 提到 `ImpactServiceGameplaySupportMixin` 顶层（命名为 `_resolve_target_name(group_id, target_id, is_self)`），删除 `_mine_target_name` 重复实现。

## 测试

- **单测** `tests/test_handle_suo.py`：
  - 嗦别人命中 → 末尾含 `{name}的{jj}现在是`，不含裸 `现在是 X cm` 后接句号（必须出现"{name}的"在"现在是"前）。
- **单测** `tests/test_handle_mine.py`：补强 `test_other_hit_changes_target_only` 末尾断言。
- **QA** `qa_scripts/qa_mining.py` 的 `scenario_other`：在 `expect_match(r"挖|液体|cm")` 后追加 `expect_match(r"{被挖者名}的{牛子}现在是")`。
- **QA 回归**：现有所有 pytest / QA 用例不能失败。

## 不动的东西

- DAJIAO（self only）：不传 `current_subject`，零变化。
- PK / fuck_wife：不走 `_format_single_change`，零变化。
- 文案池（SUCK_GROW/SHRINK、MINE_OTHER_GROW/SHRINK 等）：不动——主句内的"TA的{jj}"已经说明长度归属的是对方；只在末尾"现在是 X cm"前补一次主语，避免连续两次"TA的"听起来冗长。
- 配置 / schema：不增不改。
- `MineTargetSpec` / `MineResult`：不动。