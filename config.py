BUFFER_SIZE = 4096
FRAME_SIZE = 960
SAMPLE_RATE = 48000
CHANNELS = 1
RTP_VERSION = 2
PAYLOAD_TYPE = 96
SAMPLE_FORMAT = "int16"

# IPs
# mock_whisper_api
MOCK_API_HOST = "172.21.100.2"
MOCK_API_PORT = 8000
MOCK_API_WS = f"ws://{MOCK_API_HOST}:{MOCK_API_PORT}/ws"
MOCK_API_TRANSCRIBE = f"http://{MOCK_API_HOST}:{MOCK_API_PORT}/transcribe"

# websocket_server
WS_SERVER_HOST = "172.21.100.2"
WS_SERVER_PORT = 8765
WS_SERVER_URL = f"ws://{WS_SERVER_HOST}:{WS_SERVER_PORT}"

# Configuracion para el WAV y el JITTER BUFFER
INACTIVITY_TIMEOUT = 3 # segundos de inactividad para cerrar WAV
WAV_SEGMENT_SECONDS = 5  # Segundos de cada segmento WAV

FRAME_DURATION_MS = FRAME_SIZE / 48000 * 1000  # ms por paquete
PREFILL_MS = 200  # queremos 200 ms
JITTER_BUFFER_SIZE = int(PREFILL_MS / FRAME_DURATION_MS)

MAX_WAIT = 0.2  # Máximo tiempo de espera para procesar paquetes en el jitter buffer

# Canales:
url1 = "https://www.youtube.com/@olgaenvivo_/live"
url2 = "https://www.youtube.com/@luzutv/live"
url3 = "https://www.youtube.com/@todonoticias/live"
url4 = "https://www.youtube.com/@lanacion/live"
url5 = "https://www.youtube.com/@C5N/live"
url6 = "https://www.youtube.com/@A24com/live"
url7 = "https://www.youtube.com/@Telefe/live"
url8 = "https://www.youtube.com/@UrbanaPlayFM/live"

urls_canales = [url1]