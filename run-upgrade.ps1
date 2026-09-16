param(
    [switch]$Probe,
    [int]$Seconds = 0,
    [switch]$Echo
)

# run-upgrade.ps1 —— 启动「升级版」网关（与 MVP 各跑各的，互不影响）
#
#   启动：.\run-upgrade.ps1
#   探针：.\run-upgrade.ps1 -Probe                验证权限 / 文件下载是否通
#   限时：.\run-upgrade.ps1 -Probe -Seconds 20    跑 20 秒自动退出（看结果用）
#   回执：.\run-upgrade.ps1 -Probe -Echo          探针额外回一句话（顺带验发送权限）
#         —— -Echo 只在 -Probe 下生效：--echo 由 tools\probe_feishu.py 认，网关侧不认
#   停止：网关窗口按 Ctrl+C
#
# 它干三件事：
#   ① 把 .env.upgrade 的值临时喂给本次进程（环境变量优先于 .env，见 src/config.py）
#   ② 指定升级版专属数据根与单实例锁端口（否则会被 MVP 的 47653 端口挡在门外）
#   ③ 启动长连接（不占公网、不需要回调地址）
#
# 关键：只改当前窗口的环境变量，退出时清掉 —— 同一个窗口再跑 MVP 也不会串凭据。
# 注意：本文件必须存成「UTF-8 带 BOM」，否则 Windows PowerShell 5.1 会把中文读成乱码并报语法错。

$ErrorActionPreference = 'Stop'
$repo    = $PSScriptRoot
$envFile = Join-Path $repo '.env.upgrade'

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Host "[启动中止] 找不到 $envFile —— 先照格式把升级版凭据填好。" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host '[启动中止] PATH 里找不到 python。' -ForegroundColor Red
    exit 1
}

$loaded = @()
foreach ($line in [System.IO.File]::ReadAllLines($envFile)) {
    $t = $line.Trim()
    if (-not $t -or $t.StartsWith('#')) { continue }
    $i = $t.IndexOf('=')
    if ($i -lt 1) {
        Write-Host "[启动中止] $envFile 里有不带变量名的行：$t" -ForegroundColor Red
        exit 1
    }
    $name  = $t.Substring(0, $i).Trim()
    $value = $t.Substring($i + 1).Trim().Trim('"').Trim("'")
    Set-Item -Path ('Env:' + $name) -Value $value
    $loaded += $name
}

if (-not $env:FEISHU_APP_ID -or -not $env:FEISHU_APP_SECRET) {
    Write-Host '[启动中止] FEISHU_APP_ID / FEISHU_APP_SECRET 还是空的，先去 .env.upgrade 填。' -ForegroundColor Red
    exit 1
}

$env:DATA_DIR          = Join-Path $repo 'data-upgrade'
$env:GATEWAY_LOCK_PORT = '47654'
$loaded += 'DATA_DIR', 'GATEWAY_LOCK_PORT'

$extra = @()
if ($Seconds -gt 0) { $extra += @('--seconds', "$Seconds") }
# -Echo 只在探针下有意义：'--echo' 是 tools\probe_feishu.py 的参数，
# src\gateway\app.py 的 argparse 认不出它（不带 -Probe 时透传 ⇒ 启动必 exit 2）。
# 网关侧要新的开关就另开一个参数，别复用这个。
if ($Echo -and $Probe) { $extra += '--echo' }
$argv = @($extra) + @($args)

try {
    Set-Location -LiteralPath $repo
    Write-Host "[升级版] 数据根 = $env:DATA_DIR"
    Write-Host "[升级版] 锁端口 = $env:GATEWAY_LOCK_PORT（MVP 用 47653）"
    $ErrorActionPreference = 'Continue'   # 别让原生程序写 stderr 被当成致命错误
    if ($Probe) {
        Write-Host '[升级版] 跑探针：重点看「文件下载权限是通的」那一行。'
        python -m tools.probe_feishu --save-dir (Join-Path $env:DATA_DIR 'probe') @argv
    } else {
        Write-Host '[升级版] 正在建立长连接（首次加载 SDK 约 20 秒）…'
        python -m src.gateway.app @argv
    }
    Write-Host "[升级版] 进程已退出（exit=$LASTEXITCODE）。"
}
finally {
    foreach ($n in $loaded) { Remove-Item -Path ('Env:' + $n) -ErrorAction SilentlyContinue }
}