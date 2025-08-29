
# Audio Automatizado Testing v4 - Cliente Pesado y Sistema RTP

Sistema automatizado para grabar audio desde streams de video, procesar y segmentar localmente en el cliente, y transmitir en tiempo real usando **RTP**. Incluye automatización de navegador, captura de audio, jitter buffer, segmentación y almacenamiento robusto, pensado para Ubuntu Server 24.04+ y compatible con Windows en el lado servidor.

---

## 🏗️ Arquitectura del Sistema


```
Cliente (Linux)
┌──────────────────────────────┐
│ Chromium/Chrome (Navegador) │
│ ↓                            │
│ PulseAudio                   │
│ ↓                            │
│ FFmpeg/Parec (grabación)     │
│ ↓                            │
│ JitterBuffer (acumulación y reordenamiento) │
│ ↓                            │
│ Worker (procesa y segmenta)  │
│ ↓                            │
│ Archivos WAV locales         │
└──────────────────────────────┘
```

---

## 📋 Requisitos del Sistema

### Cliente (Linux)
- **Ubuntu Server 24.04+**
- **Python 3.12+** y **python3.12-venv**
- **Chromium** o **Google Chrome**
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

### Servidor
```bash
cd server/
python main.py
# Salida: 🎧 Listening for RTP audio on <IP>:6001
```

### Cliente
```bash
cd client/
python main.py "https://stream-url.com/live" "ffmpeg/parec"
# Para múltiples clientes:
python levantar_varios_clientes.py "https://stream-url.com/live" "ffmpeg/parec"
```

---

## 🔧 Configuración Rápida

### Cliente (`client/config.py`)
```python
DEST_IP = "<IP del servidor>"
DEST_PORT = 6001
FRAME_SIZE = 960
SAMPLE_RATE = 48000
JITTER_BUFFER_SIZE = 25  # ms de prefill
WAV_SEGMENT_SECONDS = 5
INACTIVITY_TIMEOUT = 3
```

### Servidor (`server/main.py`)
```python
LISTEN_IP = "<IP de escucha>"
LISTEN_PORT = 6001
CHANNELS = 1
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

1. **Cliente**: Chromium/Chrome reproduce stream → PulseAudio captura → FFmpeg/Parec graba → JitterBuffer acumula y reordena → Worker procesa y segmenta → Archivos WAV locales

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
