# Usa Ubuntu 24.04 como base
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

# Variables de usuario
ENV USER=soflex
ENV PASSWORD=soflex

# Instalar dependencias básicas y escritorio
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y universe && \
    apt-get update && \
    apt-get install -y \
        xubuntu-desktop \
        xvfb x11vnc \
        x11-utils \
        pulseaudio pulseaudio-utils \
        sudo wget curl dbus-x11 apt-utils \
        python3 python3-venv python3-dev python3-pip \
        ffmpeg \
        gnupg apt-transport-https ca-certificates \
        xdotool \
        htop \
    && rm -rf /var/lib/apt/lists/*

# Limpiar applets innecesarios (bluetooth, network, updates, power manager)
RUN apt-get remove -y blueman network-manager-gnome update-manager xfce4-power-manager && \
    rm -f /etc/xdg/autostart/blueman.desktop && \
    rm -f /etc/xdg/autostart/nm-applet.desktop && \
    rm -f /etc/xdg/autostart/update-notifier.desktop && \
    rm -f /etc/xdg/autostart/xfce4-power-manager.desktop && \
    apt-get autoremove -y && apt-get clean

# Crear usuario y añadirlo a sudo y pulse-access
RUN useradd -m -s /bin/bash $USER && \
    echo "$USER:$PASSWORD" | chpasswd && \
    adduser $USER sudo && \
    adduser $USER pulse-access

# Instalar Firefox directamente del .deb oficial de Mozilla
RUN apt-get update && \
    apt-get install -y wget bzip2 libdbus-glib-1-2 libgtk-3-0 && \
    wget -q "https://download-installer.cdn.mozilla.net/pub/firefox/releases/124.0.1/linux-x86_64/es-AR/firefox-124.0.1.tar.bz2" -O /tmp/firefox.tar.bz2 && \
    mkdir -p /opt/firefox && \
    tar -xjf /tmp/firefox.tar.bz2 -C /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox && \
    rm /tmp/firefox.tar.bz2 && \
    # Crear acceso directo para el escritorio y menú de aplicaciones
    mkdir -p /usr/share/applications && \
    echo '[Desktop Entry]\nVersion=1.0\nName=Firefox\nGenericName=Web Browser\nComment=Navegar por la Web\nExec=/opt/firefox/firefox %u\nTerminal=false\nType=Application\nIcon=/opt/firefox/browser/chrome/icons/default/default128.png\nCategories=Network;WebBrowser;\nStartupWMClass=firefox\nStartupNotify=true' > /usr/share/applications/firefox.desktop && \
    chmod +x /usr/share/applications/firefox.desktop && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instalar Google Chrome estable (.deb)
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb && \
    apt-get install -y /tmp/chrome.deb && \
    rm /tmp/chrome.deb

# Wrapper para Chrome sin sandbox
RUN echo '#!/bin/bash\nexec /usr/bin/google-chrome-stable --no-sandbox "$@"' \
    > /usr/local/bin/google-chrome-wrapper && \
    chmod +x /usr/local/bin/google-chrome-wrapper && \
    update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/google-chrome-wrapper 50

# Alias gnome-terminal → xfce4-terminal
RUN ln -sf /usr/bin/xfce4-terminal /usr/bin/gnome-terminal || true

# Crear carpeta Soflex y dar permisos
USER root
RUN mkdir -p /home/$USER/Escritorio/Soflex && \
    chown -R $USER:$USER /home/$USER/Escritorio/Soflex && \
    # Crear acceso directo en el escritorio del usuario
    mkdir -p /home/$USER/Desktop && \
    cp /usr/share/applications/firefox.desktop /home/$USER/Desktop/ && \
    cp /usr/share/applications/google-chrome.desktop /home/$USER/Desktop/ && \
    chown -R $USER:$USER /home/$USER/Desktop

# --- Proyecto y entorno ---
WORKDIR /home/$USER/Escritorio/Soflex/audio-automatizado-api-transcript

# Crear venv vacío (requirements se instalarán en runtime)
USER $USER
RUN python3 -m venv /home/$USER/Escritorio/Soflex/venv && \
    /home/$USER/Escritorio/Soflex/venv/bin/pip install --upgrade pip

# --- Red y puertos ---
EXPOSE 5900

# --- Entrypoint ---
USER root
ENTRYPOINT ["/bin/bash", "/start.sh"]
