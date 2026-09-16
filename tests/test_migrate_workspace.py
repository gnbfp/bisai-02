r"""`tools/migrate_workspace.py` 的回归用例（依据 §3.3 / §3.4）。

为什么要有这组用例：工具是离线的，但它的两条命门 —— **幂等**（重跑不产生第二份工作
空间、不覆盖已有索引条目）与 **`Resolve-Path` 守卫**（只许写/删目标根之内的东西）
—— 靠人工演练只能证明"这一次"，改一行就可能悄悄退化。这里用 `tmp_path` 上的假源盘
把它们钉住；真机演练（`data-upgrade\_rehearsal`）照旧要跑，但那是证据、不是回归网。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from tools.migrate_workspace import (
    REPO_ROOT,
    GuardError,
    Locked,
    OutOfScope,
    check_process_lock,
    guard_within,
    migrate,
    resolve_path,
    rollback,
    safe_key,
    source_label,
    tree_digest,
)

CHAT = "oc_33225a17a5b9fdde00a70f92d002a033"
OTHER_CHAT = "oc_6feb8f648197fd033b8de55a78f64d80"
MEMBER_A = "ou_0040fcec9ebf80235a33c3afeed30e84"
MEMBER_B = "ou_4537b96e5257168f1d9d13c6ad0227ea"
MEMBER_C = "ou_01507b0ba78fef38ae31e86aef16637d"
TAIL = CHAT[-6:]


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rubric() -> list[dict]:
    return [
        {"id": "R1", "quote": "交付一个可运行的 Web 业务系统", "observable": "服务端能起", "status": "normal"},
        {"id": "R2", "quote": "提交课程报告一份", "observable": "报告按期提交", "status": "normal"},
        {"id": "R3", "quote": "分组方式自行决定", "observable": "不可观测", "status": "ambiguous"},
    ]


def _cards() -> list[dict]:
    return [
        {"task_id": "T1", "module_name": "后端", "rubric_refs": ["R1"], "effort_hours": 6.0,
         "deliverable": "接口", "acceptance": "能跑", "depends_on": []},
        {"task_id": "T2", "module_name": "报告", "rubric_refs": ["R2"], "effort_hours": 4.0,
         "deliverable": "报告", "acceptance": "含截图", "depends_on": []},
    ]


def make_source(tmp_path: Path, *, chat_id: str = CHAT, pending_chat: str | None = CHAT,
                title: str = "课程任务书") -> Path:
    """造一份"像 MVP data\\ 那样"的源盘：13 个候选名里只放假源盘真有的那几个。"""
    src = tmp_path / "data"
    src.mkdir(parents=True, exist_ok=True)
    _write(src / "assignment.json", {"course": "软件系统设计与开发实践", "title": title,
                                     "submission": "报告一份", "deadline": "", "source_file": "x.pdf"})
    _write(src / "rubric.json", _rubric())
    _write(src / "cards.json", _cards())
    _write(src / "members.json", {
        "leader": MEMBER_A,
        "members": [{"open_id": MEMBER_A, "name": "甲"}, {"open_id": MEMBER_B, "name": "乙"},
                    {"open_id": MEMBER_C, "name": "丙"}],
        "registered_at": "2026-09-15T15:17:46",
        "confirmed_by": MEMBER_A,
    })
    _write(src / "preferences.json", [{"user_id": MEMBER_A, "ranked_task_ids": ["T1"],
                                       "submitted_at": "2026-09-15T16:00:00"}])
    state: dict = {"group_chat_id": chat_id, "awaiting": None, "vote": None, "register": None}
    if pending_chat is not None:
        state["pending_file"] = {"file_key": "file_x", "file_name": "任务书.pdf",
                                 "resource_type": "file", "chat_id": pending_chat, "message_id": "om_x"}
    _write(src / "state.json", state)
    (src / "uploads").mkdir(parents=True, exist_ok=True)
    (src / "uploads" / "任务书.pdf").write_bytes(b"%PDF-1.4 fake\n")
    (src / "state.json.bak").write_text("{}\n", encoding="utf-8")   # 不在候选名里 -> 只进整份备份
    return src


def _dest(tmp_path: Path) -> Path:
    return tmp_path / "data-upgrade"


# --------------------------------------------------------------------------
# 幂等
# --------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path):
    src = make_source(tmp_path)
    manifest = migrate(src, _dest(tmp_path))
    assert manifest["dry_run"] is True
    assert manifest["workspace_changes"] is None
    assert manifest["payload"], "干跑也要给出逐文件计划"
    assert not _dest(tmp_path).exists(), "干跑不许建目录"


def test_apply_copies_payload_and_writes_index(tmp_path):
    src = make_source(tmp_path)
    manifest = migrate(src, _dest(tmp_path), apply=True)
    ws = _dest(tmp_path) / "workspaces" / CHAT
    assert manifest["verify"]["ok"] is True
    assert (ws / "rubric.json").exists() and (ws / "uploads" / "任务书.pdf").exists()
    index = json.loads((_dest(tmp_path) / "index.json").read_text(encoding="utf-8"))
    assert index["workspaces"][CHAT]["name"] == f"课程任务书-{TAIL}"
    assert index["workspaces"][CHAT]["migrated_from"] == source_label(src)
    assert index["user_last_group"] == {MEMBER_A: CHAT, MEMBER_B: CHAT, MEMBER_C: CHAT}
    reads = manifest["verify"]["reads"]
    assert reads["members"] == {"source": 3, "workspace": 3, "equal": True}, "花名册按人数计（§3.4）"
    assert reads["rubric"]["workspace"] == 3 and reads["cards"]["workspace"] == 2
    assert src.exists(), "源盘必须原样留着（只复制、不移动）"


def test_second_run_is_idempotent(tmp_path):
    src = make_source(tmp_path)
    first = migrate(src, _dest(tmp_path), apply=True)
    assert first["workspace_changes"] > 0
    before = tree_digest(_dest(tmp_path) / "workspaces")
    second = migrate(src, _dest(tmp_path), apply=True)
    assert second["workspace_changes"] == 0
    assert second["idempotent"] is True
    assert {row["action"] for row in second["payload"]} <= {"unchanged", "missing"}
    assert second["backup"]["action"] == "reused", "同一份源数据不该堆第二份备份"
    assert second["index"]["workspace_entry"] == "kept"
    assert tree_digest(_dest(tmp_path) / "workspaces") == before


def test_index_merge_keeps_existing_name_and_binding(tmp_path):
    src = make_source(tmp_path)
    dest = _dest(tmp_path)
    _write(dest / "index.json", {
        "workspaces": {CHAT: {"name": "计科2201-A组", "created_at": "2026-09-15T00:00:00",
                              "migrated_from": "data"}},
        "user_last_group": {MEMBER_A: OTHER_CHAT},
    })
    migrate(src, dest, apply=True)
    index = json.loads((dest / "index.json").read_text(encoding="utf-8"))
    assert index["workspaces"][CHAT]["name"] == "计科2201-A组", "改名不许被重跑冲掉（§3.2）"
    assert index["user_last_group"][MEMBER_A] == OTHER_CHAT, "运行时的绑定不许被重跑冲掉"
    assert index["user_last_group"][MEMBER_B] == CHAT


# --------------------------------------------------------------------------
# 源盘只读 / pending_file 守卫
# --------------------------------------------------------------------------


def test_source_label_is_repo_relative_for_repo_sources(tmp_path):
    """仓库内的源根不许把机器绝对路径写进索引（换台机器就成了假信息）。"""
    assert source_label(REPO_ROOT / "data") == "data"
    assert ":" not in source_label(REPO_ROOT / "data")
    outside = tmp_path / "data"
    assert source_label(outside) == resolve_path(outside).as_posix()


def test_created_at_means_registration_time_and_survives_reruns(tmp_path):
    """`created_at` = 索引登记时刻；重跑不许把它改成后来的时间（§3.3 第 5 步的字段名）。"""
    src = make_source(tmp_path)
    dest = _dest(tmp_path)
    migrate(src, dest, apply=True, now=datetime(2026, 9, 17, 9, 0, 0))
    migrate(src, dest, apply=True, now=datetime(2026, 9, 17, 10, 0, 0))
    index = json.loads((dest / "index.json").read_text(encoding="utf-8"))
    assert index["workspaces"][CHAT]["created_at"] == "2026-09-17T09:00:00"


def test_source_root_is_never_touched(tmp_path):
    src = make_source(tmp_path)
    before = tree_digest(src)
    migrate(src, _dest(tmp_path), apply=True)
    migrate(src, _dest(tmp_path), apply=True)
    assert tree_digest(src) == before
    assert not list(src.rglob("*.tmp")), "原子写的临时文件不许落在源盘"


def test_pending_file_is_not_migrated_when_chat_id_differs(tmp_path):
    src = make_source(tmp_path, pending_chat=OTHER_CHAT)
    manifest = migrate(src, _dest(tmp_path), apply=True)
    assert manifest["pending_file"]["migrated"] is False
    assert "按会话拒掉" in manifest["pending_file"]["reason"]
    migrated_state = json.loads(
        (_dest(tmp_path) / "workspaces" / CHAT / "state.json").read_text(encoding="utf-8"))
    assert "pending_file" not in migrated_state
    assert migrated_state["group_chat_id"] == CHAT
    source_state = json.loads((src / "state.json").read_text(encoding="utf-8"))
    assert "pending_file" in source_state, "守卫只改目标侧，源盘一个字都不动"


def test_pending_file_is_migrated_when_chat_id_matches(tmp_path):
    src = make_source(tmp_path, pending_chat=CHAT)
    manifest = migrate(src, _dest(tmp_path), apply=True)
    assert manifest["pending_file"]["migrated"] is True
    migrated_state = json.loads(
        (_dest(tmp_path) / "workspaces" / CHAT / "state.json").read_text(encoding="utf-8"))
    assert migrated_state["pending_file"]["file_key"] == "file_x"


def test_empty_group_chat_id_aborts(tmp_path):
    src = make_source(tmp_path, chat_id="")
    with pytest.raises(GuardError):
        migrate(src, _dest(tmp_path), apply=True)
    assert not _dest(tmp_path).exists(), "归属不明时一个字都不许写"


# --------------------------------------------------------------------------
# Resolve-Path 守卫
# --------------------------------------------------------------------------


def test_guard_within_refuses_root_itself_and_outside(tmp_path):
    dest = _dest(tmp_path)
    dest.mkdir(parents=True)
    with pytest.raises(OutOfScope):
        guard_within(dest, dest, what="测试")
    with pytest.raises(OutOfScope):
        guard_within(dest / "workspaces" / CHAT, dest / "workspaces" / ".." / ".." / "别处", what="测试")


def test_roots_may_not_overlap(tmp_path):
    src = make_source(tmp_path)
    with pytest.raises(GuardError):
        migrate(src, src / "inner", apply=True)
    with pytest.raises(GuardError):
        migrate(src, src, apply=True)


def test_safe_key_rejects_path_traversal():
    for bad in ("..", "a/b", "a\\b", ""):
        with pytest.raises(GuardError):
            safe_key(bad)
    assert safe_key(CHAT) == CHAT


def test_resolve_path_accepts_missing_tail(tmp_path):
    target = resolve_path(tmp_path / "还没建" / "更深")
    assert target.is_absolute()
    assert target.name == "更深"
    assert target.parent == resolve_path(tmp_path) / "还没建"


# --------------------------------------------------------------------------
# 进程锁 / 回退
# --------------------------------------------------------------------------


def test_process_lock_blocks_a_live_pid(tmp_path):
    src = make_source(tmp_path)
    dest = _dest(tmp_path)
    _write(dest / "app.lock", {"pid": os.getpid(), "started_at": "2026-09-16T10:43:33", "port": 47654})
    with pytest.raises(Locked):
        migrate(src, dest, apply=True)
    assert not (dest / "workspaces").exists()
    assert check_process_lock(dest, force=True), "--force 要能跳过阻断并留一句说明"


def test_rollback_removes_workspace_and_keeps_source(tmp_path):
    src = make_source(tmp_path)
    dest = _dest(tmp_path)
    migrate(src, dest, apply=True)
    digest = tree_digest(src)
    manifest = rollback(src, dest)
    assert manifest["workspace"] == "removed"
    assert not (dest / "workspaces" / CHAT).exists()
    index = json.loads((dest / "index.json").read_text(encoding="utf-8"))
    assert CHAT not in (index.get("workspaces") or {})
    assert index.get("user_last_group") == {}, "指向死工作空间的悬挂绑定要一起摘掉"
    assert tree_digest(src) == digest
    again = rollback(src, dest)
    assert again["workspace_changes"] == 0 and again["workspace"] == "absent", "回退也要幂等"


def test_manifests_do_not_collide_across_runs_in_the_same_second(tmp_path):
    """同一秒内跑两次，两份 MANIFEST 都要留着 —— 后一次不许把前一次覆盖掉。"""
    src = make_source(tmp_path)
    dest = _dest(tmp_path)
    at = datetime(2026, 9, 17, 9, 30, 0)
    first = migrate(src, dest, apply=True, now=at)
    second = migrate(src, dest, apply=True, now=at)
    assert first["manifest_path"] != second["manifest_path"]
    assert Path(first["manifest_path"]).is_file() and Path(second["manifest_path"]).is_file()
    kept = json.loads(Path(second["manifest_path"]).read_text(encoding="utf-8"))
    assert kept["idempotent"] is True and kept["manifest_path"] == second["manifest_path"]
