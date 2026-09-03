"""
Handler de estadísticas y analytics del bot.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import get_user_stats, get_global_stats, create_alert, get_user_alerts
from utils.formatters import fmt_user_stats, fmt_global_stats
from config import ADMIN_USER_IDS


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el dashboard de estadísticas del usuario."""
    user = update.effective_user
    stats = await get_user_stats(user.id)
    name = user.first_name or "Usuario"
    text = fmt_user_stats(stats, name)

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Actualizar", callback_data="stats_refresh"),
        InlineKeyboardButton("🏆 Top QR", callback_data="stats_top"),
    ]])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def callback_stats_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actualiza las estadísticas en el mensaje existente."""
    query = update.callback_query
    await query.answer("Actualizando...")
    user = query.from_user
    stats = await get_user_stats(user.id)
    text = fmt_user_stats(stats, user.first_name or "Usuario")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Actualizar", callback_data="stats_refresh"),
        InlineKeyboardButton("🏆 Top QR", callback_data="stats_top"),
    ]])
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el historial reciente de QR generados."""
    from database import get_user_qrs
    from utils.formatters import fmt_qr_list
    user = update.effective_user
    qrs = await get_user_qrs(user.id, limit=10)
    text = fmt_qr_list(qrs, page=1)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── ALERTAS ───────────────────────────────────────────────────────────────────

async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú de configuración de alertas."""
    user = update.effective_user
    alerts = await get_user_alerts(user.id)

    if not alerts:
        alert_text = "📭 No tienes alertas configuradas."
    else:
        lines = ["🔔 *Tus alertas activas:*\n"]
        for a in alerts:
            atype = a.get("alert_type", "")
            qr_name = a.get("qr_name", f"QR #{a.get('qr_id', '?')}")
            threshold = a.get("threshold", 0)
            if atype == "scan_threshold":
                lines.append(f"• 📊 *{qr_name}* → Alerta al llegar a `{threshold}` scans")
            elif atype == "daily_summary":
                lines.append("• ☀️ Resumen diario activado")
        alert_text = "\n".join(lines)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Nueva alerta de escaneos", callback_data="alert_new_scan")],
        [InlineKeyboardButton("☀️ Activar reporte diario", callback_data="alert_daily")],
        [InlineKeyboardButton("🗑 Eliminar todas las alertas", callback_data="alert_clear")],
    ])
    await update.message.reply_text(
        alert_text + "\n\n⚙️ *Gestionar alertas:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )


async def callback_alert_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el reporte diario para el usuario."""
    query = update.callback_query
    await query.answer()
    await create_alert(query.from_user.id, None, "daily_summary", 0)
    await query.edit_message_text(
        "☀️ *Reporte diario activado!*\n"
        "Recibirás un resumen automático cada mañana a las 9:00 AM. ✅",
        parse_mode=ParseMode.MARKDOWN
    )


async def callback_alert_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina todas las alertas del usuario."""
    query = update.callback_query
    await query.answer()
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE alerts SET is_active = 0 WHERE user_id = ?",
            (query.from_user.id,)
        )
        await db.commit()
    await query.edit_message_text("✅ Todas las alertas eliminadas.")


# ── ADMIN ─────────────────────────────────────────────────────────────────────

async def cmd_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Estadísticas globales (solo admins)."""
    user = update.effective_user
    if ADMIN_USER_IDS and user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return
    stats = await get_global_stats()
    await update.message.reply_text(fmt_global_stats(stats), parse_mode=ParseMode.MARKDOWN)


async def cmd_difusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Difusión masiva a todos los usuarios del bot.
    Muestra preview + confirmación antes de enviar.
    Uso: /difusion <mensaje>
    """
    user = update.effective_user
    if ADMIN_USER_IDS and user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Solo el administrador puede enviar difusiones.")
        return

    if not context.args:
        await update.message.reply_text(
            "📢 *Difusión masiva*\n\n"
            "Envía un mensaje a *todos* los usuarios del bot.\n\n"
            "Uso: `/difusion <tu mensaje aquí>`\n\n"
            "Ejemplo:\n"
            "`/difusion 🎉 ¡Nueva función disponible! Prueba /qr\\_crypto`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    msg = " ".join(context.args)
    context.user_data["difusion_msg"] = msg

    from database import get_all_users
    users = await get_all_users()
    total = len(users)

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ Enviar a {total} usuarios", callback_data="difusion_confirm"),
        InlineKeyboardButton("❌ Cancelar", callback_data="difusion_cancel"),
    ]])

    preview = (
        f"📢 *Vista previa de tu difusión:*\n\n"
        f"─────────────────────\n"
        f"📢 *Mensaje del bot:*\n\n{msg}\n"
        f"─────────────────────\n\n"
        f"👥 Se enviará a *{total} usuario{'s' if total != 1 else ''}*\n\n"
        f"¿Confirmas el envío?"
    )
    await update.message.reply_text(preview, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def callback_difusion_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta el envío masivo tras confirmación."""
    query = update.callback_query
    await query.answer("📤 Enviando...")

    msg = context.user_data.get("difusion_msg", "")
    if not msg:
        await query.edit_message_text("❌ Error: usa /difusion de nuevo.")
        return

    from database import get_all_users
    users = await get_all_users()
    total = len(users)

    progress_msg = await query.edit_message_text(
        f"📤 *Enviando difusión...*\n\n⏳ 0 / {total} usuarios",
        parse_mode=ParseMode.MARKDOWN
    )

    sent = 0
    failed = 0

    for i, u in enumerate(users, 1):
        try:
            await context.bot.send_message(
                u["user_id"],
                f"📢 *Mensaje de QR IFORMACIONES:*\n\n{msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Exception:
            failed += 1

        if i % 10 == 0 or i == total:
            try:
                await progress_msg.edit_text(
                    f"📤 *Enviando difusión...*\n\n"
                    f"⏳ {i} / {total}\n"
                    f"✅ Enviados: {sent} │ ❌ Fallidos: {failed}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

    await progress_msg.edit_text(
        f"🎉 *¡Difusión completada!*\n\n"
        f"👥 Total: *{total}*\n"
        f"✅ Enviados: *{sent}*\n"
        f"❌ Fallidos (bloquearon el bot): *{failed}*\n\n"
        f"📝 _{msg[:100]}{'...' if len(msg) > 100 else ''}_",
        parse_mode=ParseMode.MARKDOWN
    )


async def callback_difusion_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la difusión."""
    query = update.callback_query
    await query.answer("Cancelado ✋")
    context.user_data.pop("difusion_msg", None)
    await query.edit_message_text("❌ *Difusión cancelada.*", parse_mode=ParseMode.MARKDOWN)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias de /difusion."""
    await cmd_difusion(update, context)
