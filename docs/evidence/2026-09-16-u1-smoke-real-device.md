# 真机冒烟：U1 门禁 + `作业书` 两条链路（2026-09-16 10:44–10:46）

**目的**：U1（群聊必须 @）落地后**必须真机验一次** —— 单测离线跑得再全，也证明不了"平台上 @ 到底长什么样"。
**环境**：升级版机器人 `机器人007`（`FEISHU_APP_ID` 见 `.env.upgrade`，不入库）· 独立测试群 `oc_2d805f19bf755763edd6c63b835f01df` ·
`data-upgrade\` 数据根 · 单实例锁端口 47654 · `run-upgrade.ps1 -Seconds 900`（`PYTHONUTF8=1` + `PYTHONUNBUFFERED=1`）。
**跑的人**：真人（PM）在飞书里发消息；开发起进程、读日志。

## 1. 原样日志（`recv` = 收到，`-> … ok` = 回话）

原始文件：`%TEMP%\u1_smoke.log`（2026-09-16 10:46:40 收尾，**3332 字节 / 24 行**；复核时 sha256 前 16 = `7EB8633B39C147DB`）。

下面贴的是该文件的**第 9–23 行（15 行）逐字原文**（行尾统一为 LF 存放，内容一字未改）。未贴的四类：脚本启动横幅、两条 Python 依赖 warning、`[Lark] connected to wss://…` 那一行（带 `access_key` / `ticket`，按 `.gitignore` 的口径「运行日志可能含凭据，禁止入库」剔除）、以及最后的退出行 —— **被剔除的只有这些**。`%TEMP%` 会被系统清理，所以内容在这里贴全。

```
[M0] 2026-09-16T10:44:31 recv id=om_x100b65946624b514b24107288bc1c34 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 你好
[M0] 2026-09-16T10:44:32 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 直接说要做哪件就行：
1. 把作业书发进群，再 @我 说「作业书」—— 我抽评分
[M0] 2026-09-16T10:44:39 recv id=om_x100b659467b90914b2ef3cc9c75577e chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=大家好
[M0] 2026-09-16T10:44:53 recv id=om_x100b6594649c60b0df99e9a182d13fd chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=file text=
[M0] 2026-09-16T10:45:05 recv id=om_x100b659465d9c4bcb3f4aed722328c5 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 作业书
[M0] 2026-09-16T10:45:06 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，开始解析作业书，大概半分钟。
Consider using the pymupdf_layout package for a greatly improved page layout analysis.
[M0] 2026-09-16T10:45:15 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 《营销方案计划》 电子商务技能检测｜交付：现场操作，小组合作完成一份营销计划方案
[M0] 2026-09-16T10:45:21 recv id=om_x100b659462da5cacb39f164983abd5d chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=作业书
[M0] 2026-09-16T10:45:44 recv id=om_x100b659463b088a0dfe9ad74b7e591c chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=file text=
[M0] 2026-09-16T10:45:45 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 《营销方案计划》任务书.pdf》我拿到了，回「作业书」我就开始解析。
[M0] 2026-09-16T10:45:48 recv id=om_x100b6594637408b0b32aab79593c03c chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=作业书
[M0] 2026-09-16T10:45:49 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 收到，开始解析作业书，大概半分钟。
[M0] 2026-09-16T10:45:57 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 《营销方案计划》 电子商务技能检测｜交付：现场操作，小组合作完成一份营销计划方案
```

对着 §2 的时间戳读：`10:44:39` / `10:44:53` / `10:45:21` 三处**只有 `recv`、没有 `-> ` 行** —— 那就是「静默」在日志里的样子。

**一处读日志的注意点**：`10:44:32` 那条回话的清单第 1 行在**原始日志里就是断的** —— 到「我抽评分」为止（原文件那个字节位置之后直接就是 `\r\n`，不是本文件贴漏）；完整正文以 §2 ① 引的那句为准（`…我抽评分点、拆任务卡`）。

## 2. 逐条结论

| # | 动作 | 期望 | 实际（看日志） |
|---|---|---|---|
| ① | 群里 `@机器人007 你好` | 有回应（门禁放行） | `10:44:31 recv` → `10:44:32 -> … ok | 直接说要做哪件就行：` ✅ |
| ② | 群里 `大家好`（不 @） | 静默 | `10:44:39 recv` → **没有 `-> ` 行** ✅ |
| ③ | 群里投 PDF（不 @） | 静默 + 缓存 | `10:44:53 recv … type=file` → **没有 `-> ` 行**；随后 ④ 命中缓存 ✅ |
| ④ | 群里 `@机器人007 作业书` | 出评分点 | `10:45:06 PARSING` → `10:45:15` 核对清单；`rubric.json` **12 条评分点** / `cards.json` **7 张卡** ✅ |
| ⑤ | 群里 `作业书`（不 @） | 静默（**门禁吃掉自己教的动作**那一格） | `10:45:21 recv` → **没有 `-> ` 行** ✅ |
| ⑥ | 私聊投 PDF → `作业书` | 回执 → 出评分点 | `10:45:45` 回执（私聊保留）→ `10:45:49 PARSING` → `10:45:57` 核对清单 ✅ |

**文案修复的真机证据（这一轮改的那 4 处）**：① 的回应正文第 1 条已经是
`1. 把作业书发进群，再 @我 说「作业书」—— 我抽评分点、拆任务卡` —— 修之前这里写的是"再回「作业书」"，
而 ⑤ 证明**群里不 @ 就是静默**：机器人当时在教一个必然被自己门禁吃掉的动作。

## 3. 落盘证据（`data-upgrade\`）

```
10:45:08  129583  uploads\营销方案计划》任务书.pdf        ← 私聊那份被下载
10:45:14     260  assignment.json   ← 作业元信息（storage.py:52 的 ASSIGNMENT：课程 / 标题 / 截止）
                                      分配记录是**另一个文件**：assignments.json（storage.py:56），本盘尚未产生 —— 这两个名字别当笔误
10:45:14    3000  rubric.json      → 12 条评分点（R1…R12，status=normal）
10:45:14    2925  cards.json       → 7 张任务卡（T1…T7，带 rubric_refs）
10:45:15      64  state.json       → pending_file 已被消费（只剩 group_chat_id）
10:45:21     803  seen.json        → 14 条 message_id（去重台账）
```

## 4. 没覆盖的（不许当成通过）

- **图片消息**（群里静默 / 私聊拒回收执）本轮没发。
- **投票窗 × 群内裸数字**、**投票中 `@` 作业书**（§4.3 矩阵的另两格）本轮没发。
- **`@` 识别是哪条判据命中的**：`mentioned_type` 与 `FEISHU_BOT_OPEN_ID` 兜底**同时配着**，
  日志分不出是哪一条让 ① 通过的 —— 想单独验 `mentioned_type` 就把 `FEISHU_BOT_OPEN_ID` 临时清空再发一条。
- 私聊归属（双群用户）与 U2/U3/U4 的全部链路：不属本轮。
