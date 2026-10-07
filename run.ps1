# Launch from any working directory. dotnet restores the VM's native packages.
$ErrorActionPreference = 'Stop'
$marbleVmProject = Join-Path $PSScriptRoot '..\AquariusDesktopVMREPL\AquariusDesktopVMREPL.csproj'
$marbleEntry = Join-Path $PSScriptRoot 'main.aqua'
& dotnet run --project $marbleVmProject -c Release -- $marbleEntry
exit $LASTEXITCODE
