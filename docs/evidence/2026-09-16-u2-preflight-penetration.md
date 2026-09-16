# U2 开工前穿透批（run1 + run2）—— 现状基线

**目的**：U2 动 `data-upgrade\` **之前**，把「群聊门禁 / 图片消息 / 投票窗 × 裸数字 / 私聊归属」的**现状**行为钉住。
U2 一落地（root 从扁平 `data-upgrade\` 变成 `workspaces\<群>\`），这些"之前"就再也测不到了 —— 这是本批的**唯一理由**。
**依据**：`docs\evidence\2026-09-16-u2-single-value-mapping-alignment.md` §3（穿透批硬约束 + 三条清单项 + 当前代码期望）。
**环境**：升级版机器人 `机器人007`（凭据见 `.env.upgrade`，不入库）· 测试群 `oc_2d805f19bf755763edd6c63b835f01df` ·
组长的私聊 `oc_e4a2bb0ffbb56d8ddc288917b66d5a5f` · 数据根 `data-upgrade\`（**扁平态**）· 单实例锁端口 47654 ·
`run-upgrade.ps1 -Seconds 1200`（`PYTHONUTF8=1` + `PYTHONUNBUFFERED=1`）。
**跑的人**：真人（PM）在飞书里发消息；开发起进程、读日志。

## 0. 采集纪律（本轮定死）

**日志一律不覆盖。** 每次起进程写**带时间戳的独立文件**（或 `>>` 追加），禁止复用同一个文件名。

run1 的证据能补回来纯属侥幸 —— `%TEMP%\u2_penetration.log` 在第二次起进程**之前**被手动留档成 `u2_penetration_run1.log`，
否则 `11:52` 那两条关键证据（裸数字计票 / 投票中 `@作业书`）会被下一次启动直接截掉。
现在改成规则：启动器写 `u2_penetration_<yyyyMMdd-HHmmss>.log`，且**不删除**任何已有日志。
（同一规则已落进材料侧：`docs\REHEARSAL-0918.md` §0 硬规则 + `docs\ARCHITECTURE-UPGRADE.md` v1.16。）

### 0.1 读日志的两条注意点（都不改原文）

1. **回话文本被日志裁到 40 字**：`src\gateway\app.py:226` 的落点写作 `ok | {message.text[:40]}`，收信侧 `src\gateway\app.py:164`
   同样是 `text={inbound.text[:40]}`。所以日志里那些"断在半句"的位置（如 `11:52:05` 的候选清单、`12:03:25` 的票数）
   是**日志裁的，不是机器人少发了** —— U1 冒烟那次记的"截断伪影"，本轮定到了具体行号。
2. 下面每段都**没有**贴这些行（与 U1 冒烟同一口径）：脚本启动横幅、`[M0] 正在建立长连接…`、Python 依赖 warning、
   `[Lark] connected to wss://…`（带 `access_key` / `ticket`，禁止入库）。

## 1. run1 原样日志（11:45:20 – 11:53:22）

原始文件 `%TEMP%\u2_penetration_run1.log`（49 行 / 5768 字节）。下面 = 该文件**第 10–49 行逐字原文**（行尾 LF，内容一字未改）。

```
[M0] 2026-09-16T11:46:26 recv id=om_x100b65955fec18acb28b1f9ad41cf3f chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 你好
[M0] 2026-09-16T11:46:27 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 直接说要做哪件就行：
1. 把作业书发进群，再 @我 说「作业书」—— 我抽评分
[M0] 2026-09-16T11:46:46 recv id=om_x100b65955c9644b0b4cd26b273e1336 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=image text=
[M0] 2026-09-16T11:47:00 recv id=om_x100b65955df7b8acb3275550cb911a8 chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=image text=
[M0] 2026-09-16T11:47:01 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 图片我读不了，作业书发 PDF 或 Word 文件给我。
[M0] 2026-09-16T11:47:22 recv id=om_x100b65955a5190b0b2af5306abef32a chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 方向
[M0] 2026-09-16T11:47:22 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 还没有花名册。先在群里回「登记」建一份，再回「方向」。
[M0] 2026-09-16T11:47:33 recv id=om_x100b65955b83890cb186c7ab14292e4 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 登记
[M0] 2026-09-16T11:47:34 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 照这个样子填，把人 @ 上：
登记
组长：@某人
组员：@某人 @某人 @某人
[M0] 2026-09-16T11:48:06 recv id=om_x100b65955991bca8b12c2e14913c482 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=登记
组长：@_user_1 
组员：@_user_2 @_user_3
[M0] 2026-09-16T11:48:07 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 我读到的是这样：
组长：神
组员：戚相宜、雨鑫 左（含组长共 3 人）
回「同意
[M0] 2026-09-16T11:48:21 recv id=om_x100b6595569798b0b101804c23ff2be chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=同意
[M0] 2026-09-16T11:48:22 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 花名册存好了，组长是 神，含组长一共 3 人。
[M0] 2026-09-16T11:48:24 recv id=om_x100b6595564624a0b26cccdada2b21e chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=1
[M0] 2026-09-16T11:48:53 recv id=om_x100b6595548178b0b1f3db624bbcb55 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 作业书
[M0] 2026-09-16T11:48:54 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 我手上还没有作业书文件。把作业书发进这个群，再 @我一次。
[M0] 2026-09-16T11:49:09 recv id=om_x100b6595559890a0b1c83e7bb8008ac chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=file text=
[M0] 2026-09-16T11:52:01 recv id=om_x100b659568dc48b8b0316ba8ae96c32 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 方向
[M0] 2026-09-16T11:52:02 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，按评分点想几个候选方向，大概半分钟。
[M0] 2026-09-16T11:52:05 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 候选方向（仅供参考，由全组拍板）：
1. 校园咖啡店营销计划方案
   覆盖目标
[M0] 2026-09-16T11:52:13 recv id=om_x100b6595681acc6cb344f22dfc00b52 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=1
[M0] 2026-09-16T11:52:14 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 记下了，你投的是 1. 校园咖啡店营销计划方案。想改再回一次数字。
[M0] 2026-09-16T11:52:22 recv id=om_x100b65956993a4a0b2e3b07f9b87492 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 作业书
[M0] 2026-09-16T11:52:22 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，开始解析作业书，大概半分钟。
Consider using the pymupdf_layout package for a greatly improved page layout analysis.
[M0] 2026-09-16T11:52:31 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 《营销方案计划》 电子商务技能检测｜交付：现场操作方式，小组在规定时间内合作完成
[M0] 2026-09-16T11:53:21 recv id=om_x100b659565c760b0b1d097d5bc0987c chat=oc_fb5094e9cac398f66035b630c7099beb from=ou_c5aa3b1889a851d3276493f88862742c type=text text=你好
[M0] 2026-09-16T11:53:22 -> chat_id:oc_fb5094e9cac398f66035b630c7099beb ok | 直接说要做哪件就行：
1. 发作业书文件给我，再回「作业书」—— 我抽评分点、拆
```

## 2. run2 原样日志（11:54:38 – 12:05:18，快照）

原始文件 `%TEMP%\u2_penetration_run2.log`（28 行；生成本文时从仍在跑的 `u2_penetration.log` 快照）。
下面 = 第 10–28 行逐字原文。

```
[M0] 2026-09-16T11:58:00 recv id=om_x100b659572b0a0b8b4bfeb55d03fbaf chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 方向
[M0] 2026-09-16T11:58:01 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 投票还在走，还剩 5 分钟。直接回数字就行。
[M0] 2026-09-16T12:03:24 recv id=om_x100b65951e08d0a8b3d6d6061efe205 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 方向
[M0] 2026-09-16T12:03:25 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 10 分钟到了，还没有方向过半：1 号 1 票 / 2 号 0 票 / 3 号 
[M0] 2026-09-16T12:03:26 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，按评分点想几个候选方向，大概半分钟。
[M0] 2026-09-16T12:03:30 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 候选方向（仅供参考，由全组拍板）：
1. 为校园周边奶茶店制定营销计划方案
  
[M0] 2026-09-16T12:03:36 recv id=om_x100b65951f4984b0b17da5abd112fde chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=1
[M0] 2026-09-16T12:03:37 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 记下了，你投的是 1. 为校园周边奶茶店制定营销计划方案。想改再回一次数字。
[M0] 2026-09-16T12:03:55 recv id=om_x100b65951c7f80a8b2451d79650a3e7 chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=我想提议校园咖啡测试
[M0] 2026-09-16T12:03:56 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 直接说要做哪件就行：
1. 发作业书文件给我，再回「作业书」—— 我抽评分点、拆
[M0] 2026-09-16T12:04:09 recv id=om_x100b65951d5fb0a0b1760696bfc61bf chat=oc_e4a2bb0ffbb56d8ddc288917b66d5a5f from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=我想提议：校园开发测试
[M0] 2026-09-16T12:04:10 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 有组员提议：校园开发测试
[M0] 2026-09-16T12:04:11 -> chat_id:oc_e4a2bb0ffbb56d8ddc288917b66d5a5f ok | 已经匿名发到群里了。
[M0] 2026-09-16T12:04:35 recv id=om_x100b65951bfac4a0b29e2966e5ba28a chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 封盘1
[M0] 2026-09-16T12:04:36 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 方向定了：1. 为校园周边奶茶店制定营销计划方案，组长拍板。
[M0] 2026-09-16T12:04:40 recv id=om_x100b65951bb174acb1141c29a11c9b1 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=3
```

## 3. 逐条判定

| # | 动作 | 期望 | 实际（日志 / 落盘） | 判定 |
|---|---|---|---|---|
| — | 暖场：群里 `@机器人007 你好` | 有回应 | run1 `11:46:26 recv` → `11:46:27 -> … ok \| 直接说要做哪件就行：` | ✅ |
| ① | 群里**不 @** 发图片 | 静默 | run1 `11:46:46 recv … type=image`，**无** `->` 行 | ✅ |
| ① | 私聊发图片 | 拒收回执 | run1 `11:47:00 recv … type=image` → `11:47:01 -> … ok \| 图片我读不了，作业书发 PDF 或 Word 文件给我。` | ✅ |
| ① | 图片**不进缓存** | `state.json` 无 `pending_file`、`uploads\` 无图片 | 见 §5.1：只有一份 PDF，`state.json` 里没有 `pending_file` 这个键 | ✅ |
| ② | 窗内、成员、**裸数字** | 计票 | run1 `11:52:13 recv … text=1`（无 @）→ `11:52:14 -> … ok \| 记下了，你投的是 1. 校园咖啡店营销计划方案。` | ✅ |
| ② | 窗**没到期**时再 `@方向` | `VOTE_IN_PROGRESS` | run2 `11:58:00 recv … @_user_1 方向` → `11:58:01 -> … ok \| 投票还在走，还剩 5 分钟。直接回数字就行。` | ✅ |
| ② | 窗**到期后**再 `@方向` | 先收口、再开新窗 | run2 `12:03:24` → `12:03:25 -> … ok \| 10 分钟到了，还没有方向过半：1 号 1 票 / 2 号 0 票 / 3 号 `（裁）→ `12:03:26` 收到解析 → `12:03:30` 新候选 | ✅ |
| ② | **新窗**内裸数字 | 计票 | run2 `12:03:36 recv … text=1` → `12:03:37 -> … ok \| 记下了，你投的是 1. 为校园周边奶茶店制定营销计划方案。` | ✅ |
| ③ | 投票**进行中** `@作业书` | 窗不被吞、照常出评分点 | run1 `11:52:22 recv … @_user_1 作业书` → `11:52:22` 收到解析 → `11:52:31` 出评分点；此后 `awaiting` 仍是 `vote`、候选与票数原样在（§5.3） | ✅ |
| ④ | 组长 `@… 封盘1` 后，群里裸数字 | 静默（门禁立刻恢复，T05） | run2 `12:04:35` 封盘 → `12:04:36` 方向定；`12:04:40 recv … text=3`，**无** `->` 行；`state.json` 的 `awaiting` / `vote` 一起清（§5.4） | ✅ |
| ④ | **非成员**账号群内裸数字 | 静默 | **未测**（需要第二个不在花名册里的账号） | ⏳ |
| ⑤ | 成员私聊 `我想提议：…` | （卡里写的是）`NEED_GROUP` | run2 `12:04:09 recv`（私聊）→ `12:04:10 -> chat_id:oc_2d805f19… ok \| 有组员提议：校园开发测试` + `12:04:11` 私聊回执"已经匿名发到群里了。" ⇒ **转发进群**，不是 `NEED_GROUP` | ❌ 现状不可复现（见 §4） |
| ⑤ | 私聊 `我想提议校园咖啡测试`（**没带冒号**） | — | run2 `12:03:55` → `12:03:56` 走帮助兜底 ⇒ 前缀**必须带冒号** | ℹ️ 附带钉住 |

## 4. ⑤「未入群用户私聊 → NEED_GROUP」：现状不可复现（机制）

全仓只有**一个**产点：`src/gateway/router.py:404-407`，判据是**全局** `state["group_chat_id"]` 为空 ——

```
404:     group = (state or {}).get("group_chat_id") or ""
405:     if not group:
406:         # 发不到群就别假装发了：不转达、也不落盘（留痕是给"已发布的内容"追责用的）
407:         return Outcome(replies=(reply(inbound, replies.NEED_GROUP),))
```

它挂在 `我想提议：` 这条路径上（`PROPOSAL_PREFIXES = ("我想提议：", "我想提议:")`，`router.py:46`），
而**非花名册成员会先在 `router.py:393` 被 `PROPOSAL_NOT_MEMBER` 挡掉**。

本轮的落盘 `group_chat_id` **全程非空**（任何一次群消息都会写入它）⇒ 私聊提议**必然**走"转发进群"，`NEED_GROUP` 拿不到。
run2 `12:04:09` 实测印证：私聊提议被转发进群，私聊侧只回执"已经匿名发到群里了"，全程没有 `NEED_GROUP`。

**判定**：这条**不是"现状回归"**，是 U2 之后才成立的**按人**行为（§7.2 的"该用户从没在群里互动过"）。
对齐卡 §4 证据槽第 2 条据此改成「U2 后按人验」。

## 5. 落盘佐证

### 5.1 图片没进缓存（① 的第 3 项）

`data-upgrade\uploads\` 清单（原样）：

```
营销方案计划》任务书.pdf
```

只有一份 PDF —— 那是 run1 `@作业书` 之后落下来的（`11:52:24`）；**没有任何图片文件**。
`state.json` 里**没有** `pending_file` 这个键（§5.4）。两条图片消息（群 `11:46:46` / 私聊 `11:47:00`）一个字节都没落。

### 5.2 members.json（run1 `11:48:21` 登记、`11:48:22` 落盘）

```json
{
  "leader": "ou_b8f6fdba44c4bdaa6cb1775c55f5f06f",
  "members": [
    {
      "open_id": "ou_b8f6fdba44c4bdaa6cb1775c55f5f06f",
      "name": "神"
    },
    {
      "open_id": "ou_c5aa3b1889a851d3276493f88862742c",
      "name": "戚相宜"
    },
    {
      "open_id": "ou_a79861323d0c6f45676d3f62b68284e3",
      "name": "雨鑫 左"
    }
  ],
  "registered_at": "2026-09-16T11:48:21",
  "confirmed_by": "ou_b8f6fdba44c4bdaa6cb1775c55f5f06f"
}
```

### 5.3 state.json · **封盘前**（run1 `11:55:20` 读取）

原文已在 `12:04:36` 被封盘覆盖 ⇒ 此处记**关键字段**（不再是"原样"）：
`awaiting = "vote"` · `vote.chat_id = oc_2d805f19bf755763edd6c63b835f01df` ·
`vote.opened_at = "2026-09-16T11:52:04"` · `vote.opened_by = ou_b8f6fdba44c4bdaa6cb1775c55f5f06f` ·
`votes = {"ou_b8f6fdba44c4bdaa6cb1775c55f5f06f": 1}` · 候选 3 条。

**这一条本身就是采集纪律的注脚**：`state.json` 是单份可覆盖产物，唯一的"封盘前现场"没留档。

### 5.4 state.json · **封盘后**（`12:05:18` 读取，全量原样）

```json
{
  "group_chat_id": "oc_2d805f19bf755763edd6c63b835f01df",
  "awaiting": null,
  "preference": null,
  "vote": null,
  "register": null
}
```

### 5.5 proposals.json（`12:04:11` 落盘 —— 私聊提议被记成了群里的提案）

```json
[
  {
    "user_id": "ou_b8f6fdba44c4bdaa6cb1775c55f5f06f",
    "text": "校园开发测试",
    "created_at": "2026-09-16T12:04:09"
  }
]
```

### 5.6 direction.json（`12:04:36` 落盘 —— 封盘定方向）

```json
{
  "decided_at": "2026-09-16T12:04:35",
  "source": "leader",
  "decided_by": "leader",
  "winner": {
    "id": 1,
    "title": "为校园周边奶茶店制定营销计划方案",
    "note": "覆盖目标、市场现状、竞争与内外部环境分析，贴合报告类作业要求"
  },
  "candidates": [
    {
      "id": 1,
      "title": "为校园周边奶茶店制定营销计划方案",
      "note": "覆盖目标、市场现状、竞争与内外部环境分析，贴合报告类作业要求",
      "rubric_refs": [
        "R2",
        "R3",
        "R4",
        "R5",
        "R6"
      ]
    },
    {
      "id": 2,
      "title": "为国产运动品牌设计新品上市营销方案",
      "note": "聚焦营销目标、目标市场与定位，完整呈现营销组合与渠道职能",
      "rubric_refs": [
        "R7",
        "R8",
        "R9",
        "R10"
      ]
    },
    {
      "id": 3,
      "title": "为社区生鲜电商平台撰写营销计划书",
      "note": "按规范格式整理目录与命名上传，兼顾写作水平与文件提交要求",
      "rubric_refs": [
        "R1",
        "R11",
        "R12"
      ]
    }
  ],
  "votes": {
    "ou_b8f6fdba44c4bdaa6cb1775c55f5f06f": 1
  },
  "tally": {
    "1": 1,
    "2": 0,
    "3": 0
  },
  "reason": "组长拍板"
}
```

## 6. 结论 / 对对齐卡的影响

- 清单项 **① 图片**：三项全过（群静默 / 私聊回执 / 不进缓存）。
- 清单项 **② 投票窗 × 群内裸数字**：主路径（计票）+ 未到期提示 + 到期收口后重开，全部过。
- 清单项 **③ 投票中 `@作业书`**：过 —— 而且是**在开着的窗里**测的，窗没被吞。
- **④** 主路径（封盘后门禁立刻恢复）过；"非成员裸数字"未测。
- **⑤** 现状不可复现（§4）⇒ 对齐卡 §4 证据槽第 2 条改成「U2 后按人验」；第 1 / 3 条（双群、并发）仍要两个群 + U2 落地，本轮未动。
- **给 U2 的硬要求（本批新发现）**：`NEED_GROUP` 现在**只有"提议"一条路径**会给（`router.py` 的 `我想提议：` 分支，判据是全局列）。而 `docs\ACCEPTANCE-U2.md` §2 要求丙私聊 `你想做哪一块` / `作业书` 也回 `NEED_GROUP` ⇒ U2 必须把判据从「全局列空」换成「**该人无绑定**」，并覆盖**所有**依赖归属的私聊指令，而不只是提议 —— 否则验收清单第 2 条根本走不到那个分支。
- 附带钉住：`我想提议：` 前缀**必须带冒号**；`app.py:164/226` 的 `[:40]` 让日志无法承载"原样回话"，要长证据得另存或入库（本轮靠消息 id + 落盘文件绕开）。

