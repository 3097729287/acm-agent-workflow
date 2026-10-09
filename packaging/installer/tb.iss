#ifndef AppId
  #define AppId "{{0F82D178-AC2B-4696-96C1-1A210F72B509}"
#endif
#ifndef AppVersion
  #define AppVersion "0.6.0"
#endif
#ifndef PackageDir
  #error PackageDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef WebViewInstaller
  #error WebViewInstaller is required (offline x64 installer)
#endif

[Setup]
AppId={#AppId}
AppName=TB 训练工作台
AppVersion={#AppVersion}
AppPublisher=TB contributors
AppPublisherURL=https://github.com/3097729287/acm-agent-workflow
AppSupportURL=https://github.com/3097729287/acm-agent-workflow/issues
AppUpdatesURL=https://github.com/3097729287/acm-agent-workflow/releases
DefaultDirName={localappdata}\Programs\TB
DefaultGroupName=TB 训练工作台
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=TB-Setup-{#AppVersion}-win64
SetupIconFile={#PackageDir}\tb.ico
UninstallDisplayIcon={app}\tb.ico
UninstallDisplayName=TB 训练工作台
Compression=lzma2
SolidCompression=yes
LZMANumBlockThreads=2
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
SetupLogging=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked
Name: "importlegacy"; Description: "导入此电脑原 TB 的训练、提交、草稿及配置"; GroupDescription: "已有记录："; Flags: unchecked; Check: LegacyDatabaseExists

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Excludes: "data\*,state\*,cache\*,backups\*,logs\*,*.log"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PackageDir}\data\library.sqlite3"; DestDir: "{app}\data"; Flags: ignoreversion
Source: "{#WebViewInstaller}"; DestName: "WebView2-offline-x64.exe"; Flags: dontcopy nocompression

[Icons]
Name: "{group}\TB 训练工作台"; Filename: "{app}\TB新版.exe"; WorkingDir: "{app}"; IconFilename: "{app}\tb.ico"
Name: "{autodesktop}\TB 训练工作台"; Filename: "{app}\TB新版.exe"; WorkingDir: "{app}"; IconFilename: "{app}\tb.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\TB新版.exe"; Description: "打开 TB 训练工作台"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
function LegacyDatabaseExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{userprofile}\.dsh\state\tb-personal.sqlite3'));
end;

function WebViewPresent: Boolean;
var
  Version: String;
  Key: String;
begin
  Key := 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result := (RegQueryStringValue(HKCU, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
            (RegQueryStringValue(HKLM32, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
            (RegQueryStringValue(HKLM64, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
begin
  Result := '';
  if not WebViewPresent then
  begin
    ExtractTemporaryFile('WebView2-offline-x64.exe');
    if not Exec(ExpandConstant('{tmp}\WebView2-offline-x64.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      Result := 'WebView2 运行组件未能安装，请重试安装程序。'
    else if not WebViewPresent then
      Result := 'WebView2 安装尚未完成，请重新启动电脑后重试安装程序。';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ExitCode: Integer;
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('importlegacy') then
  begin
    if not Exec(ExpandConstant('{app}\TB新版.exe'), '--migrate-local', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      MsgBox('旧记录未能迁入；原软件数据已保留。请关闭旧软件后重新运行安装程序。', mbError, MB_OK)
    else if ExitCode <> 0 then
      MsgBox('旧记录尚未完整迁入；原数据已保留。请关闭旧软件后重新运行安装程序。', mbError, MB_OK);
  end;
end;

// Generated state/cache/backups are never registered as installed files.
// Uninstall removes distributed files only and leaves personal SQLite data.
