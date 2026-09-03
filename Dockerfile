FROM python:3.12-slim

# Dependencias del sistema para OpenCV y zbar
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libzbar-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Crear directorios necesarios
RUN mkdir -p data assets qr_images

CMD ["python", "bot.py"]
