"""
🤖 PingPongElite QR Bot - Bot principal de Telegram
Bot avanzado de QR con generación, lectura, tracking y automatización.

Comandos disponibles: /start, /menu, /help, /qr, /qr_url, /qr_wifi,
/qr_vcard, /qr_email, /qr_sms, /qr_ubicacion, /qr_crypto, /qr_batch,
/mis_qr, /top_qr, /buscar, /stats, /historial, /alertas, /estilos
"""
import logging
import os
import sys

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

# Asegurar que el directorio del bot esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    BOT_TOKEN, WELCOME_MSG, HELP_MSG,
    QR_OUTPUT_DIR, ASSETS_DIR
)
from database import init_db, upsert_user
from handlers.scheduler import setup_scheduler
from handlers.ai_chat import (
    cmd_chat, cmd_salir, handle_ai_message, callback_ai_clear
)

# Handlers de generación
from handlers.qr_generator import (
    cmd_qr_quick, cmd_qr_url, cmd_qr_wifi, cmd_qr_vcard,
    cmd_qr_email, cmd_qr_sms, cmd_qr_ubicacion, cmd_qr_crypto, cmd_qr_batch,
    cmd_mis_qr, cmd_top_qr, cmd_buscar,
    # Funciones de estado de conversación
    receive_general_content, receive_style, receive_module,
    receive_name, receive_expiry_and_generate,
    wifi_ssid, wifi_pass, wifi_sec,
    vcard_name, vcard_phone, vcard_email, vcard_company, vcard_url_and_generate,
    email_to, email_subject, email_body_and_generate,
    sms_phone, sms_message_and_generate,
    geo_lat, geo_lon, geo_label_and_generate,
    crypto_coin, crypto_addr, crypto_amount_and_generate,
    batch_generate,
    callback_qr_detail, callback_qr_delete, callback_qr_delete_confirm,
    callback_qr_cancel, callback_qr_regen,
    # Estados
    STATE_STYLE, STATE_MODULE, STATE_NAME, STATE_EXPIRY,
    WIFI_SSID, WIFI_PASS, WIFI_SEC,
    VCARD_NAME, VCARD_PHONE, VCARD_EMAIL, VCARD_COMPANY, VCARD_URL,
    EMAIL_TO, EMAIL_SUBJECT, EMAIL_BODY,
    SMS_PHONE, SMS_MESSAGE,
    GEO_LAT, GEO_LON, GEO_LABEL,
    CRYPTO_COIN, CRYPTO_ADDR, CRYPTO_AMOUNT,
    BATCH_LINES, GENERAL_CONTENT,
)

# Handlers de lectura
from handlers.qr_reader import (
    handle_photo_qr, handle_document_qr, callback_regen_from_read
)

# Handlers de analytics
from handlers.analytics import (
    cmd_stats, cmd_historial, cmd_alertas, cmd_admin_stats,
    cmd_broadcast, cmd_difusion,
    callback_stats_refresh, callback_alert_daily, callback_alert_clear,
    callback_difusion_confirm, callback_difusion_cancel
)
from utils.formatters import fmt_styles_menu

# Handlers PRO
from handlers.pro_features import (
    cmd_pro, cmd_qr_menu, cmd_qr_bcard, cmd_qr_telegram,
    cmd_qr_pago, cmd_qr_dinamico, cmd_qr_ab, cmd_qr_gradiente,
    # Conversation states
    MENU_NOMBRE, MENU_ITEMS,
    BCARD_NAME, BCARD_JOB, BCARD_PHONE, BCARD_EMAIL, BCARD_WEB, BCARD_SOCIAL,
    TG_TYPE, TG_LINK,
    PAY_METHOD, PAY_HANDLE, PAY_CONCEPT,
    DYN_URL, DYN_NAME,
    AB_URL1, AB_URL2, AB_NAME,
    # Handlers de pasos
    menu_nombre, menu_url_and_generate,
    bcard_name, bcard_job, bcard_phone, bcard_email, bcard_web, bcard_social_and_generate,
    tg_type, tg_link_and_generate,
    pay_method, pay_handle, pay_concept_and_generate,
    dyn_url, dyn_name_and_generate,
    ab_url1, ab_url2, ab_name_and_generate,
    # Callbacks
    callback_pro_menu, callback_gradient_style,
)

# ── Crear directorios necesarios ANTES del logging ───────────────────────────
os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "assets"), exist_ok=True)
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "data", "bot.log"),
            encoding="utf-8"
        )
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ── Middleware: registrar usuario ─────────────────────────────────────────────

async def _register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware global que registra/actualiza cada usuario."""
    user = update.effective_user
    if user:
        await upsert_user(user.id, user.username, user.first_name, user.last_name or "")


# ── Comandos principales ──────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bienvenida con menú completo PRO."""
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name, user.last_name or "")

    nombre = user.first_name or "👋"
    texto = (
        f"🔲 *QR IFORMACIONES* — Hola, {nombre}!\n\n"
        f"El bot más completo de Telegram para *generar, leer y gestionar* códigos QR.\n\n"
        f"🆓 *Básico:* URL, WiFi, Contacto, Email, SMS, GPS, Crypto\n"
        f"⭐ *PRO:* Menú negocio, Tarjeta visita, Pagos, Dinámico, A/B Test\n"
        f"📸 *Leer QR:* Envíame cualquier foto con un QR y lo decodifico\n"
        f"📊 *Stats:* Seguimiento de escaneos y reportes diarios\n\n"
        f"👇 *Elige una categoría:*"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ QR Básico",     callback_data="menu_generate"),
            InlineKeyboardButton("⭐ QR PRO",        callback_data="menu_pro"),
        ],
        [
            InlineKeyboardButton("📸 Leer un QR",    callback_data="menu_read"),
            InlineKeyboardButton("💳 QR de Pago",    callback_data="menu_pago"),
        ],
        [
            InlineKeyboardButton("📂 Mis QR",        callback_data="menu_myqr"),
            InlineKeyboardButton("📊 Estadísticas",  callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton("🔔 Alertas",       callback_data="menu_alerts"),
            InlineKeyboardButton("🎨 Estilos",       callback_data="menu_styles"),
        ],
        [InlineKeyboardButton("❓ Ayuda completa",   callback_data="menu_help")],
    ])
    await update.effective_message.reply_text(
        texto, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú principal."""
    await cmd_start(update, context)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la ayuda completa con todos los comandos."""
    help_text = (
        "📚 *Comandos de QR IFORMACIONES*\n\n"
        "─── 🆓 *QR BÁSICO* ───\n"
        "/qr `<texto>` — QR rápido al instante\n"
        "/qr\\_url — URL con estilo y expiración\n"
        "/qr\\_wifi — Red WiFi (escanear = conectar)\n"
        "/qr\\_vcard — Tarjeta de contacto (vCard)\n"
        "/qr\\_email — Email pre-rellenado\n"
        "/qr\\_sms — SMS pre-configurado\n"
        "/qr\\_ubicacion — Coordenadas GPS\n"
        "/qr\\_crypto — Wallet BTC/ETH/SOL/USDT/BNB\n"
        "/qr\\_batch — Hasta 10 QR a la vez en ZIP\n\n"
        "─── ⭐ *QR PRO (Negocios)* ───\n"
        "/pro — Menú de funciones PRO\n"
        "/qr\\_menu — Menú digital de restaurante\n"
        "/qr\\_bcard — Tarjeta visita digital PRO\n"
        "/qr\\_telegram — Canal, grupo o bot de Telegram\n"
        "/qr\\_pago — Bizum, PayPal, Revolut, IBAN\n"
        "/qr\\_dinamico — URL editable sin reimprimir\n"
        "/qr\\_gradiente — QR con degradado de colores\n"
        "/qr\\_ab — A/B Testing de dos variantes\n\n"
        "─── 📸 *LECTURA* ───\n"
        "Envíame cualquier foto con QR → decodifico automáticamente\n\n"
        "─── 📊 *GESTIÓN* ───\n"
        "/mis\\_qr — Gestionar mis QR\n"
        "/top\\_qr — Los más escaneados\n"
        "/buscar — Buscar por nombre/contenido\n"
        "/historial — Últimos generados\n"
        "/stats — Dashboard de estadísticas\n"
        "/alertas — Reporte diario y alertas\n"
        "/estilos — Ver los 8 estilos visuales\n\n"
        "─── 📢 *ADMIN* ───\n"
        "/difusion `<msg>` — Enviar a todos los usuarios"
    )
    await update.effective_message.reply_text(
        help_text, parse_mode=ParseMode.MARKDOWN
    )


async def cmd_estilos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los estilos de QR disponibles."""
    await update.message.reply_text(fmt_styles_menu(), parse_mode=ParseMode.MARKDOWN)



# ── Helpers reutilizables ─────────────────────────────────────────────────────

def _main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ QR Básico",    callback_data="menu_generate"),
         InlineKeyboardButton("⭐ QR PRO",       callback_data="menu_pro")],
        [InlineKeyboardButton("📸 Leer un QR",   callback_data="menu_read"),
         InlineKeyboardButton("💳 QR de Pago",   callback_data="menu_pago")],
        [InlineKeyboardButton("📂 Mis QR",       callback_data="menu_myqr"),
         InlineKeyboardButton("📊 Estadísticas", callback_data="menu_stats")],
        [InlineKeyboardButton("🔔 Alertas",      callback_data="menu_alerts"),
         InlineKeyboardButton("🎨 Estilos",      callback_data="menu_styles")],
        [InlineKeyboardButton("❓ Ayuda completa", callback_data="menu_help")],
    ])

def _main_text(nombre: str) -> str:
    return (
        f"🔲 *QR IFORMACIONES* — Hola, {nombre}!\n\n"
        "El bot más completo de Telegram para *generar, leer y gestionar* códigos QR.\n\n"
        "🆓 *Básico:* URL, WiFi, Contacto, Email, SMS, GPS, Crypto\n"
        "⭐ *PRO:* Menú negocio, Tarjeta visita, Pagos, Dinámico, A/B Test\n"
        "📸 *Leer QR:* Envíame cualquier foto y lo decodifico\n"
        "📊 *Stats:* Seguimiento de escaneos y reportes diarios\n\n"
        "👇 *Elige una categoría:*"
    )

def _back_kb(back_to: str = "menu_back"):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Menú principal", callback_data=back_to)
    ]])


# ── Callback del menú principal ───────────────────────────────────────────────

async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los botones del menú principal con navegación correcta."""
    query = update.callback_query
    await query.answer()
    action = query.data

    # ── VOLVER AL INICIO (siempre reconstruye el menú PRO nuevo) ─────────────
    if action == "menu_back":
        nombre = query.from_user.first_name or "👋"
        await query.edit_message_text(
            _main_text(nombre), parse_mode=ParseMode.MARKDOWN,
            reply_markup=_main_keyboard()
        )

    # ── QR BÁSICO ─────────────────────────────────────────────────────────────
    elif action == "menu_generate":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 URL personalizada", callback_data="gen_url"),
             InlineKeyboardButton("📶 WiFi",             callback_data="gen_wifi")],
            [InlineKeyboardButton("👤 Tarjeta contacto", callback_data="gen_vcard"),
             InlineKeyboardButton("📧 Email",            callback_data="gen_email")],
            [InlineKeyboardButton("💬 SMS",              callback_data="gen_sms"),
             InlineKeyboardButton("📍 Ubicación GPS",    callback_data="gen_geo")],
            [InlineKeyboardButton("₿ Crypto wallet",     callback_data="gen_crypto"),
             InlineKeyboardButton("📦 Batch ZIP",        callback_data="gen_batch")],
            [InlineKeyboardButton("⬅️ Menú principal", callback_data="menu_back")],
        ])
        await query.edit_message_text(
            "⚡ *QR Básico — Elige el tipo:*\n\n"
            "🔗 URL · 📶 WiFi · 👤 Contacto · 📧 Email\n"
            "💬 SMS · 📍 GPS · ₿ Crypto · 📦 Batch ZIP",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )

    # ── QR PRO ────────────────────────────────────────────────────────────────
    elif action == "menu_pro":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🍽️ Menú negocio",  callback_data="gen_menu"),
             InlineKeyboardButton("💼 Tarjeta visita", callback_data="gen_bcard")],
            [InlineKeyboardButton("✈️ QR Telegram",   callback_data="gen_telegram"),
             InlineKeyboardButton("💳 QR de Pago",    callback_data="gen_pago")],
            [InlineKeyboardButton("🔄 QR Dinámico",   callback_data="gen_dinamico"),
             InlineKeyboardButton("🔬 A/B Testing",   callback_data="gen_ab")],
            [InlineKeyboardButton("🎨 QR Gradiente",  callback_data="gen_gradiente")],
            [InlineKeyboardButton("⬅️ Menú principal", callback_data="menu_back")],
        ])
        await query.edit_message_text(
            "⭐ *QR PRO — Funciones para negocios:*\n\n"
            "🍽️ Menú negocio · 💼 Tarjeta visita\n"
            "✈️ QR Telegram · 💳 Pagos (Bizum/PayPal)\n"
            "🔄 QR Dinámico · 🔬 A/B Test · 🎨 Gradiente",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )

    # ── LEER QR ───────────────────────────────────────────────────────────────
    elif action == "menu_read":
        await query.edit_message_text(
            "📸 *Leer / Decodificar QR*\n\n"
            "✅ *Envíame una foto directamente* con un QR\n"
            "y lo decodificaré automáticamente.\n\n"
            "Funciona con:\n"
            "• Fotos tomadas con cámara\n"
            "• Capturas de pantalla\n"
            "• Imágenes guardadas\n"
            "• Documentos de imagen\n\n"
            "📤 _Solo manda la foto, sin escribir nada más_",
            parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb()
        )

    # ── QR DE PAGO ────────────────────────────────────────────────────────────
    elif action == "menu_pago":
        await query.edit_message_text(
            "💳 *QR de Pago*\n\n"
            "Genera un QR para cobrar al instante:\n\n"
            "💙 *Bizum* — Número de teléfono\n"
            "🔵 *PayPal* — Link paypal.me/tu\\_nombre\n"
            "🟣 *Revolut* — Link revolut.me/tu\\_nombre\n"
            "🟢 *Verse* — Link o teléfono\n"
            "🏦 *IBAN* — Número de cuenta bancaria\n\n"
            "Escribe `/qr_pago` para comenzar 👇",
            parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb()
        )

    # ── MIS QR ────────────────────────────────────────────────────────────────
    elif action == "menu_myqr":
        from database import get_user_qrs
        from utils.formatters import fmt_qr_list
        qrs = await get_user_qrs(query.from_user.id, limit=10)
        text = (fmt_qr_list(qrs) if qrs else
                "📂 *Mis QR*\n\nAún no tienes QR generados.\n\n"
                "Usa ⚡ *QR Básico* o ⭐ *QR PRO* para crear tu primero.")
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb()
        )

    # ── ESTADÍSTICAS ──────────────────────────────────────────────────────────
    elif action == "menu_stats":
        from database import get_user_stats
        from utils.formatters import fmt_user_stats
        stats = await get_user_stats(query.from_user.id)
        text = fmt_user_stats(stats, query.from_user.first_name or "Usuario")
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Refrescar", callback_data="menu_stats"),
                InlineKeyboardButton("⬅️ Menú principal", callback_data="menu_back"),
            ]])
        )

    # ── ALERTAS ───────────────────────────────────────────────────────────────
    elif action == "menu_alerts":
        from database import get_user_alerts
        alerts = await get_user_alerts(query.from_user.id)
        n = len(alerts)
        estado = "✅ Reporte diario activado." if n > 0 else "❌ Sin alertas activas."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("☀️ Activar reporte diario (9 AM)", callback_data="alert_daily")],
            [InlineKeyboardButton("🗑 Eliminar todas las alertas",    callback_data="alert_clear")],
            [InlineKeyboardButton("⬅️ Menú principal", callback_data="menu_back")],
        ])
        await query.edit_message_text(
            f"🔔 *Alertas automáticas*\n\n{estado}\n\n"
            "• ☀️ Reporte diario a las 9:00 AM\n"
            "• 📊 Aviso al superar umbral de escaneos",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )

    # ── ESTILOS ───────────────────────────────────────────────────────────────
    elif action == "menu_styles":
        await query.edit_message_text(
            fmt_styles_menu(), parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb()
        )

    # ── AYUDA ─────────────────────────────────────────────────────────────────
    elif action == "menu_help":
        help_text = (
            "📚 *Todos los comandos*\n\n"
            "─── ⚡ *QR BÁSICO* ───\n"
            "`/qr` `<texto>` — QR instantáneo\n"
            "`/qr_url` — URL con estilo + expiración\n"
            "`/qr_wifi` — WiFi (escanear = conectar)\n"
            "`/qr_vcard` — Tarjeta de contacto\n"
            "`/qr_email` — Email pre-rellenado\n"
            "`/qr_sms` — SMS pre-configurado\n"
            "`/qr_ubicacion` — Coordenadas GPS\n"
            "`/qr_crypto` — BTC/ETH/SOL/USDT/BNB\n"
            "`/qr_batch` — Hasta 10 QR en ZIP\n\n"
            "─── ⭐ *QR PRO* ───\n"
            "`/pro` · `/qr_menu` · `/qr_bcard`\n"
            "`/qr_telegram` · `/qr_pago`\n"
            "`/qr_dinamico` · `/qr_gradiente` · `/qr_ab`\n\n"
            "─── 📊 *GESTIÓN* ───\n"
            "`/mis_qr` · `/stats` · `/historial`\n"
            "`/alertas` · `/top_qr` · `/buscar`\n\n"
            "📸 *Envía una foto con QR para leerlo*"
        )
        await query.edit_message_text(
            help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=_back_kb()
        )

    # ── GEN_* — redirige al comando correcto ──────────────────────────────────
    elif action.startswith("gen_"):
        basicos = {"gen_url","gen_wifi","gen_vcard","gen_email","gen_sms","gen_geo","gen_crypto","gen_batch"}
        gen_map = {
            "gen_url":       ("/qr_url",      "🔗 URL personalizada"),
            "gen_wifi":      ("/qr_wifi",     "📶 Red WiFi"),
            "gen_vcard":     ("/qr_vcard",    "👤 Tarjeta de contacto"),
            "gen_email":     ("/qr_email",    "📧 Email pre-rellenado"),
            "gen_sms":       ("/qr_sms",      "💬 SMS pre-configurado"),
            "gen_geo":       ("/qr_ubicacion","📍 Ubicación GPS"),
            "gen_crypto":    ("/qr_crypto",   "₿ Wallet crypto"),
            "gen_batch":     ("/qr_batch",    "📦 Batch hasta 10 QR"),
            "gen_menu":      ("/qr_menu",     "🍽️ Menú digital negocio"),
            "gen_bcard":     ("/qr_bcard",    "💼 Tarjeta visita digital"),
            "gen_telegram":  ("/qr_telegram", "✈️ Canal/grupo/bot Telegram"),
            "gen_pago":      ("/qr_pago",     "💳 Pago Bizum/PayPal/Revolut"),
            "gen_dinamico":  ("/qr_dinamico", "🔄 QR Dinámico editable"),
            "gen_ab":        ("/qr_ab",       "🔬 A/B Testing"),
            "gen_gradiente": ("/qr_gradiente","🎨 QR con gradiente de color"),
        }
        cmd, desc = gen_map.get(action, ("/menu", "Inicio"))
        volver = "menu_generate" if action in basicos else "menu_pro"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Volver", callback_data=volver),
            InlineKeyboardButton("🏠 Inicio",  callback_data="menu_back"),
        ]])
        await query.edit_message_text(
            f"✅ *{desc}*\n\n"
            f"Escribe `{cmd}` y pulsa enviar ▶️\n\n"
            f"_El bot te guiará paso a paso_",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )


async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja comandos desconocidos."""
    await update.message.reply_text(
        "❓ Comando no reconocido. Usa /menu o /help para ver las opciones disponibles."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores del bot."""
    logger.error(f"Error: {context.error}", exc_info=True)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Ocurrió un error inesperado. Por favor intenta de nuevo."
            )
        except Exception:
            pass


# ── Construcción de la aplicación ─────────────────────────────────────────────

def build_app() -> Application:
    """Construye la aplicación con todos los handlers."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ── Middleware global
    app.add_handler(MessageHandler(filters.ALL, _register_user), group=-1)

    # ── Comandos simples
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("estilos", cmd_estilos))
    app.add_handler(CommandHandler("mis_qr", cmd_mis_qr))
    app.add_handler(CommandHandler("top_qr", cmd_top_qr))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("historial", cmd_historial))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(CommandHandler("admin", cmd_admin_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("difusion", cmd_difusion))
    app.add_handler(CommandHandler("qr", cmd_qr_quick))

    # ── Comandos PRO ─────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("pro",          cmd_pro))
    app.add_handler(CommandHandler("qr_menu",      cmd_qr_menu))
    app.add_handler(CommandHandler("qr_bcard",     cmd_qr_bcard))
    app.add_handler(CommandHandler("qr_telegram",  cmd_qr_telegram))
    app.add_handler(CommandHandler("qr_pago",      cmd_qr_pago))
    app.add_handler(CommandHandler("qr_dinamico",  cmd_qr_dinamico))
    app.add_handler(CommandHandler("qr_ab",        cmd_qr_ab))
    app.add_handler(CommandHandler("qr_gradiente", cmd_qr_gradiente))

    # ── ConversationHandlers para flujos de QR ──────────────────────────────

    # URL con personalización completa
    conv_url = ConversationHandler(
        entry_points=[CommandHandler("qr_url", cmd_qr_url)],
        states={
            GENERAL_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_general_content)],
            STATE_STYLE:     [CallbackQueryHandler(receive_style, pattern=r"^style:")],
            STATE_MODULE:    [CallbackQueryHandler(receive_module, pattern=r"^module:")],
            STATE_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            STATE_EXPIRY:    [CallbackQueryHandler(receive_expiry_and_generate, pattern=r"^expiry:")],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
        per_message=False,
    )
    app.add_handler(conv_url)

    # WiFi
    conv_wifi = ConversationHandler(
        entry_points=[CommandHandler("qr_wifi", cmd_qr_wifi)],
        states={
            WIFI_SSID: [MessageHandler(filters.TEXT & ~filters.COMMAND, wifi_ssid)],
            WIFI_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, wifi_pass)],
            WIFI_SEC:  [CallbackQueryHandler(wifi_sec, pattern=r"^wifi_sec:")],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    )
    app.add_handler(conv_wifi)

    # vCard
    conv_vcard = ConversationHandler(
        entry_points=[CommandHandler("qr_vcard", cmd_qr_vcard)],
        states={
            VCARD_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, vcard_name)],
            VCARD_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, vcard_phone)],
            VCARD_EMAIL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, vcard_email)],
            VCARD_COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, vcard_company)],
            VCARD_URL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, vcard_url_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    )
    app.add_handler(conv_vcard)

    # Email
    conv_email = ConversationHandler(
        entry_points=[CommandHandler("qr_email", cmd_qr_email)],
        states={
            EMAIL_TO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, email_to)],
            EMAIL_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, email_subject)],
            EMAIL_BODY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, email_body_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    )
    app.add_handler(conv_email)

    # SMS
    conv_sms = ConversationHandler(
        entry_points=[CommandHandler("qr_sms", cmd_qr_sms)],
        states={
            SMS_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, sms_phone)],
            SMS_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sms_message_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    )
    app.add_handler(conv_sms)

    # GPS / Ubicación
    conv_geo = ConversationHandler(
        entry_points=[CommandHandler("qr_ubicacion", cmd_qr_ubicacion)],
        states={
            GEO_LAT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, geo_lat)],
            GEO_LON:   [MessageHandler(filters.TEXT & ~filters.COMMAND, geo_lon)],
            GEO_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, geo_label_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    )
    app.add_handler(conv_geo)

    # Crypto
    conv_crypto = ConversationHandler(
        entry_points=[CommandHandler("qr_crypto", cmd_qr_crypto)],
        states={
            CRYPTO_COIN:   [CallbackQueryHandler(crypto_coin, pattern=r"^crypto_coin:")],
            CRYPTO_ADDR:   [MessageHandler(filters.TEXT & ~filters.COMMAND, crypto_addr)],
            CRYPTO_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, crypto_amount_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    )
    app.add_handler(conv_crypto)

    # Batch
    conv_batch = ConversationHandler(
        entry_points=[CommandHandler("qr_batch", cmd_qr_batch)],
        states={
            BATCH_LINES: [MessageHandler(filters.TEXT & ~filters.COMMAND, batch_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    )
    app.add_handler(conv_batch)

    # ── ConversationHandlers PRO ──────────────────────────────────────────────

    # Menú de restaurante
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("qr_menu", cmd_qr_menu)],
        states={
            MENU_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_nombre)],
            MENU_ITEMS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_url_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    ))

    # Tarjeta de visita digital
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("qr_bcard", cmd_qr_bcard)],
        states={
            BCARD_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, bcard_name)],
            BCARD_JOB:   [MessageHandler(filters.TEXT & ~filters.COMMAND, bcard_job)],
            BCARD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bcard_phone)],
            BCARD_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bcard_email)],
            BCARD_WEB:   [MessageHandler(filters.TEXT & ~filters.COMMAND, bcard_web)],
            BCARD_SOCIAL:[MessageHandler(filters.TEXT & ~filters.COMMAND, bcard_social_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    ))

    # QR de Telegram
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("qr_telegram", cmd_qr_telegram)],
        states={
            TG_TYPE: [CallbackQueryHandler(tg_type, pattern=r"^tg_type:")],
            TG_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, tg_link_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    ))

    # QR de pago
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("qr_pago", cmd_qr_pago)],
        states={
            PAY_METHOD:  [CallbackQueryHandler(pay_method, pattern=r"^pay:")],
            PAY_HANDLE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_handle)],
            PAY_CONCEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_concept_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    ))

    # QR dinámico
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("qr_dinamico", cmd_qr_dinamico)],
        states={
            DYN_URL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, dyn_url)],
            DYN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, dyn_name_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    ))

    # A/B Testing
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("qr_ab", cmd_qr_ab)],
        states={
            AB_URL1: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab_url1)],
            AB_URL2: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab_url2)],
            AB_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab_name_and_generate)],
        },
        fallbacks=[CommandHandler("menu", cmd_menu)],
    ))

    # ── Lectura automática de QR desde imágenes ──────────────────────────────
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_qr))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document_qr))

    # ── Callbacks de botones inline ──────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_menu, pattern=r"^menu_|^gen_"))
    app.add_handler(CallbackQueryHandler(callback_qr_detail, pattern=r"^qr_detail:"))
    app.add_handler(CallbackQueryHandler(callback_qr_delete, pattern=r"^qr_delete:\d+$"))
    app.add_handler(CallbackQueryHandler(callback_qr_delete_confirm, pattern=r"^qr_delete_confirm:"))
    app.add_handler(CallbackQueryHandler(callback_qr_cancel, pattern=r"^qr_cancel"))
    app.add_handler(CallbackQueryHandler(callback_qr_regen, pattern=r"^qr_regen:"))
    app.add_handler(CallbackQueryHandler(callback_stats_refresh, pattern=r"^stats_refresh"))
    app.add_handler(CallbackQueryHandler(callback_alert_daily, pattern=r"^alert_daily"))
    app.add_handler(CallbackQueryHandler(callback_alert_clear, pattern=r"^alert_clear"))
    app.add_handler(CallbackQueryHandler(callback_difusion_confirm, pattern=r"^difusion_confirm"))
    app.add_handler(CallbackQueryHandler(callback_difusion_cancel, pattern=r"^difusion_cancel"))
    # Callbacks PRO
    app.add_handler(CallbackQueryHandler(callback_pro_menu,      pattern=r"^pro_"))
    app.add_handler(CallbackQueryHandler(callback_gradient_style,pattern=r"^grad:"))
    app.add_handler(CallbackQueryHandler(callback_regen_from_read, pattern=r"^regen_from_read:"))
    # Callbacks IA
    app.add_handler(CallbackQueryHandler(callback_ai_clear, pattern=r"^ai_clear"))

    async def _cb_ai_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data["ai_mode"] = True
        context.user_data["ai_history"] = []
        await query.edit_message_text(
            "🤖 *Modo IA activado*\n\n"
            "Escríbeme cualquier pregunta 👇\n"
            "_/salir para volver al menú QR_",
            parse_mode="Markdown"
        )
    app.add_handler(CallbackQueryHandler(_cb_ai_activate, pattern=r"^ai_activate"))

    # ── IA Chat ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("chat",  cmd_chat))
    app.add_handler(CommandHandler("ia",    cmd_chat))
    app.add_handler(CommandHandler("salir", cmd_salir))


    # Handler global de texto para modo IA (actúa solo cuando ai_mode=True)
    async def _global_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        handled = await handle_ai_message(update, context)
        if not handled:
            # Si no hay acción pendiente y no está en modo IA, sugerir el chat
            await update.message.reply_text(
                "💡 Escribe un comando o usa el menú.\n"
                "🤖 Para chatear con IA escribe /chat",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menú", callback_data="menu_back"),
                    InlineKeyboardButton("🤖 Activar IA", callback_data="ai_activate"),
                ]])
            )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _global_text_handler))

    # ── Comandos desconocidos ────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    # ── Error handler ────────────────────────────────────────────────────────
    app.add_error_handler(error_handler)

    return app


async def set_bot_commands(app: Application):
    """Registra los comandos en el menú de Telegram."""
    commands = [
        # ── Básicos ───────────────────────────────────────────────────────────
        BotCommand("start",        "🚀 Inicio / Menú principal"),
        BotCommand("pro",          "⭐ Funciones PRO para negocios"),
        BotCommand("help",         "❓ Ayuda completa"),
        # ── QR Básicos ────────────────────────────────────────────────────────
        BotCommand("qr",           "⚡ QR rápido desde texto o URL"),
        BotCommand("qr_url",       "🔗 QR de URL con diseño personalizado"),
        BotCommand("qr_wifi",      "📶 QR de red WiFi"),
        BotCommand("qr_vcard",     "👤 QR tarjeta de contacto (vCard)"),
        BotCommand("qr_email",     "📧 QR de email pre-rellenado"),
        BotCommand("qr_sms",       "💬 QR de SMS"),
        BotCommand("qr_ubicacion", "📍 QR de ubicación GPS"),
        BotCommand("qr_crypto",    "₿ QR wallet crypto (BTC/ETH/SOL...)"),
        BotCommand("qr_batch",     "📦 Hasta 10 QR a la vez en ZIP"),
        # ── QR PRO ────────────────────────────────────────────────────────────
        BotCommand("qr_menu",      "🍽️ QR menú digital para restaurante"),
        BotCommand("qr_bcard",     "💼 QR tarjeta de visita digital PRO"),
        BotCommand("qr_telegram",  "✈️ QR de canal, grupo o bot de Telegram"),
        BotCommand("qr_pago",      "💳 QR de pago (Bizum, PayPal, Revolut...)"),
        BotCommand("qr_dinamico",  "🔄 QR dinámico (URL editable sin reimprimir)"),
        BotCommand("qr_gradiente", "🎨 QR con colores en gradiente"),
        BotCommand("qr_ab",        "🔬 A/B Testing con dos QR para comparar"),
        # ── Gestión ───────────────────────────────────────────────────────────
        BotCommand("mis_qr",       "📂 Ver y gestionar todos mis QR"),
        BotCommand("top_qr",       "🏆 Mis QR más escaneados"),
        BotCommand("buscar",       "🔍 Buscar QR por nombre o contenido"),
        BotCommand("historial",    "🕐 Historial reciente de QR"),
        # ── Analytics ─────────────────────────────────────────────────────────
        BotCommand("stats",        "📊 Dashboard de estadísticas"),
        BotCommand("alertas",      "🔔 Alertas automáticas y reporte diario"),
        BotCommand("estilos",      "🎨 Ver los 8 estilos visuales disponibles"),
        # ── Admin ─────────────────────────────────────────────────────────────
        BotCommand("difusion",     "📢 Difusión masiva a todos los usuarios"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info(f"✅ {len(commands)} comandos registrados en Telegram")


# ── Main ──────────────────────────────────────────────────────────────────────

def _launch_caffeinate():
    """Lanza caffeinate en segundo plano para evitar que el Mac duerma."""
    import subprocess
    try:
        proc = subprocess.Popen(
            ["/usr/bin/caffeinate", "-si"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info(f"☕ caffeinate activo (PID {proc.pid}) — Mac no dormirá")
        return proc
    except Exception as e:
        logger.warning(f"⚠️ No se pudo iniciar caffeinate: {e}")
        return None


async def keep_alive_pinger():
    """Envía pings periódicos para evitar que Render hiberne el bot."""
    import urllib.request
    urls = [
        "https://qr-iformaciones-bot.onrender.com/health",
        "https://ben-informante-pdf-bot.onrender.com/health"
    ]
    await asyncio.sleep(45)
    while True:
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AntiSleep/1.0)"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    pass
            except Exception as e:
                logger.debug(f"KeepAlive ping error: {e}")
        await asyncio.sleep(480)  # Ping cada 8 minutos


async def health_server():
    """Servidor HTTP mínimo para el health-check de Render."""
    from aiohttp import web
    port = int(os.environ.get("PORT", 8080))

    async def handle(_request):
        return web.Response(text="OK — QR Bot activo ✅")

    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Health server en puerto {port}")
    # Iniciar ping continuo entre bots para evitar reposo
    asyncio.create_task(keep_alive_pinger())





def main():
    """Punto de entrada principal."""
    import asyncio

    # Crear directorios necesarios
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    os.makedirs(QR_OUTPUT_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # Evitar que el Mac entre en reposo mientras el bot está activo
    caff_proc = _launch_caffeinate()

    logger.info("🚀 Iniciando PingPongElite QR Bot...")
    logger.info(f"📁 Directorio: {os.path.dirname(__file__)}")

    async def startup():
        await init_db()
        logger.info("✅ Base de datos inicializada")

        # Health check HTTP server (necesario para Render web_service)
        try:
            await health_server()
        except Exception as e:
            logger.warning(f"⚠️ Health server no disponible: {e}")

        app = build_app()
        await app.initialize()
        await set_bot_commands(app)

        scheduler = setup_scheduler(app)
        scheduler.start()
        logger.info("✅ Scheduler iniciado")

        logger.info("✅ Bot activo y escuchando...")
        logger.info("👉 Abre @PingPongEliteBot en Telegram para probarlo")

        await app.start()
        await app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        logger.info("🟢 Bot activo. Ctrl+C para detener.")

        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            logger.info("🛑 Deteniendo bot...")
            scheduler.shutdown(wait=False)
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    try:
        asyncio.run(startup())
    except KeyboardInterrupt:
        logger.info("🛑 Bot detenido manualmente")
    finally:
        if caff_proc:
            caff_proc.terminate()
            logger.info("☕ caffeinate detenido")


if __name__ == "__main__":
    main()
