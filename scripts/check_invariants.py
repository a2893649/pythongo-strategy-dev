#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_invariants.py —— PythonGO 策略 12 条不变量静态校验（pythongo-strategy-dev skill）

用法：
    python scripts/check_invariants.py <strategy_file.py> [--strict]

设计目标：对纯文本做轻量、可解释的检查，逐条对 §二 不变量给出 通过/告警/失败。
不依赖框架、不执行策略，可在 CI 或本地门禁运行。

检查项：
  ② 抬价容差：比较式须显式 `+1e-9`（或 `HIKE_TOLERANCE`），禁止 `-1e-9` 写法；
  ⑤ 禁止挂单单一真源：出现 `self._*block*` 形式的内部镜像标志时告警；
  ⑦ 持仓累加：出现 `_pending_exit =` / `_position =` 的覆盖赋值（非 `+=`）时告警；
  ⑥ 报单被拒不留登记：应存在「被拒 → 清登记」的处理；
  ⑩ 订单归属过滤：应存在 `_is_my_oid` / `_my_oids` 或 `order_id` 过滤；
  ⑪ 放弃不清零：`_exit_give_up` 不得出现 `_pending_exit = 0`；
  ① 先判定后入窗：`_feed_range` / `feed(` 的调用应在 `_run_quote_loop` / `open_gate` 之后
     （按源码行序粗判，命中则通过，否则仅告警）。

任何「告警」不阻断（除非 --strict）；「失败」即非零退出。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 每条不变量：id / 名称 / 级别(pass|warn|fail)
RESULTS = []


def record(iid: str, name: str, level: str, detail: str) -> None:
    RESULTS.append((iid, name, level, detail))


def strip_comment(line: str) -> str:
    """剥掉行内注释，避免注释文本误触发检查（如「写成 -1e-9 会让…」）。

    仅当 '#' 位于行首或空格之后才视为注释起点；字符串内的 '#' 不处理（够用即可）。
    """
    out = []
    for i, ch in enumerate(line):
        if ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out)


def mask_strings(src: str) -> str:
    """把三引号字符串（docstring/注释块）与单双引号行内字符串的内容抹掉。

    避免文档/注释文本（如「写成 - 1e-9 会让…」「_pending_exit = 0」）误触发检查。
    只保留引号外壳，正则对残留代码生效。
    """
    # 三引号（优先，长短均可）
    for q in ('"""', "'''"):
        pattern = re.compile(re.escape(q) + r".*?" + re.escape(q), re.S)
        src = pattern.sub(q + q, src)
    # 行内单/双引号字符串（非三引号）
    src = re.sub(r'"[^"\n]*"', '""', src)
    src = re.sub(r"'[^'\n]*'", "''", src)
    return src


def scan(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = mask_strings(text)              # 抹掉字符串/docstring 内容
    raw_lines = text.splitlines()
    lines = [strip_comment(ln) for ln in raw_lines]

    # ② 抬价容差：只捕捉「抬价判定式」里的 `- 1e-9`
    #    （合法用法如 `fixed_target - 1e-9` 是跟追阈值，不算违规）
    #    高危特征：`> ... - 1e-9` 或 `< ... - 1e-9` 出现在与 OrderPrice 比较处。
    bad_tol = False
    for ln in lines:
        if re.search(r"order_price", ln) and re.search(r">[^>]*-\s*1e-9", ln):
            bad_tol = True
        if re.search(r"order_price", ln) and re.search(r"<\s*[^<]*-1e-9", ln):
            bad_tol = True
    if bad_tol:
        record("2", "抬价容差", "fail", "检测到 `-1e-9` 抬价写法，应为 `+1e-9`（持平亦判抬价→刷单）")
    else:
        record("2", "抬价容差", "pass", "未发现危险抬价写法（容差建议以 +1e-9 / 命名常量显式表达）")

    # ⑤ 禁止挂单单一真源：self._*block* 形式（排除 order_blocked）
    mirror = [
        ln for ln in lines
        if re.search(r"self\._\w*block\w*\s*=", ln)
        and "order_blocked" not in ln
    ]
    if mirror:
        record("5", "禁止挂单单一真源", "warn",
               f"发现疑似内部镜像标志 {len(mirror)} 处（应保持 state_map.order_blocked 唯一）")
    else:
        record("5", "禁止挂单单一真源", "pass", "未发现额外镜像标志")

    # ⑦ 持仓/待平累加：仅对「清零式赋值」告警（危险的是覆盖掉已累计持仓）
    #    排除 ⑫ 的合法对账方法 `_sync_position`（那里清零是设计内），其余清零即告警。
    reset_pe = reset_pos = False
    in_sync = False
    for ln in lines:
        if re.match(r"\s*def\s+_sync_position\b", ln):
            in_sync = True
            continue
        if in_sync and re.match(r"\s*def\s+\w+", ln):
            in_sync = False
        if in_sync:
            continue
        if re.search(r"_pending_exit\s*=\s*(?:0|0\.0|None)\b", ln):
            reset_pe = True
        if re.search(r"_position\s*=\s*(?:0|0\.0|None)\b", ln):
            reset_pos = True
    if reset_pe or reset_pos:
        record("7", "持仓/待平累加", "warn",
               "发现清零式赋值（=0/None，且不在 _sync_position 对账内）；确认非「已有未平持仓时少算平仓量」的覆盖")
    else:
        record("7", "持仓/待平累加", "pass", "未发现可疑清零式覆盖赋值")

    # ⑥ 报单被拒不留登记
    if re.search(r"on_order_rejected|_on_order_rejected|不支持撤销未知单", text) \
            or re.search(r"_clear_open_order\(\)", text):
        record("6", "报单被拒不留登记", "pass", "存在被拒/清登记处理")
    else:
        record("6", "报单被拒不留登记", "warn", "未发现「报单被拒→清登记」逻辑")

    # ⑩ 订单归属过滤
    if re.search(r"_is_my_oid|_my_oids|order_id", text):
        record("10", "订单归属过滤", "pass", "存在订单归属过滤")
    else:
        record("10", "订单归属过滤", "warn", "未发现订单归属过滤（同合约他方成交会被计入）")

    # ⑪ 放弃不清零待平（按缩进截取 _exit_give_up 方法体）
    start = None
    for i, ln in enumerate(raw_lines, 1):
        if re.match(r"\s*def\s+_exit_give_up\b", ln):
            start = i
            break
    if start is not None:
        def_indent = len(raw_lines[start - 1]) - len(raw_lines[start - 1].lstrip())
        body = []
        for ln in raw_lines[start:]:
            m = re.match(r"(\s*)def\s+\w+", ln)
            if m and len(m.group(1)) <= def_indent:
                break   # 下一个同级/更高级方法，方法体结束
            body.append(strip_comment(ln))   # 先去行注释，避免注释文本误判
        body_text = mask_strings("\n".join(body))
        if re.search(r"_pending_exit\s*=\s*0", body_text):
            record("11", "放弃不清零待平", "fail", "_exit_give_up 内清零 _pending_exit（应保留待平+置 _exit_stuck）")
        else:
            record("11", "放弃不清零待平", "pass", "_exit_give_up 未清零待平")
    else:
        record("11", "放弃不清零待平", "warn", "未找到 _exit_give_up，无法校验")

    # ① 先判定后入窗：调用点（缩进）上，feed 应在判定调用之后
    feed_line = None
    gate_line = None
    for i, ln in enumerate(lines, 1):
        if re.match(r"\s+", ln) and re.search(r"\.feed\(|_feed_range\(", ln):
            feed_line = i
        if re.match(r"\s+", ln) and re.search(r"_run_quote_loop\(|_open_gate\(|run_quote_loop\(", ln):
            gate_line = i
    if feed_line is not None and gate_line is not None:
        if feed_line >= gate_line:
            record("1", "先判定后入窗", "pass", f"判定@{gate_line} <= 入窗@{feed_line}")
        else:
            record("1", "先判定后入窗", "warn", f"入窗@{feed_line} 早于判定@{gate_line}，请确认时序")
    else:
        record("1", "先判定后入窗", "pass", "未发现同方法内「先判定后入窗」的调用对，跳过（单测/纯逻辑模块无此约束）")


def main() -> int:
    ap = argparse.ArgumentParser(description="PythonGO 策略不变量静态校验")
    ap.add_argument("file", type=Path, help="待校验策略文件路径")
    ap.add_argument("--strict", action="store_true", help="告警也视为失败")
    args = ap.parse_args()

    if not args.file.exists():
        print(f"[FATAL] 文件不存在: {args.file}", file=sys.stderr)
        return 2

    scan(args.file)

    print(f"== 不变量校验：{args.file} ==")
    failed = False
    for iid, name, level, detail in RESULTS:
        tag = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[level]
        print(f"  [{tag}] {iid} {name} — {detail}")
        if level == "fail" or (args.strict and level == "warn"):
            failed = True

    print("== 校验完成 ==")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
