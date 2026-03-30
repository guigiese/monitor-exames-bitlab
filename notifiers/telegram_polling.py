"""
Polling loop para receber comandos do Telegram Bot.

Comandos reconhecidos:
  /start    — boas-vindas e lista de comandos (sem info sensível)
  /assinar  — inscreve o usuário para receber notificações
  /sair     — remove o usuário da lista
  /status   — informa se o usuário está inscrito

Singleton: apenas uma instância de polling roda por processo.
Ao iniciar, drena updates pendentes para evitar processar comandos antigos.
"""

import os
import threading
import time

import requests

from .telegram import add_user, get_users, remove_user, get_user_ids

_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8704375512:AAFs8ICnxKAphbFscOK9NKNbpzWwyYTB4tA")

_polling_lock = threading.Lock()
_polling_started = False


def _send(token: str, chat_id, text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"[TelegramBot] Erro ao responder {chat_id}: {e}")


def _get_initial_offset(token: str) -> int:
    """
    Drena updates pendentes e retorna o próximo offset a usar.
    Isso garante que comandos enviados enquanto o bot estava offline
    não sejam processados ao reiniciar.
    """
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": -1, "timeout": 0},
            timeout=10,
        )
        if resp.ok:
            updates = resp.json().get("result", [])
            if updates:
                latest_id = updates[-1]["update_id"]
                # Acknowledge all pending updates
                requests.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params={"offset": latest_id + 1, "timeout": 0},
                    timeout=10,
                )
                return latest_id + 1
    except Exception as e:
        print(f"[TelegramBot] Erro ao inicializar offset: {e}")
    return 0


def _handle_update(token: str, update: dict):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = (message.get("text") or "").strip().lower()

    if text.startswith("/"):
        text = text.split("@")[0]

    # Extract user info from Telegram (phone number not available via Bot API)
    from_user = message.get("from", {})
    first_name = from_user.get("first_name", "")
    last_name = from_user.get("last_name", "")
    name = f"{first_name} {last_name}".strip()
    username = from_user.get("username", "")

    if text == "/start":
        _send(token, chat_id,
              "👋 <b>Olá! Bem-vindo(a)!</b>\n\n"
              "Este bot envia notificações automáticas de resultados.\n\n"
              "📋 Comandos disponíveis:\n"
              "• /assinar — receber notificações\n"
              "• /sair — cancelar inscrição\n"
              "• /status — verificar sua situação")

    elif text in ("/assinar", "/subscribe"):
        if add_user(chat_id, name=name, username=username):
            _send(token, chat_id,
                  "✅ <b>Inscrito com sucesso!</b>\n\n"
                  "Você passará a receber notificações automaticamente.\n\n"
                  "Para cancelar, envie /sair.")
        else:
            _send(token, chat_id,
                  "ℹ️ Você <b>já está inscrito</b> e receberá as notificações normalmente.\n\n"
                  "Para cancelar, envie /sair.")

    elif text in ("/sair", "/cancelar", "/unsubscribe"):
        if remove_user(chat_id):
            _send(token, chat_id,
                  "👋 Você foi <b>removido</b> da lista de notificações.\n\n"
                  "Para se inscrever novamente, envie /assinar.")
        else:
            _send(token, chat_id,
                  "ℹ️ Você não está na lista de notificações.")

    elif text == "/status":
        if chat_id in get_user_ids():
            _send(token, chat_id, "✅ Você está inscrito e receberá notificações.\n\nPara cancelar, envie /sair.")
        else:
            _send(token, chat_id, "❌ Você não está inscrito.\n\nEnvie /assinar para se inscrever.")


def run_bot_polling(token: str | None = None):
    """
    Roda em background thread. Singleton — ignora chamadas duplicadas.
    Drena updates pendentes ao iniciar para evitar processar comandos antigos.
    """
    global _polling_started
    with _polling_lock:
        if _polling_started:
            print("[TelegramBot] Polling já ativo — ignorando segunda chamada.")
            return
        _polling_started = True

    token = token or _TOKEN
    if not token:
        print("[TelegramBot] Token não configurado — polling desativado.")
        return

    print("[TelegramBot] Polling iniciado.")
    offset = _get_initial_offset(token)
    print(f"[TelegramBot] Offset inicial: {offset} (updates anteriores ignorados)")

    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=40,
            )
            if resp.ok:
                updates = resp.json().get("result", [])
                for update in updates:
                    _handle_update(token, update)
                    offset = update["update_id"] + 1
        except Exception as e:
            print(f"[TelegramBot] Erro no polling: {e}")
            time.sleep(5)
