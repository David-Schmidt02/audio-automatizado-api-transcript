# ========= Base =========
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

# ========= Usuario app =========
ENV USER=soflex
ENV PASSWORD=soflex

# ========= Paquetes base / escritorio / utilidades =========
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y universe && \
    apt-get update && \
    apt-get install -y \
        xubuntu-desktop \
        xvfb x11vnc x11-utils \
        pulseaudio pulseaudio-utils dbus-x11 \
        sudo wget curl gnupg ca-certificates apt-transport-https \
        python3 python3-venv python3-dev python3-pip \
        ffmpeg xdotool htop \
    && rm -rf /var/lib/apt/lists/*

# ========= Quitar applets ruidosos de XFCE (evita errores de D-Bus/Power/BT) =========
RUN apt-get remove -y blueman network-manager-gnome update-manager xfce4-power-manager || true && \
    rm -f /etc/xdg/autostart/blueman.desktop \
          /etc/xdg/autostart/nm-applet.desktop \
          /etc/xdg/autostart/update-notifier.desktop \
          /etc/xdg/autostart/xfce4-power-manager.desktop && \
    apt-get autoremove -y && apt-get clean

# ========= Usuario no-root y grupos útiles =========
RUN useradd -m -s /bin/bash ${USER} && \
    echo "${USER}:${PASSWORD}" | chpasswd && \
    adduser ${USER} sudo && \
    adduser ${USER} pulse-access

# ========= Firefox (tarball oficial de Mozilla) =========
RUN apt-get update && \
    apt-get install -y wget bzip2 libdbus-glib-1-2 libgtk-3-0 && \
    wget -q "https://download-installer.cdn.mozilla.net/pub/firefox/releases/124.0.1/linux-x86_64/es-AR/firefox-124.0.1.tar.bz2" -O /tmp/firefox.tar.bz2 && \
    mkdir -p /opt && \
    tar -xjf /tmp/firefox.tar.bz2 -C /opt && \
    ln -sf /opt/firefox/firefox /usr/local/bin/firefox && \
    rm -f /tmp/firefox.tar.bz2 && \
    # .desktop para menú y acceso rápido
    mkdir -p /usr/share/applications && \
    printf '%s\n' \
      '[Desktop Entry]' \
      'Version=1.0' \
      'Name=Firefox' \
      'GenericName=Web Browser' \
      'Comment=Navegar por la Web' \
      'Exec=/opt/firefox/firefox %u' \
      'Terminal=false' \
      'Type=Application' \
      'Icon=/opt/firefox/browser/chrome/icons/default/default128.png' \
      'Categories=Network;WebBrowser;' \
      'StartupWMClass=firefox' \
      'StartupNotify=true' \
      > /usr/share/applications/firefox.desktop && \
    chmod +x /usr/share/applications/firefox.desktop && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ========= Google Chrome estable =========
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb && \
    apt-get update && apt-get install -y /tmp/chrome.deb && \
    rm -f /tmp/chrome.deb && \
    # Wrapper sin sandbox (útil en contenedor)
    printf '%s\n' '#!/bin/bash' 'exec /usr/bin/google-chrome-stable --no-sandbox "$@"' \
      > /usr/local/bin/google-chrome-wrapper && \
    chmod +x /usr/local/bin/google-chrome-wrapper && \
    update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/google-chrome-wrapper 50

# ========= Alias gnome-terminal → xfce4-terminal (compatibilidad) =========
RUN ln -sf /usr/bin/xfce4-terminal /usr/bin/gnome-terminal || true

# ========= Estructura de trabajo del usuario =========
USER root
RUN mkdir -p /home/${USER}/Escritorio/Soflex && \
    chown -R ${USER}:${USER} /home/${USER}/Escritorio/Soflex && \
    # Accesos directos al escritorio del usuario
    mkdir -p /home/${USER}/Desktop && \
    cp /usr/share/applications/firefox.desktop /home/${USER}/Desktop/ || true && \
    cp /usr/share/applications/google-chrome.desktop /home/${USER}/Desktop/ || true && \
    chown -R ${USER}:${USER} /home/${USER}/Desktop

# ========= Proyecto y venv (el código lo montás como volumen) =========
WORKDIR /home/${USER}/Escritorio/Soflex/audio-automatizado-api-transcript

# Crear venv vacío para usarlo en runtime (requirements se instalan al arrancar)
USER ${USER}
RUN python3 -m venv /home/${USER}/Escritorio/Soflex/venv && \
    /home/${USER}/Escritorio/Soflex/venv/bin/pip install --upgrade pip

# ========= Red y puertos =========
EXPOSE 5900

# ========= Entrypoint =========
# Nota: en desarrollo, montá tu start.sh a /start.sh
USER root
ENTRYPOINT ["/bin/bash", "/start.sh"]
