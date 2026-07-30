# Design: 挖矿玩法实现

## 数据模型

**不新增任何数据库表，不新增持久资源。** 仅对现有 `injections` 表「今日行」做减记。
- 储量来源：yinpa（`finish_yinpa` → `add_injection`）写入的当日 `volume_ml`，由 `get_today_injection` 读取。
- 挖矿只是把「今日被注入量」挖走一部分（减记），不入库为新资源、不跨日保留。

## 存储层改动（`impact_store_basic.py`）

新增 `consume_today_injection(user_id, want_ml) -> float`：
```python
def consume_today_injection(self, user_id: int, want_ml: float) -> float:
    today = self._today_text()
    with self._connect() as conn:
        row = conn.execute(
            "SELECT volume_ml FROM injections WHERE user_id=? AND date_text=?",
            (user_id, today)).fetchone()
        available = float(row["volume_ml"]) if row is not None else 0.0
        dug = round(min(max(want_ml, 0.0), available), 3)
        if dug > 0:
            conn.execute(
                "INSERT INTO injections(user_id,date_text,volume_ml) VALUES(?,?,?) "
                "ON CONFLICT(user_id,date_text) DO UPDATE SET volume_ml=excluded.volume_ml",
                (user_id, today, available - dug))
    return dug
```
- 液体不为负：`dug = min(max(want_ml,0), available)`，剩余量 `available-dug ≥ 0`。
- `get_today_injection` 不变（后续读到的就是减记后剩余量）。
- 原 `add_injection` 用于 yinpa 注入，不受影响；挖矿只走 `consume_today_injection`。

## 配置（`ImpactConfig`）

新增字段（均在 `from_dict` 提供默认值）：

| 字段 | raw key | 类型 | 默认 | 含义 |
|---|---|---|---|---|
| `mine_cd_time` | `minecdtime` | int | 300 | 挖矿冷却秒数（按发送者） |
| `mine_self_prob` | `mine_self_prob` | float | 0.7 | 挖自己且挖到液体时，命中长度变化的概率 |
| `mine_self_change_range` | `mine_self_change_range` | tuple[float,float] | (-1.0, 2.0) | 挖自己命中后的长度变化区间 |
| `mine_other_prob` | `mine_other_prob` | float | 0.5 | 挖别人且挖到液体时，命中长度变化的概率 |
| `mine_other_change_range` | `mine_other_change_range` | tuple[float,float] | (-2.0, 1.0) | 挖别人命中后的长度变化区间（偏掉，趣味） |
| `mine_other_notify` | `mine_other_notify` | bool | True | 挖别人且挖到液体时是否 @ 通知被挖者 |
| `mine_fluid_range` | `mine_fluid_range` | tuple[float,float] | (1.0, 20.0) | 单次尝试挖出的液体随机范围（再受剩余量与比例上限约束） |
| `mine_fluid_max_ratio_to_reserve` | `mine_fluid_max_ratio_to_reserve` | float | 1.0 | 单次最多挖走「剩余量 × 该比例」（<1 防一次掏空） |

`_conf_schema.json` 同步新增这 8 个配置项（描述/类型/默认/hint）。
`DEFAULT_COMMANDS` / `commands_enabled` 默认追加 `"mine"`。

## 命令与路由

- `impact_command_defs.py`：
  - `COMMAND_ALIASES["mine"] = ("挖群友", "挖矿")`
  - `COMMAND_GROUP_MAP["mine"] = COMMAND_ALIASES["mine"]`
  - `USAGE_TEXT` 追加挖矿说明（含「挖出今日被注入液体 + 牛子长度概率变化」）
- `impact_plugin_handlers.py`：
  - `_dispatch` 增加 `if command_key == "mine" and not is_private: return await self._handle_mine(...)`
  - 挖矿仅群聊（私聊不处理，与 yinpa/fuck_wife 一致）。
  - 复用既有「注册群成员 / 周报结算 / 保存 session」前置逻辑（dispatch 已对所有非 toggle/help 命令统一执行）。

## 扩展点：`MineTargetSpec`

```python
@dataclass(frozen=True, slots=True)
class MineTargetSpec:
    vein_type: str      # "user" (v1) / "wife" (future, animewifexI)
    target_id: int      # 被挖者 QQ（user）/ wid（wife，后续）
    is_self: bool
```

`_resolve_mine_target(event, at_id, sender_id) -> MineTargetSpec`：
- `at_id is None` → `MineTargetSpec("user", sender_id, True)`
- 否则 → `MineTargetSpec("user", int(at_id), False)`

v1 只处理 `vein_type == "user"`，储量读取/扣减直接调 `get_today_injection` / `consume_today_injection`。结算核心 `handle_mine` 只依赖 `is_self` 选配置 + `target_id` 改长度 + 一个 `reserve` 读取/扣减抽象（v1 即 injections 今日量），完全不感知矿脉来源——后续老婆矿只需在解析层加 `wife` 分支（从 `data.plugins.astrbot_plugin_animewifexI.app.interop` 解析 wid/owner 并接其储量接口），结算层零改动。

## 结算核心：`ImpactService.handle_mine(group_enabled, group_id, sender_id, spec, at_id)`

流程：
1. `group_enabled` 为 False → 返回 `not_enabled_reply`。
2. 冷却检查 `_mine_cd_data`（用 `_cooldown_text`，新增 `COOLDOWN_MINE` 文案池）。
3. 目标建档：`ensure_user(target_id, user_initial_length)`（被挖者无档则补 10cm 起步；无档则今日注入必为 0，自然挖不到）。
4. 挖液体：
   - `want = random.uniform(*mine_fluid_range)`，再受 `reserve = get_today_injection(target)` 与 `reserve * mine_fluid_max_ratio_to_reserve` 约束 → `dug = consume_today_injection(target, min(want, reserve, reserve*ratio))`。
5. `dug == 0`（无液体）：设置冷却、touch 双方活跃，返回 `MINE_MISS` 文案（含目标名 / 「你」），长度不变。
6. `dug > 0`：
   - 按 `is_self` 选 `(prob, change_range)`。
   - 掷骰 `random.random() < prob`：
     - 命中：`delta = random.uniform(*change_range)`，`current = change_length(target_id, delta)`，用 `MINE_SELF_GROW/SHRINK` 或 `MINE_OTHER_GROW/SHRINK`（按 delta 正负）。
     - 未命中：长度不变，文案说明「挖到液体但什么也没发生」。
   - 设置冷却、touch 双方活跃。
   - 若 `is_self is False` 且 `mine_other_notify`：异步发 `@target` 通知（机制同 `_notify_cuckold`，取群 session umo），文案含挖出量。
7. 返回 `PlainReply`，含被挖者昵称、挖出量、变化量、当前长度。

## 文案（`impact_copy_bank.py`）

新增（各含 `_SAFE`）：
- `MINE_SELF_GROW` / `MINE_SELF_SHRINK`
- `MINE_OTHER_GROW` / `MINE_OTHER_SHRINK`
- `MINE_MISS`（挖不到液体，无长度变化）
- `COOLDOWN_MINE` / `COOLDOWN_MINE_SAFE`
- `MINE_OTHER_NOTIFY`（主动通知文案，含 `{fluid}`）

渲染：复用 `_format_single_change(growth_pool, shrink_pool, delta, current, is_critical=False)` 得到长度变化句，再在 handler 层拼上「挖出 {fluid}ml」前缀与被挖者名字。

## 测试与验收

- 单测（pytest，`tests/test_handle_mine.py`）：
  - 挖自己挖到液体命中→长度在 `[orig+范围]`；未命中→长度不变但液体已减。
  - 挖别人挖到液体命中→target 长度变化、sender 不变；通知被调用（mock `context.send_message`）。
  - 目标今日无注入→`dug==0`、长度不变、今日注入仍为 0（不出现负数）。
  - 冷却：第二次在冷却内→长度不变、液体不减。
  - `consume_today_injection` 边界：want>available 时返回 available，剩余量=0。
- QA（按 AGENTS.md，改命令后必须跑 `skills/astrbot-qa`）：模拟群聊 `挖矿`、`挖矿 @某人`，校验回显（挖出量/长度变化）与 @ 通知。
