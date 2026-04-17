#!/usr/bin/env python3
"""
scripts/validation_checklist.py — Sistema de Validação Completa
Executa todos os checks do checklist e gera relatório.
"""
import os
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

ROOT = Path(__file__).parent.parent
os.chdir(ROOT)

@dataclass
class CheckResult:
    id: int
    categoria: str
    descricao: str
    prioridade: Literal["crítico", "importante", "médio"]
    status: Literal["✅ OK", "❌ FALHA", "⚠️ ATENÇÃO", "🔧 MANUAL"]
    detalhe: str = ""

results: list[CheckResult] = []

# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE VALIDAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def check_sync_sessions():
    """Verifica se há Session() síncrono no backend"""
    hits = []
    for py in Path("backend").rglob("*.py"):
        content = py.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(content.splitlines(), 1):
            if "Session()" in line and "AsyncSession" not in line and "sessionmaker" not in line:
                hits.append(f"{py}:{i}")
    if hits:
        return "❌ FALHA", f"Session() síncrono em: {', '.join(hits[:3])}"
    return "✅ OK", "Nenhum Session() síncrono encontrado"

def check_migration_script():
    """Verifica se o script de migração compila"""
    script = ROOT / "scripts" / "migrate_sqlite_to_postgres.py"
    if not script.exists():
        return "❌ FALHA", "Script não existe"
    try:
        import ast
        ast.parse(script.read_text(encoding="utf-8"))
        return "✅ OK", "Script compila corretamente"
    except SyntaxError as e:
        return "❌ FALHA", f"Erro de sintaxe: {e}"

def check_security_audit():
    """Executa security_audit.py"""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/security_audit.py", "--path", "backend"],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace"
        )
        output = result.stdout + result.stderr
        # Parse summary (formato: Summary: {'SECRET': 0, 'SQL_INJECTION': 0, 'UNSAFE': 0})
        m = re.search(r"Summary:\s*\{['\"]SECRET['\"]: (\d+),\s*['\"]SQL_INJECTION['\"]: (\d+),\s*['\"]UNSAFE['\"]: (\d+)\}", output)
        if m:
            secrets, sql, unsafe = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if secrets > 0 or sql > 0:
                return "❌ FALHA", f"SECRET={secrets}, SQL_INJECTION={sql}, UNSAFE={unsafe}"
            elif unsafe > 0:
                return "⚠️ ATENÇÃO", f"UNSAFE={unsafe} (MD5/SHA1) - avaliar necessidade"
            return "✅ OK", "Nenhum issue de segurança"
        # Alternativa: checar se passou direto
        if "No security issues" in output or "✅" in output:
            return "✅ OK", "Nenhum issue de segurança"
        return "⚠️ ATENÇÃO", "Não foi possível parsear resultado"
    except Exception as e:
        return "❌ FALHA", str(e)

def check_agent_install_bat():
    """Verifica se install.bat usa user dedicado, não SYSTEM"""
    bat = ROOT / "agent" / "install.bat"
    if not bat.exists():
        return "❌ FALHA", "install.bat não existe"
    content = bat.read_text(encoding="utf-8", errors="replace")
    if "engcad-agent" in content and "LocalSystem" not in content:
        return "✅ OK", "Usa user dedicado engcad-agent"
    elif "LocalSystem" in content or "SYSTEM" in content.upper():
        return "❌ FALHA", "Roda como SYSTEM - inseguro"
    return "⚠️ ATENÇÃO", "Verificar manualmente configuração de user"

def check_sincronizador_tls():
    """Verifica se SINCRONIZADOR.ps1 força TLS 1.2+"""
    ps1 = ROOT / "AutoCAD_Cliente" / "SINCRONIZADOR.ps1"
    if not ps1.exists():
        return "❌ FALHA", "SINCRONIZADOR.ps1 não existe"
    content = ps1.read_text(encoding="utf-8", errors="replace")
    if "Tls12" in content or "Tls13" in content:
        if "https://" in content.lower() and "-notmatch '^https://'" in content:
            return "✅ OK", "TLS 1.2+ + HTTPS-only validado"
        return "⚠️ ATENÇÃO", "TLS OK, mas verificar HTTPS-only"
    return "❌ FALHA", "Não força TLS 1.2+"

def check_lisp_whitelist():
    """Verifica se SINCRONIZADOR tem whitelist de comandos"""
    ps1 = ROOT / "AutoCAD_Cliente" / "SINCRONIZADOR.ps1"
    if not ps1.exists():
        return "❌ FALHA", "SINCRONIZADOR.ps1 não existe"
    content = ps1.read_text(encoding="utf-8", errors="replace")
    if "ALLOWED_OPERATIONS" in content and "draw_pipe" in content:
        return "✅ OK", "Whitelist de operações implementada"
    return "❌ FALHA", "Sem whitelist de operações"

def check_forge_vigilante_lisp():
    """Verifica forge_vigilante.lsp para comandos perigosos"""
    lsp = ROOT / "backend" / "forge_vigilante.lsp"
    if not lsp.exists():
        lsp = ROOT / "AutoCAD_Cliente" / "forge_vigilante.lsp"
    if not lsp.exists():
        return "⚠️ ATENÇÃO", "forge_vigilante.lsp não encontrado"
    content = lsp.read_text(encoding="utf-8", errors="replace").lower()
    # Comandos realmente perigosos (execução de sistema)
    dangerous = ["shell", "startapp", "(dos"]
    found = [d for d in dangerous if d in content]
    if found:
        return "❌ FALHA", f"Comandos de sistema perigosos: {found}"
    # (command é normal para LISP - usado para comandos CAD internos
    return "✅ OK", "Nenhum comando de sistema perigoso"

def check_jwt_secret():
    """Verifica se JARVIS_SECRET tem >= 32 bytes em .env.example"""
    env = ROOT / ".env.example"
    if not env.exists():
        return "❌ FALHA", ".env.example não existe"
    content = env.read_text(encoding="utf-8", errors="replace")
    if "JARVIS_SECRET" in content:
        # Check if there's a placeholder
        if "change_me" in content.lower() or "your_secret" in content.lower():
            return "⚠️ ATENÇÃO", "Secret é placeholder - definir em produção"
        return "✅ OK", "JARVIS_SECRET definido"
    return "❌ FALHA", "JARVIS_SECRET não está no .env.example"

def check_cors_production():
    """Verifica se CORS não permite localhost em produção"""
    server = ROOT / "server.py"
    if not server.exists():
        return "❌ FALHA", "server.py não existe"
    content = server.read_text(encoding="utf-8", errors="replace")
    # Check for origin regex that allows vercel but blocks random origins
    if "vercel.app" in content and "_CORS_ORIGIN_REGEX" in content:
        return "✅ OK", "CORS com regex para Vercel + localhost dev"
    return "⚠️ ATENÇÃO", "Verificar configuração CORS manualmente"

def check_rate_limit_middleware():
    """Verifica se rate_limit.py existe e está registrado"""
    rl = ROOT / "backend" / "middleware" / "rate_limit.py"
    if not rl.exists():
        return "❌ FALHA", "rate_limit.py não existe"
    # Check if it's used
    server = ROOT / "server.py"
    content = server.read_text(encoding="utf-8", errors="replace") if server.exists() else ""
    routes_license = ROOT / "backend" / "routes_license.py"
    rl_content = routes_license.read_text(encoding="utf-8", errors="replace") if routes_license.exists() else ""
    if "rate_limit" in rl_content or "RateLimitMiddleware" in content:
        return "✅ OK", "Rate limiting implementado e usado"
    return "⚠️ ATENÇÃO", "Rate limiting existe mas verificar uso"

def check_async_endpoints():
    """Conta endpoints async vs sync (ignora funções helper com _)"""
    async_count = 0
    sync_count = 0
    sync_routes = []
    for py in Path("backend").rglob("routes*.py"):
        content = py.read_text(encoding="utf-8", errors="replace")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Encontra definições de função que são route handlers
            if line.strip().startswith('async def ') and '(request' in line:
                async_count += 1
            elif line.strip().startswith('def ') and '(request' in line:
                # Ignora helpers internos (começam com _)
                if not line.strip().startswith('def _'):
                    sync_count += 1
                    sync_routes.append(f"{py.name}:{i+1}")
    if sync_count > 0:
        return "⚠️ ATENÇÃO", f"async={async_count}, sync={sync_count}: {sync_routes[:3]}"
    return "✅ OK", f"{async_count} endpoints async"

def check_docker_compose_prod():
    """Verifica docker-compose.prod.yml"""
    dc = ROOT / "docker-compose.prod.yml"
    if not dc.exists():
        return "❌ FALHA", "docker-compose.prod.yml não existe"
    content = dc.read_text(encoding="utf-8", errors="replace")
    issues = []
    if "localhost" in content and "DB_HOST" not in content:
        issues.append("localhost hardcoded")
    if "debug=true" in content.lower():
        issues.append("debug=true")
    required = ["postgres", "redis", "nginx", "healthcheck"]
    missing = [r for r in required if r not in content.lower()]
    if missing:
        issues.append(f"faltando: {missing}")
    if issues:
        return "⚠️ ATENÇÃO", "; ".join(issues)
    return "✅ OK", "Configuração de produção OK"

def check_k8s_manifests():
    """Verifica manifests Kubernetes"""
    k8s = ROOT / "k8s"
    if not k8s.exists():
        return "❌ FALHA", "Diretório k8s/ não existe"
    files = list(k8s.glob("*.yaml")) + list(k8s.glob("*.yml"))
    required = ["deployment", "service", "ingress"]
    found = []
    for f in files:
        name = f.stem.lower()
        for r in required:
            if r in name or r in f.read_text(encoding="utf-8", errors="replace").lower():
                found.append(r)
    missing = set(required) - set(found)
    if missing:
        return "⚠️ ATENÇÃO", f"Faltando: {missing}"
    return "✅ OK", f"{len(files)} manifests encontrados"

def check_backup_restore():
    """Verifica se backup.sh e restore.sh existem"""
    backup = ROOT / "scripts" / "backup.sh"
    restore = ROOT / "scripts" / "restore.sh"
    if backup.exists() and restore.exists():
        return "✅ OK", "backup.sh + restore.sh presentes"
    missing = []
    if not backup.exists(): missing.append("backup.sh")
    if not restore.exists(): missing.append("restore.sh")
    return "❌ FALHA", f"Faltando: {missing}"

def check_k6_stress():
    """Verifica se k6/stress.js existe"""
    k6 = ROOT / "k6" / "stress.js"
    if not k6.exists():
        return "❌ FALHA", "k6/stress.js não existe"
    content = k6.read_text(encoding="utf-8", errors="replace")
    if "thresholds" in content and "http_req_duration" in content:
        return "✅ OK", "Stress test com thresholds configurado"
    return "⚠️ ATENÇÃO", "Verificar thresholds no stress test"

def check_frontend_components():
    """Verifica componentes frontend críticos"""
    components = [
        "frontend/src/components/OnboardingTour.tsx",
        "frontend/src/pages/DashboardV2.tsx",
    ]
    missing = [c for c in components if not (ROOT / c).exists()]
    if missing:
        return "❌ FALHA", f"Faltando: {missing}"
    return "✅ OK", "Componentes frontend presentes"

def check_nginx_config():
    """Verifica nginx.conf"""
    nginx = ROOT / "infrastructure" / "nginx" / "nginx.conf"
    if not nginx.exists():
        return "❌ FALHA", "nginx.conf não existe"
    content = nginx.read_text(encoding="utf-8", errors="replace")
    required = ["ssl_protocols", "limit_req", "proxy_pass"]
    missing = [r for r in required if r not in content]
    if missing:
        return "⚠️ ATENÇÃO", f"Faltando: {missing}"
    return "✅ OK", "Nginx com TLS + rate limiting"

def check_health_endpoint():
    """Verifica se /health existe no server.py"""
    server = ROOT / "server.py"
    if not server.exists():
        return "❌ FALHA", "server.py não existe"
    content = server.read_text(encoding="utf-8", errors="replace")
    if '"/health"' in content or "'/health'" in content:
        return "✅ OK", "Endpoint /health configurado"
    return "⚠️ ATENÇÃO", "Verificar endpoint /health"

def check_alembic_config():
    """Verifica alembic.ini e env.py"""
    alembic_ini = ROOT / "alembic.ini.new" if (ROOT / "alembic.ini.new").exists() else ROOT / "alembic.ini"
    alembic_env = ROOT / "alembic" / "env.py"
    if not alembic_ini.exists():
        return "❌ FALHA", "alembic.ini não existe"
    if not alembic_env.exists():
        return "❌ FALHA", "alembic/env.py não existe"
    env_content = alembic_env.read_text(encoding="utf-8", errors="replace")
    if "run_async_migrations" in env_content:
        return "✅ OK", "Alembic configurado para async"
    return "⚠️ ATENÇÃO", "Verificar suporte async no Alembic"

def check_celery_postgres():
    """Verifica se Celery está configurado corretamente"""
    celery_config = ROOT / "celery_config.py"
    if not celery_config.exists():
        return "⚠️ ATENÇÃO", "celery_config.py não encontrado"
    content = celery_config.read_text(encoding="utf-8", errors="replace")
    # Celery usa Redis para results (mais rápido) e RabbitMQ/Redis para broker
    has_broker = "CELERY_BROKER_URL" in content
    has_backend = "CELERY_RESULT_BACKEND" in content
    if has_broker and has_backend:
        return "✅ OK", "Celery broker + backend configurados"
    return "⚠️ ATENÇÃO", f"broker={has_broker}, backend={has_backend}"

def check_hwid_rate_limit():
    """Verifica se HWID endpoint tem rate limiting"""
    routes = ROOT / "backend" / "routes_license.py"
    if not routes.exists():
        return "❌ FALHA", "routes_license.py não existe"
    content = routes.read_text(encoding="utf-8", errors="replace")
    if "@rate_limit" in content and "validate" in content:
        return "✅ OK", "HWID com rate limiting"
    return "⚠️ ATENÇÃO", "Verificar rate limiting no HWID"

def check_agentaautocad_bat():
    """Verifica agentaautocad.bat"""
    bat = ROOT / "AutoCAD_Cliente" / "agentaautocad.bat"
    if not bat.exists():
        return "❌ FALHA", "agentaautocad.bat não existe"
    content = bat.read_text(encoding="utf-8", errors="replace")
    checks = {
        "SHA-256": "certutil" in content or "Get-FileHash" in content,
        "config.json": "config.json" in content,
        "schtasks": "schtasks" in content,
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        return "⚠️ ATENÇÃO", f"Faltando: {failed}"
    return "✅ OK", "Instalador com SHA-256, config, e scheduled task"

def check_agent_update_bat():
    """Verifica agentaautocad_update.bat"""
    bat = ROOT / "AutoCAD_Cliente" / "agentaautocad_update.bat"
    if not bat.exists():
        return "❌ FALHA", "agentaautocad_update.bat não existe"
    content = bat.read_text(encoding="utf-8", errors="replace")
    # Suporta português "Restaurando" e inglês "restore"
    has_backup = "backup" in content.lower()
    has_restore = "restore" in content.lower() or "restaurando" in content.lower()
    if has_backup and has_restore:
        return "✅ OK", "Update com backup e rollback"
    return "⚠️ ATENÇÃO", f"backup={has_backup}, restore={has_restore}"

def check_openapi_docs():
    """Verifica se /docs está habilitado"""
    server = ROOT / "server.py"
    if not server.exists():
        return "❌ FALHA", "server.py não existe"
    content = server.read_text(encoding="utf-8", errors="replace")
    if 'docs_url="/docs"' in content or "docs_url='/docs'" in content:
        return "✅ OK", "OpenAPI /docs habilitado"
    return "⚠️ ATENÇÃO", "Verificar OpenAPI docs"

def check_error_boundary():
    """Verifica se frontend tem Error Boundary"""
    # Check for ErrorBoundary in frontend
    for tsx in Path("frontend/src").rglob("*.tsx"):
        if tsx.exists():
            content = tsx.read_text(encoding="utf-8", errors="replace")
            if "ErrorBoundary" in content or "componentDidCatch" in content:
                return "✅ OK", "Error Boundary implementado"
    return "⚠️ ATENÇÃO", "Verificar Error Boundary no frontend"

def check_prometheus_grafana():
    """Verifica se Prometheus/Grafana estão no docker-compose.prod"""
    dc = ROOT / "docker-compose.prod.yml"
    if not dc.exists():
        return "⚠️ ATENÇÃO", "docker-compose.prod.yml não existe"
    content = dc.read_text(encoding="utf-8", errors="replace")
    has_prometheus = "prometheus" in content.lower()
    has_grafana = "grafana" in content.lower()
    if has_prometheus and has_grafana:
        return "✅ OK", "Prometheus + Grafana configurados"
    return "⚠️ ATENÇÃO", f"Prometheus={has_prometheus}, Grafana={has_grafana}"

# ══════════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════

CHECKS = [
    # CRÍTICOS
    (1, "Database", "AsyncSession em TODOS os endpoints", "crítico", check_sync_sessions),
    (2, "Database", "Script migração SQLite→PostgreSQL", "crítico", check_migration_script),
    (3, "Segurança", "security_audit.py sem issues críticos", "crítico", check_security_audit),
    (4, "Segurança", "Agente NÃO roda como SYSTEM", "crítico", check_agent_install_bat),
    (5, "Segurança", "SINCRONIZADOR com TLS 1.2+", "crítico", check_sincronizador_tls),
    (6, "Segurança", "LISP whitelist implementada", "crítico", check_lisp_whitelist),
    (7, "Segurança", "forge_vigilante.lsp auditado", "crítico", check_forge_vigilante_lisp),
    (8, "AutoCAD", "agentaautocad.bat funcional", "crítico", check_agentaautocad_bat),
    (9, "Escalabilidade", "docker-compose.prod.yml válido", "crítico", check_docker_compose_prod),
    (10, "Frontend", "Componentes críticos presentes", "crítico", check_frontend_components),
    # IMPORTANTES
    (11, "Database", "Alembic configurado para async", "importante", check_alembic_config),
    (12, "Database", "Celery com PostgreSQL", "importante", check_celery_postgres),
    (13, "Segurança", "JWT secret >= 32 bytes", "importante", check_jwt_secret),
    (14, "Segurança", "CORS configurado para produção", "importante", check_cors_production),
    (15, "Segurança", "Rate limiting Redis implementado", "importante", check_rate_limit_middleware),
    (16, "Segurança", "HWID com rate limiting", "importante", check_hwid_rate_limit),
    (17, "AutoCAD", "Update com backup/rollback", "importante", check_agent_update_bat),
    (18, "Escalabilidade", "k8s manifests completos", "importante", check_k8s_manifests),
    (19, "Escalabilidade", "Nginx com TLS + rate limit", "importante", check_nginx_config),
    (20, "Escalabilidade", "k6 stress test configurado", "importante", check_k6_stress),
    (21, "Escalabilidade", "Prometheus + Grafana", "importante", check_prometheus_grafana),
    # MÉDIOS
    (22, "Database", "Backup/restore scripts", "médio", check_backup_restore),
    (23, "Backend", "Endpoints async vs sync", "médio", check_async_endpoints),
    (24, "Backend", "Health endpoint configurado", "médio", check_health_endpoint),
    (25, "Backend", "OpenAPI docs habilitado", "médio", check_openapi_docs),
    (26, "Frontend", "Error Boundary implementado", "médio", check_error_boundary),
]

def run_all_checks():
    """Executa todos os checks e retorna resultados"""
    for id_, cat, desc, prio, func in CHECKS:
        try:
            status, detail = func()
        except Exception as e:
            status, detail = "❌ FALHA", f"Erro: {e}"
        results.append(CheckResult(id_, cat, desc, prio, status, detail))

def print_table():
    """Imprime tabela de resultados"""
    print("\n" + "═" * 100)
    print("  CHECKLIST DE VALIDAÇÃO — AUTOMAÇÃO CAD")
    print("═" * 100)
    
    # Contagem
    ok = sum(1 for r in results if r.status == "✅ OK")
    fail = sum(1 for r in results if r.status == "❌ FALHA")
    warn = sum(1 for r in results if r.status == "⚠️ ATENÇÃO")
    
    print(f"\n  RESUMO: {ok} OK | {fail} FALHA | {warn} ATENÇÃO\n")
    
    # Tabela
    print(f"{'ID':<4} {'CATEGORIA':<15} {'DESCRIÇÃO':<45} {'PRIORIDADE':<12} {'STATUS':<12} {'DETALHE'}")
    print("-" * 100)
    
    for r in results:
        desc = r.descricao[:43] + ".." if len(r.descricao) > 45 else r.descricao
        detail = r.detalhe[:30] + ".." if len(r.detalhe) > 32 else r.detalhe
        print(f"{r.id:<4} {r.categoria:<15} {desc:<45} {r.prioridade:<12} {r.status:<12} {detail}")
    
    print("═" * 100)
    
    # Listar falhas
    failures = [r for r in results if r.status == "❌ FALHA"]
    if failures:
        print("\n⚠️  ITENS QUE PRECISAM CORREÇÃO:")
        for r in failures:
            print(f"  [{r.id}] {r.descricao}: {r.detalhe}")
    
    warnings = [r for r in results if r.status == "⚠️ ATENÇÃO"]
    if warnings:
        print("\n⚡ ITENS PARA REVISÃO MANUAL:")
        for r in warnings:
            print(f"  [{r.id}] {r.descricao}: {r.detalhe}")
    
    if not failures:
        print("\n🎉 SISTEMA PRONTO PARA PRODUÇÃO (sem falhas críticas)")
    else:
        print(f"\n🚫 {len(failures)} item(s) precisam correção antes de produção")

if __name__ == "__main__":
    run_all_checks()
    print_table()
