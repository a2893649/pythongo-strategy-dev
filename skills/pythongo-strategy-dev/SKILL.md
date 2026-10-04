---
name: pythongo-strategy-dev
description: 按 PythonGO 实盘规范开发 / 审查 / 封装交易策略：强制合规骨架、12 条不可动摇的不变量、模块分解模板与上线前门禁。
whenToUse: 用户要写、改、审查、或封装一个 PythonGO 策略（提到 BaseStrategy / pythongo / verify_pythongo_compliance / 报单状态机 / 布林带区间门 / 单向抬价挂单）；或把现有单个巨石策略拆成可维护模块、生成可安装的 skill。
---

# PythonGO 策略开发（实盘合规封装）

> 本 skill 服务于「PythonGO 期权/期货实盘策略」的开发与封装。**所有口径来自真实
> 实盘事故**，不是风格偏好。改动策略前必须逐条核对「不可动摇的不变量」（§二）。
> 改完必须跑门禁（§五），门禁不通过不得上线。

## 何时使用本 skill

- 新建一个 PythonGO 策略（套用 `assets/strategy_template.py`）；
- 修改/审查已有策略（对照 `references/invariants.md` 逐条核对是否触碰不变量）；
- 把单个巨石策略（如 1900 行的 `snow.py`）拆成 `references/module-layout.md`
  推荐的「纯逻辑 + 编排」结构；
- 生成可安装的策略 skill 包（参考本 skill 自身的 bundle 结构）。

## 一、PythonGO 官方规范（硬约束）

逐条列在 `references/compliance.md`。改完先跑：
```
python scripts/verify_pythongo_compliance.py
```
（默认目标即待审查文件）。易踩的几条：

- `exchange` + `instrument_id` **成对**传入每个报单/订阅调用；
- 每个回调（`on_tick/on_order/on_trade/on_error/on_init/on_start/on_stop/set_params`）
  **首行 `super()`**；
- 所有可调值**只走 `params_map`**（用 `BaseParams` + `Field`），禁止散落魔数；
- 报单**终结状态精确匹配**（见下），不用子串匹配；
- **行宽 ≤ 80**；
- 框架调用**必须包异常**（单次冒泡会让该策略的 `on_tick` 之后全部停摆）。

### 报单终结状态（精确值，禁止子串）

```
ORDER_STATUS_FILLED   = ("全部成交", "部成部撤")   # 成交类终结
ORDER_STATUS_CANCELLED= ("已撤销",)               # 撤销类终结
EXIT_TERMINAL_STATUS  = ("已撤销", "部成部撤")    # 平仓单需清登记
```

⚠️ 用子串匹配会把「部成部撤还在队列中」误判为「部成部撤」终结 → 提前清登记 → 重复挂单。

## 二、12 条不可动摇的不变量（改前必读）

逐条事故与回归测试要求见 `references/invariants.md`，并由 `scripts/check_invariants.py`
做静态/运行时断言。**任一改动触碰下述条目，必须配回归测试，且门禁通过才允许上线。**

| # | 不变量 | 一句话 |
|---|---|---|
| ① | 先判定、后入窗 | `_run_quote_loop()` 用历史区间判定，再把本 tick 纳入区间；先入窗会让门恒真 |
| ② | 抬价容差必须 `+1e-9` | 写成 `-1e-9` 会让「持平」也判抬价 → 每 tick 撤挂刷单 |
| ③ | 撤单必须串行化 + 冷却 | 受理≠已撤；冷却自撤单发起时刻起算，回执到达不提前结束；回执可能丢失须超时兜底 |
| ④ | 回执判定顺序 | `on_order` 里「待确认撤单回执」判断必须排在「本地有在途单就 return」之前 |
| ⑤ | 禁止挂单单一真源 | 只由 `state_map.order_blocked` 承载，不引入内部镜像标志 |
| ⑥ | 报单被拒必须清本地登记 | 被拒不清登记 → 后续撤单回「不支持撤销未知单」→ 无限重试 → 静默停挂 |
| ⑦ | 持仓/待平必须【累加】 | 覆盖赋值会让「已有未平持仓」少算平仓量 → 平仓不足、超仓、风控失效 |
| ⑧ | 各等待/退避独立字段 | 否则「成交后首挂延时」顺带触发「撤单被拒重试」计时器 → 误撤已挂开仓单 |
| ⑨ | 框架调用必须包异常 | 单次异常冒泡打断 `on_tick`，使该策略后续 tick 完全不再被处理 |
| ⑩ | `on_trade` 订单归属过滤 | 框架把同合约所有成交投递给本策略；不过滤会把他方成交算成本地持仓 |
| ⑪ | 平仓「放弃」不得静默清零待平 | 清零 → 永久不再平仓、状态栏无异常（曾遗留 5 手）；须置 `_exit_stuck`+告警+慢重试+禁开仓 |
| ⑫ | 卡死标志必须有出口 | `_exit_stuck` 若只在慢重试清除，持仓被外部平掉后永久禁开仓；须连续读到账户零仓归零 |

## 三、推荐结构（巨石 → 可维护）

把**不依赖 `BaseStrategy` 的纯逻辑**抽成独立模块（可在无框架环境单测），
策略类只做「框架适配 + 编排」。完整包结构与每个方法的来源映射见
`references/module-layout.md`。要点：

- `session_calendar.py` 时段/交易日判定（纯函数）；
- `bollinger_range.py` K 线合成 + 布林带 + 越界判定；
- `gating.py` 时段门/风控门/盘口/开仓总门；
- `order_fsm.py` 开仓单生命周期（挂/撤/冷却/回执/重试）；
- `exit_manager.py` 两段式平仓 + 持仓采纳/对账；
- `strategy.py`（`SnowStrategy(BaseStrategy)`）只做编排与回调。

## 四、两段式平仓口径（老板裁定，逐字不变）

① 首挂恒用「成交价 + N 跳」固定止盈价；
② `exit_hold_min_sec`（默认 300s，自成交起算）内**不撤单、不跟追**；
③ 冷却期满仍未成交 → 跟追卖一价离场（此后持续跟追）；
④ 连续失败 `EXIT_RETRY_MAX`(20) 次 → 置 `_exit_stuck` + 告警 + 每 60s 慢重试 + 禁开仓
（**不静默卡死**，2026-09-29 授权新增）。

⚠️ 风控门（时段门/持仓上限/单日次数/单日亏损）**只禁开仓，绝不禁平仓**；平仓是风险出口。

## 五、上线前门禁（强制）

1. `python scripts/verify_pythongo_compliance.py <file>` —— PythonGO 官方规范；
2. `python scripts/check_invariants.py <file>` —— 本 skill 的 12 条不变量静态校验
   （`scripts/check_invariants.py` 为本 skill 自带工具，见 `references/`）；
3. 改动若触碰 §二 任一条不变量，补对应回归测试并跑通；
4. 行宽 ≤ 80、回调首行 super()、可调值只走 params_map。

## 六、配套资源

- `assets/strategy_template.py` —— 最小合规骨架（params/state/生命周期 + 不变量护栏注释）；
- `references/compliance.md` —— PythonGO 规范逐条说明；
- `references/invariants.md` —— 12 条不变量 + 每条事故与回归测试要求；
- `references/module-layout.md` —— 模块分解包结构与来源行号映射；
- `scripts/check_invariants.py` —— 不变量静态校验器。

> 使用本 skill 产出策略时，默认遵守以上全部约束；如需偏离某条不变量，必须在
> 策略文件对应位置写明偏离理由（事故级风险），并经显式授权。
