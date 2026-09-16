r"""离线迁移工具：MVP 的扁平 `data\`  ->  升级版的工作空间布局（**只复制、不移动**）。

依据：`docs/ARCHITECTURE-UPGRADE.md` §3.1-§3.3（七步流程）、§3.4（2026-09-15 演练口径）、
`requirements-upgrade.md` §8 第 2 条（开工前必须通过那批）。
补丁来源：审核 #2 补丁 1 + 3（工具本身 + `Resolve-Path` 守卫），排 9/17 上午、U2 之前。

四条纪律（照 §3.3 的口径，不要自由发挥）：

1. **只复制、不移动** —— 源根 `data\` 全程只读。工具在写/删之前，先用 `Resolve-Path`
   的等价物（`resolve_path()`）把目标解析成真实路径，校验它**严格落在目标根之内**
   （`guard_within()`：不等于根、不在根之外）；不合格就抛 `OutOfScope` 中止。
2. **幂等** —— 重跑不产生第二份工作空间、不覆盖已有索引条目：负载按 `sha256`
   "相同即跳过"；`index.json` 只补缺失的键（已有键一律保留，免得把 §3.2 的改名冲掉）；
   同一份源数据的备份只留一份（`SOURCE.sha256` 认领，重跑复用）。
3. **归属不明不猜** —— `data\state.json` 的 `group_chat_id` 为空即中止；
   `pending_file.chat_id` 与群标识不一致就**不搬它**（§3.3 第 3 步，v1.7），并在
   `MANIFEST` 记一行 —— 搬过去只会留个被 `_pending_file()` 拒掉的死缓存。
4. **每一步留痕** —— 每次跑都写一份 `MANIFEST`（JSON）：逐文件动作 + 哈希 +
   索引增量 + 覆盖率前后读数 + "源根哈希没变"的自证。

`index.json` 两个字段的口径（v1.12 起，PM 2026-09-16 裁）：
`migrated_from` 记**仓库相对路径**（`data`）—— 不把机器绝对路径写进索引；
`created_at` = 该工作空间在索引里的**登记时刻**（懒创建 = 首条消息那刻，迁移进来的 =
迁移时刻），重跑**不覆盖**已有值。

跑法（在源码根目录）::

    python tools/migrate_workspace.py                    # 干跑：只打印计划，一个字节都不写
    python tools/migrate_workspace.py --apply            # 真跑：备份 -> 复制 -> 索引 -> 校验 -> MANIFEST
    python tools/migrate_workspace.py --rollback         # 回退：删副本 + 删索引条目（源根不动）
    python tools/migrate_workspace.py --apply --dest-root data-upgrade/_rehearsal   # 演练：只在沙箱里跑

**不进运行时**（`src\` 不许 import 本模块，同 `tools\probe_feishu.py`）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.intelligence.coverage import coverage_loop  # noqa: E402
from src.storage import (  # noqa: E402
    ASSIGNMENT,
    ASSIGNMENTS,
    CARDS,
    DIRECTION,
    GANTT,
    MEMBERS,
    PREFERENCES,
    PROPOSALS,
    REMINDERS,
    REPORT,
    RUBRIC,
    SEEN,
    STATE,
    UPLOADS,
    JsonStore,
)

__all__ = [
    "source_label",
    "GuardError",
    "Locked",
    "OutOfScope",
    "VerifyFailed",
    "Plan",
    "build_plan",
    "check_process_lock",
    "guard_roots_disjoint",
    "guard_within",
    "merge_index",
    "migrate",
    "readable_name",
    "resolve_path",
    "rollback",
    "safe_key",
    "tree_digest",
    "main",
]

TOOL = "tools/migrate_workspace.py"
TOOL_VERSION = "1.0"

DEFAULT_SOURCE = "data"
DEFAULT_DEST = "data-upgrade"
INDEX = "index.json"
WORKSPACES_DIR = "workspaces"
MIGRATION_DIR = "_migration"
BACKUP_MARKER = "SOURCE.sha256"
LOCK_NAME = "app.lock"

# §3.1 的 13 个候选名（"存在即复制"）。`changes.json` 是升级版新增的，不在迁移范围。
PAYLOAD_FILES = (
    ASSIGNMENT,
    RUBRIC,
    CARDS,
    PREFERENCES,
    ASSIGNMENTS,
    PROPOSALS,
    DIRECTION,
    MEMBERS,
    STATE,
    SEEN,
    REMINDERS,
    REPORT,
    GANTT,
)

EXIT_OK = 0
EXIT_GUARD = 2          # 归属不明 / 根目录混淆 / 路径段非法
EXIT_OUT_OF_SCOPE = 3   # Resolve-Path 守卫拒绝
EXIT_LOCKED = 4         # 升级版进程还在
EXIT_VERIFY = 5         # 校验不一致


# --------------------------------------------------------------------------
# 守卫
# --------------------------------------------------------------------------


class GuardError(Exception):
    """守卫拒绝执行（归属不明 / 根目录混淆 / 路径段非法 / 进程还在）。"""


class OutOfScope(GuardError):
    """`Resolve-Path` 守卫拦下的目标（落在允许根之外，或就是根本身）。"""


class Locked(GuardError):
    """目标数据根上还有活着的升级版进程。"""


class VerifyFailed(GuardError):
    """迁移后校验不一致（哈希 / 读数 / 覆盖率）。"""


_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def safe_key(key: str) -> str:
    """群标识一类的路径段守卫：不许出现分隔符、点段、空串。"""
    if not _KEY_RE.match(str(key or "")):
        raise GuardError(f"非法路径段 {key!r}：只允许 [A-Za-z0-9_-]（防目录穿越）")
    return str(key)


def resolve_path(path: Path | str) -> Path:
    """`Resolve-Path` 的等价物：解析成真实绝对路径（含符号链接）。

    目标**允许尚不存在** —— 逐级向上找到最近的已存在祖先，再把剩余段拼回去。
    """
    raw = Path(path)
    tail: list[str] = []
    cur = raw
    while not cur.exists():
        if cur.parent == cur:
            return Path(os.path.realpath(raw))
        tail.append(cur.name)
        cur = cur.parent
    real = Path(os.path.realpath(cur))
    for name in reversed(tail):
        real = real / name
    return real


def guard_within(target: Path | str, root: Path | str, *, what: str) -> Path:
    """写 / 删之前唯一的一道闸：目标的真实路径必须**严格落在** root 之内。

    额外挡两件事：目标就是 root 本身（可能把整个数据根删掉）、目标在 root 之外。
    """
    root_real = resolve_path(root)
    target_real = resolve_path(target)
    if target_real == root_real:
        raise OutOfScope(f"{what}：目标就是根目录本身（{target_real}），拒绝执行")
    if root_real not in target_real.parents:
        raise OutOfScope(f"{what}：目标 {target_real} 不在 {root_real} 之内，拒绝执行")
    return target_real


def guard_roots_disjoint(source_root: Path | str, dest_root: Path | str) -> tuple[Path, Path]:
    """源根与目标根不许重合、不许互相包含 —— 否则"只复制、不移动"这句话就没了。"""
    src = resolve_path(source_root)
    dst = resolve_path(dest_root)
    if src == dst or src in dst.parents or dst in src.parents:
        raise GuardError(f"源根与目标根不能重合或互相包含：{src} / {dst}")
    return src, dst


# --------------------------------------------------------------------------
# 哈希 / JSON 小工具
# --------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def tree_digest(root: Path | str) -> str:
    """目录内容哈希（按相对路径排序后逐文件哈希）：用来认领"同一份源数据"。"""
    root = Path(root)
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts:
            continue
        lines.append(f"{path.relative_to(root).as_posix()} {sha256_file(path)}")
    return sha256_bytes("\n".join(lines).encode("utf-8"))


def _load_json(path: Path | str, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if text.strip() else default


def _json_text(payload) -> str:
    """与 `JsonStore._write_unlocked` 同一形态：indent=2 + 结尾换行。"""
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# 进程锁（§3.3 第 1 步）
# --------------------------------------------------------------------------


def _pid_alive(pid: int) -> bool:
    """进程存活判定。

    **Windows 上绝不能用 `os.kill(pid, 0)`** —— CPython 在 Windows 上把它译成
    `TerminateProcess(handle, 0)`，会直接把目标进程杀掉。所以走 OpenProcess +
    GetExitCodeProcess == STILL_ACTIVE。
    """
    try:
        if os.name != "nt":
            os.kill(pid, 0)      # POSIX：信号 0 只做权限/存在性检查
            return True
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except OSError:
        return False


def check_process_lock(dest_root: Path | str, *, force: bool = False) -> str | None:
    """迁移前必须停升级版进程（§3.3 第 1 步）。锁在进程根，也就是目标根。"""
    lock = Path(dest_root) / LOCK_NAME
    if not lock.is_file():
        return None
    info = _load_json(lock, {}) or {}
    pid = info.get("pid") if isinstance(info, dict) else None
    started = info.get("started_at") if isinstance(info, dict) else None
    note = f"{LOCK_NAME} 存在（pid={pid}, started_at={started}）"
    if isinstance(pid, int) and _pid_alive(pid):
        if not force:
            raise Locked(f"升级版进程还在跑（{note}）—— 先停进程，或显式加 --force")
        return f"{note}；活着，但 --force 已跳过阻断"
    return f"{note}；该进程已不在，按已停处理"


# --------------------------------------------------------------------------
# 计划的组成
# --------------------------------------------------------------------------


@dataclass
class Payload:
    """一个候选文件的迁移条目。`data` = 目标字节（`state.json` 会被守卫改写）。"""

    name: str
    source: Path | None
    data: bytes | None
    sha256: str | None


@dataclass
class Plan:
    source_root: Path
    dest_root: Path
    chat_id: str
    readable_name: str
    workspace_dir: Path
    backup_root: Path
    index_path: Path
    payload: list
    uploads: list
    member_ids: list
    workspace_entry: dict
    index_doc: dict
    index_actions: dict
    pending_file: dict
    source_digest: str
    skipped: list


def readable_name(title: str, chat_id: str) -> str:
    """§3.2 的可读名：`<作业书标题>-<chat_id 尾 6 位>`；没标题就退成 `群<尾 6 位>`。"""
    tail = chat_id[-6:]
    title = (title or "").strip()
    return f"{title}-{tail}" if title else f"群{tail}"


def source_label(source_root: Path | str) -> str:
    r"""索引里的 `migrated_from`：**仓库内的源根记仓库相对路径**（`data`）。

    绝对路径是机器相关的，写进 `index.json` 就等于把 `D:\AI创新创业大赛\data`
    这种值钉进数据里（换台机器 / 换目录就成了假信息）。仓库外的源根（回归用例的
    临时目录）没有有意义的相对形式，退成解析后的绝对路径。
    """
    resolved = resolve_path(source_root)
    try:
        rel = resolved.relative_to(resolve_path(REPO_ROOT))
    except ValueError:
        return resolved.as_posix()
    return rel.as_posix() or "."


def _member_ids(doc) -> list[str]:
    """从 `members.json` 推花名册 open_id（§3.3 第 5 步的 `user_last_group` 来源）。"""
    ids: list[str] = []
    if isinstance(doc, dict):
        for item in doc.get("members") or []:
            if isinstance(item, dict) and item.get("open_id"):
                ids.append(str(item["open_id"]))
        if doc.get("leader"):
            ids.append(str(doc["leader"]))
    out: list[str] = []
    for open_id in ids:
        if open_id not in out:
            out.append(open_id)
    return out


def _build_payload(source_root: Path, state: dict, chat_id: str) -> tuple[list, dict]:
    """逐候选文件算出目标字节；`pending_file` 的跨会话守卫在这里生效。"""
    pending = state.get("pending_file")
    keep_pending = False
    if not isinstance(pending, dict) or not pending:
        pending_note = {"migrated": False, "reason": "源盘没有 pending_file（无需处置）"}
    else:
        pending_chat = str(pending.get("chat_id") or "")
        if pending_chat and pending_chat != chat_id:
            pending_note = {
                "migrated": False,
                "reason": (
                    f"搬过去会被 _pending_file() 按会话拒掉（§3.3 第 3 步，v1.7）："
                    f"pending_file.chat_id={pending_chat} != group_chat_id={chat_id}"
                ),
            }
        else:
            keep_pending = True
            pending_note = {
                "migrated": True,
                "reason": f"pending_file.chat_id={pending_chat or '(空)'} 与群标识一致",
            }

    entries: list[Payload] = []
    for name in PAYLOAD_FILES:
        src = source_root / name
        if not src.is_file():
            entries.append(Payload(name=name, source=None, data=None, sha256=None))
            continue
        data = src.read_bytes()
        if name == STATE:
            doc = dict(state)
            if not keep_pending:
                doc.pop("pending_file", None)
            data = _json_text(doc).encode("utf-8")
        entries.append(Payload(name=name, source=src, data=data, sha256=sha256_bytes(data)))
    return entries, pending_note


def _collect_uploads(source_root: Path) -> list[tuple[str, Path]]:
    root = source_root / UPLOADS
    if not root.is_dir():
        return []
    return [
        (path.relative_to(root).as_posix(), path)
        for path in sorted(p for p in root.rglob("*") if p.is_file())
        if "__pycache__" not in path.parts
    ]


def merge_index(existing, chat_id: str, entry: dict, member_ids: list) -> tuple[dict, dict]:
    """幂等合并索引：工作空间条目与 `user_last_group` 只补缺失的键。

    已有键一律保留 —— 否则重跑会把 §3.2 的"改名"和运行时刚更新的"最近一次群内互动"冲掉。
    """
    doc = dict(existing) if isinstance(existing, dict) else {}
    workspaces = dict(doc.get("workspaces") or {})
    entry_action = "kept" if chat_id in workspaces else "added"
    if entry_action == "added":
        workspaces[chat_id] = dict(entry)
    doc["workspaces"] = workspaces

    last = dict(doc.get("user_last_group") or {})
    added, kept = [], []
    for open_id in member_ids:
        if open_id in last:
            kept.append(open_id)
        else:
            last[open_id] = chat_id
            added.append(open_id)
    doc["user_last_group"] = last

    actions = {
        "workspace_entry": entry_action,
        "user_last_group_added": added,
        "user_last_group_kept": kept,
    }
    return doc, actions


def build_plan(source_root: Path | str, dest_root: Path | str, *, now: datetime | None = None) -> Plan:
    """算出"该做什么"，不碰盘 —— 干跑与真跑共用这一份计算，避免两边逻辑漂移。"""
    now = now or datetime.now()
    src = resolve_path(source_root)
    dst = resolve_path(dest_root)

    state = _load_json(src / STATE)
    if not isinstance(state, dict):
        raise GuardError(f"{src / STATE} 不是 JSON 对象 —— 归属不明，中止（§3.3 第 3 步）")
    chat_id = str(state.get("group_chat_id") or "").strip()
    if not chat_id:
        raise GuardError(
            "data\\state.json 的 group_chat_id 为空 —— 无法判定归属，绝不猜（§3.3 第 3 步）"
        )
    chat_id = safe_key(chat_id)

    assignment = _load_json(src / ASSIGNMENT) or {}
    title = str(assignment.get("title") or "") if isinstance(assignment, dict) else ""

    payload, pending_note = _build_payload(src, state, chat_id)
    member_ids = _member_ids(_load_json(src / MEMBERS))
    entry = {
        "name": readable_name(title, chat_id),
        # created_at = 该工作空间在索引里的"登记时刻"：懒创建的工作空间 = 首条消息那刻，
        # 迁移进来的 = 迁移时刻。字段名沿用 §3.3 第 5 步的字面，语义写在这里与手册里；
        # merge_index 只补缺失键 ⇒ 重跑不会把它改成后来的时间。
        "created_at": now.isoformat(timespec="seconds"),
        "migrated_from": source_label(source_root),
    }
    index_doc, index_actions = merge_index(_load_json(dst / INDEX), chat_id, entry, member_ids)

    skipped = [
        {"name": path.name, "reason": "不在 §3.1 的 13 个候选名里（整份备份仍会覆盖它）"}
        for path in sorted(src.iterdir())
        if path.name not in PAYLOAD_FILES and path.name != UPLOADS
    ]

    return Plan(
        source_root=src,
        dest_root=dst,
        chat_id=chat_id,
        readable_name=entry["name"],
        workspace_dir=dst / WORKSPACES_DIR / chat_id,
        backup_root=dst / MIGRATION_DIR,
        index_path=dst / INDEX,
        payload=payload,
        uploads=_collect_uploads(src),
        member_ids=member_ids,
        workspace_entry=entry,
        index_doc=index_doc,
        index_actions=index_actions,
        pending_file=pending_note,
        source_digest=tree_digest(src),
        skipped=skipped,
    )


# --------------------------------------------------------------------------
# 校验（§3.3 第 6 步）
# --------------------------------------------------------------------------


def _size(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _roster_size(roster) -> int:
    """花名册的读数 = 人数（不是"一个对象"）—— 与 §3.4 的读数表直接对表。"""
    return len(roster.members) if roster else 0


def _file_action(dest: Path, data: bytes | None) -> str:
    if data is None:
        return "missing"
    if not dest.exists():
        return "copy"
    return "unchanged" if sha256_file(dest) == sha256_bytes(data) else "overwrite"


def _verify(plan: Plan) -> dict:
    src_store = JsonStore(plan.source_root)
    ws_store = JsonStore(plan.workspace_dir)

    reads = {}
    reads_ok = True
    for label, loader, counter in (
        ("rubric", "load_rubric", _size),
        ("cards", "load_cards", _size),
        ("members", "load_members", _roster_size),   # §3.4 的读数表按"花名册人数"计
        ("preferences", "load_preferences", _size),
        ("assignments", "load_assignments", _size),
    ):
        before = counter(getattr(src_store, loader)())
        after = counter(getattr(ws_store, loader)())
        reads[label] = {"source": before, "workspace": after, "equal": before == after}
        reads_ok = reads_ok and before == after

    cov_src = coverage_loop(src_store.load_cards(), src_store.load_rubric())
    cov_ws = coverage_loop(ws_store.load_cards(), ws_store.load_rubric())
    coverage = {
        "source": {
            "eligible": list(cov_src.eligible),
            "covered": list(cov_src.covered),
            "missing": list(cov_src.missing),
        },
        "workspace": {
            "eligible": list(cov_ws.eligible),
            "covered": list(cov_ws.covered),
            "missing": list(cov_ws.missing),
        },
        "equal": cov_src == cov_ws,
    }

    payload_hash_equal = all(
        sha256_file(plan.workspace_dir / item.name) == item.sha256
        for item in plan.payload
        if item.data is not None
    )
    uploads_hash_equal = all(
        sha256_file(plan.workspace_dir / UPLOADS / rel) == sha256_file(source)
        for rel, source in plan.uploads
    )

    return {
        "reads": reads,
        "reads_equal": reads_ok,
        "coverage": coverage,
        "payload_hash_equal": payload_hash_equal,
        "uploads_hash_equal": uploads_hash_equal,
        "ok": reads_ok and coverage["equal"] and payload_hash_equal and uploads_hash_equal,
    }


# --------------------------------------------------------------------------
# 两个动作
# --------------------------------------------------------------------------


def _manifest_path(plan: Plan, action: str, stamp: str) -> Path:
    return plan.backup_root / f"MANIFEST-{action}-{stamp}.json"


def _unique_path(path: Path) -> Path:
    """同一秒里跑两次不许互相覆盖 —— MANIFEST 是记录，记录丢了就等于没跑过。"""
    if not path.exists():
        return path
    for n in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise GuardError(f"同一时间戳下 MANIFEST 已堆到 999 份：{path}")


def _dump_manifest(path: Path, root: Path, manifest: dict) -> str:
    target = _unique_path(guard_within(path, root, what=f"写 {path.name}"))
    manifest["manifest_path"] = str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(target, _json_text(manifest).encode("utf-8"))
    return str(target)


def _backup(plan: Plan, stamp: str) -> dict:
    """§3.3 第 2 步：先备份。同一份源数据已备份过就复用（幂等，且不堆磁盘）。"""
    backup_root = guard_within(plan.backup_root, plan.dest_root, what="备份目录")
    if backup_root.is_dir():
        for candidate in sorted(p for p in backup_root.iterdir() if p.is_dir()):
            marker = candidate / BACKUP_MARKER
            if marker.is_file() and marker.read_text(encoding="utf-8").strip() == plan.source_digest:
                return {
                    "dir": str(candidate),
                    "action": "reused",
                    "reason": f"{BACKUP_MARKER} 与本次源根哈希一致",
                    "source_digest": plan.source_digest,
                    "source_files": sum(1 for _ in plan.source_root.rglob("*") if _.is_file()),
                }
    target = guard_within(plan.backup_root / stamp, plan.dest_root, what="备份目录")
    shutil.copytree(plan.source_root, target, ignore=shutil.ignore_patterns("__pycache__"))
    (target / BACKUP_MARKER).write_text(plan.source_digest + "\n", encoding="utf-8")
    return {
        "dir": str(target),
        "action": "created",
        "reason": "本次新建",
        "source_digest": plan.source_digest,
        "source_files": sum(1 for _ in target.rglob("*") if _.is_file()),
    }


def migrate(
    source_root: Path | str = DEFAULT_SOURCE,
    dest_root: Path | str = DEFAULT_DEST,
    *,
    apply: bool = False,
    force: bool = False,
    now: datetime | None = None,
) -> dict:
    """干跑（默认）或真跑一次迁移，返回 `MANIFEST` 字典。"""
    now = now or datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    src_root, dest_root_real = guard_roots_disjoint(source_root, dest_root)
    plan = build_plan(src_root, dest_root_real, now=now)

    manifest = {
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "action": "migrate",
        "at": now.isoformat(timespec="seconds"),
        "apply": bool(apply),
        "source_root": str(plan.source_root),
        "dest_root": str(plan.dest_root),
        "chat_id": plan.chat_id,
        "readable_name": plan.readable_name,
        "workspace_dir": str(plan.workspace_dir),
        "source_digest": plan.source_digest,
        "pending_file": plan.pending_file,
        "skipped": plan.skipped,
        "index": {"path": str(plan.index_path), **plan.index_actions},
        "manifest_path": str(_manifest_path(plan, "migrate", stamp)),
    }

    if not apply:
        manifest["dry_run"] = True
        manifest["backup"] = {"dir": str(plan.backup_root / stamp), "action": "would_create"}
        manifest["payload"] = [
            {
                "name": item.name,
                "action": _file_action(plan.workspace_dir / item.name, item.data),
                "bytes": len(item.data) if item.data is not None else None,
                "sha256": item.sha256,
            }
            for item in plan.payload
        ]
        manifest["uploads"] = {"count": len(plan.uploads), "files": [rel for rel, _ in plan.uploads]}
        manifest["workspace_changes"] = None
        manifest["idempotent"] = None
        return manifest

    notes: list[str] = []
    lock_note = check_process_lock(plan.dest_root, force=force)
    if lock_note:
        notes.append(f"进程锁：{lock_note}")
    manifest["backup"] = _backup(plan, stamp)
    writes = 1 if manifest["backup"]["action"] == "created" else 0

    ws_dir = guard_within(plan.workspace_dir, plan.dest_root / WORKSPACES_DIR, what="写工作空间目录")
    if not ws_dir.is_dir():
        ws_dir.mkdir(parents=True, exist_ok=True)
        writes += 1
    guard_within(plan.index_path, plan.dest_root, what="写索引")

    rows = []
    for item in plan.payload:
        target = ws_dir / item.name
        action = _file_action(target, item.data)
        if action in ("copy", "overwrite") and item.data is not None:
            _write_atomic(target, item.data)
            writes += 1
        rows.append(
            {
                "name": item.name,
                "action": action,
                "bytes": len(item.data) if item.data is not None else None,
                "sha256": item.sha256,
            }
        )
    manifest["payload"] = rows

    upload_rows = []
    for rel, source in plan.uploads:
        target = ws_dir / UPLOADS / rel
        action = "unchanged" if target.exists() and sha256_file(target) == sha256_file(source) else "copy"
        if action == "copy":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            writes += 1
        upload_rows.append({"path": f"{UPLOADS}/{rel}", "action": action})
    manifest["uploads"] = {"count": len(plan.uploads), "files": upload_rows}

    kept_not_in_source = [
        item.name for item in plan.payload if item.data is None and (ws_dir / item.name).exists()
    ]
    if kept_not_in_source:
        notes.append(f"工作空间里已存在、源盘没有的文件一律保留（只增不删）：{kept_not_in_source}")
    manifest["kept_not_in_source"] = kept_not_in_source

    store = JsonStore(plan.dest_root)
    index_before = store.read_raw(INDEX, {}) or {}
    merged, index_actions = merge_index(
        index_before, plan.chat_id, plan.workspace_entry, plan.member_ids
    )
    index_action = "unchanged"
    if merged != index_before:
        store.write_raw(INDEX, merged)
        writes += 1
        index_action = "created" if not index_before else "updated"
    manifest["index"] = {"path": str(plan.index_path), "action": index_action, **index_actions}

    verify = _verify(plan)
    verify["source_unchanged"] = tree_digest(plan.source_root) == plan.source_digest
    verify["ok"] = verify["ok"] and verify["source_unchanged"]
    manifest["verify"] = verify
    manifest["notes"] = notes
    manifest["workspace_changes"] = writes
    manifest["idempotent"] = writes == 0

    path = _dump_manifest(_manifest_path(plan, "migrate", stamp), plan.dest_root, manifest)
    manifest["manifest_path"] = path

    if not verify["ok"]:
        raise VerifyFailed(f"迁移后校验不一致，见 {path}（verify.ok=false）")
    return manifest


def rollback(
    source_root: Path | str = DEFAULT_SOURCE,
    dest_root: Path | str = DEFAULT_DEST,
    *,
    chat_id: str = "",
    force: bool = False,
    now: datetime | None = None,
) -> dict:
    """§3.3 第 7 步：回退 = 删副本 + 删索引条目。源根只读，所以回退无数据风险。

    回退照样**删副本 / 改索引** ⇒ 与 `migrate()` 同一条纪律：升级版进程还在跑就不许动盘
    （§3.3 第 1 步）。检查点放在任何写之前，拦下就是**一个字节都没动**。
    """
    now = now or datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    src_root, dest_root_real = guard_roots_disjoint(source_root, dest_root)
    lock_note = check_process_lock(dest_root_real, force=force)

    key = str(chat_id or "").strip()
    if not key:
        state = _load_json(src_root / STATE)
        if isinstance(state, dict):
            key = str(state.get("group_chat_id") or "").strip()
    index_path = dest_root_real / INDEX
    if not key:
        index = _load_json(index_path) or {}
        keys = sorted((index.get("workspaces") or {})) if isinstance(index, dict) else []
        if len(keys) == 1:
            key = keys[0]
        else:
            raise GuardError("回退需要 --chat-id：源 state.json 取不到群标识，索引里也不是唯一一条")
    key = safe_key(key)

    ws_root = dest_root_real / WORKSPACES_DIR
    ws_dir = guard_within(ws_root / key, ws_root, what="回退：删工作空间副本")
    guard_within(index_path, dest_root_real, what="回退：改索引")

    manifest = {
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "action": "rollback",
        "at": now.isoformat(timespec="seconds"),
        "source_root": str(src_root),
        "dest_root": str(dest_root_real),
        "chat_id": key,
        "lock": lock_note,
        "workspace_dir": str(ws_dir),
        "manifest_path": str(dest_root_real / MIGRATION_DIR / f"MANIFEST-rollback-{stamp}.json"),
    }

    writes = 0
    manifest["workspace"] = "removed" if ws_dir.is_dir() else "absent"
    if ws_dir.is_dir():
        shutil.rmtree(ws_dir)
        writes += 1

    store = JsonStore(dest_root_real)
    before = store.read_raw(INDEX, {}) or {}
    after = dict(before) if isinstance(before, dict) else {}
    workspaces = dict(after.get("workspaces") or {})
    dropped_entry = key in workspaces
    workspaces.pop(key, None)
    last = dict(after.get("user_last_group") or {})
    dropped_bindings = sorted(oid for oid, target in last.items() if target == key)
    for oid in dropped_bindings:
        last.pop(oid, None)
    if dropped_entry or dropped_bindings:
        after["workspaces"] = workspaces
        after["user_last_group"] = last
        store.write_raw(INDEX, after)
        writes += 1
    manifest["index"] = {
        "path": str(index_path),
        "workspace_entry": "dropped" if dropped_entry else "absent",
        "user_last_group_dropped": dropped_bindings,
        "note": "「删索引条目」按删 workspaces[key] 读；顺带摘掉指向它的 user_last_group 绑定（悬挂绑定会把私聊路由到死工作空间）",
    }
    manifest["source_untouched"] = True
    manifest["workspace_changes"] = writes
    manifest["idempotent"] = writes == 0

    path = _dump_manifest(
        dest_root_real / MIGRATION_DIR / f"MANIFEST-rollback-{stamp}.json",
        dest_root_real,
        manifest,
    )
    manifest["manifest_path"] = path
    return manifest


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _print_summary(manifest: dict) -> None:
    action = manifest["action"]
    if action == "migrate":
        head = "干跑（一个字节都没写）" if manifest.get("dry_run") else "已执行"
    else:
        head = "已执行"
    print(f"[{TOOL} v{TOOL_VERSION}] {action} · {head}")
    print(f"  源根   = {manifest['source_root']}")
    print(f"  目标根 = {manifest['dest_root']}")
    if action == "migrate":
        print(f"  工作空间 = {manifest['workspace_dir']}  （可读名 {manifest['readable_name']}）")
        print(f"  备份   = {manifest['backup']['dir']}  [{manifest['backup']['action']}]")
        for row in manifest["payload"]:
            print(f"    - {row['name']:<18} {row['action']}")
        uploads = manifest["uploads"]
        print(f"  附件   = {uploads['count']} 个")
        pending = manifest["pending_file"]
        print(f"  pending_file = {'搬' if pending['migrated'] else '不搬'}（{pending['reason']}）")
        if manifest.get("skipped"):
            for row in manifest["skipped"]:
                print(f"    跳过 {row['name']}：{row['reason']}")
        if not manifest.get("dry_run"):
            verify = manifest["verify"]
            print(f"  校验   = ok={verify['ok']} 读数一致={verify['reads_equal']} "
                  f"覆盖率一致={verify['coverage']['equal']} 负载哈希={verify['payload_hash_equal']} "
                  f"附件哈希={verify['uploads_hash_equal']} 源根未变={verify['source_unchanged']}")
            cov = verify["coverage"]["workspace"]
            print(f"  覆盖率 = {len(cov['covered'])}/{len(cov['eligible'])} missing={cov['missing']}")
            print(f"  写盘次数 = {manifest['workspace_changes']}  幂等={manifest['idempotent']}")
    else:
        print(f"  工作空间 = {manifest['workspace_dir']}  [{manifest['workspace']}]")
        print(f"  索引条目 = {manifest['index']['workspace_entry']}；"
              f"摘掉绑定 {len(manifest['index']['user_last_group_dropped'])} 条")
        print(f"  写盘次数 = {manifest['workspace_changes']}  幂等={manifest['idempotent']}")
    print(f"  MANIFEST = {manifest['manifest_path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools/migrate_workspace.py",
        description="离线迁移：MVP 的扁平 data\\ -> 升级版工作空间布局（§3.3；只复制、不移动）",
    )
    parser.add_argument("--source-root", default=DEFAULT_SOURCE, help="源根（默认 data）")
    parser.add_argument("--dest-root", default=DEFAULT_DEST, help="目标根（默认 data-upgrade）")
    parser.add_argument("--apply", action="store_true", help="真跑；不给就是干跑")
    parser.add_argument("--rollback", action="store_true", help="回退：删副本 + 删索引条目")
    parser.add_argument("--chat-id", default="", help="回退用；缺省从源 state.json / 索引推")
    parser.add_argument("--force", action="store_true", help="跳过进程锁检查")
    parser.add_argument("--json", action="store_true", help="把 MANIFEST 原样打到 stdout")
    args = parser.parse_args(argv)

    try:
        if args.rollback:
            manifest = rollback(args.source_root, args.dest_root, chat_id=args.chat_id, force=args.force)
        else:
            manifest = migrate(args.source_root, args.dest_root, apply=args.apply, force=args.force)
    except Locked as exc:
        print(f"[迁移中止] {exc}", file=sys.stderr)
        return EXIT_LOCKED
    except OutOfScope as exc:
        print(f"[迁移中止] Resolve-Path 守卫：{exc}", file=sys.stderr)
        return EXIT_OUT_OF_SCOPE
    except VerifyFailed as exc:
        print(f"[迁移中止] 校验不一致：{exc}", file=sys.stderr)
        return EXIT_VERIFY
    except GuardError as exc:
        print(f"[迁移中止] {exc}", file=sys.stderr)
        return EXIT_GUARD

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        _print_summary(manifest)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())