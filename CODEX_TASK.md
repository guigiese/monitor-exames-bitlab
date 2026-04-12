# Tarefa Codex — Módulo Plantão (parte mecânica)

**Ao concluir: apagar este arquivo e abrir PR de `session/20260412-plantao-foundation` → `main`.**

---

## O que já existe

```
modules/plantao/
  schema.py       — 12 tabelas, init_schema(), seed feriados/tarifas
  business.py     — lógica pura (horas, prazos, tarifas, remuneração)
  auth.py         — sessão isolada plantonista, CSRF, guards
  audit.py        — log imutável
  notifications.py — notificações in-app
  jobs.py         — loop background
  router.py       — TODAS as rotas declaradas; auth (login/cadastro/logout/senha) IMPLEMENTADO; demais raise NotImplementedError
  queries.py      — stubs com docstrings completas
  actions.py      — stubs com docstrings completas
  templates/      — plantao_base.html, plantao_admin_base.html, todos os templates de auth
```

## Sua tarefa

Implementar em ordem:

### 1. queries.py — todos os `raise NotImplementedError`
SELECT puro, sem efeitos colaterais. Ver docstring de cada função para a query esperada.

### 2. actions.py — todos os `raise NotImplementedError`
Cada função deve: validar pré-condições → transaction → `audit()` → `notificar()` quando relevante.
Imports necessários:
```python
from .audit import audit
from .notifications import notificar
from .business import calcular_horas_turno, calcular_valor_base, pode_cancelar, inferir_subtipo
from .queries import (get_perfil_por_id, get_candidatura, get_posicao, get_data_plantao,
                      listar_tarifas_vigentes, get_set_feriados, contar_confirmados_por_posicao)
from pb_platform.security import hash_password, verify_password
from .auth import revogar_todas_sessoes
```

> `app_kv`: verificar se existe no schema. Se não, adicionar em `init_schema()`:
> `CREATE TABLE IF NOT EXISTS app_kv (chave TEXT PRIMARY KEY, valor TEXT NOT NULL, alterado_em TEXT NOT NULL)`

### 3. router.py — todos os `raise NotImplementedError`
Cada endpoint tem comentário `# TODO (Codex): ...` indicando qual função chamar.
Seguir o padrão dos endpoints já implementados no mesmo arquivo.

### 4. Templates — criar os faltantes

**Plantonista** (herda `plantao_base.html`):
- `plantao_escalas.html` — calendário CSS Grid com datas, cores por status, botão "Candidatar" com HTMX
- `plantao_meus_turnos.html` — candidaturas agrupadas por status, botão cancelar
- `plantao_trocas.html` — lista de trocas + substituições abertas, formulário solicitar troca
- `plantao_sobreaviso.html` — minha posição na lista + aderir/cancelar (**sem campo de remuneração**)

**Admin** (herda `plantao_admin_base.html`, colocar em `templates/admin/`):
- `dashboard.html` — cards: cadastros pendentes, datas sem vagas, sobreaviso vazio
- `cadastros.html` — tabs pendente/ativo/inativo, botões aprovar/rejeitar
- `escalas.html` — calendário + formulário criar data + botão "Gerar mês completo"
- `candidaturas.html` — filtro data_id, tabela com botões confirmar/recusar
- `sobreaviso.html` — lista ordenável (botões ↑↓), sem mostrar remuneração
- `relatorios.html` — índice dos 4 relatórios
- `relatorios_escalas.html`, `relatorios_participacao.html`, `relatorios_cancelamentos.html`, `relatorios_pre_fechamento.html`
- `locais.html`, `tarifas.html`, `feriados.html`, `configuracoes.html`, `audit_log.html`

---

## Regras de negócio (não inventar variações)

| Regra | Detalhe |
|---|---|
| Remuneração vet | `MAX(valor_base_calculado, comissão_dia_INTEIRO)` — comissão = dia inteiro no SimplesVet, SEM filtro de horário |
| Remuneração aux | `valor_hora × horas_turno`, sem comissão |
| Sobreaviso | **NÃO remunerado**. `valor_base_calculado = NULL`. Não exibir remuneração na tela do plantonista |
| Pré-fechamento | Excluir sobreaviso do cálculo; aparece em seção separada apenas informativa |
| Subtipo | `regular`/`substituicao`/`feriado` diferem APENAS na tarifa — fluxo idêntico |
| Candidatura duplicada | Bloquear se status NOT IN ('cancelado','recusado') no mesmo perfil+data |
| Lista de espera | Ao cancelar confirmado → promover menor `ordem_espera` para 'provisorio' |
| Prazo cancelamento | `business.pode_cancelar()` — horas úteis seg-sex 08h-18h; padrão 24h em `app_kv` |
| Troca expira | direta=48h, substituição=72h; `aceitar_troca()` deve ser atômica |
| Sobreaviso prioridade | 1=principal; ao cancelar prioridade=1, próximo assume; reordenar sem gaps |
| Auth | Gestor = cookie `session_token` + `users.gestor_plantao=1`; Plantonista = cookie `plantao_session` |

## Stack e convenções

- **Banco**: SQLAlchemy Core 2.0, `text()` + named params, nunca ORM, nunca f-string em query
- **Timestamps**: TEXT ISO 8601 `"YYYY-MM-DDTHH:MM:SS"` (sem timezone)
- **Writes**: `engine.begin()`. **Reads**: `engine.connect()`
- **CSRF**: `_validar_csrf_ou_403()` em TODOS os POST de plantonista
- **IDOR**: verificar `perfil_id` antes de qualquer modificação de recurso
- **Templates**: TailwindCSS CDN (já no base), mobile-first `max-w-2xl mx-auto`

## Checklist de aceite

- [ ] Nenhum `NotImplementedError` restante em queries/actions/router
- [ ] Todos os templates renderizam sem erro
- [ ] CSRF em todos os POSTs de plantonista
- [ ] IDOR verificado em candidaturas, trocas e sobreaviso
- [ ] Sobreaviso: sem campo de remuneração em nenhuma tela
- [ ] Relatório pré-fechamento: sobreaviso excluído do cálculo
- [ ] `init_schema()` idempotente
- [ ] Apagar este arquivo (CODEX_TASK.md)
- [ ] Abrir PR `session/20260412-plantao-foundation` → `main`
