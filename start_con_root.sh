#!/bin/bash
set -euo pipefail

# =========================
# Config
# =========================
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/0           # runtime para root (necesario p/ pulseaudio)
VENV_PY="/home/soflex/Escritorio/Soflex/venv/bin/python3"
APP_DIR="/home/soflex/Escritorio/Soflex/audio-automatizado-api-transcript"
LOG_DIR="/root"
XVFB_ARGS=":0 -screen 0 1280x720x16 -dpms"
VNC_ARGS="-display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900 -noxdamage -noipv6"

mkdir -p "$XDG_RUNTIME_DIR" "$LOG_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

# =========================
# Limpieza idempotente
# =========================
pkill -9 -f "Xvfb :0"        2>/dev/null || true
pkill -9 -f "x11vnc .*:0"    2>/dev/null || true
pkill -9 -f "xfce4-session"  2>/dev/null || true
pkill -9 -x pulseaudio       2>/dev/null || true

rm -f /tmp/.X0-lock 2>/dev/null || true
rm -f /run/dbus/pid 2>/dev/null || true
# No tocamos /var/run/pulse/native en modo usuario (root) — lo maneja el daemon

# =========================
# D-Bus system mínimo (silencia applets charlatanes)
# =========================
mkdir -p /run/dbus
if [ ! -S /run/dbus/system_bus_socket ]; then
  dbus-daemon --system --fork
fi

# =========================
# PulseAudio (modo usuario para root)
# IMPORTANTE: NO exportar PULSE_SERVER antes de arrancar
# =========================
pulseaudio --start --exit-idle-time=-1 || true

# Esperar a que aparezca el socket de PA del usuario root
PA_SOCK="$XDG_RUNTIME_DIR/pulse/native"
for i in {1..20}; do
  if [ -S "$PA_SOCK" ]; then
    echo "🎧 PulseAudio (user=root) listo: $PA_SOCK"
    break
  fi
  echo "⏳ Esperando PulseAudio..."
  sleep 0.25
done

# (Opcional) Si querés forzar que apps usen ese socket:
export PULSE_SERVER="unix:$PA_SOCK"

# =========================
# Xvfb + XFCE + VNC
# =========================
Xvfb $XVFB_ARGS >"$LOG_DIR/xvfb.log" 2>&1 &
# Esperar a que el display responda
if command -v xdpyinfo >/dev/null 2>&1; then
  for i in {1..20}; do xdpyinfo -display :0 >/dev/null 2>&1 && break || sleep 0.25; done
else
  sleep 2
fi

# Desactivar DPMS y screen saver
export DISPLAY=:0
xset -dpms
xset s off

startxfce4 >"$LOG_DIR/xfce.log" 2>&1 &
sleep 1

x11vnc $VNC_ARGS >"$LOG_DIR/x11vnc.log" 2>&1 &
sleep 1

# =========================
# Lanzar tu app Python usando el binario del venv
# (evitamos 'source' para que no importe el usuario)
# =========================
cd "$APP_DIR" || cd /
PY="$VENV_PY"
if [ ! -x "$PY" ]; then
  echo "[WARN] No encontré $VENV_PY, uso python3 del sistema" | tee -a "$LOG_DIR/main.log"
  PY="python3"
fi

PYTHONUNBUFFERED=1 "$PY" client/levantar_varios_clientes.py >> "$LOG_DIR/main.log" 2>&1 &

# =========================
# Mantener vivo y ver logs
# =========================
tail -F "$LOG_DIR/main.log" "$LOG_DIR/x11vnc.log" "$LOG_DIR/xfce.log" "$LOG_DIR/xvfb.log"
