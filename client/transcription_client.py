
import json
import threading
import time
import websocket
from config import WS_SERVER_URL

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
            print(f"Error enviando: {e}")

    def close(self):
        self.ws.close()
