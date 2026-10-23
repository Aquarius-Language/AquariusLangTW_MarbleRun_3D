param([switch]$Android, [switch]$APK)
$ErrorActionPreference = 'Stop'
# 只使用 PATH 中的 aqua 編譯器。
if (!(Get-Command aqua -ErrorAction SilentlyContinue)) { throw '找不到 aqua，請先將星泉編譯器加入 PATH。' }
Push-Location $PSScriptRoot
try {
    & aqua bottle restore --project .
    if ($LASTEXITCODE) { throw 'Bottle 函式庫還原失敗。' }
    & aqua build . -o marble_run.wasm
    if ($LASTEXITCODE) { throw 'TOML 專案編譯失敗。' }
    & aqua build . --target web -o web
    if ($LASTEXITCODE) { throw '網頁輸出失敗。' }
    & aqua build . --target windows -o dist/marble_run.exe
    if ($LASTEXITCODE) { throw '桌面 EXE 輸出失敗。' }
    if ($Android -or $APK) {
        $輸出 = if ($APK) { 'dist/android.apk' } else { 'dist/android-' + [Guid]::NewGuid().ToString('N').Substring(0,8) }
        & aqua build . --target android -o $輸出
        if ($LASTEXITCODE) { throw 'Android 建置失敗。' }
    }
} finally { Pop-Location }
