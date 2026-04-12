"""
Módulo Plantão — camada de leitura do banco (queries).

CONVENÇÃO:
- Todas as funções aqui são leituras (SELECT). Nenhuma escrita.
- Recebem `engine` como primeiro argumento.
- Retornam dict, list[dict] ou None. Nunca Row objects.
- Nomes: listar_*, buscar_*, contar_*, get_*.

TODO (Codex): implementar todas as funções abaixo.
Cada função tem docstring completa descrevendo inputs, outputs e a query
esperada. Implemente seguindo o padrão SQLAlchemy Core com text() e named
parameters — mesmo padrão de pb_platform/storage.py.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text


# ── Locais ────────────────────────────────────────────────────────────────────

def listar_locais(engine: Any, apenas_ativos: bool = True) -> list[dict]:
    """Lista todos os locais de plantão.

    SELECT * FROM plantao_locais [WHERE ativo=1] ORDER BY nome.
    """
    raise NotImplementedError


def get_local(engine: Any, local_id: int) -> dict | None:
    """Busca um local pelo ID."""
    raise NotImplementedError


# ── Perfis ────────────────────────────────────────────────────────────────────

def get_perfil_por_email(engine: Any, email: str) -> dict | None:
    """Busca perfil pelo e-mail (case-insensitive)."""
    raise NotImplementedError


def get_perfil_por_id(engine: Any, perfil_id: int) -> dict | None:
    """Busca perfil pelo ID."""
    raise NotImplementedError


def listar_perfis(
    engine: Any,
    status: str | None = None,
    tipo: str | None = None,
) -> list[dict]:
    """Lista perfis opcionalmente filtrados por status e/ou tipo.

    status: 'pendente' | 'ativo' | 'inativo' | 'rejeitado' | None (todos)
    tipo:   'veterinario' | 'auxiliar' | None (todos)
    ORDER BY nome ASC.
    """
    raise NotImplementedError


# ── Tarifas ───────────────────────────────────────────────────────────────────

def listar_tarifas_vigentes(engine: Any, data_ref: str) -> list[dict]:
    """Lista tarifas vigentes na data_ref (YYYY-MM-DD).

    WHERE vigente_de <= data_ref AND (vigente_ate IS NULL OR vigente_ate >= data_ref)
    ORDER BY tipo_perfil, dia_semana NULLS LAST, subtipo_turno NULLS LAST.
    """
    raise NotImplementedError


# ── Feriados ──────────────────────────────────────────────────────────────────

def listar_feriados_por_periodo(
    engine: Any,
    data_inicio: str,
    data_fim: str,
    local_id: int | None = None,
) -> list[dict]:
    """Lista feriados no intervalo [data_inicio, data_fim].

    Inclui feriados nacionais (local_id IS NULL) + feriados do local se local_id fornecido.
    """
    raise NotImplementedError


def get_set_feriados(
    engine: Any,
    data_inicio: str,
    data_fim: str,
    local_id: int | None = None,
) -> set:
    """Retorna set de date Python para uso em business.py.

    Chama listar_feriados_por_periodo e converte datas para date objects.
    """
    from datetime import date
    rows = listar_feriados_por_periodo(engine, data_inicio, data_fim, local_id)
    return {date.fromisoformat(r["data"]) for r in rows}


# ── Datas de plantão ──────────────────────────────────────────────────────────

def listar_datas_por_mes(
    engine: Any,
    ano: int,
    mes: int,
    local_id: int | None = None,
    tipo: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Lista datas de plantão de um mês específico.

    Joins com plantao_posicoes para incluir contagem de vagas e preenchimento.
    """
    raise NotImplementedError


def get_data_plantao(engine: Any, data_id: int) -> dict | None:
    """Busca uma data de plantão pelo ID, com posições e candidaturas."""
    raise NotImplementedError


def listar_datas_com_vagas_abertas(
    engine: Any,
    local_id: int | None = None,
    tipo_perfil: str | None = None,
) -> list[dict]:
    """Lista datas publicadas com vagas ainda disponíveis para candidatura.

    Vaga disponível = posicao.vagas > COUNT(candidaturas confirmadas).
    Inclui apenas data >= hoje.
    """
    raise NotImplementedError


# ── Posições ──────────────────────────────────────────────────────────────────

def listar_posicoes_por_data(engine: Any, data_id: int) -> list[dict]:
    """Lista posições (vagas) de uma data com contagem de candidatos por posição."""
    raise NotImplementedError


def get_posicao(engine: Any, posicao_id: int) -> dict | None:
    """Busca posição pelo ID, com data de plantão joinada."""
    raise NotImplementedError


# ── Candidaturas ──────────────────────────────────────────────────────────────

def listar_candidaturas_por_data(
    engine: Any,
    data_id: int,
    status: str | None = None,
) -> list[dict]:
    """Lista candidaturas de uma data, com perfil do plantonista joinado.

    ORDER BY posicao_id, status, criado_em.
    """
    raise NotImplementedError


def listar_candidaturas_por_perfil(
    engine: Any,
    perfil_id: int,
    apenas_futuras: bool = False,
    status: str | None = None,
) -> list[dict]:
    """Lista candidaturas de um plantonista, com data de plantão joinada.

    ORDER BY data DESC, hora_inicio.
    """
    raise NotImplementedError


def get_candidatura(engine: Any, candidatura_id: int) -> dict | None:
    """Busca candidatura pelo ID, com posição e data joinadas."""
    raise NotImplementedError


def candidatura_existe(engine: Any, perfil_id: int, data_id: int) -> bool:
    """Verifica se o perfil já tem candidatura ativa na mesma data/turno.

    Uma candidatura 'cancelada' ou 'recusada' não bloqueia nova candidatura.
    """
    raise NotImplementedError


def contar_confirmados_por_posicao(engine: Any, posicao_id: int) -> int:
    """Conta candidaturas confirmadas em uma posição."""
    raise NotImplementedError


# ── Trocas ────────────────────────────────────────────────────────────────────

def listar_trocas_por_perfil(
    engine: Any,
    perfil_id: int,
    status: str | None = None,
) -> list[dict]:
    """Lista trocas/substituições onde o perfil é parte (a ou b).

    Inclui candidaturas e datas joinadas.
    ORDER BY criado_em DESC.
    """
    raise NotImplementedError


def get_troca(engine: Any, troca_id: int) -> dict | None:
    """Busca troca pelo ID com candidaturas e datas joinadas."""
    raise NotImplementedError


def listar_substituicoes_abertas(
    engine: Any,
    tipo_perfil: str,
    local_id: int | None = None,
) -> list[dict]:
    """Lista substituições abertas (aguardando voluntário) para um tipo de perfil.

    Inclui data e turno joinados. Exclui substituições expiradas.
    """
    raise NotImplementedError


# ── Sobreaviso ────────────────────────────────────────────────────────────────

def listar_sobreaviso_por_data(engine: Any, data_id: int) -> list[dict]:
    """Lista adesões de sobreaviso de uma data, ORDER BY prioridade ASC."""
    raise NotImplementedError


def listar_sobreaviso_por_perfil(engine: Any, perfil_id: int) -> list[dict]:
    """Lista adesões de sobreaviso do perfil, com datas joinadas."""
    raise NotImplementedError


def get_sobreaviso_ativo(
    engine: Any,
    data: str,
    hora: str,
    local_id: int | None = None,
) -> list[dict]:
    """Lista veterinários em sobreaviso ativo para uma data/hora específica.

    Usado pelo endpoint de integração ChatPro (futuro).
    Retorna: [{"nome", "telefone", "prioridade", "email"}, ...] ORDER BY prioridade ASC.
    """
    raise NotImplementedError


# ── Dashboard / alertas ───────────────────────────────────────────────────────

def get_alertas_dashboard(engine: Any, dias: int = 7) -> dict:
    """Retorna dados de alerta para o dashboard do gestor.

    Returns dict com:
        - datas_sem_vagas: list[dict] — datas publicadas sem vagas preenchidas nos próximos N dias
        - sobreaviso_vazio: list[dict] — datas de sobreaviso sem participantes
        - cadastros_pendentes: int — perfis aguardando aprovação
    """
    raise NotImplementedError


# ── Relatórios ────────────────────────────────────────────────────────────────

def relatorio_escalas_por_periodo(
    engine: Any,
    data_inicio: str,
    data_fim: str,
    local_id: int | None = None,
) -> list[dict]:
    """Relatório de todas as escalas no período com status e preenchimento."""
    raise NotImplementedError


def relatorio_participacao_por_plantonista(
    engine: Any,
    data_inicio: str,
    data_fim: str,
    perfil_id: int | None = None,
) -> list[dict]:
    """Relatório de participação: plantonista → quantidade de turnos confirmados."""
    raise NotImplementedError


def relatorio_cancelamentos_trocas(
    engine: Any,
    data_inicio: str,
    data_fim: str,
) -> list[dict]:
    """Relatório de cancelamentos e trocas no período."""
    raise NotImplementedError


def relatorio_pre_fechamento(
    engine: Any,
    data_inicio: str,
    data_fim: str,
    local_id: int | None = None,
) -> list[dict]:
    """Relatório de pré-fechamento para o módulo financeiro.

    Retorna candidaturas confirmadas (tipo='presencial', excluindo sobreaviso)
    com valor_hora_snapshot, valor_base_calculado, horas_turno por plantonista.
    Sobreaviso aparece em seção separada apenas informativa.
    ORDER BY data, perfil.nome.
    """
    raise NotImplementedError


# ── Endpoint de integração (financeiro / ChatPro) ─────────────────────────────

def get_fechamento_api(
    engine: Any,
    data_inicio: str,
    data_fim: str,
    local_id: int | None = None,
) -> list[dict]:
    """Dados para o endpoint GET /plantao/api/fechamento.

    Retorna por plantonista/turno:
        email, nome, data, hora_inicio, hora_fim, tipo_perfil, subtipo,
        horas_turno, valor_hora_snapshot, valor_base_calculado.

    Exclui sobreaviso (valor_base_calculado NULL para sobreaviso).
    """
    raise NotImplementedError
