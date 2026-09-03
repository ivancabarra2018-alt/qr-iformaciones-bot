"""
Handler para lectura y análisis de QR desde imágenes enviadas al bot.
"""
import io
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.qr_reader import decode_qr_from_bytes, analyze_qr_content
from utils.formatters import fmt_qr_decoded
from database import register_scan
from utils.qr_engine import generate_qr_basic


async def handle_photo_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Detecta si una foto enviada contiene un QR y lo decodifica.
    Se activa automáticamente con cualquier imagen enviada.
    """
    message = update.effective_message
    await message.reply_chat_action("typing")

    # Obtener la foto en máxima resolución
    photo = message.photo[-1]
    photo_file = await photo.get_file()
    img_bytes = await photo_file.download_as_bytearray()

    await message.reply_text("🔍 Analizando imagen en busca de QR codes...")

    decoded_list = decode_qr_from_bytes(bytes(img_bytes))

    if not decoded_list:
        await message.reply_text(
            "❌ *No se encontró ningún QR* en la imagen.\n\n"
            "💡 *Consejos:*\n"
            "• Asegúrate de que el QR sea visible y esté bien iluminado\n"
            "• Evita imágenes borrosas o muy pequeñas\n"
            "• El QR debe estar completo en la foto",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    for i, decoded in enumerate(decoded_list, 1):
        analysis = analyze_qr_content(decoded["data"])
        text = fmt_qr_decoded(analysis)

        if len(decoded_list) > 1:
            text = f"*QR #{i} de {len(decoded_list)}*\n\n" + text

        # Botones de acción según el tipo
        keyboard = _action_keyboard(analysis)

        await message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )


async def handle_document_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Decodifica QR desde documentos/archivos de imagen."""
    message = update.effective_message
    doc = message.document

    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        return

    await message.reply_text("🔍 Procesando imagen como QR...")
    doc_file = await doc.get_file()
    img_bytes = await doc_file.download_as_bytearray()

    decoded_list = decode_qr_from_bytes(bytes(img_bytes))

    if not decoded_list:
        await message.reply_text("❌ No se encontró QR en el archivo.")
        return

    for decoded in decoded_list:
        analysis = analyze_qr_content(decoded["data"])
        await message.reply_text(
            fmt_qr_decoded(analysis),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_action_keyboard(analysis)
        )


def _action_keyboard(analysis: dict) -> InlineKeyboardMarkup:
    """Genera teclado con acciones según el tipo de QR detectado."""
    qr_type = analysis.get("type", "TEXT")
    content = analysis.get("content", "")
    rows = []

    if qr_type == "URL":
        rows.append([InlineKeyboardButton("🔗 Abrir URL", url=content)])

    elif qr_type == "WIFI":
        parsed = analysis.get("parsed", {})
        rows.append([
            InlineKeyboardButton(
                f"📶 Copiar: {parsed.get('ssid', '')}",
                callback_data=f"copy_wifi:{parsed.get('ssid', '')}"
            )
        ])

    elif qr_type == "GEO":
        parsed = analysis.get("parsed", {})
        lat = parsed.get("lat", "")
        lon = parsed.get("lon", "")
        if lat and lon:
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
            rows.append([InlineKeyboardButton("🗺 Abrir en Maps", url=maps_url)])

    elif qr_type == "EMAIL":
        rows.append([InlineKeyboardButton("📧 Abrir Email", url=f"mailto:{content}")])

    # Botón siempre disponible: regenerar como QR
    rows.append([
        InlineKeyboardButton(
            "🔄 Re-generar como QR",
            callback_data=f"regen_from_read:{content[:200]}"
        )
    ])

    return InlineKeyboardMarkup(rows) if rows else None


async def callback_regen_from_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Regenera un QR desde datos leídos."""
    query = update.callback_query
    await query.answer()
    content = query.data.replace("regen_from_read:", "")

    from database import save_qr
    qr_bytes = generate_qr_basic(content, style="clasico")
    qr_id = await save_qr(query.from_user.id, "QR desde lectura", "texto", content, "clasico")

    await query.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=f"✅ *QR re-generado!*\n🆔 ID: `{qr_id}`",
        parse_mode=ParseMode.MARKDOWN
    )
