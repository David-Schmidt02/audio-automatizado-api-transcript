FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV USER=user
ENV PASSWORD=1234

# Instalar utilidades
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    xfce4 xfce4-goodies x11vnc xvfb \
    pulseaudio \
    firefox \
    dbus-x11 sudo \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario normal
RUN useradd -m -s /bin/bash $USER && echo "$USER:$PASSWORD" | chpasswd && adduser $USER sudo

# Configurar PulseAudio
RUN mkdir -p /home/$USER/.config/pulse && chown -R $USER:$USER /home/$USER

# Exponer puerto VNC
EXPOSE 5900

# Copiar proyecto y permisos
COPY . /home/$USER/Escritorio/Soflex/audio-automatizado-api-transcript
RUN chown -R $USER:$USER /home/$USER/Escritorio/Soflex/audio-automatizado-api-transcript

# Script de inicio
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/bin/bash", "/start.sh"]
