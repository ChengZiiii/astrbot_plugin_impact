# Proposal: 挖矿（挖群友 / 挖矿）玩法

## Intent

为 `astrbot_plugin_impact` 增加一个轻量级社交互动玩法「挖矿」，让群友之间多一层互相「折腾」的入口，进一步拉动群活跃度。

玩法定位：日群友会**注入**液体到目标身上（记在 `injections` 表今日量），挖矿则把目标身上「今日被注入的液体」挖出来（从今日量减记），并且挖到液体时目标牛子长度按概率发生随机变化（涨或掉）。挖自己与挖别人两套独立配置。

## Scope

**In scope (v1):**
- 新命令 `挖群友` / `挖矿`（默认关键词），可配置别名。
- 不艾特任何人时挖自己；艾特他人时挖对方。
- 每次挖矿**必定尝试挖液体**：从目标「今日被注入量」(`injections` 今日行) 中挖走随机数量（可配范围 `mine_fluid_range`），上限不超过当前剩余量与「剩余量 × `mine_fluid_max_ratio_to_reserve`」。液体不会为负。
- 若目标今日被注入量为 0（挖不出液体）：仍算一次挖矿（走冷却），但**挖不到东西、牛子长度不变**。
- 若挖到液体（>0）：被挖者（自己或他人）牛子长度按配置的**独立概率** `mine_self_prob` / `mine_other_prob` 有概率发生变化，变化幅度取 `mine_self_change_range` / `mine_other_change_range`。
- 独立的挖矿冷却（`mine_cd_time`）。
- 挖别人且挖到液体时，按 `mine_other_notify`（默认开）用 `@` 通知被挖者。
- 为后续联动 animewifexI「挖老婆矿」预留 `vein_type` 扩展点（命令解析层产出 `MineTargetSpec`，结算层按 `self/other` + `vein_type` 分发，v1 仅实现 `user` 矿脉）。

**Out of scope (v1 / 后续):**
- ❌ 不新增任何资源存储；挖出的液体只是从 `injections` 今日量减记（不入库成新资源，也不跨日保留）。
- ❌ 不接入周报 / 排行。
- ❌ 老婆矿（animewifexI 联动）—— 仅留扩展点，不实现。
- ❌ 挖矿成功率受牛子长度加成（纯概率）。

## Approach

1. 配置层（`ImpactConfig`）：新增 `mine_cd_time`、`mine_self_prob`、`mine_self_change_range`、`mine_other_prob`、`mine_other_change_range`、`mine_other_notify`、`mine_fluid_range`、`mine_fluid_max_ratio_to_reserve`，并提供合理默认值。
2. 存储层（`ImpactStoreBasicMixin`）：新增 `consume_today_injection(user_id, want_ml)` —— 从今日注入量中扣减，返回实际挖出量（≥0，且不超过剩余量），原 `injections` 表语义/其它读取路径不受影响（仅减记今日行）。`get_today_injection` 仍返回剩余量。
3. 命令层（`impact_command_defs.py`）：新增 `mine` 命令组 + 别名 `挖群友/挖矿`，加入 `COMMAND_GROUP_MAP` 与 `USAGE_TEXT`；`DEFAULT_COMMANDS` 追加 `mine`。
4. 命令解析与路由（`impact_plugin_handlers.py`）：`handle_all_commands` 增加对 `mine` 的调度；新增 `_resolve_mine_target` 产出 `MineTargetSpec(vein_type, target_id, is_self)`。
5. 结算核心（`impact_service_gameplay.py`）：新增 `handle_mine`：
   - 先 `consume_today_injection(target, rand_in_range(mine_fluid_range))` 得实际挖出量 `dug`。
   - `dug == 0` → 回显「什么也没挖到」，设冷却、不掷长度骰、长度不变。
   - `dug > 0` → 按 `is_self` 选 self/other 概率掷骰，命中则 `change_length(target, delta)`；回显挖出量 + 长度变化（或无变化），并（other 且 `mine_other_notify`）发 `@` 通知。
6. 文案（`impact_copy_bank.py`）：新增 `MINE_SELF_GROW/SHRINK`、`MINE_OTHER_GROW/SHRINK`、`MINE_MISS`、`COOLDOWN_MINE`（及 `_SAFE`），`{fluid}` 占位挖出量、`{name}` 占位被挖者。
7. 冷却缓存（`impact_service.py`）：新增 `_mine_cd_data`。

## Extensibility note

`MineTargetSpec` 携带 `vein_type`（`"user"` | `"wife"` 等）。v1 解析层只对 `user` 生效（矿脉储量 = `injections` 今日量）。未来 animewifexI 老婆矿只需：在解析层加 `vein_type == "wife"` 分支（从 interop 解析 wid/owner），并提供一个「该老婆今日可挖储量」的读取 + 减记接口替换 `consume_today_injection`。结算核心只依赖 `is_self` 选配置 + `target_id` 改长度 + 一个 `reserve` 读取/扣减抽象，矿脉来源完全解耦。
