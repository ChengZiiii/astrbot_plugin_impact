# length-display Specification

## Purpose
TBD - created by archiving change fix-other-length-attribution. Update Purpose after archive.
## Requirements
### Requirement: length attribution in other paths
当 SUO（嗦牛子）或 MINE（挖矿）作用于**别人**时，回显的当前长度 MUST 带明确主语（被作用方名称），避免与发送者混淆。

#### Scenario: 挖别人命中 - 当前长度带主语
- **Given** 用户对他人挖矿且命中长度变化
- **Then** 回复末尾的当前长度形如 `{被挖者昵称}的{jj}现在是 X cm`，**不是**裸"现在是 X cm"

#### Scenario: 嗦别人命中 - 当前长度带主语
- **Given** 用户对他人嗦牛子且命中长度变化
- **Then** 回复末尾的当前长度形如 `{被作用方昵称}的{jj}现在是 X cm`，**不是**裸"现在是 X cm"

### Requirement: backward compatibility for self paths
DAJIAO（打胶）、SUO（嗦自己）、MINE（挖自己）的现有回显 SHALL **零变动**（仍以裸"现在是 X cm"结尾，但 self 路径的主句里已有"你的{jj}"主语）。

#### Scenario: 挖自己 - 现有回显不变
- **Given** 用户挖自己且命中长度变化
- **Then** 回复仍以"现在是 X cm。"结尾（主句已含"你的{jj}"，主语明确）

#### Scenario: 打胶 - 现有回显不变
- **Given** 用户打胶
- **Then** 回复仍以"现在是 X cm。"结尾（无歧义，因为只作用于自己）

### Requirement: _format_single_change opt-in attribution
`ImpactServiceGameplaySupportMixin._format_single_change` 新增**可选**关键字参数 `current_subject: str = ""`：
- 当 `current_subject == ""`：行为与原版完全一致（末尾 `现在是{current}cm。`）。
- 当 `current_subject != ""`：末尾拼 `{current_subject}现在是{current}cm。`。

默认参数 SHALL 保证所有未升级的调用方行为零变化。

#### Scenario: 不传 current_subject
- **Given** 调用方不传 `current_subject`
- **Then** 末尾为 `现在是{current}cm。`（与原版一致）

#### Scenario: 传 current_subject
- **Given** 调用方传 `current_subject="Bob的牛子"`
- **Then** 末尾为 `Bob的牛子现在是{current}cm。`

