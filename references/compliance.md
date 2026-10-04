# PythonGO 官方规范逐条（硬约束）

> 来源：snow.py 文件头 §七。规范不在文件头复述（复述会与代码漂移），改完先跑
> `python scripts/verify_pythongo_compliance.py`（默认目标即待审查文件）。

## 1. 成对传参
`exchange` 与 `instrument_id` 必须**成对**传入每个报单/订阅调用。漏掉其一会让 tick
过滤或报单落错合约。

## 2. 回调首行 super()
`on_tick / on_order / on_trade / on_error / on_init / on_start / on_stop / set_params`
**必须**先调 `super().<method>(...)` 再写本策略逻辑。父类负责框架侧预处理
（如 `on_tick` 刷新交易态、`set_params` 写 `params_map`）。

## 3. 可调值只走 params_map
所有用户可调值用 `BaseParams` + `Field` 声明（带 `title`），运行时只改 `params_map`。
禁止在方法里散落魔数（阈值如需注释标定依据，写在 `Field` 默认值附近的注释里）。

## 4. 报单终结状态精确匹配
见 SKILL.md §一。取值来自 `pythongo.types.TypeOrderStatus`，必须精确相等，
禁止子串 `"部成部撤" in status` 这类写法。

## 5. 行宽 ≤ 80
PEP8 风格硬要求；实测是该仓库门禁脚本的失败项之一。

## 6. 框架调用包异常
`send_order / cancel_order / get_position / update_status_bar` 等框架副作用一律经
统一异常包裹（如 `_try(fn, what, ...)`），失败仅记日志，绝不冒泡打断 `on_tick`。

## 7. oid=0 合法
PythonGO 从 0 计数，`oid == 0` 是合法报单编号。判「成功」须
`oid is not None and oid != -1`；判「存在」用 `is not None`，禁止 `if oid:`。

## 8. 报单方向常量共用
`on_order` / `on_trade` 的方向过滤共用 `BUY_DIRS = ("0","buy","BUY")`，
避免两处各写一份导致漏判。

## 9. 状态栏节流
报单/持仓/统计等「关键字段」变化立即刷 UI；行情展示类（区间高低、样本数、挂单基准价、
时段门）按 `STATE_PUSH_MIN_SEC` 节流，避免把 IPC 打成每 tick 一次。

## 门禁脚本
```
python scripts/verify_pythongo_compliance.py <target_file.py>
```
默认目标即待审查文件。核心几条（易踩）：成对传参、`super()`、可调值走 params_map、
终止状态精确匹配、行宽 ≤80。
