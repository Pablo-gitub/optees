#ifndef AppVersion
  #error AppVersion must be supplied by the release build
#endif

#ifndef SourceDir
  #error SourceDir must point to the PyInstaller onedir output
#endif

#ifndef AppNumericVersion
  #error AppNumericVersion must be supplied by the release build
#endif

#define AppName "Optees"
#define AppPublisher "Optees contributors"
#define AppUrl "https://github.com/Pablo-gitub/optees"
#define AppExecutable "optees.exe"

[Setup]
AppId={{7B07EED7-C851-4B42-B0DC-184BF7793D6A}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={localappdata}\Programs\Optees
DefaultGroupName=Optees
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=optees-windows-x64-setup
SetupIconFile=..\..\src\optees\assets\logo\dark\optees.ico
UninstallDisplayIcon={app}\{#AppExecutable}
VersionInfoVersion={#AppNumericVersion}
VersionInfoProductVersion={#AppNumericVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesEnvironment=no
ChangesAssociations=no
UsePreviousAppDir=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Optees"; Filename: "{app}\{#AppExecutable}"
Name: "{autodesktop}\Optees"; Filename: "{app}\{#AppExecutable}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExecutable}"; Description: "{cm:LaunchProgram,Optees}"; Flags: nowait postinstall skipifsilent
