import os
import random
import subprocess
import sys
import threading

from rtp_client import RTPClient
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from my_logger import log, log_and_save
from config import BUFFER_SIZE
FRAME_BYTES = 1920

class RecordClient:
    def __init__(self, client: RTPClient, id_instance):

        self.client: RTPClient = client
        self.sink_name = None
        self.module_id = None
        self.recording_thread = None

        self.sequence_number = 0
        self.id_instance = id_instance
        self.output_dir = None
        self.stop_event = threading.Event()

    def create_pulse_sink(self):
        """Crea un sink de audio único."""

        self.sink_name = f"audio-sink-{random.randint(10000, 99999)}"
        log_and_save(f"🎧 Creating audio sink: {self.sink_name}", "INFO", self.id_instance)

        try:
            result = subprocess.run([
                "pactl", "load-module", "module-null-sink",
                f"sink_name={self.sink_name}"
            ], capture_output=True, text=True, check=True)

            self.module_id = result.stdout.strip()
            log_and_save(f"✅ Audio sink created with module ID: {self.module_id}", "INFO", self.id_instance)

            return self.sink_name

        except subprocess.CalledProcessError as e:
            log_and_save(f"❌ Failed to create audio sink: {e}", "ERROR", self.id_instance)
            return None


    def record_audio(self, pulse_device, formato):
        """Graba y envía un stream continuo de audio usando ffmpeg sin segmentación, con afinidad/prioridad si es Linux."""
        log_and_save("🎵 Starting continuous audio streaming (sin segmentación)", "INFO", self.id_instance)
        import platform
        try:
            # Grabacion con ffmpeg
            if formato == "ffmpeg":
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "pulse",
                    "-i", pulse_device,
                    "-acodec", "pcm_s16le",
                    "-ar", "48000",
                    "-ac", "1",
                    "-f", "s16le",     # ⚠️ NO "wav"
                    "-loglevel", "error",
                    "pipe:1"
                ]
                # Grabacion con parec
            if formato == "parec":
                cmd = [
                    "parec",
                    "-d", pulse_device,
                    "--rate=48000",
                    "--channels=1",
                    "--format=s16le"
                ]

            log_and_save(f"🚀 Starting {formato.upper()} streaming...", "INFO", self.id_instance)
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
                try:
                    leftover = b""
                    while not self.stop_event.is_set():
                        data = process.stdout.read(BUFFER_SIZE)
                        if not data:
                            break
                        data = leftover + data
                        offset = 0
                        try:
                            while offset + FRAME_BYTES <= len(data):
                                frame = data[offset:offset+FRAME_BYTES]
                                self.sequence_number =  self.client.send_rtp_stream_to_jitter(frame, self.id_instance, self.sequence_number)
                                offset += FRAME_BYTES
                            leftover = data[offset:]
                        except Exception as e:
                            log_and_save(f"⚠️ Error enviando audio: {e}", "ERROR", self.id_instance)
                            break
                    if process.poll() is None:
                        log_and_save("Stopping FFmpeg...", "INFO", self.id_instance)
                        process.terminate()
                        try:
                            process.communicate(timeout=5)
                            log_and_save("✅ FFmpeg stopped successfully.", "SUCCESS", self.id_instance)
                        except Exception:
                            pass
                except Exception as e:
                    log_and_save(f"❌ Error in continuous streaming: {e}", "ERROR", self.id_instance)
        except Exception as e:
            log_and_save(f"❌ Error in continuous streaming: {e}", "ERROR", self.id_instance)


    def start_audio_recording(self, pulse_device, formato):
        """Inicia el hilo de grabación de audio."""

        pulse_device_monitor = f"{pulse_device}.monitor"
        log_and_save(f"🎤 Starting audio capture from PulseAudio source: {pulse_device_monitor}", "INFO", self.id_instance)
        self.recording_thread = threading.Thread(
            target=self.record_audio, 
            args=(pulse_device_monitor, formato), 
            daemon=True
        )
        self.recording_thread.start()
        return self.recording_thread


    def cleanup(self):
        """Limpieza de recursos al finalizar."""
        log_and_save("Cleaning up Audio Client Session", "WARN", self.id_instance)

        # Señalar a todos los hilos que paren
        self.stop_event.set()

        # Esperar a que termine el hilo de grabación
        if self.recording_thread and self.recording_thread.is_alive():
            log_and_save("🔥 Waiting for recording thread to finish...", "INFO", self.id_instance)
            self.recording_thread.join(timeout=10)

        # Descargar módulo PulseAudio
        if self.module_id:
            log_and_save(f"🎧 Unloading PulseAudio module: {self.module_id}", "INFO", self.id_instance)
            try:
                subprocess.run(["pactl", "unload-module", self.module_id], check=True)
            except Exception as e:
                log_and_save(f"⚠️ Failed to unload PulseAudio module: {e}", "ERROR", self.id_instance)

        log_and_save("✅ Cleanup: Audio Client Session complete.", "SUCCESS", self.id_instance)

# --- WATCHDOG DE AUDIO (EJEMPLO, NO INTEGRADO) ---
# Este bloque muestra cómo podrías lanzar un hilo watchdog que periódicamente chequea
# si el archivo de audio grabado contiene audio real (no solo silencio) usando ffmpeg.
# No está integrado al flujo principal, solo como referencia para futuras mejoras.
'''
import threading
import subprocess
import time

def watchdog_audio(path_wav, intervalo=30, umbral_db=-50, repeticiones=4):
    """
    Chequea cada 'intervalo' segundos si el archivo WAV tiene audio real.
    Si detecta 'repeticiones' veces seguidas que el nivel RMS está por debajo de 'umbral_db',
    puede disparar una acción correctiva (reinicio, alerta, etc).
    """
    silencios = 0
    while True:
        try:
            # Usar ffmpeg para obtener el nivel RMS del archivo
            cmd = [
                'ffmpeg', '-i', path_wav, '-af', 'volumedetect', '-f', 'null', '-'
            ]
            result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            salida = result.stderr
            # Buscar la línea con 'mean_volume:'
            for linea in salida.split('\n'):
                if 'mean_volume:' in linea:
                    db = float(linea.split('mean_volume:')[1].split(' dB')[0].strip())
                    print(f"[WATCHDOG] mean_volume: {db} dB")
                    if db < umbral_db:
                        silencios += 1
                    else:
                        silencios = 0
                    break
            if silencios >= repeticiones:
                print(f"[WATCHDOG] ¡Audio inactivo detectado! Se recomienda reiniciar grabación o alertar.")
                # Aquí podrías reiniciar el proceso, lanzar una alerta, etc.
                silencios = 0  # O salir del loop si prefieres
        except Exception as e:
            print(f"[WATCHDOG] Error al chequear audio: {e}")
        time.sleep(intervalo)

# Ejemplo de uso (no integrado):
# threading.Thread(target=watchdog_audio, args=("/ruta/al/archivo.wav",), daemon=True).start()
'''
# --- FIN WATCHDOG DE AUDIO ---

