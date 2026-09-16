# 证据：`tools\migrate_workspace.py` 落地 + 演练（9/17 补丁批前半，§3.3 的证据）

> **时间**：2026-09-16（填写期跑通；批次排 **9/17 上午、U2 之前**）
> **用途**：`docs/ARCHITECTURE-UPGRADE.md` §3.3（七步）/ §3.4（读数表）/ §12.4 的 9/17 补丁批；审核 #2 补丁 1 + 3
> **手法**：工具**真跑** —— 干跑 → 迁移 → 复跑（验幂等）→ 回退，全程只落在 `data-upgrade\_rehearsal\`；MVP `data\` 只读
> **机器**：`D:\AI创新创业大赛`，Python 3.13.9。`pytest`：**438 passed**（基线 421 + 本轮新增 17）
> **不写密钥**；群标识保留完整值（它是 chat_id，不是凭据；且已在现场日志中可见）

## 1. 交付物

| 文件 | 内容 | 规模 | sha256（前 16） |
|---|---|---|---|
| `tools\migrate_workspace.py` | 干跑 / 迁移 / 回退 + `Resolve-Path` 守卫 + 幂等 + `MANIFEST`（§3.3 七步） | 933 行 / 35654 字节 | `DA61C8F66821C682` |
| `tests\test_migrate_workspace.py` | 17 条回归：幂等 / 守卫 / `pending_file` 跨会话 / 进程锁 / 回退 / MANIFEST 不互相覆盖 / 来源标签与 `created_at` 语义 | 293 行 / 12932 字节 | `1277A5713BC985BF` |
| `run-upgrade.ps1` | `-Echo` 只在 `-Probe` 时透传（+ 头注释一行用法），见 §12 | 85 行 / 3664 字节 | `F767E7B6CAF2AE28` |

**不进运行时**：`src\` 不 import 本模块（同 `tools\probe_feishu.py`）；默认干跑，`--apply` 才动盘。
**四条纪律**（写在模块 docstring 里）：只复制不移动 / 幂等 / 归属不明不猜 / 每一步留痕。

## 2. 干跑：`python tools\migrate_workspace.py --dest-root data-upgrade\_rehearsal`

原样输出（**一个字节都没写**；跑完 `data-upgrade\_rehearsal` 仍不存在）：

```
[tools/migrate_workspace.py v1.0] migrate · 干跑（一个字节都没写）
  源根   = D:\AI创新创业大赛\data
  目标根 = D:\AI创新创业大赛\data-upgrade\_rehearsal
  工作空间 = D:\AI创新创业大赛\data-upgrade\_rehearsal\workspaces\oc_33225a17a5b9fdde00a70f92d002a033  （可读名 课程任务书-02a033）
  备份   = D:\AI创新创业大赛\data-upgrade\_rehearsal\_migration\20260916-105347  [would_create]
    - assignment.json    copy
    - rubric.json        copy
    - cards.json         copy
    - preferences.json   copy
    - assignments.json   missing
    - proposals.json     missing
    - direction.json     copy
    - members.json       copy
    - state.json         copy
    - seen.json          copy
    - reminders.json     missing
    - report.md          copy
    - gantt.png          copy
  附件   = 4 个
  pending_file = 不搬（搬过去会被 _pending_file() 按会话拒掉（§3.3 第 3 步，v1.7）：pending_file.chat_id=oc_6feb8f648197fd033b8de55a78f64d80 != group_chat_id=oc_33225a17a5b9fdde00a70f92d002a033）
    跳过 probe：不在 §3.1 的 13 个候选名里（整份备份仍会覆盖它）
    跳过 state.json.bak：不在 §3.1 的 13 个候选名里（整份备份仍会覆盖它）
  MANIFEST = D:\AI创新创业大赛\data-upgrade\_rehearsal\_migration\MANIFEST-migrate-20260916-105347.json
exit=0
```

## 3. 迁移：`--apply`（第 1 次）

```
[tools/migrate_workspace.py v1.0] migrate · 已执行
  工作空间 = …\_rehearsal\workspaces\oc_33225a17a5b9fdde00a70f92d002a033  （可读名 课程任务书-02a033）
  备份   = …\_rehearsal\_migration\20260916-105529  [created]
    - 10 个已存在文件 copy、3 个 missing（assignments / proposals / reminders）
  附件   = 4 个
  校验   = ok=True 读数一致=True 覆盖率一致=True 负载哈希=True 附件哈希=True 源根未变=True
  覆盖率 = 4/4 missing=[]
  写盘次数 = 17  幂等=False
  MANIFEST = D:\AI创新创业大赛\data-upgrade\_rehearsal\_migration\MANIFEST-migrate-20260916-105529.json
```

MANIFEST 关键字段（原样摘录，空行略）：

```json
{
  "action": "migrate",
  "chat_id": "oc_33225a17a5b9fdde00a70f92d002a033",
  "readable_name": "课程任务书-02a033",
  "pending_file": {
    "migrated": false,
    "reason": "搬过去会被 _pending_file() 按会话拒掉（§3.3 第 3 步，v1.7）：pending_file.chat_id=oc_6feb8f648197fd033b8de55a78f64d80 != group_chat_id=oc_33225a17a5b9fdde00a70f92d002a033"
  },
  "skipped": [{"name": "probe", "reason": "不在 §3.1 的 13 个候选名里（整份备份仍会覆盖它）"},
              {"name": "state.json.bak", "reason": "不在 §3.1 的 13 个候选名里（整份备份仍会覆盖它）"}],
  "index": {"action": "created", "workspace_entry": "added",
            "user_last_group_added": ["ou_0040fcec9ebf80235a33c3afeed30e84",
                                      "ou_4537b96e5257168f1d9d13c6ad0227ea",
                                      "ou_01507b0ba78fef38ae31e86aef16637d"],
            "user_last_group_kept": []},
  "backup": {"dir": "…\_migration\\20260916-105529", "action": "created", "source_files": 22},
  "uploads": {"count": 4, "files": [{"path": "uploads/BIM 技术原理及其应用课程设.pdf", "action": "copy"},
                                    {"path": "uploads/软件系统设计与开发实践》课程任 1.pdf", "action": "copy"},
                                    {"path": "uploads/过年不放炮的软工导论课程报告.pdf", "action": "copy"},
                                    {"path": "uploads/854ccfa5-…_.docx", "action": "copy"}]},
  "kept_not_in_source": [],
  "verify": {"reads": {"rubric": {"source": 5, "workspace": 5, "equal": true},
                       "cards": {"source": 5, "workspace": 5, "equal": true},
                       "members": {"source": 3, "workspace": 3, "equal": true},
                       "preferences": {"source": 1, "workspace": 1, "equal": true},
                       "assignments": {"source": 0, "workspace": 0, "equal": true}},
             "reads_equal": true,
             "coverage": {"workspace": {"eligible": ["R2", "R3", "R4", "R5"],
                                        "covered": ["R2", "R3", "R4", "R5"], "missing": []},
                          "equal": true},
             "payload_hash_equal": true, "uploads_hash_equal": true,
             "ok": true, "source_unchanged": true},
  "workspace_changes": 17, "idempotent": false
}
```

（`state.json` 是唯一被改写的负载：`pending_file` 按守卫摘掉 ⇒ 目标侧 297 字节 vs 源侧 660 字节。）.

迁移后的 `index.json` 原样（**v1.12 起 `migrated_from` 记仓库相对路径**，不再把机器绝对路径写进索引）：

```json
{
  "workspaces": {
    "oc_33225a17a5b9fdde00a70f92d002a033": {
      "name": "课程任务书-02a033",
      "created_at": "2026-09-16T11:29:26",
      "migrated_from": "data"
    }
  },
  "user_last_group": {
    "ou_0040fcec9ebf80235a33c3afeed30e84": "oc_33225a17a5b9fdde00a70f92d002a033",
    "ou_4537b96e5257168f1d9d13c6ad0227ea": "oc_33225a17a5b9fdde00a70f92d002a033",
    "ou_01507b0ba78fef38ae31e86aef16637d": "oc_33225a17a5b9fdde00a70f92d002a033"
  }
}
```

## 4. 复跑：`--apply`（第 2 次，同一份源数据）

```
  备份   = …\_rehearsal\_migration\20260916-105529  [reused]
    - 10 个文件 unchanged、3 个 missing
  校验   = ok=True 读数一致=True 覆盖率一致=True 负载哈希=True 附件哈希=True 源根未变=True
  覆盖率 = 4/4 missing=[]
  写盘次数 = 0  幂等=True
  MANIFEST = …\_rehearsal\_migration\MANIFEST-migrate-20260916-105529-2.json
```

- **写盘 0 次**、备份 `reused`（`SOURCE.sha256` 认领，不堆第二份）、索引 `unchanged` / 条目 `kept`。
- 注意文件名尾巴的 **`-2`**：第 1 次与第 2 次落在同一秒，靠唯一化才没互相覆盖（见 §8）。

## 5. 回退：`--rollback`

```
  工作空间 = …\_rehearsal\workspaces\oc_33225a17a5b9fdde00a70f92d002a033  [removed]
  索引条目 = dropped；摘掉绑定 3 条
  写盘次数 = 2  幂等=False
  MANIFEST = …\_rehearsal\_migration\MANIFEST-rollback-20260916-105529.json
```

回退后 `index.json` 原样：

```json
{
  "workspaces": {},
  "user_last_group": {}
}
```

`workspaces\` 下条目数 = **0**；再跑一次 `--rollback` = `workspace=absent` / 写盘 0 次（回退也幂等）。

## 6. 源数据安全（独立复核，不信工具自证）

- 工具的 `verify.source_unchanged` = `True`；
- **独立**比对：跑前 / 跑后对 `data\` 递归取 SHA256，**21 个文件哈希完全一致 = True**（含 `uploads\` 4 个附件、`probe\` 里的 PDF、`state.json.bak`）；
- `data\` 下无 `*.tmp` 残留；`data-upgrade\_rehearsal\` 之外没有任何新路径。

## 7. 与 §3.4 读数表逐项对表

| 读法 | §3.4（2026-09-15 演练） | 本轮（2026-09-16，工具跑） |
|---|---|---|
| `load_rubric()` | 5 → 5 | **5 → 5** |
| `load_cards()` | 5 → 5 | **5 → 5** |
| `load_members()`（按人数） | 3 → 3 | **3 → 3** |
| `load_preferences()` | 1 → 1 | **1 → 1** |
| `load_assignments()` | 0 → 0（不算证据力） | **0 → 0**（同口径，不算证据力） |
| `coverage_loop()` 分子/分母 | 4 / 4（`missing=()`） | **4 / 4（`missing=()`）** |
| `index.json` | 1 工作空间 / 3 人绑定 | **1 工作空间 / 3 人绑定**（回退后清空） |

覆盖率那一行是**逐项相等断言**（`coverage.equal = true`），不是"看起来一样"。

## 8. 演练当场抓到的真缺陷：MANIFEST 同名互相覆盖（已修）

第 1 次跑完再跑第 2 次时发现：两次都落在**同一秒** ⇒ `MANIFEST-migrate-<时间戳>.json` **同名**，第 2 次把第 1 次的记录**覆盖**了 —— 盘上只剩"写盘 0 次"那份，"17 次写盘"的证据没了。**记录丢了等于没跑过**，与"每一步留痕"直接冲突。

处置：`_unique_path()` 同名时加 `-2` / `-3` 后缀（真跑里可见 `MANIFEST-migrate-20260916-105529-2.json`），并补 1 条用例 `test_manifests_do_not_collide_across_runs_in_the_same_second`（用固定 `now` 强制同秒）。

## 9. 回归网：15 条用例 + 变异验证

`tests\test_migrate_workspace.py`（17 个 test）覆盖：干跑不写盘 / 首次迁移 + 索引形状 / **复跑幂等（写盘 0）** / 索引已有键不被覆盖（改名与运行时绑定） / **源根零改动** / `pending_file` 不一致不搬 + 一致才搬 / `group_chat_id` 空即中止 / **`guard_within` 拒绝根本身与越界** / 源目标根不许互相包含 / 路径段防穿越（`..`、`a/b`）/ `resolve_path` 容忍不存在的尾巴 / 活进程锁阻断（`--force` 可跳过）/ 回退删副本 + 摘悬挂绑定 + 回退幂等 / MANIFEST 同秒不互相覆盖 / **仓库内源根记相对路径、不写机器绝对路径** / **`created_at` = 登记时刻且重跑不覆盖**。

**变异验证**（改一行看用例咬不咬得住；跑完按字节还原，sha256 前后一致）：

| 变异体 | 结果 |
|---|---|
| 幂等：索引条目永远覆盖（`entry_action` 恒为 `added`） | **2 failed**, 13 passed |
| 守卫：`guard_within` 直接放行 | **1 failed**, 14 passed |
| `pending_file` 跨会话守卫失效（条件恒假） | **1 failed**, 14 passed |

## 10. 这份演练证明了什么 / 没证明什么

**证明了**

1. 工具的**干跑 / 迁移 / 复跑 / 回退**四步真跑通，且**复跑写盘 0 次**（幂等不是口头承诺）。
2. §3.4 的读数表与覆盖率**逐项复现**（5/5、5/5、3/3、1/1、0/0、4/4）。
3. §3.3 第 3 步（v1.7）的 `pending_file` 跨会话守卫**在真数据上命中**（源盘那两个 chat_id 确实并存，见 §3.6）。
4. 源数据**一个字节都没动**（工具自证 + 独立哈希比对，21 个文件）。
5. `Resolve-Path` 守卫**拦住越界写/删**（含"目标 = 根本身"）。

**没证明（不得当成通过）**

- [ ] **真实目标根（`data-upgrade\`）上的迁移没跑** —— 本轮只跑 `_rehearsal`（PM 2026-09-16 明令"只在 `data-upgrade\_rehearsal` 上跑，一个字节都别碰 `data\`"）。真跑要等 9/17，且跑前必须**停升级版进程**（工具会读 `app.lock` 的 pid 并阻断，CLI 实测见 §11；**另注**：现网那个 `app.lock` 的 pid=70576 是 2026-09-16 10:43 冒烟那次进程，实测**已不在** ⇒ 工具按"已停"放行 —— 真跑前请重看这个文件）。
- [ ] **迁移中断**（复制到一半）的现场处置：仍是"先备份 + 重跑幂等"兜，**未演练**（§3.5 原样保留）。
- [ ] ≥2 个工作空间**同时活跃**的并发写（`index.json` 仍是全局热点）。
- [ ] 手册 `docs\OPERATIONS-U2.md` 与 `data-upgrade\maintenance.log`（归架构师，随 U2 交付）。
- [ ] **"重跑演练 + `MANIFEST`"的验收归架构师** —— 本文件是开发侧自测证据，不等于验收通过。
- [ ] 待认 3 条（工具层读法，文档未定，见 §12.4 / §13）：`migrated_from` 取值形态 / `created_at` 语义 / 回退时顺带摘 `user_last_group` 悬挂绑定。

## 11. 守卫在 CLI 上的实测（三条，均不写盘）

**① 目标根落在源根之内** —— `python tools\migrate_workspace.py --source-root data --dest-root data\_inner --apply`

```
[迁移中止] 源根与目标根不能重合或互相包含：D:\AI创新创业大赛\data / D:\AI创新创业大赛\data\_inner
exit=2
```

**② 回退时 `--chat-id` 带目录穿越** —— `--rollback --chat-id ..\..\data`

```
[迁移中止] 非法路径段 '..\..\data'：只允许 [A-Za-z0-9_-]（防目录穿越）
exit=2
```

**③ 目标根上有活进程** —— 临时目标根（`%TEMP%\mw-lock-demo`）+ 写一份"活 pid"的 `app.lock`

```
[迁移中止] 升级版进程还在跑（app.lock 存在（pid=59216, started_at: 2026-09-16T11:00:00））—— 先停进程，或显式加 --force
exit=4
```

同一目标根加 `--force` 后照常跑完（`写盘 17 次`、`校验 ok=True`），落点在 `%TEMP%\mw-lock-demo\`（**不在仓库里**）。

**两条与真跑有关的补充事实**

- 现网 `data-upgrade\app.lock` = `{"pid": 70576, "started_at": "2026-09-16T10:43:33", "port": 47654}` —— 那是冒烟那次的进程，**实测已不在** ⇒ 工具会按"已停"放行。真跑（9/17）之前重看这个文件，别拿旧的当"已停"。
- 本轮**没有**对真实目标根 `data-upgrade\` 跑过迁移：一次尝试被**沙箱的文件权限**挡在 `mkdir data-upgrade\_migration` 上（`WinError 5`），当场复核 **`data-upgrade\_migration` 不存在、源根 digest 与 `MANIFEST` 记录逐字节相同** ⇒ 没留下半截状态。（这是沙箱限制，不是工具行为；但也说明"写到一半被打断"的现场处置仍未演练，见 §10。）

## 12. v1.12 收尾：PM 2026-09-16 的四条裁决 + 一条顺手清理

**① `migrated_from` 记仓库相对路径**（原来 `str(source_root)` 会把 `D:\AI创新创业大赛\data` 写进索引）：新增 `source_label()` —— 仓库内的源根记仓库相对路径（`data`），仓库外的（回归用例的临时目录）退成解析后的绝对路径。落地后的 `index.json` 见 §3；用例 `test_source_label_is_repo_relative_for_repo_sources` 钉住"里面不允许出现 `:`"。

**② `created_at` 语义写明**（原名不副实）：= 该工作空间在索引里的**登记时刻**（懒创建的工作空间 = 首条消息那刻；迁移进来的 = 迁移时刻），重跑**不覆盖**已有值（字段名沿用 §3.3 第 5 步的字面）。用例 `test_created_at_means_registration_time_and_survives_reruns`：同一目标根，`now` 从 `2026-09-17T09:00` 推到 `10:00`，索引里仍是 `09:00`。**手册 `docs\OPERATIONS-U2.md` 需要抄这句**（归架构师）。

**③ 回退摘 `user_last_group` 悬挂绑定** —— PM 认，**保持原样**（理由：悬挂绑定会把私聊路由到已删工作空间）。

**④ `-Echo` 选 ② 落地**：`run-upgrade.ps1` 只在 `-Probe` 时透传 `--echo`，脚本头补一行用法。用一次性打桩 `python.cmd`（只 `echo` 参数）截获三种组合，原样输出：

```
--- 不带 -Probe，只加 -Echo（旧版本这里会 exit 2）---
STUB-ARGS -m src.gateway.app
--- -Probe -Echo（探针侧要拿到 --echo）---
STUB-ARGS -m tools.probe_feishu --save-dir D:\AI创新创业大赛\data-upgrade\probe --echo
--- -Probe（不传 --echo）---
STUB-ARGS -m tools.probe_feishu --save-dir D:\AI创新创业大赛\data-upgrade\probe
```

脚本语法：`[System.Management.Automation.Language.Parser]::ParseFile(...)` ⇒ **ParseError 数 = 0**；文件仍是 **UTF-8 带 BOM**（Windows PowerShell 5.1 读中文的前提，已复核头 3 字节）。

**⑤ 顺手清理**：`tests\test_gateway_router.py` 的 `_nobody` 原本定义两处（`:36` / `:735`，签名只差一个默认参数），**并掉**，保留带默认值的那份（docstring 合并）。`pytest` **438 passed**（基线 421 + 本轮 17）。
