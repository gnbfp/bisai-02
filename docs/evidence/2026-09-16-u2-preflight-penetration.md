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

## 2. run2 / run3 原样日志

### 2.1 run2（11:54:38 – 12:05:18，快照）

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

### 2.2 run3（12:09:46 – 12:19:38）

原始文件 `%TEMP%\u2_penetration_run3.log`（35 行）。这个窗口是 run2 那个 20 分钟窗口自动退出后重开的，`state` 与 run2 连着，所以下面能看到 `12:12` 那轮新的开窗与 `过半：1/1 票`。
下面 = 第 10–35 行逐字原文。

```
[M0] 2026-09-16T12:12:47 recv id=om_x100b65953d3568a0b1fafc3cf148ef1 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 方向
[M0] 2026-09-16T12:12:49 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，按评分点想几个候选方向，大概半分钟。
[M0] 2026-09-16T12:12:52 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 候选方向（仅供参考，由全组拍板）：
1. 校园奶茶店营销计划方案
   覆盖目标
[M0] 2026-09-16T12:12:58 recv id=om_x100b65953a6a5ca0b1bd339f81ae2f1 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=2
[M0] 2026-09-16T12:12:59 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 记下了，你投的是 2. 国产美妆品牌校园推广营销方案。想改再回一次数字。
[M0] 2026-09-16T12:13:00 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 方向定了：2. 国产美妆品牌校园推广营销方案，过半：1/1 票。
[M0] 2026-09-16T12:18:55 recv id=om_x100b6595c43584b4c2fa68f4f8f1fc9 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=file text=
[M0] 2026-09-16T12:19:18 recv id=om_x100b6595c29600a0c11984217ab3698 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=image text=
[M0] 2026-09-16T12:19:29 recv id=om_x100b6595c3de30b4c25f5d990a67d82 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 作业书
[M0] 2026-09-16T12:19:30 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，开始解析作业书，大概半分钟。
Consider using the pymupdf_layout package for a greatly improved page layout analysis.
[M0] 2026-09-16T12:19:38 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 《营销方案计划》 电子商务技能检测｜交付：现场操作，小组合作完成一份营销计划方案
[M0] 2026-09-16T12:24:04 recv id=om_x100b6595d088e0a0b49efe5068bf1c8 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 方向
[M0] 2026-09-16T12:24:05 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，按评分点想几个候选方向，大概半分钟。
[M0] 2026-09-16T12:24:09 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 候选方向（仅供参考，由全组拍板）：
1. 校园咖啡店营销计划方案
   覆盖目标
[M0] 2026-09-16T12:25:11 recv id=om_x100b6595eca0e0acc0277c3b8632a98 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_a79861323d0c6f45676d3f62b68284e3 type=text text=@_user_1 方向
[M0] 2026-09-16T12:25:12 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 投票还在走，还剩 9 分钟。直接回数字就行。
[M0] 2026-09-16T12:25:21 recv id=om_x100b6595eddac0a8c4aac7a0af9f23d chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_a79861323d0c6f45676d3f62b68284e3 type=text text=1
[M0] 2026-09-16T12:25:22 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 记下了，你投的是 1. 校园咖啡店营销计划方案。想改再回一次数字。
[M0] 2026-09-16T12:25:34 recv id=om_x100b6595ed13d4acb04db98ed920c86 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=1
[M0] 2026-09-16T12:25:35 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 记下了，你投的是 1. 校园咖啡店营销计划方案。想改再回一次数字。
[M0] 2026-09-16T12:25:35 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 方向定了：1. 校园咖啡店营销计划方案，过半：2/2 票。
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
| ④ | **非成员**账号群内裸数字 | 静默 | **未测** —— 用「临时摘花名册成员」造非成员，摘/还原本身已跑通并留痕（§8），但两次窗口都没等到那条裸数字（顺序纪律见 §6.1） | ⏳ |
| ⑤ | 成员私聊 `我想提议：…` | （卡里写的是）`NEED_GROUP` | run2 `12:04:09 recv`（私聊）→ `12:04:10 -> chat_id:oc_2d805f19… ok \| 有组员提议：校园开发测试` + `12:04:11` 私聊回执"已经匿名发到群里了。" ⇒ **转发进群**，不是 `NEED_GROUP` | ❌ 现状不可复现（见 §4） |
| ⑤ | 私聊 `我想提议校园咖啡测试`（**没带冒号**） | — | run2 `12:03:55` → `12:03:56` 走帮助兜底 ⇒ 前缀**必须带冒号** | ℹ️ 附带钉住 |
| ① | **D-45 ① 子格**：投 PDF → 发图 → `@作业书` | 图不许挤掉刚到的 PDF | run3 `12:18:55 file` 静默 → `12:19:18 image` 静默 → `12:19:29 @作业书` → `12:19:38` 出评分点（评分点来自那份 PDF）；`uploads\` 只有 PDF、无图片（§7） | ✅ |

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

### 6.1 窗口 / 花名册测试的顺序纪律（本批踩出来的两条）

1. **裸数字必须先有窗**：窗口关着时，裸数字静默是「没窗」的必然结果，跟成员资格**无关** —— 拿它当证据就是假阳性。
   本批第一次 ② 就踩了这个坑（`11:48:24` 那个 `1` 是在没窗时发的，静默属正确行为，却证明不了豁免）。
   判据永远是「**窗开着** + `recv` / `-> ` 行」这一对，而不是「群里没看见回话」。
2. **摘花名册成员会同时改分母**：D-36 的过半门槛 = 已投票人数 ≥ `ceil(花名册人数 / 2)`，分母是**当时的花名册人数**。
   2 人花名册下 **1 票即结算**（run3 `12:13:00` 实测 `-> … ok | 方向定了：2. …，过半：1/1 票`），窗会被立刻关掉。
   所以用「临时摘人」验非成员时，顺序必须是 **非成员先发（应静默）→ 成员后发（应计票，随即结算）**；
   反过来窗先被结算掉，非成员那条又变成上面第 1 条那个假阳性。

   摘 / 还原用 `D:\rehearsal-logs\roster_toggle.ps1`（`-Drop ou_…` / `-Restore`）：
   还原点固定 `D:\rehearsal-logs\members_restore_point.json`，还原是**字节级回到原哈希**
   （已在假人盘上验过 round-trip + 拒错保护）；只碰 `data-upgrade\members.json`，`data\` 一个字节不动。

## 7. D-45 ① 子格：PDF → 图 → `@作业书`（run3，12:18–12:19）

**要验的**：一张图**不许**把刚发来的作业书 PDF 挤掉（D-45 ①）。run1 那次图片发在 PDF **之前**，顺序不对，这一格实际没测到；本轮按正确顺序补上。

**原样日志**（同一份 `u2_penetration_run3.log`，见 §2.2）：

```
[M0] 2026-09-16T12:18:55 recv id=om_x100b6595c43584b4c2fa68f4f8f1fc9 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=file text=
[M0] 2026-09-16T12:19:18 recv id=om_x100b6595c29600a0c11984217ab3698 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=image text=
[M0] 2026-09-16T12:19:29 recv id=om_x100b6595c3de30b4c25f5d990a67d82 chat=oc_2d805f19bf755763edd6c63b835f01df from=ou_b8f6fdba44c4bdaa6cb1775c55f5f06f type=text text=@_user_1 作业书
[M0] 2026-09-16T12:19:30 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 收到，开始解析作业书，大概半分钟。
[M0] 2026-09-16T12:19:38 -> chat_id:oc_2d805f19bf755763edd6c63b835f01df ok | 《营销方案计划》 电子商务技能检测｜交付：现场操作，小组合作完成一份营销计划方案
```

- `12:18:55 type=file` 后面**没有** `-> ` 行 ⇒ 群里投文件静默。
- `12:19:18 type=image` 后面**没有** `-> ` 行 ⇒ 群里发图静默。
- `12:19:38` 出的评分点来自**那份 PDF** ⇒ 图没把它挤掉。

**落盘（`uploads\` 原样，12:19:38 之后读）**：只有 PDF、**没有任何图片**。

```
LastWriteTime       Length  Name
2026/9/16 12:19:31  129583  营销方案计划》任务书.pdf
sha256 = 83E749CFA3C6600201758C57ABD277836B1AEDFBE84CD0D6EC9C36680B77F27A
```

**`pending_file` 中间态没有留成原样**：`12:19:30` 那句 `@作业书` 已经把它消费掉，事后的 `state.json` 里没有这个键。
**不为此重跑一轮**，改用代码旁证：

- `router.remember_file()` 存进 `state.pending_file` 的是 `{file_key, file_name, resource_type, chat_id, message_id, received_at}`，**不含路径**；
  下载归 app 层、发生在解析时 —— 这也解释了 `uploads` 那份的 `LastWriteTime` 是 `12:19:31` 而不是收信时刻。
- `router.route()` 的 image 分支在群里直接 `return Outcome()`，**不带 `state`** ⇒ 图片这条路根本不写 `pending_file`，挤不掉。

**判定：D-45 ① 子格 —— 已过（2026-09-16 12:18–12:19）。**

## 8. 花名册摘 / 还原的哈希留痕（④ 非成员半格的前置动作）

没有第三方账号 ⇒ 用「临时摘花名册成员」造一个非成员。两次摘人都**只碰 `data-upgrade\members.json`**，`data\` 一个字节没动。

| 轮次 | 时点 | 动作 | sha256 | 人数 |
|---|---|---|---|---|
| ① | 12:09:34 | 摘前（基线） | `D9A0E915EBC023D83322AB23FF4948D640727D0A66DB11C9EC5095E048D41A40` | 3 |
| ① | 12:09:34 | 摘后 | `BC3262D61B675B1D32209128B512A23ADF68DFCA9601F345D421360A7A746625` | 2 |
| ① | 12:16:24 | 还原后 | `D9A0E915…`（与基线一致） | 3 |
| ② | 12:26:45 | 摘前（基线） | `D9A0E915…` | 3 |
| ② | 12:26:45 | 摘后 | `D88C7ECE94B141344911BF30E7969AC69102D649F1FF486165210E1B2A3A3157` | 2 |
| ② | 12:32:01 | 还原后 | `D9A0E915…`（与基线一致） | 3 |

第 ① 轮是手写脚本改的；第 ② 轮起用 `D:\rehearsal-logs\roster_toggle.ps1`（`-Drop` / `-Restore`）⇒ 两轮"摘后"哈希不同（同一份逻辑内容、不同序列化），
**但两轮都精确还原回同一个基线哈希**。

**还原前后 diff（第 ② 轮）**：

```
--- members.dropped.json
+++ members.restored.json
@@ -9,4 +9,8 @@
       "open_id": "ou_c5aa3b1889a851d3276493f88862742c",
       "name": "戚相宜"
+    },
+    {
+      "open_id": "ou_a79861323d0c6f45676d3f62b68284e3",
+      "name": "雨鑫 左"
     }
   ],
```

（diff 就是"那一行回来"，其余字节不变。）

`roster_toggle.ps1` 的 round-trip 与拒错保护另外在**假人盘**上验过（不拿真盘试）：`-Drop` 3→2、`-Restore` 字节级回原哈希；
`-Drop` 一个不在名册里的 open_id 会抛错、拒绝执行。

## 9. 归属注记

`4ed71cb`（"§8.10 ④ 非成员半格顺序…"）**是审核员的提交**，不是架构师的；笔是他的（`git add -u` 顺手带走了本批开发的两处修订），内容是本批开发的。
按"不重写已推历史"处置，只在此留一行注记（开发此前在汇报里把这笔写成"架构师"，是笔误）。
