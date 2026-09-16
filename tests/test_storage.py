import json

import pytest

from src import storage
from src.models import (
    AssignmentRecord,
    ChangeRecord,
    Member,
    Roster,
    RubricPoint,
    SchemaError,
    TaskCard,
)
from src.storage import JsonStore


@pytest.fixture()
def store(tmp_path):
    return JsonStore(tmp_path)


def _card(**over):
    data = dict(
        task_id="T1",
        module_name="实现登录模块",
        rubric_refs=["R1"],
        effort_hours=4.0,
        deliverable="一个源文件",
        acceptance="从 R1 原文改写",
    )
    data.update(over)
    return TaskCard(**data)


def test_roundtrip_cards(store):
    store.save_cards([_card()])
    cards = store.load_cards()
    assert [c.task_id for c in cards] == ["T1"]
    assert cards[0].rubric_refs == ["R1"]


def test_missing_files_are_empty_not_error(store):
    assert store.load_cards() == []
    assert store.load_rubric() == []
    assert store.load_preferences() == []
    assert store.load_assignments() == []
    assert store.load_assignment() is None
    assert store.load_members() is None
    assert store.load_proposals() == []
    assert store.load_state() == {}
    assert store.load_changes() == []


def test_write_is_atomic_and_leaves_no_tmp(store):
    store.save_cards([_card()])
    assert list(store.root.glob("*.tmp")) == []
    assert (store.root / storage.CARDS).exists()


def test_validate_runs_on_write_and_leaves_file_intact(store):
    store.save_cards([_card()])
    bad = _card(task_id="T2", rubric_refs=[{"id": "R1", "quote": "原文"}])
    with pytest.raises(SchemaError):
        store.save_cards([bad])
    assert [c.task_id for c in store.load_cards()] == ["T1"]


def test_mutate_many_is_typed_and_persists(store):
    store.save_rubric([RubricPoint(id="R1", quote="原文一段", observable="可核对")])

    def add(points):
        points.append(RubricPoint(id="R2", quote="原文两段", observable="可核对"))
        return points

    result = store.mutate_many(storage.RUBRIC, RubricPoint, add)
    assert [p.id for p in result] == ["R1", "R2"]
    assert [p.id for p in store.load_rubric()] == ["R1", "R2"]


def test_mutate_many_does_not_write_when_fn_raises(store):
    store.save_rubric([RubricPoint(id="R1", quote="原文", observable="可核对")])

    def boom(points):
        raise RuntimeError("生成失败")

    with pytest.raises(RuntimeError):
        store.mutate_many(storage.RUBRIC, RubricPoint, boom)
    assert [p.id for p in store.load_rubric()] == ["R1"]


def test_mutate_many_does_not_write_when_validation_fails(store):
    store.save_cards([_card()])

    def corrupt(cards):
        cards[0].rubric_refs = [{"id": "R1"}]        # D-03 违规
        return cards

    with pytest.raises(SchemaError):
        store.mutate_many(storage.CARDS, TaskCard, corrupt)
    assert store.load_cards()[0].rubric_refs == ["R1"]


def test_mutate_raw_for_state(store):
    def set_awaiting(state):
        state["awaiting"] = "vote"
        return state

    store.mutate_raw(storage.STATE, set_awaiting, default={})
    assert store.load_state() == {"awaiting": "vote"}


def _fingerprint(*paths):
    """字节 + mtime + 大小：条件写要证明的是"根本没动过这份文件"。"""
    return [(p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_size) for p in paths]


def test_mutate_writes_nothing_when_the_value_is_unchanged(store):
    """9/17 补丁批 ③（§8.2 v1.8 条件写）：新值 == 旧值 ⇒ **不写盘**（字节与 mtime 都不动）。"""
    store.save_state({"awaiting": None, "seen": ["m1"]})
    store.save_rubric([RubricPoint(id="R1", quote="原文", observable="可核对")])
    state_path = store.root / storage.STATE
    rubric_path = store.root / storage.RUBRIC
    before = _fingerprint(state_path, rubric_path)

    same_state = store.mutate_raw(storage.STATE, lambda payload: payload, default={})
    same_rubric = store.mutate_many(storage.RUBRIC, RubricPoint, lambda items: items)

    assert same_state == {"awaiting": None, "seen": ["m1"]}       # 值照样原样返回
    assert [p.id for p in same_rubric] == ["R1"]
    assert _fingerprint(state_path, rubric_path) == before


def test_mutate_does_not_materialize_a_missing_file_without_a_change(store):
    """文件不存在 + 值还是 `default`（fn 原样返回）⇒ 也不凭空造一份出来。"""
    store.mutate_raw(storage.STATE, lambda payload: payload, default={})
    assert not (store.root / storage.STATE).exists()


def test_mutate_still_writes_when_the_value_changes(store):
    """条件写不许过火：真变了就必须落盘（防"幂等"把正常写入一起吃掉）。"""
    store.save_state({"awaiting": None})
    path = store.root / storage.STATE
    before = path.read_bytes()

    store.mutate_raw(storage.STATE, lambda payload: {**payload, "awaiting": "vote"}, default={})

    assert path.read_bytes() != before
    assert store.load_state() == {"awaiting": "vote"}


def test_corrupt_json_raises_instead_of_guessing(store):
    (store.root / storage.CARDS).write_text("{不是合法 JSON", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        store.load_cards()


def test_members_roundtrip(store):
    roster = Roster(
        leader="u_zhang",
        registered_at="ts",
        confirmed_by="u_zhang",
        members=[
            Member(open_id="u_zhang", name="张三"),
            Member(open_id="u_li", name="李四"),
        ],
    )
    store.save_members(roster)
    back = store.load_members()
    assert back.leader == "u_zhang"
    assert [m.name for m in back.members] == ["张三", "李四"]


def test_lock_is_process_wide_not_per_instance():
    a = JsonStore("x")
    b = JsonStore("y")
    assert a._lock is b._lock


# ---------- U4 变更台账（§8.2）----------


def _change(**over):
    data = dict(
        at="2026-09-17T21:00:00",
        by="ou_zhang",
        kind="reassign",
        task_id="T1",
        from_user="ou_li",
        to_user="ou_wang",
        confirmed_by=["ou_zhang"],
    )
    data.update(over)
    return ChangeRecord(**data)


def _owner(open_id, source="auto"):
    return AssignmentRecord(task_id="T1", assignee=open_id, source=source)


def test_mutate_change_writes_the_ledger_before_the_state(store, monkeypatch):
    """§8.2 v1.6 的写序：先 changes.json（意图日志）、再 assignments.json（状态）。"""
    store.save_assignments([_owner("")])
    written: list[str] = []
    original = store._write_unlocked

    def spy(name, payload):
        written.append(name)
        original(name, payload)

    monkeypatch.setattr(store, "_write_unlocked", spy)
    ok, owner = store.mutate_change(_change(), "T1", "ou_wang", "leader")

    assert (ok, owner) == (True, "ou_wang")
    assert written == [storage.CHANGES, storage.ASSIGNMENTS]


def test_mutate_change_round_trips_the_ledger(store):
    store.save_assignments([_owner("ou_li")])
    store.mutate_change(_change(task_id="T1", from_user="ou_li"), "T1", "ou_wang", "leader")

    changes = store.load_changes()
    assert [(c.kind, c.from_user, c.to_user, c.by) for c in changes] == [
        ("reassign", "ou_li", "ou_wang", "ou_zhang")
    ]
    record = store.load_assignments()[0]
    assert (record.assignee, record.source) == ("ou_wang", "leader")


def test_release_sends_the_card_back_to_the_pool_and_keeps_the_source(store):
    store.save_assignments([_owner("ou_li", source="volunteer_1")])
    ok, _ = store.mutate_change(
        _change(kind="release", from_user="ou_li", to_user=""), "T1", ""
    )

    assert ok is True
    record = store.load_assignments()[0]
    assert (record.assignee, record.source) == ("", "volunteer_1")
    assert store.load_changes()[0].kind == "release"


def test_mutate_change_refuses_a_card_someone_else_took(store):
    """认领竞态（§8.2）：expect_empty 的判据在锁内求值 —— 后到者一个字节都不写。"""
    store.save_assignments([_owner("ou_li")])

    ok, owner = store.mutate_change(
        _change(kind="claim", from_user="", to_user="ou_wang"),
        "T1",
        "ou_wang",
        expect_empty=True,
    )

    assert (ok, owner) == (False, "ou_li")
    assert store.load_changes() == []                       # 台账没写
    assert store.load_assignments()[0].assignee == "ou_li"  # 状态没动


def test_mutate_change_is_a_no_op_when_the_owner_is_unchanged(store):
    """§9.1 第 17 条：没有变化就不产生台账条目。"""
    store.save_assignments([_owner("ou_li")])

    ok, owner = store.mutate_change(_change(from_user="ou_li", to_user="ou_li"), "T1", "ou_li")

    assert (ok, owner) == (False, "ou_li")
    assert store.load_changes() == []


def test_mutate_change_does_not_invent_a_missing_card(store):
    ok, owner = store.mutate_change(_change(task_id="T9"), "T9", "ou_wang")

    assert (ok, owner) == (False, "")
    assert store.load_changes() == []
    assert store.load_assignments() == []


def test_change_record_rejects_what_the_doc_does_not_allow():
    _change().validate()                                    # 正例：不抛就是过
    with pytest.raises(SchemaError):
        _change(kind="swap").validate()
    with pytest.raises(SchemaError):
        _change(to_user="").validate()                      # reassign 必须写明接手
    with pytest.raises(SchemaError):
        _change(kind="release", to_user="ou_wang").validate()
    with pytest.raises(SchemaError):
        _change(by="").validate()
