# 离线操作手册 · U2 数据层（清空 / 重置 / 改名）

> **这是什么**：U2「防呆三动作」的**离线操作**手册。三动作**不做机器人指令**（那是对 U2 的收窄），所以"二次确认"和"执行人记录"落在人这边 —— 落在**这份手册**和 `data-upgrade\maintenance.log` 上。
> **落点依据**：`docs/ARCHITECTURE-UPGRADE.md` §3.2（防呆三动作的落点与三条件）、§12.3 第 17 条（PM 2026-09-16 认）、§12.4（排期与分工）；工具 = `tools\migrate_workspace.py`。
> **适用范围**：升级版进程根 `data-upgrade\`。**MVP 的 `data\` 全程只读** —— 本手册的每个动作都不许碰它（工具纪律第 1 条：只复制、不移动）。
> **进不进运行时**：不进。本手册描述的是**人**在命令行手动做的操作，不是机器人能力。

---

## 0. 三动作是什么（先把边界钉死）

| 动作 | 干什么 | 影响面 | 现成命令 |
|---|---|---|---|
| **清空** | 删掉某个群的工作空间副本 + `index.json` 里那条条目 + 摘掉指向它的 `user_last_group` 绑定 | `data-upgrade\workspaces\<chat_id>\`、`index.json` | `--rollback` |
| **重置** | 清空之后，从 `data\` 重新迁移一遍（回到"刚搬进来"的状态） | 同上 + 重建副本 | `--rollback` 后 `--apply` |
| **改名** | 改 `index.json` 里该群工作空间的**可读名**（`name`），只改这一个键 | `index.json` 一个键 | 手动改 JSON |

**不在这三个动作里的**（要另行授权，见 §7）：把 `data-upgrade\` **整根清空**、删 `maintenance.log`、碰 `data\`。

---

**降级备选（砍序已定，PM 2026-09-16 点头）** —— 排期被挤时按这个顺序砍：本手册的**排障 / 示例段** → **演练留痕行** → **§2.3 改名章节**。**必须留**：迁移工具本体（`tools\migrate_workspace.py`）+ 「**清空 / 重置 / 执行人记录字段表**」这三样。
**砍掉 §2.3 时，§2 这一段必须留下列这一行**（否则「三动作」会被读成两动作）：

> **改名本轮不做（P2 开关）** —— 可读名要改就手工编辑 `index.json` 的 `name`（口径见 §2.3 / §5），或等 P2 开关开。

---

## 1. 动手前的四条前置检查（一条不满足就别动手）

1. **进程已停** —— 迁移前必须停升级版（`docs\ARCHITECTURE-UPGRADE.md` §3.3 第 1 步）。锁在进程根：`data-upgrade\app.lock`（`src/gateway/app.py` 的 `LOCK_FILE` = `tools\migrate_workspace.py` 的 `LOCK_NAME`）。**⚠️ 这道守卫只装在迁移上**：`check_process_lock()` 只在 `migrate()` 里调用 —— 进程还在跑时**默认拒绝**（`--force` 只跳过阻断、不代表进程真停了）；**回退（清空 / 重置）走 `rollback()`，它压根不查锁**。也就是说**最容易出事的动作没有工具守卫**，只能靠本节 + §4 的复核人守住。
2. **路径解析过** —— 目标必须**严格落在** `data-upgrade\` 之内（不等于根、不在根之外）。工具用 `resolve_path()` + `guard_within()` 做这件事，不合格直接抛 `OutOfScope` 中止。**人工改 JSON 时同样按这条自查**。
3. **备份在** —— 真跑会先备份到 `data-upgrade\_migration\<stamp>\`；同一份源数据只留一份备份（`SOURCE.sha256` 认领，重跑复用，不堆垃圾）。
4. **先写台账** —— 动手**之前**先往 `maintenance.log` 追加一行（§3）。顺序反了就等于"没有记录"。

---

## 2. 三个动作怎么做

### 2.1 清空

**什么时候用**：这个群不做了 / 数据脏了要重来 / 群标识换了。

**怎么做（首选现成命令，别手删目录）**：

```powershell
python tools\migrate_workspace.py --rollback --chat-id oc_xxxxxxxxxxxxxxxx
```

**⚠️ 回退没有干跑档（v1.18 订正，原先写成「干跑」是错的）**：`--rollback` **不吃 `--apply`** —— `main()` 里 `if args.rollback:` 直接调 `rollback()`，敲下去就是**真删**（副本 + 索引条目一起没）。所以动手**之前**必须三件事齐：① 进程已停（§1 第 1 条 —— 这一条**没有工具守卫**，只能靠人）；② 台账先写（§3）；③ 复核人点头（§4）。**没有「先看一眼」的机会**，别把它当成可以随手试的命令。

`--chat-id` 缺省时，工具从 `data\state.json` 的 `group_chat_id` 或索引里推；**推不出来就停手问人**（归属不明不猜）。

**它做了什么**：删工作空间副本（`workspaces\<chat_id>\` → 报 `[removed]`）+ 删索引条目（报 `dropped`）+ 摘掉 `user_last_group` 里指向该群的绑定。回退**不碰源根**（源盘哈希不变，见 §6）。

**二次确认**：见 §4。

### 2.2 重置

**什么时候用**：工作空间内容坏了，但 `data\` 是好的（想回到"刚迁移进来"的样子）。

```powershell
python tools\migrate_workspace.py --rollback --chat-id oc_xxxxxxxxxxxxxxxx   # 先清（真删，无干跑档 —— 见 §2.1）
python tools\migrate_workspace.py                                             # 干跑：看计划
python tools\migrate_workspace.py --apply                                     # 真跑：重建
```

**看什么**：干跑的清单里若出现 `- <文件>  copy (源盘没有)` / 读数为 `0 -> 0`，说明**源盘本身就没有这份数据** —— 那不是"重置成功"，是"没东西可搬"，要人确认后再决定是不是该手工补。**`0 -> 0` 不算证据力**（同 §3.4 的口径）。

**幂等**：重置后立刻再跑一次 `--apply`，应当报 **`写盘次数 = 0` / `幂等 = True`**。不是 0 就说明有东西在反复写，停下来查（这正是 §6 的验收点）。

### 2.3 改名

**什么时候用**：可读名跟实际作业书对不上（改名**不影响**任何功能，只影响人看索引时的辨识度）。

**怎么做**：改 `data-upgrade\index.json` 里该群的 `name`：

```json
{
  "workspaces": {
    "oc_xxxxxxxxxxxxxxxx": {
      "name": "课程任务书-02a033",
      "created_at": "2026-09-16T11:30:11",
      "migrated_from": "data"
    }
  },
  "user_last_group": { "ou_xxx": "oc_xxxxxxxxxxxxxxxx" }
}
```

- 可读名的形状 = `<作业书标题>-<chat_id 尾 6 位>`；没有标题就退成 `群<尾 6 位>`（工具 `readable_name()` 的口径，改名前照它写）。
- **只改 `name` 这一个键。** `created_at` / `migrated_from` 别动（语义见 §5）。
- 改完**存回 UTF-8 / LF**（仓库 `.gitattributes` = `* text=auto eol=lf`）；`index.json` 在 `data-upgrade\` 里不进 git，但换行风格保持一致免得备份 diff 噪音。
- **编辑前先停进程**：运行时也会写 `index.json`（`user_last_group`），并发写会互相覆盖。

**为什么改名不能用工具**：工具的索引合并是"**只补缺失的键**"（`merge_index()`），已有键一律保留 —— 这是刻意的：否则重跑会把人工改名和运行时刚更新的"最近一次群内互动"一起冲掉。

---

## 3. 执行人记录：`data-upgrade\maintenance.log`

**位置**：`data-upgrade\maintenance.log`（**进程根**，不在工作空间目录里 —— 所以删工作空间删不掉它）。**JSON Lines**：一行一个 JSON 对象，追加写。

| 字段 | 含义 | 必填 |
|---|---|---|
| `at` | 动作发生时间（ISO 8601，秒） | ✅ |
| `action` | `clear` / `reset` / `rename` | ✅ |
| `operator` | **执行人**（做动作的人） | ✅ |
| `verifier` | **复核人**（二次确认的那个人） | ✅ |
| `workspace` | 目标 `chat_id`（改名前先记**旧名**也放这里） | ✅ |
| `command` | 实际敲的命令（人工改 JSON 就写 `manual:edit-index`） | ✅ |
| `before_digest` / `after_digest` | 动作前后 `data-upgrade\workspaces\<chat_id>\` 的树哈希（没有就写 `null`） | 建议 |
| `result` | `ok` / `failed:<原因>` | ✅ |
| `note` | 为什么要做 / 有谁在场 / 特殊处置 | 建议 |

样例：

```json
{"at":"2026-09-16T11:30:11","action":"clear","operator":"架构师","verifier":"PM","workspace":"oc_xxxxxxxxxxxxxxxx","command":"python tools\\migrate_workspace.py --rollback --chat-id oc_xxxxxxxxxxxxxxxx","before_digest":"3f2a…","after_digest":null,"result":"ok","note":"该群作业作废，PM 在场确认"}
```

**四条规则**

1. **动手前先写**（写 `result:"…in progress"` 或先写一行 `action` 再补结果）—— 崩在中途也得留下"有人动过"。
2. **只追加，不覆盖**（历史就是历史；写错了再追加一行 `note:"corrects <at>"`）。
3. **两个人都要留名**（`operator` + `verifier`）—— 这是"二次确认"的**唯一可核对物**。
4. **它的删除要另行授权**（见 §7）。

---

## 4. 二次确认怎么做（三动作通用）

1. **执行人**：在群里 / 当面对**复核人**说清三件事 —— 哪个群（`chat_id` 或可读名）、做哪个动作、为什么。
2. **复核人**：自己确认**目标群对得上**（建议当场看 `index.json` 的可读名），然后点头。
3. **执行人**：先写 `maintenance.log`（§3），再动手；动手后把 `result` 与 `after_digest` 补进同一行（或紧接着追加一行）。
4. **复核人**：看 `MANIFEST`（§6）确认"做了什么"与"说好的"一致。

**没有复核人就不动手。** 这是 PM 2026-09-16 认的第 17 条三条件里的第二条（"执行人记录有落点"）在流程上的兑现。

---

## 5. 索引两个字段的口径（照抄，别自由发挥）

| 字段 | 口径 | 为什么 |
|---|---|---|
| `migrated_from` | **仓库相对路径**（正常就是 `data`） | 绝对路径是机器相关的（`D:\AI创新创业大赛\data`），写进索引换台机器 / 换目录就成了假信息 |
| `created_at` | **该工作空间在索引里的"登记时刻"**（懒创建的 = 首条消息那刻；迁移进来的 = 迁移时刻）；**重跑不覆盖** | 它是"这个工作空间什么时候被登记"的锚点，不是"最后一次改动时间" |

---

## 6. 验收口径（做什么才算收工）

**跑一遍演练，四步**（在源码根目录）：

```powershell
python tools\migrate_workspace.py --dest-root data-upgrade\_rehearsal                # 1 干跑
python tools\migrate_workspace.py --dest-root data-upgrade\_rehearsal --apply        # 2 迁移
python tools\migrate_workspace.py --dest-root data-upgrade\_rehearsal --apply        # 3 复跑（验幂等）
python tools\migrate_workspace.py --dest-root data-upgrade\_rehearsal --rollback     # 4 回退（真删，无干跑档）
```

**判据（四条，缺一条就不算过）**

1. 第 2 步的 `MANIFEST`：`校验 = ok=True`、`覆盖率 = 4 / 4 missing=[]`、`源根未动=True`。
2. 第 3 步：**`写盘次数 = 0` / `幂等 = True`**（同一秒里跑两次时，第二份 `MANIFEST` 必须落成 `MANIFEST-…-2.json`，**不许覆盖第一份**）。
3. 第 4 步：工作空间 `[removed]`、索引条目 `dropped`。
4. **全程结束后，MVP `data\` 的文件哈希与开工前一致**（`data\` 只读的硬证据）。

**留痕**：`data-upgrade\_migration\MANIFEST-migrate-<stamp>.json` + `MANIFEST-rollback-<stamp>.json`（原样 JSON，别手改）。

**已跑过一次（2026-09-16，架构师）**：干跑 / 迁移 / 复跑 / 回退四步全通，幂等 `workspace_changes=0`、同秒 `-2` 唯一化、回退 `[removed]` + 摘 3 条绑定、`data\` 21 文件哈希前后一致 —— 记录见 `docs/evidence/2026-09-16-architect-countersign-v1.12.md`。

---

## 7. 越界与禁止（这几条出事就是事故）

- ❌ **不许删 / 改 `data\`**（MVP 真源；工具纪律第 1 条：只复制、不移动）。
- ❌ **不许把 `data-upgrade\` 整根清空**（那会连 `maintenance.log` 一起删掉 —— 记录和动作一起消失）。要整根清空**必须另行授权**（§3.2 的约束，PM 2026-09-16）。
- ❌ **不许用 `--force` 掩盖"进程还在跑"** —— 它只是跳过阻断；并发写 `index.json` 会把改名 / 绑定冲掉。
- ⚠️ **回退（清空 / 重置）没有进程锁守卫**（`rollback()` 不调 `check_process_lock()`）—— 进程在跑时它**不会拒绝**，照删不误；这一条只能靠 §1 第 1 条 + §4 的复核人守住。
- ❌ **不许把机器绝对路径写进 `index.json`**（§5）。
- ❌ **不许只写 `operator` 不写 `verifier`**（等于没做二次确认）。
- ⚠️ **手工编辑 JSON 前先停进程**（2.3）。

---

## 8. 收工自检（逐条打勾）

- [ ] 前置四条全过（进程停 / 路径解析过 / 备份在 / 台账先写）
- [ ] 动作是"清空 / 重置 / 改名"之一，**没碰 `data\`**
- [ ] `maintenance.log` 有 `operator` + `verifier` + 时间 + 命令 + 结果
- [ ] 有 `MANIFEST`（`MANIFEST-migrate-*.json` 或回退的 `MANIFEST-rollback-*.json`）
- [ ] 需要时跑过 §6 的四步演练，四条判据全过
- [ ] `index.json` 里没有绝对路径
- [ ] **回退类动作（清空 / 重置）动手前：进程已停 + 复核人在场**（回退没有工具守卫，见 §1 / §7）
