# Programa 2 — Agente de IA (blueprint)

> Este documento é o **projeto completo** do Programa 2: arquitetura, modelo
> de negócio, instalação e suporte. Ainda não é implementação em código — é
> o blueprint que orienta a próxima fase de construção, na mesma lógica que
> o `Projeto_SaaS_Agendamento_Inteligente.md` orientou a construção do
> Programa 1.

---

## 1. Conceito e proposta de valor

Um agente conversacional que atende os clientes finais do seu cliente (o
lojista) via **WhatsApp** (canal principal) e **email** (secundário),
respondendo dúvidas e criando/alterando agendamentos sozinho, 24 horas por
dia — sem precisar de um atendente humano disponível o tempo todo.

**Pitch de vendas**: *"Um funcionário que trabalha 24 horas, tira dúvida,
marca horário e faz atendimento básico — no lugar de contratar 2 ou 3 pessoas
para isso."* Vendido como **upsell** para quem já usa o Programa 1 (ou junto,
para quem está entrando agora).

**Nome do produto/persona**:
- **Persona da IA confirmada**: **Lia** — nome padrão que o cliente final vê
  no WhatsApp. Continua configurável por tenant (`AiAgentConfig`), então um
  cliente pode trocar para outro nome se quiser, mas "Lia" é o padrão de
  fábrica.
- **Marca/produto do Programa 2** (ainda a decidir, candidatos): "Sempre
  Aberto" ou "Atende+".

## 2. Arquitetura técnica

### Decisão central: extensão do backend existente, não um produto separado

O Programa 2 **não duplica** a lógica de agendamento. Ele é um novo módulo
dentro do mesmo backend do Programa 1, porque precisa chamar exatamente as
mesmas funções que já resolvem conflito de horário, RLS e multi-tenancy:
`booking_service.py` e `appointment_service.py`. Um agente de IA com sua
própria lógica de agendamento recriaria — pior, e sem os mesmos testes — tudo
que já está resolvido.

### Peças novas

- **Canal de entrada**: o webhook de WhatsApp já existe
  (`backend/src/app/routers/webhooks.py`, Milestone 7) e hoje só entende
  respostas por palavra-chave ("1" confirma, "2" cancela). Vira uma
  bifurcação: mensagem que não bate com o parser simples **e** tenant com o
  agente de IA habilitado → roteia para o novo `ai_concierge_service.py`. Uma
  mensagem que bate com o parser simples (ex.: "1") continua indo pelo
  caminho antigo, sem passar pela IA — mais barato e mais previsível para o
  caso mais comum (confirmar um lembrete).
- **Tabelas novas**:
  - `ConversationSession` — uma por telefone + tenant, guarda o estado da
    conversa em andamento.
  - `ConversationMessage` — histórico de turnos (auditoria + reconstrução de
    contexto entre mensagens).
  - `AiAgentConfig` — configuração por tenant: nome da persona, tom de voz,
    FAQs extras, liga/desliga do agente.
- **`ai_concierge_service.py`**: monta o *system prompt* daquele tenant
  (nome do negócio, catálogo de serviços, horários, FAQs, tom), acrescenta o
  histórico da conversa, chama a API da Anthropic com *tool use*. As tools
  são wrappers finos sobre funções já existentes:
  - `list_services` → `catalog_repository`
  - `check_availability` → `appointment_service.has_conflict` (a mesma função
    que já protege a agenda visual e o link público)
  - `create_booking` / `cancel_or_reschedule` → `booking_service`
  - `escalate_to_human` → marca a conversa para atendimento humano (não é uma
    tool que "faz" algo sozinha; sinaliza que a IA não deve prosseguir)
- **Roteamento de modelo por custo** (detalhe econômico na Seção 4): Haiku
  4.5 primeiro para triagem e ações diretas; escalar para Sonnet 5 só quando
  o pedido é ambíguo ou multi-etapa.

### Por que isso é seguro de operar

Toda ação que a IA executa passa pelas **mesmas** camadas de serviço e
repositório do Programa 1 — a mesma prevenção de conflito de horário (duas
camadas: checagem na aplicação + exclusion constraint no Postgres), o mesmo
RLS por tenant. A IA não tem um caminho de escrita paralelo e menos
verificado; ela é só mais um cliente das funções que já existem.

## 3. Modelo de negócio

### Precificação: assinatura mensal, não pagamento único

O Programa 1 pode ter uma taxa de implantação única + mensalidade — mas o
Programa 2 tem um **custo variável recorrente real** (tokens de IA a cada
conversa), o que exige receita recorrente para se sustentar. É assim que
praticamente todo produto de "agente de IA" precifica hoje no mercado.

Estrutura sugerida — faixas por volume de conversas por mês. Como o custo de
IA escala com o volume, o preço absoluto sobe junto (isso é esperado — o que
importa é a margem sobre o custo estimado da própria faixa, não o preço por
si só):

| Plano | Conversas/mês | Preço sugerido (a validar) |
|---|---|---|
| Essencial | até 300 | R$297/mês |
| Profissional | até 1.000 | R$797/mês |
| Alto volume | até 3.000 (aviso de uso justo acima disso) | R$1.997/mês |

### Por que o custo de IA não vira uma surpresa na sua própria conta

Como a hospedagem é **centralizada** (você opera uma única conta/chave da
Anthropic para todos os tenants — decisão já confirmada), a mensalidade
cobrada de cada cliente precisa **embutir margem** sobre o custo real de
tokens daquele cliente. Isso é o modelo padrão do mercado — a alternativa
("BYOK", o cliente traz sua própria chave da Anthropic) existe como opção
avançada para clientes de altíssimo volume que queiram eliminar o markup, mas
**não deve ser o modelo padrão**: exige que o cliente crie sua própria conta
na Anthropic, o que vai contra o pedido de instalação simples.

### Estimativa de custo por conversa

Preços atuais da API (Anthropic, via skill `claude-api` — tratar como ponto
de partida, a validar com uso real depois que o Programa 2 estiver no ar):

| Modelo | Entrada (por milhão de tokens) | Saída (por milhão de tokens) |
|---|---|---|
| Haiku 4.5 | US$1,00 | US$5,00 |
| Sonnet 5 | US$3,00 (US$2,00 promocional até 31/08/2026) | US$15,00 (US$10,00 promocional) |

**Prompt caching é a peça decisiva**: o system prompt de cada tenant (dados
do negócio + definição das tools) é idêntico em toda mensagem da mesma
conversa e entre conversas diferentes do mesmo tenant — é o caso de uso ideal
de cache (leitura de cache custa ~10% do preço normal de entrada). Na
prática, depois da primeira mensagem do dia para aquele tenant, a maior parte
do prompt de cada conversa nova já sai quase de graça.

Uma conversa típica de agendamento via WhatsApp (5 a 8 turnos) processa uma
fração pequena de tokens não-cacheados por turno — a mensagem do cliente e
uma resposta curta. Rodando majoritariamente em Haiku com cache ativo, o
custo real de uma conversa simples fica na casa de **poucos centavos de
real**; conversas escaladas para Sonnet (pedidos ambíguos, múltiplas etapas)
custam mais, mas devem ser minoria se a triagem funcionar bem.

**Exemplo de margem** (conservador, com folga para outliers e escalonamento
para Sonnet): supondo uma média de ~R$0,50 por conversa em todas as faixas —

| Plano | Custo estimado de IA | Preço | Margem bruta antes de outros custos |
|---|---|---|---|
| Essencial (300) | ~R$150/mês | R$297/mês | ~R$147 (≈50%) |
| Profissional (1.000) | ~R$500/mês | R$797/mês | ~R$297 (≈37%) |
| Alto volume (3.000) | ~R$1.500/mês | R$1.997/mês | ~R$497 (≈25%) |

A margem percentual cai um pouco nas faixas maiores (efeito natural de
desconto por volume), mas fica positiva e saudável em todas — o modelo
sustenta a receita recorrente sem depender de nenhum plano subsidiar outro.
**Isto é só um ponto de partida**: o número real de conversas por assinante,
a taxa de escalonamento para Sonnet e o comprimento médio de conversa vão
definir a economia de verdade. Recomendação prática: comece com os preços
acima como hipótese, rode um piloto pequeno (5-10 clientes), meça o custo
real de IA por tenant nas primeiras semanas, e reajuste as faixas/preços com
base nisso antes de vender em escala.

**Mitigação de abuso/outlier**: teto mensal de conversas por tenant e por
plano, com aviso gracioso ("estamos com alta demanda, fale com nosso time")
ao ultrapassar, em vez de corte abrupto do serviço.

## 4. Manual de instalação (para o próprio usuário executar)

Como é centralizado, "instalar" o Programa 2 para um cliente = provisionar um
tenant, não instalar nada na máquina do cliente:

1. Reaproveitar o comando `create-tenant` já existente na CLI
   (`backend/src/app/cli.py`, Milestone 3) — ou o tenant já existe, se o
   cliente já usa o Programa 1.
2. Habilitar `ai_concierge_enabled=true` para aquele tenant.
3. Preencher a persona (nome, tom, FAQs extras) numa tela simples do painel
   administrativo (a construir na próxima fase).
4. Confirmar que o número de WhatsApp do cliente já está linkado (reaproveita
   a infraestrutura de webhook da Milestone 7).

Este passo a passo deve virar um manual detalhado, com telas, quando o código
for implementado.

## 5. Suporte ao cliente

Como a hospedagem é centralizada, dar suporte a um cliente do Programa 2
significa investigar/corrigir algo na mesma infraestrutura que você já
opera — exatamente como esta sessão de trabalho já funciona hoje. Não existe
necessidade de acesso administrativo à infraestrutura de terceiros: o acesso
é sempre à sua própria infraestrutura, para todos os clientes.

## Próximos passos

Este documento é o projeto. A implementação em código (tabelas, service,
integração com a API da Anthropic, tela de configuração da persona) é a
próxima fase de construção, depois que este blueprint for revisado.
