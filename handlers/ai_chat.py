"""
Handler de IA (Google Gemini) para el bot QR.
Permite chat inteligente sobre cualquier tema.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

SYSTEM_PROMPT = """Eres un asistente inteligente integrado en @PingPongEliteBot, un bot de Telegram especializado en códigos QR.

Puedes responder cualquier pregunta sobre:
- Códigos QR: tipos, formatos, usos, diferencias
- Tecnología en general
- Preguntas cotidianas, cultura, ciencia, matemáticas
- Ayuda para negocios, marketing con QR
- Cualquier duda general

Responde siempre en español, de forma concisa y amigable.
Usa emojis con moderación. Máximo 300 palabras por respuesta.
Si el usuario pregunta sobre QR, recomienda los comandos del bot cuando sea relevante."""

MAX_HISTORY = 10  # Mensajes de historial por usuario


def _gemini_request(messages: list[dict]) -> str:
    """Llama a la API de Gemini y devuelve la respuesta."""
    if not GEMINI_API_KEY:
        return "⚠️ La IA no está configurada aún. El administrador debe añadir la GEMINI_API_KEY."

    # Construir contenidos para Gemini
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 500,
        }
    }

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=15
        )
        data = resp.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            logger.error(f"Gemini error: {data['error']}")
            return f"❌ Error de IA: {data['error'].get('message', 'desconocido')}"
    except requests.Timeout:
        return "⏳ La IA tardó demasiado. Intenta de nuevo."
    except Exception as e:
        logger.error(f"Gemini exception: {e}")
        return "❌ Error conectando con la IA. Intenta más tarde."

    return "❌ Sin respuesta de la IA."


from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode


async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el modo chat IA."""
    context.user_data["ai_mode"] = True
    context.user_data["ai_history"] = []
    await update.message.reply_text(
        "🤖 *Modo IA activado*\n\n"
        "Soy tu asistente inteligente. Puedo responder cualquier pregunta:\n"
        "• ❓ Dudas generales\n"
        "• 📱 Tecnología y QR\n"
        "• 🏢 Negocios y marketing\n"
        "• 🔬 Ciencia, cultura, math...\n\n"
        "Escríbeme lo que quieras 👇\n\n"
        "_Usa /salir para volver al menú QR_",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_salir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactiva el modo chat IA."""
    context.user_data["ai_mode"] = False
    context.user_data["ai_history"] = []
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Ver menú QR", callback_data="menu_back")
    ]])
    await update.message.reply_text(
        "✅ Modo IA desactivado. Volviendo al bot QR.",
        reply_markup=kb
    )


async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Procesa mensajes en modo IA.
    Devuelve True si manejó el mensaje, False si no es modo IA.
    """
    if not context.user_data.get("ai_mode", False):
        return False

    # Si hay acción pendiente del bot QR, salir del modo IA temporalmente
    if context.user_data.get("pending_action", ""):
        return False

    user_text = update.message.text
    if not user_text:
        return False

    # Mostrar "escribiendo..."
    await update.message.reply_chat_action("typing")

    # Gestionar historial
    history = context.user_data.get("ai_history", [])
    history.append({"role": "user", "content": user_text})

    # Limitar historial
    if len(history) > MAX_HISTORY * 2:
        history = history[-(MAX_HISTORY * 2):]

    # Llamar a Gemini
    response = _gemini_request(history)

    # Guardar respuesta en historial
    history.append({"role": "assistant", "content": response})
    context.user_data["ai_history"] = history

    # Botones de acción rápida
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Nueva pregunta", callback_data="ai_clear"),
            InlineKeyboardButton("🏠 Menú QR",        callback_data="menu_back"),
        ]
    ])

    await update.message.reply_text(
        response,
        reply_markup=kb
    )
    return True


async def callback_ai_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpia el historial de chat IA."""
    query = update.callback_query
    await query.answer()
    context.user_data["ai_history"] = []
    await query.edit_message_text(
        "🔄 *Historial limpiado.*\n\n"
        "Escribe tu próxima pregunta 👇\n"
        "_Usa /salir para volver al menú_",
        parse_mode=ParseMode.MARKDOWN
    )
