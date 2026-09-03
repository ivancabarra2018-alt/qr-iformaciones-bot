"""
Handlers para generación de QR - todos los tipos y flujos de conversación.
"""
import os
import io
import zipfile
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.constants import ParseMode

from database import save_qr, get_user_qrs, get_qr, delete_qr, get_top_qrs
from utils.qr_engine import (
    generate_qr_basic, generate_qr_gradient,
    format_wifi_content, format_vcard_content, format_email_content,
    format_sms_content, format_geo_content, format_event_content,
    format_crypto_content
)
from utils.formatters import fmt_qr_list, fmt_qr_detail, fmt_styles_menu
from config import QR_STYLES, QR_TYPES, QR_OUTPUT_DIR

# ── Estados de ConversationHandler ────────────────────────────────────────────
(
    STATE_STYLE, STATE_MODULE, STATE_NAME, STATE_EXPIRY,
    # WiFi
    WIFI_SSID, WIFI_PASS, WIFI_SEC,
    # vCard
    VCARD_NAME, VCARD_PHONE, VCARD_EMAIL, VCARD_COMPANY, VCARD_URL,
    # Email
    EMAIL_TO, EMAIL_SUBJECT, EMAIL_BODY,
    # SMS
    SMS_PHONE, SMS_MESSAGE,
    # Geo
    GEO_LAT, GEO_LON, GEO_LABEL,
    # Evento
    EVT_SUMMARY, EVT_START, EVT_END, EVT_LOCATION, EVT_DESC,
    # Crypto
    CRYPTO_COIN, CRYPTO_ADDR, CRYPTO_AMOUNT,
    # Batch
    BATCH_LINES,
    # General
    GENERAL_CONTENT,
) = range(30)


def _style_keyboard():
    """Teclado inline para selección de estilo."""
    buttons = []
    styles = list(QR_STYLES.items())
    for i in range(0, len(styles), 2):
        row = []
        for key, val in styles[i:i+2]:
            row.append(InlineKeyboardButton(val["description"], callback_data=f"style:{key}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def _module_keyboard():
    """Teclado inline para estilo de módulos."""
    modules = [
        ("◼ Cuadrado", "cuadrado"), ("⬤ Círculo", "circulo"),
        ("▪ Redondeado", "redondeado"), ("≡ Barras H", "barras_h"),
        ("║ Barras V", "barras_v"),
    ]
    buttons = [[InlineKeyboardButton(n, callback_data=f"module:{k}")] for n, k in modules]
    return InlineKeyboardMarkup(buttons)


def _expiry_keyboard():
    """Teclado inline para expiración."""
    options = [
        ("Sin expiración", "never"), ("1 día", "1d"),
        ("7 días", "7d"), ("30 días", "30d"),
        ("90 días", "90d"), ("1 año", "365d"),
    ]
    buttons = []
    for i in range(0, len(options), 2):
        row = [InlineKeyboardButton(n, callback_data=f"expiry:{k}") for n, k in options[i:i+2]]
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def _send_qr_image(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          qr_bytes: bytes, caption: str, qr_id: int):
    """Envía la imagen del QR con botones de gestión."""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 Detalles", callback_data=f"qr_detail:{qr_id}"),
            InlineKeyboardButton("🗑 Eliminar", callback_data=f"qr_delete:{qr_id}"),
        ],
        [
            InlineKeyboardButton("🔄 Regenerar", callback_data=f"qr_regen:{qr_id}"),
            InlineKeyboardButton("📤 Compartir", callback_data=f"qr_share:{qr_id}"),
        ],
    ])
    await update.effective_message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ── /qr RÁPIDO ───────────────────────────────────────────────────────────────

async def cmd_qr_quick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera un QR rápido desde texto. Uso: /qr <contenido>"""
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "📝 Uso: `/qr <texto o URL>`\n\nEjemplo: `/qr https://google.com`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    content = " ".join(context.args)
    style = context.user_data.get("default_style", "clasico")

    await update.message.reply_chat_action("upload_photo")

    qr_bytes = generate_qr_basic(content, style=style)
    qr_id = await save_qr(
        user.id, f"QR Rápido", "url" if content.startswith("http") else "texto",
        content, style
    )

    await _send_qr_image(
        update, context, qr_bytes,
        f"✅ *QR generado!*\n📄 `{content[:60]}`\n🎨 Estilo: {QR_STYLES[style]['description']}\n🆔 ID: `{qr_id}`",
        qr_id
    )


# ── /qr_url ───────────────────────────────────────────────────────────────────

async def cmd_qr_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de QR de URL con personalización completa."""
    context.user_data.clear()
    context.user_data["qr_type"] = "url"
    await update.message.reply_text(
        "🔗 *QR de URL/Web*\n\nEscribe la URL completa:",
        parse_mode=ParseMode.MARKDOWN
    )
    return GENERAL_CONTENT


async def receive_general_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el contenido y pide el estilo."""
    context.user_data["content"] = update.message.text
    await update.message.reply_text(
        "🎨 *Elige el estilo visual de tu QR:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_style_keyboard()
    )
    return STATE_STYLE


async def receive_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la selección de estilo."""
    query = update.callback_query
    await query.answer()
    style = query.data.split(":")[1]
    context.user_data["style"] = style

    await query.edit_message_text(
        "⬛ *Elige el estilo de los módulos del QR:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_module_keyboard()
    )
    return STATE_MODULE


async def receive_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el estilo de módulo."""
    query = update.callback_query
    await query.answer()
    module = query.data.split(":")[1]
    context.user_data["module"] = module

    await query.edit_message_text(
        "📛 *Ponle un nombre a este QR (o escribe 'skip' para saltar):*",
        parse_mode=ParseMode.MARKDOWN
    )
    return STATE_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre y pide expiración."""
    text = update.message.text
    context.user_data["name"] = "" if text.lower() == "skip" else text

    await update.message.reply_text(
        "⏳ *¿Cuándo debe expirar este QR?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_expiry_keyboard()
    )
    return STATE_EXPIRY


async def receive_expiry_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe expiración, genera y envía el QR."""
    query = update.callback_query
    await query.answer()
    expiry_key = query.data.split(":")[1]

    expires_at = None
    if expiry_key != "never":
        days = int(expiry_key.replace("d", ""))
        expires_at = datetime.utcnow() + timedelta(days=days)

    user = update.effective_user
    ud = context.user_data
    content = ud.get("content", "")
    style = ud.get("style", "clasico")
    module = ud.get("module", "redondeado")
    name = ud.get("name") or f"QR {datetime.now().strftime('%d/%m %H:%M')}"
    qr_type = ud.get("qr_type", "url")

    await query.edit_message_text("⏳ Generando tu QR...")

    qr_bytes = generate_qr_basic(content, style=style, module_style=module, label=name if name else None)
    qr_id = await save_qr(user.id, name, qr_type, content, style, expires_at)

    style_desc = QR_STYLES.get(style, {}).get("description", style)
    expiry_str = f"\n⏳ Expira: {expires_at.strftime('%d/%m/%Y')}" if expires_at else ""

    await query.delete_message()
    await _send_qr_image(
        update, context, qr_bytes,
        f"✅ *{name}*\n🆔 `{qr_id}` │ 🎨 {style_desc}{expiry_str}",
        qr_id
    )
    return ConversationHandler.END


# ── /qr_wifi ──────────────────────────────────────────────────────────────────

async def cmd_qr_wifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["qr_type"] = "wifi"
    await update.message.reply_text(
        "📶 *QR de WiFi*\n\n📡 Escribe el nombre de la red (SSID):",
        parse_mode=ParseMode.MARKDOWN
    )
    return WIFI_SSID


async def wifi_ssid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wifi_ssid"] = update.message.text
    await update.message.reply_text("🔑 Ahora escribe la contraseña de la red:")
    return WIFI_PASS


async def wifi_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wifi_pass"] = update.message.text
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("WPA/WPA2", callback_data="wifi_sec:WPA"),
        InlineKeyboardButton("WEP", callback_data="wifi_sec:WEP"),
        InlineKeyboardButton("Sin contraseña", callback_data="wifi_sec:nopass"),
    ]])
    await update.message.reply_text(
        "🔒 Tipo de seguridad:", reply_markup=kb
    )
    return WIFI_SEC


async def wifi_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    security = query.data.split(":")[1]
    ud = context.user_data
    content = format_wifi_content(ud["wifi_ssid"], ud.get("wifi_pass", ""), security)
    ud["content"] = content
    name = f"WiFi: {ud['wifi_ssid']}"

    await query.edit_message_text("⏳ Generando QR de WiFi...")
    qr_bytes = generate_qr_basic(content, style="azul", module_style="redondeado")
    qr_id = await save_qr(query.from_user.id, name, "wifi", content, "azul")

    await query.delete_message()
    await _send_qr_image(
        update, context, qr_bytes,
        f"📶 *QR WiFi generado!*\n🔌 Red: `{ud['wifi_ssid']}`\n🆔 `{qr_id}`",
        qr_id
    )
    return ConversationHandler.END


# ── /qr_vcard ─────────────────────────────────────────────────────────────────

async def cmd_qr_vcard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["qr_type"] = "vcard"
    await update.message.reply_text(
        "👤 *QR Tarjeta de Contacto (vCard)*\n\n✍️ Escribe el nombre completo:",
        parse_mode=ParseMode.MARKDOWN
    )
    return VCARD_NAME


async def vcard_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["vcard_name"] = update.message.text
    await update.message.reply_text("📞 Teléfono (o 'skip'):")
    return VCARD_PHONE


async def vcard_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["vcard_phone"] = "" if t.lower() == "skip" else t
    await update.message.reply_text("📧 Email (o 'skip'):")
    return VCARD_EMAIL


async def vcard_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["vcard_email"] = "" if t.lower() == "skip" else t
    await update.message.reply_text("🏢 Empresa (o 'skip'):")
    return VCARD_COMPANY


async def vcard_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["vcard_company"] = "" if t.lower() == "skip" else t
    await update.message.reply_text("🌐 Sitio web (o 'skip'):")
    return VCARD_URL


async def vcard_url_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ud = context.user_data
    url = "" if t.lower() == "skip" else t

    content = format_vcard_content(
        ud["vcard_name"], ud.get("vcard_phone", ""),
        ud.get("vcard_email", ""), ud.get("vcard_company", ""), url
    )
    name = f"vCard: {ud['vcard_name']}"
    await update.message.reply_text("⏳ Generando QR de contacto...")
    qr_bytes = generate_qr_basic(content, style="morado", module_style="redondeado")
    qr_id = await save_qr(update.effective_user.id, name, "vcard", content, "morado")

    await _send_qr_image(
        update, context, qr_bytes,
        f"👤 *vCard generada!*\n👤 {ud['vcard_name']}\n🆔 `{qr_id}`",
        qr_id
    )
    return ConversationHandler.END


# ── /qr_email ─────────────────────────────────────────────────────────────────

async def cmd_qr_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["qr_type"] = "email"
    await update.message.reply_text(
        "📧 *QR de Email*\n\n✉️ ¿A qué dirección de email?",
        parse_mode=ParseMode.MARKDOWN
    )
    return EMAIL_TO


async def email_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email_to"] = update.message.text
    await update.message.reply_text("📝 Asunto del email (o 'skip'):")
    return EMAIL_SUBJECT


async def email_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["email_subject"] = "" if t.lower() == "skip" else t
    await update.message.reply_text("💬 Cuerpo del mensaje (o 'skip'):")
    return EMAIL_BODY


async def email_body_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ud = context.user_data
    body = "" if t.lower() == "skip" else t
    content = format_email_content(ud["email_to"], ud.get("email_subject", ""), body)
    name = f"Email: {ud['email_to']}"
    qr_bytes = generate_qr_basic(content, style="azul")
    qr_id = await save_qr(update.effective_user.id, name, "email", content, "azul")
    await _send_qr_image(
        update, context, qr_bytes,
        f"📧 *QR Email creado!*\n✉️ Para: `{ud['email_to']}`\n🆔 `{qr_id}`",
        qr_id
    )
    return ConversationHandler.END


# ── /qr_sms ───────────────────────────────────────────────────────────────────

async def cmd_qr_sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "💬 *QR de SMS*\n\n📞 Número de teléfono destino:",
        parse_mode=ParseMode.MARKDOWN
    )
    return SMS_PHONE


async def sms_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sms_phone"] = update.message.text
    await update.message.reply_text("💬 Mensaje de texto (o 'skip'):")
    return SMS_MESSAGE


async def sms_message_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ud = context.user_data
    msg = "" if t.lower() == "skip" else t
    content = format_sms_content(ud["sms_phone"], msg)
    name = f"SMS: {ud['sms_phone']}"
    qr_bytes = generate_qr_basic(content, style="verde")
    qr_id = await save_qr(update.effective_user.id, name, "sms", content, "verde")
    await _send_qr_image(
        update, context, qr_bytes,
        f"💬 *QR SMS creado!*\n📞 Para: `{ud['sms_phone']}`\n🆔 `{qr_id}`",
        qr_id
    )
    return ConversationHandler.END


# ── /qr_ubicacion ─────────────────────────────────────────────────────────────

async def cmd_qr_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "📍 *QR de Ubicación GPS*\n\n🌐 Escribe la latitud (ej: 40.4168):",
        parse_mode=ParseMode.MARKDOWN
    )
    return GEO_LAT


async def geo_lat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["geo_lat"] = float(update.message.text)
        await update.message.reply_text("🌐 Ahora la longitud (ej: -3.7038):")
        return GEO_LON
    except ValueError:
        await update.message.reply_text("❌ Latitud inválida. Escribe un número como: 40.4168")
        return GEO_LAT


async def geo_lon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["geo_lon"] = float(update.message.text)
        await update.message.reply_text("🏷 Etiqueta del lugar (o 'skip'):")
        return GEO_LABEL
    except ValueError:
        await update.message.reply_text("❌ Longitud inválida. Escribe un número como: -3.7038")
        return GEO_LON


async def geo_label_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ud = context.user_data
    label = "" if t.lower() == "skip" else t
    lat, lon = ud["geo_lat"], ud["geo_lon"]
    content = format_geo_content(lat, lon, label)
    name = label or f"GPS {lat:.4f},{lon:.4f}"
    qr_bytes = generate_qr_basic(content, style="verde", module_style="redondeado")
    qr_id = await save_qr(update.effective_user.id, name, "ubicacion", content, "verde")
    await _send_qr_image(
        update, context, qr_bytes,
        f"📍 *QR GPS creado!*\n🌐 `{lat}, {lon}`\n🆔 `{qr_id}`",
        qr_id
    )
    return ConversationHandler.END


# ── /qr_crypto ────────────────────────────────────────────────────────────────

async def cmd_qr_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("₿ Bitcoin", callback_data="crypto_coin:bitcoin"),
        InlineKeyboardButton("Ξ Ethereum", callback_data="crypto_coin:ethereum"),
        InlineKeyboardButton("◎ Solana", callback_data="crypto_coin:solana"),
    ], [
        InlineKeyboardButton("🔵 USDT", callback_data="crypto_coin:tether"),
        InlineKeyboardButton("💎 BNB", callback_data="crypto_coin:binancecoin"),
    ]])
    await update.message.reply_text(
        "₿ *QR Crypto*\n\nElige la criptomoneda:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return CRYPTO_COIN


async def crypto_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["crypto_coin"] = query.data.split(":")[1]
    await query.edit_message_text("📋 Pega la dirección de tu wallet:")
    return CRYPTO_ADDR


async def crypto_addr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["crypto_addr"] = update.message.text
    await update.message.reply_text("💰 Cantidad (o 'skip' para omitir):")
    return CRYPTO_AMOUNT


async def crypto_amount_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ud = context.user_data
    amount = "" if t.lower() == "skip" else t
    coin = ud["crypto_coin"]
    content = format_crypto_content(coin, ud["crypto_addr"], amount)
    name = f"{coin.title()} Wallet"
    qr_bytes = generate_qr_basic(content, style="dorado", module_style="redondeado")
    qr_id = await save_qr(update.effective_user.id, name, "crypto", content, "dorado")
    await _send_qr_image(
        update, context, qr_bytes,
        f"₿ *QR Crypto creado!*\n🪙 {coin.title()}\n🆔 `{qr_id}`",
        qr_id
    )
    return ConversationHandler.END


# ── /qr_batch ─────────────────────────────────────────────────────────────────

async def cmd_qr_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 *QR en Lote*\n\n"
        "Escribe hasta 10 URLs o textos, *uno por línea*:\n\n"
        "```\nhttps://google.com\nhttps://github.com\nMi empresa 2024\n```",
        parse_mode=ParseMode.MARKDOWN
    )
    return BATCH_LINES


async def batch_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [l.strip() for l in update.message.text.split("\n") if l.strip()][:10]
    if not lines:
        await update.message.reply_text("❌ No encontré contenido válido.")
        return ConversationHandler.END

    user = update.effective_user
    await update.message.reply_text(f"⏳ Generando {len(lines)} QR codes...")

    # Crear ZIP en memoria
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, line in enumerate(lines, 1):
            style = list(QR_STYLES.keys())[i % len(QR_STYLES)]
            qr_bytes = generate_qr_basic(line, style=style)
            filename = f"qr_{i:02d}_{line[:30].replace('/', '_').replace(':', '')}.png"
            zf.writestr(filename, qr_bytes)
            await save_qr(user.id, f"Batch QR {i}", "url" if line.startswith("http") else "texto", line, style)

    zip_buf.seek(0)
    await update.message.reply_document(
        document=zip_buf,
        filename=f"qr_batch_{len(lines)}.zip",
        caption=f"📦 *{len(lines)} QR codes generados!*\nTodos están guardados en tu historial.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


# ── GESTIÓN DE QR ─────────────────────────────────────────────────────────────

async def cmd_mis_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los QR del usuario con paginación."""
    user = update.effective_user
    page = int(context.args[0]) if context.args else 1
    offset = (page - 1) * 10
    qrs = await get_user_qrs(user.id, limit=10, offset=offset)

    text = fmt_qr_list(qrs, page=page)
    kb_rows = []
    if page > 1:
        kb_rows.append(InlineKeyboardButton(f"⬅️ Anterior", callback_data=f"qr_page:{page-1}"))
    if len(qrs) == 10:
        kb_rows.append(InlineKeyboardButton(f"Siguiente ➡️", callback_data=f"qr_page:{page+1}"))

    kb = InlineKeyboardMarkup([kb_rows]) if kb_rows else None
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def callback_qr_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra detalles de un QR."""
    query = update.callback_query
    await query.answer()
    qr_id = int(query.data.split(":")[1])
    qr = await get_qr(qr_id)
    if not qr:
        await query.answer("QR no encontrado", show_alert=True)
        return
    text = fmt_qr_detail(qr)
    await query.edit_message_caption(text, parse_mode=ParseMode.MARKDOWN)


async def callback_qr_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina un QR con confirmación."""
    query = update.callback_query
    qr_id = int(query.data.split(":")[1])
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar borrado", callback_data=f"qr_delete_confirm:{qr_id}"),
        InlineKeyboardButton("❌ Cancelar", callback_data="qr_cancel"),
    ]])
    await query.answer()
    await query.edit_message_caption(
        f"⚠️ ¿Seguro que quieres eliminar el QR `{qr_id}`?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )


async def callback_qr_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    qr_id = int(query.data.split(":")[1])
    ok = await delete_qr(qr_id, query.from_user.id)
    await query.answer("✅ QR eliminado" if ok else "❌ Error al eliminar", show_alert=True)
    if ok:
        await query.delete_message()


async def callback_qr_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Cancelado")
    await query.delete_message()


async def callback_qr_regen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Regenera el QR con nuevas opciones de estilo."""
    query = update.callback_query
    await query.answer()
    qr_id = int(query.data.split(":")[1])
    qr = await get_qr(qr_id)
    if not qr:
        await query.answer("QR no encontrado", show_alert=True)
        return

    context.user_data["regen_qr_id"] = qr_id
    context.user_data["content"] = qr["content"]
    context.user_data["qr_type"] = qr["qr_type"]
    context.user_data["name"] = qr["name"]

    await query.edit_message_caption(
        "🎨 *Elige el nuevo estilo:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_style_keyboard()
    )


async def cmd_top_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los QR más escaneados."""
    user = update.effective_user
    qrs = await get_top_qrs(user.id, limit=5)
    if not qrs:
        await update.message.reply_text("📭 Aún no tienes QR con escaneos registrados.")
        return
    lines = ["🏆 *Tus QR más escaneados:*\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, qr in enumerate(qrs):
        name = qr.get("name") or f"QR #{qr['id']}"
        lines.append(f"{medals[i]} *{name}* → {qr['scan_count']} scans")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca QR del usuario por nombre o contenido."""
    from database import search_user_qrs
    if not context.args:
        await update.message.reply_text("🔍 Uso: `/buscar <término>`", parse_mode=ParseMode.MARKDOWN)
        return
    query_str = " ".join(context.args)
    results = await search_user_qrs(update.effective_user.id, query_str)
    text = fmt_qr_list(results) if results else f"🔍 No encontré QR con '{query_str}'"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
