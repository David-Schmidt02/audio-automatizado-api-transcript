import logging
import datetime
import os

# Configuración del logger
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)

# Colores para el logging
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'  # Reset color

def log(message, level="INFO"):
    """Sistema de logging con colores usando hora local y guardado en archivo."""
    now = datetime.datetime.now()
    timestamp = now.strftime("%H:%M:%S")

    color_map = {
        "INFO": Colors.CYAN,
        "WARN": Colors.YELLOW,
        "ERROR": Colors.RED,
        "SUCCESS": Colors.GREEN,
        "DEBUG": Colors.MAGENTA,
        "HEADER": Colors.BLUE + Colors.BOLD
    }
    color = color_map.get(level, Colors.WHITE)
    line = f"[{timestamp}] [{level}] {message}"
    print(f"{color}{line}{Colors.END}")
    return line


LOG_DIR = os.environ.get("SOFLEX_LOGDIR", "/home/soflex/logs")
os.makedirs(LOG_DIR, exist_ok=True)

def log_and_save(message, level, ssrc):
    """Loguea con color, guarda en archivo global y en archivo por cliente."""
    line = log(message, level)
    # Archivo específico del cliente (client/logs/<ssrc>-client.log)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    client_log_dir = os.path.join(base_dir, "client", "logs")
    os.makedirs(client_log_dir, exist_ok=True)
    client_log_file = os.path.join(client_log_dir, f"{ssrc}-client.log")
    with open(client_log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")
