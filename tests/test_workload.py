"""U3 无评分点链路（工作量拆解）单测 —— 含 §6.2 的红线机械检查。

不碰网络、不碰飞书：LLM 用假客户端，纯数据进出。
"""

import inspect

import pytest

from src.intelligence import workload
from src.intelligence.llm import LLMOutputError
from src.intelligence.workload import check_workload, decompose_workload
from src.models import SchemaError, TaskCard

DOC = "作业书：1 实现词法分析器，交付源码。2 撰写实验报告，不少于 3 页。"


def _card(task_id="T1", refs=None, hours=4.0, depends_on=None, rubric_refs=None):
    return TaskCard(
        task_id=task_id,
        module_name=f"模块{task_id}",
        rubric_refs=list(rubric_refs or []),
        effort_hours=hours,
        deliverable="一个源文件",
        acceptance="可运行",
        depends_on=list(depends_on or []),
        source_refs=list(refs if refs is not None else ["实现词法分析器 → 参考同类课程 4 人时"]),
    )


class FakeLLM:
    """按次序吐 payload；用 caller 记录 prompt 里有没有喂回失败详情。"""

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def chat_json(self, system, user, parse, **kwargs):
        self.calls.append(user)
        payload = self.payloads[min(len(self.calls) - 1, len(self.payloads) - 1)]
        return parse(payload)


def _good_payload():
    return {
        "cards": [
            {
                "task_id": "T1",
                "module_name": "实现词法分析器",
                "rubric_refs": [],
                "source_refs": ["实现词法分析器 → 参考同类课程 4 人时"],
                "effort_hours": 4,
                "depends_on": [],
                "deliverable": "一个源文件",
                "acceptance": "能跑通词法用例",
            },
            {
                "task_id": "T2",
                "module_name": "撰写实验报告",
                "rubric_refs": [],
                "source_refs": ["撰写实验报告 → 3 页 × 2 人时"],
                "effort_hours": 6,
                "depends_on": ["T1"],
                "deliverable": "一份报告",
                "acceptance": "不少于 3 页",
            },
        ]
    }


# ---------- 溯源字段：按链路二选一（§6.4 (a)）----------


def test_a_card_may_carry_source_refs_instead_of_rubric_refs():
    _card().validate()                      # 不抛就是过


def test_a_card_without_any_trace_is_rejected():
    with pytest.raises(SchemaError) as exc:
        _card(refs=[]).validate()
    assert "溯源" in str(exc.value)


def test_source_refs_must_be_non_empty_strings():
    with pytest.raises(SchemaError):
        _card(refs=["  "]).validate()


# ---------- check_workload：判定 ----------


def test_missing_trace_and_borrowed_points_are_both_flagged():
    problems = check_workload(
        [_card("T1", refs=[]), _card("T2", rubric_refs=["R1"])], DOC
    )

    assert any("source_refs 是空的" in item for item in problems)
    assert any("引用了评分点" in item and "凑数" in item for item in problems)


def test_an_empty_card_list_is_short_circuited():
    assert check_workload([], DOC) == [
        "没有任何任务卡（工作量链路至少要拆出一张卡）"
    ]


def test_the_quote_must_appear_in_the_source_text():
    ok = check_workload([_card("T1", refs=["实现词法分析器 → 4 人时"])], DOC)
    bad = check_workload([_card("T1", refs=["做一个聊天机器人 → 8 人时"])], DOC)

    assert ok == []
    assert any("对不上作业书" in item for item in bad)


def test_a_quote_may_use_an_ellipsis():
    card = _card("T1", refs=["实现词法分析器…交付源码 → 4 人时"])
    assert check_workload([card], DOC) == []


def test_the_quote_check_is_skipped_without_the_source_text():
    """M7 是拿盘上的卡重算自检的，手里没有正文 ⇒ 只查形态，不诬告。"""
    card = _card("T1", refs=["做一个聊天机器人 → 8 人时"])
    assert check_workload([card]) == []


def test_a_ref_without_a_basis_is_flagged():
    problems = check_workload([_card("T1", refs=["实现词法分析器"])], DOC)

    assert any("估算依据" in item for item in problems)


def test_unbalanced_hours_and_cycles_are_flagged():
    unbalanced = check_workload(
        [_card("T1", hours=1.0), _card("T2", hours=30.0)], DOC
    )
    cycle = check_workload(
        [
            _card("T1", depends_on=["T2"]),
            _card("T2", depends_on=["T1"]),
        ],
        DOC,
    )

    assert any("不够均衡" in item for item in unbalanced)
    assert any("成环" in item for item in cycle)


# ---------- §6.2 红线：不碰覆盖率 ----------


def test_the_workload_module_never_mentions_the_coverage_loop():
    """机械检查：源码里连名字都不许出现（红线「写一个字都要拦」）。"""
    source = inspect.getsource(workload)
    assert "coverage_loop" not in source


def test_the_workload_link_never_calls_the_coverage_loop(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("无评分点链路不许碰覆盖率取数（§6.2）")

    monkeypatch.setattr("src.intelligence.coverage.coverage_loop", boom)
    result = decompose_workload(DOC, FakeLLM([_good_payload()]), max_generations=1)

    assert result.ok
    assert all(not card.rubric_refs for card in result.cards)


# ---------- decompose_workload：生成 → 自检 → 喂回重拆 ----------


def test_a_quote_that_misses_the_source_is_fed_back_and_regenerated():
    """schema 过得去、内容对不上（编造段落引用）⇒ 走自检喂回重拆，不是直接失败。"""
    first = _good_payload()
    first["cards"][0]["source_refs"] = ["做一个聊天机器人 → 8 人时"]
    llm = FakeLLM([first, _good_payload()])
    result = decompose_workload(DOC, llm)

    assert result.generations == 2
    assert result.ok
    assert "上一次拆解未通过自检" in llm.calls[1]
    assert "对不上作业书" in llm.calls[1]


def test_a_card_without_source_refs_is_a_schema_error():
    """每卡非空是**字段契约**（`TaskCard.validate()`），不靠自检兜 —— 与 M1 同款。"""
    payload = {**_good_payload(), "cards": [{**_good_payload()["cards"][0], "source_refs": []}]}
    with pytest.raises(LLMOutputError):
        decompose_workload(DOC, FakeLLM([payload]), max_generations=1)


def test_borrowed_points_never_pass():
    payload = {
        "cards": [
            {**_good_payload()["cards"][0], "rubric_refs": ["R1"]},
            _good_payload()["cards"][1],
        ]
    }
    result = decompose_workload(DOC, FakeLLM([payload]), max_generations=2)

    assert not result.ok
    assert any("凑数" in item for item in result.failures)


def test_the_llm_output_must_be_a_non_empty_card_list():
    with pytest.raises(LLMOutputError):
        decompose_workload(DOC, FakeLLM([{"cards": []}]), max_generations=1)


def test_a_broken_card_is_a_schema_error_not_a_silent_pass():
    llm = FakeLLM([{"cards": [{"task_id": "T1"}]}])
    with pytest.raises(LLMOutputError):
        decompose_workload(DOC, llm, max_generations=1)
