#!/bin/bash

# Iniciar PulseAudio
echo "Iniciando PulseAudio..."
pulseaudio --start --system=false --disallow-exit --exit-idle-time=-1

# Iniciar Xvfb y entorno gráfico
echo "Iniciando Xvfb y XFCE..."
Xvfb :0 -screen 0 1280x720x16 &
export DISPLAY=:0
sleep 2
startxfce4 &

# Iniciar VNC
echo "Iniciando x11vnc..."
x11vnc -display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900 &

# Esperar unos segundos para asegurar que todo esté listo
sleep 5


# Ejecutar el cliente main.py como usuario normal y mostrar salida/errores
echo "Ejecutando main.py como $USER..."
sudo -u $USER -H bash -c 'cd /home/$USER/audio-automatizado-api-transcript/client && python3 main.py' > /home/$USER/mainpy.log 2>&1 &
sleep 1
echo "Salida de main.py (primeras 20 líneas):"
sudo -u $USER head -20 /home/$USER/mainpy.log || echo "No se pudo leer el log."

# Mantener el contenedor vivo
tail -f /dev/null
