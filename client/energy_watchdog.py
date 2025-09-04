import threading
import time
import wave
import numpy as np
import os
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
from my_logger import log_and_save  # noqa: E402

class EnergyWatchdog:
    """
    Analiza WAVs cerrados para estimar energía (RMS) y disparar alerta si
    el nivel promedio se mantiene por debajo de un umbral durante `timeout` segundos.

    - Usa un hilo con cola simple.
    - Siempre libera el semáforo del productor (cliente) aunque falle el análisis.
    - Soporta detención limpia con stop().
    """
    def __init__(self, semaphore, ssrc, umbral=500, timeout=600, check_interval=5, frame_ms=30):
        self.ssrc = ssrc
        self.umbral = float(umbral)
        self.timeout = float(timeout)
        self.check_interval = float(check_interval)
        self.frame_ms = int(frame_ms)

        self.energy_low_since = None

        self._sem_done = semaphore            # semáforo que el productor espera para poder seguir
        self._queue_lock = threading.Lock()
        self._queue = []                      # cola muy simple de paths WAV
        self._stop_evt = threading.Event()

        self._queue_sem = threading.Semaphore(0)  # para despertar el hilo
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ------------------------------
    # API pública
    # ------------------------------
    def notify_wav_ready(self, path_wav: str):
        """El productor (RTPClient) agrega un WAV finalizado para análisis."""
        if not path_wav:
            return
        with self._queue_lock:
            self._queue.append(path_wav)
        self._queue_sem.release()

    def stop(self):
        """Detiene el hilo del watchdog limpiamente."""
        self._stop_evt.set()
        # despertar al hilo si está esperando
        self._queue_sem.release()
        # no bloqueante, pero si querés asegurarte:
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass

    # ------------------------------
    # Hilo interno
    # ------------------------------
    def _run(self):
        while not self._stop_evt.is_set():
            # Espera a que haya trabajo o a que pase check_interval
            got_item = self._queue_sem.acquire(timeout=self.check_interval)
            if not got_item and not self._queue:
                # nada nuevo
                continue

            path_wav = None
            with self._queue_lock:
                if self._queue:
                    path_wav = self._queue.pop(0)

            if not path_wav:
                continue

            try:
                energia = self._energia_audio_wav(path_wav)
                log_and_save(f"[ENERGÍA] Cliente {self.ssrc} energía: {energia:.2f}", "WARN", self.ssrc)

                # Lógica de silencio prolongado
                if energia < self.umbral:
                    now = time.time()
                    if self.energy_low_since is None:
                        self.energy_low_since = now
                        log_and_save(f"[WATCHDOG] Energía baja inicial ({energia:.2f}).", "WARN", self.ssrc)
                    elif (now - self.energy_low_since) > self.timeout:
                        mins = int(self.timeout // 60)
                        log_and_save(f"[WATCHDOG] Silencio > {mins} min. Disparando alerta.", "WARN", self.ssrc)
                        # Aquí podrías invocar callback/WS/lo que necesites
                else:
                    # audio OK: resetea contador
                    if self.energy_low_since is not None:
                        log_and_save(f"[WATCHDOG] Energía recuperada ({energia:.2f}).", "INFO", self.ssrc)
                    self.energy_low_since = None

            except Exception as e:
                log_and_save(f"[WATCHDOG] Error analizando WAV: {e}", "ERROR", self.ssrc)
            finally:
                # Pase lo que pase, liberar al productor para que no se quede esperando
                try:
                    self._sem_done.release()
                except Exception:
                    pass

        # flush final: liberar a cualquiera que espere
        try:
            while True:
                self._sem_done.release()
        except ValueError:
            # en py3 el semáforo no tira ValueError por overflow, pero por si acaso
            pass
        except Exception:
            pass

    # ------------------------------
    # Cálculo de energía (RMS)
    # ------------------------------
    def _energia_audio_wav(self, path_wav: str) -> float:
        with wave.open(path_wav, 'rb') as wf:
            n_channels = wf.getnchannels()
            fr = wf.getframerate()
            n_frames = wf.getnframes()
            audio = wf.readframes(n_frames)

        # int16 mono o interleaved si stereo
        arr = np.frombuffer(audio, dtype=np.int16)
        if n_channels == 2:
            # promedio entre canales para RMS global
            arr = arr.reshape(-1, 2).mean(axis=1).astype(np.int16)

        # tamaño de frame interno en samples (por canal ya colapsado)
        frame_size = max(1, int(fr * self.frame_ms / 1000))
        if frame_size <= 0:
            frame_size = 1

        total = len(arr)
        if total == 0:
            return 0.0

        # Partir en frames y calcular RMS por frame; devolver RMS promedio
        rms_vals = []
        for i in range(0, total, frame_size):
            frame = arr[i:i + frame_size].astype(np.float64)
            if frame.size == 0:
                continue
            rms = float(np.sqrt(np.mean(frame * frame)))
            rms_vals.append(rms)

        if not rms_vals:
            return 0.0
        return float(np.mean(rms_vals))
