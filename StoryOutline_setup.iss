; StoryOutline 安装包脚本 (Inno Setup)
; 特性: 用户可选安装位置 + 桌面快捷方式 + wenjian 数据文件夹

#define MyAppName "StoryOutline"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "StoryOutline"
#define MyAppExeName "StoryOutline.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableDirPage=no
OutputDir=installer
OutputBaseFilename=StoryOutline_Setup_v1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
WizardSizePercent=120

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "startmenu"; Description: "Create Start Menu shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
Source: "dist\StoryOutline.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Tasks: startmenu

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DataDir: String;

function GetDataDir(Param: String): String;
begin
  Result := ExpandConstant('{app}') + '\wenjian';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    DataDir := ExpandConstant('{app}') + '\wenjian';
    if not DirExists(DataDir) then
      CreateDir(DataDir);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    DataDir := ExpandConstant('{app}') + '\wenjian';
    if DirExists(DataDir) then
    begin
      if MsgBox('Do you want to remove user data (all analysis results in wenjian folder)?', mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
