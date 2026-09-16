# U2 落地后真机验收（`ACCEPTANCE-U2.md` §1–§5）—— 2026-09-16 20:04–20:18

**目的**：U2（④-a 两段式工作空间 + ④-1 拆回退）落地入库后，趁**人齐**按 `docs\ACCEPTANCE-U2.md` 把三条证据槽（§1 双群绑定 / §2 按人 `NEED_GROUP` / §3 并发后到者胜出）与两条回归（§4 条件写 / §5 投票块缺 `chat_id`）一次跑完。
**依据**：`docs\ACCEPTANCE-U2.md` §0–§6 · 对齐卡 `docs\evidence\2026-09-16-u2-single-value-mapping-alignment.md` §5 的签字口径（#1 键 = `sender_open_id` / #3 静默也算互动 / #4 刷新在 `handle()` / #7 两处回退 / #9 来源标题）。
**被测提交**：`21fd34a`（④-a 两段式工作空间）—— 其前依次 `ceaf62a`（④-1 拆 `exempt()`/`accept()` 两处回退）、`5dcb019`（③ 条件写）、`18820b7`（② 回退锁守卫）、`aa742c0`（① `方向` 成员判据）。
**前置**：`python -m pytest -q` = **456 passed / 8 warnings**（`21fd34a` 上复跑）。
**环境**：机器人 `机器人007`（凭据 `.env.upgrade`，不入库）· 群A = **新机器人测试1群** `oc_2d805f19bf755763edd6c63b835f01df` · 群B = **新机器人测试2群** `oc_3e969aae31860e36f1c8652e3f666578` · 数据根 `data-upgrade\` · 单实例锁端口 47654 · `run-upgrade.ps1 -Seconds 3600`（`PYTHONUTF8=1` + `PYTHONUNBUFFERED=1`）。
**跑的人**：真人（PM）在飞书里发消息；开发起进程、读日志、并以 1 秒 / 300 毫秒两级采样 `index.json` 的值与 `mtime`。
**日志**：`D:\rehearsal-logs\u2_acceptance-20260916-195543.log`（105 行 / 13242 B）—— 带时间戳文件名，未覆盖任何旧日志。**本文剔除**：启动横幅、`[M0] 正在建立长连接…`、依赖 warning、`[Lark] connected to wss://…`（带 `access_key`/`ticket`，禁止入库）。
**收工**：显式 `Stop-Process -Id 74596 -Force`（不靠 `-Seconds`）；之后 `Get-Process python` 为空、端口 47654 为空。

> 文件名按**项目日历 9/17**（PM 口径）；机器时间戳一律是 `2026-09-16T20:xx`，两者差一天，别当成笔误。

## 结论速览

| 槽 | 判据 | 结果 |
|---|---|---|
| §1 双群绑定 | 私聊回话**首行** = 绑定群的作业书标题；`index.json` 值随「最后一条群消息」变；反向再验一次 | ✅ |
| §2 按人 `NEED_GROUP` | 未绑定者私聊**多条**归属类指令都回 `NEED_GROUP`；索引**不出现**该人；日志无 pipeline | ✅ |
| §3 并发后到者胜出 | 5 轮 A/B 各一句；每轮值与**后到**那条一致；无丢更新 | ✅ |
| §4 条件写 | 值不变 ⇒ 不落盘（`mtime` 不动） | ✅ 单测 + 真机 |
| §5 投票块缺 `chat_id` | 缺块不豁免/不计票（单测）；正常开窗块 ⇒ 群内裸数字计票 | ✅ 单测 + 真机正面对照 |

## 0. 先看这三条，否则会误判（本轮真踩过）

1. **④-a 之后 root 变了**：运行时只读 `data-upgrade\workspaces\<群 chat_id>\`。`data-upgrade\` **顶层**那批扁平文件（9/16 彩排留下的 `cards.json` / `members.json` / `state.json` …）**运行时一个字都不读**（进程根 store 只剩 `index.json` / `app.lock` / `bound_chats()` 三处用途），`pending_file` 又按 v1.7 守卫没搬进工作空间。⇒ **「盘上有」≠「机器人看得见」**，本轮两个群必须现场重建。
2. **两个测试群的工作空间起手是空的**，所以各做了一遍：投 PDF（群里静默、落 `pending_file`）→ `@机器人007 作业书`（出评分点 + 任务卡）→ `@机器人007 登记`（3 人花名册，`registered_at` 群A `20:04:53` / 群B `20:05:35`，组长 = 神）。两群标题**故意不同**：群A《营销方案计划》（`cards.json` 2624 B）、群B《数据库课程设计任务书》（`1331 B`）—— §1 靠它分 A/B。
3. **§1 第一次没跑出来，卡的不是绑定**：`你想做哪一块` 私聊有**两道前置**（`src\gateway\preference.py:87` 先判 `cards`、再判 `roster`；`replies.py:283`），缺花名册就回 `PREFERENCE_NEED_ROSTER`，**首行不会有来源标题**。原样：

```
[M0] 2026-09-16T20:01:00 recv id=om_x100b659c010084b4b1a4776cefe288a chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=你想做哪一块
[M0] 2026-09-16T20:01:01 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 还没有花名册。先在群里回「登记」，再回「你想做哪一块」。
```

## 1. 证据槽 ①：双群绑定 —— 先 A 再 B ⇒ 私聊看 B（含反向）✅

原样日志（20:06:25 – 20:07:23，`recv` / `-> ok` 成对）：

```
[M0] 2026-09-16T20:06:25 recv id=om_x100b659c2adb0cb0b14bcff529ba510 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 收到A
[M0] 2026-09-16T20:06:38 recv id=om_x100b659c2a217cacb11b1b7e4749f1b chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 收到B
[M0] 2026-09-16T20:06:50 recv id=om_x100b659c2b67dca4b0351d323b95756 chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=你想做哪一块
[M0] 2026-09-16T20:06:50 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 当前任务卡来自《数据库课程设计任务书》（3 张）
[M0] 2026-09-16T20:07:09 recv id=om_x100b659c282de8acb10aa8241a3ce3f chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 收到A2
[M0] 2026-09-16T20:07:22 recv id=om_x100b659c29665ca8b48beccfcb57da9 chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=你想做哪一块
[M0] 2026-09-16T20:07:23 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 当前任务卡来自《营销方案计划》（7 张）
```

- **正面**：20:06:50 私聊首行 = 《数据库课程设计任务书》 = **群B**（20:06:38 最后一条群消息在 B）✅
- **反向**：群A 20:07:09 后再私聊（20:07:22）⇒ 首行变《营销方案计划》 = **群A** ✅ ⇒ 是「最后一次胜出」，不是「首次绑定生效」。
- **索引**：`ou_b8f6fdba44c4bdaa6cb1775c55f5f06f` 20:06:50 读作 `oc_3e969aae…`（群B），20:07:09 后写为 `oc_2d805f…`（群A），`mtime` = 20:07:09 ✅
- **对齐卡 #9**（私聊回话也必须带来源标题）✅ —— 首行 24 字，没被日志 40 字裁剪切到。

## 2. 证据槽 ②：从没互动过 ⇒ 按人 `NEED_GROUP` ✅

**丙 = `ou_038fbabf3dc05aabc02410bf73c9269d`（昵称「勉强算个人」）** —— 两个群都在，但从开窗到此刻**在群里一句话没发过**（文件也没发）。**顺序按 §2 纪律：丙先、甲后，中间不插别的动作。**

```
[M0] 2026-09-16T20:08:07 recv id=om_x100b659c24b1c0a8b10c700ee941566 chat=oc_9c5f7b4bf0d19c178ca24f2ef16740b9 from=ou_038fbabf3dc05aabc02410bf73c9269d type=text text=你想做哪一块
[M0] 2026-09-16T20:08:07 none 没有绑定 id=om_x100b659c24b1c0a8b10c700ee941566
[M0] 2026-09-16T20:08:08 -> chat_id:oc_9c5f7b4bf0d19c178ca24f2ef16740b9 ok | 我还不知道你是哪个群的。先在群里发一次指令，比如「作业书」，我就认下这个群。
[M0] 2026-09-16T20:08:17 recv id=om_x100b659c25e9bcb0b3907b25647f103 chat=oc_9c5f7b4bf0d19c178ca24f2ef16740b9 from=ou_038fbabf3dc05aabc02410bf73c9269d type=text text=作业书
[M0] 2026-09-16T20:08:17 none 没有绑定 id=om_x100b659c25e9bcb0b3907b25647f103
[M0] 2026-09-16T20:08:18 -> chat_id:oc_9c5f7b4bf0d19c178ca24f2ef16740b9 ok | 我还不知道你是哪个群的。先在群里发一次指令，比如「作业书」，我就认下这个群。
[M0] 2026-09-16T20:08:55 recv id=om_x100b659c2348bca4b1caba40943e545 chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=你想做哪一块
[M0] 2026-09-16T20:08:56 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 当前任务卡来自《营销方案计划》（7 张）
```

- 丙两条**都**走 `none 没有绑定`（`src\gateway\app.py` 的 `handle()` 第一步）⇒ 判据是**按人**的，且**覆盖多条指令**（不是只堵 `我想提议：`）✅
- `index.json` 里**没有** `ou_038fbabf…`；更强的证据是 `mtime`：从 20:07:09 一直**到 20:10:52 都没动过**（1 秒采样 171 个点）⇒ **不落盘** ✅
- 丙那条没有 `-> ` 之外的任何行 ⇒ **没起 pipeline**（工单 §2 判据）✅
- 甲（成员）随后那条仍正常出《营销方案计划》⇒ 丙的两条没污染状态 ✅

## 3. 证据槽 ③：绑定写入的并发正确性 —— 5 轮 ✅

recv 原样（每轮 A 先、B 后，轮间约 12 秒）：

```
[M0] 2026-09-16T20:10:50 recv id=om_x100b659c3a7530a0c4abc1828f36ed9 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮1A
[M0] 2026-09-16T20:10:53 recv id=om_x100b659c3a2d04acdd87dc0463f8622 chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮1B
[M0] 2026-09-16T20:11:06 recv id=om_x100b659c3b66e0a0c4f0cd29c1f4f94 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮2A
[M0] 2026-09-16T20:11:08 recv id=om_x100b659c3b0660a8c2497b4e12ab72e chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮2B
[M0] 2026-09-16T20:11:20 recv id=om_x100b659c385c88acc255e347141202a chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮3A
[M0] 2026-09-16T20:11:22 recv id=om_x100b659c386074a4c258de04f08585a chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮3B
[M0] 2026-09-16T20:11:33 recv id=om_x100b659c39a43ca4c4f3a2ecd6f8949 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮4A
[M0] 2026-09-16T20:11:35 recv id=om_x100b659c394b64a4c223c0507925f93 chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮4B
[M0] 2026-09-16T20:11:49 recv id=om_x100b659c369654a8df9ba0cefec8277 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮5A
[M0] 2026-09-16T20:11:51 recv id=om_x100b659c36b640acc439492aebf9c0b chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@机器人007 轮5B
```

`index.json` 采样（1 秒一次；只列**值变化过**的采样点，`mtime` 与 `recv` 秒级对齐）：

```
20:09:19 | mtime=20:07:09 | oc_2d805f19bf755763edd6c63b835f01df      ← 起手（§1 反留下的群A）
20:10:53 | mtime=20:10:53 | oc_3e969aae31860e36f1c8652e3f666578      ← 轮1：A(20:10:50) 值没变⇒没写，B 写
20:11:06 | mtime=20:11:06 | oc_2d805f19bf755763edd6c63b835f01df      ← 轮2 A
20:11:08 | mtime=20:11:08 | oc_3e969aae31860e36f1c8652e3f666578      ← 轮2 B
20:11:20 | mtime=20:11:20 | oc_2d805f19bf755763edd6c63b835f01df      ← 轮3 A
20:11:22 | mtime=20:11:22 | oc_3e969aae31860e36f1c8652e3f666578      ← 轮3 B
20:11:33 | mtime=20:11:33 | oc_2d805f19bf755763edd6c63b835f01df      ← 轮4 A
20:11:36 | mtime=20:11:35 | oc_3e969aae31860e36f1c8652e3f666578      ← 轮4 B
20:11:49 | mtime=20:11:49 | oc_2d805f19bf755763edd6c63b835f01df      ← 轮5 A
20:11:51 | mtime=20:11:51 | oc_3e969aae31860e36f1c8652e3f666578      ← 轮5 B（末值）
```

| 轮 | recv A | recv B | 索引轨迹 | 判 |
|---|---|---|---|---|
| 1 | 20:10:50 | 20:10:53 | 20:10:50 **不写**（值本来就是 A）→ 20:10:53 = **B** | ✅ |
| 2 | 20:11:06 | 20:11:08 | A → **B** | ✅ |
| 3 | 20:11:20 | 20:11:22 | A → **B** | ✅ |
| 4 | 20:11:33 | 20:11:35 | A → **B** | ✅ |
| 5 | 20:11:49 | 20:11:51 | A → **B** | ✅ |

- 10 条群消息、9 次写盘（轮1 的 A 因值未变按条件写跳过），**mtime 与 recv 一一对上，无一轮丢更新**；末值 = 群B，与**最后一条**群消息（20:11:51）一致 ✅
- 写盘路径 = `JsonStore.mutate_raw()` 的**锁内读-改-写**；索引文件 810 B / 5 条绑定。

## 4. 回归（对齐卡 #5）：`storage` 不再「没变化也写盘」✅

**单测（主判据，已落地 `5dcb019`）**：`mutate_raw(name, lambda doc: doc)` 原样返回 ⇒ 文件字节与 `mtime` 都不变；同形状再测 `mutate_many`。

**真机手工格（本轮补做；300 毫秒采样）** —— 必须先让值离开群B，否则第一次就不写、看不出「第一条写」：

```
[M0] 2026-09-16T20:15:29 recv id=om_x100b659cc8e80ca0b1112653cf72854 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 铺垫
[M0] 2026-09-16T20:15:46 recv id=om_x100b659cc9e03c40b2a51420ea3f19c chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 四一
[M0] 2026-09-16T20:15:52 recv id=om_x100b659cc947dcb8b2e86ec6ee6373c chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 四二
```

```
20:13:59.376 | mtime=20:11:51.156 | oc_3e969aae…    ← 起手（§3 末值）
20:15:29.959 | mtime=20:15:29.747 | oc_2d805f…     ← ① 群A「铺垫」：值变 A ⇒ 写盘
20:15:46.567 | mtime=20:15:46.468 | oc_3e969aae…   ← ② 群B「四一」：值变 B ⇒ 写盘
20:16:10.754 | mtime=20:15:46.468 | oc_3e969aae…   ← ③ 群B「四二」：值没变 ⇒ **mtime 不动** ✅
```

判据（第一条之后变、第二条之后不动）**成立** ✅。§3 轮1 的 A（20:10:50）是同一条机制在真机上的第二次显形。

## 5. 回归（对齐卡 #7）：投票块缺 `chat_id` ⇒ 不豁免、不算票 ✅

**单测（主判据，已落地 `ceaf62a`）**：`tests\test_vote.py::test_a_window_block_without_chat_id_neither_exempts_nor_counts` —— 孤儿块（有 `state.group_chat_id`、**块内无 `chat_id`**）下 `vote.exempt(...)` 返回 False、`vote.accept(...)` 不计票；反向对照（块里有 `chat_id`）行为与升级前一致。

**真机正面对照（本轮补做，群B）** —— 3 人花名册（20:05:35 冻结，未再登记）：

```
[M0] 2026-09-16T20:16:05 recv id=om_x100b659cc6ab1c70b24370254915d1c chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 方向
[M0] 2026-09-16T20:16:06 -> chat_id:oc_3e969aae31860e36f1c8652e3f666578 ok | 收到，按评分点想几个候选方向，大概半分钟。
[M0] 2026-09-16T20:16:09 -> chat_id:oc_3e969aae31860e36f1c8652e3f666578 ok | 候选方向（仅供参考，由全组拍板）：
[M0] 2026-09-16T20:16:14 recv id=om_x100b659cc63b4cb8b29bb5883739a39 chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=1
[M0] 2026-09-16T20:16:15 -> chat_id:oc_3e969aae31860e36f1c8652e3f666578 ok | 记下了，你投的是 1. 校园二手交易平台数据库设计与实现。想改再回一次数字。
[M0] 2026-09-16T20:16:59 recv id=om_x100b659cc50d80a0c378bb659b35d8c chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_a79861323d0c6f45676d3f62b68284e3 type=text text=2
[M0] 2026-09-16T20:17:00 -> chat_id:oc_3e969aae31860e36f1c8652e3f666578 ok | 记下了，你投的是 2. 高校选课管理系统数据库设计与实现。想改再回一次数字。
[M0] 2026-09-16T20:17:50 recv id=om_x100b659cc03874a8c2e40e141f52e74 chat=oc_3e969aae31860e36f1c8652e3f666578 from=ou_a79861323d0c6f45676d3f62b68284e3 type=text text=1
[M0] 2026-09-16T20:17:51 -> chat_id:oc_3e969aae31860e36f1c8652e3f666578 ok | 记下了，你投的是 1. 校园二手交易平台数据库设计与实现。想改再回一次数字。
[M0] 2026-09-16T20:17:52 -> chat_id:oc_3e969aae31860e36f1c8652e3f666578 ok | 方向定了：1. 校园二手交易平台数据库设计与实现，过半：2/2 票。
```

- 20:16:14 = 神**不 @**发裸数字 ⇒ **计票**（免 @ 白名单 = `exempt()`：窗开着 + 开窗那个群 + 花名册成员 + 纯数字）；20:16:59、20:17:50 雨鑫左 两票（含**改票**）同样豁免 ✅
- 门槛按 D-36：`ceil(3/2)=2` 票且集中在方向 1 ⇒ `过半：2/2 票` 落定 ✅（花名册全程 3 人，没顶门槛）
- 结算后 `workspaces\oc_3e969aae…\state.json` = `{awaiting:null, preference:null, vote:null, register:null}`（投票块已清）；`direction.json` 原样：`decided_at 2026-09-16T20:17:50` / `source: vote` / `votes: {神:1, 雨鑫左:1}` / `tally {1:2,2:0,3:0}` / `reason: 过半落定`。
- **口径说明**：窗口**带 `chat_id`** 的快照没抓到（结算后块被清）。正面对照 = 计票**成功**这件事本身：`ceaf62a` 之后不再有全局回退，计数只可能走「块内 `chat_id` == 所在群」这一条路。负面（缺 `chat_id`）由上面那条单测钉住。

## 6. 收尾核验

### 6.1 MVP `data\` 全程只读 ✅

口径 = `tools\migrate_workspace.py::tree_digest`（按相对路径排序，逐文件 sha256 后再整串 sha256）：

- 验收结束时重算 = `8948C043C15874A4A2500C853DA41B17407AAF229C90E8DA7F3F8A5D196895FB`
- 迁移当时写下的 `data-upgrade\_migration\20260916-195438\SOURCE.sha256` = `8948C043C15874A4A2500C853DA41B17407AAF229C90E8DA7F3F8A5D196895FB`
- **逐字符相同** ⇒ 从迁移到验收结束（含真机窗口全程）`data\` **一个字节没动** ✅（21 个文件，逐行哈希见 §6.4）

### 6.2 `index.json` 快照（验收结束时原样）

```json
{
  "workspaces": {
    "oc_33225a17a5b9fdde00a70f92d002a033": {
      "name": "课程任务书-02a033",
      "created_at": "2026-09-16T19:54:38",
      "migrated_from": "data"
    },
    "oc_2d805f19bf755763edd6c63b835f01df": {
      "name": "群5f01df",
      "created_at": "2026-09-16T19:58:48"
    },
    "oc_3e969aae31860e36f1c8652e3f666578": {
      "name": "群666578",
      "created_at": "2026-09-16T19:59:47"
    }
  },
  "user_last_group": {
    "ou_0040fcec9ebf80235a33c3afeed30e84": "oc_33225a17a5b9fdde00a70f92d002a033",
    "ou_4537b96e5257168f1d9d13c6ad0227ea": "oc_33225a17a5b9fdde00a70f92d002a033",
    "ou_01507b0ba78fef38ae31e86aef16637d": "oc_33225a17a5b9fdde00a70f92d002a033",
    "ou_b8f6fdba44c4bdaa6cb1775c55f5f06f": "oc_3e969aae31860e36f1c8652e3f666578",
    "ou_a79861323d0c6f45676d3f62b68284e3": "oc_3e969aae31860e36f1c8652e3f666578"
  }
}
```

（`oc_33225a17…` = 迁移种下的 MVP 工作空间；`ou_0040fc…/ou_4537b9…/ou_01507b…` = 迁移种下的 MVP 侧 open_id，与升级版账号不是一套。升级版账号里只有**真在群里发过言**的两个人进了表：神 → 群B、雨鑫左 → 群B。）

### 6.3 迁移 MANIFEST（引用）

`data-upgrade\_migration\MANIFEST-migrate-20260916-195438-2.json`：`verify.ok=true` / `source_unchanged=true` / `reads_equal=true` / `payload_hash_equal=true` / `uploads_hash_equal=true` / 覆盖率 `eligible 4/4、covered 4/4、missing=[]`（源与工作空间两侧一致）/ `idempotent=true` / `workspace_changes=0` / `pending_file.migrated=false`（v1.7 守卫：`chat_id` 与群不一致不搬）。

### 6.4 `data\` 21 行逐文件哈希（验收结束时重算）

```
assignment.json 4B9B762422F3A1DB5B5262028752E0F5C0BE5E5791953080D73252D0C8B79F84
cards.json C7ED938C10E9C97AA18C862315B122E0AD5AC9107F56EFDBD8C5BE0A7E6C494D
direction.json 86B916262C6C69F06B75C5B2FE0B495BC750E457762482AD363E2337EE6A2D70
gantt.png 80A193DAB594356BFC45A5F71FB9AE4FD9EF4514C6BE3E4899AC0D119AC88CD1
members.json B5832811725E91CC9F3143468459D13415A7627B55B83DB1D50F2662CAA70137
preferences.json A7A23063C6028970E9E7622BCDE113F4F03E3227DABAB49B6EE26CFD513C2FF5
probe/02_过年不放炮的软工导论课程报告.pdf 3DC0D8D780D29977665B71F7DAB9780099F0DEE0D74E7DC6CA13AA362DF25366
probe/05_过年不放炮的软工导论课程报告.pdf 3DC0D8D780D29977665B71F7DAB9780099F0DEE0D74E7DC6CA13AA362DF25366
probe/06_过年不放炮的软工导论课程报告.pdf 3DC0D8D780D29977665B71F7DAB9780099F0DEE0D74E7DC6CA13AA362DF25366
probe/13_学业生涯规划书.pdf 5B67145186F4C1FA46F5F32FA061630DEB4A42690D887042588BC85D07AD53D2
probe/_peek_assign.txt 72CBDD49DDD829FB61EFA24844B14CB6A8FB8B85B095189B8E8E845E2A7A068A
probe/_peek_assign_readable.txt C339C7BB566A8D8C353A7F74A120F0C990AD0EB1FE0F1AE6BE826E81C210A96B
report.md A812A8903FFAFFEBED2940E45C8326EA569534B0181B909C0863843BBBB8FBB8
rubric.json 75742D5BB2AB7DAB49A459589EB212C59C7B1187D8AAF2AABD83E673D76120AB
seen.json 1782BC9CB2408EA6F99E8859B8CC4C6B9F76A029886DD1802BF5F64D76956CD2
state.json 574204A1CCA521FADB1C8A6FF298CD2F88031E95548E65B8D0C2847FA06446B9
state.json.bak 58C452709C9786C8C8F7A097F9A9159A6A7977B458007F5F4B4A330DBF93396F
uploads/854ccfa5-08fb-440e-81bf-92289bfb3151_________________.docx 754E781AADDD5C7747328B6A6CAB2C94679FE820DFAC320EE2FF29B3DD6F80FB
uploads/BIM 技术原理及其应用课程设.pdf ECC8E29CA203C9E71806D30DB637A1AE5B892991BC97CCB1B498A9B17A6C030D
uploads/软件系统设计与开发实践》课程任 1.pdf 9F5344572F26E1BE521D6BE928C2BA1F045F35A7724CF644303D62ECA45807A8
uploads/过年不放炮的软工导论课程报告.pdf 3DC0D8D780D29977665B71F7DAB9780099F0DEE0D74E7DC6CA13AA362DF25366
```

> **`state.json` 的两个哈希别读错**：本节这行 = `data\state.json` **原始字节**（660 B / `574204A1…`）；
> `MANIFEST-migrate-20260916-195438-2.json` 里那条 `payload[state.json].sha256` = **搬进工作空间后的负载哈希**
> （297 B / `8D850D76…`）—— 差的 363 B 正是被 v1.7 守卫摘掉的 `pending_file` 块（`pending_file.migrated=false` 与它同源）。
> 两条都对，不是「源盘被动过」。

### 6.5 进程

`Stop-Process -Id 74596 -Force`（20:19 前后）⇒ `Get-Process python` 空、端口 47654 空。日志文件保留在 `D:\rehearsal-logs\`（带时间戳，未覆盖旧文件）。

## 7. 未覆盖 / 遗留（下一轮别漏）

1. **§5 的 T05 格没测**（窗关后再发裸数字应静默；本轮没发）⇒ 归 `docs\REHEARSAL-0918.md` 格 B4。
2. **§2 只覆盖了 2 条私聊归属指令**（`你想做哪一块`、`作业书`）—— `报告`/`完成 T3`/`我想提议：` 等**没逐条**跑（`报告` 还只认组长、只认群里）。⇒ 判据本身**已在 `21fd34a`**（PM 2026-09-16 确认：④-c 就落在 `app.py` 的 `handle()` —— 选不到数据域即回 `NEED_GROUP`，本轮 §2 那两条 `none 没有绑定` 就是它）⇒ **不需要再排一遍代码**，剩下的只是**按人补测**（`报告` 只认组长且只认群里，得单独安排）。
3. **非成员裸数字**（run5 验过）本轮没重跑 —— 3 人花名册下门槛 2 票，非成员那条得另开一轮窗、且顺序必须「非成员先发 ⇒ 成员后发」。
4. `data-upgrade\` **顶层扁平残留**（含 `_rehearsal\`）现在是**死数据**：运行时一个字不读，但工具**没有**「把升级版自己的扁平数据就地收编进工作空间」的路径（`migrate_workspace.py` 只支持 `data\` → dest）。**PM 2026-09-16 裁决：不另加「就地收编」命令**（要动 `migrate_workspace.py` 的语义 + 补回归，不值），口径改为一句话写进文档 —— **进程根运行时只读 `index.json` / `workspaces\`，顶层是迁移前快照**。本轮按纪律**一个字节没动**；清理按 `docs\OPERATIONS-U2.md` §7 需另行授权。

## 8. 本轮捞出来的新问题（给架构师 / 补丁批）

1. **文案同族缺陷（真机复现）**：群里「教用户回某个词」的话必须自带 @我，否则被自己的门禁吃掉。已修的是 U1 那 4 处（`replies.py` 的 `command_list` 第 1 条 + `file_missing()/parse_failed()/needs_rubric()`）。**同族还没修**：`VOTE_NEED_ROSTER:208`、`DIRECTION_NOT_MEMBER:210`、`COMPLETE_NEED_ASSIGNMENTS:246`、`REPORT_NEED_ROSTER:268`、`REPORT_NEED_ASSIGNMENTS:270`、`PREFERENCE_NEED_ROSTER:283`、`PREFERENCE_NOT_MEMBER:284`、`PROPOSAL_NOT_MEMBER:303`，以及 `command_list(GROUP)` 第 2–7 行（`group_line` 只有「作业书」一条有）。修法照 `file_missing()` 的 scope 分叉。**处置（PM 2026-09-16）：先不改、先记台账** —— 与 U3/U4 的文案一次收（现在改会牵动 §11 对照表 + 计数快照 + 再复跑一轮）；本条即台账入口。
2. **`NEED_GROUP:297` 不算缺陷，别顺手改**：它教「先在群里发一次指令」，而绑定刷新在门禁**之前**（对齐卡 #3）⇒ 静默发也照样认下这个群。
3. **§1 的隐性前置**：`你想做哪一块` 私聊需要 `cards` + `roster` **两样都有**，缺任一个都拿不到来源标题（`preference.py:87`）。`ACCEPTANCE-U2.md` §1 的步骤里没写「先登记」，下一版清单补一句，省得下一轮又卡在同一个地方。
