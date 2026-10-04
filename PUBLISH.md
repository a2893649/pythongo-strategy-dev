# 发布到 awesome-deepseek-harness-plugins（1024 插件市场）

> 本文件是「提交到插件市场」的手把手说明。本机沙箱**没有** `gh`/`git`/`npm` 与 GitHub
> Token，故无法在此自动推送。以下步骤在你本地终端执行即可（已验证所需产物均齐备）。

## 市场提交规则（来自 CONTRIBUTING.md，摘要）
- 社区 PR **只能新增一个** `catalog/plugins/<owner>--<repo>.json` 文件，不得改其它文件。
- `id` 决定身份：仓库级插件为 `owner/repository`；子目录插件为 `owner/repository/sub/dir`。
- `repository` 字段必须等于 `https://github.com/<id 的 owner>/<id 的 repo>`。
- 必须保证你的 GitHub 仓库里已提交 `package.json`（声明 `dsh.bundle.patch`）**和** 该 patch
  文件（`cordis.patch.yml`）。静态门禁会经 GitHub API 读取你的仓库默认分支并校验这两项。
- `category` 必须来自官方允许列表（本包用 `skill`）。
- `added` = 提交日期（YYYY-MM-DD）。
- **安装有 npm-only 限制**：未发布到 npm 的包仍会被收录，但只显示仓库链接（browse-only），
  **没有安装按钮**。发布 npm 后市场自动识别并出现安装命令，无需再提 PR。

## 步骤一：准备 GitHub 仓库
1. 在 GitHub 新建仓库 `pythongo-strategy-dev`（公开）。
2. 把本目录全部内容 push（已就绪：`package.json` 已改回公开可发布形态、`cordis.patch.yml`、
   `index.js`、`skills/`、`references/`、`assets/`、`scripts/`、`icon.svg`、`locale/` 等）。
3. 确保默认分支为 `main`，且 `package.json` 的 `repository.url` / `author` 改成你的账号。

## 步骤二：提交流 catalog PR（browse-only，无需 npm）
1. Fork `imsai-sh/awesome-deepseek-harness-plugins`。
2. 仅新增一个文件：`catalog/plugins/a2893649--pythongo-strategy-dev.json`，内容如下
   （日期改成当天）：
```json
{
  "$schema": "../schema/plugin.schema.json",
  "id": "a2893649/pythongo-strategy-dev",
  "name": "pythongo-strategy-dev",
  "repository": "https://github.com/a2893649/pythongo-strategy-dev",
  "category": "skill",
  "description": {
    "en": "A PythonGO live-trading strategy development skill: minimal-compliant skeleton, a static gate for 12 non-negotiable invariants, and module-layout templates. Encodes real incident-derived rules (precise termination-status matching, plus-or-minus 1e-9 hike tolerance, order-ownership filtering).",
    "zh": "PythonGO 实盘策略开发技能：最小合规骨架、12 条不可动摇的不变量静态门禁与模块分解模板，固化自真实事故口径（报单终结状态精确匹配、抬价容差 +1e-9、订单归属过滤等）。"
  },
  "added": "2026-10-04"
}
```
3. 开 PR（非 draft），唯一改动就是上面这一个 json。静态门禁（auto-merge）通过后会被自动
   squash 合并，并自动同步进 1024 市场目录。此时为 **browse-only**（有仓库链接，无安装按钮）。

## 步骤三：（可选）发布 npm，让市场出现「安装」按钮
1. `npm login`（需 npm 账号）。
2. 在本目录执行 `npm publish --access public`。
   - `package.json` 已是公开形态、含 `dsh.bundle.patch`，`files` 含全部运行时文件。
   - 安装命令 `dsh plugin install pythongo-strategy-dev` 由市场自动从已发布 npm 包生成。
3. 发布后市场自动重新抓取，**无需再提 PR**。

## 校验清单（提交前自检）
- [ ] `package.json` 中 `name` 可发布（非 `@local/*`、`private` 已移除）、`dsh.bundle.patch` 存在
- [ ] 仓库根已提交 `package.json` 与 `cordis.patch.yml`
- [ ] catalog json 仅此一个新增文件，文件名 `a2893649--pythongo-strategy-dev.json`
- [ ] `id`/`repository`/`category`/`added` 与本文一致；`description.en/zh` 客观无夸张
- [ ] `added` 为当天日期

## 故障排查
- 门禁报 `dsh.bundle.patch does not exist`：确认 `cordis.patch.yml` 已 commit 且路径与
  `package.json` 中 `dsh.bundle.patch` 一致（当前为 `./cordis.patch.yml`）。
- 门禁报 `repository must be ...`：把 json 的 `repository` 改成与 `id` 推导出的 URL 完全一致。
- 仅 browse-only 无安装按钮：尚未发布 npm，属预期（见上「步骤三」）。
