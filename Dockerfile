FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV USER=soflex
ENV PASSWORD=soflex

# Instalar sudo y dependencias básicas
RUN apt-get update && apt-get install -y \
    sudo wget curl dbus-x11 software-properties-common apt-utils \
    python3 python3-venv python3-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario normal con sudo
RUN useradd -m -s /bin/bash $USER && echo "$USER:$PASSWORD" | chpasswd && adduser $USER sudo

# Copiar proyecto al contenedor
WORKDIR /home/$USER/Escritorio/Soflex/audio-automatizado-api-transcript
COPY . .
RUN chown -R $USER:$USER /home/$USER/Escritorio/Soflex/audio-automatizado-api-transcript

# Instalar navegadores + dependencias vía setup.sh
COPY scripts/setup.sh /tmp/setup.sh
RUN chmod +x /tmp/setup.sh && /tmp/setup.sh

# Configurar PulseAudio
RUN mkdir -p /home/$USER/.config/pulse && chown -R $USER:$USER /home/$USER

# Exponer puerto VNC
EXPOSE 5900

# Script de inicio
COPY start.sh /start.sh
RUN chmod +x /start.sh

USER $USER
ENTRYPOINT ["/bin/bash", "/start.sh"]
