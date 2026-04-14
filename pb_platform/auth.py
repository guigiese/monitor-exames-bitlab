from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .settings import settings
from .storage import store

PUBLIC_PATH_PREFIXES = (
    "/login",
    "/logout",
    "/cadastro",
    "/telegram/webhook/",
    "/ops-map-static/",
    "/sandboxes/cards-static/",
)

# ── CSRF ──────────────────────────────────────────────────────────────────────

_CSRF_SECRET = settings.csrf_secret or os.environ.get("PB_CSRF_SECRET") or secrets.token_hex(32)
CSRF_HEADER = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"


def gerar_csrf_token(session_token: str) -> str:
    """Gera token CSRF vinculado à sessão via HMAC-SHA256."""
    return hmac.new(_CSRF_SECRET.encode(), session_token.encode(), hashlib.sha256).hexdigest()


async def validar_csrf(request: Request, session_token: str) -> bool:
    """Valida o token CSRF do header ou do form. Retorna True se válido."""
    esperado = gerar_csrf_token(session_token)
    # Tenta header primeiro (HTMX)
    recebido = request.headers.get(CSRF_HEADER, "")
    if not recebido:
        # Tenta form field
        try:
            form = await request.form()
            recebido = form.get(CSRF_FORM_FIELD, "") or ""
        except Exception:
            recebido = ""
    if not recebido:
        return False
    return hmac.compare_digest(esperado, str(recebido))


# ── Auth helpers ──────────────────────────────────────────────────────────────

def path_requires_auth(path: str) -> bool:
    if not settings.auth_enabled:
        return False
    if path == "/favicon.ico":
        return False
    return not any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)


def auth_bypassed(request: Request) -> bool:
    return bool(getattr(request.app.state, "disable_auth", False))


def attach_user_to_request(request: Request) -> dict | None:
    token = request.cookies.get(settings.session_cookie_name)
    user = store.get_user_for_session(token)
    request.state.user = user
    return user


def redirect_to_login(request: Request) -> RedirectResponse:
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=f"/login?next={quote(target)}", status_code=303)


def is_admin(request: Request) -> bool:
    user = getattr(request.state, "user", None)
    return bool(user and user.get("role") == "admin")


def user_permissions(user: dict | None) -> dict[str, bool]:
    return store.get_user_permissions(user)


def default_redirect_for_user(user: dict | None) -> str:
    permissions = user_permissions(user)
    if permissions.get("manage_plantao"):
        return "/plantao/admin/"
    if permissions.get("platform_access"):
        return "/"
    if permissions.get("plantao_access"):
        return "/plantao/"
    if permissions.get("labmonitor_access"):
        return "/labmonitor/"
    return "/login"


def has_permission(request: Request, permission: str) -> bool:
    user = getattr(request.state, "user", None)
    if not user:
        return False
    return bool(user_permissions(user).get(permission))


def required_permission(path: str, method: str) -> str | None:
    method = method.upper()
    # Módulo Plantão — granularidade por sub-rota
    if path.startswith("/plantao/admin/escalas"):
        return "plantao_gerir_escalas"
    if path.startswith("/plantao/admin/candidaturas") or path.startswith("/plantao/admin/disponibilidade") or path.startswith("/plantao/admin/aprovacoes"):
        return "plantao_aprovar_candidaturas"
    if path.startswith("/plantao/admin/cadastros"):
        return "plantao_aprovar_cadastros"
    if path.startswith("/plantao/admin/relatorios") or path.startswith("/plantao/admin/audit-log"):
        return "plantao_ver_relatorios"
    if path.startswith("/plantao/admin"):
        return "manage_plantao"
    if path.startswith("/plantao"):
        return "plantao_access"
    # Plataforma interna
    if path.startswith("/admin/usuarios") or path.startswith("/admin/permissoes") or path.startswith("/admin/perfis"):
        return "manage_users"
    if path.startswith("/ops-map") or path.startswith("/sandboxes"):
        return "ops_tools"
    if path.startswith("/labmonitor/sync"):
        return "manage_labmonitor"
    if path.startswith("/labmonitor/labs") or path.startswith("/labmonitor/canais"):
        return "manage_labmonitor" if method in {"GET", "POST"} else "labmonitor_access"
    if path.startswith("/labmonitor/notificacoes") or path.startswith("/labmonitor/tolerancias") or path.startswith("/labmonitor/settings"):
        return "manage_labmonitor"
    if path.startswith("/labmonitor"):
        return "labmonitor_access"
    if path == "/":
        return "platform_access"
    return None


def forbidden_response(request: Request):
    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(
            '<div class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">Você não tem permissão para acessar esta área.</div>',
            status_code=403,
        )
    return RedirectResponse(url=default_redirect_for_user(getattr(request.state, "user", None)), status_code=303)
