param([string]$編譯器 = '', [switch]$桌面, [switch]$Android, [switch]$APK)
$ErrorActionPreference = 'Stop'
if (!$編譯器) { $編譯器 = Join-Path $PSScriptRoot '../AquariusLangTW/dist/aqua-current/aqua.exe'; if (!(Test-Path -LiteralPath $編譯器)) { $編譯器 = 'aqua' } }
Push-Location $PSScriptRoot
try {
    & $編譯器 bottle restore --project .
    if ($LASTEXITCODE) { throw 'Bottle 函式庫還原失敗。' }
    & $編譯器 build . -o marble_run.wasm
    if ($LASTEXITCODE) { throw 'TOML 專案編譯失敗。' }
    & $編譯器 build . --target web -o web
    if ($LASTEXITCODE) { throw '網頁輸出失敗。' }
    if ($桌面) { & $編譯器 build . --target windows -o dist/marble_run.exe; if ($LASTEXITCODE) { throw '桌面輸出失敗。' } }
    if ($Android -or $APK) {
        $輸出 = if ($APK) { 'dist/android.apk' } else { 'dist/android-' + [Guid]::NewGuid().ToString('N').Substring(0,8) }
        & $編譯器 build . --target android -o $輸出
        if ($LASTEXITCODE) { throw 'Android 建置失敗。' }
    }
} finally { Pop-Location }
