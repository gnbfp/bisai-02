"""U4 任务变更（换人 / 退出回流 / 补位认领）—— 纯函数、零 I/O、零 LLM（§8）。

依据：`docs/ARCHITECTURE-UPGRADE.md` §8.1（类型与权限）/ §8.2（台账与写序）/
§8.4（与兜底分配的关系）、§9.1 第 13–17 条（失败路径话术）、§7.1 第 10–12 条。

三条纪律（与 M6 的 ``complete.py`` 同源）：
  * **判定与落盘同源** —— 能不能改、改成什么，都在这一个函数里判死；落盘只发一个
    ``Outcome.save_change`` 纯数据（app 层走 ``JsonStore.mutate_change()``）。
  * **不产生台账的空动作** —— 无变化改派（§9.1 第 17 条）一个字节都不写，但**不静默**
    （组长的动作要有回执）。
  * **人名是事实槽位**（U5）—— 公示里的人名从花名册原样取，不润色、不省略。

PM 2026-09-15 裁 **A 方案**（§8.1）：改派 = 组长直改即生效，被指派人可用
``我不做了 T3`` 退回池子，**不加前置确认窗口** —— 少一个 ``awaiting`` 就少一处
"窗口吃掉指令"的死锁面（``register.py`` 外审必修 1 就是这类病）。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Sequence

from src.gateway import replies
from src.gateway.events import Inbound, Outcome, Reply, reply
from src.models import AssignmentRecord, Roster, TaskCard

__all__ = [
    "REASSIGN_PATTERN",
    "RELEASE_PATTERN",
    "CLAIM_PATTERN",
    "reassign",
    "release",
    "claim",
    "name_of",
]

# 前缀与「完成 T3」同款：容忍空格与大小写，但**整句必须就是这条指令**之后剩卡号
# （@ 段已被 ``strip_mentions`` 剥掉）—— "改派 T3 谢谢" 落提示，不猜。
REASSIGN_PATTERN = re.compile(r"^改派\s*[Tt](\d+)\s*$")
RELEASE_PATTERN = re.compile(r"^我不做了\s*[Tt](\d+)\s*$")
CLAIM_PATTERN = re.compile(r"^我想接\s*[Tt](\d+)\s*$")


def reassign(
    text: str,
    inbound: Inbound,
    roster: Roster | None = None,
    cards: Sequence[TaskCard] = (),
    assignments: Sequence[AssignmentRecord] = (),
    now: datetime | None = None,
    group_chat_id: str = "",
) -> Outcome:
    """``@机器人 改派 T3 @某人`` —— 群 + 组长（§7.1 第 10 条 / §8.1）。

    顺序 = 作用域 / 花名册 / 权限 / 解析 / 卡存在 / 目标在册 / 无变化 / 落盘。
    每一格失败都**只回话、不落盘**，且都不静默（§9.1 第 13–14 条的反面：静默是
    D-61 ② 的"非成员在群里办事"场景，改派不在其中）。
    """
    if inbound.chat_type != "group":
        return Outcome(replies=(reply(inbound, replies.REASSIGN_NEED_GROUP),))
    if roster is None or not getattr(roster, "members", None):
        return Outcome(replies=(reply(inbound, replies.REASSIGN_NEED_ROSTER),))
    if not inbound.sender_open_id or inbound.sender_open_id != roster.leader:
        # 权限沿用既有 `roster.leader`，不新造角色（L1 / D-72）
        return Outcome(replies=(reply(inbound, replies.REASSIGN_NEED_LEADER),))

    match = REASSIGN_PATTERN.match((text or "").strip())
    target = _mentioned_user(inbound)
    if not match or not target:
        return Outcome(replies=(reply(inbound, replies.REASSIGN_FORM),))

    task_id = f"T{match.group(1)}"
    record = next((r for r in (assignments or ()) if r.task_id == task_id), None)
    if record is None:
        # §9.1 第 13 条：列当前卡号，不解释内部原因，**不落盘**
        return Outcome(replies=(reply(inbound, replies.reassign_unknown(task_id, assignments)),))

    if target not in {member.open_id for member in roster.members}:
        # §9.1 第 14 条：沿用非成员口径 + 指路「登记」，**不静默**
        return Outcome(replies=(reply(inbound, replies.REASSIGN_NOT_MEMBER),))

    if record.assignee == target:
        # §9.1 第 17 条：无变化改派 —— 不落盘、不公示（没有变化就不产生台账条目），
        # 但组长的动作要有回执 ⇒ 不静默
        who = "你" if target == inbound.sender_open_id else name_of(roster, target)
        return Outcome(
            replies=(reply(inbound, replies.REASSIGN_NOOP.format(task_id=task_id, who=who)),)
        )

    stamp = (now or datetime.now()).isoformat(timespec="seconds")
    group = group_chat_id or inbound.chat_id
    to_name = name_of(roster, target)
    if record.assignee:
        announced = replies.REASSIGN_DONE.format(
            task_id=task_id, frm=name_of(roster, record.assignee), to=to_name
        )
    else:
        # 回流池里的卡（§8.3：`assignee == ""` 就是"待认领"）：没有前任，公示写成两段
        announced = replies.REASSIGN_DONE_POOL.format(task_id=task_id, to=to_name)

    return Outcome(
        # 群里那句同时是**回执**与**群公示**（§8.1）—— 白名单播报，不受 @ 门禁约束
        replies=(Reply(chat_id=group, text=announced),),
        save_change={
            "change": {
                "at": stamp,
                "by": inbound.sender_open_id,
                "kind": "reassign",
                "task_id": task_id,
                "from_user": record.assignee,
                "to_user": target,
                "reason": "",
                "confirmed_by": [inbound.sender_open_id],
            },
            # 改派的来源翻成 `leader`（requirements.md §6.4 / D-20 的第四个取值）
            "update": {"task_id": task_id, "assignee": target, "source": "leader"},
        },
    )


def release(
    text: str,
    inbound: Inbound,
    roster: Roster | None = None,
    cards: Sequence[TaskCard] = (),
    assignments: Sequence[AssignmentRecord] = (),
    now: datetime | None = None,
    group_chat_id: str = "",
) -> Outcome:
    """``我不做了 T3`` —— 私聊、本人是负责人（§7.1 第 11 条 / §8.1）。

    本人私聊发出即确认退出：``assignee`` 清空 ⇒ 卡进"待认领"（§8.3：回流池不新增文件），
    再写一条台账、往群里播一句公示。被改派的人就是用这一条退回池子（PM 裁的 A 方案）。

    幂等（§9.1 第 15 条）：不是你的 / 已经回流过 ⇒ 回"现在不在你名下"，**不重复回流、
    不重复公示**，也不说"操作失败"。
    """
    if inbound.chat_type != "p2p":
        return Outcome(replies=(reply(inbound, replies.RELEASE_NEED_DM),))

    match = RELEASE_PATTERN.match((text or "").strip())
    if not match:
        return Outcome(replies=(reply(inbound, replies.RELEASE_FORM),))

    task_id = f"T{match.group(1)}"
    record = next((r for r in (assignments or ()) if r.task_id == task_id), None)
    if record is None or record.assignee != inbound.sender_open_id:
        return Outcome(
            replies=(reply(inbound, replies.RELEASE_NOT_YOURS.format(task_id=task_id)),)
        )

    sender = inbound.sender_open_id
    stamp = (now or datetime.now()).isoformat(timespec="seconds")
    out = [reply(inbound, replies.RELEASE_OK.format(task_id=task_id))]
    # 群公示（§8.1 / §8.3）：发到**绑定的那个群**。拿不到群也不拦着人退出 ——
    # 卡照回池子，只是这一句播报没地方发（U2 之前就是这个口径的反面教材）。
    if group_chat_id:
        out.append(
            Reply(
                chat_id=group_chat_id,
                text=replies.RELEASE_ANNOUNCED.format(
                    name=name_of(roster, sender),
                    task_id=task_id,
                    module=_module_name(task_id, cards),
                ),
            )
        )
    return Outcome(
        replies=tuple(out),
        save_change={
            "change": {
                "at": stamp,
                "by": sender,
                "kind": "release",
                "task_id": task_id,
                "from_user": sender,
                "to_user": "",                      # 回流没有接手人（§8.2 表）
                "reason": "",
                "confirmed_by": [sender],
            },
            # `source` 一个字不动：回流改的是"谁做"，不改这张卡为什么存在（§8.2 没定义
            # 回流后的 source 取值 ⇒ 不臆想一个新枚举值；真相在台账里）
            "update": {"task_id": task_id, "assignee": ""},
        },
    )


def claim(
    text: str,
    inbound: Inbound,
    roster: Roster | None = None,
    cards: Sequence[TaskCard] = (),
    assignments: Sequence[AssignmentRecord] = (),
    now: datetime | None = None,
    group_chat_id: str = "",
) -> Outcome:
    """``我想接 T3`` —— 私聊、是花名册成员（§7.1 第 12 条 / §8.1）。

    本人私聊发出即确认接手：待认领的卡（``assignee == ""``）写上自己 + 台账 + 群公示。
    非成员不给办事（§9.1 第 14 条），但**不静默** —— 回同一句人话 + 指路「登记」。

    **认领竞态**（§8.2 / §9.1 第 16 条）：终局判据 = ``assignee`` 是否为空，判据与写入
    在同一个 ``mutate_change()`` 里求值（``update.expect_empty``）⇒ 卡不可能落到两个人
    名下。锁内判据万一不成立（``fallback``），app 层改发第 16 条那句、**不发假公示**。
    """
    if inbound.chat_type != "p2p":
        return Outcome(replies=(reply(inbound, replies.CLAIM_NEED_DM),))

    match = CLAIM_PATTERN.match((text or "").strip())
    if not match:
        return Outcome(replies=(reply(inbound, replies.CLAIM_FORM),))

    me = inbound.sender_open_id
    known = {member.open_id for member in (getattr(roster, "members", None) or ())}
    if not me or (known and me not in known):
        return Outcome(replies=(reply(inbound, replies.CLAIM_NOT_MEMBER),))

    task_id = f"T{match.group(1)}"
    record = next((r for r in (assignments or ()) if r.task_id == task_id), None)
    if record is None:
        return Outcome(replies=(reply(inbound, replies.claim_unknown(task_id, assignments)),))
    if record.assignee:
        if record.assignee == me:
            # 幂等：已经在你自己名下，没有变化 ⇒ 不落盘、不公示，但不静默
            return Outcome(
                replies=(reply(inbound, replies.CLAIM_ALREADY.format(task_id=task_id)),)
            )
        # §9.1 第 16 条：先到先得（D-52），并把剩余能接的卡一并给出
        return Outcome(
            replies=(
                reply(
                    inbound,
                    replies.claim_taken(
                        task_id, name_of(roster, record.assignee), assignments
                    ),
                ),
            )
        )

    stamp = (now or datetime.now()).isoformat(timespec="seconds")
    module = _module_name(task_id, cards)
    out = [reply(inbound, replies.CLAIM_OK.format(task_id=task_id, module=module))]
    if group_chat_id:
        out.append(
            Reply(
                chat_id=group_chat_id,
                text=replies.CLAIM_ANNOUNCED.format(
                    name=name_of(roster, me), task_id=task_id, module=module
                ),
            )
        )
    return Outcome(
        replies=tuple(out),
        save_change={
            "change": {
                "at": stamp,
                "by": me,
                "kind": "claim",
                "task_id": task_id,
                "from_user": "",                    # 从待认领池里拿的，没有前任
                "to_user": me,
                "reason": "",
                "confirmed_by": [me],
            },
            # source 不动（认领改的是"谁做"）—— 同上，不臆想新枚举值，真相在台账里
            "update": {"task_id": task_id, "assignee": me, "expect_empty": True},
            # 锁内判据不成立时改发的句子（认领竞态，§9.1 第 16 条）；人名由 app 层填
            "fallback": {
                "chat_id": inbound.chat_id,
                "template": replies.CLAIM_TAKEN,
                "fields": {"task_id": task_id, "tasks": _pool_text(assignments, task_id)},
            },
        },
    )


def _pool_text(assignments: Sequence[AssignmentRecord], exclude: str = "") -> str:
    """还剩哪些能接（照 `PREFERENCE_BAD` 的形态列编号，不催人）。"""
    ids = [
        record.task_id
        for record in (assignments or ())
        if not record.assignee and record.task_id != exclude
    ]
    return "、".join(ids) if ids else replies.CLAIM_NO_POOL


def _module_name(task_id: str, cards: Sequence[TaskCard]) -> str:
    for card in cards or ():
        if card.task_id == task_id:
            return card.module_name or task_id
    return task_id


def _mentioned_user(inbound: Inbound) -> str:
    """@ 结构里的**人** —— open_id 只从 @ 结构取（D-34），机器人自己那个 @ 不算。"""
    for mention in inbound.mentions or ():
        if mention.is_bot or not mention.open_id:
            continue
        return mention.open_id
    return ""


def name_of(roster: Roster | None, open_id: str) -> str:
    """花名册里查名字；查不到就原样回 open_id（宁可不润色，也不编一个人名）。

    公开的：app 层在"认领竞态"那条回话里也要用它（人名是事实槽位，U5）。
    """
    for member in getattr(roster, "members", None) or ():
        if member.open_id == open_id:
            return member.name or open_id
    return open_id
