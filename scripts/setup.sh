#!/bin/bash
set -e

echo "=== Instalando paquetes base, terminal y dependencias ==="
apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    ffmpeg \
    xfce4-terminal \
    curl software-properties-common apt-transport-https ca-certificates gnupg wget \
    && rm -rf /var/lib/apt/lists/*

echo "=== Instalando Chromium clásico desde PPA ==="
add-apt-repository -y ppa:xtradeb/apps
apt-get update
apt-get install -y chromium

echo "=== Instalando Google Chrome estable (archivo .deb) ==="
if ! command -v google-chrome &> /dev/null; then
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
         -O /tmp/google-chrome.deb
    apt-get install -y /tmp/google-chrome.deb
    rm -f /tmp/google-chrome.deb
else
    echo "Google Chrome ya está instalado."
fi

echo "=== Configurando entorno de Python ==="
python3 -m venv /home/$USER/venv
/home/$USER/venv/bin/pip install --upgrade pip

REQ_FILE="/home/$USER/Escritorio/Soflex/audio-automatizado-api-transcript/requirements.txt"
if [ -f "$REQ_FILE" ]; then
    echo "Instalando dependencias Python desde requirements.txt..."
    /home/$USER/venv/bin/pip install -r "$REQ_FILE"
else
    echo "⚠️  requirements.txt no encontrado; instalando dependencias básicas..."
    /home/$USER/venv/bin/pip install selenium webdriver-manager rtp
fi

echo "✅ setup.sh finalizado"
