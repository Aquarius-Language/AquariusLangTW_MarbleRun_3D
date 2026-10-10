param([string]$編譯器 = 'aqua', [switch]$桌面)
$ErrorActionPreference = 'Stop'

$原主控台輸出編碼 = [Console]::OutputEncoding
$原輸出編碼 = $OutputEncoding
Push-Location $PSScriptRoot
try {
    # aqua 使用 UTF-8 輸出；Windows PowerShell 需要明確指定解碼方式。
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
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
} finally {
    [Console]::OutputEncoding = $原主控台輸出編碼
    $OutputEncoding = $原輸出編碼
    Pop-Location
}
