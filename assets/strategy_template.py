# -*- coding: utf-8 -*-
"""
PythonGO 策略最小合规骨架（pythongo-strategy-dev skill 生成）
==================================================================
仅含合规脚手架与 12 条不变量的护栏注释。复制后补业务逻辑。

门禁：
    python scripts/verify_pythongo_compliance.py <本文件>
    python scripts/check_invariants.py           <本文件>
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from pythongo.base import BaseParams, BaseState, BaseStrategy, Field


# ----------------------------------------------------------------------
# 可调值只走 params_map（禁止散落魔数）
# ----------------------------------------------------------------------
class StrategyParams(BaseParams):
    exchange: str = Field(default="CZCE", title="交易所代码")
    instrument_id: str = Field(default="SA611C960", title="合约代码")
    volume: int = Field(default=1, title="单次委托手数", ge=1)
    # —— 以下为示例口径，按业务补齐 ——


class StrategyState(BaseState):
    status: str = Field(default="初始化", title="状态")
    order_blocked: bool = Field(default=False, title="禁止挂单")   # ⑤ 单一真源


# 抬价容差（② 必须 +1e-9，禁止写成 -1e-9）
HIKE_TOLERANCE = 1e-9


class MyStrategy(BaseStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.params_map = StrategyParams()
        self.state_map = StrategyState()
        self._lock = threading.RLock()
        self._open_order_id: Any = None

    # ---- 入口串行化：行情/回报/错误线程与 watchdog 线程共用状态机 ----
    def _serialized(self, fn):  # 见 skill base_helpers 装饰器实现
        def wrapper(*a, **k):
            with self._lock:
                return fn(*a, **k)
        return wrapper

    def _try(self, fn, what, *args, **kwargs):
        """⑨ 框架调用统一异常保护：失败仅记日志，绝不冒泡打断 on_tick"""
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            self.output(f"[ERROR] {what}异常: {exc}")
            return None

    # ---- 生命周期：每个回调首行 super()（规范 §2）----
    def on_init(self) -> None:
        super().on_init()
        self.output("策略已初始化")

    def on_start(self) -> None:
        super().on_start()

    def on_stop(self) -> None:
        super().on_stop()

    def set_params(self, data: dict) -> None:
        super().set_params(data)   # 必须在 super() 之前比较区间口径参数

    # ---- 行情回调 ----
    def on_tick(self, tick):
        super().on_tick(tick)
        if not self.trading:
            return
        if str(getattr(tick, "instrument_id", "")) != self.params_map.instrument_id:
            return
        # ① 先判定（用历史区间），后入窗（把本 tick 纳入区间）
        # self._run_quote_loop()           # 先判定
        # self._feed_range(price)          # 再入窗

    def on_order(self, order):
        super().on_order(order)
        oid = getattr(order, "order_id", None)
        status = str(getattr(order, "status", ""))
        # ④ 待确认撤单回执判断必须排在最前
        # if self._handle_cancel_ack(oid): return
        # ⑥ 报单被拒必须清本地登记

    def on_trade(self, trade, log=False):
        super().on_trade(trade, log)
        # ⑩ 订单归属过滤：只认本实例报出的 order_id
        # ⑦ 持仓/待平必须累加，禁止覆盖赋值

    def on_error(self, error) -> None:
        super().on_error(error)
        # ⑥ 带 orderID 的 error 调 _on_order_rejected 清登记

    # ---- 不变量护栏（详情见 skill references/invariants.md）----
    # ③ 撤单串行化 + 冷却（冷却自撤单发起时刻起算，回执不提前结束，超时兜底）
    # ⑧ 各等待/退避独立字段
    # ⑪ 平仓放弃不得静默清零待平（置 _exit_stuck + 告警 + 慢重试 + 禁开仓）
    # ⑫ 卡死标志须连续读零仓归零出口
