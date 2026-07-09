; Inno Setup script — Meridian Vision Agent (Windows one-click installer).
; Compiled in CI:  iscc /DAgentDir=dist\meridian-agent edge\installer\windows\meridian-agent.iss
; Produces Output\meridian-agent-setup.exe. Optionally Authenticode-signed in CI.
;
; The frozen PyInstaller onedir bundle (with go2rtc.exe + go2rtc.yaml + weights inside)
; is installed to {app}. A custom page collects the pairing code; a Scheduled Task runs
; the agent at boot whether or not a user is logged in.

#ifndef AgentDir
  #define AgentDir "dist\meridian-agent"
#endif

[Setup]
AppId={{7C4B2E90-9A1E-4D77-9B2F-MERIDIANVISION}
AppName=Meridian Vision Agent
AppVersion=1.0.0
AppPublisher=Meridian
DefaultDirName={autopf}\Meridian\Agent
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=Output
OutputBaseFilename=meridian-agent-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "{#AgentDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Code]
var
  PairPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  PairPage := CreateInputQueryPage(wpSelectDir,
    'Connect to Meridian',
    'Enter the pairing code from your portal',
    'Open your Meridian portal, go to "Connect cameras", and paste the pairing code below. ' +
    'It links this machine to your account (valid for 15 minutes).');
  PairPage.Add('Pairing code:', False);
  PairPage.Add('Meridian API (leave default):', False);
  PairPage.Values[1] := 'https://api.meridian.tips';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = PairPage.ID then
  begin
    if Trim(PairPage.Values[0]) = '' then
    begin
      MsgBox('Please paste the pairing code from the portal.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfDir, Conf: string;
  Lines: TArrayOfString;
begin
  if CurStep = ssPostInstall then
  begin
    ConfDir := ExpandConstant('{commonappdata}\Meridian');
    ForceDirectories(ConfDir);
    Conf := ConfDir + '\agent.conf';
    SetArrayLength(Lines, 3);
    Lines[0] := '# Meridian Vision Agent config — keep private.';
    Lines[1] := 'MERIDIAN_PAIRING_CODE=' + Trim(PairPage.Values[0]);
    Lines[2] := 'MERIDIAN_API=' + Trim(PairPage.Values[1]);
    SaveStringsToFile(Conf, Lines, False);
  end;
end;

[Run]
; Register a boot-time Scheduled Task that runs as SYSTEM (survives logoff/reboot),
; then start it now so cameras appear immediately.
Filename: "schtasks"; \
  Parameters: "/Create /F /RU SYSTEM /SC ONSTART /TN ""MeridianVisionAgent"" /TR ""\""{app}\meridian-agent.exe\"""""; \
  Flags: runhidden; StatusMsg: "Registering the Meridian service..."
Filename: "schtasks"; Parameters: "/Run /TN ""MeridianVisionAgent"""; Flags: runhidden

[UninstallRun]
Filename: "schtasks"; Parameters: "/Delete /F /TN ""MeridianVisionAgent"""; Flags: runhidden; RunOnceId: "DelTask"

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\Meridian"
