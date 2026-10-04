# pythongo-strategy-dev

一个按 **PythonGO 实盘规范**封装的 DeepSeek Harness 技能包（skill bundle）。它把「PythonGO
期权/期货实盘策略」的开发、审查、封装流程标准化为可复用、可校验的技能，并自带 12 条
「不可动摇的不变量」静态门禁。

> 所有口径来自真实实盘事故反推（见 `skills/pythongo-strategy-dev/SKILL.md`）。改动策略前
> 必须逐条核对不变量；改完必须跑门禁，门禁不通过不得上线。

## 安装

### 方式一：从 1024 插件市场（推荐，需已发布 npm 包）
```bash
dsh plugin install pythongo-strategy-dev
```
或从 [deepseek1024.com](https://deepseek1024.com/) 一键安装。

### 方式二：从 Git 仓库直接装（npm install 失败或想用最新源码）
```bash
dsh plugin install github:a2893649/pythongo-strategy-dev
```

### 方式三：本地 profile 安装（开发/测试）
```bash
# 在本目录执行，由 plugin_manager 完成 pnpm link 与 bundle 挂载
dsh plugin install ./   # 或指向本目录绝对路径
```

安装后技能 `pythongo-strategy-dev` 会出现在可用技能目录；在对话中说「按 PythonGO 规范
写/改/审查一个策略」即会触发。

## 包含内容
- `skills/pythongo-strategy-dev/SKILL.md` —— 规范 + 12 不变量 + 模块分解 + 上线门禁
- `references/` —— compliance / invariants / module-layout 三份说明
- `assets/strategy_template.py` —— 最小合规骨架（params/state/生命周期 + 不变量护栏注释）
- `scripts/check_invariants.py` —— 12 条不变量静态校验器
- `index.js` —— 零依赖「打包 skill 提供者」，枚举本包 `skills/` 目录并暴露给 Harness 技能注册表
- `cordis.patch.yml` —— 注入插件行

## 使用
新建/审查策略时，调用技能后按其 §五 门禁执行：
```bash
python scripts/check_invariants.py <策略文件.py>
# 再加官方规范校验（若仓库提供 scripts/verify_pythongo_compliance.py）
```

## 不变量（节选，完整见 SKILL.md §二）
① 先判定后入窗 · ② 抬价容差 `+1e-9` · ③ 撤单串行化+冷却 · ④ 回执判定顺序 ·
⑤ 禁止挂单单一真源 · ⑥ 报单被拒不留登记 · ⑦ 持仓/待平累加 · ⑧ 各等待/退避独立 ·
⑨ 框架调用包异常 · ⑩ on_trade 订单归属过滤 · ⑪ 平仓放弃不清零待平 · ⑫ 卡死标志有出口。

## 发布到 1024 插件市场
见 `PUBLISH.md`（本目录）。
