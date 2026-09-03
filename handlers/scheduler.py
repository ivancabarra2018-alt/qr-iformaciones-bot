"""
Tareas automáticas programadas del bot:
- Reporte diario a las 9:00 AM
- Verificación de QR expirados cada 30 min
- Alertas de escaneos
- Limpieza de datos obsoletos
"""
import logging
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import Application
from telegram.constants import ParseMode

from database import (
    get_all_users, get_user_stats, deactivate_expired_qrs,
    get_triggered_alerts, mark_alert_triggered, get_expired_qrs,
    get_global_stats
)
from utils.formatters import fmt_daily_report
from config import DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE, ADMIN_USER_IDS

logger = logging.getLogger(__name__)


def setup_scheduler(app: Application) -> AsyncIOScheduler:
    """Configura y devuelve el scheduler con todas las tareas."""
    scheduler = AsyncIOScheduler(timezone="Europe/Madrid")

    # ── Reporte diario a las 9:00 AM ────────────────────────────────────────
    scheduler.add_job(
        _send_daily_reports,
        trigger=CronTrigger(hour=DAILY_REPORT_HOUR, minute=DAILY_REPORT_MINUTE),
        args=[app],
        id="daily_reports",
        name="Reportes Diarios",
        replace_existing=True,
    )

    # ── Verificar QR expirados cada 30 minutos ───────────────────────────────
    scheduler.add_job(
        _check_expired_qrs,
        trigger=IntervalTrigger(minutes=30),
        args=[app],
        id="check_expiry",
        name="Check QR Expirados",
        replace_existing=True,
    )

    # ── Verificar alertas de escaneo cada 15 minutos ─────────────────────────
    scheduler.add_job(
        _check_scan_alerts,
        trigger=IntervalTrigger(minutes=15),
        args=[app],
        id="scan_alerts",
        name="Alertas de Escaneo",
        replace_existing=True,
    )

    # ── Reporte semanal del bot a admins (lunes 8:00 AM) ─────────────────────
    scheduler.add_job(
        _send_admin_weekly_report,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        args=[app],
        id="admin_weekly",
        name="Reporte Semanal Admin",
        replace_existing=True,
    )

    logger.info("✅ Scheduler configurado con 4 tareas automáticas")
    return scheduler


async def _send_daily_reports(app: Application):
    """Envía reportes diarios a usuarios que tienen esta alerta activada."""
    logger.info("📊 Ejecutando tarea: Reportes diarios")
    import aiosqlite
    from config import DB_PATH

    today = date.today().isoformat()

    # Obtener usuarios con alerta de reporte diario
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT DISTINCT u.user_id, u.first_name
            FROM users u
            JOIN alerts a ON a.user_id = u.user_id
            WHERE a.alert_type = 'daily_summary'
                AND a.is_active = 1
                AND u.is_blocked = 0
        """) as cursor:
            users = [dict(r) for r in await cursor.fetchall()]

    sent = 0
    for user in users:
        try:
            stats = await get_user_stats(user["user_id"])
            text = fmt_daily_report(stats, user["first_name"] or "Usuario", today)
            await app.bot.send_message(
                user["user_id"],
                text,
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Error enviando reporte a {user['user_id']}: {e}")

    logger.info(f"✅ Reportes diarios enviados: {sent}/{len(users)}")


async def _check_expired_qrs(app: Application):
    """Notifica a usuarios sobre QR que han expirado."""
    logger.info("⏳ Verificando QR expirados...")

    # Obtener QR que acaban de expirar (antes de desactivarlos)
    expired = await get_expired_qrs()

    # Notificar a los usuarios
    for qr in expired[:50]:  # Máximo 50 notificaciones por ciclo
        try:
            name = qr.get("name") or f"QR #{qr['id']}"
            await app.bot.send_message(
                qr["user_id"],
                f"⏰ *Tu QR ha expirado:* `{name}`\n"
                f"🆔 ID: `{qr['id']}`\n\n"
                f"Usa /mis\\_qr para gestionar tus códigos.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

    # Desactivar todos los expirados
    count = await deactivate_expired_qrs()
    if count:
        logger.info(f"✅ {count} QR desactivados por expiración")


async def _check_scan_alerts(app: Application):
    """Verifica y dispara alertas por umbral de escaneos."""
    logger.info("🔔 Verificando alertas de escaneos...")

    alerts = await get_triggered_alerts()
    for alert in alerts:
        try:
            qr_name = alert.get("qr_name") or f"QR #{alert.get('qr_id', '?')}"
            scan_count = alert.get("scan_count", 0)
            threshold = alert.get("threshold", 0)

            await app.bot.send_message(
                alert["user_id"],
                f"🔔 *¡Alerta de escaneos!*\n\n"
                f"Tu QR *\"{qr_name}\"* ha alcanzado\n"
                f"**{scan_count} escaneos** (umbral: {threshold})! 🎉\n\n"
                f"Usa /stats para ver tus estadísticas.",
                parse_mode=ParseMode.MARKDOWN
            )
            await mark_alert_triggered(alert["id"])
        except Exception as e:
            logger.warning(f"Error enviando alerta {alert['id']}: {e}")

    if alerts:
        logger.info(f"✅ {len(alerts)} alertas de escaneo procesadas")


async def _send_admin_weekly_report(app: Application):
    """Envía reporte semanal a los administradores."""
    if not ADMIN_USER_IDS:
        return

    logger.info("📊 Enviando reporte semanal a admins...")
    stats = await get_global_stats()

    text = (
        f"📊 *Reporte Semanal del Bot*\n"
        f"🗓 Semana del {datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"👥 Usuarios: *{stats.get('total_users', 0)}*\n"
        f"🔲 QR totales: *{stats.get('total_qr', 0)}*\n"
        f"👁 Escaneos: *{stats.get('total_scans') or 0}*\n"
        f"📅 Activos hoy: *{stats.get('active_today', 0)}*"
    )

    for admin_id in ADMIN_USER_IDS:
        try:
            await app.bot.send_message(admin_id, text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Error enviando reporte a admin {admin_id}: {e}")
