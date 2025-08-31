import gc
import os
import sys
import json
from transcription_client import TranscriptionClient
from rtp import RTP, PayloadType
import threading
import time
from jitter_buffer import JitterBuffer

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
from my_logger import log_and_save
from config import FRAME_SIZE, RTP_VERSION, CHANNELS, SAMPLE_RATE, WAV_SEGMENT_SECONDS, INACTIVITY_TIMEOUT, MOCK_API_TRANSCRIBE
# PAYLOAD_TYPE termina sobreescribiendose con el de la clase de la libreria rtp
# Configuración RTP


class RTPClient:
    def __init__(self, ssrc, url ,shutdown_event=None):
        self.ssrc = ssrc
        self.jitter_buffer = JitterBuffer(ssrc)
        self.shutdown_event = shutdown_event
        self.thread_worker = threading.Thread(target=self.start_worker_client, args=(shutdown_event,), daemon=True)

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
        self.transcription_client = None
        # Crear el primer archivo WAV y el cliente de transcripción 
        self.transcription_client = TranscriptionClient(self.ssrc, self.channel_name)
        self.wavefile = self.create_wav_file(self.ssrc, 0)
        self.wav_start_time = time.time()

    def rotate_wav_file(self,):
        """Cierra el archivo actual y abre uno nuevo, incrementando el índice."""
        if self.wavefile:
            self.wavefile.close()
        self.wav_index += 1
        self.wavefile = self.create_wav_file(self.ssrc, wav_index=self.wav_index)
        self.wav_start_time = time.time()

    def create_wav_file(self, ssrc, wav_index=0):
        import wave
        """Crea un WAV nuevo para el cliente en un directorio propio dentro de 'records'."""
        base_dir = "records"
        self.client_dir = os.path.join(base_dir, self.channel_name)
        if not os.path.exists(self.client_dir):
            os.makedirs(self.client_dir)
            log_and_save(f"📂 Creando directorio para canal: {self.channel_name}", "ERROR", self.ssrc)
        name_wav = os.path.join(self.client_dir, f"record-{time.strftime('%Y%m%d-%H%M%S')}-{ssrc}-{self.channel_name}-{wav_index}.wav")
        wf = wave.open(name_wav, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        log_and_save(f"💾 [Cliente {ssrc}] WAV abierto: {name_wav}", "INFO", self.ssrc)
        self.wav_path = name_wav
        return wf

    def extract_channel_name(self, url):
        import re
        match = re.search(r'youtube\.com/@([^/]+)', url)
        log_and_save(f"🔍 Canal extraído de la URL: {url}", "INFO", self.ssrc)
        if match:
            canal = match.group(1)
            log_and_save(f"🔍 Canal extraído: {canal}", "INFO", self.ssrc)
            return canal
        else:
            log_and_save(f"🔍 Canal extraído: unknown", "INFO", self.ssrc)
            return "unknown"

    def send_rtp_stream_to_jitter(self, data, ssrc, sequence_number):
        total_len = len(data)
        offset = 0
        frame_bytes = FRAME_SIZE * 2
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
        # Asegurar que payload es bytearray
        if not isinstance(payload, bytearray):
            payload = bytearray(payload)
        
        # Usar timestamp basado en samples, no en tiempo real
        timestamp = sequence_number * FRAME_SIZE  # Timestamp basado en samples procesados
        
        rtp_packet = RTP(
            version=RTP_VERSION,  # Usar valor directo 2
            payloadType=PayloadType.DYNAMIC_96,  # Usar PayloadType enum
            sequenceNumber=sequence_number,      # camelCase
            timestamp=timestamp % 2**32,         # Timestamp predecible basado en samples
            ssrc=ssrc,
            payload=payload
        )
        return rtp_packet

    def start_worker_client(self, shutdown_event=None):
        log_and_save(f"[Worker] Iniciado para cliente con SSRC: {self.ssrc}", "INFO", self.ssrc)
        jitter_buffer = self.jitter_buffer
        if shutdown_event is None:
            shutdown_event = getattr(self, 'shutdown_event', None)
        self.wav_start_time = time.time()
        while True:
            if shutdown_event and shutdown_event.is_set():
                log_and_save(f"[Worker] Shutdown event detectado. Cerrando worker SSRC: {self.ssrc}", "INFO", self.ssrc)
                break
            with self.lock:
                # Esperar a que el jitter buffer tenga prefill suficiente
                if not jitter_buffer.ready_to_consume():
                    log_and_save(f"Esperando prefill del Jitter Buffer...", "DEBUG", self.ssrc)
                    if self.handle_inactivity(self.ssrc):
                        break
                    time.sleep(0.005)
                    continue
                        
                next_seq = self.next_seq
                # Procesar paquetes SOLO mientras el buffer siga listo para consumir
                while jitter_buffer.ready_to_consume():
                    packet = jitter_buffer.pop_next(next_seq)
                    if packet is None:
                        break
                    now = time.time()
                    # Lógica de segmentación WAV por tiempo
                    if now - self.wav_start_time >= WAV_SEGMENT_SECONDS:
                        print("DEBUG: enviando a Whisper:", self.wav_path)
                        if self.wavefile:
                            self.wavefile.close()
                        if self.wav_path:
                            self.send_to_whisper(self.wav_path)
                            log_and_save(f"✅ Enviado {self.wav_path} para transcripción.", "INFO", self.ssrc)
                            # Eliminación del wavefile después de enviar a Whisper
                            self.eliminar_wavefile(self.wav_path)
                        self.wavefile = None
                        self.wav_path = None
                        gc.collect()
                        self.wav_index += 1
                        self.wavefile = self.create_wav_file(self.ssrc, wav_index=self.wav_index)
                        self.wav_start_time = time.time()
                        log_and_save(f"[Segmentación] Nuevo archivo WAV para {self.ssrc}, segmento {self.wav_index}", "INFO", self.ssrc)

                    if self.wavefile:
                        self.wavefile.writeframes(packet["payload"])
                    if not packet.get("is_silence", False):
                        self.last_time = now
                    next_seq = (next_seq + 1) % 65536
                self.next_seq = next_seq

                if self.handle_inactivity(self.ssrc):
                    break
            time.sleep(0.005)
    
    def eliminar_wavefile(self, wav_path):
        import os
        try:
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
                log_and_save(f"🗑️ Archivo WAV eliminado: {wav_path}", "INFO", self.ssrc)
        except Exception as e:
            log_and_save(f"❌ Error al eliminar WAV {wav_path}: {e}", "ERROR", self.ssrc)


    def send_to_whisper(self, wav_path: str):
        import requests
        url = MOCK_API_TRANSCRIBE
        """params = {
            "model_path": "/home/soflex/servicios/t_whisper/whisper-v3-turbo-es-ar/checkpoint-14000",
            "language": "Spanish"
        }"""
        params = {
            "source_language": "es",
            "target_language": "es",
            "task": "asr",
            "model": "v2",
            # "gpu_id": "0"  # solo si quieres especificar GPU
        }
        with open(wav_path, "rb") as f:
            files = {"audio": (wav_path, f, "audio/wav")}
            response = requests.post(url, params=params, files=files)

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Transcripción completa de {wav_path}:")
            # Enviar por WebSocket
            self.transcription_client.send_transcription(data.get("transcription", ""))
        else:
            print(f"❌ Error {response.status_code}: {response.text}")


    def cleanup(self):
        """Cierra archivos y libera recursos del cliente RTP."""
        with self.lock:
            if self.wavefile:
                try:
                    self.wavefile.close()
                    self.eliminar_wavefile(self.wav_path)
                except Exception:
                    pass
                self.wavefile = None
            self.jitter_buffer = None
            self.transcription_client.close()
            gc.collect()
        log_and_save(f"[Cleanup] Recursos liberados para cliente SSRC: {self.ssrc}", "INFO", self.ssrc)

    def handle_inactivity(self, ssrc):
        """
        Maneja la inactividad de un cliente, cerrando su archivo WAV si ha estado inactivo durante más de INACTIVITY_TIMEOUT segundos.
        """
        if self.last_time is None:
            return False
        if time.time() - self.last_time > INACTIVITY_TIMEOUT:
            try:
                log_and_save(f"[Worker] Cliente {self.ssrc} inactivo por {INACTIVITY_TIMEOUT}s, cerrando recursos.", "INFO", self.ssrc)
                self.cleanup()
                log_and_save(f"[Worker] Cliente {self.ssrc} inactivo por {INACTIVITY_TIMEOUT}s, recursos liberados.", "INFO", self.ssrc)
            except Exception as e:
                log_and_save(f"[Worker] Error en cleanup de cliente {self.ssrc}: {e}", "ERROR", self.ssrc)
            return True
        return False



