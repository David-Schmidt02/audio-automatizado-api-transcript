import sys
import os
import time
import subprocess
# ~/Desktop/Soflex/audio-test-env/bin/python 
# main.py "https://www.youtube.com/@olgaenvivo_/live" Chromium F
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
from config import urls_canales


def main():
    formato = "ffmpeg" # o parec
    navigator = "Chrome"
    env_active = os.path.expanduser("~/Escritorio/Soflex/audio-test-env/bin/activate")
    python_env_interprete = os.path.expanduser("~/Escritorio/Soflex/audio-test-env/bin/python")
    script_path = os.path.abspath("main.py")
    #num_cores = 6  # Cambia este valor según los núcleos que quieras usar

    for i, url in enumerate(urls_canales):
        print(f"Processing {url}")
        #core = i % num_cores  # Asigna núcleo de forma cíclica
        """cmd = f"taskset -c {core} {python_env_interprete} {script_path} '{url}' '{navigator}' '{formato}'; exec bash"
        """
        cmd = f"{python_env_interprete} {script_path} '{url}' '{navigator}' '{formato}'; exec bash"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", cmd])
        time.sleep(20)

if __name__ == "__main__":
    main()
