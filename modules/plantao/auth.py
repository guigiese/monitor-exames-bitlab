"""
Módulo Plantão — autenticação e autorização isoladas.

Os plantonistas têm auth completamente separado da plataforma:
  - Sessão própria via cookie 'plantao_session'
  - Tabela plantao_sessoes (não usa a sessions da plataforma)
  - Scrypt para senhas, sha256 para tokens de sessão (igual à plataforma)

Os gestores usam a sessão da plataforma (cookie 'session_token') + campo
gestor_plantao=1 na tabela users.

CSRF: HMAC-SHA256 gerado por sessão, validado em todos os POST.
Rate limiting: contador de tentativas em plantao_perfis.tentativas_login.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text

log = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

COOKIE_NAME = "plantao_session"
SESSION_TTL_HOURS = 24 * 7  # 7 dias
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
CSRF_HEADER = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"

_CSRF_SECRET = os.environ.get("PLANTAO_CSRF_SECRET") or secrets.token_hex(32)


# ── Utilitários internos ──────────────────────────────────────────────────────

def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _utcnow_dt() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _parse_dt(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


# ── CSRF ──────────────────────────────────────────────────────────────────────

def gerar_csrf_token(session_id: str) -> str:
    """Gera token CSRF vinculado à sessão (HMAC-SHA256)."""
    return hmac.new(_CSRF_SECRET.encode(), session_id.encode(), hashlib.sha256).hexdigest()


def validar_csrf(request: Request, session_id: str) -> bool:
    """Valida token CSRF do header ou do form field."""
    esperado = gerar_csrf_token(session_id)
    recebido = (
        request.headers.get(CSRF_HEADER)
        or (request._form or {}).get(CSRF_FORM_FIELD, "")  # type: ignore[attr-defined]
        if hasattr(request, "_form")
        else request.headers.get(CSRF_HEADER, "")
    )
    if not recebido:
        return False
    return hmac.compare_digest(esperado, recebido)


# ── Sessão de plantonista ─────────────────────────────────────────────────────

def criar_sessao(engine: Any, perfil_id: int, ip: str = "", user_agent: str = "") -> str:
    """Cria uma sessão para o plantonista. Retorna o token raw (para o cookie)."""
    raw_token = secrets.token_hex(32)
    session_id = _token_hash(raw_token)
    agora = _utcnow()
    expira = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).strftime("%Y-%m-%dT%H:%M:%S")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO plantao_sessoes (id, perfil_id, criada_em, expira_em, ultimo_acesso, ip, user_agent)"
                " VALUES (:id, :perfil_id, :criada_em, :expira_em, :ultimo_acesso, :ip, :ua)"
            ),
            {
                "id": session_id,
                "perfil_id": perfil_id,
                "criada_em": agora,
                "expira_em": expira,
                "ultimo_acesso": agora,
                "ip": ip,
                "ua": user_agent,
            },
        )
    return raw_token


def obter_sessao(engine: Any, raw_token: str) -> dict | None:
    """Valida o token e devolve a sessão se válida e não expirada.

    Atualiza ultimo_acesso como efeito colateral.
    """
    session_id = _token_hash(raw_token)
    agora = _utcnow()
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM plantao_sessoes WHERE id = :id"),
            {"id": session_id},
        ).mappings().first()
        if not row:
            return None
        if row["expira_em"] < agora:
            conn.execute(text("DELETE FROM plantao_sessoes WHERE id = :id"), {"id": session_id})
            return None
        conn.execute(
            text("UPDATE plantao_sessoes SET ultimo_acesso = :ts WHERE id = :id"),
            {"ts": agora, "id": session_id},
        )
        return dict(row)


def revogar_sessao(engine: Any, raw_token: str) -> None:
    """Invalida a sessão (logout)."""
    session_id = _token_hash(raw_token)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM plantao_sessoes WHERE id = :id"), {"id": session_id})


def revogar_todas_sessoes(engine: Any, perfil_id: int) -> None:
    """Invalida todas as sessões do perfil (ex: conta desativada)."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM plantao_sessoes WHERE perfil_id = :pid"),
            {"pid": perfil_id},
        )


# ── Autenticação de plantonista ───────────────────────────────────────────────

def autenticar_plantonista(engine: Any, email: str, senha: str) -> dict | None:
    """Verifica credenciais e controla rate limiting.

    Returns:
        dict do perfil se autenticado, None caso contrário.
        Lança RuntimeError com mensagem se conta bloqueada.
    """
    from pb_platform.security import verify_password

    with engine.begin() as conn:
        perfil = conn.execute(
            text("SELECT * FROM plantao_perfis WHERE LOWER(email) = LOWER(:email)"),
            {"email": email},
        ).mappings().first()

        if not perfil:
            return None

        perfil = dict(perfil)

        # conta bloqueada?
        if perfil.get("bloqueado_ate"):
            bloqueado_ate = _parse_dt(perfil["bloqueado_ate"])
            if bloqueado_ate and bloqueado_ate > _utcnow_dt():
                restam = int((bloqueado_ate - _utcnow_dt()).total_seconds() / 60)
                raise RuntimeError(f"Conta bloqueada. Tente novamente em {restam} minuto(s).")
            else:
                # desbloqueio automático
                conn.execute(
                    text(
                        "UPDATE plantao_perfis SET tentativas_login=0, bloqueado_ate=NULL"
                        " WHERE id=:id"
                    ),
                    {"id": perfil["id"]},
                )
                perfil["tentativas_login"] = 0
                perfil["bloqueado_ate"] = None

        if not verify_password(senha, perfil["senha_hash"]):
            tentativas = perfil.get("tentativas_login", 0) + 1
            bloqueado_ate = None
            if tentativas >= MAX_LOGIN_ATTEMPTS:
                bloqueado_ate = (
                    datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
                ).strftime("%Y-%m-%dT%H:%M:%S")
            conn.execute(
                text(
                    "UPDATE plantao_perfis SET tentativas_login=:t, bloqueado_ate=:ba"
                    " WHERE id=:id"
                ),
                {"t": tentativas, "ba": bloqueado_ate, "id": perfil["id"]},
            )
            return None

        # senha correta — zera contador
        conn.execute(
            text(
                "UPDATE plantao_perfis SET tentativas_login=0, bloqueado_ate=NULL WHERE id=:id"
            ),
            {"id": perfil["id"]},
        )
        return perfil


# ── Guards de rota ─────────────────────────────────────────────────────────────

def get_perfil_atual(request: Request, engine: Any) -> dict | None:
    """Retorna o perfil do plantonista logado ou None."""
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        return None
    sessao = obter_sessao(engine, raw_token)
    if not sessao:
        return None
    with engine.connect() as conn:
        perfil = conn.execute(
            text("SELECT * FROM plantao_perfis WHERE id = :id"),
            {"id": sessao["perfil_id"]},
        ).mappings().first()
    if not perfil:
        return None
    return {**dict(perfil), "_session_id": sessao["id"], "_session_raw": raw_token}


def require_plantonista(engine: Any):
    """Decorator para rotas que exigem plantonista logado e ativo."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            perfil = get_perfil_atual(request, engine)
            if not perfil:
                return RedirectResponse("/plantao/login", status_code=303)
            if perfil["status"] == "pendente":
                return RedirectResponse("/plantao/cadastro/aguardando", status_code=303)
            if perfil["status"] in ("inativo", "rejeitado"):
                return RedirectResponse("/plantao/login?erro=conta_inativa", status_code=303)
            request.state.plantonista = perfil
            request.state.csrf_token = gerar_csrf_token(perfil["_session_id"])
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_gestor_plantao(engine: Any):
    """Decorator para rotas admin que exigem usuário da plataforma com gestor_plantao=1."""
    from pb_platform.auth import attach_user_to_request

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = attach_user_to_request(request)
            if not user:
                return RedirectResponse("/login?next=" + str(request.url.path), status_code=303)
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT gestor_plantao FROM users WHERE id = :id"),
                    {"id": user["id"]},
                ).mappings().first()
            if not row or not row["gestor_plantao"]:
                from fastapi.responses import HTMLResponse
                return HTMLResponse("<h1>403 — Acesso restrito a gestores de plantão.</h1>", status_code=403)
            request.state.gestor = user
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# ── Helpers de resposta ───────────────────────────────────────────────────────

def set_session_cookie(response: Any, raw_token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        raw_token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_HOURS * 3600,
    )


def delete_session_cookie(response: Any) -> None:
    response.delete_cookie(COOKIE_NAME)
