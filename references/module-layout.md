# 模块分解包结构（巨石 → 可维护）

> 把**不依赖 `BaseStrategy` 的纯逻辑**抽成独立模块（可在无框架环境单测），
> 策略类只做「框架适配 + 编排」。

## 推荐包结构
```
snow_pkg/
├── __init__.py            # 导出 SnowStrategy
├── base_helpers.py        # _try / _safe_float / _num / _serialized / _best_effort
├── session_calendar.py    # SESSIONS + 时段/交易日判定（几乎纯函数）
├── bollinger_range.py     # RangeEngine：K线合成 + 布林带 + 越界判定
├── gating.py              # GatePolicy：时段门/风控门/盘口/开仓总门
├── bid_reference.py       # BidReference：挂单基准价（买N档）
├── order_fsm.py           # OpenOrderFSM：开仓单生命周期（挂/撤/冷却/回执/重试）
├── exit_manager.py        # ExitManager：两段式平仓 + 持仓采纳/对账
├── persistence.py         # ParamBackup：双写落盘/恢复
├── ui_state.py            # StatePublisher：派生字段 + 节流推送
└── strategy.py            # SnowStrategy(BaseStrategy)：编排 + 回调
```

## 各模块职责与 snow.py 来源映射

| 模块 | 抽出自 snow.py | 关键状态 |
|---|---|---|
| `session_calendar.py` | `_now_min`(694) `_session_of`(700) `_trading_day`(707) `_session_key`(718) `_roll_session`(731) `_roll_day`(756) `SESSIONS`(178) | `sess_key/sess_name/day` |
| `bollinger_range.py` | `_need_samples`(862) `_range_params_changed`(866) `_reset_range_state`(875) `_range_block`(897) `_feed_range`(916) `_recalc_range`(945) | `range_* _bar_*` |
| `gating.py` | `_time_gate`(770) `_risk_block`(793) `_quote_valid`(819) `_open_gate`(831) | 只读 params + 行情快照 |
| `bid_reference.py` | `_calc_bid_ref`(1019) | — |
| `order_fsm.py` | `_clear_open_order`(974) `_on_open_order_filled`(982) `_place_buy_order`(1039) `_cancel_open_order`(1076) `_retry_stale_cancel`(1130) `_release_stale_cancel`(1143) `_check_open_order_protect`(1159) `_on_order_rejected`(1169) `_handle_cancel_ack`(1193) 冷却态(1270-1290) | `open_order_* _cancel_*` |
| `exit_manager.py` | `_clear_exit_order`(1321) `_exit_give_up`(1326) `_exit_backoff`(1348) `_ask_fresh`(1354) `_try_pending_exit`(1370) `_sync_position`(1538) | `position/pending_exit/entry_* _exit_* _exit_stuck* _pos_zero_streak` |
| `persistence.py` | `_backup_file`(419) `_ensure_dirs`(439) `_backup_params`(451) `_restore_from_backup`(466) `_persist_params`(497) | — |
| `ui_state.py` | `_set_order_lock`(1860) `_derived_state`(1871) `_push_state`(1887) `_order_phase`(1292) | `last_state_push` |
| `base_helpers.py` | `_try`(387) `_safe_float`(398) `_num`(405) `_tick`(409) 两装饰器(218/239) | — |
| `strategy.py` | `__init__` `set_params` `on_init` `on_start` `on_stop` `on_tick`(1632) `on_order`(1668) `on_trade`(1732) `on_error`(1845) `_housekeeping`(1608) `_watchdog`(1615) | 编排 glue，持有上述模块实例 |

## 重构后编排骨架（示意）
```python
class SnowStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params_map = StrategyParams()
        self.state_map  = StrategyState()
        self._lock = threading.RLock()
        self.calendar = SessionCalendar()
        self.range    = RangeEngine(self._now_ts)
        self.gates    = GatePolicy(self.params_map)
        self.orders   = OpenOrderFSM(self)     # 持有 send_order/cancel_order 适配
        self.exits    = ExitManager(self)
        self.ui       = StatePublisher(self)

    @_serialized
    def on_tick(self, tick):
        super().on_tick(tick)
        if not self.trading: return
        if tick.instrument_id != self.params_map.instrument_id: return
        self.calendar.roll()
        self._refresh_quote(tick)
        self._housekeeping()
        self.orders.run_quote_loop(...)
        self.range.feed(self._last_price)      # 本 tick 入窗（在判定之后）
```
要点：纯逻辑模块**不继承** `BaseStrategy`，只接收「时间函数 / 行情快照 / 框架适配回调」，
从而可在无框架环境单测；策略类只做适配与编排，体积可压到 ~400 行。
