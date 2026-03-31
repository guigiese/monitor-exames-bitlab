import os
import re
import zlib
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Form, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bs4 import BeautifulSoup

from web.state import state
from core import run_monitor_loop
from labs import CONNECTORS
from notifiers import NOTIFIERS
from notifiers.telegram import get_users, remove_user
from notifiers.telegram_polling import (
    handle_update,
    register_webhook,
    WEBHOOK_SECRET_PATH,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

APP_URL = os.environ.get("APP_URL", "https://pinkblue-vet-production.up.railway.app")
STANDARD_STATUSES = ["Pronto", "Parcial", "Em Andamento", "Analisando", "Recebido", "Cancelado"]


@asynccontextmanager
async def lifespan(app):
    # Monitor loop
    monitor_thread = threading.Thread(target=run_monitor_loop, args=(state,), daemon=True)
    monitor_thread.start()

    # Register Telegram webhook (replaces polling — no thread needed)
    register_webhook(APP_URL)

    yield


app = FastAPI(lifespan=lifespan, title="PinkBlue Vet")
router = APIRouter(prefix="/labmonitor")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _render(request, template, **ctx):
    return templates.TemplateResponse(template, {"request": request, **ctx})


# ── Telegram Webhook ─────────────────────────────────────────────────────────

@app.post(f"/telegram/webhook/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(request: Request):
    """Receives Telegram updates via webhook. One update = one response, no polling race."""
    try:
        update = await request.json()
        handle_update(update)
    except Exception as e:
        print(f"[Webhook] Erro ao processar update: {e}")
    return JSONResponse({"ok": True})


# ── Landing page ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return _render(request, "index.html")


# ── Lab Monitor Pages ─────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    return _render(request, "dashboard.html",
                   lab_counts=state.get_lab_counts(),
                   notifications=state.notifications)


@router.get("/", response_class=HTMLResponse)
async def dashboard_slash(request: Request):
    return _render(request, "dashboard.html",
                   lab_counts=state.get_lab_counts(),
                   notifications=state.notifications)


@router.get("/exames", response_class=HTMLResponse)
async def exames(request: Request, lab: str = "", status: str = "", q: str = ""):
    return _render(request, "exames.html",
                   groups=state.get_exames(lab, status, q),
                   labs_cfg=state.config["labs"],
                   statuses=STANDARD_STATUSES,
                   lab_filter=lab,
                   status_filter=status,
                   q=q)


@router.get("/labs", response_class=HTMLResponse)
async def labs_page(request: Request):
    return _render(request, "labs.html",
                   labs=state.config["labs"],
                   last_check=state.last_check,
                   last_error=state.last_error)


@router.get("/canais", response_class=HTMLResponse)
async def canais_page(request: Request):
    return _render(request, "canais.html",
                   notifiers=state.config["notifiers"],
                   telegram_users=get_users())


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return _render(request, "settings.html",
                   config=state.config)


# ── HTMX Partials ─────────────────────────────────────────────────────────────

@router.get("/partials/notifications", response_class=HTMLResponse)
async def partial_notifications(request: Request):
    return _render(request, "partials/notifications.html",
                   notifications=state.notifications)


@router.get("/partials/lab_counts", response_class=HTMLResponse)
async def partial_lab_counts(request: Request):
    return _render(request, "partials/lab_counts.html",
                   lab_counts=state.get_lab_counts())


@router.get("/partials/exames", response_class=HTMLResponse)
async def partial_exames(request: Request, lab: str = "", status: str = "", q: str = ""):
    return _render(request, "partials/exames_table.html",
                   groups=state.get_exames(lab, status, q))


@router.get("/partials/telegram-users", response_class=HTMLResponse)
async def partial_telegram_users(request: Request):
    return _render(request, "partials/telegram_users.html",
                   telegram_users=get_users())


# ── Actions ───────────────────────────────────────────────────────────────────

@router.post("/labs/{lab_id}/toggle", response_class=HTMLResponse)
async def toggle_lab(request: Request, lab_id: str):
    state.toggle_lab(lab_id)
    lab = next(l for l in state.config["labs"] if l["id"] == lab_id)
    return HTMLResponse(_toggle_html("labs", lab_id, lab.get("enabled", True), lab["name"]))


@router.post("/canais/{notifier_id}/toggle", response_class=HTMLResponse)
async def toggle_notifier(request: Request, notifier_id: str):
    state.toggle_notifier(notifier_id)
    n = next(x for x in state.config["notifiers"] if x["id"] == notifier_id)
    return HTMLResponse(_toggle_html("canais", notifier_id, n.get("enabled", True), n["id"].capitalize()))


@router.post("/labs/{lab_id}/test", response_class=HTMLResponse)
async def test_lab(lab_id: str):
    lab_cfg = next((l for l in state.config["labs"] if l["id"] == lab_id), None)
    if not lab_cfg or lab_cfg["connector"] not in CONNECTORS:
        return HTMLResponse('<span class="text-red-600 text-sm">Lab não encontrado</span>')
    try:
        connector = CONNECTORS[lab_cfg["connector"]]()
        snap = connector.snapshot()
        return HTMLResponse(f'<span class="text-green-600 text-sm">✓ Conexão OK — {len(snap)} registros</span>')
    except Exception as e:
        return HTMLResponse(f'<span class="text-red-600 text-sm">✗ Erro: {e}</span>')


@router.post("/canais/{notifier_id}/test", response_class=HTMLResponse)
async def test_notifier(notifier_id: str):
    n_cfg = next((n for n in state.config["notifiers"] if n["id"] == notifier_id), None)
    if not n_cfg or n_cfg["type"] not in NOTIFIERS:
        return HTMLResponse('<span class="text-red-600 text-sm">Canal não encontrado</span>')
    try:
        notifier = NOTIFIERS[n_cfg["type"]]()
        notifier.enviar("🔔 <b>Teste — Lab Monitor</b>\nCanal funcionando!")
        return HTMLResponse('<span class="text-green-600 text-sm">✓ Mensagem enviada</span>')
    except Exception as e:
        return HTMLResponse(f'<span class="text-red-600 text-sm">✗ Erro: {e}</span>')


@router.post("/canais/telegram/users/{chat_id}/remove", response_class=HTMLResponse)
async def remove_telegram_user(request: Request, chat_id: str):
    remove_user(chat_id)
    return _render(request, "partials/telegram_users.html",
                   telegram_users=get_users())


@router.post("/settings/interval", response_class=HTMLResponse)
async def save_interval(minutes: int = Form(...)):
    state.set_interval(max(1, minutes))
    return HTMLResponse(f'<span class="text-green-600 text-sm">✓ Intervalo atualizado para {minutes} min</span>')


# ── Helper ────────────────────────────────────────────────────────────────────

def _toggle_html(route: str, id: str, enabled: bool, label: str) -> str:
    checked = "checked" if enabled else ""
    status_text  = "Habilitado" if enabled else "Desabilitado"
    status_color = "text-green-600" if enabled else "text-gray-400"
    return f'''
    <div id="toggle-{id}" class="flex items-center gap-3">
      <label class="toggle-switch" title="{status_text}">
        <input type="checkbox" {checked}
               hx-post="/labmonitor/{route}/{id}/toggle"
               hx-target="#toggle-{id}"
               hx-swap="outerHTML"
               hx-trigger="change">
        <span class="toggle-track"></span>
        <span class="toggle-thumb"></span>
      </label>
      <span class="text-sm font-medium {status_color}">{status_text}</span>
    </div>'''


@router.get("/partials/resultado/{item_id:path}", response_class=HTMLResponse)
async def partial_resultado(request: Request, item_id: str):
    """Fetches and parses a BitLab exam result HTML for inline display."""
    try:
        import requests as req_lib
        from labs.bitlab import BitlabConnector
        connector = BitlabConnector()
        token = connector._login()
        url = f"{connector.BASE}/ItemRequisicao/{item_id}?type=Html"
        resp = req_lib.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        resp.raise_for_status()
        rows = _parse_bitlab_resultado(resp.content)
    except Exception as e:
        rows = []
        return HTMLResponse(
            f'<p class="text-red-500 text-xs p-3">Erro ao carregar resultado: {e}</p>'
        )
    return _render(request, "partials/resultado_bitlab.html", rows=rows)


def _parse_bitlab_resultado(raw_bytes: bytes) -> list[dict]:
    """Parse BitLab zlib-compressed HTML into structured result rows with alert levels."""
    try:
        html = zlib.decompress(raw_bytes).decode("latin-1")
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    rows_by_top: dict[int, list[dict]] = {}

    for div in soup.find_all("div", style=True):
        style = div.get("style", "")
        lm = re.search(r"left:(\d+)px", style)
        tm = re.search(r"top:(\d+)px", style)
        if not lm or not tm or div.find("img"):
            continue
        left = int(lm.group(1))
        top = int(tm.group(1))
        text = div.get_text().strip()
        is_bold = bool(div.find("b"))
        if text:
            rows_by_top.setdefault(top, []).append(
                {"left": left, "text": text, "bold": is_bold}
            )

    # Reference range pattern (e.g. "5,0 a 10,0" or "200.000 a 630.000")
    _ref_pat = re.compile(r"[\d.,]+\s+a\s+[\d.,]+")

    results = []
    for top in sorted(rows_by_top):
        cols = sorted(rows_by_top[top], key=lambda c: c["left"])

        # Name: leftmost column to the left of 240
        name_col = next((c for c in cols if c["left"] < 240), None)
        if not name_col:
            continue

        # Reference: rightmost column that contains a "X a Y" range pattern
        ref_col = next(
            (c for c in sorted(cols, key=lambda c: -c["left"])
             if _ref_pat.search(c["text"])),
            None,
        )
        if not ref_col:
            continue

        # Value: first bold column ≥240 that is not ref_col; fallback to any non-name column
        val_candidates = [c for c in cols if c["left"] >= 240 and c is not ref_col]
        val_col = (
            next((c for c in val_candidates if c["bold"]), None)
            or next((c for c in val_candidates), None)
        )
        if not val_col:
            continue

        name = re.sub(r"\.{2,}:?\s*$", "", name_col["text"]).rstrip(":").strip()
        if len(name) < 3:
            continue

        value_str = val_col["text"].strip()
        ref_str   = re.sub(r"\s{2,}", " / ", ref_col["text"].strip())

        alert = None
        try:
            numeric = float(value_str.replace(".", "").replace(",", "."))
            ref_m = _ref_pat.search(ref_col["text"])
            if ref_m:
                parts = ref_m.group().split(" a ")
                rmin = float(parts[0].strip().replace(".", "").replace(",", "."))
                rmax = float(parts[1].strip().replace(".", "").replace(",", "."))
                if numeric < rmin or numeric > rmax:
                    boundary = rmin if numeric < rmin else rmax
                    deviation = abs(numeric - boundary) / boundary if boundary else 1
                    alert = "red" if deviation > 0.20 else "yellow"
        except (ValueError, ZeroDivisionError):
            pass

        results.append({
            "nome":       name,
            "valor":      value_str,
            "referencia": ref_str,
            "alerta":     alert,
        })

    return results


app.include_router(router)
