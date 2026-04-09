# 🚀 CLIENTE ENGENHARIA CAD - SETUP 1-CLICK

## Pré-requisitos

- Windows 10/11
- AutoCAD 2021+ instalado (trial OK)

## 📥 Instalação (30s)

1. **Baixe** `AutoCAD_Cliente.zip` → Extraia na Desktop
2. **Execute** `AutoCAD_Cliente/AUTO_SETUP.bat` como **Administrador**

```
   ✅ AutoCAD detectado/iniciado
   ✅ Pastas criadas: C:\EngenhariaCAD + C:\AutoCAD_Drop
   ✅ LSP carregado via COM
   ✅ FORGE_START executado
   ✅ Backend configurado
```

## 🧪 Teste Imediato

```
curl -X POST http://localhost:8000/api/autocad/test-automation
```

✅ Desenha círculo + tubulação + zoom!

## 🔄 Uso Diário

- Execute `AUTO_SETUP.bat` (abre CAD + conecta)
- Backend web gera desenhos automaticamente
- LSP executa em background

## ❓ Troubleshooting

```
- CAD não abre? → Instale AutoCAD trial
- LSP não carrega? → Execute manual APPLOAD
- Sem backend? → python server.py
```

**Pronto para produção/licenças!** 🎉
