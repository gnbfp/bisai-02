# -*- coding: utf-8 -*-
"""只读计数：src/gateway/replies.py 的规模口径（供 docs/ARCHITECTURE-UPGRADE.md §11 复跑）。

口径（§11.1）：规模数字不手抄，只从本脚本输出复制。
  all   = len(__all__)          —— 对外可见名字总数
  text  = 文案绑定（字符串字面量 + 非字面量模板）
  sym   = 符号（类 + 函数）
  lines = 文件行数

用法：python tools/count_replies.py
不进运行时：src/ 不 import 本模块；本模块不 import src（纯 AST、只读）。
"""
import ast
import io
import os
import sys

TARGET = os.path.join("src", "gateway", "replies.py")
TEMPLATES = {"COMMANDS", "COMMAND_LIST_TEXT", "COMMAND_LIST_DM", "REGISTER_FORM_BAD"}


def classify(tree):
    kind = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    literal = isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                    kind[target.id] = "text_literal" if literal else "text_template"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind[node.name] = "symbol"
    return kind


def main(path=TARGET):
    src = io.open(path, "r", encoding="utf-8", newline="").read()
    tree = ast.parse(src)
    kind = classify(tree)
    names = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "__all__" for t in node.targets):
            names = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
    if names is None:
        raise SystemExit("找不到 __all__")
    unknown = [n for n in names if n not in kind]
    text = [n for n in names if kind.get(n, "").startswith("text_")]
    tmpl = sorted(set(text) & TEMPLATES)
    sym = [n for n in names if kind.get(n) == "symbol"]
    print("[count_replies] %s" % path.replace(os.sep, "/"))
    print("  all   = %d   (= len(__all__))" % len(names))
    print("  text  = %d   (字符串字面量 %d + 非字面量模板 %d %s)" % (
        len(text), len(text) - len(tmpl), len(tmpl), tmpl))
    print("  sym   = %d   %s" % (len(sym), sorted(sym)))
    print("  lines = %d" % len(src.splitlines()))
    if unknown:
        print("  未分类 = %s   <-- 口径要更新" % sorted(unknown))
    return 0 if not unknown else 1


if __name__ == "__main__":
    sys.exit(main())
