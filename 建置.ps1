param([string]$編譯器 = '', [string]$參考專案 = 'C:\OfficialProjects\AquariusLangTW', [switch]$桌面)
$ErrorActionPreference = 'Stop'

if (-not $編譯器) {
    $開發編譯器 = Join-Path $參考專案 'dist/aqua/aqua.exe'
    if (Test-Path -LiteralPath $開發編譯器) { $編譯器 = $開發編譯器 }
    else {
        $最新套件 = Get-ChildItem -LiteralPath (Join-Path $參考專案 'dist/releases') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
        if ($最新套件) { $編譯器 = Join-Path $最新套件.FullName 'aqua/aqua.exe' }
    }
}
if (-not $編譯器 -or -not (Test-Path -LiteralPath $編譯器)) { throw '找不到星泉編譯器，請用 -編譯器 指定新版 aqua.exe。' }

Push-Location $PSScriptRoot
try {
    $來源 = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.aqua' | Sort-Object Name | ForEach-Object FullName)
    & $編譯器 build @來源 --root . --entry main.aqua -o marble_run.wasm
    if ($LASTEXITCODE -ne 0) { throw '彈珠原始碼編譯失敗。' }
    & $編譯器 build marble_run.wasm --target web -o web
    if ($LASTEXITCODE -ne 0) { throw '網頁輸出失敗。' }
    if ($桌面) {
        & $編譯器 build marble_run.wasm --target windows -o dist/marble_run.exe
        if ($LASTEXITCODE -ne 0) { throw '桌面輸出失敗。' }
    }
    Write-Output '完成：marble_run.wasm 與 ./web。'
} finally { Pop-Location }
