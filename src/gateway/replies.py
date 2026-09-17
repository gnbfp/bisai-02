"""M0 所有对用户可见的文案 —— 集中一处，改词只改这里。

依据：M0 网关方案 §2 / §11、`requirements.md` §7.1（T01 指令列表）/ §7.7（登记）/ §7.5、
U5「说人话」（`requirements-upgrade.md` §2 U5 + `docs/ARCHITECTURE-UPGRADE.md` §11）。

U5 的四层（§11.2，可机械检查）：
  ① 事实槽位原样注入 —— 人名 / 任务号 / 时间 / 数字 / 飞书 ``<at user_id="ou_x"></at>`` 语法，
     永不润色成同义表达；
  ② 完整句子、口语词序：不写"字段名：值"（``已标记完成：`` / ``花名册已保存：`` 这类结构一处不留）；
  ③ 群消息 ≤4 行、私聊 ≤6 行，更长的内容进报告 / 图片；
  ④ 短、直、不修辞：不卖萌、不"您 / 请知悉 / 已受理"、不连发感叹号。

**群聊文案自带「@我」**（U1 门禁的连带影响）：凡是教用户"回某个词"的话，群里那版必须
写成"@我 …" —— 门禁在群里没 @ 就静默，否则机器人自己教的动作会被自己的门禁吃掉
（§9.1 第 4/5 条）。目前按此分叉的是 `作业书` 的清单行与 `FILE_MISSING` /
`PARSE_FAILED` / `NEEDS_RUBRIC`（后面三个走 `file_missing()` / `parse_failed()` /
`needs_rubric()` 取，调用方必须传 `inbound.chat_type`）。

指令清单**不写死条数**（D-76）：由 ``COMMANDS`` 表按作用域派生。当前派生结果 = 群 7 / 私聊 5 /
路由 9 条；U4 的 3 条变更指令落地后自动变成 8 / 7 / 12，这里一个字都不用改。
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "COMMAND_LIST_TEXT",
    "COMMAND_LIST_DM",
    "GROUP",
    "DM",
    "Command",
    "COMMANDS",
    "command_list",
    "FILE_RECEIVED",
    "FILE_MISSING",
    "FILE_MISSING_GROUP",
    "file_missing",
    "parse_failed",
    "needs_rubric",
    "IMAGE_REJECTED",
    "PARSING",
    "PARSE_FAILED",
    "PARSE_FAILED_GROUP",
    "EXTRACT_REJECTED",
    "DECOMPOSING",
    "NEEDS_RUBRIC",
    "NEEDS_RUBRIC_GROUP",
    "VOTE_GENERATING",
    "VOTE_NEED_GROUP",
    "VOTE_NEED_ROSTER",
    "VOTE_NO_RUBRIC_HUMAN",
    "VOTE_NO_RUBRIC_HUMAN_DM",
    "vote_no_rubric",
    "DIRECTION_NOT_MEMBER",
    "VOTE_IN_PROGRESS",
    "VOTE_CANDIDATES",
    "VOTE_ACK",
    "VOTE_BAD",
    "VOTE_TIMEOUT",
    "VOTE_SETTLED",
    "VOTE_SEAL_NEED_PICK",
    "VOTE_NEED_LEADER",
    "VOTE_GENERATE_FAILED",
    "VOTE_HUMAN_EMPTY",
    "VOTE_HUMAN_SETTLED",
    "VOTE_HUMAN_MERGED",
    "VOTE_HUMAN_NEED_LEADER",
    "VOTE_HUMAN_NEED_GROUP",
    "COMPLETE_NEED_DM",
    "COMPLETE_NEED_ASSIGNMENTS",
    "COMPLETE_UNKNOWN",
    "COMPLETE_NOT_YOURS",
    "COMPLETE_MINE",
    "COMPLETE_MINE_NONE",
    "COMPLETE_OK",
    "COMPLETE_ALREADY",
    "REMIND_DUE",
    "REMIND_OVERDUE",
    "REPORT_NEED_GROUP",
    "REPORT_NEED_ROSTER",
    "REPORT_NEED_LEADER",
    "REPORT_NEED_ASSIGNMENTS",
    "REPORT_GENERATING",
    "REPORT_FAILED",
    "IMAGE_SEND_FAILED",
    "PREFERENCE_LIST",
    "PREFERENCE_SAVED",
    "PREFERENCE_BAD",
    "PREFERENCE_NEED_CARDS",
    "PREFERENCE_NEED_ROSTER",
    "PREFERENCE_NOT_MEMBER",
    "PREFERENCE_CONFIRM_SEAL",
    "PREFERENCE_DM_FAILED",
    "NEED_GROUP",
    "PROPOSAL_POSTED",
    "PROPOSAL_ACK",
    "PROPOSAL_EMPTY",
    "PROPOSAL_NOT_MEMBER",
    "REASSIGN_NEED_GROUP",
    "REASSIGN_NEED_ROSTER",
    "REASSIGN_NEED_LEADER",
    "REASSIGN_FORM",
    "REASSIGN_UNKNOWN",
    "REASSIGN_NO_ASSIGNMENTS",
    "REASSIGN_NOT_MEMBER",
    "REASSIGN_DONE",
    "REASSIGN_DONE_POOL",
    "REASSIGN_NOOP",
    "reassign_unknown",
    "RELEASE_NEED_DM",
    "RELEASE_FORM",
    "RELEASE_NOT_YOURS",
    "RELEASE_OK",
    "RELEASE_ANNOUNCED",
    "CLAIM_NEED_DM",
    "CLAIM_FORM",
    "CLAIM_NOT_MEMBER",
    "CLAIM_UNKNOWN",
    "CLAIM_NO_POOL",
    "CLAIM_TAKEN",
    "CLAIM_ALREADY",
    "CLAIM_OK",
    "CLAIM_ANNOUNCED",
    "claim_unknown",
    "claim_taken",
    "REGISTER_FORM",
    "REGISTER_FORM_BAD",
    "REGISTER_NEED_LEADER",
    "REGISTER_NEED_MEMBERS",
    "REGISTER_CONFIRM",
    "REGISTER_SAVED",
    "REGISTER_CANCELLED",
    "REGISTER_EXPIRED",
    "REGISTER_LEADER_ONLY",
    "WELCOME",
]

GROUP = "group"
DM = "p2p"


@dataclass(frozen=True)
class Command:
    """一条顶层前缀 —— 清单文案与"能用在哪"的唯一来源（D-76：条数不写死）。"""

    prefix: str                       # 与 router._by_prefix() 的前缀表逐条对齐（有单测盯着）
    scopes: tuple[str, ...]           # 生效作用域：GROUP / DM
    line: str                         # 清单里那一行（序号由 command_list() 加）

    # 群里那版文案（带「@我」）；``None`` = 与 ``line`` 同一份。
    # 门禁只放行"@ 了机器人"的群文本，所以**群里教用户"回某个词"的话必须自带 @我** ——
    # 否则机器人自己教的动作会被自己的门禁吃掉（§9.1 第 4 条，真机复现）。
    group_line: str | None = None

    def usable_in(self, scope: str) -> bool:
        return scope in self.scopes

    def line_for(self, scope: str) -> str:
        """清单里那一行：群聊给带「@我」的版本，私聊给原版。"""
        if scope == GROUP and self.group_line:
            return self.group_line
        return self.line


COMMANDS = (
    Command(
        "作业书",
        (GROUP, DM),
        "发作业书文件给我，再回「作业书」—— 我抽评分点、拆任务卡",
        group_line="把作业书发进群，再 @我 说「作业书」—— 我抽评分点、拆任务卡",
    ),
    Command("拆解", (GROUP, DM), "回「拆解」，我拿现有评分点重拆一遍"),
    Command("方向", (GROUP,), "群里回「方向」，我出 2–3 个候选方向并开投票"),
    Command("你想做哪一块", (GROUP, DM), "回「你想做哪一块」，我发任务卡清单给你填志愿"),
    Command("我想提议：", (DM,), "私聊发「我想提议：…」，我匿名替你转达"),
    Command("完成 T3", (DM,), "私聊发「完成 T3」，我把这张卡标成做完"),
    Command("登记", (GROUP,), "群里回「登记」，照我回的表单 @ 人建花名册"),
    Command("报告", (GROUP,), "组长在群里回「报告」，我发执行报告和甘特图"),
    Command("我们要做的方向是：", (GROUP,), "群里发「我们要做的方向是：…」，直接定方向，不用投票"),
    Command("改派 T3 @某人", (GROUP,), "组长在群里发「改派 T3 @某人」，换人做这张卡"),
    Command("我不做了 T3", (DM,), "私聊发「我不做了 T3」，把这张卡退回待认领"),
    Command("我想接 T3", (DM,), "私聊发「我想接 T3」，认领一张待认领的卡"),
)


def command_list(scope: str) -> str:
    """按作用域派生清单 —— 条数**不写死**，从 COMMANDS 数出来（D-76）。"""
    lines = [
        f"{index}. {command.line_for(scope)}"
        for index, command in enumerate(
            (item for item in COMMANDS if item.usable_in(scope)), start=1
        )
    ]
    return "直接说要做哪件就行：\n" + "\n".join(lines)


# 群里 @ 后的"群内可用"清单（T01 的 8 条口径）与私聊兜底清单 —— 两份都是派生的。
COMMAND_LIST_TEXT = command_list(GROUP)
COMMAND_LIST_DM = command_list(DM)

# ---- 入群欢迎语（§9.1 第 20 条 · PM 2026-09-17 收）----

# 欢迎语里点名哪 5 条 —— 只是**挑选**，文案照 COMMANDS 渲染（D-76：不另抄一份）
WELCOME_PICKS = ("作业书", "登记", "方向", "你想做哪一块", "报告")


def _picked_lines() -> list[str]:
    by_prefix = {item.prefix: item for item in COMMANDS}
    return [by_prefix[prefix].line_for(GROUP) for prefix in WELCOME_PICKS]


# 机器人被拉进群时**只发这一次**（`client.py` 的 `register_p2_im_chat_member_bot_added_v1`）：
# 一句欢迎 + 5 条高频指令 + 有事 @我（PM 口径）。那句块级「群里每条都要 @我」是有意的 ——
# 这 5 条里 4 条的 `group_line` 还欠「@我」（§9.1 第 4 条同族的 8 处，等文案批一次收）。
WELCOME = (
    "我是小组作业机器人。有事 @我（群里不 @ 我是不理的，私聊直接说就行）。\n"
    "最常用的 5 条 —— 群里每条都要 @我：\n"
    + "\n".join(f"{index}. {line}" for index, line in enumerate(_picked_lines(), start=1))
)

# ---- 作业书 / 拆解 主链路 ----
FILE_RECEIVED = "《{name}》我拿到了，回「作业书」我就开始解析。"
FILE_MISSING = "我手上还没有作业书文件。先把作业书发进来，再回一次「作业书」。"
# 群里那版必须带「@我」：门禁在群里没 @ 就静默，教一句"再回一次「作业书」"
# 等于教用户去撞门禁（§9.1 第 4 条：补一句"把作业书发进这个群，再 @我一次"）。
FILE_MISSING_GROUP = "我手上还没有作业书文件。把作业书发进这个群，再 @我一次。"


def file_missing(scope: str) -> str:
    """按作用域取"没文件"那句 —— 群里带 @我，私聊保持原样（照 command_list() 的做法）。"""
    return FILE_MISSING_GROUP if scope == GROUP else FILE_MISSING


def parse_failed(scope: str) -> str:
    """"没解析出来"那句：群里的重试动作同样要带 @我（§9.1 第 5 条）。"""
    return PARSE_FAILED_GROUP if scope == GROUP else PARSE_FAILED


def needs_rubric(scope: str) -> str:
    """"还没评分点"那句：群里的重试动作同样要带 @我（§9.1 第 5 条）。"""
    return NEEDS_RUBRIC_GROUP if scope == GROUP else NEEDS_RUBRIC
IMAGE_REJECTED = "图片我读不了，作业书发 PDF 或 Word 文件给我。"
PARSING = "收到，开始解析作业书，大概半分钟。"
PARSE_FAILED = "这份作业书没解析出来。如果是拍照或扫描的，换成文字版再回一次「作业书」。"
# 群里那版带「@我」：门禁在群里没 @ 就静默（§9.1 第 5 条，与 FILE_MISSING 同款）。
PARSE_FAILED_GROUP = "这份作业书没解析出来。如果是拍照或扫描的，换成文字版，再 @我一次「作业书」。"
EXTRACT_REJECTED = "这份文件我读不了：{reason}"
DECOMPOSING = "收到，拿现有评分点重拆一遍，马上好。"
NEEDS_RUBRIC = "现在还没有评分点。先把作业书发给我，再回一次「作业书」。"
# 群里那版带「@我」：同上（§9.1 第 5 条）。
NEEDS_RUBRIC_GROUP = "现在还没有评分点。把作业书发进群，再 @我一次「作业书」。"

# ---- M2 方向候选 + 群内投票（§7.1 / §7.6 / D-35 / D-36）----
VOTE_GENERATING = "收到，按评分点想几个候选方向，大概半分钟。"
VOTE_NEED_GROUP = "方向投票是群里的事，把「方向」发到群里。"
VOTE_NEED_ROSTER = "还没有花名册。先在群里回「登记」建一份，再回「方向」。"
# U3（PM 2026-09-17 裁 ①）：**没有可拆评分点 ⇒ 不出候选**，改引导人工拍板 ——
# M2 的候选是拿评分点生成的，没有评分点就只能由人拍（§5.3 第 9 条那条指令）。
# 群里那版带「@我」：它教的是群里发指令，门禁会吃掉不带 @ 的动作（§9.1 第 4 条）。
VOTE_NO_RUBRIC_HUMAN = (
    "现在没有可拆的评分点，我出不了候选。"
    "直接 @我 发「我们要做的方向是：…」，定一个就行。"
)
VOTE_NO_RUBRIC_HUMAN_DM = (
    "现在没有可拆的评分点，我出不了候选。到群里发「我们要做的方向是：…」，定一个就行。"
)


def vote_no_rubric(scope: str) -> str:
    """「方向」在没有可拆评分点时那句 —— 群里带 @我、私聊保持原样（照 `needs_rubric()`）。"""
    return VOTE_NO_RUBRIC_HUMAN if scope == GROUP else VOTE_NO_RUBRIC_HUMAN_DM
# v1.24（§5.1 第 3 条 / §12.4）：开窗能力只给名册成员 —— 判点与 `_proposal()` 同款。
DIRECTION_NOT_MEMBER = "这份花名册里没有你。先在群里回「登记」把自己 @ 进去，再回「方向」开投票。"
VOTE_IN_PROGRESS = "投票还在走，还剩 {minutes} 分钟。直接回数字就行。"
# 候选文案里这句"仅供参考，由全组拍板"是 §7 验收项，别删。
VOTE_CANDIDATES = (
    "候选方向（仅供参考，由全组拍板）：\n"
    "{items}\n"
    "回复数字投票，一人一票，可以改；10 分钟内过半就定。"
)
VOTE_ACK = "记下了，你投的是 {id}. {title}。想改再回一次数字。"
VOTE_BAD = "这个数字我没对上，候选只有 {ids}，回其中一个就行。"
# 超时后窗口只是**冻住**（vote.closed），候选与票数都还在，所以直接让组长拍板就行 ——
# 别再让人重开一轮：重开会重新生成候选，编号跟这张票数表就对不上了。
VOTE_TIMEOUT = (
    "10 分钟到了，还没有方向过半：{tally}。数字不再计票。\n"
    "组长拍板，回「封盘」取票最多的，或者回「封盘 2」直接指定。"
)
VOTE_SETTLED = "方向定了：{id}. {title}，{detail}。"
VOTE_SEAL_NEED_PICK = "现在还没有票。组长回「封盘 2」直接指定一个方向，数字是候选编号。"
VOTE_NEED_LEADER = "只有组长能封盘。"
VOTE_GENERATE_FAILED = "候选方向没生成出来。过一会儿再回一次「方向」，我重试。"

# ---- U6 人工拍板方向（§5.3 / D-74）----
VOTE_HUMAN_EMPTY = (
    "「我们要做的方向是：」后面得写上方向，"
    "比如「我们要做的方向是：做个校园二手书平台」。"
)
VOTE_HUMAN_SETTLED = "方向定了：{title}。要重拆任务卡就回「拆解」，我不会自动重拆。"
VOTE_HUMAN_MERGED = (
    "这句跟候选 {letter} 差不多，我就按候选 {letter} 记了：{title}。"
    "要重拆任务卡就回「拆解」。"
)
VOTE_HUMAN_NEED_LEADER = "方向已经定过了，改方向得组长来发这句。"
VOTE_HUMAN_NEED_GROUP = "方向是群里的事，这句发到群里。"

# ---- M6 完成标记（§7.1 第 6 条 / D-22 / D-31）----
COMPLETE_NEED_DM = "这条私聊发我就行：私聊发「完成 T3」。"
COMPLETE_NEED_ASSIGNMENTS = "现在还没有分配。先在群里回「你想做哪一块」，拿到卡才能标完成。"
# 不是你的卡 / 没这张卡时，都**列出他自己领到的卡** —— 不许给假确认（§6.3 的口径）
COMPLETE_UNKNOWN = "没有 T{index} 这张卡。{mine}"
COMPLETE_NOT_YOURS = "T{index} 不是我分给你的卡，我不能替你标。{mine}"
COMPLETE_MINE = "你现在手上的卡是 {tasks}。"
COMPLETE_MINE_NONE = "你现在手上没有卡。"
COMPLETE_OK = "收到，{task_id}（{module}）算你做完了。"
COMPLETE_ALREADY = "{task_id} 之前就标过了（{at}），时间我没动。"

# ---- M6 临期催办（§2.2；两档 = 待定义-35，逾期档 = D-66）----
# ``{at}`` 是飞书的 @ 语法 ``<at user_id="ou_x"></at>``，写成纯文本 @某人 不会真 @。
REMIND_DUE = (
    "{at} 你的「{module}」还差 {hours} 小时到截止（{deadline}）。"
    "做完私聊我发「完成 {task_id}」。"
)
REMIND_OVERDUE = (
    "{at} 你的「{module}」已经逾期了（截止 {deadline}）。"
    "做完私聊我发「完成 {task_id}」。"
)

# ---- M7 执行报告（D-64）----
REPORT_NEED_GROUP = "报告是群里的事，把「报告」发到群里。"
REPORT_NEED_ROSTER = "还没有花名册。先在群里回「登记」，再回「报告」。"
REPORT_NEED_LEADER = "只有组长能要报告。"
REPORT_NEED_ASSIGNMENTS = "现在还没有分配。先在群里回「你想做哪一块」，分完再回「报告」。"
REPORT_GENERATING = "收到，开始出执行报告（分配总表 / 核对清单 / 甘特图），好了就发群。"
REPORT_FAILED = "报告没出成，渲染的时候出错了。过一会儿再回一次「报告」，我重试。"
IMAGE_SEND_FAILED = "甘特图没发出去，网络出了问题。上面的文字先看，过一会儿回一次「报告」我补一张。"

# ---- M4 志愿分配（§7.1 / D-52~D-54）----
PREFERENCE_LIST = (
    "任务卡清单，回序号就行，想排顺序就按优先级发，比如「2 1」：\n"
    "{items}"
)
PREFERENCE_SAVED = "记下了，你的志愿是 {tasks}。想改再回一次序号。"
PREFERENCE_BAD = "序号我没看懂。我这边看到的是 {tasks}，重发一次就行。"
PREFERENCE_NEED_CARDS = "现在还没有任务卡。先把作业书发给我，回「作业书」拆出卡。"
PREFERENCE_NEED_ROSTER = "还没有花名册。先在群里回「登记」，再回「你想做哪一块」。"
PREFERENCE_NOT_MEMBER = "这份花名册里没有你。先在群里回「登记」把自己 @ 进去，再私聊我填志愿。"
# 组长重发「你想做哪一块」不再直接封盘（P0-B / D-56）：有人交过就先确认一次，
# 免得"为了再发一遍清单"顺手把窗口关了、不可撤回。
PREFERENCE_CONFIRM_SEAL = (
    "现在封盘的话，就按已经交的 {done} 份志愿分配，还有 {missing} 人没交。"
    "回「封盘」确认，回别的就继续等。"
)
# 主动私聊发不出去时，在群里把话说清楚（P0-C），别"群里说已发、实际没人收到"。
PREFERENCE_DM_FAILED = (
    "有 {count} 个人我没私聊到。这几位私聊我发「你想做哪一块」，我把清单单独发给你。"
)

# 主动发群 / 私聊的前置：机器人得先见过至少一条群消息，才知道"群"是哪个（D-54）。
NEED_GROUP = "我还不知道你是哪个群的。先在群里发一次指令，比如「作业书」，我就认下这个群。"

# ---- M5 匿名代言（§6.5 / D-55）----
PROPOSAL_POSTED = "有组员提议：{text}"
PROPOSAL_ACK = "已经匿名发到群里了。"
PROPOSAL_EMPTY = "「我想提议：」后面得写上内容，比如「我想提议：前端用 React」。"
PROPOSAL_NOT_MEMBER = "这份花名册里没有你。先在群里回「登记」把自己 @ 进去，再来找我提议。"

# ---- U4 任务变更：换人（改派）（§8.1 / §9.1 第 13–17 条）----
# 群里那几句教动作的都自带「@我」：门禁只放行 @ 了机器人的群文本（§9.1 第 4 条）。
REASSIGN_NEED_GROUP = "改派是群里的事，把「改派 T3 @某人」发到群里。"
REASSIGN_NEED_ROSTER = "还没有花名册。先在群里 @我 回「登记」，建好名单再改派。"
REASSIGN_NEED_LEADER = "只有组长能改派。"
REASSIGN_FORM = "改派要写清卡号和人，比如：@我 改派 T3 @某人。"
REASSIGN_UNKNOWN = "没有 {task_id} 这张卡。现在能改派的是 {tasks}。"
REASSIGN_NO_ASSIGNMENTS = "现在还没有分配，没得改派。先在群里 @我 回「你想做哪一块」，分完再来。"
REASSIGN_NOT_MEMBER = "这位不在花名册里。先在群里 @我 回「登记」把 TA @ 进去，再改派。"
REASSIGN_DONE = "改派好了：{task_id} 从{frm}交给 {to}，台账我记了。"
REASSIGN_DONE_POOL = "改派好了：{task_id} 从待认领交给 {to}，台账我记了。"
REASSIGN_NOOP = "{task_id} 现在就在{who}名下，没改。"


def reassign_unknown(task_id: str, assignments=()) -> str:
    """"这个编号我没找到" + 列当前卡号（§9.1 第 13 条，照 `PREFERENCE_BAD` 的形态）。"""
    ids = [record.task_id for record in (assignments or ())]
    if not ids:
        return REASSIGN_NO_ASSIGNMENTS
    return REASSIGN_UNKNOWN.format(task_id=task_id, tasks="、".join(ids))


# ---- U4 任务变更：退出回流（§8.1 / §9.1 第 15 条）----
RELEASE_NEED_DM = "「我不做了 T3」私聊我发就行，群里说会吵到别人。"
RELEASE_FORM = "要说退出哪张卡：私聊发「我不做了 T3」就行。"
# 幂等（§9.1 第 15 条）：不是你的 / 已经回流过，都用这一句，不说"操作失败"
RELEASE_NOT_YOURS = "{task_id} 现在不在你名下，我没动。"
RELEASE_OK = "收到，{task_id} 不算你的了，卡回到待认领。"
# 群公示：教的是私聊动作，所以不套「@我」（L5）；上行数仍受 ≤4 行约束
RELEASE_ANNOUNCED = (
    "{name} 退出了 {task_id}（{module}），这张卡回到待认领。"
    "想接的私聊我发「我想接 {task_id}」。"
)


# ---- U4 任务变更：补位认领（§8.1 / §9.1 第 16 条）----
CLAIM_NEED_DM = "「我想接 T3」私聊我发就行，群里说会吵到别人。"
CLAIM_FORM = "要说接哪张卡：私聊发「我想接 T3」就行。"
# 教的是群里的「登记」⇒ 带上「@我」（这门禁只放行 @ 了机器人的群文本，§9.1 第 4 条）
CLAIM_NOT_MEMBER = (
    "这份花名册里没有你。先在群里 @我 回「登记」把自己 @ 进去，"
    "再私聊我说「我想接 T3」。"
)
CLAIM_UNKNOWN = "没有 {task_id} 这张卡。现在能认领的是 {tasks}。"
CLAIM_NO_POOL = "暂时没有别的待认领卡"
# §9.1 第 16 条：人名是事实槽位，原样注入
CLAIM_TAKEN = "{task_id} 刚被{name}接走了。现在能认领的是 {tasks}。"
CLAIM_ALREADY = "{task_id} 现在就在你名下，没改。"
CLAIM_OK = "接到手了：{task_id}（{module}）。"
CLAIM_ANNOUNCED = "{name} 接了 {task_id}（{module}）。"


def claim_unknown(task_id: str, assignments=()) -> str:
    """"这个编号我没找到" + 列**可认领**的卡号（§9.1 第 13 条的形态，口径同第 16 条）。"""
    return CLAIM_UNKNOWN.format(task_id=task_id, tasks=claim_pool(assignments))


def claim_pool(assignments=()) -> str:
    """待认领的卡号清单（§8.3：`assignee == ""` 就是"待认领"）。"""
    ids = [record.task_id for record in (assignments or ()) if not record.assignee]
    return "、".join(ids) if ids else CLAIM_NO_POOL


def claim_taken(task_id: str, name: str, assignments=()) -> str:
    """§9.1 第 16 条那句（含剩余可认领卡）。"""
    return CLAIM_TAKEN.format(task_id=task_id, name=name, tasks=claim_pool(assignments))


# ---- 登记（§7.7）----
# 这一段是**表单模板**：用户要照着它把「登记 / 组长 / 组员」三行发回来，
# 所以格式与词头不动（``register._FORM_LINE`` 认的就是这几个词）。
REGISTER_FORM = (
    "照这个样子填，把人 @ 上：\n"
    "登记\n"
    "组长：@某人\n"
    "组员：@某人 @某人 @某人"
)
REGISTER_FORM_BAD = (
    "表单我没看懂。照下面这个格式重发一遍 —— 要用 @ 选人，别直接打名字：\n\n" + REGISTER_FORM
)
REGISTER_NEED_LEADER = "「组长」那一行要正好 1 个人，改完重发一次。"
REGISTER_NEED_MEMBERS = "「组员」那一行至少 2 个人，改完重发一次。"
# 表单回显也只有 4 行（§11.2 ③：群消息 ≤4 行，回显不是例外）。
REGISTER_CONFIRM = (
    "我读到的是这样：\n"
    "组长：{leader}\n"
    "组员：{members}（含组长共 {total} 人）\n"
    "回「同意」我就存，回别的作废。"
)
REGISTER_SAVED = "花名册存好了，组长是 {leader}，含组长一共 {total} 人。"
REGISTER_CANCELLED = "这次作废了，原来的名单没动。"
REGISTER_EXPIRED = "登记超时作废了，原来的名单没动。要登记就再回一次「登记」。"
REGISTER_LEADER_ONLY = "已经有花名册了，重新登记只有组长能开。"
