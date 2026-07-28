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

[CustomMessages]
english.ExportDirectoryTitle=Artifact and report downloads
english.ExportDirectoryDescription=Choose where Optees should save artifacts and reports downloaded by local agents.
english.ExportDirectoryPrompt=Destination folder:
italian.ExportDirectoryTitle=Download di artifact e report
italian.ExportDirectoryDescription=Scegli dove Optees deve salvare gli artifact e i report scaricati dagli agenti locali.
italian.ExportDirectoryPrompt=Cartella di destinazione:

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Optees"; Filename: "{app}\{#AppExecutable}"
Name: "{autodesktop}\Optees"; Filename: "{app}\{#AppExecutable}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExecutable}"; Parameters: "--set-export-directory ""{code:GetExportDirectory}"""; Flags: runhidden waituntilterminated; Check: ShouldInitializeExportDirectory
Filename: "{app}\{#AppExecutable}"; Description: "{cm:LaunchProgram,Optees}"; Flags: nowait postinstall skipifsilent

[Code]
var
  ExportDirectoryPage: TInputDirWizardPage;

procedure InitializeWizard;
begin
  ExportDirectoryPage :=
    CreateInputDirPage(
      wpSelectDir,
      ExpandConstant('{cm:ExportDirectoryTitle}'),
      ExpandConstant('{cm:ExportDirectoryDescription}'),
      ExpandConstant('{cm:ExportDirectoryPrompt}'),
      False,
      ''
    );
  ExportDirectoryPage.Add('');
  ExportDirectoryPage.Values[0] := ExpandConstant('{%USERPROFILE}\Downloads\Optees');
end;

function GetExportDirectory(Param: String): String;
begin
  Result := ExportDirectoryPage.Values[0];
end;

function HasExportSettings: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Optees\settings.json'));
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result :=
    (ExportDirectoryPage <> nil) and
    (PageID = ExportDirectoryPage.ID) and
    HasExportSettings;
end;

function ShouldInitializeExportDirectory: Boolean;
begin
  Result := not HasExportSettings;
end;
