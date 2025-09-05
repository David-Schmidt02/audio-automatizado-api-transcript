
import json
import threading
import time
import websocket
from config import WS_SERVER_URL
from my_logger import log_and_save

class TranscriptionClient:
    def __init__(self, client_id, channel_name, url=None):
        self.client_id = client_id
        self.channel_name = channel_name
        self.url = url or WS_SERVER_URL

        self.ws = None
        self._connect()

    def _connect(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
            on_message=self.on_message
        )
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.thread.start()
        # Esperar a que la conexión esté lista
        time.sleep(1)

    def on_open(self, ws):
        print("WebSocket abierto")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket cerrado")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_message(self, ws, message):
        pass  # No necesitas procesar mensajes en este caso

    def send_transcription(self, transcription):
        payload = {
            "client_id": self.client_id,
            "channel_name": self.channel_name,
            "transcription": transcription
        }

        try:
            self.ws.send(json.dumps(payload))
        except Exception as e:
            log_and_save(f"Error enviando: {e}. Intentando reconectar...", "ERROR", self.client_id)
            try:
                self.reconnect_ws()  # Debes tener un método que reconecte el websocket
                self.ws.send(json.dumps(payload))
                log_and_save("Reenvío exitoso tras reconexión.", "INFO", self.client_id)
            except Exception as e2:
                log_and_save(f"Error al reenviar tras reconexión: {e2}", "ERROR", self.client_id)
    def reconnect_ws(self):
        try:
            if self.ws:
                self.ws.close()
            time.sleep(1)  # Espera breve antes de reconectar
            self._connect()
            log_and_save("Reconexión WebSocket exitosa.", "INFO", self.client_id)
        except Exception as e:
            log_and_save(f"Error al reconectar WebSocket: {e}", "ERROR", self.client_id)

    def close(self):
        self.ws.close()
