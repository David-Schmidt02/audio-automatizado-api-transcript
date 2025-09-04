import os
import sys
import time

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
from my_logger import log_and_save
from config import JITTER_BUFFER_SIZE, MAX_WAIT, FRAME_SIZE, CHANNELS

class JitterBuffer:
    """
    Versión simple:
      - Prefill por tamaño (JITTER_BUFFER_SIZE)
      - Lleva expected_seq internamente
      - Inyecta silencio después de MAX_WAIT si falta el paquete esperado
    """
    def __init__(self, ssrc, jt_bf_size=JITTER_BUFFER_SIZE, max_wait=MAX_WAIT):
        self.ssrc = ssrc
        self.buffer = {}              # seq_num -> (arrival_ts, payload)
        self.prefill_min = jt_bf_size
        self.prefill_done = False
        self.max_wait = max_wait

        self.expected_seq = None
        self.last_seq_time = None     # (seq, time)
        self.missing_since = None

    def _seq_inc(self, x): return (x + 1) & 0xFFFF

    def add_packet(self, seq_num, arrival_ts, payload):
        if seq_num % 1000 == 0:
            log_and_save(f"[JitterBuffer] Paquete N° {seq_num} añadido", "DEBUG", self.ssrc)

        if self.expected_seq is None:
            self.expected_seq = seq_num

        self.buffer[seq_num] = (arrival_ts, payload)

        if not self.prefill_done and len(self.buffer) >= self.prefill_min:
            self.prefill_done = True
            log_and_save(f"[JitterBuffer] Prefill completado con {len(self.buffer)} paquetes", "INFO", self.ssrc)

    def ready_to_consume(self):
        return self.prefill_done

    def pop_next(self, next_seq=None):
        """
        Si `next_seq` viene del caller, lo usamos; si no, usamos `expected_seq`.
        Devuelve:
          - {"payload": ..., "is_silence": False} si llegó el esperado
          - {"payload": silencio, "is_silence": True} si se venció MAX_WAIT
          - None si hay que esperar
        """
        frame_bytes = FRAME_SIZE * CHANNELS * 2
        now = time.time()

        if next_seq is None:
            next_seq = self.expected_seq
        else:
            # sincronizar el interno si el caller avanza
            self.expected_seq = next_seq if self.expected_seq is None else self.expected_seq

        if self.expected_seq is None or not self.prefill_done:
            return None

        # Llego el esperado
        if self.expected_seq in self.buffer:
            _, payload = self.buffer.pop(self.expected_seq)
            self.last_seq_time = (self.expected_seq, now)
            self.missing_since = None
            self.expected_seq = self._seq_inc(self.expected_seq)
            return {"payload": payload, "is_silence": False}

        # Falta el esperado: medir espera
        if self.missing_since is None:
            self.missing_since = now
            return None

        if (now - self.missing_since) > self.max_wait:
            # Inyectar silencio de un frame y avanzar
            self.last_seq_time = (self.expected_seq, now)
            self.missing_since = None
            self.expected_seq = self._seq_inc(self.expected_seq)
            return {"payload": b"\x00" * frame_bytes, "is_silence": True}

        return None

    def get_size(self):
        return len(self.buffer)

    def discard_old(self, current_timestamp):
        to_remove = [seq for seq, (ts, _) in self.buffer.items() if ts < current_timestamp - 10]
        for seq in to_remove:
            del self.buffer[seq]
