"""U2 ④-a 的工作空间归属单测（§3.1 布局 / §7.2 规则 / §7.4）。

离线：不碰飞书、不碰网络、不碰 LLM；只在 `tmp_path` 上造一个假的进程根。
夹具里那句"预置索引"对应现实中的"这个群已经登记过、这几个人在里面说过话"。
"""

from datetime import datetime

import pytest

from src.gateway import workspace
from src.gateway.events import Inbound
from src.models import RubricPoint
from src.storage import INDEX, JsonStore, safe_key, workspace_dir

NOW = datetime(2026, 9, 17, 9, 0, 0)
CHAT = "oc_aaaaaa111111"
OTHER = "oc_bbbbbb222222"
ALICE = "ou_alice"


def _root(tmp_path) -> JsonStore:
    store = JsonStore(tmp_path / "data-upgrade")
    store.ensure_root_dirs()
    return store


def _inbound(text="", **over) -> Inbound:
    data = dict(
        chat_id=CHAT,
        chat_type="group",
        message_type="text",
        text=text,
        sender_type="user",
        sender_open_id=ALICE,
        message_id="m1",
        bot_mentioned=True,
    )
    data.update(over)
    return Inbound(**data)


def _fingerprint(path):
    stat = path.stat()
    return (path.read_bytes(), stat.st_mtime_ns, stat.st_size)


def test_a_group_message_binds_the_sender_and_registers_the_workspace(tmp_path):
    """一条群消息同时干两件事：记绑定（§7.2）+ 懒创建索引条目（§3.2）。"""
    store = _root(tmp_path)

    assert workspace.refresh(store, _inbound(), NOW) == CHAT

    doc = store.read_raw(INDEX)
    assert doc["user_last_group"] == {ALICE: CHAT}
    assert doc["workspaces"][CHAT] == {
        "name": "群111111",                       # 默认可读名 = 群<尾 6 位>
        "created_at": NOW.isoformat(timespec="seconds"),
    }
    assert workspace.bound_group(store, ALICE) == CHAT
    assert workspace.bound_group(store, "ou_nobody") == ""     # 没绑定 = 调用方回 NEED_GROUP
    assert workspace.bound_chats(store) == [CHAT]


def test_only_real_users_in_groups_refresh_the_binding(tmp_path):
    """判据三段：机器人自己的消息 / 私聊 / `chat_id` 空 —— 一条都不许刷（对齐卡 #1）。"""
    store = _root(tmp_path)

    assert workspace.refresh(store, _inbound(sender_type="app"), NOW) == ""
    assert workspace.refresh(store, _inbound(chat_type="p2p", chat_id=ALICE), NOW) == ""
    assert workspace.refresh(store, _inbound(chat_id=""), NOW) == ""
    assert workspace.refresh(store, _inbound(sender_open_id=""), NOW) == ""

    assert not (store.root / INDEX).exists(), "一次都没刷新 ⇒ 索引文件都不该出现"


def test_the_binding_moves_to_the_last_group_that_spoke(tmp_path):
    """单值映射：后发言的群胜出（L4 = 一个群一份作业，同一时刻只有一个活跃工作空间）。"""
    store = _root(tmp_path)

    workspace.refresh(store, _inbound(chat_id=CHAT), NOW)
    workspace.refresh(store, _inbound(chat_id=OTHER), NOW)

    assert workspace.bound_group(store, ALICE) == OTHER
    assert workspace.bound_chats(store) == [CHAT, OTHER]


def test_refresh_does_not_touch_the_file_when_nothing_changed(tmp_path):
    """`index.json` 是全局热点（§7.3）⇒ 走条件写：同一个人同一个群，字节与 mtime 都不动。"""
    store = _root(tmp_path)
    workspace.refresh(store, _inbound(), NOW)
    path = store.root / INDEX
    before = _fingerprint(path)

    assert workspace.refresh(store, _inbound(), NOW) == CHAT

    assert _fingerprint(path) == before


def test_store_for_is_the_workspace_directory_and_is_writable(tmp_path):
    """`store_for()` 就是"换个根换一个数据域"：写进去的文件落在 workspaces\\<chat_id>\\。"""
    store = _root(tmp_path)
    ws = workspace.store_for(store.root, CHAT)

    assert ws.root == workspace_dir(store.root, CHAT)
    assert (ws.root.parent.name, ws.root.name) == ("workspaces", CHAT)

    ws.save_rubric([RubricPoint(id="R1", quote="原文", observable="可核对")])
    assert (store.root / "workspaces" / CHAT / "rubric.json").is_file()
    assert [p.id for p in ws.load_rubric()] == ["R1"]


def test_safe_key_is_the_same_guard_as_the_migration_tool(tmp_path):
    """运行时与迁移工具共用一条正则 —— 工具建的目录名，运行时必须按同一个 chat_id 找回来。"""
    from tools.migrate_workspace import GuardError, safe_key as tool_safe_key

    assert safe_key(CHAT) == tool_safe_key(CHAT) == CHAT
    for bad in ("..", "a/b", "a\\b", ""):
        with pytest.raises(ValueError):
            safe_key(bad)
        with pytest.raises(GuardError):
            tool_safe_key(bad)