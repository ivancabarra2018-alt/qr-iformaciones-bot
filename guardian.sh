#!/bin/bash
# ============================================================
# Bot QR — Guardián de reconexión automática tras reposo
# Se reinicia solo cuando el Mac despierta del sueño
# ============================================================

LOG="/Users/ASUS/.gemini/antigravity/scratch/qr_bot/data/guardian.log"
BOT_PY="/Users/ASUS/.gemini/antigravity/scratch/qr_bot/bot.py"
BOT_PYTHON="/Users/ASUS/.gemini/antigravity/scratch/qr_bot/venv/bin/python"
BOT_DIR="/Users/ASUS/.gemini/antigravity/scratch/qr_bot"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }

log "🟢 Guardián iniciado"

while true; do
    # Lanzar el bot
    log "▶️  Arrancando bot QR..."
    cd "$BOT_DIR" || exit 1
    "$BOT_PYTHON" "$BOT_PY" >> "$LOG" 2>&1
    EXIT_CODE=$?
    log "⚠️  Bot salió con código $EXIT_CODE — esperando 5s para reiniciar..."
    sleep 5
    # Esperar a que haya conexión a internet antes de reiniciar
    for i in $(seq 1 30); do
        if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
            log "✅ Internet disponible — reiniciando bot"
            break
        fi
        log "⏳ Sin internet, reintento $i/30..."
        sleep 3
    done
done
