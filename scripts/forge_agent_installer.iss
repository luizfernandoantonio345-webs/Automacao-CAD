; ═══════════════════════════════════════════════════════════════════════════════
; Forge CAD Local Agent — Inno Setup Script
;
; Gera Setup.exe que:
;   1. Instala ForgeLocalAgent.exe em C:\Program Files\ForgeCAD
;   2. Registra e inicia o serviço Windows automaticamente
;   3. Configura auto-start com o Windows
;   4. Cria atalho opcional no Menu Iniciar
;
; PRÉ-REQUISITO: Compilar o agente ANTES de rodar este script:
;   powershell -File scripts\build_agent.ps1
;
; Para compilar o instalador:
;   1. Abra este .iss no Inno Setup Compiler
;   2. Clique em Build > Compile
;   3. O Setup.exe será gerado em dist\installer_output\
; ═══════════════════════════════════════════════════════════════════════════════

#define MyAppName "Forge CAD Local Agent"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Engenharia CAD"
#define MyAppURL "https://automacao-cad-frontend.vercel.app"
#define MyAppExeName "ForgeLocalAgent.exe"
#define ServiceName "ForgeLocalAgent"

[Setup]
AppId={{B3E7A1F0-CAD1-4E5B-9A3C-FORGE0LOCAL0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\ForgeCAD
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer_output
OutputBaseFilename=ForgeCAD_Setup_{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
SetupLogging=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Principal — executável compilado pelo PyInstaller
Source: "..\dist\ForgeLocalAgent.exe"; DestDir: "{app}"; Flags: ignoreversion

; LSP do vigilante AutoCAD (copiado para pasta do agente + pasta do AutoCAD)
Source: "..\AutoCAD_Cliente\forge_vigilante.lsp"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\AutoCAD_Cliente\forge_vigilante.lsp"; DestDir: "C:\EngenhariaCAD"; Flags: ignoreversion onlyifdoesntexist

[Dirs]
Name: "C:\AutoCAD_Drop"; Permissions: users-full
Name: "C:\EngenhariaCAD"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "console"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Instalar o serviço Windows (silencioso)
Filename: "{app}\{#MyAppExeName}"; Parameters: "install"; \
  StatusMsg: "Registrando servico Windows..."; Flags: runhidden waituntilterminated

; Iniciar o serviço imediatamente
Filename: "net"; Parameters: "start {#ServiceName}"; \
  StatusMsg: "Iniciando agente..."; Flags: runhidden waituntilterminated

; Configurar auto-start (delayed) — sobrevive reboot
Filename: "sc"; Parameters: "config {#ServiceName} start= delayed-auto"; \
  StatusMsg: "Configurando inicio automatico..."; Flags: runhidden waituntilterminated

[UninstallRun]
; Parar o serviço antes de desinstalar
Filename: "net"; Parameters: "stop {#ServiceName}"; Flags: runhidden waituntilterminated
; Remover o serviço do Windows
Filename: "{app}\{#MyAppExeName}"; Parameters: "remove"; Flags: runhidden waituntilterminated

[Code]
// ─── Validação pré-instalação ─────────────────────────────────────────────
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Verificar se já existe uma instância do serviço rodando
  if Exec('sc', 'query ' + '{#ServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      // Serviço existe — parar antes de atualizar
      Exec('net', 'stop {#ServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(2000);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    Log('ForgeCAD Agent installed to: ' + ExpandConstant('{app}'));
    Log('Service name: {#ServiceName}');
    Log('Drop folder: C:\AutoCAD_Drop');
    Log('LSP folder: C:\EngenhariaCAD');
  end;
end;
