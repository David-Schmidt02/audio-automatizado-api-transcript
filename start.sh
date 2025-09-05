
# =============================================
# Este script se ejecuta SIEMPRE dentro de un contenedor Linux (Docker),
# sin importar si el host es Windows o Linux.
#
# No es necesario modificar nada según el host.
#
# Requisitos:
#   - Mantener finales de línea LF (no CRLF)
#   - No modificar el shebang ni los comandos
#   - Los volúmenes deben mapearse correctamente en docker-compose.yml
#
# Si alguna vez necesitas ejecutarlo fuera de Docker, descomenta y adapta según corresponda.
# =============================================
#!/bin/bash
set -euo pipefail

# ========= Config =========
USER_NAME=soflex
USER_UID=$(id -u "$USER_NAME")
USER_GID=$(id -g "$USER_NAME")

export DISPLAY=:0
AUTO_START="${AUTO_START:-1}"          # 1 = lanzar Python al inicio
OPEN_URL="${OPEN_URL:-}"               # ej: OPEN_URL="https://youtube.com/@algo/live"
BROWSER="${BROWSER:-firefox}"          # firefox | chrome (usa /usr/local/bin/firefox o google-chrome-wrapper)

APP_DIR="/home/$USER_NAME/Escritorio/Soflex/audio-automatizado-api-transcript"
VENV_PY="/home/$USER_NAME/Escritorio/Soflex/venv/bin/python3"
VENV_PIP="/home/$USER_NAME/Escritorio/Soflex/venv/bin/pip"
LOG_DIR="/home/$USER_NAME/logs"

XVFB_ARGS=":0 -screen 0 1280x720x16"
VNC_ARGS="-display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900 -noxdamage -noipv6 -noshm"

# ========= Helpers =========
as_user() { su - "$USER_NAME" -s /bin/bash -lc "$*"; }

# ========= Preparación de dirs y permisos =========
mkdir -p "$LOG_DIR" "/run/user/$USER_UID" "/run/dbus"
chown -R "$USER_NAME:$USER_NAME" "$LOG_DIR" "/run/user/$USER_UID"
chmod 700 "/run/user/$USER_UID"

# ========= Limpieza idempotente =========
pkill -9 -f "Xvfb :0"        2>/dev/null || true
pkill -9 -f "x11vnc .*:0"    2>/dev/null || true
pkill -9 -f "xfce4-session"  2>/dev/null || true
pkill -9 -x pulseaudio       2>/dev/null || true

rm -f /tmp/.X0-lock /run/dbus/pid 2>/dev/null || true
rm -rf "/run/user/$USER_UID/pulse" 2>/dev/null || true  # limpia socket viejo del usuario

# ========= D-Bus (system) mínimo =========
[ -S /run/dbus/system_bus_socket ] || dbus-daemon --system --fork

# ========= Xvfb =========
Xvfb $XVFB_ARGS >"$LOG_DIR/xvfb.log" 2>&1 &
if command -v xdpyinfo >/dev/null 2>&1; then
  for i in {1..40}; do xdpyinfo -display :0 >/dev/null 2>&1 && break || sleep 0.25; done
else
  sleep 2
fi
DISPLAY=:0 xset -dpms || true
DISPLAY=:0 xset s off || true

# ========= PulseAudio por usuario (soflex) =========
as_user "
  export XDG_RUNTIME_DIR=/run/user/$USER_UID
  mkdir -p \"\$XDG_RUNTIME_DIR\" && chmod 700 \"\$XDG_RUNTIME_DIR\"
  pulseaudio --start --exit-idle-time=-1 || true
"

PA_SOCK="/run/user/$USER_UID/pulse/native"
for i in {1..40}; do
  [ -S "$PA_SOCK" ] && { echo "🎧 PulseAudio OK: $PA_SOCK"; break; }
  echo "⏳ Esperando PulseAudio de $USER_NAME..."
  sleep 0.25
done

# ========= XFCE + VNC (como soflex) =========
as_user "
  export DISPLAY=:0
  export XDG_RUNTIME_DIR=/run/user/$USER_UID
  export PULSE_SERVER=unix:$PA_SOCK
  startxfce4 >\"$LOG_DIR/xfce.log\" 2>&1 &
  sleep 1
  x11vnc $VNC_ARGS >\"$LOG_DIR/x11vnc.log\" 2>&1 &
"

# Esperar unos segundos antes de lanzar el navegador
sleep 5

# Lanzar el navegador (ajusta el comando según tu preferencia)
#as_user "DISPLAY=:0 PULSE_SERVER=unix:$PA_SOCK firefox 'https://youtube.com/' >/dev/null 2>&1 &"

# Esperar a que el navegador inicie completamente
sleep 5

# ========= Lanzar tu app Python automáticamente (como soflex) =========
if [ -z "${VENV_PY}" ] || [ ! -x "${VENV_PY}" ]; then
  echo "[WARN] VENV_PY no existe, uso python3 del sistema" >> "$LOG_DIR/main.log"
  VENV_PY="$(command -v python3)"
  VENV_PIP="$(command -v pip3 || command -v pip || echo true)"
fi

# instalar deps en runtime (útil si montás el repo como volumen)
as_user "
  export DISPLAY=:0
  export XDG_RUNTIME_DIR=/run/user/$USER_UID
  export PULSE_SERVER=unix:$PA_SOCK
  export PYTHONUNBUFFERED=1
  export PYTHONPATH='$APP_DIR:$APP_DIR/client:'\"\\\$PYTHONPATH\"
  cd '$APP_DIR'
  '$VENV_PIP' -q install -U pip wheel setuptools || true
  [ -f requirements.txt ] && '$VENV_PIP' -q install -r requirements.txt || true
" >> "$LOG_DIR/main.log" 2>&1 || true

if [ "$AUTO_START" = "1" ]; then
  APP_ARGS="${APP_ARGS:-}"   # argumentos que quieras pasar
  as_user "
    export DISPLAY=:0
    export XDG_RUNTIME_DIR=/run/user/$USER_UID
    export PULSE_SERVER=unix:$PA_SOCK
    export PYTHONUNBUFFERED=1
    export PYTHONPATH='$APP_DIR:$APP_DIR/client:'\"\\\$PYTHONPATH\"
    cd '$APP_DIR'
    echo \"[INFO] Lanzando client/main.py \$APP_ARGS\" >> '$LOG_DIR/main.log'
    nohup '$VENV_PY' client/main.py \$APP_ARGS >> '$LOG_DIR/main.log' 2>&1 &
  "
else
  echo "[INFO] AUTO_START=0 → no se lanza la app automáticamente" >> "$LOG_DIR/main.log"
fi

# ========= Seguir logs (mantener vivo) =========
touch "$LOG_DIR/main.log" "$LOG_DIR/xvfb.log" "$LOG_DIR/xfce.log" "$LOG_DIR/x11vnc.log"
tail -F "$LOG_DIR/main.log" "$LOG_DIR/xvfb.log" "$LOG_DIR/xfce.log" "$LOG_DIR/x11vnc.log"
