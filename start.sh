#!/bin/bash
set -euo pipefail

# ========= Config =========
USER_NAME=soflex
USER_UID=$(id -u "$USER_NAME")
USER_GID=$(id -g "$USER_NAME")

export DISPLAY=:0

VENV_PY="/home/$USER_NAME/Escritorio/Soflex/venv/bin/python3"
APP_DIR="/home/$USER_NAME/Escritorio/Soflex/audio-automatizado-api-transcript"
LOG_DIR="/home/$USER_NAME/logs"

XVFB_ARGS=":0 -screen 0 1280x720x16"
VNC_ARGS="-display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900 -noxdamage -noipv6 -noshm"

# ========= Preparación de dirs y permisos =========
mkdir -p "$LOG_DIR" "/run/user/0" "/run/user/$USER_UID" "/run/dbus"
chown -R "$USER_NAME:$USER_NAME" "$LOG_DIR" "/run/user/$USER_UID"
chmod 700 "/run/user/0" "/run/user/$USER_UID"

# ========= Limpieza idempotente =========
pkill -9 -f "Xvfb :0"        2>/dev/null || true
pkill -9 -f "x11vnc .*:0"    2>/dev/null || true
pkill -9 -f "xfce4-session"  2>/dev/null || true
pkill -9 -x pulseaudio       2>/dev/null || true

rm -f /tmp/.X0-lock 2>/dev/null || true
rm -f /run/dbus/pid 2>/dev/null || true

# Limpieza específica de PulseAudio como root (¡antes de iniciar nada!)
rm -rf "/run/user/0/pulse"            2>/dev/null || true
rm -rf "/run/user/$USER_UID/pulse"    2>/dev/null || true
# (No borramos ~/.config/pulse del usuario)

# ========= D-Bus system mínimo =========
if [ ! -S /run/dbus/system_bus_socket ]; then
  dbus-daemon --system --fork
fi

# ========= PulseAudio como soflex =========
# Creamos/corregimos runtime del usuario y levantamos su PA
su - "$USER_NAME" -c "
  export XDG_RUNTIME_DIR=/run/user/$USER_UID
  mkdir -p \"\$XDG_RUNTIME_DIR\"
  chmod 700 \"\$XDG_RUNTIME_DIR\"
  pulseaudio --start --exit-idle-time=-1
"

# Esperar el socket del usuario
PA_SOCK="/run/user/$USER_UID/pulse/native"
for i in {1..40}; do
  if [ -S "$PA_SOCK" ]; then
    echo "🎧 PulseAudio (user=$USER_NAME) OK: $PA_SOCK"
    break
  fi
  echo "⏳ Esperando PulseAudio de $USER_NAME..."
  sleep 0.25
done

# (Opcional) Diagnóstico a log
su - "$USER_NAME" -c "
  export XDG_RUNTIME_DIR=/run/user/$USER_UID
  export PULSE_SERVER=unix:$PA_SOCK
  pactl info >> \"$LOG_DIR/main.log\" 2>&1 || true
"

# ========= Xvfb =========
Xvfb $XVFB_ARGS >"$LOG_DIR/xvfb.log" 2>&1 &
if command -v xdpyinfo >/dev/null 2>&1; then
  for i in {1..40}; do xdpyinfo -display :0 >/dev/null 2>&1 && break || sleep 0.25; done
else
  sleep 2
fi
DISPLAY=:0 xset -dpms || true
DISPLAY=:0 xset s off || true

# ========= XFCE + VNC (como soflex) =========
su - "$USER_NAME" -c "
  export DISPLAY=:0
  export XDG_RUNTIME_DIR=/run/user/$USER_UID
  export PULSE_SERVER=unix:$PA_SOCK
  startxfce4 >\"$LOG_DIR/xfce.log\" 2>&1 &
  sleep 1
  x11vnc $VNC_ARGS >\"$LOG_DIR/x11vnc.log\" 2>&1 &
"

# ========= (Opcional) Arrancar tu app Python automáticamente =========
# Descomentar si querés que se ejecute al iniciar el contenedor
 su - "$USER_NAME" -c "
   export DISPLAY=:0
   export XDG_RUNTIME_DIR=/run/user/$USER_UID
   export PULSE_SERVER=unix:$PA_SOCK
   export APP_DIR=\"$APP_DIR\"
   export PYTHONPATH=\"\$APP_DIR:\$APP_DIR/client:\$PYTHONPATH\"
   \"${VENV_PY}\" -m pip install -U pip wheel setuptools >> \"$LOG_DIR/main.log\" 2>&1 || true
   if [ -f \"\$APP_DIR/requirements.txt\" ]; then
     \"${VENV_PY}\" -m pip install -r \"\$APP_DIR/requirements.txt\" >> \"$LOG_DIR/main.log\" 2>&1 || true
   fi
   cd \"$APP_DIR\"
   PYTHONUNBUFFERED=1 \"${VENV_PY}\" client/levantar_varios_clientes.py >> \"$LOG_DIR/main.log\" 2>&1 &
# "

# ========= Seguir logs =========
touch "$LOG_DIR/main.log" "$LOG_DIR/xvfb.log" "$LOG_DIR/xfce.log" "$LOG_DIR/x11vnc.log"
tail -F "$LOG_DIR/main.log" "$LOG_DIR/xvfb.log" "$LOG_DIR/xfce.log" "$LOG_DIR/x11vnc.log"
