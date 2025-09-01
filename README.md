
# Audio Automatizado Testing v4 - Cliente Pesado y Sistema RTP

Sistema automatizado para grabar audio desde streams de video, procesar y segmentar localmente en el cliente, y transmitir en tiempo real usando **RTP**. Incluye automatización de navegador, captura de audio, jitter buffer, segmentación y almacenamiento robusto, pensado para Ubuntu Server 24.04+ y compatible con Windows en el lado servidor.

---


## 🏗️ Arquitectura del Sistema

```
┌──────────────────────────────┐
│      Navegador Web           │
│ (Chrome/Chromium, sesión     │
│  iniciada, perfil Default)   │
└─────────────┬────────────────┘
              │ Audio (PulseAudio)
              ▼
        ┌───────────────┐
        │   FFmpeg /   │
        │    Parec     │
        └──────┬────────┘
               │ PCM
               ▼
        ┌───────────────┐
        │ JitterBuffer  │
        └──────┬────────┘
               │
               ▼
        ┌───────────────┐
        │ Segmentación  │
        │   WAV (5s)    │
        └──────┬────────┘
               │
               ▼
        ┌───────────────┐
        │ Cliente RTP   │
        │ (Python)      │
        └──────┬────────┘
               │ POST /transcribe
               ▼
   ┌──────────────────────────────┐
   │   mock_whisper_api.py        │
   │ (API de transcripción mock)  │
   └──────┬───────────────┬───────┘
          │               │
          │               │ WebSocket
          ▼               ▼
   ┌───────────────┐   ┌───────────────┐
   │ websocket_    │   │ Frontend/     │
   │ server.py     │   │ Monitor HTML  │
   └───────────────┘   └───────────────┘
```

**Componentes principales:**
- `mock_whisper_api.py`: API mock que simula transcripción y broadcast por WebSocket.
- `websocket_server.py`: Servidor WebSocket para broadcast y monitoreo en tiempo real.
- `client/rtp_client.py`, `client/transcription_client.py`: Cliente RTP y cliente WebSocket modularizados.
- `config.py`: Centraliza todos los endpoints y puertos.

---

## 📋 Requisitos del Sistema

### Cliente (Linux)
- **Ubuntu Server 24.04+**
- **Python 3.12+** y **python3.12-venv**
- **Chromium** o **Google Chrome** (con cuenta y sesión iniciada)
- **PulseAudio**
- **FFmpeg** o **parec**
- **Git**

### Servidor (Linux/Windows)
- **Python 3.12+**
- **Librerías Python**: `rtp`, `wave`
- **Puerto UDP 6001** disponible (configurable)

---

## 🚀 Instalación Paso a Paso (Cliente Ubuntu 24.04+)

### 1. Instalar Python y venv

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv git
```

### 2. Crear y activar entorno virtual

```bash
cd Desktop
python3.12 -m venv audio-test-env
source audio-test-env/bin/activate
```

### 3. Clonar el repositorio dentro del entorno

```bash
# (Asegúrate de tener el entorno virtual activado)
git clone https://github.com/David-Schmidt02/audio-automatizado-api-transcript.git
cd audio-automatizado-api-transcript
```

### 4. Instalar dependencias del sistema

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 5. Instalar dependencias Python

```bash
# (El setup.sh ya se encarga e instalarlo)
pip install -r requirements.txt
```

---

## 📁 Estructura del Proyecto

```
audio-automatizado-api-transcript/
├── README.md                    # Documentación principal
├── my_logger.py                 # Sistema de logging con colores
├── client/                      # 🖥️ Cliente (captura, procesamiento y envío)
│   ├── main.py                  # Script principal del cliente
│   ├── audio_client_session.py  # Lógica de grabación y control de sesión
│   ├── rtp_client.py            # JitterBuffer, segmentación y envío RTP
│   ├── navigator_manager.py     # Automatización de navegador
│   └── levantar_varios_clientes.py # Multi-instancia
├── scripts/
│   └── setup.sh                 # Instalador automatizado (opcional)
├── requirements.txt             # Dependencias Python
├── config.py                    # Configuración global
└── ...
```

---


## ⚙️ Características Técnicas

- **Audio**: 48kHz, 16-bit, Mono
- **JitterBuffer**: Acumulación, reordenamiento y tolerancia a jitter/red
- **Segmentación**: Archivos WAV automáticos cada 5 segundos
- **Procesamiento local**: Todo el flujo (grabación, buffer, segmentación, almacenamiento) ocurre en el cliente
- **Multi-cliente**: Soporte simultáneo por SSRC
- **Limpieza robusta**: Todos los recursos y threads se liberan correctamente al shutdown o inactividad
- **Sin transmisión RTP a servidor externo**: No se envían paquetes RTP fuera del cliente, todo es procesamiento interno

---


## 🕹️ Uso Básico

### 1. Levantar el mock de transcripción (API + WebSocket)
```bash
python3 mock_whisper_api.py
# o
uvicorn mock_whisper_api:app --reload
# Accede a la doc interactiva en: http://localhost:8000/docs
```

**IMPORTANTE:**
- Debes tener una cuenta de Google y sesión iniciada en el navegador Chrome/Chromium para que la automatización funcione correctamente.
- El perfil debe ser "Default" o uno donde ya hayas iniciado sesión.

### 2. Levantar el servidor WebSocket
```bash
python3 websocket_server.py
# Escucha en ws://localhost:8765 (o el puerto configurado en config.py)

#### Flags de Chrome/Chromium
El sistema utiliza solo flags mínimas para compatibilidad y autoplay:

```
--window-size=1920,1080
--autoplay-policy=no-user-gesture-required
--mute-audio (opcional, recomendado para autoplay)
--disable-translate
--disable-infobars
```
No se recomienda usar flags como --incognito, --disable-sync, --disable-notifications, --disable-popup-blocking, --disable-extensions, etc., ya que pueden interferir con el perfil y la sesión.
```

### 3. Ejecutar el cliente RTP
```bash
cd client/
python3 main.py "https://www.youtube.com/@canal/live" Chromium ffmpeg
# Para múltiples clientes:
python3 levantar_varios_clientes.py
```

### 4. Visualizar transcripciones en tiempo real
- Conéctate al WebSocket con un frontend o herramienta compatible (por ejemplo, transcripciones.html).

---


## 🔧 Configuración Centralizada

Todos los endpoints, puertos y rutas están en `config.py`:

```python
# mock_whisper_api
MOCK_API_HOST = "localhost"
MOCK_API_PORT = 8000
MOCK_API_WS = f"ws://{MOCK_API_HOST}:{MOCK_API_PORT}/ws"
MOCK_API_TRANSCRIBE = f"http://{MOCK_API_HOST}:{MOCK_API_PORT}/transcribe"

# websocket_server
WS_SERVER_HOST = "localhost"
WS_SERVER_PORT = 8765
WS_SERVER_URL = f"ws://{WS_SERVER_HOST}:{WS_SERVER_PORT}"

# Navegador
# Es necesario tener una cuenta de Google y sesión iniciada en el perfil seleccionado (por defecto: Default).
```

---

## 🛠️ Solución de Problemas

### PulseAudio no responde
```bash
pulseaudio -k && pulseaudio --start
```

### Verificar dispositivos de audio
```bash
pactl list sinks short
```

### Problemas de red
```bash
netstat -tuln | grep 6001
telnet <IP servidor> 6001
```

### Variables de entorno para VM
```bash
export DISPLAY=:0
export MOZ_DISABLE_CONTENT_SANDBOX=1
```

---

## 📊 Logging y Debug

- **INFO** (Cyan): Información general
- **DEBUG** (Magenta): Detalles técnicos
- **ERROR** (Rojo): Errores del sistema
- **SUCCESS** (Verde): Operaciones exitosas

---


## 🔄 Flujo de Datos

1. **Cliente**: Navegador → PulseAudio → FFmpeg/Parec → JitterBuffer → Segmentación WAV → POST a mock_whisper_api → Broadcast WebSocket → Frontend/Monitor

---

## 📈 Rendimiento

- **Latencia**: ~200ms (prefill jitter + red)
- **Throughput**: ~384 kbps por cliente (48kHz * 16bit * 1ch)
- **Clientes simultáneos**: Limitado por ancho de banda y CPU

---

## 📝 Notas

- Siempre activa el entorno virtual antes de instalar o ejecutar scripts Python.
- El script `setup.sh` puede automatizar la instalación en sistemas compatibles.
- Para personalizaciones, revisa los archivos de configuración y los scripts en `client/` y `server/`.
- El cliente ahora es responsable de la grabación, jitter buffer, segmentación y limpieza de recursos.

---

## 🧩 Créditos y Licencia

Desarrollado por David Schmidt. Uso libre para fines educativos y de testing.
