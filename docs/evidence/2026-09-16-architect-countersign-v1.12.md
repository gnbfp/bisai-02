# 证据：架构师独立复核 —— v1.12「迁移工具已落地」+ §11 数字口径

> **时间**：2026-09-16（架构师复核；v1.13 的 ②③④ 引用的就是本文件）
> **口径**：本文件只写**我复跑出来的东西**。开发自评的数字与实测不符的，这里订正并留差因；复跑不出来的，标「未验证」，不替它升级。
> **环境**：`D:\AI创新创业大赛`，Python **3.13.9**，pytest **8.4.2**；复核基线 = **`063e6b9`**（架构材料 v1.12）。
> **不写密钥**；`chat_id` / `open_id` 保留原值（是标识，不是凭据，且已在现场日志中出现）。

---

## 1. 复核对象的范围（先分清"自评"与"我复核过的"）

| v1.12 条目 | 性质 | 本次复核结论 | 落在本文 |
|---|---|---|---|
| ① 工具已落地 + 真跑演练 | 开发自评 | **通过**（独立复跑四步全通） | §3 |
| ② §3.4 读数表逐项复现（`load_*` 5→5 / 3→3 …） | 开发自评 | **部分**：覆盖率与 `verify.ok` 复跑到一致；**源盘逐项读数的"5 / 3 / 1 / 0"未独立复算** | §3.3 |
| ③ `pending_file` 跨会话守卫 | 开发自评 | **通过**（本次演练里真命中一次：`chat_id` 不一致 ⇒ 不搬 + `MANIFEST` 记一行） | §3.2 |
| ④ `MANIFEST` 唯一化（同秒两次不互相覆盖） | 开发自评 | **通过**（同秒两跑落 `…-113011.json` 与 `…-113011-2.json`） | §3.4 |
| ⑤ 新增回归 15 条 / `pytest` 436 | 开发自评 | **订正**：**17 条** / **438 passed** | §4 |
| ⑨ §11 数字改「复跑命令 + 输出」 | PM 指示 + 开发落笔 | **通过**（`tools\count_replies.py` 逐字复跑，快照逐字符一致） | §2 |
| ⑥⑦⑧⑩ | PM 裁决落地 / 代码去重 | **不在本次范围**（属开发交付面，未查） | — |

---

## 2. §11 口径复跑（`tools\count_replies.py`）

命令（源码根目录）：

```powershell
python tools\count_replies.py
```

原样输出（2026-09-16）：

```
[count_replies] src/gateway/replies.py
  all   = 78   (= len(__all__))
  text  = 73   (字符串字面量 69 + 非字面量模板 4 ['COMMANDS', 'COMMAND_LIST_DM', 'COMMAND_LIST_TEXT', 'REGISTER_FORM_BAD'])
  sym   = 5    ['Command', 'command_list', 'file_missing', 'needs_rubric', 'parse_failed']
  lines = 326
```

- 与 §11.1 贴的快照**逐字符一致** ⇒ §11 这节复核**通过**。
- 口径说明：`text = 73` 里含 4 个**非字面量模板**（`COMMANDS` / `COMMAND_LIST_DM` / `COMMAND_LIST_TEXT` / `REGISTER_FORM_BAD`），纯字符串字面量是 **69**。PM 说的「73 常量」与这里的 `text` 是同一个数，只是脚本给了更细的拆法。
- 独立第二路径（纯 AST，不 import 模块）复算，四数同值 ⇒ 两条路径互证。

---

## 3. 迁移工具演练复跑（`tools\migrate_workspace.py`）

**手法**：我自己跑一遍 干跑 → 迁移 → 复跑 → 回退，目标根落仓库外的临时目录（`_rehearsal`），**源根 `data\` 只读**。

### 3.1 四步结果

| 步 | 命令 | 结果 |
|---|---|---|
| 1 干跑 | `python tools\migrate_workspace.py --dest-root _rehearsal` | 打印计划 + `MANIFEST-…`；**未创建目标根** |
| 2 迁移 | 同上 `--apply` | `校验 = ok=True`、`覆盖率 = 4 / 4 missing=[]`、`源根未动=True`、**写盘次数 = 17** |
| 3 复跑 | 同上 `--apply` | **写盘次数 = 0、幂等 = True**（`index.workspace_entry = kept`） |
| 4 回退 | 同上 `--rollback` | 工作空间 `[removed]`、索引条目 `dropped`、**摘掉 3 条 `user_last_group` 绑定**、写盘次数 = 2 |

### 3.2 §3.3 第 3 步守卫（跨会话）真命中

源盘 `pending_file.chat_id=oc_6feb8f648197fd033b8de55a78f64d80` ≠ `group_chat_id=oc_33225a17a5b9fdde00a70f92d002a033` ⇒ 工具**不搬 `pending_file`**，只在 `MANIFEST` 记一行。与我复跑一致。

### 3.3 源盘（MVP `data\`）零改动 —— 硬证据

开工前 / 收工后各算一次 `data\` 的逐文件 sha256 拼接摘要：**21 个文件、1364 字符摘要、前后完全相同**（`SOURCE-UNTOUCHED = True`）。

### 3.4 `MANIFEST` 三份的字段（原样取值）

| 文件 | `action` | `workspace_changes` | `idempotent` | `index.workspace_entry` |
|---|---|---|---|---|
| `MANIFEST-migrate-20260916-113011.json` | migrate | 17 | False | `added` |
| `MANIFEST-migrate-20260916-113011-2.json` | migrate | **0** | **True** | `kept` |
| `MANIFEST-rollback-20260916-113011.json` | rollback | 2 | False | `dropped`（摘 3 条绑定） |

`verify.ok = True`，`coverage` 两侧 `eligible = covered = ['R2','R3','R4','R5']`、`missing = []`、`equal = True`。

**⇒ v1.12 ④ 的"同一秒跑两次不许互相覆盖"在我的复跑里**真出现并生效**（`-2` 后缀）。**

---

## 4. 与 v1.12 的差异（订正清单）

| # | v1.12 原文 | 实测 | 差因（推测 / 已知） |
|---|---|---|---|
| 1 | `tests\test_migrate_workspace.py` **15 条** | **17 条**（`--collect-only` 实测） | ④ 之后又补了用例，条数没回头改；材料已按 17 统一 |
| 2 | `pytest` **436 passed** | **438 passed**（基线 421 + 17） | 同上：436 = 421 + 15 |

**环境注记（复跑必看）**：本机 `%TEMP%\pytest-of-617` 被拒（`PermissionError: [WinError 5]`）⇒ 直接 `python -m pytest` 会有 95 个 setup error 的**假红**。复跑请显式指定可写的 basetemp：

```powershell
python -m pytest -q --basetemp=<可写目录>
```

---

## 5. 未覆盖 / 遗留（不算通过）

- **v1.12 ②的源盘逐项读数**（`load_rubric` 5 / `load_cards` 5 / `load_members` 3 / `load_preferences` 1 / `load_assignments` 0）——本次只复核了覆盖率与校验位，**没有独立复算这 5 个数字**。要把它变成硬证据，得单独跑一次读数脚本。
- **`pending_file` 之外的其他跨会话栏**（`seen.json` / `reminders.json` 的会话归属）——未逐一构造。
- **并发 / 中断 / 磁盘满**三类失败场景——未构造（`MANIFEST` 里"迁移中被 Ctrl+C"没有实测记录）。
- **真机面**（图片消息 × 群静默、投票窗 × 群内裸数字）：仍归 **9/18 彩排**（§4.6 的未覆盖格）。
'
