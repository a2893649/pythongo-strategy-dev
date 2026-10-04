<#
 .SYNOPSIS
   一键把 pythongo-strategy-dev 上架到 deepseek1024.com（即提交到
   imsai-sh/awesome-deepseek-harness-plugins 的 catalog PR，市场自动同步）。

 .DESCRIPTION
   本脚本在「已安装 gh 且已登录」的机器上运行（沙箱内无 gh/git，故需你本地执行）：
     1) 初始化 git 并提交本目录全部文件；
     2) 创建 GitHub 仓库 a2893649/pythongo-strategy-dev（需 token 具备 repo 权限）；
     3) push 到 main；
     4) Fork 市场仓库、开 PR，仅新增 catalog/plugins/a2893649--pythongo-strategy-dev.json。
   市场读取该 PR 合并后自动出现在 deepseek1024.com（先为 browse-only 仓库链接）。

 .PREREQUISITES
   - 安装 git 与 GitHub CLI：winget install Git.Git GitHub.cli
   - 登录：gh auth login  （或用下方 $Token 环境变量 / 脚本顶部填写）
   - 确认用户名：下方 $Owner 必须为 a2893649（与 catalog id 一致）

 .USAGE
   pwsh ./submit-to-1024.ps1            # 交互式：脚本会提示输入 token（不回显）
   $env:GH_TOKEN="ghp_xxx"; pwsh ./submit-to-1024.ps1
#>

param(
    [string]$Owner = "a2893649",
    [string]$Repo  = "pythongo-strategy-dev",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition

# ---- 1. 凭证 ----
if (-not $env:GH_TOKEN) {
    $secure = Read-Host -Prompt "粘贴 GitHub token（需 repo 权限，输入不回显）" -AsSecureString
    $env:GH_TOKEN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}
$env:GH_TOKEN = $env:GH_TOKEN.Trim()
gh auth status > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    # 用 token 登录（仅设置凭据，不修改 git 配置）
    $null = $env:GH_TOKEN | gh auth login --with-token
}

# ---- 2. 校验 gh 已登录且为正确账号 ----
$whoami = (gh api user --jq .login).Trim()
if ($whoami -ne $Owner) {
    throw "当前 gh 登录账号为 '$whoami'，但 catalog id 要求 owner 为 '$Owner'。请先 `gh auth login` 切换到 $Owner。"
}

# ---- 3. 初始化 git 并提交 ----
Set-Location $here
if (-not (Test-Path .git)) { git init -q }
git config user.email | Out-Null
if (-not (git config user.email)) { git config user.email "$Owner@users.noreply.github.com" }
if (-not (git config user.name))  { git config user.name  $Owner }
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -q -m "feat: pythongo-strategy-dev skill bundle"
} else {
    Write-Host "（无新改动，跳过 commit）"
}

# ---- 4. 创建远程仓库（若不存在）并 push ----
$exists = gh repo view "$Owner/$Repo" > $null 2>&1; $null = $?
if (-not $exists) {
    gh repo create "$Repo" --public --description "PythonGO 实盘策略开发 skill bundle（上架 deepseek1024.com）"
} else {
    Write-Host "远程仓库已存在：$Owner/$Repo"
}
$remoteUrl = "https://github.com/$Owner/$Repo.git"
if (-not (git remote | Where-Object { $_ -eq "origin" })) {
    git remote add origin $remoteUrl
} else {
    git remote set-url origin $remoteUrl
}
git branch -M $Branch
git push -u origin $Branch --force

# ---- 5. Fork 市场仓库并开 catalog PR ----
$CatalogRepo = "imsai-sh/awesome-deepseek-harness-plugins"
gh repo fork $CatalogRepo --clone=false --remote=true
$Fork = "$Owner/awesome-deepseek-harness-plugins"

# 取市场默认分支名
$BaseBranch = (gh repo view $CatalogRepo --json defaultBranchRef --jq .defaultBranchRef.name)
if (-not $BaseBranch) { $BaseBranch = "main" }

# 本地建提交分支
git clone "https://github.com/$Fork.git" "$env:TEMP\dsh-catalog-fork" -q
Set-Location "$env:TEMP\dsh-catalog-fork"
git remote add upstream "https://github.com/$CatalogRepo.git"
git fetch upstream $BaseBranch -q
git checkout -b "add-$Repo" "upstream/$BaseBranch"

# 仅新增 catalog 文件
$CatSrc = Join-Path $here "catalog-entry\a2893649--pythongo-strategy-dev.json"
$CatDst = "catalog\plugins\a2893649--pythongo-strategy-dev.json"
Copy-Item $CatSrc $CatDst -Force
git add "$CatDst"
git commit -q -m "catalog: add $Owner/$Repo"

git push -u origin "add-$Repo" --force

gh pr create `
    --repo $CatalogRepo `
    --head "$Fork:add-$Repo" `
    --base $BaseBranch `
    --title "catalog: add $Owner/$Repo" `
    --body "Add pythongo-strategy-dev to the catalog.`n`n- id: $Owner/$Repo`n- category: skill`n- repository: https://github.com/$Owner/$Repo`n- Source repo already contains package.json with dsh.bundle.patch and the referenced cordis.patch.yml.`n- Browse-only entry (no npm publish yet); install via git link or dsh plugin install github:$Owner/$Repo." `
    --web

Write-Host ""
Write-Host "完成：PR 已开。合并后 pythongo-strategy-dev 会自动出现在 https://deepseek1024.com/ "
Write-Host "（先为 browse-only 仓库链接；如需 dsh plugin install 安装按钮，本地再 `npm publish --access public`。）"
