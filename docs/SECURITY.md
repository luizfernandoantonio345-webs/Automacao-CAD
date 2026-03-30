# Security Policy

## Supported Versions

Atualmente, apenas a branch principal e a ultima release estavel sao suportadas com correcoes de seguranca.

## Reporting a Vulnerability

Para reportar vulnerabilidades:

1. Nao abra issue publica com detalhes sensiveis.
2. Envie o relato com evidencias, impacto e passos de reproducao para o canal interno de seguranca da equipe.
3. Inclua versao, ambiente (dev/staging/prod) e logs relevantes sem dados pessoais.

Fluxo de tratamento:

1. Triage inicial em ate 2 dias uteis.
2. Classificacao de severidade (Critica, Alta, Media, Baixa).
3. Correcao e validacao em ambiente de staging.
4. Publicacao com changelog e janela de atualizacao.

## Security Requirements (Production)

- Segredos apenas por variaveis de ambiente e gerenciador de segredos.
- Rotacao periodica de chaves e tokens.
- Sem credenciais em README, codigo, logs ou fixtures publicas.
- Dependencias com varredura continua (SCA) no CI.
- Autenticacao com hash bcrypt e tokens com expiracao.
- Backup e restore testados periodicamente.

## Hardening Checklist

- [ ] SAST no CI
- [ ] SCA no CI
- [ ] DAST em staging
- [ ] Alertas de seguranca configurados
- [ ] Inventario de ativos e SBOM
- [ ] Plano de resposta a incidente atualizado
