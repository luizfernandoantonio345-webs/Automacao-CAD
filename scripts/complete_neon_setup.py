#!/usr/bin/env python3
"""
Complete Neon PostgreSQL Setup - Engenharia CAD
===============================================

USO:
    python scripts/complete_neon_setup.py "postgresql://user:pass@host/db?sslmode=require"

OU:
    Defina DATABASE_URL no ambiente e execute sem argumentos:
    $env:DATABASE_URL = "postgresql://..."
    python scripts/complete_neon_setup.py
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(text: str):
    print(f"\n{'='*50}")
    print(f" {text}")
    print(f"{'='*50}\n")


def print_ok(text: str):
    print(f"[OK] {text}")


def print_error(text: str):
    print(f"[ERRO] {text}")


def print_info(text: str):
    print(f"[INFO] {text}")


def validate_url(url: str) -> str:
    """Valida e normaliza a URL do PostgreSQL."""
    if not url:
        return None
    
    # Normalizar postgres:// para postgresql://
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    if not url.startswith("postgresql://"):
        print_error("URL deve começar com postgresql://")
        return None
    
    # Garantir sslmode=require
    if "sslmode=" not in url:
        if "?" in url:
            url = f"{url}&sslmode=require"
        else:
            url = f"{url}?sslmode=require"
    
    return url


def test_connection(url: str) -> bool:
    """Testa conexão com PostgreSQL."""
    try:
        import psycopg2
        print_info("Conectando ao PostgreSQL...")
        
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        conn.close()
        
        print_ok(f"Conectado: {version[:60]}...")
        return True
        
    except ImportError:
        print_error("psycopg2 não instalado. Execute: pip install psycopg2-binary")
        return False
    except Exception as e:
        print_error(f"Falha na conexão: {e}")
        return False


def run_migrations() -> bool:
    """Executa migrations do Alembic."""
    print_info("Executando migrations...")
    
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print_ok("Migrations concluídas!")
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    print(f"    {line}")
            return True
        else:
            print_error(f"Falha nas migrations: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print_error("Alembic não encontrado. Execute: pip install alembic")
        return False
    except Exception as e:
        print_error(f"Erro: {e}")
        return False


def verify_tables(url: str) -> bool:
    """Verifica tabelas criadas no banco."""
    try:
        import psycopg2
        print_info("Verificando tabelas...")
        
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        conn.close()
        
        if tables:
            print_ok(f"Tabelas criadas: {len(tables)}")
            for t in tables:
                print(f"    - {t[0]}")
            return True
        else:
            print_info("Nenhuma tabela encontrada (banco vazio)")
            return True
            
    except Exception as e:
        print_error(f"Erro ao verificar tabelas: {e}")
        return False


def create_env_file(url: str):
    """Cria ou atualiza arquivo .env com DATABASE_URL."""
    env_path = Path(__file__).parent.parent / ".env"
    
    if env_path.exists():
        content = env_path.read_text()
        if "DATABASE_URL=" in content:
            # Atualizar valor existente
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if line.startswith("DATABASE_URL="):
                    new_lines.append(f"DATABASE_URL={url}")
                else:
                    new_lines.append(line)
            env_path.write_text("\n".join(new_lines))
            print_ok("DATABASE_URL atualizada em .env")
        else:
            # Adicionar ao final
            with open(env_path, "a") as f:
                f.write(f"\nDATABASE_URL={url}\n")
            print_ok("DATABASE_URL adicionada ao .env")
    else:
        # Criar novo .env
        env_path.write_text(f"DATABASE_URL={url}\n")
        print_ok("Arquivo .env criado com DATABASE_URL")


def print_vercel_instructions(url: str):
    """Mostra instruções para configurar no Vercel."""
    print_header("PRÓXIMO PASSO: CONFIGURAR NO VERCEL")
    
    print("""1. Acesse: https://vercel.com/dashboard
2. Selecione: automacao-cad-backend
3. Vá para: Settings -> Environment Variables
4. Adicione:

   Key:   DATABASE_URL
   Value: (a URL abaixo)
""")
    
    # Mostrar URL com senha mascarada para segurança
    masked_url = url
    if "@" in url:
        parts = url.split("@")
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            masked_url = url.replace(user_pass, f"{user}:****")
    
    print(f"   {masked_url}")
    print("""
5. Marque: Production e Preview
6. Clique: Save
7. Faça Redeploy do projeto

Depois verifique em:
https://automacao-cad-backend.vercel.app/health

O campo "database.type" deve mostrar "postgresql"!
""")


def main():
    print_header("CONFIGURAR POSTGRESQL NEON")
    
    # Obter URL
    url = None
    
    # 1. Tentar argumento da linha de comando
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    # 2. Tentar variável de ambiente
    if not url:
        url = os.environ.get("DATABASE_URL")
    
    # 3. Solicitar interativamente
    if not url:
        print("Cole a Connection String do Neon:")
        print("(Formato: postgresql://user:pass@host/db?sslmode=require)")
        print()
        url = input("DATABASE_URL: ").strip()
    
    # Validar URL
    url = validate_url(url)
    if not url:
        print_error("URL inválida!")
        sys.exit(1)
    
    print_ok("URL validada")
    
    # Definir variável de ambiente para este processo
    os.environ["DATABASE_URL"] = url
    
    # Testar conexão
    if not test_connection(url):
        print_error("Não foi possível conectar ao banco de dados")
        print()
        print("Verifique:")
        print("  1. A Connection String está correta?")
        print("  2. Você está conectado à internet?")
        print("  3. O projeto Neon está ativo?")
        sys.exit(1)
    
    # Executar migrations
    if not run_migrations():
        print_error("Falha nas migrations")
        print("Você pode tentar manualmente: alembic upgrade head")
        sys.exit(1)
    
    # Verificar tabelas
    verify_tables(url)
    
    # Criar/atualizar .env
    create_env_file(url)
    
    # Instruções para Vercel
    print_vercel_instructions(url)
    
    print_header("CONFIGURAÇÃO LOCAL CONCLUÍDA!")


if __name__ == "__main__":
    main()
