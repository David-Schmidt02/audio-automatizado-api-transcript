import threading
import time
import wave
import numpy as np
import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from my_logger import log_and_save

class EnergyWatchdog:
    def __init__(self, semaphore, ssrc, umbral=500, timeout=600, check_interval=5, frame_ms=30):
        """
        semaphore     : threading.Semaphore para proteger el WAV hasta ser analizado
        ssrc          : identificador del cliente
        umbral        : RMS mínimo para considerar actividad
        timeout       : tiempo en segundos de silencio prolongado antes de disparar alerta
        check_interval: intervalo en segundos para revisar la cola de WAVs
        frame_ms      : ventana en ms para calcular RMS interno
        """
        self.ssrc = ssrc
        self.umbral = umbral
        self.timeout = timeout
        self.check_interval = check_interval
        self.frame_ms = frame_ms

        self.energy_low_since = None
        self.semaphore_delete_wav = semaphore
        self._wav_queue = []
        self._lock = threading.Lock()
        self._stop = False

        self.semaphore_queue = threading.Semaphore(0)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def notify_wav_ready(self, path_wav):
        """Agregar WAV a la cola para procesar"""
        with self._lock:
            self._wav_queue.append(path_wav)
        self.semaphore_queue.release()

    def energia_audio_wav(self, path_wav):
        """Calcula RMS promedio por frames internos de 30 ms"""
        wf = wave.open(path_wav, 'rb')
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        wf.close()

        frame_size = int(wf.getframerate() * self.frame_ms / 1000)
        n_frames = len(audio) // frame_size
        rms_values = [np.sqrt(np.mean(audio[i*frame_size:(i+1)*frame_size].astype(np.float64)**2))
                      for i in range(n_frames)]
        return np.mean(rms_values)

    def run(self):
        while not self._stop:
            self.semaphore_queue.acquire()
            path_wav = None
            with self._lock:
                if self._wav_queue:
                    path_wav = self._wav_queue.pop(0)

            if path_wav:
                try:
                    energia = self.energia_audio_wav(path_wav)
                    log_and_save(f"[ENERGÍA] Cliente {self.ssrc} energía: {energia:.2f}", "WARN", self.ssrc)
                except Exception as e:
                    print(f"[ENERGÍA] Error analizando {path_wav}: {e}")
                    energia = None

                # Liberamos siempre el semáforo al terminar de analizar
                self.semaphore_delete_wav.release()

                if energia is not None:
                    if energia < self.umbral:
                        now = time.time()
                        log_and_save(f"[WATCHDOG] Cliente {self.ssrc} energía baja: {energia:.2f}", "WARN", self.ssrc)
                        if self.energy_low_since is None:
                            self.energy_low_since = now
                        elif now - self.energy_low_since > self.timeout:
                            log_and_save(f"[WATCHDOG] Cliente {self.ssrc} silencio > {self.timeout//60} min. Disparando alerta.", "WARN", self.ssrc)
                            # Aquí podrías avisar a un callback, log, o al backend
                    else:
                        self.energy_low_since = None


    def stop(self):
        self._stop = True