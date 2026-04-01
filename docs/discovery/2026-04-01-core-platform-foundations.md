# Discovery - Core Platform Foundations

Data: 2026-04-01
Escopo Jira: `PBCORE-14`, `PBCORE-15`, `PBCORE-18`, `PBCORE-21`, `PBCORE-22`

## Objetivo

Detalhar a próxima camada estrutural da PinkBlue Vet para que o Lab Monitor deixe de depender de memória + arquivos locais como base operacional.

Esta nota não implementa nada. Ela organiza:

- o problema atual;
- a proposta de arquitetura;
- as ferramentas recomendadas;
- a infra necessária;
- a sequência segura de migração.

## Estado atual observado no repositório

O módulo já está funcional, mas hoje sua base operacional ainda depende de mecanismos transitórios:

- `web/state.py` mantém snapshots, últimos checks, erros e feed em memória;
- `config.json` continua sendo lido e escrito no disco do container;
- `telegram_users.json` ainda representa um cadastro operacional fora de banco;
- `core.py` usa `_EXTERNAL_EVENT_CACHE` em memória para deduplicar eventos externos;
- `notifiers/telegram.py`, `labs/bitlab.py` e `labs/nexio.py` ainda possuem fallbacks sensíveis no código;
- `git remote -v` ainda expõe token no próprio URL remoto local;
- `.secrets` segue como mecanismo de desenvolvimento local, o que é aceitável apenas enquanto isolado e nunca versionado.

Consequência prática:

- restart/redeploy reseta parte da operação;
- a idempotência de notificações não sobrevive a restart;
- não há base persistente para auth, auditoria ou preferências;
- a superfície de segredos está maior do que deveria.

## Recomendação de arquitetura

### 1. Persistência

Recomendação principal:

- adicionar um serviço PostgreSQL no Railway como banco transacional da plataforma;
- manter a aplicação web/monitor como serviço separado, consumindo esse banco;
- usar camada ORM/migrations para evitar SQL espalhado e permitir evolução controlada.

Stack sugerida:

- SQLAlchemy 2.0 como ORM e engine principal;
- Alembic para migrations versionadas;
- Pydantic Settings para centralizar configuração e origem dos segredos;
- Railway PostgreSQL como primeiro banco oficial da plataforma.

Justificativa:

- SQLAlchemy 2.0 continua sendo a base ORM mais madura para um backend Python desse porte;
- Alembic resolve a trilha de mudanças de schema sem improviso;
- Pydantic Settings reduz o acoplamento atual com `os.environ` espalhado e `.secrets` ad hoc;
- Postgres resolve de uma vez estado operacional, auth, auditoria e preferências.

### 2. Auth e permissões

Para o estado atual do app, a recomendação não é JWT-first.

Como a interface é majoritariamente server-rendered (`Jinja2 + HTMX`), o encaixe mais natural é:

- login por usuário/senha;
- sessão por cookie assinado;
- escopos/perfis simples (`admin`, `operator`, `viewer`);
- proteção das rotas `/labmonitor/*` e `/ops-map/*`.

Modelo inicial recomendado:

- `users`
- `roles`
- `user_roles`
- `sessions` ou sessões assinadas com estado mínimo no servidor

### 3. Segredos

Recomendação pragmática por fase:

- fase 1: concentrar segredos de produção exclusivamente nas variables do Railway;
- fase 2: remover fallbacks sensíveis do código e limpar remoto/token local;
- fase 3: só avaliar Vault quando houver mais de um serviço relevante, mais de um ambiente crítico ou exigência de rotação/auditoria mais forte.

Importante:

- Vault faz sentido como camada de maturidade, não como primeiro passo obrigatório;
- para o momento atual, Railway variables + saneamento do repositório trazem o maior ganho pelo menor custo operacional.

### 4. Observabilidade

Recomendação mínima para a próxima fase:

- endpoint de health/readiness do app;
- heartbeat do loop de monitoramento;
- último sucesso/erro por lab persistido;
- execuções de sync registradas em tabela;
- eventos de notificação persistidos com status de envio;
- uso do `/ops-map/` como painel operacional de alto nível, não como fonte primária de verdade.

Isto dá visibilidade para:

- falha de conector;
- atraso de loop;
- fila de envio;
- regressões de deploy;
- diferença entre “app no ar” e “operação saudável”.

## Modelo de dados sugerido para a primeira fase

Não é o modelo final da plataforma inteira; é o recorte mínimo para estabilizar o Lab Monitor.

### Tabelas de operação

- `sync_runs`
  - um registro por execução do monitor por lab
  - guarda início, fim, status, quantidade de registros, erro

- `lab_records`
  - representa a requisição/grupo do snapshot
  - chave natural: `lab_id + record_id`

- `lab_items`
  - itens/exames dentro do record
  - status atual, timestamps relevantes, `portal_id`, metadados do item

- `item_status_events`
  - histórico de transição relevante
  - permite auditoria e explicação de notificações

- `notification_events`
  - eventos externos gerados/enviados
  - assinatura idempotente, canal, payload resumido, resultado do envio

- `telegram_subscriptions`
  - substitui `telegram_users.json`

- `app_settings`
  - configurações operacionais editáveis sem depender de arquivo no container

### Tabelas de acesso

- `users`
- `roles`
- `user_roles`
- opcional depois: `audit_log`

## Ferramentas / infra necessária

### Necessário para a próxima fase

- 1 serviço PostgreSQL no Railway
- 1 pipeline de migrations com Alembic
- 1 módulo de configuração central (`settings.py`)
- 1 estratégia de backup/restore do banco
- limpeza dos segredos/fallbacks atuais

### Opcional, mas não prioritário agora

- Vault como cofre dedicado
- SSO
- event bus
- observabilidade externa dedicada

## Migração sugerida por etapas

### Etapa 0 - Saneamento sem mudar comportamento

- remover tokens/fallbacks sensíveis do código;
- remover token do `git remote`;
- parar de tratar `telegram_users.json` como base aceitável de longo prazo;
- centralizar configuração em objeto de settings.

### Etapa 1 - Banco no ar sem trocar o comportamento do produto

- provisionar Postgres no Railway;
- criar migrations iniciais;
- introduzir tabelas de operação e acesso;
- manter o app ainda lendo o estado legado onde necessário.

### Etapa 2 - Migrar estado operacional

- migrar inscrições do Telegram;
- migrar idempotência de eventos externos;
- persistir sync runs e erros por lab;
- persistir settings editáveis.

### Etapa 3 - Migrar estado de domínio do monitor

- gravar records/items no banco;
- preservar histórico mínimo de transições;
- parar de depender da memória como fonte principal.

### Etapa 4 - Ligar auth/perfis

- login e sessão;
- proteção das rotas;
- perfis mínimos por tipo de usuário.

## Proposta objetiva por card

### `PBCORE-14` - arquitetura de persistência

Saída esperada:

- decisão por Postgres no Railway;
- escolha do stack de persistência;
- modelo inicial de tabelas;
- critério do que continua arquivo e do que vira dado persistido.

### `PBCORE-15` - plano de migração

Saída esperada:

- sequência de rollout por etapas;
- risco por etapa;
- estratégia de fallback;
- critérios de corte para abandonar memória/JSON.

### `PBCORE-18` + `PBCORE-21` - segredos e artefatos operacionais

Saída esperada:

- lista objetiva do que precisa sair do código/repo;
- novo lugar de cada segredo/artefato;
- política para desenvolvimento local versus produção.

### `PBCORE-22` - observabilidade

Saída esperada:

- health/readiness;
- heartbeat do monitor;
- registro persistido de syncs/notificações;
- painel operacional acoplado ao `/ops-map/`.

## Perguntas em aberto para responder no momento oportuno

1. Quais dados do Lab Monitor precisam sobreviver obrigatoriamente a todo redeploy?
2. O acesso ao módulo será só interno da clínica ou haverá usuários externos?
3. O Telegram deve continuar sendo o canal operacional principal mesmo após auth e banco?
4. O `config.json` deve desaparecer por completo ou permanecer como bootstrap imutável?

## Fontes externas consultadas

- Railway docs - backups/volumes: https://docs.railway.com/volumes/backups
- FastAPI SQL databases: https://fastapi.tiangolo.com/tutorial/sql-databases/
- SQLAlchemy ORM quickstart: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Starlette auth/permissions: https://www.starlette.io/authentication/
- Vault auth concepts: https://developer.hashicorp.com/vault/docs/concepts/auth
- Vault AppRole: https://developer.hashicorp.com/vault/docs/auth/approle
