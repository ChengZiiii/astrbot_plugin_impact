# Proposal: 在"对别人触发指令"的回显里明确长度归属

## Intent

修复 SUO（嗦牛子）与 MINE（挖矿）命令中"挖别人时回显对方当前长度无主语"导致的歧义：
当前 `_format_single_change` 末尾硬追加 `现在是{current}cm。`，当命令作用于别人时（SUO/MINE 的 other 路径），这个 X cm 实际是**被作用方**的长度，但句子里没有主语，读者可能误以为是"你（发送者）"的。

回显示例（挖别人）：
- 现状：`你从Bob身上挖走5.0ml，顺便把TA的牛子挖短了0.738cm。现在是8.048cm。`
- 修复后：`你从Bob身上挖走5.0ml，顺便把TA的牛子挖短了0.738cm。Bob的牛子现在是8.048cm。`

DAJIAO（打胶）只有 self 路径不存在歧义；PK 与 fuck_wife 走自己的格式函数，不复用 `_format_single_change`，也不在本 change 范围。

## Scope

**In scope:**
- 给 `ImpactServiceGameplaySupportMixin._format_single_change` 增加**可选**关键字参数 `current_subject: str = ""`。
  - 兼容默认行为：`current_subject=""` 时末尾仍为 `现在是{current}cm。`（现有所有调用方零改动）。
  - 当 `current_subject != ""` 时末尾变为 `{current_subject}现在是{current}cm。`。
- `handle_suo`（other 路径，target_id != sender_id）：传入 `current_subject=f"{target_name}的{jj}"`。
- `handle_mine`（other 路径，spec.is_self is False）：传入 `current_subject=f"{target_name}的{jj}"`。
- 单测与 QA 各加 1 条断言：挖别人时回显必须包含 `{name}的{jj}现在是`，而**不是**裸"现在是"。
- `_format_single_change` 的 docstring 增补行为说明。

**Out of scope:**
- DAJIAO（打胶）—— 只作用于自己，末尾"现在是 X cm"无歧义。
- PK、fuck_wife —— 不走 `_format_single_change`。
- 文案池本身不动（self 路径已经含"你的{jj}"，无需修改）。

## Approach

1. `impact_service_gameplay_support.py`：`_format_single_change` 增 `current_subject` 可选参 + 末尾拼字符串按 `current_subject` 是否为空分支（默认空时行为不变）。
2. `impact_service_gameplay.py`：
   - `handle_suo` 在调用 `_format_single_change` 时计算 `target_name`（已有从 `_mine_target_name` 风格的解析，可参考或单独抽），`is_self` 时不传、`other` 时传。
   - `handle_mine` 在命中分支调用 `_format_single_change` 时同样按 `spec.is_self` 分支传 `current_subject`。
3. 单测：`tests/test_handle_suo.py`（如不存在则新建）+ `tests/test_handle_mine.py` 各加 1 条断言。
4. QA：`qa_scripts/qa_mining.py` 的 `scenario_other` / `scenario_no_fluid` 加正则匹配 `{name}的牛子现在是`；`qa_scripts/qa_suo.py` 同步增加（v1 若无此 QA 脚本，新建）。

## 兼容性 / 风险

- `_format_single_change` 新参数默认空，DAJIAO 路径**零回归**。
- 既有 SUO/MINE 的 self 路径**零回归**。
- 改 SUO/MINE 的 other 路径**仅改末尾 6 个字符**（追加主语），文案语义、UI 风格、占位符都不动。
- 风险点：SUO 的"target_name"获取路径需确认 —— 当前 SUO 路径没现成 `target_name` 变量，需新增小段解析（参考 MINE 的 `_mine_target_name`，或独立写一个类似 `_suo_target_name`）。