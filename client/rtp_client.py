import gc
import os
import sys
import json
import threading
import time

from rtp import RTP, PayloadType
from jitter_buffer import JitterBuffer
from energy_watchdog import EnergyWatchdog

# Rutas / imports locales
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
from my_logger import log_and_save  # noqa: E402
from config import (                # noqa: E402
    FRAME_SIZE, RTP_VERSION, CHANNELS, SAMPLE_RATE,
    WAV_SEGMENT_SECONDS, INACTIVITY_TIMEOUT, MOCK_API_TRANSCRIBE
)

class RTPClient:
    """
    Cliente RTP que:
      - recorta el stream en segmentos WAV de tamaño fijo,
      - alimenta un JitterBuffer,
      - notifica WAVs terminados al EnergyWatchdog,
      - y (opcionalmente) los envía a un backend (Whisper mock).
    """
    def __init__(self, ssrc, url, shutdown_event=None):
        self.ssrc = ssrc
        self.jitter_buffer = JitterBuffer(ssrc)
        self.shutdown_event = shutdown_event
        self.thread_worker = threading.Thread(
            target=self.start_worker_client,
            args=(shutdown_event,),
            daemon=True
        )

        self.channel_name = self.extract_channel_name(url)
        self.client_dir = None

        self.lock = threading.Lock()
        self.next_seq = 0
        self.last_time = None

        self.wavefile = None
        self.wav_path = None
        self.wav_start_time = None
        self.wav_index = 0

        # Inicializar después de definir todos los atributos
        self.transcription_client = None  # se crea sólo cuando lo uses
        self.semaphore_watchdog = threading.Semaphore(0)
        self.energy_watchdog = EnergyWatchdog(
            semaphore=self.semaphore_watchdog,
            ssrc=self.ssrc,
            umbral=500,         # ajustá a gusto
            timeout=600,        # 10 min
            check_interval=5,   # s
            frame_ms=30
        )

        # Abrir primer WAV
        self.wavefile = self.create_wav_file(self.ssrc, 0)
        self.wav_start_time = time.time()

    # ------------------------------
    # Archivos WAV
    # ------------------------------
    def rotate_wav_file(self):
        """Cierra el archivo actual y abre uno nuevo, incrementando el índice."""
        if self.wavefile:
            try:
                self.wavefile.close()
            except Exception:
                pass
        self.wav_index += 1
        self.wavefile = self.create_wav_file(self.ssrc, wav_index=self.wav_index)
        self.wav_start_time = time.time()

    def create_wav_file(self, ssrc, wav_index=0):
        import wave
        """Crea un WAV nuevo para el cliente en records/<canal>/."""
        base_dir = os.path.abspath("records")
        self.client_dir = os.path.join(base_dir, self.channel_name)
        if not os.path.exists(self.client_dir):
            os.makedirs(self.client_dir, exist_ok=True)
            log_and_save(f"📂 Creando directorio para canal: {self.channel_name}", "INFO", self.ssrc)

        name_wav = os.path.join(
            self.client_dir,
            f"record-{time.strftime('%Y%m%d-%H%M%S')}-{ssrc}-{self.channel_name}-{wav_index}.wav"
        )

        wf = wave.open(name_wav, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        log_and_save(f"💾 [Cliente {ssrc}] WAV abierto: {name_wav}", "INFO", self.ssrc)
        self.wav_path = name_wav
        return wf

    def eliminar_wavefile(self, wav_path):
        try:
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
                log_and_save(f"🗑️ Archivo WAV eliminado: {wav_path}", "INFO", self.ssrc)
        except Exception as e:
            log_and_save(f"❌ Error al eliminar WAV {wav_path}: {e}", "ERROR", self.ssrc)

    # ------------------------------
    # Utilidad
    # ------------------------------
    def extract_channel_name(self, url):
        import re
        log_and_save(f"🔍 Canal extraído de la URL: {url}", "INFO", self.ssrc)
        match = re.search(r'youtube\.com/@([^/]+)', url)
        if match:
            canal = match.group(1)
            log_and_save(f"🔍 Canal extraído: {canal}", "INFO", self.ssrc)
            return canal
        log_and_save("🔍 Canal extraído: unknown", "INFO", self.ssrc)
        return "unknown"

    # ------------------------------
    # RTP
    # ------------------------------
    def send_rtp_stream_to_jitter(self, data, ssrc, sequence_number):
        """Parte un bloque PCM en frames y los empuja como RTP al jitter buffer."""
        total_len = len(data)
        offset = 0
        frame_bytes = FRAME_SIZE * 2  # 16-bit (2 bytes)
        while offset < total_len:
            frame = data[offset:offset + frame_bytes]
            if not frame:
                break
            rtp_packet = self.create_rtp_packet(bytearray(frame), sequence_number, ssrc)
            self.send_to_jitter(rtp_packet)
            if sequence_number % 1000 == 0:
                log_and_save(f"📤 Enviado paquete seq {sequence_number} (raw stream)", "DEBUG", self.ssrc)
            sequence_number = (sequence_number + 1) % 65536
            offset += frame_bytes
        return sequence_number

    def send_to_jitter(self, rtp_packet):
        if self.last_time is None:
            self.last_time = time.time()
        if rtp_packet.sequenceNumber % 1000 == 0:
            log_and_save(f"📤 Enviado paquete RTP: {rtp_packet.sequenceNumber}", "DEBUG", self.ssrc)
        self.jitter_buffer.add_packet(rtp_packet.sequenceNumber, time.time(), rtp_packet.payload)

    def create_rtp_packet(self, payload, sequence_number, ssrc):
        # timestamp basado en samples (estable)
        timestamp = (sequence_number * FRAME_SIZE) % (2**32)
        return RTP(
            version=RTP_VERSION,
            payloadType=PayloadType.DYNAMIC_96,
            sequenceNumber=sequence_number,
            timestamp=timestamp,
            ssrc=ssrc,
            payload=payload if isinstance(payload, bytearray) else bytearray(payload),
        )

    # ------------------------------
    # Loop de consumo / segmentación WAV
    # ------------------------------
    def start_worker_client(self, shutdown_event=None):
        log_and_save(f"[Worker] Iniciado para cliente con SSRC: {self.ssrc}", "INFO", self.ssrc)
        if shutdown_event is None:
            shutdown_event = getattr(self, 'shutdown_event', None)

        self.wav_start_time = time.time()

        while True:
            if shutdown_event and shutdown_event.is_set():
                log_and_save(f"[Worker] Shutdown detectado. SSRC: {self.ssrc}", "INFO", self.ssrc)
                break

            with self.lock:
                # Prefill del jitter
                if not self.jitter_buffer.ready_to_consume():
                    log_and_save("Esperando prefill del Jitter Buffer...", "DEBUG", self.ssrc)
                    if self.handle_inactivity(self.ssrc):
                        break
                    time.sleep(0.005)
                    continue

                next_seq = self.next_seq

                # Consumir mientras haya material suficiente
                while self.jitter_buffer.ready_to_consume():
                    packet = self.jitter_buffer.pop_next(next_seq)
                    if packet is None:
                        break

                    now = time.time()

                    # Segmentación por tiempo
                    if now - self.wav_start_time >= WAV_SEGMENT_SECONDS:
                        # Cerrar WAV actual y notificar al watchdog
                        if self.wavefile:
                            try:
                                self.wavefile.close()
                            except Exception:
                                pass

                        if self.wav_path:
                            log_and_save(f"✅ Enviando {self.wav_path} al watchdog de energía", "INFO", self.ssrc)
                            try:
                                self.energy_watchdog.notify_wav_ready(self.wav_path)
                                # Evita bloquearte si el watchdog tarda: timeout breve y log
                                if not self.semaphore_watchdog.acquire(timeout=10):
                                    log_and_save("⌛ Watchdog no respondió a tiempo (10s). Continuo.", "WARN", self.ssrc)
                                #self.send_to_whisper(self.wav_path)
                                self.eliminar_wavefile(self.wav_path)
                            except Exception as e:
                                log_and_save(f"❌ Error notificando watchdog: {e}", "ERROR", self.ssrc)

                        # Abrir el siguiente segmento
                        self.wavefile = None
                        self.wav_path = None
                        gc.collect()
                        self.wav_index += 1
                        self.wavefile = self.create_wav_file(self.ssrc, wav_index=self.wav_index)
                        self.wav_start_time = time.time()
                        log_and_save(f"[Segmentación] Nuevo WAV segmento {self.wav_index}", "INFO", self.ssrc)

                    # Escribir frames
                    if self.wavefile:
                        self.wavefile.writeframes(packet["payload"])

                    # Actualizar actividad
                    if not packet.get("is_silence", False):
                        self.last_time = now

                    next_seq = (next_seq + 1) % 65536

                self.next_seq = next_seq

                if self.handle_inactivity(self.ssrc):
                    break

            time.sleep(0.005)

        # Salida limpia
        self.cleanup()

    # ------------------------------
    # Inactividad / Cleanup
    # ------------------------------
    def handle_inactivity(self, ssrc):
        """
        Si no hay audio por INACTIVITY_TIMEOUT, cerramos recursos del cliente.
        """
        if self.last_time is None:
            return False
        if time.time() - self.last_time > INACTIVITY_TIMEOUT:
            try:
                log_and_save(f"[Worker] Cliente {self.ssrc} inactivo por {INACTIVITY_TIMEOUT}s, cerrando.", "INFO", self.ssrc)
                self.cleanup()
                log_and_save(f"[Worker] Cliente {self.ssrc} recursos liberados.", "INFO", self.ssrc)
            except Exception as e:
                log_and_save(f"[Worker] Error en cleanup: {e}", "ERROR", self.ssrc)
            return True
        return False

    def cleanup(self):
        """Cierra archivos y libera recursos del cliente RTP."""
        try:
            if self.wavefile:
                try:
                    self.wavefile.close()
                except Exception:
                    pass
                self.eliminar_wavefile(self.wav_path)
            self.wavefile = None
            self.jitter_buffer = None
            # Si en algún momento instanciás TranscriptionClient, cerralo aquí:
            try:
                if self.transcription_client:
                    self.transcription_client.close()
            except Exception:
                pass
            # Apagar watchdog
            try:
                self.energy_watchdog.stop()
            except Exception:
                pass
        finally:
            gc.collect()
            log_and_save(f"[Cleanup] Recursos liberados para SSRC: {self.ssrc}", "INFO", self.ssrc)

    # ------------------------------
    # (Opcional) Envío a Whisper mock
    # ------------------------------
    def send_to_whisper(self, wav_path: str):
        import requests
        url = MOCK_API_TRANSCRIBE
        params = {
            "source_language": "es",
            "target_language": "es",
            "task": "asr",
            "model": "v2",
        }
        with open(wav_path, "rb") as f:
            files = {"audio": (os.path.basename(wav_path), f, "audio/wav")}
            response = requests.post(url, params=params, files=files)

        if response.status_code == 200:
            data = response.json()
            self.transcription_client.send_transcription(data.get("transcription", ""))
            log_and_save(f"📝 Transcrito {wav_path}", "INFO", self.ssrc)
        else:
            log_and_save(f"❌ Whisper {response.status_code}: {response.text}", "ERROR", self.ssrc)
