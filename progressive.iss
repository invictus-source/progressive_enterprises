[Setup]
AppName=Progressive Enterprises
AppVersion=1.0.0
AppPublisher=Progressive Enterprises
AppUpdatesURL=http://localhost
DefaultDirName={autopf}\ProgressiveEnterprises
DisableProgramGroupPage=yes
OutputDir=installers
OutputBaseFilename=ProgressiveSetup_v1.0.0
SetupIconFile=assets\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Full dist bundle (onedir layout)
Source: "dist\Progressive Enterprises\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Explicit Qt plugin dirs – ensures they are not silently skipped
Source: "dist\Progressive Enterprises\_internal\PySide6\plugins\styles\*";           DestDir: "{app}\_internal\PySide6\plugins\styles";           Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "dist\Progressive Enterprises\_internal\PySide6\plugins\platforms\*";        DestDir: "{app}\_internal\PySide6\plugins\platforms";        Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "dist\Progressive Enterprises\_internal\PySide6\plugins\imageformats\*";     DestDir: "{app}\_internal\PySide6\plugins\imageformats";     Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "dist\Progressive Enterprises\_internal\PySide6\plugins\iconengines\*";      DestDir: "{app}\_internal\PySide6\plugins\iconengines";      Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "dist\Progressive Enterprises\_internal\PySide6\plugins\tls\*";              DestDir: "{app}\_internal\PySide6\plugins\tls";              Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
; qt.conf – tells Qt where to find plugins relative to the exe
Source: "dist\Progressive Enterprises\qt.conf"; DestDir: "{app}"; Flags: ignoreversion
; App assets
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Progressive Enterprises"; Filename: "{app}\Progressive Enterprises.exe"; IconFilename: "{app}\assets\logo.ico"
Name: "{autodesktop}\Progressive Enterprises"; Filename: "{app}\Progressive Enterprises.exe"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\Progressive Enterprises.exe"; Description: "{cm:LaunchProgram,Progressive Enterprises}"; Flags: nowait postinstall skipifsilent
