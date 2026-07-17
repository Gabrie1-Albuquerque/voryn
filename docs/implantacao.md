# Guia de Implantação — Voryn

Checklist direto ao ponto para colocar um novo assinante no ar, do zero até
notificações e pagamentos reais funcionando. Tempo total típico: **30–45 min**,
sendo a maior parte cadastro de catálogo.

---

## 1. Criar a empresa (você, via SSH no servidor)

```bash
ssh -i ~/.ssh/voryn-app.pem ubuntu@54.227.8.122
cd /home/ubuntu/voryn-app
docker compose -f docker-compose.prod.yml exec backend python -m app.cli create-tenant \
  --company-name "Nome da Empresa" \
  --company-slug nome-da-empresa \
  --admin-email dono@empresa.com \
  --admin-password "senha-temporaria-forte"
```

- O **slug** vira a URL pública: `https://voryn.app.br/booking/{slug}` — curto,
  minúsculo, com hífens.
- Peça para o assinante trocar a senha no primeiro acesso ("Esqueci minha
  senha" na tela de login também funciona).

## 2. Configurar o negócio (pelo painel, em `voryn.app.br/login`)

Na ordem — cada passo depende do anterior:

1. **Configurações → Informações da empresa**: confira nome/fuso; decida se
   agendamentos do link público confirmam sozinhos.
2. **Serviços & Salas**: cadastre cada serviço (nome, duração, preço) e, nos
   que exigem sinal, use **Editar → Exige sinal** (valor fixo ou %). Salas só
   se o negócio usa espaços limitados.
3. **Funcionários**: cadastre cada profissional e — passo que mais esquece —
   clique em **Configurar** para marcar **quais serviços atende** e os
   **horários de trabalho**. Sem isso o profissional NÃO aparece no link
   público (a tabela mostra ⚠ quando falta algo).
4. **Configurações → Lembretes**: padrão 24h/2h; ajuste se o assinante quiser.
5. **Configurações → Seu link de agendamento**: copie e entregue ao assinante
   (bio do Instagram, status do WhatsApp, Google).

## 3. Email real (5 min, funciona imediatamente)

O email sai da conta do próprio assinante, via SMTP:

1. Na conta Gmail do negócio: ativar **Verificação em duas etapas** →
   [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   → gerar uma **senha de app** (16 letras). Outlook/outros têm fluxo similar.
2. Painel → **Configurações → Email (SMTP)**:
   - Servidor: `smtp.gmail.com` · Porta: `587`
   - Usuário e remetente: o email do negócio · Senha: a senha de app
3. **Testar conexão** → deve dar sucesso → **Salvar**.
4. A partir daí, todo cliente final **com email cadastrado** recebe
   confirmações/lembretes reais por email. (O email do cliente entra pelo
   formulário do link público ou pela tela Clientes.)

## 4. WhatsApp real (10 min + escanear QR)

As mensagens saem do **número do próprio negócio** (Evolution API
auto-hospedada — custo R$0/mês). O celular do assinante continua funcionando
normal (conexão tipo WhatsApp Web).

1. Painel → **Configurações → WhatsApp** → **Conectar WhatsApp** → aparece um
   QR code.
2. No celular do negócio: WhatsApp → Configurações → **Aparelhos conectados**
   → Conectar aparelho → escanear o QR. (Expira rápido; se falhar, "Gerar
   novo QR".)
3. Badge muda para **✓ WhatsApp conectado**. Pronto: confirmações, lembretes
   (24h/2h ou o que estiver configurado), cancelamentos e lista de espera
   saem sozinhos — e o cliente pode responder **1** para confirmar / **2**
   para cancelar.
4. Teste: crie um agendamento de teste com o SEU número como cliente e
   confira a mensagem chegando.

Pré-requisito de servidor (uma vez só, já parte do deploy): serviço
`evolution` no ar, `EVOLUTION_API_KEY` no `.env`, database `evolution` criado
no Postgres — ver comentários em `docker-compose.prod.yml`.

## 5. Pagamentos: sinal caindo na conta do assinante (10 min)

O sinal via PIX cai **direto na conta Mercado Pago do assinante** — a Voryn
nunca toca no dinheiro.

1. O assinante cria/usa conta em [mercadopago.com.br](https://mercadopago.com.br)
   (gratuita) e, em **Seu negócio → Configurações → Credenciais de produção**,
   copia o **Access Token** (começa com `APP_USR-`; o `TEST-` é sandbox e NÃO
   recebe dinheiro real — a tela avisa se colar o errado).
2. Painel → **Configurações → Pagamentos (Mercado Pago)** → colar o token →
   **Testar token** (mostra o apelido da conta) → **Salvar**.
3. No painel do Mercado Pago, em **Webhooks/Notificações**, cadastrar a URL
   exibida no card (formato
   `https://voryn.app.br/webhooks/mercadopago/{slug}`), evento *Pagamentos* —
   e colar a **assinatura secreta** gerada lá de volta no card, campo
   "Assinatura secreta do webhook" → Salvar.
4. Teste de fogo: marque pelo link público um serviço com sinal, pague R$1 de
   verdade (configure um serviço-teste com sinal de R$1), confira o dinheiro
   na conta MP do assinante e o agendamento confirmando sozinho. Depois
   apague o serviço-teste.

Sem Mercado Pago configurado, serviços com sinal usam o modo simulado
(confirmam sem cobrar) — configure antes de ativar sinal em serviço real.

## 6. Teste final de ponta a ponta (5 min)

- [ ] Abrir o link público em aba anônima → serviço → profissional → horário →
      agendar com um telefone/email de teste.
- [ ] Mensagem de confirmação chegou no WhatsApp? E no email?
- [ ] Agendamento apareceu na Agenda do painel?
- [ ] Responder **2** no WhatsApp → cancelou no painel?
- [ ] (Se sinal ativo) PIX de R$1 caiu na conta MP e confirmou o horário?

Tudo ✓ → assinante no ar. Combine a data de revisão do período de teste.
