Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!define APP "WinCip Compresor"
!define PRODUCT_ID "WinCip.Compresor.3"
!define ARP "Software\Microsoft\Windows\CurrentVersion\Uninstall\WinCip"
!define ROOT "${__FILEDIR__}\.."
Name "${APP}"
OutFile "${ROOT}\release\WinCip-Compresor-3.2.0-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\WinCip"
InstallDirRegKey HKCU "${ARP}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetDatablockOptimize on
BrandingText "WinCip Compresor 3.2.0"
VIProductVersion "3.2.0.0"
VIAddVersionKey /LANG=3082 "ProductName" "${APP}"
VIAddVersionKey /LANG=3082 "FileDescription" "Instalador de ${APP}"
VIAddVersionKey /LANG=3082 "FileVersion" "3.2.0"
VIAddVersionKey /LANG=3082 "LegalCopyright" "2026 WinCip Compresor contributors"
!define MUI_ICON "${ROOT}\WinCip.ico"
!define MUI_UNICON "${ROOT}\WinCip.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "${__FILEDIR__}\header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${__FILEDIR__}\welcome.bmp"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Instalar WinCip Compresor"
!define MUI_WELCOMEPAGE_TEXT "Comprime, explora y extrae tus archivos en tu equipo.$\r$\n$\r$\nEl asistente instalará la aplicación para tu usuario. No necesitas instalar Python ni 7-Zip por separado.$\r$\n$\r$\nCierra WinCip antes de actualizar."
!define MUI_FINISHPAGE_RUN "$INSTDIR\WinCip.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${ROOT}\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "Spanish"
Var NoShortcuts
Var Integrated

Section "Aplicación y documentación" Core
  SectionIn RO
  Call .onVerifyInstDir
  SetShellVarContext current
  SetRegView 64
  ReadINIStr $Integrated "$INSTDIR\WinCip.install.ini" "Install" "Integration"
  SetOutPath "$INSTDIR"
  SetOverwrite on
  !include "${ROOT}\build\installer-files.nsh"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "Product" "${PRODUCT_ID}"
  WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "Architecture" "x64"
  WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "Integration" "$Integrated"
  WriteRegStr HKCU "${ARP}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${ARP}" "DisplayVersion" "3.2.0"
  WriteRegStr HKCU "${ARP}" "DisplayIcon" "$INSTDIR\WinCip.exe,0"
  WriteRegStr HKCU "${ARP}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${ARP}" "UninstallString" '$\"$INSTDIR\Desinstalar.exe$\"'
  WriteRegStr HKCU "${ARP}" "QuietUninstallString" '$\"$INSTDIR\Desinstalar.exe$\" /S'
  WriteRegDWORD HKCU "${ARP}" "NoModify" 1
  WriteRegDWORD HKCU "${ARP}" "NoRepair" 1
  WriteRegDWORD HKCU "${ARP}" "EstimatedSize" 41000
  ${If} $NoShortcuts != 1
    CreateDirectory "$SMPROGRAMS\${APP}"
    CreateShortcut "$SMPROGRAMS\${APP}\${APP}.lnk" "$INSTDIR\WinCip.exe"
    CreateShortcut "$SMPROGRAMS\${APP}\Guía de uso.lnk" "$INSTDIR\docs\USO.md"
    CreateShortcut "$SMPROGRAMS\${APP}\Desinstalar.lnk" "$INSTDIR\Desinstalar.exe"
    WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "StartMenu" "1"
  ${EndIf}
SectionEnd

Section "Menú del Explorador y opción Abrir con" Shell
  DetailPrint "Registrando las acciones de archivos..."
  nsExec::ExecToLog '$\"$INSTDIR\WinCip.exe$\" --register-shell'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_OK|MB_ICONEXCLAMATION "La aplicación se instaló, pero no se pudo registrar el menú del Explorador." /SD IDOK
    SetErrorLevel 2
  ${Else}
    WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "Integration" "1"
  ${EndIf}
SectionEnd

Section /o "Menú moderno de Windows 11 (opcional)" Modern
  nsExec::ExecToLog '$\"$INSTDIR\WinCip.exe$\" --register-shell --modern'
  Pop $0
  WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "Integration" "1"
  ${If} $0 != 0
    WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "ModernMenu" "Unavailable"
    MessageBox MB_OK|MB_ICONINFORMATION "Windows no permitió activar el menú moderno. Las acciones siguen disponibles en Mostrar más opciones." /SD IDOK
  ${Else}
    WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "ModernMenu" "Registered"
  ${EndIf}
SectionEnd

Section /o "Acceso directo en el escritorio" Desktop
  CreateShortcut "$DESKTOP\${APP}.lnk" "$INSTDIR\WinCip.exe"
  WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "Desktop" "1"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${Core} "Programa, motor de formatos, licencias y documentación."
  !insertmacro MUI_DESCRIPTION_TEXT ${Shell} "Añade abrir, extraer y comprimir al menú del Explorador. Conserva tu aplicación predeterminada actual."
  !insertmacro MUI_DESCRIPTION_TEXT ${Modern} "Intenta añadir las acciones al menú principal de Windows 11 si Windows permite registrar el paquete."
  !insertmacro MUI_DESCRIPTION_TEXT ${Desktop} "Crea un acceso directo a WinCip Compresor en tu escritorio."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Function .onInit
  ${IfNot} ${IsNativeAMD64}
    MessageBox MB_OK|MB_ICONSTOP "Esta versión necesita Windows x64 (Intel o AMD)."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "Esta versión necesita Windows 10 o posterior."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin11}
    SectionSetFlags ${Modern} 0
    SectionSetText ${Modern} ""
  ${EndIf}
  SetRegView 64
  StrCpy $NoShortcuts 0
  ${GetParameters} $R0
  ${GetOptions} $R0 "/NOINTEGRATION" $R1
  ${IfNot} ${Errors}
    SectionSetFlags ${Shell} 0
    SectionSetFlags ${Modern} 0
  ${EndIf}
  ClearErrors
  ${GetOptions} $R0 "/NOSTARTMENU" $R1
  ${IfNot} ${Errors}
    StrCpy $NoShortcuts 1
  ${EndIf}
FunctionEnd

Function .onVerifyInstDir
  IfFileExists "$INSTDIR\WinCip.install.ini" owned
  FindFirst $0 $1 "$INSTDIR\*.*"
  scan:
    StrCmp $1 "" empty
    StrCmp $1 "." next
    StrCmp $1 ".." next
    FindClose $0
    Abort
  next:
    FindNext $0 $1
    Goto scan
  empty:
    FindClose $0
    Return
  owned:
    ReadINIStr $0 "$INSTDIR\WinCip.install.ini" "Install" "Product"
    StrCmp $0 "${PRODUCT_ID}" valid
    Abort
  valid:
    ReadINIStr $0 "$INSTDIR\WinCip.install.ini" "Install" "Architecture"
    ${If} $0 == "x86"
      MessageBox MB_OK|MB_ICONSTOP "Desinstala primero la edición x86 de WinCip antes de instalar la edición x64." /SD IDOK
      Abort
    ${EndIf}
FunctionEnd

Function un.onInit
  SetRegView 64
  ReadINIStr $0 "$INSTDIR\WinCip.install.ini" "Install" "Product"
  ${If} $0 != "${PRODUCT_ID}"
    MessageBox MB_OK|MB_ICONSTOP "No se reconoce esta carpeta como una instalación de WinCip."
    Abort
  ${EndIf}
  IfFileExists "$INSTDIR\WinCip.exe" 0 available
  StrCpy $R0 0
  retry_executable:
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\WinCip.exe", i 0x40000000, i 7, p 0, i 3, i 0, p 0) p.r0'
  ${If} $0 == -1
    IntOp $R0 $R0 + 1
    ${If} $R0 < 8
      Sleep 500
      Goto retry_executable
    ${EndIf}
    MessageBox MB_OK|MB_ICONEXCLAMATION "Cierra WinCip antes de desinstalarlo." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  System::Call 'kernel32::CloseHandle(p r0)'
  available:
FunctionEnd

Section "Uninstall"
  SetShellVarContext current
  SetRegView 64
  ReadINIStr $0 "$INSTDIR\WinCip.install.ini" "Install" "Integration"
  ${If} $0 == 1
    nsExec::ExecToLog '$\"$INSTDIR\WinCip.exe$\" --unregister-shell'
    Pop $0
    ${If} $0 != 0
      MessageBox MB_OK|MB_ICONEXCLAMATION "No se pudo retirar toda la integración. Cierra WinCip y vuelve a ejecutar el desinstalador." /SD IDOK
      SetErrorLevel 2
      Quit
    ${EndIf}
    WriteINIStr "$INSTDIR\WinCip.install.ini" "Install" "Integration" "0"
  ${EndIf}
  ReadINIStr $0 "$INSTDIR\WinCip.install.ini" "Install" "Desktop"
  ${If} $0 == 1
    Delete "$DESKTOP\${APP}.lnk"
  ${EndIf}
  ReadINIStr $0 "$INSTDIR\WinCip.install.ini" "Install" "StartMenu"
  ${If} $0 == 1
    Delete "$SMPROGRAMS\${APP}\${APP}.lnk"
    Delete "$SMPROGRAMS\${APP}\Guía de uso.lnk"
    Delete "$SMPROGRAMS\${APP}\Desinstalar.lnk"
    RMDir "$SMPROGRAMS\${APP}"
  ${EndIf}
  !include "${ROOT}\build\uninstaller-files.nsh"
  ${If} $R5 == 1
    MessageBox MB_OK|MB_ICONEXCLAMATION "Algunos archivos están en uso. Ciérralos y vuelve a ejecutar el desinstalador." /SD IDOK
    SetErrorLevel 2
    Quit
  ${EndIf}
  Delete "$INSTDIR\WinCip.install.ini"
  Delete "$INSTDIR\Desinstalar.exe"
  ReadRegStr $0 HKCU "${ARP}" "InstallLocation"
  ${If} $0 == $INSTDIR
    DeleteRegKey HKCU "${ARP}"
  ${EndIf}
  RMDir "$INSTDIR"
SectionEnd
