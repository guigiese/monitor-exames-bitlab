"""
Módulo Plantão — router FastAPI.

Estrutura de rotas:
  /plantao/          → landing redirect
  /plantao/login     → auth de plantonista
  /plantao/cadastro  → registro público
  /plantao/logout
  /plantao/senha/*   → reset de senha
  /plantao/escalas   → plantonista: ver datas com vagas
  /plantao/meus-turnos → plantonista: minhas candidaturas
  /plantao/notificacoes → plantonista: notificações
  /plantao/trocas    → plantonista: trocas/substituições
  /plantao/sobreaviso → plantonista: adesão ao sobreaviso
  /plantao/perfil    → plantonista: editar próprio perfil
  /plantao/admin/*   → gestor: painéis de gestão
  /plantao/api/*     → API JSON (integração financeira)

Os endpoints de auth estão completamente implementados neste arquivo.
Os demais endpoints têm stub com TODO para o Codex completar.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .auth import (
    COOKIE_NAME,
    autenticar_plantonista,
    criar_sessao,
    delete_session_cookie,
    gerar_csrf_token,
    get_perfil_atual,
    require_gestor_plantao,
    require_plantonista,
    revogar_sessao,
    set_session_cookie,
    validar_csrf,
)
from .notifications import (
    contar_nao_lidas,
    listar_notificacoes,
    marcar_lida,
    marcar_todas_lidas,
)

log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
_templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Engine é injetado em make_router()
_engine: Any = None


def make_router(engine: Any) -> APIRouter:
    """Cria e retorna o APIRouter do módulo Plantão com engine injetado."""
    global _engine
    _engine = engine

    router = APIRouter(prefix="/plantao")

    # ── Auth ──────────────────────────────────────────────────────────────────

    @router.get("", response_class=HTMLResponse)
    @router.get("/", response_class=HTMLResponse)
    async def landing(request: Request):
        perfil = get_perfil_atual(request, engine)
        if perfil and perfil["status"] == "ativo":
            return RedirectResponse("/plantao/escalas", status_code=303)
        return RedirectResponse("/plantao/login", status_code=303)

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, erro: str = ""):
        perfil = get_perfil_atual(request, engine)
        if perfil and perfil["status"] == "ativo":
            return RedirectResponse("/plantao/escalas", status_code=303)
        return _render(request, "plantao_login.html", erro=erro)

    @router.post("/login")
    async def login_action(
        request: Request,
        email: str = Form(...),
        senha: str = Form(...),
    ):
        try:
            perfil = autenticar_plantonista(engine, email.strip().lower(), senha)
        except RuntimeError as exc:
            return _render(request, "plantao_login.html", erro=str(exc))

        if not perfil:
            return _render(request, "plantao_login.html", erro="E-mail ou senha inválidos.")

        if perfil["status"] == "pendente":
            return RedirectResponse("/plantao/cadastro/aguardando", status_code=303)

        if perfil["status"] in ("inativo", "rejeitado"):
            return _render(
                request, "plantao_login.html",
                erro="Conta inativa ou rejeitada. Entre em contato com a clínica."
            )

        ip = request.client.host if request.client else ""
        ua = request.headers.get("user-agent", "")
        raw_token = criar_sessao(engine, perfil["id"], ip=ip, user_agent=ua)

        response = RedirectResponse("/plantao/escalas", status_code=303)
        set_session_cookie(response, raw_token)
        return response

    @router.get("/logout")
    async def logout(request: Request):
        raw_token = request.cookies.get(COOKIE_NAME)
        if raw_token:
            revogar_sessao(engine, raw_token)
        response = RedirectResponse("/plantao/login", status_code=303)
        delete_session_cookie(response)
        return response

    @router.get("/cadastro", response_class=HTMLResponse)
    async def cadastro_page(request: Request, erro: str = ""):
        return _render(request, "plantao_cadastro.html", erro=erro)

    @router.post("/cadastro")
    async def cadastro_action(
        request: Request,
        nome: str = Form(...),
        email: str = Form(...),
        senha: str = Form(...),
        senha_confirma: str = Form(...),
        tipo: str = Form(...),
        crmv: str = Form(""),
        especialidade: str = Form(""),
        telefone: str = Form(""),
    ):
        from .actions import cadastrar_plantonista
        email = email.strip().lower()

        if senha != senha_confirma:
            return _render(request, "plantao_cadastro.html", erro="As senhas não coincidem.")
        if len(senha) < 8:
            return _render(request, "plantao_cadastro.html", erro="A senha deve ter no mínimo 8 caracteres.")
        if tipo not in ("veterinario", "auxiliar"):
            return _render(request, "plantao_cadastro.html", erro="Tipo inválido.")
        if tipo == "veterinario" and not crmv.strip():
            return _render(request, "plantao_cadastro.html", erro="CRMV é obrigatório para veterinários.")

        try:
            cadastrar_plantonista(
                engine,
                nome=nome.strip(),
                email=email,
                senha=senha,
                tipo=tipo,
                crmv=crmv.strip() or None,
                especialidade=especialidade.strip(),
                telefone=telefone.strip(),
            )
        except ValueError as exc:
            return _render(request, "plantao_cadastro.html", erro=str(exc))

        return RedirectResponse("/plantao/cadastro/aguardando", status_code=303)

    @router.get("/cadastro/aguardando", response_class=HTMLResponse)
    async def cadastro_aguardando(request: Request):
        return _render(request, "plantao_cadastro_aguardando.html")

    @router.get("/senha/recuperar", response_class=HTMLResponse)
    async def recuperar_senha_page(request: Request, enviado: str = ""):
        return _render(request, "plantao_recuperar_senha.html", enviado=enviado)

    @router.post("/senha/recuperar")
    async def recuperar_senha_action(request: Request, email: str = Form(...)):
        from .actions import iniciar_reset_senha
        # Silencioso: não revela se e-mail existe ou não
        iniciar_reset_senha(engine, email.strip().lower())
        return RedirectResponse("/plantao/senha/recuperar?enviado=1", status_code=303)

    @router.get("/senha/redefinir", response_class=HTMLResponse)
    async def redefinir_senha_page(request: Request, token: str = "", erro: str = ""):
        if not token:
            return RedirectResponse("/plantao/senha/recuperar", status_code=303)
        return _render(request, "plantao_redefinir_senha.html", token=token, erro=erro)

    @router.post("/senha/redefinir")
    async def redefinir_senha_action(
        request: Request,
        token: str = Form(...),
        nova_senha: str = Form(...),
        nova_senha_confirma: str = Form(...),
    ):
        from .actions import confirmar_reset_senha
        if nova_senha != nova_senha_confirma:
            return _render(
                request, "plantao_redefinir_senha.html",
                token=token, erro="As senhas não coincidem."
            )
        if len(nova_senha) < 8:
            return _render(
                request, "plantao_redefinir_senha.html",
                token=token, erro="A senha deve ter no mínimo 8 caracteres."
            )
        ok = confirmar_reset_senha(engine, token, nova_senha)
        if not ok:
            return _render(
                request, "plantao_redefinir_senha.html",
                token=token, erro="Link inválido ou expirado. Solicite um novo link."
            )
        return RedirectResponse("/plantao/login?erro=senha_redefinida", status_code=303)

    # ── Plantonista: escalas ───────────────────────────────────────────────────

    @router.get("/escalas", response_class=HTMLResponse)
    async def escalas_page(request: Request, mes: int = 0, ano: int = 0, local_id: int = 0):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        # TODO (Codex): usar queries.listar_datas_com_vagas_abertas() e
        # queries.listar_datas_por_mes() para montar o calendário mensal.
        # Renderizar plantao_escalas.html com calendário CSS Grid.
        raise NotImplementedError

    @router.post("/escalas/{posicao_id}/candidatar")
    async def candidatar_action(request: Request, posicao_id: int):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): chamar actions.candidatar(engine, posicao_id, perfil["id"])
        raise NotImplementedError

    # ── Plantonista: meus turnos ───────────────────────────────────────────────

    @router.get("/meus-turnos", response_class=HTMLResponse)
    async def meus_turnos_page(request: Request):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        # TODO (Codex): queries.listar_candidaturas_por_perfil(engine, perfil["id"])
        raise NotImplementedError

    @router.post("/candidaturas/{candidatura_id}/cancelar")
    async def cancelar_candidatura_action(request: Request, candidatura_id: int):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): buscar prazo configurado e chamar actions.cancelar_candidatura()
        raise NotImplementedError

    # ── Plantonista: trocas ────────────────────────────────────────────────────

    @router.get("/trocas", response_class=HTMLResponse)
    async def trocas_page(request: Request):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        # TODO (Codex): queries.listar_trocas_por_perfil() + queries.listar_substituicoes_abertas()
        raise NotImplementedError

    @router.post("/trocas/solicitar")
    async def solicitar_troca_action(
        request: Request,
        candidatura_a_id: int = Form(...),
        candidatura_b_id: int = Form(...),
        mensagem: str = Form(""),
    ):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): actions.solicitar_troca_direta()
        raise NotImplementedError

    @router.post("/trocas/substituicao")
    async def abrir_substituicao_action(
        request: Request,
        candidatura_a_id: int = Form(...),
        mensagem: str = Form(""),
    ):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): actions.abrir_substituicao()
        raise NotImplementedError

    @router.post("/trocas/{troca_id}/aceitar")
    async def aceitar_troca_action(request: Request, troca_id: int):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): actions.aceitar_troca()
        raise NotImplementedError

    @router.post("/trocas/{troca_id}/recusar")
    async def recusar_troca_action(request: Request, troca_id: int):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): actions.recusar_troca()
        raise NotImplementedError

    # ── Plantonista: sobreaviso ────────────────────────────────────────────────

    @router.get("/sobreaviso", response_class=HTMLResponse)
    async def sobreaviso_page(request: Request):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        # TODO (Codex): queries.listar_sobreaviso_por_perfil() + datas abertas
        raise NotImplementedError

    @router.post("/sobreaviso/{data_id}/aderir")
    async def aderir_sobreaviso_action(request: Request, data_id: int):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): actions.aderir_sobreaviso()
        raise NotImplementedError

    @router.post("/sobreaviso/{adesao_id}/cancelar")
    async def cancelar_sobreaviso_action(request: Request, adesao_id: int):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        # TODO (Codex): actions.cancelar_sobreaviso()
        raise NotImplementedError

    # ── Plantonista: notificações ─────────────────────────────────────────────

    @router.get("/notificacoes", response_class=HTMLResponse)
    async def notificacoes_page(request: Request):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        notifs = listar_notificacoes(engine, perfil["id"])
        csrf = gerar_csrf_token(perfil["_session_id"])
        return _render(request, "plantao_notificacoes.html", notificacoes=notifs, csrf_token=csrf)

    @router.post("/notificacoes/{notif_id}/lida", response_class=HTMLResponse)
    async def marcar_notificacao_lida(request: Request, notif_id: int):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        marcar_lida(engine, notif_id, perfil["id"])
        return HTMLResponse("", status_code=200)

    @router.post("/notificacoes/todas-lidas")
    async def marcar_todas_lidas_action(request: Request):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        marcar_todas_lidas(engine, perfil["id"])
        return RedirectResponse("/plantao/notificacoes", status_code=303)

    @router.get("/partials/badge-notificacoes", response_class=HTMLResponse)
    async def badge_notificacoes(request: Request):
        perfil = get_perfil_atual(request, engine)
        if not perfil:
            return HTMLResponse("")
        n = contar_nao_lidas(engine, perfil["id"])
        if n == 0:
            return HTMLResponse("")
        return HTMLResponse(
            f'<span class="inline-flex items-center justify-center px-1.5 py-0.5 text-xs'
            f' font-bold leading-none text-white bg-red-600 rounded-full">{n}</span>'
        )

    # ── Plantonista: perfil ────────────────────────────────────────────────────

    @router.get("/perfil", response_class=HTMLResponse)
    async def perfil_page(request: Request, salvo: str = ""):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        csrf = gerar_csrf_token(perfil["_session_id"])
        return _render(request, "plantao_perfil.html", perfil=perfil, csrf_token=csrf, salvo=salvo)

    @router.post("/perfil/atualizar")
    async def atualizar_perfil_action(
        request: Request,
        nome: str = Form(...),
        telefone: str = Form(""),
        especialidade: str = Form(""),
    ):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        from .actions import atualizar_perfil
        atualizar_perfil(
            engine, perfil["id"],
            {"nome": nome.strip(), "telefone": telefone.strip(), "especialidade": especialidade.strip()},
            ip=request.client.host if request.client else "",
        )
        return RedirectResponse("/plantao/perfil?salvo=1", status_code=303)

    @router.post("/perfil/senha")
    async def alterar_senha_action(
        request: Request,
        senha_atual: str = Form(...),
        nova_senha: str = Form(...),
        nova_senha_confirma: str = Form(...),
    ):
        perfil = _exige_plantonista(request)
        if isinstance(perfil, RedirectResponse):
            return perfil
        _validar_csrf_ou_403(request, perfil)
        csrf = gerar_csrf_token(perfil["_session_id"])
        if nova_senha != nova_senha_confirma:
            return _render(
                request, "plantao_perfil.html",
                perfil=perfil, csrf_token=csrf, erro_senha="As senhas não coincidem."
            )
        from .actions import alterar_senha
        try:
            alterar_senha(engine, perfil["id"], senha_atual, nova_senha)
        except ValueError as exc:
            return _render(
                request, "plantao_perfil.html",
                perfil=perfil, csrf_token=csrf, erro_senha=str(exc)
            )
        return RedirectResponse("/plantao/perfil?salvo=1", status_code=303)

    # ── Admin: dashboard ───────────────────────────────────────────────────────

    @router.get("/admin", response_class=HTMLResponse)
    @router.get("/admin/", response_class=HTMLResponse)
    async def admin_dashboard(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.get_alertas_dashboard() para montar dashboard do gestor
        raise NotImplementedError

    @router.get("/admin/cadastros", response_class=HTMLResponse)
    async def admin_cadastros(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.listar_perfis(status='pendente') + listar todos
        raise NotImplementedError

    @router.post("/admin/cadastros/{perfil_id}/aprovar")
    async def admin_aprovar_cadastro(request: Request, perfil_id: int):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.aprovar_plantonista(engine, perfil_id, gestor["id"])
        raise NotImplementedError

    @router.post("/admin/cadastros/{perfil_id}/rejeitar")
    async def admin_rejeitar_cadastro(request: Request, perfil_id: int, motivo: str = Form("")):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.rejeitar_plantonista()
        raise NotImplementedError

    @router.post("/admin/cadastros/{perfil_id}/desativar")
    async def admin_desativar(request: Request, perfil_id: int):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.desativar_plantonista()
        raise NotImplementedError

    @router.get("/admin/escalas", response_class=HTMLResponse)
    async def admin_escalas(request: Request, mes: int = 0, ano: int = 0, local_id: int = 0):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.listar_datas_por_mes() com detalhes de preenchimento
        raise NotImplementedError

    @router.post("/admin/escalas/criar")
    async def admin_criar_data(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): parsear form e chamar actions.criar_data_plantao()
        raise NotImplementedError

    @router.post("/admin/escalas/{data_id}/publicar")
    async def admin_publicar_data(request: Request, data_id: int):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.publicar_data_plantao()
        raise NotImplementedError

    @router.post("/admin/escalas/{data_id}/cancelar")
    async def admin_cancelar_data(request: Request, data_id: int):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.cancelar_data_plantao()
        raise NotImplementedError

    @router.post("/admin/escalas/gerar-mensal")
    async def admin_gerar_mensal(
        request: Request,
        local_id: int = Form(...),
        ano: int = Form(...),
        mes: int = Form(...),
    ):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.gerar_escala_mensal()
        raise NotImplementedError

    @router.get("/admin/candidaturas", response_class=HTMLResponse)
    async def admin_candidaturas(request: Request, data_id: int = 0):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.listar_candidaturas_por_data()
        raise NotImplementedError

    @router.post("/admin/candidaturas/{candidatura_id}/confirmar")
    async def admin_confirmar_candidatura(request: Request, candidatura_id: int):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.confirmar_candidatura()
        raise NotImplementedError

    @router.post("/admin/candidaturas/{candidatura_id}/recusar")
    async def admin_recusar_candidatura(
        request: Request, candidatura_id: int, motivo: str = Form("")
    ):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.recusar_candidatura()
        raise NotImplementedError

    @router.get("/admin/sobreaviso", response_class=HTMLResponse)
    async def admin_sobreaviso(request: Request, data_id: int = 0):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.listar_sobreaviso_por_data()
        raise NotImplementedError

    @router.post("/admin/sobreaviso/{data_id}/reordenar")
    async def admin_reordenar_sobreaviso(request: Request, data_id: int):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): parsear nova ordem e chamar actions.reordenar_sobreaviso()
        raise NotImplementedError

    @router.get("/admin/relatorios", response_class=HTMLResponse)
    async def admin_relatorios(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): listar links para os 4 relatórios
        raise NotImplementedError

    @router.get("/admin/relatorios/escalas", response_class=HTMLResponse)
    async def relatorio_escalas(request: Request, data_inicio: str = "", data_fim: str = "", local_id: int = 0):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.relatorio_escalas_por_periodo()
        raise NotImplementedError

    @router.get("/admin/relatorios/participacao", response_class=HTMLResponse)
    async def relatorio_participacao(request: Request, data_inicio: str = "", data_fim: str = ""):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.relatorio_participacao_por_plantonista()
        raise NotImplementedError

    @router.get("/admin/relatorios/cancelamentos", response_class=HTMLResponse)
    async def relatorio_cancelamentos(request: Request, data_inicio: str = "", data_fim: str = ""):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.relatorio_cancelamentos_trocas()
        raise NotImplementedError

    @router.get("/admin/relatorios/pre-fechamento", response_class=HTMLResponse)
    async def relatorio_pre_fechamento(request: Request, data_inicio: str = "", data_fim: str = "", local_id: int = 0):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.relatorio_pre_fechamento()
        raise NotImplementedError

    @router.get("/admin/locais", response_class=HTMLResponse)
    async def admin_locais(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.listar_locais()
        raise NotImplementedError

    @router.post("/admin/locais/criar")
    async def admin_criar_local(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.criar_local()
        raise NotImplementedError

    @router.get("/admin/tarifas", response_class=HTMLResponse)
    async def admin_tarifas(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.listar_tarifas_vigentes()
        raise NotImplementedError

    @router.post("/admin/tarifas/criar")
    async def admin_criar_tarifa(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.criar_tarifa()
        raise NotImplementedError

    @router.get("/admin/feriados", response_class=HTMLResponse)
    async def admin_feriados(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): queries.listar_feriados_por_periodo()
        raise NotImplementedError

    @router.post("/admin/feriados/criar")
    async def admin_criar_feriado(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.criar_feriado()
        raise NotImplementedError

    @router.get("/admin/configuracoes", response_class=HTMLResponse)
    async def admin_configuracoes(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): ler configurações de app_kv com prefixo plantao_
        raise NotImplementedError

    @router.post("/admin/configuracoes/salvar")
    async def admin_salvar_configuracoes(request: Request):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): actions.salvar_configuracao() para cada campo
        raise NotImplementedError

    @router.get("/admin/audit-log", response_class=HTMLResponse)
    async def admin_audit_log(
        request: Request,
        perfil_id: int = 0,
        entidade: str = "",
        data_inicio: str = "",
        data_fim: str = "",
        page: int = 1,
    ):
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return gestor
        # TODO (Codex): SELECT paginado de plantao_audit_log com filtros
        raise NotImplementedError

    # ── API JSON (integração) ─────────────────────────────────────────────────

    @router.get("/api/fechamento", response_class=JSONResponse)
    async def api_fechamento(
        request: Request,
        data_inicio: str,
        data_fim: str,
        local_id: int = 0,
    ):
        """Endpoint de integração para o módulo financeiro.

        Chave de identidade entre sistemas: plantonista.email
        Retorna dados de pré-fechamento sem autenticação de plantonista
        (requer auth da plataforma — gestor ou integração interna).
        """
        gestor = _exige_gestor(request)
        if isinstance(gestor, RedirectResponse) or isinstance(gestor, HTMLResponse):
            return JSONResponse({"erro": "Não autorizado."}, status_code=403)
        from .queries import get_fechamento_api
        dados = get_fechamento_api(engine, data_inicio, data_fim, local_id or None)
        return JSONResponse({"data_inicio": data_inicio, "data_fim": data_fim, "turnos": dados})

    @router.get("/api/sobreaviso-ativo", response_class=JSONResponse)
    async def api_sobreaviso_ativo(
        request: Request,
        data: str,
        hora: str,
        local_id: int = 0,
    ):
        """Lista de sobreaviso ativo para um momento específico (integração ChatPro).

        Endpoint público (sem auth) — expõe apenas nome, telefone, email, prioridade.
        A chave de API deve ser enviada no header X-Plantao-API-Key.
        TODO (Codex): implementar validação de X-Plantao-API-Key contra app_kv.
        """
        from .queries import get_sobreaviso_ativo
        lista = get_sobreaviso_ativo(engine, data, hora, local_id or None)
        return JSONResponse({"data": data, "hora": hora, "sobreaviso": lista})

    return router


# ── Helpers internos ──────────────────────────────────────────────────────────

def _render(request: Request, template: str, **ctx):
    return _templates.TemplateResponse(request, template, {"request": request, **ctx})


def _exige_plantonista(request: Request):
    """Retorna o perfil ou um RedirectResponse se não autenticado/ativo."""
    perfil = get_perfil_atual(request, _engine)
    if not perfil:
        return RedirectResponse("/plantao/login", status_code=303)
    if perfil["status"] == "pendente":
        return RedirectResponse("/plantao/cadastro/aguardando", status_code=303)
    if perfil["status"] in ("inativo", "rejeitado"):
        return RedirectResponse("/plantao/login?erro=conta_inativa", status_code=303)
    return perfil


def _exige_gestor(request: Request):
    """Retorna o user da plataforma ou uma resposta de erro."""
    from pb_platform.auth import attach_user_to_request
    from sqlalchemy import text
    user = attach_user_to_request(request)
    if not user:
        return RedirectResponse("/login?next=/plantao/admin", status_code=303)
    with _engine.connect() as conn:
        row = conn.execute(
            text("SELECT gestor_plantao FROM users WHERE id = :id"),
            {"id": user["id"]},
        ).mappings().first()
    if not row or not row["gestor_plantao"]:
        return HTMLResponse("<h1>403 — Acesso restrito a gestores de plantão.</h1>", status_code=403)
    return user


def _validar_csrf_ou_403(request: Request, perfil: dict) -> None:
    """Valida CSRF ou lança HTTPException 403."""
    from fastapi import HTTPException
    if not validar_csrf(request, perfil["_session_id"]):
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")
