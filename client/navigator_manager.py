import subprocess
import os
import random
import sys
import tempfile
import psutil
import time
import shutil

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from my_logger import log_and_save

class Navigator():
    def __init__(self, name, sink_name, ssrc, user_count):
        self.navigator_name = name
        self.profile_path = None
        self.sink_name = sink_name
        self.ssrc = ssrc
        self.user_count = user_count

        self.browser_process = None
        self.navigator_profile_dir = None

        self.random_id = random.randint(10000, 99999)


    def use_existing_profile(self):
        """Crea un directorio de perfil para el navegador."""
        from config import DIR_CHROME_USER_david, DIR_CHROME_USER_lucia, DIR_CHROMIUM_USER, DIR_FIREFOX_USER_david
        if self.navigator_name == "Chrome":
            if self.user_count % 2 == 0:
                log_and_save(f"🛠️ Usando perfil de David: {DIR_CHROME_USER_david}", "INFO", self.ssrc)
                self.navigator_profile_dir = DIR_CHROME_USER_david
                return DIR_CHROME_USER_david
            else:
                log_and_save(f"🛠️ Usando perfil de Lucia: {DIR_CHROME_USER_lucia}", "INFO", self.ssrc)
                self.navigator_profile_dir = DIR_CHROME_USER_lucia
                return DIR_CHROME_USER_lucia
        elif self.navigator_name == "Chromium":
            return DIR_CHROMIUM_USER
        elif self.navigator_name == "Firefox":
            return DIR_FIREFOX_USER_david 
        else:
            #return self.create_chrome_chromium_profile()
            log_and_save("❌ Navegador no soportado", "ERROR", self.ssrc)
            return None


    def launch_navigator(self, url, display_num = None):
        """Lanza el navegador especificado con el sink preconfigurado y perfil ya creado."""
        log_and_save(f"🚀 Launching {self.navigator_name} with URL: {url}", "INFO", self.ssrc)

        # Variables de entorno
        env = os.environ.copy()
        env["PULSE_SINK"] = self.sink_name
        if display_num:
            env["DISPLAY"] = display_num
        try:
            if self.navigator_name == "Chrome" or self.navigator_name == "Chromium":
                self.browser_process = self.launch_chrome_chromium(url, env)
            elif self.navigator_name == "Firefox":
                self.browser_process = self.launch_firefox(url, env)
            log_and_save(f"✅ {self.navigator_name} launched with preconfigured audio sink and autoplay", "INFO", self.ssrc)
            return self.browser_process
        except Exception as e:
            log_and_save(f"❌ Error lanzando {self.navigator_name}: {e}", "ERROR", self.ssrc)
            return None

    def launch_firefox(self, url, env):
        """Lanza Firefox"""
        from flags_nav_ffmpeg.flags_comunes import FIREFOX_COMMON_FLAGS
        from config import DIR_FIREFOX_USER_david
        log_and_save(f"🚀 Launching Firefox with URL: {url}", "INFO", self.ssrc)
        base_cmd = ["firefox"]
        #profile_args = ["--profile", DIR_FIREFOX_USER_david]
        log_and_save(f"Using Firefox for url: {url}", "INFO", self.ssrc)
        cmd = (
            base_cmd
            + FIREFOX_COMMON_FLAGS
            #+ profile_args
            + [url]
        )
        try:
            self.browser_process = subprocess.Popen(cmd, env=env)
            log_and_save(f"✅ Firefox launched successfully", "INFO", self.ssrc)
            # Intento de auto-play: enviar tecla 'k' (YouTube play/pause)
            self._try_autoplay(env, app_class="firefox")
            return self.browser_process
        except Exception as e:
            log_and_save(f"❌ Error lanzando Firefox: {e}", "ERROR", self.ssrc)
            return None

    def launch_chrome_chromium(self, url, env):
        """Lanza Google Chrome o Chromium"""
        from flags_nav_ffmpeg.flags_comunes import CHROME_CHROMIUM_COMMON_FLAGS
        import platform

        navigator_name = self.navigator_name.lower()
        if navigator_name == "chrome":
            base_cmd = ["google-chrome"]
            profile_args = [f"--user-data-dir={os.path.dirname(self.navigator_profile_dir)}", f"--profile-directory={os.path.basename(self.navigator_profile_dir)}"]
        else:
            base_cmd = ["chromium"]
            profile_args = [f"--user-data-dir={os.path.dirname(self.navigator_profile_dir)}"]
        cmd = (
            base_cmd
            + CHROME_CHROMIUM_COMMON_FLAGS
            + profile_args
            + [url]
        )
        return subprocess.Popen(cmd, env=env)

    def _try_autoplay(self, env, app_class: str = None):
        """Intenta simular 'play' con xdotool: activa la ventana del navegador y envía 'k'."""
        try:
            if not shutil.which("xdotool"):
                log_and_save("[Autoplay] xdotool no encontrado; omitiendo auto-play.", "WARN", self.ssrc)
                return
            # Esperar a que la ventana aparezca
            time.sleep(2)
            search_cmd = ["xdotool", "search", "--onlyvisible"]
            if app_class:
                search_cmd += ["--class", app_class]
            else:
                search_cmd += ["--name", self.navigator_name]
            # Buscar ventana
            res = subprocess.run(search_cmd, env=env, capture_output=True, text=True)
            if res.returncode != 0 or not res.stdout.strip():
                log_and_save("[Autoplay] No se encontró ventana para auto-play.", "WARN", self.ssrc)
                return
            win_id = res.stdout.strip().splitlines()[-1]
            # Activar ventana y enviar 'k'
            subprocess.run(["xdotool", "windowactivate", "--sync", win_id], env=env)
            time.sleep(0.2)
            subprocess.run(["xdotool", "key", "k"], env=env)
            log_and_save("[Autoplay] Tecla 'k' enviada para reproducir.", "INFO", self.ssrc)
        except Exception as e:
            log_and_save(f"[Autoplay] Error intentando auto-play: {e}", "WARN", self.ssrc)

    def _graceful_close_windows(self):
        """Intenta cerrar el navegador como un usuario: windowclose/Alt+F4 con xdotool."""
        try:
            if not self.browser_process or self.browser_process.poll() is not None:
                return True
            if not shutil.which("xdotool"):
                log_and_save("[Close] xdotool no encontrado; no se puede cerrar amigablemente.", "WARN", self.ssrc)
                return False

            env = os.environ.copy()
            pid = self.browser_process.pid
            # Buscar ventanas por PID (más preciso)
            res = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(pid)],
                                 env=env, capture_output=True, text=True)
            win_ids = []
            if res.returncode == 0 and res.stdout.strip():
                win_ids = [w for w in res.stdout.strip().splitlines() if w.strip()]
            else:
                # Fallback por clase/nombre
                search_cmd = ["xdotool", "search", "--onlyvisible"]
                if self.navigator_name.lower() == "firefox":
                    search_cmd += ["--class", "firefox"]
                elif self.navigator_name.lower() == "chrome":
                    search_cmd += ["--class", "google-chrome"]
                else:
                    search_cmd += ["--name", self.navigator_name]
                res2 = subprocess.run(search_cmd, env=env, capture_output=True, text=True)
                if res2.returncode == 0 and res2.stdout.strip():
                    win_ids = [w for w in res2.stdout.strip().splitlines() if w.strip()]

            if not win_ids:
                log_and_save("[Close] No se encontraron ventanas visibles para cerrar.", "WARN", self.ssrc)
                return False

            # Intentar cerrar cada ventana del proceso
            for wid in win_ids:
                subprocess.run(["xdotool", "windowactivate", "--sync", wid], env=env)
                # Intento 1: WM_DELETE
                subprocess.run(["xdotool", "windowclose", wid], env=env)
                time.sleep(0.2)
            # Esperar hasta 3s a que termine el proceso
            for _ in range(15):
                if self.browser_process.poll() is not None:
                    log_and_save("[Close] Navegador cerrado amigablemente (windowclose).", "INFO", self.ssrc)
                    return True
                time.sleep(0.2)

            # Intento 2: Alt+F4 por si alguna ventana insiste
            for wid in win_ids:
                subprocess.run(["xdotool", "windowactivate", "--sync", wid], env=env)
                subprocess.run(["xdotool", "key", "Alt+F4"], env=env)
                time.sleep(0.2)
            for _ in range(15):
                if self.browser_process.poll() is not None:
                    log_and_save("[Close] Navegador cerrado con Alt+F4.", "INFO", self.ssrc)
                    return True
                time.sleep(0.2)

            return False
        except Exception as e:
            log_and_save(f"[Close] Error en cierre amigable: {e}", "WARN", self.ssrc)
            return False

    def terminate_child_processes(self, browser_process):
        if browser_process.poll() is None:  # el padre sigue vivo
            try:
                parent = psutil.Process(browser_process.pid)
                children = parent.children(recursive=True)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                return

            if not children:
                log_and_save("No child processes found to terminate.", "WARN", self.ssrc)
                return

            for child in children:
                log_and_save(f"⚠️ Killing child process {child.pid}", "WARN", self.ssrc)
                try:
                    child.terminate()
                except Exception:
                    pass

            gone, alive = psutil.wait_procs(children, timeout=3)
            for p in alive:
                log_and_save(f"⚠️ Forcibly killing child process {p.pid}", "WARN", self.ssrc)
                try:
                    p.kill()
                except Exception:
                    pass
        else:
            log_and_save("No child processes to terminate.", "INFO", self.ssrc)

    def cerrar_navegador(self):
        """Cierra el proceso de navegador (Chrome/Chromium/Firefox) y sus hijos si están en ejecución."""
        if hasattr(self, 'browser_process') and self.browser_process:
            log_and_save("🔥 Terminating navegador...", "WARN", self.ssrc)
            log_and_save(f"Proceso de navegador: {self.browser_process.pid}", "INFO", self.ssrc)

            try:
                # 1. Intento amable vía xdotool (WM_DELETE / Alt+F4)
                closed = self._graceful_close_windows()
                if closed:
                    return

                # 2. Señal suave al proceso principal
                if self.browser_process.poll() is None:
                    self.browser_process.terminate()
                    try:
                        self.browser_process.communicate(timeout=5)
                    except Exception:
                        pass

                # 3. Si aún quedan hijos colgados, limpiarlos
                if self.browser_process.poll() is None:
                    self.terminate_child_processes(self.browser_process)

            except Exception as e:
                log_and_save(f"⚠️ Failed to terminate navegador: {e}", "ERROR", self.ssrc)
                try:
                    self.browser_process.kill()
                except Exception:
                    pass
    
    def limpiar_perfil_navegador(self):
        log_and_save("🔥 Cleaning up navegador profile...", "WARN", self.ssrc)
        if self.navigator_profile_dir and os.path.exists(self.navigator_profile_dir):
            try:
                import shutil
                shutil.rmtree(self.navigator_profile_dir)
                log_and_save(f"🗑️ Perfil Navegador eliminado: {self.navigator_profile_dir}", "SUCCESS", self.ssrc)
            except Exception as e:
                log_and_save(f"⚠️ Error eliminando perfil Navegador: {e}", "ERROR", self.ssrc)

    def cleanup(self):
        """Limpia los recursos utilizados por el administrador del navegador."""
        self.cerrar_navegador()
        #self.limpiar_perfil_navegador()
