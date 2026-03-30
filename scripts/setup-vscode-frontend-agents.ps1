# Script para instalação de extensões VS Code úteis para frontend e IA
# Execute no PowerShell: .\setup-vscode-frontend-agents.ps1

$extensions = @(
  "GitHub.copilot",
  "TabNine.tabnine-vscode",
  "codeium.codeium",
  "VisualStudioExptTeam.vscodeintellicode",
  "dbaeumer.vscode-eslint",
  "esbenp.prettier-vscode",
  "stylelint.vscode-stylelint",
  "anthropic.claude" # substitua se precisar de ID correto
)

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
  Write-Host "VS Code CLI não encontrado. Instale o VS Code e habilite 'code' na PATH." -ForegroundColor Yellow
  return
}

foreach ($ext in $extensions) {
  Write-Host "Instalando $ext ..."
  code --install-extension $ext --force
}

Write-Host "Instalação concluída. Reinicie o VS Code se for necessário." -ForegroundColor Green
