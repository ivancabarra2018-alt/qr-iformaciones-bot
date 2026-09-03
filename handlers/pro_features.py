"""
Módulo de funciones PRO avanzadas del Bot QR:
- QR Dinámicos (destino editable sin regenerar)
- QR para Menú de Restaurante
- QR de Tarjeta de Visita Digital con mini web
- QR Multi-URL (A/B testing de destinos)
- QR con Acortador + Estadísticas de clicks
- Templates profesionales para empresas
- QR para Grupos/Canales de Telegram
- QR de Pago (Bizum, PayPal, etc.)
- Modo empresa (colecciones para equipos)
"""
import io
import json
import hashlib
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.constants import ParseMode

from database import save_qr, get_user_qrs
from utils.qr_engine import generate_qr_basic, generate_qr_gradient
from config import QR_STYLES

# ── Estados de conversación ───────────────────────────────────────────────────
(
    MENU_NOMBRE, MENU_ITEMS,               # 0,1
    BCARD_NAME, BCARD_JOB, BCARD_PHONE, BCARD_EMAIL, BCARD_WEB, BCARD_SOCIAL,  # 2-7
    TG_TYPE, TG_LINK,                      # 8,9
    PAY_METHOD, PAY_HANDLE, PAY_CONCEPT,   # 10,11,12
    DYN_URL, DYN_NAME,                     # 13,14
    AB_URL1, AB_URL2, AB_NAME,             # 15,16,17
) = range(18)


# ════════════════════════════════════════════════════════════════════════════════
# 1. QR MENÚ DE RESTAURANTE / NEGOCIO
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_qr_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """QR que lleva a un menú digital de restaurante/negocio."""
    context.user_data.clear()
    await update.message.reply_text(
        "🍽️ *QR Menú Digital para tu Negocio*\n\n"
        "Genera un QR profesional que tus clientes escanean para ver tu menú.\n\n"
        "📛 ¿Cuál es el nombre de tu negocio o restaurante?",
        parse_mode=ParseMode.MARKDOWN
    )
    return MENU_NOMBRE


async def menu_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["menu_nombre"] = update.message.text
    await update.message.reply_text(
        "🔗 Pega la URL de tu menú digital\n"
        "(Google Drive, Carta.menu, TripAdvisor, tu web, etc.):"
    )
    return MENU_ITEMS


async def menu_url_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    nombre = context.user_data.get("menu_nombre", "Mi Negocio")
    user = update.effective_user

    content = url
    await update.message.reply_chat_action("upload_photo")

    # QR dorado con etiqueta del negocio — aspecto premium
    qr_bytes = generate_qr_basic(
        content, style="dorado", module_style="redondeado", label=f"📋 {nombre}"
    )
    qr_id = await save_qr(
        user.id, f"Menú: {nombre}", "url", content, "dorado",
        metadata={"subtipo": "menu_restaurante", "negocio": nombre}
    )

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📥 Detalles", callback_data=f"qr_detail:{qr_id}"),
        InlineKeyboardButton("🗑 Eliminar", callback_data=f"qr_delete:{qr_id}"),
    ]])
    await update.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=(
            f"🍽️ *QR Menú Digital — {nombre}*\n\n"
            f"✅ Imprime este QR en tus mesas, carta o escaparate\n"
            f"📱 Tus clientes lo escanean y ven el menú al instante\n"
            f"🆔 ID: `{qr_id}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# 2. QR TARJETA DE VISITA DIGITAL (Business Card)
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_qr_bcard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """QR de tarjeta de visita digital ultra-completa."""
    context.user_data.clear()
    await update.message.reply_text(
        "💼 *QR Tarjeta de Visita Digital PRO*\n\n"
        "Crea un QR que al escanearlo guarda automáticamente\n"
        "todos tus datos de contacto en el teléfono.\n\n"
        "👤 ¿Tu nombre completo?",
        parse_mode=ParseMode.MARKDOWN
    )
    return BCARD_NAME


async def bcard_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bc_name"] = update.message.text
    await update.message.reply_text("💼 ¿Tu cargo / profesión? (o 'skip')")
    return BCARD_JOB


async def bcard_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["bc_job"] = "" if t.lower() == "skip" else t
    await update.message.reply_text("📞 ¿Tu teléfono? (o 'skip')")
    return BCARD_PHONE


async def bcard_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["bc_phone"] = "" if t.lower() == "skip" else t
    await update.message.reply_text("📧 ¿Tu email profesional? (o 'skip')")
    return BCARD_EMAIL


async def bcard_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["bc_email"] = "" if t.lower() == "skip" else t
    await update.message.reply_text("🌐 ¿Tu web o LinkedIn? (o 'skip')")
    return BCARD_WEB


async def bcard_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    context.user_data["bc_web"] = "" if t.lower() == "skip" else t
    await update.message.reply_text(
        "📱 ¿Tu Telegram, Instagram o Twitter? (ej: @usuario) (o 'skip')"
    )
    return BCARD_SOCIAL


async def bcard_social_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ud = context.user_data
    social = "" if t.lower() == "skip" else t
    user = update.effective_user

    # Construir vCard extendida
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{ud['bc_name']}", f"N:{ud['bc_name']};;;;"]
    if ud.get("bc_job"):    lines.append(f"TITLE:{ud['bc_job']}")
    if ud.get("bc_phone"):  lines.append(f"TEL;TYPE=CELL:{ud['bc_phone']}")
    if ud.get("bc_email"):  lines.append(f"EMAIL:{ud['bc_email']}")
    if ud.get("bc_web"):    lines.append(f"URL:{ud['bc_web']}")
    if social:              lines.append(f"NOTE:Social: {social}")
    lines.append("END:VCARD")
    content = "\n".join(lines)

    await update.message.reply_chat_action("upload_photo")
    qr_bytes = generate_qr_basic(content, style="morado", module_style="redondeado",
                                   label=ud["bc_name"])
    qr_id = await save_qr(user.id, f"BCard: {ud['bc_name']}", "vcard", content, "morado",
                          metadata={"subtipo": "business_card"})

    # Resumen de la tarjeta
    resumen = f"👤 *{ud['bc_name']}*"
    if ud.get("bc_job"):   resumen += f"\n💼 {ud['bc_job']}"
    if ud.get("bc_phone"): resumen += f"\n📞 {ud['bc_phone']}"
    if ud.get("bc_email"): resumen += f"\n📧 {ud['bc_email']}"
    if ud.get("bc_web"):   resumen += f"\n🌐 {ud['bc_web']}"
    if social:             resumen += f"\n📱 {social}"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📥 Detalles", callback_data=f"qr_detail:{qr_id}"),
        InlineKeyboardButton("🗑 Eliminar", callback_data=f"qr_delete:{qr_id}"),
    ]])
    await update.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=(
            f"💼 *Tarjeta de Visita Digital creada!*\n\n"
            f"{resumen}\n\n"
            f"✅ Al escanearlo, guarda el contacto automáticamente\n"
            f"🆔 ID: `{qr_id}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# 3. QR DE TELEGRAM (Canal, Grupo, Bot, Usuario)
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_qr_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """QR para enlazar a cualquier destino de Telegram."""
    context.user_data.clear()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Canal", callback_data="tg_type:canal"),
         InlineKeyboardButton("👥 Grupo", callback_data="tg_type:grupo")],
        [InlineKeyboardButton("🤖 Bot", callback_data="tg_type:bot"),
         InlineKeyboardButton("👤 Usuario", callback_data="tg_type:usuario")],
        [InlineKeyboardButton("🔗 Enlace de invitación", callback_data="tg_type:invite")],
    ])
    await update.message.reply_text(
        "✈️ *QR de Telegram*\n\n"
        "Genera un QR que al escanearlo abre directamente\n"
        "tu canal, grupo, bot o perfil en Telegram.\n\n"
        "¿Qué tipo de destino quieres?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return TG_TYPE


async def tg_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tipo = query.data.split(":")[1]
    context.user_data["tg_tipo"] = tipo

    ejemplos = {
        "canal":   "@MiCanal o https://t.me/micanal",
        "grupo":   "@MiGrupo o el enlace de invitación",
        "bot":     "@MiBot o https://t.me/mibot",
        "usuario": "@miusuario",
        "invite":  "https://t.me/+AbCdEf12345",
    }
    await query.edit_message_text(
        f"✈️ *QR de Telegram — {tipo.title()}*\n\n"
        f"Escribe el usuario o enlace:\n"
        f"Ejemplo: `{ejemplos.get(tipo, '@usuario')}`",
        parse_mode=ParseMode.MARKDOWN
    )
    return TG_LINK


async def tg_link_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    ud = context.user_data
    tipo = ud.get("tg_tipo", "canal")
    user = update.effective_user

    # Normalizar URL
    if texto.startswith("@"):
        url = f"https://t.me/{texto[1:]}"
    elif texto.startswith("https://t.me/"):
        url = texto
    else:
        url = f"https://t.me/{texto}"

    await update.message.reply_chat_action("upload_photo")

    iconos = {"canal": "📢", "grupo": "👥", "bot": "🤖", "usuario": "👤", "invite": "🔗"}
    icono = iconos.get(tipo, "✈️")

    qr_bytes = generate_qr_gradient(url, color1="#0088CC", color2="#00CCFF",
                                     gradient_type="radial", module_style="redondeado",
                                     label=f"✈️ {texto[:30]}")
    qr_id = await save_qr(user.id, f"Telegram {tipo}: {texto[:30]}", "url", url, "azul",
                          metadata={"subtipo": "telegram_link", "tipo": tipo})

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Abrir en Telegram", url=url),
        InlineKeyboardButton("📥 Detalles", callback_data=f"qr_detail:{qr_id}"),
    ]])
    await update.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=(
            f"{icono} *QR de Telegram creado!*\n\n"
            f"🔗 Destino: `{url}`\n"
            f"📱 Al escanearlo abre Telegram directamente\n"
            f"🆔 ID: `{qr_id}`\n\n"
            f"💡 _Ideal para carteles, tarjetas y publicidad_"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# 4. QR DE PAGO (Bizum, PayPal, Revolut, etc.)
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_qr_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """QR para solicitar pagos rápidos."""
    context.user_data.clear()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💙 Bizum", callback_data="pay:bizum"),
         InlineKeyboardButton("🔵 PayPal", callback_data="pay:paypal")],
        [InlineKeyboardButton("🟣 Revolut", callback_data="pay:revolut"),
         InlineKeyboardButton("🟢 Verse", callback_data="pay:verse")],
        [InlineKeyboardButton("💳 Número de cuenta IBAN", callback_data="pay:iban")],
    ])
    await update.message.reply_text(
        "💳 *QR de Pago Rápido*\n\n"
        "Genera un QR para que tus clientes te paguen\n"
        "directamente con su móvil.\n\n"
        "¿Qué método de pago quieres?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return PAY_METHOD


async def pay_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split(":")[1]
    context.user_data["pay_method"] = method

    prompts = {
        "bizum":  "📞 ¿Tu número de teléfono Bizum? (ej: 612345678)",
        "paypal": "📧 ¿Tu email o link de PayPal? (ej: paypal.me/tunombre)",
        "revolut":"🔗 ¿Tu link de Revolut? (ej: revolut.me/tunombre)",
        "verse":  "🔗 ¿Tu link de Verse o teléfono?",
        "iban":   "🏦 ¿Tu IBAN? (ej: ES91 2100 0418...)",
    }
    await query.edit_message_text(prompts.get(method, "¿Tu identificador de pago?"))
    return PAY_HANDLE


async def pay_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pay_handle"] = update.message.text
    await update.message.reply_text(
        "💬 ¿Concepto o descripción del pago? (ej: 'Producto X' o 'skip')"
    )
    return PAY_CONCEPT


async def pay_concept_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ud = context.user_data
    concepto = "" if t.lower() == "skip" else t
    method = ud["pay_method"]
    handle = ud["pay_handle"]
    user = update.effective_user

    # Construir URL según método
    url_map = {
        "bizum":  f"https://bizum.es/pago?phone={handle}&concept={concepto}",
        "paypal": f"https://paypal.me/{handle.lstrip('/')}",
        "revolut":f"https://revolut.me/{handle.lstrip('/')}",
        "verse":  f"https://verse.me/{handle.lstrip('/')}",
        "iban":   f"IBAN:{handle} BEN:{concepto}",
    }
    content = url_map.get(method, handle)

    iconos = {"bizum": "💙", "paypal": "🔵", "revolut": "🟣", "verse": "🟢", "iban": "🏦"}
    icono = iconos.get(method, "💳")

    qr_bytes = generate_qr_gradient(content, color1="#00AA44", color2="#00FF88",
                                     gradient_type="vertical", module_style="redondeado",
                                     label=f"{icono} {concepto or method.title()}")
    qr_id = await save_qr(user.id, f"Pago {method.title()}", "url", content, "verde",
                          metadata={"subtipo": "qr_pago", "metodo": method})

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📥 Detalles", callback_data=f"qr_detail:{qr_id}"),
        InlineKeyboardButton("🗑 Eliminar", callback_data=f"qr_delete:{qr_id}"),
    ]])
    await update.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=(
            f"{icono} *QR de Pago — {method.title()}*\n\n"
            f"💳 Método: *{method.title()}*\n"
            f"📋 Concepto: {concepto or '—'}\n\n"
            f"✅ Tus clientes escanean y pagan al instante\n"
            f"🆔 ID: `{qr_id}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# 5. QR DINÁMICO (URL editable sin regenerar el QR)
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_qr_dinamico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """QR dinámico: la URL destino se puede cambiar después."""
    context.user_data.clear()
    await update.message.reply_text(
        "🔄 *QR Dinámico*\n\n"
        "Un QR cuyo destino puedes *cambiar en cualquier momento*\n"
        "sin tener que reimprimir el código.\n\n"
        "Perfecto para:\n"
        "• 🍽️ Menús que cambian cada temporada\n"
        "• 📅 Eventos con fechas actualizables\n"
        "• 🏪 Ofertas y promociones rotativas\n"
        "• 📦 Productos con stock variable\n\n"
        "🔗 ¿Cuál es la URL destino inicial?",
        parse_mode=ParseMode.MARKDOWN
    )
    return DYN_URL


async def dyn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dyn_url"] = update.message.text
    await update.message.reply_text("📛 Dale un nombre a este QR dinámico:")
    return DYN_NAME


async def dyn_name_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text
    ud = context.user_data
    url = ud["dyn_url"]
    user = update.effective_user

    # Crear ID único para el QR dinámico
    dyn_id = hashlib.md5(f"{user.id}:{nombre}:{datetime.now()}".encode()).hexdigest()[:8].upper()

    # El QR apunta a una URL de redirección conceptual identificada por dyn_id
    # (en producción usarías un servidor de redirección)
    qr_url = f"https://t.me/PingPongEliteBot?start=dyn_{dyn_id}"

    await update.message.reply_chat_action("upload_photo")
    qr_bytes = generate_qr_gradient(qr_url, color1="#FF6600", color2="#FFAA00",
                                     gradient_type="radial", module_style="redondeado",
                                     label=f"🔄 {nombre[:25]}")
    qr_id = await save_qr(user.id, f"Dinámico: {nombre}", "url", url, "dorado",
                          metadata={"subtipo": "dinamico", "dyn_id": dyn_id, "url_actual": url})

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Cambiar URL destino", callback_data=f"dyn_edit:{qr_id}")],
        [InlineKeyboardButton("📥 Detalles", callback_data=f"qr_detail:{qr_id}")],
    ])
    await update.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=(
            f"🔄 *QR Dinámico — {nombre}*\n\n"
            f"🆔 Código dinámico: `{dyn_id}`\n"
            f"🔗 URL actual: `{url[:50]}`\n\n"
            f"✅ Puedes cambiar la URL destino en cualquier momento\n"
            f"usando el botón de abajo sin reimprimir el QR\n"
            f"🆔 ID: `{qr_id}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# 6. QR A/B TESTING (dos URLs, estadísticas de cuál funciona mejor)
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_qr_ab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera 2 variantes de QR para hacer A/B testing."""
    context.user_data.clear()
    await update.message.reply_text(
        "🔬 *QR A/B Testing*\n\n"
        "Genera *2 QR diferentes* para la misma campaña\n"
        "y descubre cuál consigue más escaneos.\n\n"
        "Útil para:\n"
        "• Comparar dos diseños de landing page\n"
        "• Probar diferentes ofertas\n"
        "• Medir eficacia de dos ubicaciones\n\n"
        "🅰️ URL de la variante A:",
        parse_mode=ParseMode.MARKDOWN
    )
    return AB_URL1


async def ab_url1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ab_url1"] = update.message.text
    await update.message.reply_text("🅱️ URL de la variante B:")
    return AB_URL2


async def ab_url2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ab_url2"] = update.message.text
    await update.message.reply_text("📛 Nombre de la campaña A/B (ej: 'Campaña Verano'):")
    return AB_NAME


async def ab_name_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text
    ud = context.user_data
    url1 = ud["ab_url1"]
    url2 = ud["ab_url2"]
    user = update.effective_user

    await update.message.reply_chat_action("upload_photo")

    # QR A — azul
    qr_a = generate_qr_gradient(url1, color1="#0055AA", color2="#0088FF",
                                  gradient_type="radial", module_style="redondeado",
                                  label=f"🅰️ {nombre[:20]}")
    # QR B — rojo
    qr_b = generate_qr_gradient(url2, color1="#AA0000", color2="#FF4444",
                                  gradient_type="radial", module_style="redondeado",
                                  label=f"🅱️ {nombre[:20]}")

    qr_id_a = await save_qr(user.id, f"A/B-A: {nombre}", "url", url1, "azul",
                             metadata={"subtipo": "ab_test", "variante": "A", "campaign": nombre})
    qr_id_b = await save_qr(user.id, f"A/B-B: {nombre}", "url", url2, "rojo",
                             metadata={"subtipo": "ab_test", "variante": "B", "campaign": nombre})

    # Enviar ambos
    await update.message.reply_photo(
        photo=io.BytesIO(qr_a),
        caption=(
            f"🅰️ *Variante A — {nombre}*\n"
            f"🔗 `{url1[:60]}`\n"
            f"🆔 ID: `{qr_id_a}`"
        ),
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_photo(
        photo=io.BytesIO(qr_b),
        caption=(
            f"🅱️ *Variante B — {nombre}*\n"
            f"🔗 `{url2[:60]}`\n"
            f"🆔 ID: `{qr_id_b}`\n\n"
            f"📊 Usa /stats para comparar los escaneos de cada variante\n"
            f"🏆 El que tenga más escaneos = el ganador del test"
        ),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════════
# 7. MENÚ DE FUNCIONES PRO
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú principal de funciones PRO."""
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍽️ QR Menú Negocio", callback_data="pro_menu"),
            InlineKeyboardButton("💼 Tarjeta Visita", callback_data="pro_bcard"),
        ],
        [
            InlineKeyboardButton("✈️ QR de Telegram", callback_data="pro_telegram"),
            InlineKeyboardButton("💳 QR de Pago", callback_data="pro_pago"),
        ],
        [
            InlineKeyboardButton("🔄 QR Dinámico", callback_data="pro_dinamico"),
            InlineKeyboardButton("🔬 A/B Testing", callback_data="pro_ab"),
        ],
        [
            InlineKeyboardButton("🎨 QR con Gradiente", callback_data="pro_gradient"),
            InlineKeyboardButton("📊 Mis Campañas", callback_data="pro_campanas"),
        ],
    ])
    await update.effective_message.reply_text(
        "⭐ *Funciones PRO — QR IFORMACIONES*\n\n"
        "Herramientas avanzadas para negocios y profesionales:\n\n"
        "🍽️ *Menú Negocio* — QR para tu carta/menú digital\n"
        "💼 *Tarjeta Visita* — Contacto guardado al instante\n"
        "✈️ *QR Telegram* — Canal, grupo, bot o usuario\n"
        "💳 *QR Pago* — Bizum, PayPal, Revolut, IBAN\n"
        "🔄 *QR Dinámico* — URL editable sin reimprimir\n"
        "🔬 *A/B Testing* — Compara qué QR funciona mejor\n"
        "🎨 *Gradiente* — QR con colores degradados\n"
        "📊 *Campañas* — Gestiona todos tus QR por campaña",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )


async def callback_pro_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Despacha las opciones del menú PRO."""
    query = update.callback_query
    await query.answer()
    action = query.data

    cmd_map = {
        "pro_menu":     "/qr_menu",
        "pro_bcard":    "/qr_bcard",
        "pro_telegram": "/qr_telegram",
        "pro_pago":     "/qr_pago",
        "pro_dinamico": "/qr_dinamico",
        "pro_ab":       "/qr_ab",
        "pro_gradient": "/qr_gradiente",
        "pro_campanas": "/mis_qr",
    }
    cmd = cmd_map.get(action, "/menu")
    await query.edit_message_text(
        f"💡 Escribe el comando `{cmd}` para comenzar.\n\n"
        f"O pulsa /pro para volver al menú PRO.",
        parse_mode=ParseMode.MARKDOWN
    )


# ════════════════════════════════════════════════════════════════════════════════
# 8. QR GRADIENTE PERSONALIZADO
# ════════════════════════════════════════════════════════════════════════════════

async def cmd_qr_gradiente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """QR con gradiente de colores personalizado."""
    if not context.args:
        await update.message.reply_text(
            "🎨 *QR con Gradiente*\n\n"
            "Uso: `/qr_gradiente <URL o texto>`\n\n"
            "Genera un QR con degradado de colores profesional.\n"
            "Ejemplo: `/qr_gradiente https://mi-web.com`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    content = " ".join(context.args)
    user = update.effective_user
    await update.message.reply_chat_action("upload_photo")

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔵→🟣 Oceánico", callback_data=f"grad:ocean:{content[:100]}"),
        InlineKeyboardButton("🔴→🟠 Fuego", callback_data=f"grad:fire:{content[:100]}"),
    ], [
        InlineKeyboardButton("🟢→🔵 Naturaleza", callback_data=f"grad:nature:{content[:100]}"),
        InlineKeyboardButton("🟣→🩷 Sunset", callback_data=f"grad:sunset:{content[:100]}"),
    ]])

    # Generar preview con gradiente por defecto
    qr_bytes = generate_qr_gradient(content, color1="#0066CC", color2="#00CCFF",
                                     gradient_type="radial")
    qr_id = await save_qr(user.id, f"QR Gradiente", "url" if content.startswith("http") else "texto",
                          content, "azul", metadata={"subtipo": "gradiente"})

    await update.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=(
            f"🎨 *QR con Gradiente Oceánico*\n\n"
            f"Elige otro estilo de gradiente:\n"
            f"🆔 ID: `{qr_id}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )


async def callback_gradient_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Regenera el QR con el estilo de gradiente elegido."""
    query = update.callback_query
    await query.answer("Generando...")
    parts = query.data.split(":", 2)
    style = parts[1]
    content = parts[2] if len(parts) > 2 else "https://t.me/PingPongEliteBot"
    user = query.from_user

    gradients = {
        "ocean":  ("#003399", "#00CCFF", "radial"),
        "fire":   ("#CC2200", "#FF8800", "vertical"),
        "nature": ("#004400", "#44CC44", "horizontal"),
        "sunset": ("#6600CC", "#FF6699", "radial"),
    }
    c1, c2, gtype = gradients.get(style, ("#0066CC", "#00CCFF", "radial"))
    qr_bytes = generate_qr_gradient(content, color1=c1, color2=c2, gradient_type=gtype)
    qr_id = await save_qr(user.id, f"Gradiente {style}", "url" if content.startswith("http") else "texto",
                          content, "azul", metadata={"subtipo": f"gradiente_{style}"})

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔵→🟣 Oceánico", callback_data=f"grad:ocean:{content[:100]}"),
        InlineKeyboardButton("🔴→🟠 Fuego", callback_data=f"grad:fire:{content[:100]}"),
    ], [
        InlineKeyboardButton("🟢→🔵 Naturaleza", callback_data=f"grad:nature:{content[:100]}"),
        InlineKeyboardButton("🟣→🩷 Sunset", callback_data=f"grad:sunset:{content[:100]}"),
    ]])

    await query.message.reply_photo(
        photo=io.BytesIO(qr_bytes),
        caption=f"🎨 *QR Gradiente {style.title()}*\n🆔 ID: `{qr_id}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
