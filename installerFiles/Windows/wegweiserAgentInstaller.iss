; Wegweiser Agent Installer - Inno Setup Script
; Updated for Refactored Agent v4.0
; Supports Windows 10/11 with Python 3.8+

#define MyAppName "Wegweiser Agent"
#define MyAppVersion "4.0"
#define MyAppVersionTimestamp "202410211800"
#define MyAppPublisher "Wegweiser by Old Forge Technologies"
#define MyAppURL "https://www.wegweiser.tech/"
#define MyAppExeName "run_agent.exe"
#define AppRootPath "Wegweiser"

[Setup]
AppId={{3d77c6a8-6cb9-4df3-81ec-023c9ec29068}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#AppRootPath}
DisableDirPage=no
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=wegweiserAgentInstaller
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

; Visual elements
SetupIconFile=assets\wegweiser.ico
UninstallDisplayIcon={app}\Assets\wegweiser.ico
WizardImageFile=assets\wizard-large.bmp
WizardSmallImageFile=assets\wizard-small.bmp

; Version info
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright=Copyright (C) 2025 Old Forge Technologies
VersionInfoDescription=Wegweiser Agent Installation
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
Name: "{app}\Agent"
Name: "{app}\Assets"
Name: "{app}\Config"
Name: "{app}\Files"
Name: "{app}\Files\failed_uploads"
Name: "{app}\Files\Loki"
Name: "{app}\Logs"
Name: "{app}\Scripts"
Name: "{app}\Snippets"

[Files]
; Python environment with all dependencies
Source: "python-weg\*"; DestDir: "{app}\Agent\python-weg"; Flags: ignoreversion recursesubdirs createallsubdirs

; Agent files - all files go directly into {app}\Agent
Source: "Agent\*"; DestDir: "{app}\Agent"; Flags: ignoreversion recursesubdirs createallsubdirs

; PowerShell scripts
Source: "scripts\createWinTaskAgent.ps1"; DestDir: "{app}\Scripts"; Flags: ignoreversion
Source: "scripts\registerAgent.ps1"; DestDir: "{app}\Scripts"; Flags: ignoreversion
Source: "scripts\msinfo32-evaluatorAgent.ps1"; DestDir: "{app}\Scripts"; Flags: ignoreversion
Source: "scripts\install_persistent_agent.ps1"; DestDir: "{app}\Scripts"; Flags: ignoreversion

; Icon file (only wegweiser.ico needed for Add/Remove Programs and shortcuts)
Source: "assets\wegweiser.ico"; DestDir: "{app}\Assets"; Flags: ignoreversion

; WinSW service host files
Source: "vendors\WegweiserServiceHost.exe"; DestDir: "{app}\Agent"; Flags: ignoreversion
Source: "vendors\WegweiserServiceHost.xml"; DestDir: "{app}\Agent"; Flags: ignoreversion

; OSQuery installer
Source: "vendors\osquery.msi"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Agent\python-weg\python.exe"; Parameters: """{app}\Agent\run_agent.py"" -d"; WorkingDir: "{app}\Agent"; IconFilename: "{app}\Assets\wegweiser.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Agent\python-weg\python.exe"; Parameters: """{app}\Agent\run_agent.py"" -d"; WorkingDir: "{app}\Agent"; IconFilename: "{app}\Assets\wegweiser.ico"; Tasks: desktopicon

[Run]
; Create agent version file with timestamp format (YYYYMMDDHHmm)
Filename: "cmd.exe"; Parameters: "/c echo {#MyAppVersionTimestamp} > ""{app}\Config\agentVersion.txt"""; Flags: runhidden waituntilterminated; StatusMsg: "Creating version file..."

; Upgrade pip first
Filename: "{app}\Agent\python-weg\python.exe"; Parameters: "-m pip install --upgrade pip setuptools"; Flags: runhidden waituntilterminated; StatusMsg: "Upgrading pip and setuptools..."

; Install Python dependencies
Filename: "{app}\Agent\python-weg\python.exe"; Parameters: "-m pip install --no-cache-dir -r ""{app}\Agent\requirements.txt"""; Flags: runhidden waituntilterminated; StatusMsg: "Installing Python dependencies..."

; Register device with server
Filename: "{app}\Agent\python-weg\python.exe"; Parameters: """{app}\Agent\register_device.py"" -g {code:GetGroupUUID} -s {code:GetServerAddr}"; WorkingDir: "{app}\Agent"; Flags: runhidden waituntilterminated; StatusMsg: "Registering agent with server..."

; Create scheduled task
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\Scripts\createWinTaskAgent.ps1"""; WorkingDir: "{app}"; Flags: runhidden; StatusMsg: "Creating scheduled task..."

; Install the service with WinSW
Filename: "{app}\Agent\WegweiserServiceHost.exe"; Parameters: "install"; Flags: runhidden waituntilterminated; StatusMsg: "Installing service..."

; Start the service
Filename: "{app}\Agent\WegweiserServiceHost.exe"; Parameters: "start"; Flags: runhidden; StatusMsg: "Starting service..."

; Install OSQuery silently
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\osquery.msi"" /qn"; Flags: runhidden waituntilterminated; StatusMsg: "Installing osquery..."

[UninstallRun]
Filename: "{app}\Agent\WegweiserServiceHost.exe"; Parameters: "stop"; Flags: runhidden
Filename: "{app}\Agent\WegweiserServiceHost.exe"; Parameters: "uninstall"; Flags: runhidden

[Code]
function GetGroupUUID(Param: string): string;
begin
  Result := ExpandConstant('{param:groupuuid}');
end;

function GetServerAddr(Param: string): string;
begin
  Result := ExpandConstant('{param:serveraddr}');
end;

function InitializeSetup(): Boolean;
var
  GroupUUID: string;
  ServerAddr: string;
begin
  Result := True;
  GroupUUID := GetGroupUUID('');
  ServerAddr := GetServerAddr('');
  
  if (Length(GroupUUID) <> 36) then
  begin
    MsgBox('Group UUID must be exactly 36 characters long. Got: ' + GroupUUID, mbError, MB_OK);
    Result := False;
  end;
  
  if (ServerAddr = '') then
  begin
    MsgBox('Server address is required.', mbError, MB_OK);
    Result := False;
  end;
end;