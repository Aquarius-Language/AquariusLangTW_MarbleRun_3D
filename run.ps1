param(
    [string]$VmPath = 'AquariusDesktopVMREPL.exe'
)

# Launch from any working directory using a prebuilt desktop VM distribution.
$ErrorActionPreference = 'Stop'
$marbleEntry = Join-Path $PSScriptRoot 'main.aqua'
& $VmPath $marbleEntry
exit $LASTEXITCODE
