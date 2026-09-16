# 证据：工作空间隔离的迁移 / 回退演练（§3 的证据）

> **时间**：2026-09-15（架构材料填写期）
> **用途**：`docs/ARCHITECTURE-UPGRADE.md` §3；`requirements-upgrade.md` §8 第 2 条（开工前必须通过那批）
> **手法**：在 `data-upgrade\_rehearsal\` 内**真跑一遍**迁移 → 校验 → 回退。MVP `data\` 全程只读。
> **不写密钥**；群标识保留完整值（它是 chat_id，不是凭据；且已在现场日志中可见）。

## 1. 迁移前基线

群标识（D-70：工作空间 key）：`oc_33225a17a5b9fdde00a70f92d002a033`
可读名生成：作业书标题 `课程任务书` + chat_id 尾 6 位 ⇒ `课程任务书-02a033`

MVP `data\` 的 SHA256（前 16 位）：

| 文件 | 哈希前缀 |
|---|---|
| assignment.json | 4B9B762422F3A1DB |
| cards.json | C7ED938C10E9C97A |
| direction.json | 86B916262C6C69F0 |
| gantt.png | 80A193DAB594356B |
| members.json | B5832811725E91CC |
| preferences.json | A7A23063C6028970 |
| report.md | A812A8903FFAFFEB |
| rubric.json | 75742D5BB2AB7DAB |
| seen.json | 1782BC9CB2408EA6 |
| state.json | 574204A1CCA521FA |

注：`assignments.json` / `proposals.json` / `reminders.json` 在 MVP 盘上**尚不存在**（没走到那一步），迁移按"存在即复制"处理 —— 这也是运行时必须容忍的形态。

## 2. 迁移结果

- 工作空间目录：`data-upgrade\_rehearsal\workspaces\oc_33225a17a5b9fdde00a70f92d002a033\`
- 复制 10 个 JSON/产物 + `uploads\` 4 个附件
- `index.json`：`workspaces` 1 条、`user_last_group` 3 人（从 `members.json` 的花名册推出）

## 3. 校验：用产品代码读数（不是手抄）

| 读法 | 迁移前 | 迁移后 |
|---|---|---|
| `JsonStore.load_rubric()` | 5 | 5 |
| `JsonStore.load_cards()` | 5 | 5 |
| `JsonStore.load_members()` | 3 | 3 |
| `JsonStore.load_preferences()` | 1 | 1 |
| `JsonStore.load_assignments()` | 0 | 0 |
| `coverage_loop()` 分子/分母 | 4 / 4（missing=()） | 4 / 4（missing=()） |

覆盖率那一行是**逐项相等断言**（`assert` 通过），不是"看起来一样"。

顺带落下一个基线数字（§6 证据槽 ②）：现网 rubric 共 5 条，其中 `status="normal"` 4 条 ⇒ **覆盖率分母 = 4**；也就是说有 1 条是 `ambiguous`，它不进分母（D-19 / §7.2）。

## 4. 回退结果

- 守卫：先 `Resolve-Path` 校验目标落在 `data-upgrade\_rehearsal\` 之内，不满足即中止（防止误删）
- 删除工作空间副本 + `index.json` ⇒ 两者均确认不存在
- **2026-09-16 补注（清理）**：回退时留下的空目录 `data-upgrade\_rehearsal\workspaces\` 已连同 `_rehearsal\` 一并删除（审核 #2 补丁 3；纯清洁，无数据影响）。
- **回退后复核：MVP `data\` 10 个已存在文件（13 个候选名里 3 个尚未产生：`assignments.json` / `proposals.json` / `reminders.json`）哈希前后完全一致 = True**

## 5. 这份演练证明了什么 / 没证明什么

**证明了**：

1. "只复制、不移动"的迁移是可回退的：回退 = 删副本，风险为 0，因为源数据全程只读。
2. `JsonStore(root)` 已经天然支持"换个根就是换一个数据域" —— 隔离**不需要改 `storage.py`**，只需要在 app 层按群选 root（`src/storage.py:77`）。
3. 迁移后覆盖率分子/分母逐项一致 ⇒ 数据搬家不影响 §6 那条硬指标。

**没证明（未验证）**：

- [ ] ≥2 个工作空间**同时**活跃时的并发写（`index.json` 会变成全局热点）
- [ ] 迁移**中断**（复制到一半）的现场处置 —— 目前设计靠"先备份 + 重跑幂等"兜，但没演练
- [ ] 磁盘占用与清理策略（`uploads\` 会随群数线性增长）