"""M7 简版：命令行「评分点核对清单」渲染（纯模板，零智能）。

依据：requirements.md §7.2 / §7.3、docs/ARCHITECTURE.md §8.1 / §12.4 第 5 步、D-18。

这是 D5 门 ② 要看的产物：评分点 → 覆盖它的任务卡，以及**循环口径**的覆盖率数字。
展示口径与判定口径必须一致：分母 = ``status="normal"`` 的可拆点（§7.2）。
模糊点单列 "[?] 需组长确认"，不进分母、也不假装被解决。

M7 执行报告复用的就是本函数：多传一个 ``assignments`` 就多出执行阶段的
「负责人 + 完成」两列（**执行**口径）；默认不传，输出与 M3 时代逐字一致。
注意别把两件事混了 —— 原来的 ``[x] / [ ] / [?]`` 是**覆盖**（这个评分点有没有
被任务卡接住，拆解阶段），新加的「完成 n/m」是**执行**（卡有没有被标完成）。
"""

from __future__ import annotations

from typing import Sequence

from src.intelligence.coverage import balance_loop, coverage_loop
from src.intelligence.decompose import DecomposeResult
from src.models import BALANCE_LIMIT, AssignmentMeta, AssignmentRecord, Roster, RubricPoint, TaskCard

__all__ = ["render_checklist", "render_workload_checklist"]


def _meta_line(meta: AssignmentMeta) -> str:
    """抬头那一行。**空字段不许显示成空档**（D-49 + 2026-09-17 拍 A）。

    ``deadline`` 早就是「未标注」；``course / title / submission`` 允许空之后同样按
    「未标注」显示 —— 肉眼看得见，才知道下一步该补什么。两条链路共用这一行。
    """

    def show(value: str) -> str:
        return (value or "").strip() or "未标注"

    return (
        f"《{show(meta.title)}》 {show(meta.course)}"
        f"｜交付：{show(meta.submission)}｜截止：{show(meta.deadline)}"
    )


def render_checklist(
    meta: AssignmentMeta,
    points: Sequence[RubricPoint],
    cards: Sequence[TaskCard],
    result: DecomposeResult,
    *,
    assignments: Sequence[AssignmentRecord] = (),
    roster: Roster | None = None,
) -> str:
    """``assignments`` / ``roster`` 都是**可选**的 keyword-only：

    传了 ``assignments`` 才渲染执行阶段那两列（M7 用）；``roster`` 只影响"负责人"显示
    人名还是 ``ou_xxx``（纯展示）。不传 = M3 时代的老输出，一个字都不变。
    """
    owners: dict[str, list[str]] = {}
    for card in cards:
        for ref in card.rubric_refs:
            owners.setdefault(ref, []).append(card.task_id)
    by_task = {record.task_id: record for record in (assignments or ())}

    coverage = coverage_loop(cards, points)
    lines = [
        _meta_line(meta),
        "",
        "评分点核对清单",
    ]
    for point in points:
        weight = f"（{point.weight:g}）" if point.weight is not None else ""
        tasks = owners.get(point.id, [])
        if point.status != "normal":
            tail = (
                "需组长确认（模糊要求，未进循环分母）"
                if not tasks
                else f"需组长确认（模糊要求；已被 {'、'.join(tasks)} 引用）"
            )
            mark = "[?]"
        else:
            mark = "[x]" if tasks else "[ ]"
            tail = "→ " + "、".join(tasks) if tasks else "未覆盖"
        line = f"- {mark} {point.id}{weight}{tail}"
        if assignments:
            line += _execution_suffix(tasks, by_task, roster)
        lines.append(line)
        lines.append(f"      原文：{point.quote}")

    balance = balance_loop(cards)
    if coverage.eligible:
        coverage_line = (
            f"覆盖率：{len(coverage.covered)}/{len(coverage.eligible)} = {coverage.ratio:.0%}"
            "（循环口径：分母 = status=normal 的可拆点）"
        )
    else:
        coverage_line = "覆盖率：无可拆点 → 拒拆（不是 100%）"
    balance_line = (
        f"工时均衡：max/min = {balance.ratio:.2f}（上限 {BALANCE_LIMIT:g}）；"
        f"任务卡 {len(cards)} 张"
    )
    if result.generations:
        # M7 的执行报告是从盘上重读的产物，没有"这一版拆了几轮"这回事（generations=0）
        balance_line += f"；生成 {result.generations} 轮"
    lines += ["", coverage_line, balance_line]
    if result.failures:
        lines.append("自检未达标（按 D-18 交人决定）：" + "；".join(result.failures))
    else:
        lines.append("自检通过：可拆评分点全覆盖、工时均衡。")
    return "\n".join(lines)


def _execution_suffix(
    tasks: Sequence[str], by_task: dict[str, AssignmentRecord], roster: Roster | None
) -> str:
    """执行阶段的两列：``｜负责人：张三 ｜完成 1/2``（没人接就都是 ``—``）。"""
    if not tasks:
        return " ｜负责人：— ｜完成 —"
    names: list[str] = []
    done = 0
    for task_id in tasks:
        record = by_task.get(task_id)
        name = _name(record.assignee, roster) if record else "未分配"
        if name not in names:
            names.append(name)
        if record is not None and record.completed_at:
            done += 1
    return f" ｜负责人：{'、'.join(names)} ｜完成 {done}/{len(tasks)}"


def _name(open_id: str, roster: Roster | None) -> str:
    for member in getattr(roster, "members", None) or ():
        if member.open_id == open_id and member.name:
            return member.name
    return (open_id[:8] if open_id else "待认领")           # §8.3：空负责人 = 回流池


def render_workload_checklist(
    meta: AssignmentMeta,
    cards: Sequence[TaskCard],
    result: DecomposeResult,
    *,
    assignments: Sequence[AssignmentRecord] = (),
    roster: Roster | None = None,
) -> str:
    """U3 **无评分点链路**的核对清单（§6.2 / §6.6）。

    与 ``render_checklist()`` 的分工：**只把"评分点核对 + 覆盖率"换成"工作量估算"**，
    抬头 / 交付 / 截止 / 负责人 / 完成那几列照旧 —— M7 的分配总表与甘特图也照旧
    （换的只是这一份清单里的那一段）。硬指标 = 工作量分布，**一个覆盖率数字都不出现**。
    """
    by_task = {record.task_id: record for record in (assignments or ())}
    lines = [
        _meta_line(meta),
        "",
        "工作量核对清单（估算，可改）",
    ]
    for card in cards:
        line = f"- {card.task_id} {card.module_name}（{card.effort_hours:g} 人时）→ {card.deliverable}"
        if assignments:
            line += _execution_suffix([card.task_id], by_task, roster)
        lines.append(line)
        lines.append(f"      验收：{card.acceptance}")
        for ref in card.source_refs:
            lines.append(f"      依据：{ref}")

    balance = balance_loop(cards)
    total = sum(card.effort_hours for card in cards)
    distribution_line = (
        f"工作量分布：合计 {total:g} 人时；max/min = {balance.ratio:.2f}"
        f"（上限 {BALANCE_LIMIT:g}）；任务卡 {len(cards)} 张"
    )
    if result.generations:
        distribution_line += f"；生成 {result.generations} 轮"
    lines += ["", distribution_line]
    if result.failures:
        lines.append("自检未达标（按 D-18 交人决定）：" + "；".join(result.failures))
    else:
        lines.append("自检通过：每张卡都有溯源、工时均衡。")
    return "\n".join(lines)
