param([string]$AppDirectory = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$AppDirectory = (Resolve-Path -LiteralPath $AppDirectory).Path
$manifest = Join-Path $AppDirectory 'shell_extension\AppxManifest.xml'
$library = Join-Path $AppDirectory 'WinCipShell-3.2.dll'
if (!(Test-Path -LiteralPath $library)) { throw 'No se encuentra WinCipShell-3.2.dll junto a WinCip.exe.' }
[xml]$definition = Get-Content -LiteralPath $manifest
$existing = Get-AppxPackage -Name 'WinCip.ShellExtension'
$expectedVersion = [version]$definition.Package.Identity.Version
$expectedLocation = Split-Path -Parent $manifest
if (!$existing -or $existing.Version -ne $expectedVersion -or $existing.InstallLocation -ne $expectedLocation -or $existing.Status -ne 'Ok') {
 Add-AppxPackage -Register $manifest -ExternalLocation $AppDirectory
}
$package = Get-AppxPackage -Name 'WinCip.ShellExtension'
if (!$package -or $package.Status -ne 'Ok') { throw 'Windows no confirmó el registro de WinCip.' }
Write-Output 'Menú de WinCip instalado en el Explorador de Windows 11.'
