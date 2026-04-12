"""
Módulo Plantão — ações de escrita (mutations).

CONVENÇÃO:
- Todas as funções aqui fazem escritas no banco (INSERT/UPDATE).
- Recebem `engine` como primeiro argumento.
- Sempre chamam audit() ao final de uma ação bem-sucedida.
- Sempre chamam notificar() para os perfis afetados.
- Lançam ValueError com mensagem amigável para regras de negócio violadas.
- Usam transactions (engine.begin()) para garantir atomicidade.

TODO (Codex): implementar todas as funções abaixo.
Cada função tem docstring completa descrevendo pré-condições, efeitos
colaterais esperados e o que deve ser auditado/notificado.
"""
from __future__ import annotations

from typing import Any


# ── Perfis ────────────────────────────────────────────────────────────────────

def cadastrar_plantonista(
    engine: Any,
    nome: str,
    email: str,
    senha: str,
    tipo: str,
    crmv: str | None = None,
    especialidade: str = "",
    telefone: str = "",
) -> int:
    """Cria um novo perfil de plantonista com status='pendente'.

    Pré-condições:
    - email não pode já existir em plantao_perfis (case-insensitive)
    - tipo deve ser 'veterinario' ou 'auxiliar'
    - se tipo='veterinario', crmv é obrigatório

    Efeitos:
    - INSERT em plantao_perfis
    - audit('perfil.cadastrado', perfil_id=novo_id)

    Returns: ID do perfil criado.
    Raises: ValueError se email duplicado, tipo inválido ou crmv ausente para vet.
    """
    raise NotImplementedError


def aprovar_plantonista(
    engine: Any,
    perfil_id: int,
    gestor_id: int,
    ip: str = "",
) -> None:
    """Aprova um plantonista (status: pendente → ativo).

    Pré-condições:
    - perfil deve existir e ter status='pendente'

    Efeitos:
    - UPDATE plantao_perfis SET status='ativo', aprovado_em=now(), aprovado_por=gestor_id
    - notificar(perfil_id, 'cadastro_aprovado', 'Seu cadastro foi aprovado! Você já pode fazer login.')
    - audit('perfil.aprovado', gestor_id=gestor_id, perfil_id=perfil_id)
    """
    raise NotImplementedError


def rejeitar_plantonista(
    engine: Any,
    perfil_id: int,
    gestor_id: int,
    motivo: str = "",
    ip: str = "",
) -> None:
    """Rejeita um plantonista (status: pendente → rejeitado).

    Efeitos:
    - UPDATE plantao_perfis SET status='rejeitado', motivo_rejeicao=motivo
    - notificar(perfil_id, 'cadastro_rejeitado', ...)
    - audit('perfil.rejeitado', gestor_id=gestor_id, perfil_id=perfil_id)
    """
    raise NotImplementedError


def desativar_plantonista(
    engine: Any,
    perfil_id: int,
    gestor_id: int,
    ip: str = "",
) -> None:
    """Desativa um plantonista ativo.

    Efeitos:
    - UPDATE status='inativo'
    - revogar_todas_sessoes(engine, perfil_id) — invalida sessões imediatamente
    - audit('perfil.desativado', ...)
    """
    raise NotImplementedError


def atualizar_perfil(
    engine: Any,
    perfil_id: int,
    dados: dict,
    ip: str = "",
) -> None:
    """Atualiza campos do próprio perfil (nome, telefone, especialidade).

    Campos atualizáveis pelo plantonista: nome, telefone, especialidade.
    CRMV e email: imutáveis após cadastro (gestor pode alterar via admin).
    Senha: via alterar_senha().

    audit('perfil.atualizado', perfil_id=perfil_id)
    """
    raise NotImplementedError


def alterar_senha(
    engine: Any,
    perfil_id: int,
    senha_atual: str,
    senha_nova: str,
    ip: str = "",
) -> None:
    """Altera senha do plantonista (exige senha atual correta).

    Raises: ValueError se senha_atual incorreta ou senha_nova fraca (<8 chars).
    audit('perfil.senha_alterada', perfil_id=perfil_id)
    """
    raise NotImplementedError


def iniciar_reset_senha(engine: Any, email: str) -> str | None:
    """Gera token de reset de senha para o e-mail informado.

    IMPORTANTE: se o e-mail não existe, retorna None silenciosamente
    (não revelar se e-mail está cadastrado).

    Efeitos:
    - UPDATE plantao_perfis SET reset_token=hash(token), reset_token_expira=now()+1h
    - Retorna o token RAW (para incluir no link do e-mail — implementação do envio é externa)
    - audit('perfil.reset_senha_solicitado', perfil_id=perfil_id)
    """
    raise NotImplementedError


def confirmar_reset_senha(engine: Any, token_raw: str, nova_senha: str) -> bool:
    """Aplica nova senha via token de reset.

    Returns True se sucesso, False se token inválido/expirado.
    audit('perfil.senha_redefinida', perfil_id=perfil_id) se sucesso.
    """
    raise NotImplementedError


# ── Locais ────────────────────────────────────────────────────────────────────

def criar_local(
    engine: Any,
    nome: str,
    endereco: str,
    cidade: str,
    uf: str,
    telefone: str,
    gestor_id: int,
) -> int:
    """Cria um novo local de plantão. Retorna o ID criado."""
    raise NotImplementedError


def atualizar_local(engine: Any, local_id: int, dados: dict, gestor_id: int) -> None:
    """Atualiza um local existente."""
    raise NotImplementedError


def desativar_local(engine: Any, local_id: int, gestor_id: int) -> None:
    """Desativa um local (ativo=0). Não deleta."""
    raise NotImplementedError


# ── Tarifas ───────────────────────────────────────────────────────────────────

def criar_tarifa(
    engine: Any,
    tipo_perfil: str,
    valor_hora: float,
    gestor_id: int,
    dia_semana: int | None = None,
    subtipo_turno: str | None = None,
    vigente_de: str = "2000-01-01",
    vigente_ate: str | None = None,
) -> int:
    """Cria uma tarifa de remuneração. Retorna o ID criado.

    Validações:
    - tipo_perfil: 'veterinario' | 'auxiliar'
    - dia_semana: 0-7 ou None
    - valor_hora: > 0
    audit('tarifa.criada', gestor_id=gestor_id, entidade_id=novo_id)
    """
    raise NotImplementedError


# ── Feriados ──────────────────────────────────────────────────────────────────

def criar_feriado(
    engine: Any,
    data: str,
    nome: str,
    tipo: str,
    local_id: int | None,
    gestor_id: int,
) -> int:
    """Cadastra um feriado. tipo: 'nacional'|'estadual'|'municipal'."""
    raise NotImplementedError


# ── Datas de plantão ──────────────────────────────────────────────────────────

def criar_data_plantao(
    engine: Any,
    local_id: int,
    tipo: str,
    subtipo: str,
    data: str,
    hora_inicio: str,
    hora_fim: str,
    posicoes: list[dict],
    gestor_id: int,
    observacoes: str = "",
    ip: str = "",
) -> int:
    """Cria uma data de plantão com suas posições (vagas).

    posicoes: [{"tipo": "veterinario", "vagas": 1}, {"tipo": "auxiliar", "vagas": 1}]

    Efeitos:
    - INSERT em plantao_datas (status='rascunho')
    - INSERT em plantao_posicoes para cada item em posicoes
    - audit('data.criada', gestor_id=gestor_id, entidade_id=data_id)

    Returns: ID da data criada.
    """
    raise NotImplementedError


def publicar_data_plantao(
    engine: Any,
    data_id: int,
    gestor_id: int,
    ip: str = "",
) -> None:
    """Publica uma data de plantão (status: rascunho → publicado).

    Pré-condição: data deve existir e estar em 'rascunho'.
    audit('data.publicada', gestor_id=gestor_id, entidade_id=data_id)
    """
    raise NotImplementedError


def cancelar_data_plantao(
    engine: Any,
    data_id: int,
    gestor_id: int,
    ip: str = "",
) -> None:
    """Cancela uma data de plantão e notifica todos os confirmados.

    Efeitos:
    - UPDATE plantao_datas SET status='cancelado'
    - UPDATE candidaturas para status='cancelado'
    - notificar() para cada plantonista confirmado
    - audit('data.cancelada', ...)
    """
    raise NotImplementedError


def gerar_escala_mensal(
    engine: Any,
    local_id: int,
    ano: int,
    mes: int,
    gestor_id: int,
    hora_inicio: str = "08:00",
    hora_fim: str = "20:00",
    hora_inicio_sobreaviso: str = "20:00",
    hora_fim_sobreaviso: str = "08:00",
) -> list[int]:
    """Gera automaticamente a escala do mês: fins de semana + feriados.

    Para cada FDS e feriado do mês:
    - Cria plantao_datas tipo='presencial' se não existir
    - Cria plantao_datas tipo='sobreaviso' para a madrugada seguinte

    Usa inferir_subtipo() de business.py para determinar o subtipo.
    Ignora datas que já têm plantão publicado/rascunho no mesmo local.

    Returns: lista de IDs criados.
    audit('escala.gerada_automaticamente', gestor_id=gestor_id, detalhes=json)
    """
    raise NotImplementedError


# ── Candidaturas ──────────────────────────────────────────────────────────────

def candidatar(
    engine: Any,
    posicao_id: int,
    perfil_id: int,
    ip: str = "",
) -> int:
    """Cria uma candidatura (status='provisorio').

    Pré-condições:
    - posicao deve existir e estar em data publicada
    - data do turno deve ser futura
    - perfil deve ser ativo e do tipo correto para a posição
    - não pode haver candidatura ativa do mesmo perfil na mesma data
    - vagas disponíveis: COUNT(confirmados) < posicao.vagas

    Se vagas = 0: cria com status='lista_espera' com ordem_espera calculada.

    audit('candidatura.criada', perfil_id=perfil_id, entidade_id=candidatura_id)
    Returns: ID da candidatura.
    """
    raise NotImplementedError


def confirmar_candidatura(
    engine: Any,
    candidatura_id: int,
    gestor_id: int,
    ip: str = "",
) -> None:
    """Confirma uma candidatura (provisorio → confirmado).

    Efeitos:
    - Calcula valor_hora_snapshot e valor_base_calculado via business.calcular_valor_base()
    - UPDATE candidatura: status='confirmado', confirmado_em=now(), confirmado_por=gestor_id,
      valor_hora_snapshot=X, valor_base_calculado=Y, horas_turno=Z
    - notificar(perfil_id, 'candidatura_confirmada', ...)
    - audit('candidatura.confirmada', gestor_id=gestor_id, entidade_id=candidatura_id)
    """
    raise NotImplementedError


def recusar_candidatura(
    engine: Any,
    candidatura_id: int,
    gestor_id: int,
    motivo: str = "",
    ip: str = "",
) -> None:
    """Recusa uma candidatura (provisorio → recusado).

    Efeitos:
    - UPDATE status='recusado', motivo_recusa=motivo
    - notificar(perfil_id, 'candidatura_recusada', ...)
    - audit('candidatura.recusada', gestor_id=gestor_id, entidade_id=candidatura_id)
    """
    raise NotImplementedError


def cancelar_candidatura(
    engine: Any,
    candidatura_id: int,
    perfil_id: int,
    prazo_horas_uteis: int,
    ip: str = "",
) -> None:
    """Cancela candidatura pelo próprio plantonista.

    Pré-condições: pode_cancelar() de business.py deve retornar True.
    Verifica prazo e seta cancelado_dentro_prazo=1 se OK (sempre OK se chegou aqui).
    Se havia lista_espera: promove próximo automaticamente via _promover_lista_espera().

    audit('candidatura.cancelada', perfil_id=perfil_id, entidade_id=candidatura_id)
    """
    raise NotImplementedError


def _promover_lista_espera(engine: Any, posicao_id: int) -> None:
    """Interna: promove o próximo da lista de espera para 'provisorio' após cancelamento.

    Chamada automaticamente por cancelar_candidatura() e executar_troca().
    """
    raise NotImplementedError


# ── Trocas e substituições ────────────────────────────────────────────────────

def solicitar_troca_direta(
    engine: Any,
    candidatura_a_id: int,
    candidatura_b_id: int,
    perfil_id: int,
    mensagem: str = "",
    ip: str = "",
) -> int:
    """Solicita troca direta entre dois plantonistas.

    perfil_id deve ser o dono de candidatura_a.
    candidatura_b deve pertencer a um plantonista diferente.
    Ambas devem ser 'confirmado'.
    Ambas as datas devem ser futuras e dentro do prazo.

    expira_em = now() + 48h.
    notificar(perfil_b, 'troca_solicitada', ..., link=/plantao/trocas/ID)
    audit('troca.solicitada', perfil_id=perfil_id, entidade_id=troca_id)
    Returns: ID da troca.
    """
    raise NotImplementedError


def abrir_substituicao(
    engine: Any,
    candidatura_a_id: int,
    perfil_id: int,
    mensagem: str = "",
    ip: str = "",
) -> int:
    """Disponibiliza turno para substituição aberta.

    candidatura_b_id = NULL (qualquer elegível pode aceitar).
    expira_em = now() + 72h.
    notificar todos os plantonistas ativos do mesmo tipo.
    audit('substituicao.aberta', ...)
    Returns: ID da troca.
    """
    raise NotImplementedError


def aceitar_troca(
    engine: Any,
    troca_id: int,
    perfil_id: int,
    ip: str = "",
) -> None:
    """Aceita uma troca e executa a movimentação.

    Para troca_direta: troca candidaturas entre A e B.
    Para substituicao: perfil_id entra no lugar de A.

    Operação atômica (transaction):
    1. Valida que troca está 'solicitado' e não expirada
    2. Valida que ambas as datas ainda são futuras e dentro do prazo
    3. Executa a troca nos registros de candidatura
    4. UPDATE trocas SET status='aceito', respondido_em=now()
    5. notificar() para ambas as partes
    6. audit('troca.executada', ...)
    """
    raise NotImplementedError


def recusar_troca(
    engine: Any,
    troca_id: int,
    perfil_id: int,
    ip: str = "",
) -> None:
    """Recusa uma troca (solicitado → recusado).

    notificar(solicitante, 'troca_recusada', ...)
    audit('troca.recusada', ...)
    """
    raise NotImplementedError


# ── Sobreaviso ────────────────────────────────────────────────────────────────

def aderir_sobreaviso(
    engine: Any,
    data_id: int,
    perfil_id: int,
    ip: str = "",
) -> int:
    """Plantonista adere ao sobreaviso de uma data.

    Pré-condições:
    - data deve ser tipo='sobreaviso' e status='publicado'
    - perfil deve ser 'veterinario' e ativo
    - não pode já ter adesão ativa na mesma data

    prioridade = MAX(prioridade) + 1 para o data_id.

    audit('sobreaviso.adesao', perfil_id=perfil_id, entidade_id=adesao_id)
    Returns: ID da adesão.
    """
    raise NotImplementedError


def cancelar_sobreaviso(
    engine: Any,
    adesao_id: int,
    perfil_id: int,
    ip: str = "",
) -> None:
    """Cancela adesão de sobreaviso.

    Se era prioridade=1: próximo da lista assume como principal.
    Reordena prioridades para manter sequência sem gaps.
    audit('sobreaviso.cancelado', ...)
    """
    raise NotImplementedError


def reordenar_sobreaviso(
    engine: Any,
    data_id: int,
    nova_ordem: list[int],
    gestor_id: int,
    ip: str = "",
) -> None:
    """Reordena a lista de sobreaviso manualmente (gestor).

    nova_ordem: lista de adesao_id na nova ordem (primeiro = prioridade 1).
    audit('sobreaviso.reordenado', gestor_id=gestor_id, entidade_id=data_id)
    """
    raise NotImplementedError


# ── Configurações ─────────────────────────────────────────────────────────────

def salvar_configuracao(
    engine: Any,
    chave: str,
    valor: str,
    gestor_id: int,
) -> None:
    """Salva ou atualiza uma configuração em app_kv com prefixo 'plantao_'.

    Chaves válidas:
    - plantao_prazo_cancelamento_horas_uteis
    - plantao_max_candidaturas_provisorias_por_vaga
    - plantao_notif_sobreaviso_dias_antecedencia
    - plantao_permitir_troca_sem_aprovacao_gestor
    """
    raise NotImplementedError


def get_configuracao(engine: Any, chave: str, default: str = "") -> str:
    """Lê uma configuração de app_kv. Retorna default se não encontrada."""
    raise NotImplementedError
