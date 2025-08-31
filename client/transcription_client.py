import json
import threading
import time
import websocket

class TranscriptionClient:
    def __init__(self, client_id, channel_name, url="ws://localhost:8765"):
        self.client_id = client_id
        self.channel_name = channel_name
        self.url = url

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

    # --- MODO CONTADOR PARA DEPURACIÓN ---
    _counter = 0
    def send_transcription(self, transcription):
        # Para enviar solo un contador incremental, descomenta las siguientes dos líneas
        TranscriptionClient._counter += 1
        payload = {
            "client_id": self.client_id,
            "channel_name": self.channel_name,
            "transcription": f"{TranscriptionClient._counter}"
        }

        # Para enviar la transcripción real, comenta las 3 líneas anteriores y descomenta esto:
        # payload = {
        #     "client_id": self.client_id,
        #     "channel_name": self.channel_name,
        #     "transcription": transcription
        # }

        try:
            self.ws.send(json.dumps(payload))
        except Exception as e:
            print(f"Error enviando: {e}")

    def close(self):
        self.ws.close()
