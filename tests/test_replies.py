"""U5「说人话」+ D-76 清单派生的**机械检查**（§11.2 的四层判据）。

主观盲评（§11.4 交付物②）留给人做；这里只钉住机器能数的那几条：
条数由前缀表派生、群消息行数预算、禁用结构与口吻词、事实槽位不被改写。
"""

import re

from src.gateway import replies
from src.gateway.events import Inbound
from src.gateway.router import route
from src.models import Member, Roster

# 块状内容（清单 / 表单 / 候选列表）按 §11.3 允许超出行数预算；其余一律照长度纪律数。
BLOCK_TEMPLATES = {
    "COMMAND_LIST_TEXT",
    "COMMAND_LIST_DM",
    "VOTE_CANDIDATES",
    "PREFERENCE_LIST",
    "REGISTER_FORM",
    "REGISTER_FORM_BAD",
    "REGISTER_CONFIRM",
}

# §11.2 ② 点名不许出现的"字段名："结构 + ④ 的口吻词表。
BANNED = (
    "已登记：",
    "已标记完成：",
    "已收到文件：",
    "花名册已保存：",
    "状态：",
    "负责人：",
    "任务：",
    "您",
    "请知悉",
    "已受理",
    "太棒",
    "～",
)


def _templates():
    for name in replies.__all__:
        value = getattr(replies, name)
        if isinstance(value, str):
            yield name, value


def _render(template):
    """把 ``{槽位}`` 换成短值：长度检查量的是**固定骨架**，不是运行时数据。"""
    return re.sub(r"\{[^}]*\}", "X", template)


def _lines(template):
    return len(_render(template).splitlines())


def _roster():
    return Roster(
        leader="ou_zhang",
        members=[
            Member(open_id=open_id, name=name)
            for open_id, name in (("ou_zhang", "张三"), ("ou_li", "李四"))
        ],
        registered_at="2026-09-13T09:00:00",
        confirmed_by="ou_zhang",
    )


def test_command_list_is_derived_from_the_scope_table():
    """D-76：条数**不写死** —— 两份清单都从 COMMANDS 按作用域数出来。

    当前派生 = 群 8 / 私聊 7（含「报告」这类只在群里能用的）—— §12.3 第 15 条的
    **终值**：U4 第 10–12 条（改派 / 退出 / 认领）已全部落地，条数全部由 COMMANDS
    按作用域派生（D-76），下面这两个数字只是"派生结果"的快照。
    """
    group = [item for item in replies.COMMANDS if item.usable_in(replies.GROUP)]
    dm = [item for item in replies.COMMANDS if item.usable_in(replies.DM)]

    assert len(group) == 8
    assert len(dm) == 7
    assert replies.COMMAND_LIST_TEXT == replies.command_list(replies.GROUP)
    assert replies.COMMAND_LIST_DM == replies.command_list(replies.DM)
    assert len(replies.COMMAND_LIST_TEXT.splitlines()) == len(group) + 1     # 表头一行


def test_the_two_lists_are_not_the_same_sheet():
    assert replies.COMMAND_LIST_TEXT != replies.COMMAND_LIST_DM
    assert "「方向」" in replies.COMMAND_LIST_TEXT
    assert "「方向」" not in replies.COMMAND_LIST_DM
    assert "「我想提议：" in replies.COMMAND_LIST_DM
    assert "「我想提议：" not in replies.COMMAND_LIST_TEXT


def test_every_listed_prefix_is_actually_routed():
    """防漂移守卫：表里每条前缀都必须**真的**被 router 接住（不是掉到兜底清单）。"""
    for item in replies.COMMANDS:
        body = item.prefix + ("X" if item.prefix.endswith(("：", ":")) else "")
        inbound = Inbound(
            chat_id="c1",
            chat_type="group",
            message_type="text",
            text=body,
            sender_type="user",
            sender_open_id="ou_user",
            message_id="m1",
            bot_mentioned=True,
        )
        outcome = route(inbound, {}, _roster())
        texts = [r.text for r in outcome.replies]
        assert texts, item.prefix
        assert texts != [replies.COMMAND_LIST_TEXT], item.prefix   # 没掉兜底
        assert outcome.pipeline == "", item.prefix                 # 前置不足不起重活


def test_messages_stay_within_the_group_line_budget():
    """§11.2 ③：群消息 ≤4 行（私聊 ≤6 自动满足）。块状模板见 §11.3 的例外。"""
    over = {
        name: _lines(text)
        for name, text in _templates()
        if name not in BLOCK_TEMPLATES and _lines(text) > 4
    }
    assert over == {}


def test_block_templates_stay_bounded():
    """块状模板允许超 4 行（§11.3），但**也得有界** —— 免得哪天清单长到刷屏。"""
    over = {name: _lines(text) for name, text in _templates() if _lines(text) > 10}
    assert over == {}


def test_no_field_label_or_polite_filler():
    """§11.2 ② / ④：不写"字段名：值"，不"您 / 请知悉 / 已受理"，不卖萌。"""
    hits = {
        name: [word for word in BANNED if word in text]
        for name, text in _templates()
        if any(word in text for word in BANNED)
    }
    assert hits == {}


def test_no_double_parenthesis_stacking_per_line():
    """§11.2 ②：同一句里不许出现 ≥2 处 ``（…）`` 堆叠。"""
    pattern = re.compile(r"（[^）]*）[^）\n]*（[^）]*）")
    hits = [
        name
        for name, text in _templates()
        if any(pattern.search(line) for line in text.splitlines())
    ]
    assert hits == []


def test_the_group_version_teaches_the_mention():
    """群里教动作必须自带「@我」：门禁在群里没 @ 就静默（§9.1 第 4 条）。

    修之前：群清单第 1 条写"再回「作业书」"、`FILE_MISSING` 也没带 @ ——
    机器人自己教的动作会被自己的门禁吃掉（真机：群里投完 PDF 再发不带 @ 的
    「作业书」，一个字都不回）。
    """
    group_first = replies.command_list(replies.GROUP).splitlines()[1]
    dm_first = replies.command_list(replies.DM).splitlines()[1]

    assert "@我" in group_first
    assert "@我" not in dm_first                        # 私聊不套 @ 规则（L5）
    assert "@我" not in replies.COMMAND_LIST_DM

    # 四处按作用域分叉的文案：群里那版必须带「@我」，私聊那版一个字都不许有
    for render, dm_text in (
        (replies.file_missing, replies.FILE_MISSING),
        (replies.parse_failed, replies.PARSE_FAILED),
        (replies.needs_rubric, replies.NEEDS_RUBRIC),
    ):
        assert render(replies.DM) == dm_text, render
        assert "@我" not in dm_text, render
        assert "@我" in render(replies.GROUP), render
