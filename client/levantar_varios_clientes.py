import sys
import os
import time
import subprocess
import shutil
import shlex
# ~/Desktop/Soflex/audio-test-env/bin/python 
# main.py "https://www.youtube.com/@olgaenvivo_/live" Chromium F
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
from config import urls_canales

def main():
    formato = "ffmpeg"  # o parec
    navigator = "Firefox"  # o Chrome

    # Intérprete Python a usar dentro del contenedor
    python_env_interprete = os.environ.get("PY_CLIENT_BIN", sys.executable)

    # Ruta correcta a main.py (dentro de este directorio client)
    script_path = os.path.join(os.path.dirname(__file__), "main.py")

    # Elegir terminal disponible si existe
    terminal_bin = shutil.which("gnome-terminal") or shutil.which("xfce4-terminal")

    contador = 1
    for i, url in enumerate(urls_canales):
        print(f"Processing {url}")

        # Comando a ejecutar en shell cuando hay terminal
        cmd = (
            f"{shlex.quote(python_env_interprete)} {shlex.quote(script_path)} "
            f"{shlex.quote(url)} {shlex.quote(navigator)} {shlex.quote(formato)} {contador}; exec bash"
        )

        try:
            if terminal_bin:
                subprocess.Popen([terminal_bin, "--", "bash", "-lc", cmd])
            else:
                # Fallback sin terminal
                subprocess.Popen([
                    python_env_interprete,
                    script_path,
                    url,
                    navigator,
                    formato,
                    str(contador),
                ])
        except Exception as e:
            print(f"No se pudo lanzar el cliente {contador}: {e}")
        finally:
            contador += 1
            time.sleep(5)

if __name__ == "__main__":
    main()
