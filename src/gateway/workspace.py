"""U2 工作空间归属（§3.1 布局 / §7.2 规则 / §7.4 未验证）—— 纯函数 + 一个 store 工厂。

两件事：

  1. **绑定表**：`index.json` 的 `user_last_group[sender_open_id] = 群 chat_id`。私聊消息
     没有"我是哪个群的"，靠这张**单值映射**找归属（L4 = 一个群一份作业 ⇒ 同一时刻只有
     一个"最近活跃工作空间"，单值天然无歧义，§7.2）。
  2. **选数据域**：群消息取 `inbound.chat_id`（零歧义，不看绑定）；私聊取绑定。
     选定之后 `JsonStore(root/workspaces/<chat_id>)` 就是那个群的数据域 —— `JsonStore`
     的语义没变（换个根 = 换一个数据域），变的是"谁来选根"。

三条硬口径（对齐卡 §5 的签字，别改）：

  * 刷新判据照 `_remember_group()` 现成的三段：`sender_type == "app"` 排除、
    `chat_type == "group"`（**不是**"不是私聊"）、`chat_id` 非空。
  * **被 @ 门禁静默的消息也算互动**，文件 / 图片消息也算（都是人在群里说话）。所以刷新
    在 app 层 `handle()` 里、`route()` **之前**：文件 / 图片在 `route()` 第一段就 return 了，
    写在文本路径里反而让"投过作业书的人"建不上绑定。
  * `state.group_chat_id` **不再是归属依据**（保留只读 + 旧数据兼容，对齐卡 #6）；
    新写入路径一处都不许再写它。
"""

from __future__ import annotations

from datetime import datetime

from src.gateway.events import Inbound
from src.storage import INDEX, JsonStore, safe_key, workspace_dir

__all__ = [
    "is_interaction",
    "read_index",
    "refresh",
    "bound_group",
    "bound_chats",
    "store_for",
]


def is_interaction(inbound: Inbound) -> bool:
    """这条消息算不算"某个人在某个群里活动"（刷新绑定的判据）。"""
    return bool(
        inbound.sender_open_id
        and inbound.sender_type != "app"
        and inbound.chat_type == "group"
        and inbound.chat_id
    )


def read_index(store: JsonStore) -> dict:
    """进程根的 `index.json`（读不出来就 `{}`）—— 归属的唯一真源。"""
    doc = store.read_raw(INDEX, {}) or {}
    return doc if isinstance(doc, dict) else {}


def refresh(store: JsonStore, inbound: Inbound, now: datetime | None = None) -> str:
    """任何**真实用户**的群消息 ⇒ `user_last_group[sender] = chat_id`；返回刷新的群。

    没刷新（机器人自己的消息 / 私聊 / `chat_id` 空）返回 `""`。
    懒创建（§3.2）：这个群第一次露面时补一条
    `workspaces[chat_id] = {name: 群<尾 6 位>, created_at: 首次互动时刻}`。
    写盘走 `JsonStore.mutate_raw()` 的条件写：值没变就一个字节都不动（`index.json`
    是全局热点，§7.3）。
    """
    if not is_interaction(inbound):
        return ""
    chat_id = safe_key(inbound.chat_id)
    sender = inbound.sender_open_id
    stamp = (now or datetime.now()).isoformat(timespec="seconds")

    def touch(doc):
        data = dict(doc) if isinstance(doc, dict) else {}
        last = dict(data.get("user_last_group") or {})
        spaces = dict(data.get("workspaces") or {})
        if last.get(sender) == chat_id and chat_id in spaces:
            return data                      # 值没变：交给条件写去"不落盘"
        last[sender] = chat_id
        spaces.setdefault(chat_id, {"name": _default_name(chat_id), "created_at": stamp})
        data["user_last_group"] = last
        data["workspaces"] = spaces
        return data

    store.mutate_raw(INDEX, touch, default={})
    return chat_id


def bound_group(store: JsonStore, sender_open_id: str) -> str:
    """这个人最近活跃的群；没有绑定 = `""`（调用方按 §7.2 回 `NEED_GROUP`）。"""
    return str((read_index(store).get("user_last_group") or {}).get(sender_open_id or "") or "")


def bound_chats(store: JsonStore) -> list[str]:
    """索引里登记过的全部工作空间 key（定时器要遍历它们 —— 一个进程管多个群）。"""
    return sorted((read_index(store).get("workspaces") or {}))


def store_for(root, chat_id: str) -> JsonStore:
    """某个群的数据域（§3.1 第二段）。目录不必先存在 —— 写第一份文件时自然建。"""
    return JsonStore(workspace_dir(root, chat_id))


def _default_name(chat_id: str) -> str:
    """可读名的默认值（§3.2）：`群<chat_id 尾 6 位>`；首份作业书解析成功后由索引改写。"""
    return f"群{str(chat_id)[-6:]}"