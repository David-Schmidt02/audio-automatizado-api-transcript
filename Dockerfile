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


# Copiar todo el proyecto al home del usuario y dar permisos
COPY . /home/$USER/audio-automatizado-api-transcript
RUN chown -R $USER:$USER /home/$USER/audio-automatizado-api-transcript

# Copiar el script de inicio y dar permisos
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Script de inicio (Xvfb + XFCE + VNC + PulseAudio + main.py)
CMD ["/bin/bash", "/start.sh"]
