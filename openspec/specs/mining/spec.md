# mining Specification

## Purpose
TBD - created by archiving change add-mining-feature. Update Purpose after archive.
## Requirements
### Requirement: mine command availability
插件 SHALL 提供名为 `mine` 的命令组，默认关键词为 `挖群友` 与 `挖矿`，管理员可在 `_conf_schema.json` / `commands_enabled` 中禁用该命令组。

#### Scenario: 默认关键词触发挖矿
- **Given** 群已开启淫趴且未禁用 `mine` 命令组
- **When** 用户发送 `挖矿` 或 `挖群友`
- **Then** 触发挖矿玩法且以自己为目标

#### Scenario: 禁用 mine 命令组
- **Given** `commands_enabled` 中不含 `mine`
- **When** 用户发送 `挖矿`
- **Then** 不触发挖矿（与其他被禁用命令行为一致）

### Requirement: mine target resolution
挖矿命令 SHALL 支持「不艾特挖自己、艾特他人挖对方」。

#### Scenario: 无艾特挖自己
- **Given** 用户发送 `挖矿` 且未艾特任何人
- **Then** 被挖目标为发送者本人

#### Scenario: 艾特他人挖对方
- **Given** 用户发送 `挖矿 @某人`
- **Then** 被挖目标为该艾特用户，且不会以自己为目标

### Requirement: mine extracts today's injected fluid
每次挖矿 SHALL 从目标「今日被注入量」中挖出随机数量的液体（范围由 `mine_fluid_range` 配置），并减记该目标的今日注入量。挖出量 MUST 不为负，且 MUST 不超过目标当前剩余今日注入量。

#### Scenario: 挖到液体
- **Given** 目标今日被注入量为正，且本次随机挖出量 ≤ 剩余量
- **When** 挖矿结算
- **Then** 目标今日注入量按挖出量减记，回复中包含挖出量

#### Scenario: 目标今日无液体
- **Given** 目标今日被注入量为 0
- **When** 用户对其挖矿
- **Then** 挖出量为 0，回复提示「什么也没挖到」，且目标的牛子长度不变；本次仍计入冷却

#### Scenario: 挖出量不超过上限
- **Given** `mine_fluid_max_ratio_to_reserve` < 1
- **When** 随机挖出量 × 上限比例仍受剩余量约束
- **Then** 实际挖出量不超过 `min(随机量, 剩余量, 剩余量 × 比例)`

### Requirement: mine applies length change only when fluid dug
被挖者（自己或他人）的牛子长度 SHALL 仅在「本次挖到液体（>0）」时，按对应配置的概率发生一次随机变化。挖自己与挖别人 MUST 使用两套独立的概率与变化范围配置。无液体挖出时长度 MUST 不变化。

#### Scenario: 挖到液体且命中长度变化
- **Given** 用户挖矿且挖到液体（>0），本次掷骰命中 `mine_self_prob`/`mine_other_prob`
- **Then** 被挖者牛子长度按对应 `mine_*_change_range` 随机变化（涨或掉），并回显新长度与挖出量

#### Scenario: 挖到液体但未命中
- **Given** 用户挖矿且挖到液体（>0），本次掷骰未命中
- **Then** 被挖者牛子长度不变，回复含挖出量但提示长度未变

#### Scenario: 未挖到液体长度不变
- **Given** 用户挖矿但目标今日无液体
- **When** 结算完成
- **Then** 被挖者牛子长度不变

### Requirement: mine cooldown
挖矿 SHALL 具有独立冷却 `mine_cd_time`（按发送者计），冷却中再次挖矿返回冷却提示且不结算。

#### Scenario: 冷却中再次挖矿
- **Given** 用户刚挖过矿且在 `mine_cd_time` 内
- **When** 用户再次发送挖矿
- **Then** 返回剩余冷却提示，不修改任何长度、不扣减液体

### Requirement: mine other notify
挖别人且挖到液体时，若 `mine_other_notify` 为真，SHALL 向被挖者发送一条 `@` 通知消息（与 fuck_wife NTR 通知机制一致，使用主动消息 `context.send_message`）。

#### Scenario: 挖别人命中并通知
- **Given** `mine_other_notify` 为真，用户挖别人且挖到液体
- **When** 结算完成
- **Then** 向被挖者所在群会话主动推送 `@被挖者 你的牛子被挖了一下…，挖出{fluid}ml…`

#### Scenario: 关闭通知
- **Given** `mine_other_notify` 为假
- **When** 用户挖别人且挖到液体
- **Then** 不发送主动通知

### Requirement: mine vein_type extensibility
挖矿命令解析层 SHALL 产出 `MineTargetSpec(vein_type: str, target_id: str, is_self: bool)`，v1 仅实现 `vein_type == "user"`（储量来自 `injections` 今日量）；结算层按 `is_self` 选择配置、按 `target_id` 改长度、按 `vein_type` 选择储量读取/扣减抽象，以便后续接入 animewifexI `wife` 矿脉时只新增解析分支。

#### Scenario: 解析产出 spec
- **Given** 用户发送 `挖矿 @某人`
- **Then** 解析得到 `MineTargetSpec(vein_type="user", target_id=<对方QQ>, is_self=False)`

