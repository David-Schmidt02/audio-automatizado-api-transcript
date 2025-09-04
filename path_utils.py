# path_utils.py
import os
import sys

# Detecta automáticamente si estamos en Docker o en host local
def is_running_in_docker():
    """Determina si el código se ejecuta dentro de un contenedor Docker"""
    # Verifica si existe el archivo /.dockerenv que Docker crea
    docker_env = os.path.exists('/.dockerenv')
    # Verifica si el cgroup contiene docker (otra señal común)
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return docker_env or 'docker' in f.read()
    except:
        return docker_env

# Base de datos/escritura configurable según entorno
if is_running_in_docker():
    # Paths para Docker
    DATA_BASE = os.environ.get("SOFLEX_DATA_DIR", "/home/soflex/data")
    LOG_BASE = os.environ.get("SOFLEX_FALLBACK_LOGDIR", "/home/soflex/logs")
else:
    # Paths para host local
    DATA_BASE = os.environ.get("SOFLEX_DATA_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "data")))
    LOG_BASE = os.environ.get("SOFLEX_FALLBACK_LOGDIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "logs")))

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def resolve_writable_dir(preferred_dir: str, fallback_base: str) -> str:
    """
    Intenta crear/escribir en preferred_dir; si no puede, cae a fallback_base/<basename(preferred_dir)>
    """
    # Primero intentamos el directorio preferido
    try:
        ensure_dir(preferred_dir)
        test = os.path.join(preferred_dir, ".perm_test")
        with open(test, "w") as f: f.write("")
        os.remove(test)
        return preferred_dir
    except Exception:
        # Determinamos el fallback apropiado según el entorno
        if is_running_in_docker():
            # En Docker, usamos las rutas del contenedor
            fb = os.path.join(fallback_base, os.path.basename(preferred_dir))
        else:
            # En host local, creamos directorios dentro del proyecto
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
            fb = os.path.join(project_root, os.path.basename(fallback_base), os.path.basename(preferred_dir))
        
        try:
            ensure_dir(fb)
            print(f"INFO: Sin permisos para {preferred_dir}, usando: {fb}")
            return fb
        except Exception as e:
            print(f"ERROR: No se pudo crear directorio alternativo {fb}: {e}")
            raise
