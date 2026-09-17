"""M0 组装与入口 —— 依赖注入 + ``main()``。

依据：M0 网关方案 §2 / §6 / §7 / §10 / §12。

两条纪律写在这里：
  * **回调里不干重活**（方案 §6）：``on_event`` 只做"路由 + 回话"，M1/M3 那种 10–30 秒
    的活丢后台线程，否则长连接的事件循环被堵住、消息收不到；
  * **判定只有一处**：路由判定在 ``router.py``、覆盖率判定在 ``intelligence/``，
    本文件只做组装、落盘与异常转文案。
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from src.config import ConfigError, load_config
from src.gateway import allocation, change, reminder, replies, vote, workspace
from src.gateway.client import FeishuClient
from src.gateway.events import ImageOut, Inbound, Outcome, Reply, reply, to_inbound
from src.gateway.router import route
from src.intelligence.coverage import coverage_loop
from src.intelligence.workload import check_workload, decompose_workload
from src.intelligence.decompose import DecomposeResult, check, decompose
from src.intelligence.direction import generate_directions
from src.intelligence.extract import (
    ExtractError,
    check_deadline,
    check_radical_residue,
    check_weight_sum,
    extract_text,
)
from src.intelligence.llm import LLMClient, LLMError
from src.intelligence.parse import parse_assignment
from src.models import AssignmentRecord, ChangeRecord, Preference, Roster
from src.report.checklist import render_checklist, render_workload_checklist
from src.report.gantt import render_gantt
from src.storage import (
    ASSIGNMENTS,
    CHANGES,
    GANTT,
    PREFERENCES,
    PROPOSALS,
    REMINDERS,
    REPORT,
    SEEN,
    JsonStore,
)

__all__ = ["Gateway", "main"]

# data/seen.json 只留最近这么多条 message_id（P0-A）。
_SEEN_LIMIT = 200

# 单实例保护的守护端口（P0-E）：第二个进程 bind 不上就拒绝启动。
# 用 GATEWAY_LOCK_PORT 覆盖：升级版与 MVP 要同时跑，必须各占一个端口（requirements-upgrade 第4节）。
INSTANCE_PORT = int(os.environ.get("GATEWAY_LOCK_PORT", 47653))
LOCK_FILE = "app.lock"


def _stamp() -> str:
    """日志时间戳（P1-J）：明天复盘要靠它把两个进程的行对齐。"""
    return datetime.now().isoformat(timespec="seconds")


def _mentions_log(mentions) -> str:
    """@ 结构的原文映射（PM 2026-09-17 收）：``key>open_id``，@ 到机器人的那一下标 ``(bot)``。

    为什么要有它：@ 相关的问题此前只能靠回显反推 —— 2026-09-17 10:48:58「组员行 @ 了两个人
    只认一个」就是推出来的结论，因为原始 ``mentions`` 没留痕。没有 @ 记 ``-``（别留空，
    空值看着像被截断）。
    """
    if not mentions:
        return "-"
    parts = []
    for mention in mentions:
        bot = "(bot)" if mention.is_bot else ""
        parts.append(f"{mention.key or '?'}>{mention.open_id or '?'}{bot}")
    return ",".join(parts)


class SingleInstance:
    """单实例保护（P0-E）—— 机器上只允许跑一个网关。

    真机故障：同时跑了两个 `python -m src.gateway.app`，同一套凭据 → 两条
    WebSocket → 每条群消息被两个进程各处理一次（重复回话、落盘互相覆盖）。
    `message_id` 去重（P0-A）对两个进程只能偶尔挡住（各读各的 seen.json，有竞态），
    所以要在**进程级**互斥。

    Windows 上按 pid 判存活不安全（`os.kill(pid, 0)` 会真的把进程杀掉），所以
    守卫用 **bind 127.0.0.1:<port>** —— bind 是原子的，第二个实例必然失败。
    `data/app.lock` 只写来给人看（pid / started_at），**不参与判定**：硬退
    （`os._exit`）留下的残留锁文件不会挡住下一次启动。
    """

    def __init__(self, data_dir, port: int = INSTANCE_PORT) -> None:
        self.path = Path(data_dir) / LOCK_FILE
        self.port = port
        self._sock: socket.socket | None = None

    def acquire(self) -> bool:
        """``True`` = 抢到；``False`` = 已有实例在跑，别启动。"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", self.port))
        except OSError:
            sock.close()
            return False
        self._sock = sock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"pid": os.getpid(), "started_at": _stamp(), "port": self.port},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return True

    def release(self) -> None:
        """正常退出：放掉端口 + 删锁。"""
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def describe(self) -> str:
        """把现有锁文件读成人话，给拒绝启动时的那行错误用。"""
        try:
            return self.path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""


class Gateway:
    """把连接层、纯路由、落盘、智能层接起来。全是依赖注入，方便离线测。"""

    def __init__(self, config, store, sender, downloader, llm_client=None) -> None:
        # U2（§3.1）：传进来的是**进程根** store —— 它只该装 index.json（归属绑定）与
        # app.lock。每个群的数据域在 workspaces\<chat_id>\，由 handle() 按消息选
        # （workspace.store_for），请求路径上的读写一律走选出来的那个 store。
        self.config = config
        self.store = store
        self.sender = sender
        self.downloader = downloader
        self._llm_client = llm_client

    # ---------- 飞书回调入口 ----------

    def on_event(self, data) -> None:
        """回调绝不能被业务异常搞崩 —— 崩了长连接还在，但消息就静默丢了。"""
        try:
            self.handle(to_inbound(data, bot_open_id=self.config.feishu_bot_open_id))
        except Exception as exc:
            print(
                f"[M0] 处理事件出错（已忽略）：{type(exc).__name__}: {exc}", file=sys.stderr
            )

    def handle(self, inbound: Inbound) -> Outcome:
        """快路径：**先选工作空间** → 路由 → 回话 → 落盘 → 需要时起后台重活。

        第一步是**选 root**（U2 / §3.1）：群消息用 `inbound.chat_id`；私聊用
        `index.json` 的 `user_last_group` 绑定（§7.2）。群消息顺手刷新绑定 ——
        **被 @ 门禁静默的、文件 / 图片的都算互动**（都是人在群里说话）。
        两个都拿不到（私聊且从没在群里互动过）⇒ 回 `NEED_GROUP`，不猜、不落盘、不起重活。

        第二步是**按 message_id 去重**（P0-A）：飞书会重复投递 / 重连补投同一个
        事件，不去重就会把同一条指令完整跑两遍（新群"先清单、再总表"就是这么来的）。
        重复事件直接丢掉：不发消息、不写业务数据。

        每条消息先打一行日志（P1-G）：真机出问题时先看这一行，否则永远是黑盒。
        """
        print(
            f"[M0] {_stamp()} recv id={inbound.message_id} chat={inbound.chat_id} "
            f"from={inbound.sender_open_id} type={inbound.message_type} "
            f"mentions={_mentions_log(inbound.mentions)} "
            f"text={inbound.text[:40]}"
        )
        # 第一步：**选工作空间**（U2 / §3.1）。群消息零歧义，用这条消息的 chat_id；
        # 顺手刷新绑定（被门禁静默的、文件 / 图片的都算互动 —— 所以放在 route() 之前）。
        # 私聊没有"我是哪个群的"：查 index.json 的绑定表（§7.2）。
        group = inbound.chat_id if inbound.chat_type == "group" else ""
        workspace.refresh(self.store, inbound)
        if not group:
            group = workspace.bound_group(self.store, inbound.sender_open_id)
        if not group:
            # §7.2 第 2 行：从没在任何群里互动过 ⇒ 不知道归属，**不猜**（不落盘、不起
            # 重活，只回一句）。没有工作空间也就没有 seen.json 可记，所以这条分支不去重：
            # 重复投递顶多多回一句 NEED_GROUP，没有副作用。
            print(f"[M0] {_stamp()} none 没有绑定 id={inbound.message_id}")
            self._send(reply(inbound, replies.NEED_GROUP))
            return Outcome()
        store = workspace.store_for(self.store.root, group)

        # 第二步：按 message_id 去重（P0-A）—— 去重表在工作空间里（§3.1 的 seen.json）。
        if self._is_duplicate(inbound.message_id, store):
            # 去重命中也要留痕，否则看不出到底有没有重复投递（P1-G / P0-A）
            print(f"[M0] {_stamp()} dup 跳过 id={inbound.message_id}")
            return Outcome()
        state = store.load_state()
        # U3（§6.1）：总开关 = **存在 ≥1 条 status="normal"**，不是"列表非空" ——
        # "非空但全是 ambiguous" 是真实可达形态，必须归入无评分点链路（否则分母 0
        # 会伪装成"覆盖率 0%"，撞上 D-48 的"不计算 ≠ 算出来是 0"）。
        has_rubric = any(point.status == "normal" for point in store.load_rubric())
        meta = store.load_assignment()
        outcome = route(
            inbound,
            state,
            store.load_members(),
            has_rubric=has_rubric,
            cards=store.load_cards(),
            preferences=store.load_preferences(),
            assignments=store.load_assignments(),
            # U6 的"覆盖已定方向要组长确认"要看盘上有没有已落定方向（§5.3）——
            # 读盘归 app 层，判定仍在纯函数里
            direction=store.load_direction(),
            source_title=meta.title if meta else "",
            # U2：归属群由 app 层选好（群消息 = 这条消息的 chat_id；私聊 = 绑定表）
            group_chat_id=group,
        )
        failures = self._deliver(outcome, store)
        # 主动私聊发不出去要说出来（P0-C）：否则"群里说清单已发、实际没人收到"。
        self._report_dm_failures(failures, outcome.state or state, group=group)

        # 重活起不起，route() 已经判过（Outcome.pipeline）—— 这里不再自己判一遍，
        # 否则"回了「表单没看懂」却照样跑 M1"（必修 4）
        if outcome.pipeline:
            threading.Thread(
                target=self.run_pipeline,
                args=(outcome.pipeline, inbound, state, store),
                daemon=True,
            ).start()
        return outcome

    def _is_duplicate(self, message_id: str, store: JsonStore) -> bool:
        """P0-A：同一条消息只处理一次。落**该工作空间**的 ``seen.json``，只留最近
        ``_SEEN_LIMIT`` 条（去重表跟数据同域，U2 之后一个进程管多个群）。

        ``message_id`` 为空（老事件 / 单测夹具）时不去重 —— 没有标识就没法认人。
        """
        if not message_id:
            return False
        seen = store.read_raw(SEEN, []) or []
        if message_id in seen:
            return True
        store.mutate_raw(
            SEEN, lambda items: [*(items or []), message_id][-_SEEN_LIMIT:], default=[]
        )
        return False

    def _send(self, message: Reply):
        """发一条并打一行轨迹（P1-J）。返回 ``None`` = 成功，否则返回异常。"""
        try:
            self.sender.send(message)
        except Exception as exc:
            print(
                f"[M0] {_stamp()} -> {message.receive_id_type}:{message.chat_id} "
                f"失败({type(exc).__name__}: {exc}) | {message.text[:40]}"
            )
            return exc
        print(
            f"[M0] {_stamp()} -> {message.receive_id_type}:{message.chat_id} "
            f"ok | {message.text[:40]}"
        )
        return None

    def _deliver(self, outcome: Outcome, store: JsonStore) -> tuple[Reply, ...]:
        """发出所有回复，返回**发失败的**那些（P0-C）。每条都打一行轨迹（P1-J）。

        U4 变更**先落盘、再播报**（§8.2 写序的配套）：没写成就别宣布 —— 认领竞态
        （``expect_empty`` 在锁内不成立）时改发第 16 条那句，群里不会出现假公示。
        """
        failed: list[Reply] = []
        pending: tuple[Reply, ...] = outcome.replies
        if outcome.save_change is not None:
            written, owner = self._save_change(store, outcome.save_change)
            if not written and owner:
                pending = self._conflict_replies(store, outcome.save_change, owner)
        for message in pending:
            # 一条发失败不能吃掉后面几条：M4 开窗口要连发"清单发群 + 每人私聊"，
            # 某个人的私聊发不出去，群里的清单必须照发（方案 §7：不能静默失败）。
            if self._send(message) is not None:
                failed.append(message)
        if outcome.state is not None:
            store.save_state(outcome.state)
        if outcome.save_roster is not None:
            store.save_members(Roster.from_dict(outcome.save_roster))
        if outcome.save_preference is not None:
            self._save_preference(store, outcome.save_preference)
        if outcome.save_assignments:
            self._save_assignments(store, outcome.save_assignments)
        if outcome.save_proposal is not None:
            self._save_proposal(store, outcome.save_proposal)
        if outcome.save_direction is not None:
            self._save_direction(store, outcome.save_direction)
        if outcome.save_complete is not None:
            self._save_complete(store, outcome.save_complete)
        if outcome.save_change is not None:
            self._save_change(store, outcome.save_change)
        for image in outcome.images:                 # M7 甘特图：文本先发、图后发
            if self._send_image(image) is not None:  # 图发失败要在群里说（必修 D）
                self._send(Reply(chat_id=image.chat_id, text=replies.IMAGE_SEND_FAILED))
        return tuple(failed)

    def _report_dm_failures(self, failures, state, group: str = "") -> None:
        """私聊发不出去就在群里补一句（P0-C）。只统计 ``open_id`` 目标 —— 那才是"人"。

        群取**志愿窗口自己记的** chat_id（P1-H），取不到再用 app 层选好的归属群（U2）；
        两处都不读 `state.group_chat_id` —— 那个字段 U2 起只读、停更（对齐卡 #6）。
        """
        dm_failed = [r for r in failures if r.receive_id_type == "open_id"]
        pref = (state or {}).get("preference") or {}
        group = pref.get("chat_id") or group or ""
        if not dm_failed or not group:
            return
        self._send(
            Reply(
                chat_id=group,
                text=replies.PREFERENCE_DM_FAILED.format(count=len(dm_failed)),
            )
        )

    # ---------- M4 / M5 的落盘 ----------

    def _save_preference(self, store: JsonStore, payload: dict) -> None:
        """按 ``user_id`` **覆盖**写志愿（后投覆盖先投，D-33 / §6.3）。

        走 ``mutate_many``：它是"类型化列表的原子读-改-写"，正是为 M4 收志愿准备的
        原语 —— 两个组员同时私聊回复时不会丢更新。
        """
        preference = Preference.from_dict(payload)
        store.mutate_many(
            PREFERENCES,
            Preference,
            lambda items: [p for p in items if p.user_id != preference.user_id] + [preference],
        )

    def _save_assignments(self, store: JsonStore, payloads) -> None:
        """M4 结算：**只填没人负责的卡 / 只新增卡**，不整份覆盖（§8.2 v1.8 / §8.4）。

        结算曾是这条链上唯一没有读-改-写保护的地方（``save_assignments()`` 整份覆盖）
        ⇒ 人工改派 / 认领 / 完成标记会被下一次结算冲掉。现在走 ``mutate_many()`` 的
        锁内读-改-写，逐条判：

          * 卡不在盘上 → **新增**（新作业书多出来的卡）；
          * 盘上那张**没有负责人**（未分配 / 回流）→ 填上负责人与来源；
          * 盘上那张**已有人负责** → **一个字都不动**（人工修订 / 执行期证据优先，D-67）。

        ``completed_at`` 因此天然保住：改过人的卡根本不会走到这里被覆盖。
        """
        incoming: dict[str, AssignmentRecord] = {}
        for payload in payloads:
            record = AssignmentRecord.from_dict(payload)
            incoming[record.task_id] = record

        def merge(items: list) -> list:
            new_items = list(items)
            for index, record in enumerate(new_items):
                fresh = incoming.get(record.task_id)
                if fresh is not None and not record.assignee:
                    new_items[index] = replace(
                        record, assignee=fresh.assignee, source=fresh.source
                    )
            known = {record.task_id for record in new_items}
            new_items.extend(
                record for task_id, record in incoming.items() if task_id not in known
            )
            return new_items

        store.mutate_many(ASSIGNMENTS, AssignmentRecord, merge)

    def _save_proposal(self, store: JsonStore, payload: dict) -> None:
        """追加一条提议 —— **含真实 ``user_id``**，这是防滥用留痕（§6.5）。

        ``proposals.json`` 的字段级定义在 requirements 里没有（§6.5 只规定了语义），
        所以走裸 JSON 的原子读-改-写，不硬造数据类。
        """
        store.mutate_raw(PROPOSALS, lambda items: [*(items or []), payload], default=[])

    def _save_direction(self, store: JsonStore, payload: dict) -> None:
        """整份方向结果一次性覆盖（M2 落定，§2.6）—— 裸 JSON，口径同 proposals.json。"""
        store.save_direction(payload)

    def _save_complete(self, store: JsonStore, payload: dict) -> None:
        """M6 的完成标记（§2.1）：走 ``mutate_many`` **只改那一条**，其余原样。

        两件事都写进 ``assignments.json`` 的同一行，所以必须走那个"类型化列表的原子
        读-改-写"原语 —— 直接整份覆盖会把别人刚标的完成擦掉。
        """
        task_id = payload.get("task_id")
        completed_at = payload.get("completed_at")
        store.mutate_many(
            ASSIGNMENTS,
            AssignmentRecord,
            lambda items: [
                replace(record, completed_at=completed_at)
                if record.task_id == task_id
                else record
                for record in items
            ],
        )

    def _conflict_replies(
        self, store: JsonStore, payload: dict, owner: str
    ) -> tuple[Reply, ...]:
        """认领竞态（§9.1 第 16 条）：卡在锁内被先到者接走 ⇒ 改发那句，不发假公示。

        人名在这里现读花名册解析 —— router 是纯函数，手里没有"锁内那一刻"的花名册。
        """
        fallback = payload.get("fallback")
        if not fallback:
            return ()
        return (
            Reply(
                chat_id=fallback["chat_id"],
                text=fallback["template"].format(
                    name=change.name_of(store.load_members(), owner),
                    **(fallback.get("fields") or {}),
                ),
            ),
        )

    def _save_change(self, store: JsonStore, payload: dict) -> tuple[bool, str]:
        """U4 变更落盘（§8.2）：一次变更 = 台账 + 状态，**锁内两写、先台账后状态**。

        返回 ``(写了没, 这张卡现在的负责人)`` —— 认领竞态（``expect_empty``）的后到者
        拿到 ``(False, 先到者)``，由调用方照 §9.1 第 16 条回话（人名是事实槽位，原样注入）。
        """
        update = payload.get("update") or {}
        return store.mutate_change(
            ChangeRecord.from_dict(payload["change"]),
            update.get("task_id", ""),
            update.get("assignee", ""),
            update.get("source"),
            expect_empty=bool(update.get("expect_empty")),
        )

    def _send_image(self, image: ImageOut):
        """发一张图并打一行轨迹（P1-J）。返回 ``None`` = 成功，否则返回异常。"""
        try:
            self.sender.send_image(image.chat_id, image.path, image.receive_id_type)
        except Exception as exc:
            print(
                f"[M0] {_stamp()} -> {image.receive_id_type}:{image.chat_id} "
                f"图片失败({type(exc).__name__}: {exc}) | {image.path}"
            )
            return exc
        print(
            f"[M0] {_stamp()} -> {image.receive_id_type}:{image.chat_id} "
            f"图片 ok | {image.path}"
        )
        return None

    # ---------- 慢路径：M1 / M2 / M3 ----------

    def run_pipeline(self, kind: str, inbound: Inbound, state: dict, store: JsonStore) -> None:
        """后台线程里跑。异常一律转成一句人话回群里（方案 §7：不能静默失败）。

        回话一律走 ``_send()``（P1-J）：它不抛异常、失败也留轨迹 —— 否则
        "except 里再发一次、再失败"会让整条后台线程静默死掉，屏幕上什么都看不到。
        """
        try:
            if kind == "assignment":
                self._run_assignment(inbound, state, store)
            elif kind == "decompose":
                self._run_decompose(inbound, store)
            elif kind == "direction":
                self._run_direction(inbound, store)
            elif kind == "report":
                self._run_report(inbound, store)
        except ExtractError as exc:
            self._send(reply(inbound, replies.EXTRACT_REJECTED.format(reason=exc)))
        except LLMError as exc:
            # 群里只回一句人话；**病因打在 stderr**（2026-09-17 真机：只看到「没解析出来」
            # 时无从定位，逐次失败的原因由 LLMClient 的 [LLM] 行给出）
            print(f"[M0] {_stamp()} LLM 失败（{kind}）：{exc}", file=sys.stderr)
            self._send(reply(inbound, replies.parse_failed(inbound.chat_type)))
        except Exception as exc:                      # 兜底也要说话
            self._send(
                reply(inbound, f"{replies.parse_failed(inbound.chat_type)}（{type(exc).__name__}）")
            )
        finally:
            if kind == "assignment":
                pending = (state or {}).get("pending_file") or {}
                self._forget_pending_file(pending.get("message_id", ""), store)

    def _run_assignment(self, inbound: Inbound, state: dict, store: JsonStore) -> None:
        """作业书 → 下载 → 抽文本 → M1 → **必须续跑 M3** → 核对清单发群（方案 §7）。"""
        pending = (state or {}).get("pending_file") or {}
        path = self.downloader.download(pending, store.uploads)

        text = extract_text(path)
        parsed = parse_assignment(text, self._llm(), source_file=path.name)

        # 空 rubric：M1 全文没找到评分标准（D-48）→ 不跑 M3、不拿正文要求凑数，
        # 也**一个字都不落盘** —— 否则拒拆会把上一份好产物清空（D-49 ②）。
        normal = [point for point in parsed.points if point.status == "normal"]
        if not normal:
            # U3（§6.1 / §6.5）：空列表与"全是 ambiguous"走**同一条**工作量链路。
            # 与旧行为的区别只有一个：不再是死路（拒拆），但也不碰覆盖率。
            self._run_workload(inbound, text, parsed, store)
            return

        # 三份产物必须**一起**落盘（F2）：M3 抛错时若 M1 的产物已经写下去，
        # 盘上就会留下“新 rubric + 旧 cards”的混用快照，下一轮「拆解」会拿新评分点去配旧卡。
        # 所以 decompose() 成功之后再一次性写完；失败就保持上一份快照不动。
        result = decompose(parsed.points, self._llm())
        store.save_assignment(parsed.meta)
        store.save_rubric(list(parsed.points))
        store.save_cards(list(result.cards))

        report = render_checklist(parsed.meta, parsed.points, result.cards, result)
        # 三道软校验都只警告、不拒收（§7.5）：权重加总 + D-43 的部首残留 + D-49 的截止时间。
        warnings = [
            w
            for w in (
                check_weight_sum(parsed.points),
                check_radical_residue(text),
                check_deadline(parsed.meta),
            )
            if w
        ]
        if warnings:
            report += "\n\n" + "\n".join(f"[软警告] {w}" for w in warnings)
        self._send(reply(inbound, report))

    def _run_workload(
        self, inbound: Inbound, text: str, parsed, store: JsonStore
    ) -> None:
        """U3 无评分点链路：正文 → 工作量卡 → 核对清单发群（§6.2）。

        落盘口径与评分点链路**同一套 F2 约束**：三份产物一起写，免得盘上留下
        "新 rubric + 旧 cards" 的混用快照。``rubric.json`` 记的是这份作业书里
        **真实的**评分点（可能为空 / 全是 ambiguous）—— 一个凑数点都不加（§6.2 红线）。
        """
        result = decompose_workload(text, self._llm())
        store.save_assignment(parsed.meta)
        store.save_rubric(list(parsed.points))
        store.save_cards(list(result.cards))

        report = render_workload_checklist(parsed.meta, result.cards, result)
        # 三道软校验同评分点链路（§7.5）：只警告、不拒收
        warnings = [
            w
            for w in (
                check_weight_sum(parsed.points),
                check_radical_residue(text),
                check_deadline(parsed.meta),
            )
            if w
        ]
        if warnings:
            report += "\n\n" + "\n".join(f"[软警告] {w}" for w in warnings)
        self._send(reply(inbound, report))

    def _run_decompose(self, inbound: Inbound, store: JsonStore) -> None:
        """「拆解」：用现有评分点重跑 M3，再出一份核对清单。"""
        points = store.load_rubric()
        if not any(point.status == "normal" for point in points):
            # §6.1 同一把尺子：没有可拆点就没有"用现有评分点重拆"这回事 ——
            # 回重试入口（跟 router 那句同源），不烧 token、不写盘（防覆盖率 0/0）
            self._send(reply(inbound, replies.needs_rubric(inbound.chat_type)))
            return
        result = decompose(points, self._llm())
        store.save_cards(list(result.cards))

        meta = store.load_assignment()
        if meta is None:
            coverage = coverage_loop(result.cards, points)
            self._send(
                reply(
                    inbound,
                    f"拆解完成：{len(result.cards)} 张任务卡，"
                    f"覆盖率 {len(coverage.covered)}/{len(coverage.eligible)}。",
                )
            )
            return
        self._send(
            reply(inbound, render_checklist(meta, points, result.cards, result))
        )

    def _run_direction(self, inbound: Inbound, store: JsonStore) -> None:
        """「方向」：评分点 → 2–3 个候选（M2 唯一的 LLM 点）→ 开投票窗口发群（§2.2）。

        前置缺哪个就回哪句、不发候选：与 router 的判定口径一致（必修 4）。
        开窗时**重新读一次 state**（生成要花十几秒），别拿十几秒前的快照覆盖回盘 ——
        不然这期间别人刚建的花名册 / 窗口会被一起写没。
        """
        points = store.load_rubric()
        if not any(point.status == "normal" for point in points):
            # U3（PM 裁 ①）：没有可拆评分点 ⇒ 不出候选，引导人工拍板（与 router 同源）
            self._send(reply(inbound, replies.vote_no_rubric(inbound.chat_type)))
            return
        roster = store.load_members()
        if roster is None or not roster.members:
            self._send(reply(inbound, replies.VOTE_NEED_ROSTER))
            return
        try:
            result = generate_directions(points, store.load_assignment(), self._llm())
        except LLMError:
            # 生成不出来就直说，别让群里干等（也不套用「作业书解析失败」那句不对路的兜底）
            self._send(reply(inbound, replies.VOTE_GENERATE_FAILED))
            return
        if not result.ok:
            self._send(reply(inbound, replies.VOTE_GENERATE_FAILED))
            return
        outcome = vote.open_window(
            inbound,
            store.load_state(),
            [direction.to_dict() for direction in result.directions],
        )
        failures = self._deliver(outcome, store)
        self._report_dm_failures(failures, outcome.state or {}, group=inbound.chat_id)

    def _run_report(self, inbound: Inbound, store: JsonStore) -> None:
        """M7 执行报告（D-64 / D-65）：分配总表 + 核对清单 + 甘特图，发群。

        报告是**从盘上重读的快照**：自检项按现状重算（``generations=0`` —— 报告不是拆解，
        没有"这一版拆了几轮"这回事）。文本落 ``data/report.md``、图落 ``data/gantt.png``。
        """
        meta = store.load_assignment()
        points = store.load_rubric()
        cards = store.load_cards()
        assignments = store.load_assignments()
        roster = store.load_members()
        # U3（PM 裁 ②）：**只换覆盖率那一段** —— 总表 / 核对清单 / 甘特图三件套照旧，
        # 所以这里不再要求"有评分点"（工作量链路里 rubric.json 可能就是空的）。
        if meta is None or not cards or not assignments:
            self._send(reply(inbound, replies.REPORT_NEED_ASSIGNMENTS))
            return
        normal = [point for point in points if point.status == "normal"]
        result = DecomposeResult(
            cards=tuple(cards),
            failures=tuple(
                check(cards, points) if normal else check_workload(cards)
            ),
            generations=0,
        )
        try:
            gantt = render_gantt(cards, assignments, meta, store.path(GANTT), roster)
        except Exception as exc:                     # 渲染崩了也要说话（方案 §7）
            print(f"[M0] {_stamp()} 甘特图渲染失败：{type(exc).__name__}: {exc}", file=sys.stderr)
            self._send(reply(inbound, replies.REPORT_FAILED))
            return

        # 拼成一条长文本客户端会折叠 → 拆成「总表」「核对清单」两条（必修 F）；
        # data/report.md 仍是两份拼起来的完整版。
        board_text = allocation.render_board(
            assignments,
            cards,
            roster,
            store.load_preferences(),
            show_completion=True,
        )
        checklist_text = (
            render_checklist(
                meta, points, cards, result, assignments=assignments, roster=roster
            )
            if normal
            else render_workload_checklist(
                meta, cards, result, assignments=assignments, roster=roster
            )
        )
        store.path(REPORT).write_text(
            board_text + "\n\n" + checklist_text + "\n", encoding="utf-8"
        )
        self._deliver(
            Outcome(
                replies=(
                    Reply(chat_id=inbound.chat_id, text=board_text),
                    Reply(chat_id=inbound.chat_id, text=checklist_text),
                ),
                images=(ImageOut(chat_id=inbound.chat_id, path=str(gantt)),),
            ),
            store,
        )

    def _forget_pending_file(self, file_message_id: str, store: JsonStore) -> None:
        """只清**这一轮消费掉的那个文件**（按 message_id 认）。

        跑 M1 的十几秒里群里可能又来了新 PDF：无脑 pop 会把新文件一起删掉，之后
        「作业书」回「请先把作业书文件发给我」—— 用户明明刚发过（必修 5）。
        成败都清（不留旧文件），但只在还是同一个文件时才清。
        """
        state = store.load_state()
        pending = state.get("pending_file") or {}
        if (pending.get("message_id") or "") != (file_message_id or ""):
            return
        state.pop("pending_file", None)
        store.save_state(state)

    # ---------- 慢路径的定时器：M6 催办 ----------

    def scan_reminders(self, now: datetime | None = None) -> list:
        """M6 临期扫描一轮（§2.2）：发群 @负责人，成败都记该工作空间的 ``reminders.json``。

        U2（§3.1）：一个进程管**多个**工作空间 ⇒ 遍历索引里登记过的每个群各扫一遍；
        群标识 = 工作空间 key（新布局下 key 就是群 chat_id，零歧义，不再读
        `state.group_chat_id`）。一个群都没有就什么都不做（还没人说过话）。
        去重靠 ``(task_id, tier)``（见 ``reminder.scan``）。
        """
        _, tier1, tier2 = reminder.settings()
        due: list = []
        for group in workspace.bound_chats(self.store):
            store = workspace.store_for(self.store.root, group)
            found = reminder.scan(
                store.load_cards(),
                store.load_assignments(),
                store.load_assignment(),
                store.read_raw(REMINDERS, []) or [],
                now,
                tier1_hours=tier1,
                tier2_hours=tier2,
            )
            for item in found:
                ok = self._send(Reply(chat_id=group, text=item.text)) is None
                record = item.to_record(group, _stamp(), ok)
                store.mutate_raw(
                    REMINDERS, lambda items, row=record: [*(items or []), row], default=[]
                )
            due.extend(found)
        return due

    def start_reminder_loop(self) -> None:
        """后台线程：**启动先扫一次**（演示不必干等一个钟头），之后按间隔循环（§2.2）。"""
        interval, _, _ = reminder.settings()

        def _loop() -> None:
            while True:
                try:
                    self.scan_reminders()
                except Exception as exc:             # 扫一轮出错不能把线程搞死
                    print(f"[M6] {_stamp()} 催办扫描出错：{type(exc).__name__}: {exc}")

                time.sleep(interval)

        threading.Thread(target=_loop, daemon=True).start()

    def _llm(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient.from_config(self.config)
        return self._llm_client


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="M0 飞书网关（长连接，不占端口）")
    parser.add_argument("--seconds", type=int, default=0, help="到点自动退出；0 = 一直跑")
    parser.add_argument("--quiet", action="store_true", help="关掉 SDK 的连接日志")
    args = parser.parse_args(argv)

    try:
        config = load_config()
        config.check_feishu()
        config.check_llm()
    except ConfigError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2

    # U2（§3.1）：这里的 store 是**进程根**（只装 index.json + app.lock）——
    # 每个群的数据域在 workspaces\<chat_id>\，由 Gateway.handle() 按消息选。
    store = JsonStore(config.data_dir)
    store.ensure_root_dirs()

    # P0-E：单实例保护。真机故障是两个进程跑同一套凭据 → 每条消息被处理两次。
    guard = SingleInstance(store.root)
    if not guard.acquire():
        print("[M0] 启动被拒：已有一个网关实例在跑（单实例保护，P0-E）。", file=sys.stderr)
        existing = guard.describe()
        if existing:
            print(f"     现有 app.lock：{existing}", file=sys.stderr)
        print(
            "     同一套凭据跑两个进程 = 每条群消息被处理两次。请先关掉另一个窗口。",
            file=sys.stderr,
        )
        return 3

    try:
        client_kwargs = {}
        if args.quiet:
            import lark_oapi as lark

            client_kwargs["log_level"] = lark.LogLevel.WARNING
        client = FeishuClient(config, **client_kwargs)
        gateway = Gateway(config, store, sender=client, downloader=client)
        gateway.start_reminder_loop()

        print("[M0] 正在建立长连接（首次加载 SDK 约 20 秒，属正常）", file=sys.stderr)
        print("     测试群里 @机器人 发「拆解」即可开始；Ctrl+C 退出", file=sys.stderr)
        if args.seconds > 0:
            def _stop() -> None:
                guard.release()
                os._exit(0)

            threading.Timer(args.seconds, _stop).start()

        try:
            client.start(gateway.on_event)
        except KeyboardInterrupt:
            pass
        return 0
    finally:
        guard.release()


if __name__ == "__main__":
    raise SystemExit(main())
