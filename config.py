"""
Configuración central del Bot QR de Telegram - PingPongEliteBot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── TOKEN DEL BOT ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "5955970564:AAH9qdWUEGs1bc7V5va-KAF4OnyKUhOQXAg")
BOT_USERNAME = "PingPongEliteBot"

# ── BASE DE DATOS ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "qr_bot.db")

# ── DIRECTORIOS ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
QR_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "qr_images")

# ── LÍMITES ───────────────────────────────────────────────────────────────────
MAX_QR_PER_USER = 500          # Máximo de QRs por usuario
MAX_BATCH_SIZE = 10            # Máximo de QRs en batch
QR_DEFAULT_SIZE = 300          # Tamaño predeterminado en píxeles
QR_MAX_SIZE = 1000             # Tamaño máximo

# ── QR SETTINGS ───────────────────────────────────────────────────────────────
QR_DEFAULT_ERROR_CORRECTION = "H"   # L, M, Q, H (H = máxima corrección)
QR_DEFAULT_BORDER = 4               # Borde en módulos
QR_DEFAULT_BOX_SIZE = 10            # Tamaño de cada módulo

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
DAILY_REPORT_HOUR = 9           # Hora del reporte diario (9:00 AM)
DAILY_REPORT_MINUTE = 0
QR_EXPIRY_CHECK_MINUTES = 30    # Revisar QRs expirados cada 30 min
AUTO_CLEANUP_DAYS = 90          # Limpiar QRs sin uso > 90 días

# ── ESTILOS DE QR DISPONIBLES ─────────────────────────────────────────────────
QR_STYLES = {
    "clasico": {"fill_color": "black", "back_color": "white", "description": "🖤 Clásico B/N"},
    "azul":    {"fill_color": "#0066CC", "back_color": "white", "description": "🔵 Azul Moderno"},
    "rojo":    {"fill_color": "#CC0000", "back_color": "white", "description": "🔴 Rojo Vibrante"},
    "verde":   {"fill_color": "#006633", "back_color": "white", "description": "🟢 Verde Profesional"},
    "morado":  {"fill_color": "#6600CC", "back_color": "white", "description": "🟣 Morado Elegante"},
    "dorado":  {"fill_color": "#CC9900", "back_color": "#1a1a1a", "description": "✨ Dorado Premium"},
    "neon":    {"fill_color": "#00FF41", "back_color": "#0D0208", "description": "💚 Neon Matrix"},
    "ocean":   {"fill_color": "#003366", "back_color": "#E6F3FF", "description": "🌊 Ocean Blue"},
}

# ── TIPOS DE QR ───────────────────────────────────────────────────────────────
QR_TYPES = {
    "url":       "🔗 URL / Web",
    "texto":     "📝 Texto Plano",
    "wifi":      "📶 WiFi",
    "email":     "📧 Email",
    "sms":       "💬 SMS",
    "telefono":  "📞 Teléfono",
    "vcard":     "👤 Tarjeta de Contacto",
    "ubicacion": "📍 Ubicación GPS",
    "evento":    "📅 Evento de Calendario",
    "crypto":    "₿ Dirección Crypto",
}

# ── ADMIN ─────────────────────────────────────────────────────────────────────
# IDs de usuarios administradores del bot (añade tu Telegram ID aquí)
ADMIN_USER_IDS: list[int] = []

# ── MENSAJES ──────────────────────────────────────────────────────────────────
WELCOME_MSG = """
🔲 *¡Bienvenido a QR IFORMACIONES Bot!* 🤖

Tu asistente completo para todo lo relacionado con *códigos QR*.

Elige una opción del menú para comenzar 👇
"""

HELP_MSG = """
📚 **Comandos disponibles:**

**🔲 Generación de QR:**
/qr `<texto o url>` - QR rápido
/qr_url - QR de URL con opciones
/qr_wifi - QR para red WiFi
/qr_vcard - QR tarjeta de contacto
/qr_email - QR de email
/qr_sms - QR de SMS
/qr_ubicacion - QR de GPS
/qr_evento - QR evento de calendario
/qr_crypto - QR dirección crypto
/qr_batch - Generar múltiples QR

**📖 Lectura de QR:**
/leer - Envía una imagen con QR para decodificar

**🎨 Personalización:**
/estilos - Ver estilos disponibles
/mi_logo - Añadir logo a tus QR

**📊 Estadísticas:**
/stats - Mis estadísticas
/historial - Mis QR recientes
/top_qr - Mis QR más escaneados

**⚙️ Gestión:**
/mis_qr - Gestionar mis QR
/buscar - Buscar QR por nombre
/exportar - Exportar QR en ZIP

**🔔 Alertas:**
/alertas - Configurar alertas de escaneo
/recordatorios - Gestionar recordatorios
"""
