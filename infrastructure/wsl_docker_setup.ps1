param([switch]$Force)

Write-Host '=== DOCKER WSL2 - Windows Fix ===' -ForegroundColor Cyan

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')) { Write-Host 'Run as Admin!' -ForegroundColor Red; exit 1 }

# WSL2 + Ubuntu
Write-Host '1. WSL2 install...' -ForegroundColor Cyan
wsl --install -d Ubuntu 2>$null; wsl --set-default-version 2 2>$null

Start-Sleep 10

# Docker in WSL one-liners
Write-Host '2. Docker in Ubuntu...' -ForegroundColor Cyan
wsl --exec 'sudo apt update &amp;&amp; sudo apt install -y curl apt-transport-https ca-certificates gnupg lsb-release'
wsl --exec 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg'
wsl --exec 'echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null'
wsl --exec 'sudo apt update &amp;&amp; sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin'
wsl --exec 'sudo usermod -aG docker $USER'
wsl --exec 'sudo mkdir -p /etc/docker &amp;&amp; echo \"{\"experimental\": true}\" | sudo tee /etc/docker/daemon.json'
wsl --exec 'sudo service docker restart'

Write-Host '3. Test...' -ForegroundColor Cyan
wsl --exec docker run --rm hello-world

# Docker CLI proxy for Windows
@'
function DockerWSL { wsl docker $args }
Set-Alias -Name docker -Value DockerWSL -Scope Global -Force
function DockerComposeWSL { wsl docker compose $args }
Set-Alias -Name docker-compose -Value DockerComposeWSL -Scope Global -Force
'@
| Out-File -FilePath $PROFILE -Append -Encoding utf8

Write-Host '✅ Setup OK! Run: docker --version' -ForegroundColor Green
Write-Host 'Reload PS: . $PROFILE' -ForegroundColor Yellow
Write-Host 'Then: docker-compose up -d' -ForegroundColor Cyan

