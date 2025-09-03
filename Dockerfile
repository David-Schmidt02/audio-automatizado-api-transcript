FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV USER=user
ENV PASSWORD=1234

# Instalar utilidades básicas, entorno XFCE y VNC
RUN apt-get update && apt-get install -y \
    xfce4 xfce4-goodies \
    x11vnc xvfb \
    pulseaudio \
    firefox \
    dbus-x11 \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario normal
RUN useradd -m -s /bin/bash $USER && echo "$USER:$PASSWORD" | chpasswd && adduser $USER sudo

# Configuración de PulseAudio en modo "system-wide"
RUN mkdir -p /home/$USER/.config/pulse && chown -R $USER:$USER /home/$USER

# Puerto VNC
EXPOSE 5900

# Script de inicio (Xvfb + XFCE + VNC + PulseAudio)
CMD ["/bin/bash", "-c", "\
    pulseaudio --start --system=false --disallow-exit --exit-idle-time=-1 && \
    Xvfb :0 -screen 0 1280x720x16 & \
    export DISPLAY=:0 && \
    startxfce4 & \
    x11vnc -display :0 -forever -nopw -listen 0.0.0.0 -rfbport 5900 \
"]
