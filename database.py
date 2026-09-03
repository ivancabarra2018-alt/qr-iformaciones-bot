"""
Capa de base de datos SQLite asíncrona para el Bot QR.
Gestiona usuarios, QR codes, estadísticas y configuraciones.
"""
import aiosqlite
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from config import DB_PATH


async def init_db():
    """Inicializa todas las tablas de la base de datos."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            -- Usuarios del bot
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                last_name   TEXT,
                joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_qr    INTEGER DEFAULT 0,
                is_blocked  INTEGER DEFAULT 0,
                settings    TEXT DEFAULT '{}'
            );

            -- Códigos QR generados
            CREATE TABLE IF NOT EXISTS qr_codes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                name            TEXT,
                qr_type         TEXT NOT NULL,
                content         TEXT NOT NULL,
                style           TEXT DEFAULT 'clasico',
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at      DATETIME,
                scan_count      INTEGER DEFAULT 0,
                last_scanned    DATETIME,
                is_active       INTEGER DEFAULT 1,
                metadata        TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Escaneos/uso de QR (tracking)
            CREATE TABLE IF NOT EXISTS qr_scans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                qr_id       INTEGER NOT NULL,
                scanned_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                source      TEXT DEFAULT 'telegram',
                FOREIGN KEY (qr_id) REFERENCES qr_codes(id)
            );

            -- Alertas configuradas por el usuario
            CREATE TABLE IF NOT EXISTS alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                qr_id           INTEGER,
                alert_type      TEXT NOT NULL,
                threshold       INTEGER,
                is_active       INTEGER DEFAULT 1,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                triggered_at    DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (qr_id) REFERENCES qr_codes(id)
            );

            -- Historial de reportes diarios enviados
            CREATE TABLE IF NOT EXISTS daily_reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                sent_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                report_data TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Colecciones de QR
            CREATE TABLE IF NOT EXISTS collections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                name        TEXT NOT NULL,
                description TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            -- Relación QR - Colección
            CREATE TABLE IF NOT EXISTS collection_items (
                collection_id INTEGER,
                qr_id         INTEGER,
                added_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (collection_id, qr_id),
                FOREIGN KEY (collection_id) REFERENCES collections(id),
                FOREIGN KEY (qr_id) REFERENCES qr_codes(id)
            );

            -- Índices para mejor rendimiento
            CREATE INDEX IF NOT EXISTS idx_qr_user ON qr_codes(user_id);
            CREATE INDEX IF NOT EXISTS idx_qr_active ON qr_codes(is_active);
            CREATE INDEX IF NOT EXISTS idx_scans_qr ON qr_scans(qr_id);
            CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
        """)
        await db.commit()


# ── USUARIOS ──────────────────────────────────────────────────────────────────

async def upsert_user(user_id: int, username: str, first_name: str, last_name: str = ""):
    """Registra o actualiza un usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name,
                last_seen  = CURRENT_TIMESTAMP
        """, (user_id, username or "", first_name or "", last_name or ""))
        await db.commit()


async def get_user(user_id: int) -> Optional[Dict]:
    """Obtiene los datos de un usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_users() -> List[Dict]:
    """Obtiene todos los usuarios activos."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_blocked = 0") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_user_settings(user_id: int) -> Dict:
    """Obtiene la configuración del usuario."""
    user = await get_user(user_id)
    if user and user["settings"]:
        return json.loads(user["settings"])
    return {}


async def update_user_settings(user_id: int, settings: Dict):
    """Actualiza la configuración del usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET settings = ? WHERE user_id = ?",
            (json.dumps(settings), user_id)
        )
        await db.commit()


# ── QR CODES ──────────────────────────────────────────────────────────────────

async def save_qr(
    user_id: int,
    name: str,
    qr_type: str,
    content: str,
    style: str = "clasico",
    expires_at: Optional[datetime] = None,
    metadata: Optional[Dict] = None
) -> int:
    """Guarda un QR generado y retorna su ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO qr_codes (user_id, name, qr_type, content, style, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, name, qr_type, content, style,
            expires_at.isoformat() if expires_at else None,
            json.dumps(metadata or {})
        ))
        qr_id = cursor.lastrowid
        await db.execute(
            "UPDATE users SET total_qr = total_qr + 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()
        return qr_id


async def get_qr(qr_id: int) -> Optional[Dict]:
    """Obtiene un QR por ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM qr_codes WHERE id = ?", (qr_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_qrs(user_id: int, limit: int = 20, offset: int = 0) -> List[Dict]:
    """Obtiene los QR de un usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM qr_codes
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_top_qrs(user_id: int, limit: int = 5) -> List[Dict]:
    """Obtiene los QR más escaneados de un usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM qr_codes
            WHERE user_id = ? AND is_active = 1
            ORDER BY scan_count DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def search_user_qrs(user_id: int, query: str) -> List[Dict]:
    """Busca QR del usuario por nombre o contenido."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM qr_codes
            WHERE user_id = ? AND is_active = 1
                AND (name LIKE ? OR content LIKE ?)
            ORDER BY created_at DESC LIMIT 20
        """, (user_id, f"%{query}%", f"%{query}%")) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def delete_qr(qr_id: int, user_id: int) -> bool:
    """Elimina (desactiva) un QR del usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE qr_codes SET is_active = 0 WHERE id = ? AND user_id = ?",
            (qr_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def register_scan(qr_id: int):
    """Registra un escaneo de QR."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO qr_scans (qr_id) VALUES (?)", (qr_id,)
        )
        await db.execute("""
            UPDATE qr_codes
            SET scan_count = scan_count + 1,
                last_scanned = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (qr_id,))
        await db.commit()


async def get_expired_qrs() -> List[Dict]:
    """Obtiene QR que han expirado."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM qr_codes
            WHERE is_active = 1
                AND expires_at IS NOT NULL
                AND expires_at <= CURRENT_TIMESTAMP
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def deactivate_expired_qrs():
    """Desactiva todos los QR expirados."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE qr_codes
            SET is_active = 0
            WHERE is_active = 1
                AND expires_at IS NOT NULL
                AND expires_at <= CURRENT_TIMESTAMP
        """)
        await db.commit()
        return cursor.rowcount


# ── ESTADÍSTICAS ──────────────────────────────────────────────────────────────

async def get_user_stats(user_id: int) -> Dict:
    """Obtiene estadísticas completas del usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Totales generales
        async with db.execute("""
            SELECT
                COUNT(*) as total_qr,
                SUM(scan_count) as total_scans,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_qr,
                MAX(created_at) as last_created
            FROM qr_codes WHERE user_id = ?
        """, (user_id,)) as c:
            general = dict(await c.fetchone())

        # QR por tipo
        async with db.execute("""
            SELECT qr_type, COUNT(*) as count
            FROM qr_codes WHERE user_id = ? AND is_active = 1
            GROUP BY qr_type ORDER BY count DESC
        """, (user_id,)) as c:
            by_type = [dict(r) for r in await c.fetchall()]

        # Escaneos por día (últimos 7 días)
        async with db.execute("""
            SELECT DATE(s.scanned_at) as day, COUNT(*) as scans
            FROM qr_scans s
            JOIN qr_codes q ON s.qr_id = q.id
            WHERE q.user_id = ?
                AND s.scanned_at >= DATE('now', '-7 days')
            GROUP BY DATE(s.scanned_at)
            ORDER BY day DESC
        """, (user_id,)) as c:
            daily_scans = [dict(r) for r in await c.fetchall()]

        return {
            "general": general,
            "by_type": by_type,
            "daily_scans": daily_scans,
        }


async def get_global_stats() -> Dict:
    """Estadísticas globales del bot (para admins)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM qr_codes) as total_qr,
                (SELECT SUM(scan_count) FROM qr_codes) as total_scans,
                (SELECT COUNT(*) FROM users WHERE last_seen >= DATE('now', '-1 day')) as active_today
        """) as c:
            return dict(await c.fetchone())


# ── ALERTAS ───────────────────────────────────────────────────────────────────

async def create_alert(user_id: int, qr_id: Optional[int], alert_type: str, threshold: int = 0) -> int:
    """Crea una alerta para el usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO alerts (user_id, qr_id, alert_type, threshold)
            VALUES (?, ?, ?, ?)
        """, (user_id, qr_id, alert_type, threshold))
        await db.commit()
        return cursor.lastrowid


async def get_user_alerts(user_id: int) -> List[Dict]:
    """Obtiene las alertas activas del usuario."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*, q.name as qr_name
            FROM alerts a
            LEFT JOIN qr_codes q ON a.qr_id = q.id
            WHERE a.user_id = ? AND a.is_active = 1
        """, (user_id,)) as c:
            return [dict(r) for r in await c.fetchall()]


async def get_triggered_alerts() -> List[Dict]:
    """Obtiene alertas que deben dispararse por scan_count."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*, q.scan_count, q.name as qr_name, q.user_id
            FROM alerts a
            JOIN qr_codes q ON a.qr_id = q.id
            WHERE a.is_active = 1
                AND a.alert_type = 'scan_threshold'
                AND q.scan_count >= a.threshold
                AND (a.triggered_at IS NULL OR a.triggered_at < DATE('now', '-1 day'))
        """) as c:
            return [dict(r) for r in await c.fetchall()]


async def mark_alert_triggered(alert_id: int):
    """Marca una alerta como disparada."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE alerts SET triggered_at = CURRENT_TIMESTAMP WHERE id = ?",
            (alert_id,)
        )
        await db.commit()
