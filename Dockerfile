FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV USER=user
ENV PASSWORD=1234
ENV DISPLAY_NUM=:0
ENV VNC_PORT=5900
ENV PROJECT_DIR=/home/$USER/audio-automatizado-api-transcript

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    xfce4 xfce4-goodies \
    x11vnc xvfb \
    pulseaudio \
    firefox \
    dbus-x11 \
    sudo \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario normal
RUN useradd -m -s /bin/bash $USER && echo "$USER:$PASSWORD" | chpasswd && adduser $USER sudo

# Crear carpetas necesarias
RUN mkdir -p $PROJECT_DIR && chown -R $USER:$USER $PROJECT_DIR

# Copiar proyecto
COPY . $PROJECT_DIR
RUN chown -R $USER:$USER $PROJECT_DIR

# Copiar script de inicio
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Exponer puerto VNC
EXPOSE $VNC_PORT

# Ejecutar el script de inicio
CMD ["/bin/bash", "/start.sh"]
