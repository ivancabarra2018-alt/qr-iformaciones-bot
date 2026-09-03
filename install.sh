#!/bin/bash
# Script de instalación y arranque del QR Bot
set -e

echo "🤖 Instalando PingPongElite QR Bot..."
echo "======================================"

# Verificar Python 3.9+
python3 -c "import sys; assert sys.version_info >= (3,9), 'Se requiere Python 3.9+'" || {
    echo "❌ Se requiere Python 3.9 o superior"
    exit 1
}

# Instalar Homebrew dependencies en macOS (para zbar)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📦 Instalando dependencias del sistema (zbar)..."
    if command -v brew &> /dev/null; then
        brew install zbar 2>/dev/null || echo "⚠️  zbar ya instalado o saltado"
    else
        echo "⚠️  Homebrew no encontrado. Instala zbar manualmente: brew install zbar"
    fi
fi

# Crear entorno virtual
echo "🐍 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias Python
echo "📦 Instalando dependencias Python..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "✅ Instalación completada!"
echo ""
echo "Para arrancar el bot:"
echo "  source venv/bin/activate"
echo "  python bot.py"
echo ""
echo "O usa el script de inicio rápido:"
echo "  bash run.sh"
