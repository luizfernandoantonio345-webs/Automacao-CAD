-- Script para liberar plano enterprise fixo para o dono do sistema
-- Execute no banco de dados PostgreSQL (banco: engcad)

INSERT INTO users (
    email, username, password_hash, empresa, tier, limite, created_at
) VALUES (
    'santossod345@gmail.com',
    'santossod345',
    '$2b$12$wQwQwQwQwQwQwQwQwQwQwOQwQwQwQwQwQwQwQwQwQwQwQwQwQwQwQwQwQwQwQw', -- hash de 'Santos14!'
    'Conta Enterprise Dono',
    'enterprise',
    9999999,
    extract(epoch from now())
)
ON CONFLICT (email) DO UPDATE SET
    username=EXCLUDED.username,
    password_hash=EXCLUDED.password_hash,
    empresa=EXCLUDED.empresa,
    tier='enterprise',
    limite=9999999,
    created_at=EXCLUDED.created_at;

-- Observação: O hash acima é um placeholder. Recomenda-se gerar o hash real de 'Santos14!' usando bcrypt.