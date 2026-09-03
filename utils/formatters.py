"""
Formateadores de mensajes para Telegram con Markdown.
"""
from datetime import datetime
from typing import Dict, List, Optional
from config import QR_TYPES, QR_STYLES


def fmt_qr_list(qrs: List[Dict], page: int = 1, per_page: int = 10) -> str:
    """Formatea una lista de QR para mostrar en Telegram."""
    if not qrs:
        return "📭 No tienes códigos QR guardados todavía."

    lines = [f"📋 *Tus Códigos QR* (página {page}):\n"]
    for i, qr in enumerate(qrs[:per_page], 1):
        name = qr.get("name") or f"QR #{qr['id']}"
        qr_type = QR_TYPES.get(qr["qr_type"], qr["qr_type"])
        scans = qr.get("scan_count", 0)
        date = qr.get("created_at", "")[:10]
        active = "✅" if qr.get("is_active") else "❌"
        expires = " ⏳" if qr.get("expires_at") else ""

        lines.append(
            f"{active} `{qr['id']:04d}` *{name}*\n"
            f"   {qr_type} │ 👁 {scans} scans │ 📅 {date}{expires}"
        )

    return "\n\n".join(lines)


def fmt_qr_detail(qr: Dict) -> str:
    """Formatea los detalles de un QR individual."""
    name = qr.get("name") or f"QR #{qr['id']}"
    qr_type = QR_TYPES.get(qr["qr_type"], qr["qr_type"])
    style_desc = QR_STYLES.get(qr.get("style", "clasico"), {}).get("description", "Clásico")
    content = qr.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    expires = ""
    if qr.get("expires_at"):
        exp = datetime.fromisoformat(qr["expires_at"])
        remaining = exp - datetime.utcnow()
        if remaining.days > 0:
            expires = f"\n⏳ *Expira en:* {remaining.days} días"
        else:
            expires = "\n❌ *Expirado*"

    last_scan = ""
    if qr.get("last_scanned"):
        last_scan = f"\n🕐 *Último scan:* `{qr['last_scanned'][:16]}`"

    return (
        f"🔲 *{name}*\n\n"
        f"🆔 ID: `{qr['id']}`\n"
        f"📦 Tipo: {qr_type}\n"
        f"🎨 Estilo: {style_desc}\n"
        f"📅 Creado: `{qr.get('created_at', '')[:10]}`\n"
        f"👁 Escaneos: *{qr.get('scan_count', 0)}*"
        f"{last_scan}{expires}\n\n"
        f"📄 *Contenido:*\n`{content}`"
    )


def fmt_user_stats(stats: Dict, user_name: str) -> str:
    """Formatea el dashboard de estadísticas del usuario."""
    g = stats.get("general", {})
    by_type = stats.get("by_type", [])
    daily = stats.get("daily_scans", [])

    total_qr = g.get("total_qr") or 0
    total_scans = g.get("total_scans") or 0
    active_qr = g.get("active_qr") or 0

    # Tipos más usados
    type_lines = ""
    if by_type:
        type_lines = "\n\n📦 *Por tipo:*\n"
        for t in by_type[:5]:
            type_name = QR_TYPES.get(t["qr_type"], t["qr_type"])
            type_lines += f"  • {type_name}: *{t['count']}*\n"

    # Escaneos recientes
    scan_lines = ""
    if daily:
        scan_lines = "\n\n📈 *Scans (últimos 7 días):*\n"
        total_week = sum(d["scans"] for d in daily)
        for d in daily[:7]:
            bar = "█" * min(10, d["scans"])
            scan_lines += f"  `{d['day'][5:]}` {bar} *{d['scans']}*\n"
        scan_lines += f"  *Total semana: {total_week}*\n"

    return (
        f"📊 *Estadísticas de {user_name}*\n\n"
        f"🔲 QR totales: *{total_qr}*\n"
        f"✅ QR activos: *{active_qr}*\n"
        f"👁 Escaneos totales: *{total_scans}*"
        f"{type_lines}{scan_lines}"
    )


def fmt_global_stats(stats: Dict) -> str:
    """Formatea estadísticas globales (para admins)."""
    return (
        f"🌐 *Estadísticas Globales del Bot*\n\n"
        f"👥 Usuarios totales: *{stats.get('total_users', 0)}*\n"
        f"🔲 QR totales: *{stats.get('total_qr', 0)}*\n"
        f"👁 Escaneos totales: *{stats.get('total_scans') or 0}*\n"
        f"📅 Activos hoy: *{stats.get('active_today', 0)}*"
    )


def fmt_qr_decoded(decoded: Dict) -> str:
    """Formatea el resultado de decodificación de un QR."""
    icon = decoded.get("icon", "📄")
    label = decoded.get("label", "Desconocido")
    content = decoded.get("content", "")
    parsed = decoded.get("parsed", {})

    lines = [
        f"✅ *QR Detectado!*\n",
        f"{icon} *Tipo:* {label}\n",
    ]

    if parsed:
        lines.append("📋 *Detalles:*")
        for k, v in parsed.items():
            if v:
                lines.append(f"  • *{k.title()}:* `{v}`")
        lines.append("")

    lines.append(f"📄 *Contenido completo:*\n`{content[:1000]}`")

    return "\n".join(lines)


def fmt_styles_menu() -> str:
    """Formatea el menú de estilos disponibles."""
    lines = ["🎨 *Estilos de QR disponibles:*\n"]
    for key, style in QR_STYLES.items():
        lines.append(f"• `{key}` → {style['description']}")
    lines.append("\n💡 _Usa el botón de estilo al generar tu QR_")
    return "\n".join(lines)


def fmt_daily_report(stats: Dict, user_name: str, date: str) -> str:
    """Formatea el reporte diario automático."""
    g = stats.get("general", {})
    daily = stats.get("daily_scans", [])

    total_scans_today = 0
    if daily:
        today_data = [d for d in daily if d["day"] == date]
        total_scans_today = today_data[0]["scans"] if today_data else 0

    return (
        f"☀️ *Reporte Diario - {date}*\n"
        f"Hola {user_name}! Aquí tu resumen:\n\n"
        f"🔲 QR activos: *{g.get('active_qr') or 0}*\n"
        f"👁 Scans hoy: *{total_scans_today}*\n"
        f"📊 Scans totales: *{g.get('total_scans') or 0}*\n\n"
        f"_Usa /stats para ver estadísticas detalladas_"
    )
