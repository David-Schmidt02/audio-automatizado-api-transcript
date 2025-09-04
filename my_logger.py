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
    print(f"{color}[{timestamp}] [{level}] {message}{Colors.END}")



from path_utils import resolve_writable_dir, LOG_BASE

def log_and_save(message, level, ssrc):
    # consola con color, igual que tenías
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{level}] {message}")

    base_dir = os.path.abspath(os.path.dirname(__file__))  # carpeta del repo
    preferred = os.path.join(base_dir, "client", "logs")
    log_dir   = resolve_writable_dir(preferred, LOG_BASE)

    log_file = os.path.join(log_dir, f"{ssrc}-client.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{level}] {message}\n")
