[Setup]
AppName=WinQuick AI
AppVersion=2.1.1
AppPublisher=WildVoid
DefaultDirName={localappdata}\WinQuick AI
DefaultGroupName=WinQuick AI
DisableProgramGroupPage=yes
OutputDir=C:\winquick\dist
OutputBaseFilename=WinQuickAI_Setup
Compression=lzma
SolidCompression=yes
UninstallDisplayIcon={app}\WinQuickAI.exe
PrivilegesRequired=lowest
SetupIconFile=C:\winquick\assets\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "C:\winquick\dist\WinQuickAI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\WinQuick AI"; Filename: "{app}\WinQuickAI.exe"
Name: "{group}\Uninstall WinQuick AI"; Filename: "{uninstallexe}"
Name: "{commondesktop}\WinQuick AI"; Filename: "{app}\WinQuickAI.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\WinQuickAI.exe"; Description: "Launch WinQuick AI"; Flags: postinstall nowait skipifsilent

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
