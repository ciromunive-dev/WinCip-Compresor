$ErrorActionPreference = 'Stop'
Get-AppxPackage -Name 'WinCip.ShellExtension' | Remove-AppxPackage
$owned = @(
 'HKCU:\Software\Classes\*\shell\WinCip',
 'HKCU:\Software\Classes\Directory\shell\WinCip',
 'HKCU:\Software\Classes\CLSID\{D4E07230-5AF0-4E95-A8A0-80D732CC1791}'
)
foreach ($key in $owned) {
 if (Test-Path -LiteralPath $key) { Remove-Item -LiteralPath $key -Recurse }
}
Write-Output 'Menú de WinCip retirado.'
