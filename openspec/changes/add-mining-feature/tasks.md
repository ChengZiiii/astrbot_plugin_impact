# Tasks

## 1. 配置层
- [x] 1.1 `impact_config.py` 的 `ImpactConfig` 增加字段：`mine_cd_time`, `mine_self_prob`, `mine_self_change_range`, `mine_other_prob`, `mine_other_change_range`, `mine_other_notify`, `mine_fluid_range`, `mine_fluid_max_ratio_to_reserve`
- [x] 1.2 `ImpactConfig.from_dict` 写入解析与默认值（key：`minecdtime`/`mine_self_prob`/`mine_self_change_range`/`mine_other_prob`/`mine_other_change_range`/`mine_other_notify`/`mine_fluid_range`/`mine_fluid_max_ratio_to_reserve`；range 用 `_parse_float_tuple`）
- [x] 1.3 `DEFAULT_COMMANDS` 追加 `"mine"`
- [x] 1.4 `_conf_schema.json` 同步新增这 8 个配置项（描述/类型/默认/hint）

## 2. 存储层（液体减记）
- [x] 2.1 `impact_store_basic.py` 新增 `consume_today_injection(user_id, want_ml) -> float`（min(max(want,0), available)，扣减今日行，返回实际挖出量，不为负）
- [x] 2.2 确认 `get_today_injection` 仍返回减记后的剩余量，yinpa 注入路径不受影响

## 3. 命令与路由
- [x] 3.1 `impact_command_defs.py`：`COMMAND_ALIASES` 增加 `mine = ("挖群友","挖矿")`；`COMMAND_GROUP_MAP` 增加 `mine`
- [x] 3.2 `impact_command_defs.py`：`USAGE_TEXT` 追加挖矿指令说明（挖出今日液体 + 牛子概率变化）
- [x] 3.3 `impact_plugin_handlers.py`：`_dispatch` 中 `mine` 路由到 `_handle_mine`（仅群聊）
- [x] 3.4 新增 `MineTargetSpec` dataclass（放 `impact_models.py`）
- [x] 3.5 新增 `_resolve_mine_target(event, at_id, sender_id) -> MineTargetSpec`

## 4. 结算核心
- [x] 4.1 `impact_service.py` 增加 `_mine_cd_data` 冷却缓存
- [x] 4.2 `impact_service_gameplay.py` 增加 `handle_mine(group_enabled, group_id, sender_id, spec, at_id)`
- [x] 4.3 `_handle_mine`：建档 → 冷却 → `consume_today_injection(target, min(want, reserve, reserve*ratio))` → dug==0 走 MINE_MISS（长度不变）→ dug>0 按 self/other 概率掷骰改长度 → 可选 @ 通知
- [x] 4.4 挖别人挖到液体且 `mine_other_notify` 真时，主动 `@` 通知被挖者（复用群 session umo，机制同 `_notify_cuckold`）

## 5. 文案
- [x] 5.1 `impact_copy_bank.py` 新增 `MINE_SELF_GROW/SHRINK`、`MINE_OTHER_GROW/SHRINK`、`MINE_MISS`、`COOLDOWN_MINE` 及各自 `_SAFE` 版、`MINE_OTHER_NOTIFY`（带 `{fluid}` 占位）

## 6. 测试与验收
- [x] 6.1 `tests/test_handle_mine.py`：挖自己命中/未命中、挖别人命中/通知、无液体(dug==0 长度不变)、冷却、`consume_today_injection` 边界
- [x] 6.2 跑 `pytest -m "not integration"` 通过
- [x] 6.3 加载 `skills/astrbot-qa` 写 QA 脚本并跑通 `挖矿` / `挖矿 @某人`
- [ ] 6.4 QA 通过后 git commit，并询问是否 `sync.bat`
