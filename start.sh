#!/bin/bash
set -e

# Variables
DISPLAY=${DISPLAY_NUM:-:0}
VNC_PORT=${VNC_PORT:-5900}
USER=${USER:-user}
PROJECT_DIR=${PROJECT_DIR:-/home/$USER/audio-automatizado-api-transcript}

echo "Iniciando contenedor para $USER con DISPLAY=$DISPLAY y VNC=$VNC_PORT"

# Iniciar PulseAudio como usuario
sudo -u $USER pulseaudio --start --system=false --disallow-exit --exit-idle-time=-1

# Iniciar Xvfb
Xvfb $DISPLAY -screen 0 1280x720x16 &
export DISPLAY=$DISPLAY
sleep 2

# Iniciar XFCE
sudo -u $USER startxfce4 &

# Iniciar VNC
x11vnc -display $DISPLAY -forever -nopw -listen 0.0.0.0 -rfbport $VNC_PORT &

sleep 5

# Ejecutar cliente main.py como usuario
sudo -u $USER bash -c "cd $PROJECT_DIR/client && python3 main.py" > $PROJECT_DIR/mainpy.log 2>&1 &

echo "Contenedor listo. Logs en $PROJECT_DIR/mainpy.log"

# Mantener contenedor vivo
tail -f /dev/null
