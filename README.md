# Plataforma Inteligente de Agendamentos

SaaS multiempresa de agendamento para salões, clínicas, barbearias, pet shops
e negócios de serviço em geral — reduz faltas com lembretes/confirmação
automática e agendamento online, com dashboard gerencial. Ver
[`Projeto_SaaS_Agendamento_Inteligente.md`](./Projeto_SaaS_Agendamento_Inteligente.md)
para a especificação de produto original.

## Stack

- **Backend**: FastAPI (async), SQLAlchemy 2.0 + `asyncpg`, PostgreSQL 16, Redis, RQ + rq-scheduler.
- **Frontend**: React 19 + Vite + TypeScript, TanStack React Query, FullCalendar, Recharts, React Router.
- **Infra**: Docker Compose, nginx, `uv` (gestão de dependências Python).
- **Multi-tenancy**: banco compartilhado + `tenant_id` em cada tabela, reforçado por Row-Level Security do Postgres (defesa em profundidade, não a única camada).

## Pré-requisitos

- Docker + Docker Compose.
- Nada além disso é necessário no host — `uv`/Node/Python não precisam estar instalados; tudo roda em containers.

## Subindo o ambiente de desenvolvimento

```bash
cp .env.example .env
# Edite .env: pelo menos gere um JWT_SECRET_KEY de verdade
# (openssl rand -hex 32) antes de qualquer uso além do seu próprio localhost.

docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Serviços expostos: `http://localhost:8080` (app via nginx), `http://localhost:8000` (backend direto), `http://localhost:5173` (frontend direto, sem nginx).

### Criando a primeira empresa (tenant)

Onboarding é provisionado pelo admin (sem autocadastro público), alinhado à
estratégia comercial do produto (demo + implantação paga):

```bash
docker compose exec backend python -m app.cli create-tenant \
  --company-name "Salão Exemplo" \
  --company-slug salao-exemplo \
  --admin-email admin@exemplo.com \
  --admin-password "SenhaForte123!"
```

Login em `http://localhost:8080/login`. A página pública de agendamento
dessa empresa fica em `http://localhost:8080/booking/salao-exemplo`.

## Rodando os testes

O backend não tem `pytest` na imagem de produção (deliberado — dependências
de teste não pertencem à imagem que roda em produção). Para rodar a suíte:

```bash
docker run --rm \
  --network projeto_agendamento_default \
  -v "$(pwd)/backend:/app" -w /app \
  ghcr.io/astral-sh/uv:python3.12-trixie-slim \
  sh -c "uv sync --locked && uv run pytest"
```

(O nome da rede pode variar; confira com `docker network ls` se o comando
acima não encontrar o Postgres. Ele já precisa estar de pé via
`docker compose up -d`.)

Type-check e lint do frontend (sem precisar de Node instalado no host):

```bash
docker run --rm -v "$(pwd)/frontend:/app" -w /app node:22-slim \
  sh -c "npm install && npx tsc -b --noEmit && npx oxlint"
```

## Estrutura do projeto

```
backend/src/app/
  core/         # config, security (JWT/hash), database (RLS), exceptions
  models/       # SQLAlchemy 2.0, TenantMixin/TimestampMixin
  schemas/      # Pydantic, espelha models/
  repositories/ # única camada que fala SQLAlchemy, sempre tenant-scoped
  services/     # regra de negócio (máquina de estados de agendamento, etc.)
  providers/    # notificações/pagamento/email plugáveis (mock/console por padrão)
  routers/      # HTTP, fino
  workers/      # jobs RQ (lembretes) + rq-scheduler
frontend/src/
  api/, auth/, components/, lib/
  features/{agenda,clients,catalog,employees,dashboard,public-booking,auth}/
```

## Provedores plugáveis

Notificação (WhatsApp), pagamento (Mercado Pago) e email seguem o mesmo
padrão: uma interface abstrata + um provedor mock/console (sem nenhuma
credencial externa, ligado por padrão) + um provedor real selecionado por
variável de ambiente (`NOTIFICATION_PROVIDER`, `PAYMENT_PROVIDER`,
`EMAIL_PROVIDER` em `.env`). O fluxo inteiro (lembretes, confirmação por
WhatsApp, sinal de pagamento) funciona ponta a ponta com os provedores
mock/console, sem precisar de nenhuma conta externa para testar.

- **WhatsApp real**: precisa de uma conta Meta Business App aprovada — fora
  do nosso controle, processo de dias/semanas. O provedor (`WhatsAppCloudProvider`/
  `ZApiProvider`) está implementado mas não validado contra uma conta real.
- **Mercado Pago real**: use um token de **sandbox** (formato `TEST-...`,
  não `APP_USR-...` — este último é o formato de produção, mesmo que apareça
  listado sob uma aba "de teste" no painel). Configure
  `MERCADOPAGO_ACCESS_TOKEN` e `PAYMENT_PROVIDER=mercadopago` em `.env`.

## Deploy em produção

`docker-compose.prod.yml` é um compose completo e independente (não um
overlay do arquivo de dev): sem bind-mount do código-fonte (roda a imagem
como construída), sem portas do Postgres/Redis publicadas para fora (só
acessíveis pela rede interna dos containers), frontend servido como bundle
estático pelo nginx em vez do dev server do Vite.

```bash
cp .env.example .env
# Edite .env com valores reais: JWT_SECRET_KEY forte, senhas de banco
# fortes, CORS_ORIGINS/PUBLIC_APP_URL com o domínio real, e mude
# DEBUG=true para DEBUG=false (desliga o eco de SQL do SQLAlchemy).

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python -m app.cli create-tenant ...
```

Nginx expõe a porta 80 (HTTP simples). Conforme a arquitetura da
especificação original (`Cliente -> Cloudflare -> Nginx -> FastAPI -> ...`),
TLS é terminado por um proxy reverso na frente deste nginx (Cloudflare ou
equivalente) — não é feito por este Compose.

### Backup

`scripts/backup.sh` faz um dump diário do Postgres (gzipped, com retenção de
14 dias localmente):

```bash
./scripts/backup.sh                    # backups/ (dev, docker-compose.yml)
./scripts/backup.sh backups prod       # contra docker-compose.prod.yml
```

Agende via cron do host (`crontab -e`):

```
0 3 * * * cd /caminho/para/Projeto_agendamento && ./scripts/backup.sh backups prod >> backups/backup.log 2>&1
```

Isso é um backup em disco local, não externo — para produção de verdade,
copie o conteúdo de `backups/` para fora da própria VPS (armazenamento de
objetos, outro host) periodicamente, já que um disco local não protege
contra a falha do próprio disco/VPS.

## Revisão de segurança (contra a lista da especificação original)

| Item | Status |
|---|---|
| HTTPS | Fora do escopo deste Compose por design — terminado por um proxy reverso na frente (Cloudflare ou equivalente), conforme a arquitetura da especificação. |
| MFA | **Adiado conscientemente** para logo após este MVP (decisão confirmada durante o planejamento) — não implementado. |
| Criptografia | Senhas com Argon2 (`pwdlib`), nunca em texto plano. Tráfego em trânsito depende do HTTPS configurado no proxy de borda (acima). Dados em repouso (disco do Postgres) **não são criptografados a nível de aplicação** — depende de criptografia de disco na VPS/provedor, não implementada aqui. |
| Logs | `logging.basicConfig` configurado; nenhuma rota loga senha em texto plano (senha nunca vira parâmetro de query SQL — só é comparada em memória contra o hash). Em produção, `DEBUG=false` desliga o eco de SQL do SQLAlchemy (que, em dev, loga parâmetros de query — nenhum deles é uma senha, mas é hábito melhor manter desligado fora de dev). |
| Auditoria | `AppointmentStatusHistory` registra toda transição de status (quem, quando, de/para). Não há trilha de auditoria genérica para todas as tabelas (ex: quem editou um cadastro de cliente) — só para o fluxo de agendamento, o mais crítico. |
| LGPD | Controle de acesso (RBAC + RLS) implementado. **Não implementado**: exportação/exclusão de dados a pedido do titular, gestão de consentimento, política de retenção de dados — necessários para conformidade completa antes de um lançamento real, fora do escopo deste MVP técnico. |

## O que fica de fora deste MVP (Fase 1)

- WhatsApp Business API real (aprovação externa) e Mercado Pago em produção
  (token sandbox `TEST-...` ainda não confirmado) — código pronto, não
  validado ao vivo.
- MFA — adiado por decisão já confirmada.
- Exportação/exclusão de dados (LGPD), criptografia em repouso, auditoria
  genérica além do fluxo de agendamento.
- Fases 2 e 3 do roadmap original (financeiro, fidelidade, Google Calendar,
  API pública, IA, app mobile).
