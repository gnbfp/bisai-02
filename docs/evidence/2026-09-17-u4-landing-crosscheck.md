# U4 / U3 落地交叉核对（2026-09-17，架构师）

依据：PM 2026-09-17 指令（追认两条口径 + 回写 §5.1 / §8.6 / §9.1 第 13–17 条 / §13 + 登记 U3 的 LLM 调用点 3→4）。
本文件只记**可复核的事实**：命令、输出、代码位置、单测名。**没有真机留痕的项一律标「未验证」。**

**核对时点 = HEAD `1fc4e71`**（工作区只剩本文件的改动）。U4 六笔终于 `2ce6997`；U3 两笔 = `6582827`（地基）+ `1fc4e71`（接入）。
本轮踩到的坑：写材料期间开发连推两笔，U3 从「在途」变「已落地」—— **凡引用代码状态，必须现读 HEAD，不能拿写稿时的印象**。

## 1. 条数：路由 12 / 群 8 / 私聊 7（终值达成）

复跑命令（源码根目录）：

```powershell
python tools\count_replies.py
```

2026-09-17 实测（HEAD `1fc4e71`）：

```
[count_replies] src/gateway/replies.py
  all   = 108   (= len(__all__))
  text  = 99   (字符串字面量 95 + 非字面量模板 4)
  sym   = 9    [Command, claim_taken, claim_unknown, command_list, file_missing, needs_rubric, parse_failed, reassign_unknown, vote_no_rubric]
  lines = 440
```

作用域派生实测：`len(replies.COMMANDS)` = **12**；`usable_in(GROUP)` = **8**；`usable_in(DM)` = **7**。
⇒ 与 §5.1 / §5.4 / §12.3 第 15 条写的终值一致（**终值不受 U3 影响**，U3 只加文案、不加指令）。

**漂移史**：U4 落地时（`2ce6997`）= 106 / 98 / 8 / 427；U3 接入后被推到 108 / 99 / 9 / 440（新增 `vote_no_rubric`）。
**注（不是口径）**：`src/gateway/replies.py` 头部 docstring 仍写着「当前派生结果 = 群 7 / 私聊 5」——
那是 U4 之前的值，属**过期注释**，不要当条数依据。

## 2. 追认口径 ①：退出 / 认领后 `AssignmentRecord.source` 不动，真相记台账 `kind`

- 代码：`src/gateway/change.py` 的 `release()` / `claim()` 的 `save_change.update` **只带 `task_id` 与 `assignee`**，**不带 `source` 键**；两处注释写明「`source` 一个字不动 … 真相在台账里」。
- **有意例外**：`reassign()` 把 `source` 翻成 `leader`（`src/models.py` 的 `ASSIGNMENT_SOURCE` 第四个取值，D-20）—— 「组长指派的」本身就是一种来源，不是漏改。
- 存储层：`src/storage.py` 的 `mutate_change(change, task_id, assignee, source=None, *, expect_empty=False)` —— `source` **默认 `None` ⇒ 不传即不动盘上的 `source`**。
- 单测（退出侧，直接断言 `source` 保留）：`tests\test_storage.py::test_release_sends_the_card_back_to_the_pool_and_keeps_the_source`：先存 `source=volunteer_1` 的卡，回流后断言 **`assignee` 为空串、`source` 仍是 `volunteer_1`**，且台账那条 `kind == release`。
- 单测（真相在 `kind`）：`test_mutate_change_round_trips_the_ledger`（断言台账元组 = `(reassign, ou_li, ou_wang, ou_zhang)`，且盘上 `source` 变 `leader`）；`test_mutate_change_refuses_a_card_someone_else_took`（认领竞态：台账与状态**一个字节都不写**）。
- **未验证**：认领侧**没有独立的「keeps the source」单测**（只有退出侧那一条）；`claim()` 不带 `source` 目前是**代码事实**，不是断言事实。真机 `changes.json` 样例归 9/18。

## 3. 追认口径 ②：公示人名查不到就回 `open_id`，不编

- 代码：`src/gateway/change.py` 的 `name_of(roster, open_id)` —— 查得到回 `member.name`，**查不到原样回 `open_id`**；docstring 原文「宁可不润色，也不编一个人名」。
- 落点四处：`RELEASE_ANNOUNCED` / `CLAIM_ANNOUNCED` / `REASSIGN_DONE`（三条指令的群公示）+ `claim_taken()`（§9.1 第 16 条那句里的人名）。
- **未验证**：真机上「成员」与「非成员」各一条人名样例（归 9/18）。

## 4. U4 落地清单（六笔）+ U3 两笔

| 提交 | 内容 |
|---|---|
| `090e78a` | `ChangeRecord` + 校验 + `mutate_change()` 锁内两写（台账先于状态） |
| `3bb5bb3` | 结算改条件写（只填空负责人 / 只新增卡）+ `allocate()` 固定已分配 |
| `e9608bf` | `改派 T3 @某人`（群 + 组长） |
| `ed75d2a` | `我不做了 T3`（私聊退出回流） |
| `f38b7b8` | `我想接 T3`（私聊补位认领） |
| `2ce6997` | 回流池在总表 / 清单 / 甘特图里渲染成「待认领」 |
| `6582827` | U3 数据地基：`TaskCard.source_refs` + `src\intelligence\workload.py` + `tests\test_workload.py` |
| `1fc4e71` | U3 接入：§6.1 分岔 / `_run_workload()` / `render_workload_checklist()` / `vote_no_rubric()` |

复跑：

```powershell
python -m pytest -q --basetemp=<可写目录>
```

- **518 passed** —— U4 六笔落地后（`2ce6997`，U3 尚未入库），本机复跑（U2 时点 456 ⇒ 净增 62）。
- **523 passed** —— HEAD `1fc4e71`（U3 两笔也入库），本机复跑。

`--basetemp` 必须指到可写目录，否则默认 `%TEMP%\pytest-of-<用户>` 在沙箱 / ACL 下 `PermissionError` 一片**假红**。

## 5. U3 的 LLM 调用点 3 → 4：**已打通**

- 3 处旧调用点（都走 `LLMClient.chat_json()`）：`src\intelligence\parse.py`（M1）/ `decompose.py`（M3）/ `direction.py`（M2）。
- 第 4 处：`src\intelligence\workload.py` —— **已入库**（`6582827`）。
- **接入已入库**（`1fc4e71`）：`src\gateway\app.py` 的 `_run_assignment()` 现在写的是
  `normal = [point for point in parsed.points if point.status == normal]` + `if not normal:` ⇒ `self._run_workload(...)`，
  **不再落到「回 `NO_RUBRIC_FOUND` 后 return」那条死路**；报告侧走 `src\report\checklist.py` 的 `render_workload_checklist()`。
- **未验证**：无评分点作业书的真机跑通（真机要真投一份没有评分标准的作业书）；§6.2 红线的真机核对（这条链路不许调 `coverage_loop()`）。
- 结论：§6.6 / §9.1 第 6 条 / §12.3 第 2 条写「**已落地**」是**有据的**（提交 + 单测 + 现读代码）；「**真机跑通**」仍未验。
