#!/bin/bash
# Script de arranque rápido del bot
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta primero: bash install.sh"
    exit 1
fi

source venv/bin/activate
echo "🚀 Iniciando PingPongElite QR Bot..."
python bot.py
