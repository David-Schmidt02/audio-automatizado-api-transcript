#!/bin/bash
set -e

echo "=== Instalando dependencias del sistema ==="
apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

echo "=== Creando entorno virtual ==="
python3 -m venv /home/$USER/venv

echo "=== Activando entorno virtual e instalando requirements ==="
/home/$USER/venv/bin/pip install --upgrade pip
if [ -f /home/$USER/requirements.txt ]; then
    /home/$USER/venv/bin/pip install -r /home/$USER/requirements.txt
else
    echo "⚠️ requirements.txt no encontrado"
fi
