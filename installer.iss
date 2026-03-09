[Setup]
AppName=Vial
AppVersion=0.7.5
AppPublisher=xcmkb
DefaultDirName={autopf}\Vial
DefaultGroupName=Vial
OutputDir=target
OutputBaseFilename=VialSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "target\Vial\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Vial"; Filename: "{app}\Vial.exe"
Name: "{commondesktop}\Vial"; Filename: "{app}\Vial.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Vial.exe"; Description: "{cm:LaunchProgram,Vial}"; Flags: nowait postinstall skipifsilent
