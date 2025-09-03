#!/bin/bash
set -e

# Variables
export DISPLAY=:0
export PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native

# Iniciar PulseAudio (modo usuario)
pulseaudio --start --disallow-exit --exit-idle-time=-1

# Iniciar Xvfb (display virtual)
Xvfb :0 -screen 0 1280x720x16 &
sleep 2

# Iniciar entorno gráfico XFCE
startxfce4 &
sleep 2

# Iniciar servidor VNC
x11vnc -display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900 &
sleep 3

# Activar entorno virtual
source /home/$USER/venv/bin/activate

# Ejecutar el proyecto Python (puedes cambiar el script si lo necesitas)
python3 client/levantar_varios_clientes.py > /home/$USER/main.log 2>&1 &

# Mantener el contenedor vivo
tail -f /dev/null




