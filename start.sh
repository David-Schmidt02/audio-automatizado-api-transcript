#!/bin/bash

# Iniciar PulseAudio
pulseaudio --start --system=false --disallow-exit --exit-idle-time=-1

# Iniciar Xvfb y entorno gráfico
Xvfb :0 -screen 0 1280x720x16 &
export DISPLAY=:0
sleep 2
startxfce4 &

# Iniciar VNC
x11vnc -display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900 &

# Esperar unos segundos
sleep 5

# Ejecutar proyecto Python
sudo -u $USER -H bash -c 'cd /home/$USER/Escritorio/Soflex/audio-automatizado-api-transcript && python3 client/levantar_varios_clientes.py' > /home/$USER/main.log 2>&1 &

# Mantener contenedor vivo
tail -f /dev/null
