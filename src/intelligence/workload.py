"""U3 无评分点链路 —— 作业书正文 → 工作量任务卡（**LLM 调用点 4/4**）。

依据：`docs/ARCHITECTURE-UPGRADE.md` §6.1（总开关）/ §6.2（两条平行链路）/
§6.4（`source_refs` 按链路二选一）/ §6.6（工作量字段复用 `effort_hours`，
估算一律"参考值、可调整"）。

**红线（§6.2，可机械检查）**：
  * 本模块**不 import 也不调用任何覆盖率取数函数**（`coverage.py` 里那个也不许）
  —— 这条链路不出覆盖率；
  * 不写凑数评分点：产出的卡 ``rubric_refs`` 一律为空，落盘时 `rubric.json` 只记
    这份作业书**真实的**评分点（可能为空 / 全是 ambiguous），**绝不合成**；
  * 工时均衡用 ``balance_loop()`` 判 —— 它是工时均衡、不是覆盖率取数，允许复用。

分工与 ``decompose.py`` 一致（B8）：**LLM 只生成，判定权在 ``check_workload()``（代码）**。
落盘不在这里（本模块不碰 I/O），由调用方（gateway）落 ``cards.json``。

M7 的报告要按现状重算自检，手里没有作业书正文 ⇒ ``check_workload(cards)`` 不带
``text`` 时**跳过"原文对得上"那一条**（只查非空 / 均衡 / 依赖），其余判定不变。
"""

from __future__ import annotations

import json
import re
from typing import Sequence

from src.intelligence.coverage import balance_loop
from src.intelligence.decompose import DecomposeResult, find_cycle
from src.intelligence.llm import LLMClient, LLMOutputError, as_number
from src.models import BALANCE_LIMIT, SchemaError, TaskCard

__all__ = ["check_workload", "decompose_workload", "WORKLOAD_SYSTEM"]

# source_refs 元素的形态：``原文片段 → 估算依据``。箭头全角 / 半角都认（照
# PROPOSAL_PREFIXES 的现成做法，中文输入法容易出半角）。
_SEPARATORS = ("→", "->")
# 引用里若带省略号，按段校验（长段落被 LLM 摘成"头…尾"是正常写法）
_ELLIPSIS = ("…", "...")
_TRIM = "「」『』《》" + chr(34) + chr(39)


WORKLOAD_SYSTEM = """你是小组作业机器人里的「工作量拆解」模块。这份作业书**没有可核对的评分标准**，所以不要找评分点、不要编评分点，按正文里的实际要求把活拆开。

只输出 JSON 对象本身，不要解释、不要 markdown 代码块：

{"cards": [{"task_id": "T1", "module_name": "实现登录模块", "rubric_refs": [],
            "source_refs": ["原文里逐字出现的片段 → 为什么估这么多人时"],
            "effort_hours": 6, "depends_on": [],
            "deliverable": "一个源文件", "acceptance": "怎么算做完"}]}

关于输入文本：它可能来自 PDF / Word 抽取的正文；表格被单独抽出，用一行"=== 表格区域 ==="标记，其下每行形如 "- 列名：值｜列名：值"。

字段要求：
- task_id：从 T1 起连续编号，全局唯一。
- module_name：动词开头的模块名（如"实现登录模块""撰写实验报告"）。
- rubric_refs：**必须是空数组**。这份作业书没有评分点，引用任何 id 都是编造。
- source_refs：**必填非空**，每张卡至少一条，每条写成 `原文片段 → 估算依据`：
  * 左边是上面文本里**逐字出现**的片段（不许改写、概括、翻译或拼接）；
  * 右边写清怎么估的（如"参考同类课程 3 页报告 × 1.5 人时"、"接口 4 个 × 2 人时"）；
  * 代码会拿左边去正文里做子串校验，对不上就把你这次输出打回重拆。
- effort_hours：人时估计，最小 0.5。这是**参考值、可以改**，不是承诺。
- depends_on：前置 task_id 数组；空数组表示可立即开始。
- deliverable：这一块交什么（一个源文件 / 一段报告章节 / 一页 PPT）。
- acceptance：怎么算做完，从正文要求改写，能直接拿去核对。

硬约束：
1. 只按正文里**真实写了**的要求建卡：交付物、报告章节、演示、测试、文档都算；正文没提的不要自己加。
2. 各卡 effort_hours 尽量均衡，最大 / 最小不超过 3 倍。
3. 卡片数量以"每个组员都领得到活"为准，不要为凑数拆碎，也不要漏掉交付物。
4. 依赖顺序合理：被依赖的卡先做。
5. 只做拆解：不要输出评分点、不要算覆盖率、不要提建议。"""


def check_workload(cards: Sequence[TaskCard], text: str = "") -> list[str]:
    """无评分点链路的自检（D-16 的形态：返回**失败原因列表**，空 = 达标）。

    ``text`` 给了就多查一条"原文对得上"（防 LLM 编造段落引用，与 M1 的 ``quote``
    子串校验同源）；M7 从盘上重算时没有正文，传空即跳过那一条。
    """
    cards = list(cards or ())
    if not cards:
        # 短路口径同 `decompose.check()`：不调 max()/min()，也别让"空集"混成"均衡"
        return ["没有任何任务卡（工作量链路至少要拆出一张卡）"]

    problems: list[str] = []
    for card in cards:
        if not card.source_refs:
            problems.append(
                f"{card.task_id} 的 source_refs 是空的 —— 无评分点链路的溯源字段不能空"
            )
        if card.rubric_refs:
            problems.append(
                f"{card.task_id} 引用了评分点（{card.rubric_refs}）—— 这条链路没有评分点，"
                "引用了就是凑数"
            )
        for ref in card.source_refs or ():
            problem = _ref_problem(ref, text)
            if problem:
                problems.append(f"{card.task_id} 的 source_refs {problem}")

    cycle = find_cycle(cards)
    if cycle:
        problems.append("依赖成环：" + " → ".join(cycle))
    balance = balance_loop(cards)
    if balance.ratio > BALANCE_LIMIT:
        problems.append(
            f"工时不够均衡：max/min = {balance.ratio:.2f}（上限 {BALANCE_LIMIT:g}）"
        )
    return problems


def decompose_workload(
    text: str, client: LLMClient, *, max_generations: int = 3
) -> DecomposeResult:
    """作业书正文 → 工作量任务卡：生成 → ``check_workload()`` → 失败详情喂回重拆。

    沿用 ``decompose()`` 的循环形态（默认 3 = 初拆 + 两次带反馈的重拆）；返回的
    ``DecomposeResult`` 只是**容器复用**（卡 / 失败原因 / 轮数三样同形），
    它背后的判定与取数**与覆盖率链路完全不共用**（红线，§6.2）。
    """
    cards = _generate(text, client, feedback=None)
    generations = 1
    failures = tuple(check_workload(cards, text))
    while failures and generations < max_generations:
        cards = _generate(text, client, feedback=failures, previous=cards)
        generations += 1
        failures = tuple(check_workload(cards, text))
    return DecomposeResult(tuple(cards), failures, generations)


def _generate(
    text: str,
    client: LLMClient,
    *,
    feedback: Sequence[str] | None = None,
    previous: Sequence[TaskCard] | None = None,
) -> list[TaskCard]:
    user = "作业书文本如下：\n\n" + text
    if feedback:
        user += "\n\n上一次拆解未通过自检：\n" + "\n".join(f"- {item}" for item in feedback)
    if feedback and previous:
        user += "\n\n上一次的任务卡（请在此基础上修正）：\n" + json.dumps(
            [card.to_dict() for card in previous], ensure_ascii=False
        )
    user += '\n\n请输出 JSON：{"cards": [...]}'

    def parse(response) -> list[TaskCard]:
        return _validate_cards(response)

    return client.chat_json(WORKLOAD_SYSTEM, user, parse)


def _validate_cards(payload) -> list[TaskCard]:
    """LLM 输出的 schema 校验（不是自检判定）：字段齐、取值合法、溯源按链路二选一。"""
    problems: list[str] = []
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("cards"), list)
        or not payload["cards"]
    ):
        raise LLMOutputError('顶层必须是 {"cards": [...]}，且 cards 非空')

    cards: list[TaskCard] = []
    for index, item in enumerate(payload["cards"]):
        if not isinstance(item, dict):
            problems.append(f"cards[{index}] 不是对象")
            continue
        data = dict(item)
        if "effort_hours" in data:
            data["effort_hours"] = as_number(data["effort_hours"])
        data.setdefault("rubric_refs", [])
        try:
            card = TaskCard.from_dict(data)
            card.validate()
        except (SchemaError, TypeError, ValueError) as exc:
            problems.append(f"cards[{index}] 字段不合法：{exc}")
            continue
        for name in ("module_name", "deliverable", "acceptance"):
            if not getattr(card, name).strip():
                problems.append(f"cards[{index}]({card.task_id}) 的 {name} 不能为空")
        if not card.source_refs:
            problems.append(f"cards[{index}]({card.task_id}) 缺 source_refs")
        elif any(not _split(ref)[0] or not _split(ref)[1] for ref in card.source_refs):
            problems.append(
                f"cards[{index}]({card.task_id}) 的 source_refs 要写成"
                "「原文片段 → 估算依据」"
            )
        cards.append(card)

    ids = [card.task_id for card in cards]
    duplicates = sorted({tid for tid in ids if ids.count(tid) > 1})
    if duplicates:
        problems.append(f"task_id 重复：{duplicates}")
    dangling = sorted({dep for card in cards for dep in card.depends_on} - set(ids))
    if dangling:
        problems.append(f"depends_on 指向不存在的 task_id：{dangling}")

    if problems:
        raise LLMOutputError("；".join(problems))
    return cards


def _split(ref: str) -> tuple[str, str]:
    """``原文片段 → 估算依据`` → 两半；没有箭头就返回两个空串。"""
    for separator in _SEPARATORS:
        if separator in ref:
            quote, _, basis = ref.partition(separator)
            return quote.strip().strip(_TRIM).strip(), basis.strip()
    return "", ""


def _ref_problem(ref: str, text: str) -> str:
    """一条 source_refs 的问题描述；``""`` = 没问题。"""
    quote, basis = _split(ref)
    if not quote or not basis:
        return f"要写成「原文片段 → 估算依据」，得到 {ref[:30]!r}"
    if not text:
        return ""                        # 没有正文可对（M7 从盘上重算）：只查形态
    haystack = _normalize(text)
    pieces = [piece for piece in re.split(r"…|\.\.\.", quote) if piece]
    for piece in pieces or [quote]:
        if _normalize(piece) not in haystack:
            return f"的原文片段对不上作业书：{piece[:30]!r}"
    return ""


def _normalize(value: str) -> str:
    """去所有空白 —— 与 M1 的 ``_normalize()`` 同款（PDF 换行 / 空格不该造成假不匹配）。"""
    return re.sub(r"\s+", "", value or "")
