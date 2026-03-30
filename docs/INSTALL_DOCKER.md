# ====================================================================

# INSTALAÇÃO DOCKER DESKTOP - Windows

# Execute estes passos para instalar Docker antes de continuar

# ====================================================================

## 📋 Pré-requisitos

- Windows 10/11 Pro, Enterprise ou Education (Hyper-V habilitado)
- Pelo menos 4GB RAM disponível
- Virtualização habilitada na BIOS

## 🚀 Passos de Instalação

### Passo 1: Baixar Docker Desktop

```powershell
# Abra PowerShell como Administrador e execute:
Start-Process "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
```

Ou baixe manualmente de: https://www.docker.com/products/docker-desktop/

### Passo 2: Instalar

1. Execute o instalador baixado
2. Siga o assistente de instalação
3. Marque "Enable Hyper-V Windows Features" se solicitado
4. Clique "Install"
5. Reinicie o computador se solicitado

### Passo 3: Verificar Instalação

```powershell
# Após instalação, abra PowerShell e execute:
docker --version
docker-compose --version
```

**Esperado:**

```
Docker version 24.x.x, build xxxxx
Docker Compose version v2.x.x
```

### Passo 4: Iniciar Docker Desktop

1. Abra o aplicativo Docker Desktop
2. Aguarde inicialização completa (ícone baleia na barra de tarefas)
3. Aceite os termos se solicitado

### Passo 5: Teste Básico

```powershell
# Teste hello-world:
docker run hello-world

# Esperado: Mensagem "Hello from Docker!"
```

---

## ⚠️ Problemas Comuns

### "WSL 2 installation is incomplete"

```powershell
# Execute no PowerShell como Admin:
wsl --update
wsl --set-default-version 2
```

### "Virtualization not enabled"

- Reinicie PC e entre na BIOS (F2/F10/Del)
- Habilite VT-x/AMD-V
- Salve e saia

### "Docker Desktop requires Windows 10 Pro"

- Se Windows Home: Instale Docker Toolbox (legacy)
- Ou upgrade para Pro

---

## ✅ Após Instalação

Execute no terminal:

```bash
cd "c:\Users\Sueli\Desktop\Automação CAD"
docker-compose up -d --build
python test_celery_phase1.py
```

---

## 📞 Suporte

- Documentação: https://docs.docker.com/desktop/windows/install/
- Fórum: https://forums.docker.com/

**Após instalar Docker, execute novamente o comando de validação!**
