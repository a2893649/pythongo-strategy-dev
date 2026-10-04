$ErrorActionPreference = 'Stop'
$here = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }

$cred = ("protocol=https`nhost=github.com`n`n" | & 'C:\Program Files\Git\cmd\git.exe' credential fill 2>$null)
$token = ($cred | Where-Object { $_ -like 'password=*' }) -replace '^password='
$owner = 'a2893649'
$repo  = 'pythongo-strategy-dev'
$catalogRepo = 'imsai-sh/awesome-deepseek-harness-plugins'
$api = 'https://api.github.com'

function api($method, $path, $bodyObj) {
    $url = "$api$path"
    $hdr = "-H", "Authorization: Bearer $token", "-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2022-11-28", "-H", "Content-Type: application/json"
    $args = @('-sS', '-X', $method, $url) + $hdr
    if ($bodyObj) { $args += '-d', ($bodyObj | ConvertTo-Json -Compress -Depth 8) }
    $json = & curl.exe @args
    if ($LASTEXITCODE -ne 0) { throw "curl failed ($method $path): $json" }
    if ($json) { return $json | ConvertFrom-Json } else { return $null }
}

Write-Host "==> 1) create source repo $owner/$repo"
try {
    api POST "/user/repos" @{ name=$repo; description="PythonGO live-trading strategy dev skill bundle (for deepseek1024.com)"; private=$false; auto_init=$false } | Out-Null
    Write-Host "    created"
} catch {
    if ($_ -match 'already exist') { Write-Host "    already exists, skip" }
    else { Write-Host "    $_"; throw }
}

Write-Host "==> 2) commit and push source"
$env:GIT_CEILING_DIRECTORIES = (Split-Path $here -Parent)
if (-not (Test-Path (Join-Path $here ".git"))) { & 'C:\Program Files\Git\cmd\git.exe' -C $here init -q 2>$null }
& 'C:\Program Files\Git\cmd\git.exe' -C $here config user.email "$owner@users.noreply.github.com"
& 'C:\Program Files\Git\cmd\git.exe' -C $here config user.name  $owner
& 'C:\Program Files\Git\cmd\git.exe' -C $here add -A 2>$null
& 'C:\Program Files\Git\cmd\git.exe' -C $here diff --cached --quiet 2>$null; $null=$?
if ($LASTEXITCODE -ne 0) { & 'C:\Program Files\Git\cmd\git.exe' -C $here commit -q -m "feat: pythongo-strategy-dev skill bundle" 2>$null }
else { Write-Host "    no changes" }
$pushUrl = "https://$owner`:$token@github.com/$owner/$repo.git"
& 'C:\Program Files\Git\cmd\git.exe' -C $here branch -M main 2>$null
$pushOut = & 'C:\Program Files\Git\cmd\git.exe' -C $here push $pushUrl main --force 2>&1
$pushOut | Where-Object { $_ -notmatch 'github.com' } | ForEach-Object { Write-Host "    $_" }

Write-Host "==> 3) fork market repo $catalogRepo"
try { api POST "/repos/$catalogRepo/forks" $null | Out-Null; Write-Host "    fork started" }
catch { if ($_ -match 'already') { Write-Host "    already forked" } else { Write-Host "    $_"; throw } }
$forkReady = $false
for ($i=0; $i -lt 24; $i++) {
    try { api GET "/repos/$owner/awesome-deepseek-harness-plugins" $null | Out-Null; $forkReady=$true; break }
    catch { Start-Sleep -Seconds 3 }
}
if (-not $forkReady) { throw "fork not ready in time, retry later" }
Write-Host "    fork ready"

Write-Host "==> 4) add catalog file on branch"
$defaultBranch = (api GET "/repos/$catalogRepo" $null).default_branch
$catalogPath = "catalog/plugins/a2893649--pythongo-strategy-dev.json"
$catalogBytes = [IO.File]::ReadAllBytes((Join-Path $here "catalog-entry\a2893649--pythongo-strategy-dev.json"))
$b64 = [Convert]::ToBase64String($catalogBytes)
$branch = "add-$repo"
api PUT "/repos/$owner/awesome-deepseek-harness-plugins/contents/$catalogPath" @{
    message = "catalog: add $owner/$repo"
    content = $b64
    branch  = $branch
} | Out-Null
Write-Host "    catalog file committed to $branch (base=$defaultBranch)"

Write-Host "==> 5) open PR"
$pr = api POST "/repos/$catalogRepo/pulls" @{
    title = "catalog: add $owner/$repo"
    head  = "${owner}:${branch}"
    base  = $defaultBranch
    body  = "Add pythongo-strategy-dev to the catalog.`n`n- id: $owner/$repo`n- category: skill`n- repository: https://github.com/$owner/$repo`n- Source repo already contains package.json declaring dsh.bundle.patch and the referenced cordis.patch.yml.`n- Browse-only entry (no npm publish yet); installable via git: dsh plugin install github:$owner/$repo."
}
Write-Host "    PR created: $($pr.html_url)"

$pj = (api GET "/repos/$owner/$repo/contents/package.json" $null).download_url
$patch = (api GET "/repos/$owner/$repo/contents/cordis.patch.yml" $null).download_url
Write-Host "==> gate check: package.json -> $pj"
Write-Host "              cordis.patch.yml -> $patch"
Write-Host "DONE"
