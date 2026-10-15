# descifrar.py
import base64
import os
import sys
from cryptography.fernet import Fernet

CLAVE = b"1wmX9QfdSjAc9CSr4uOP0MqqLhgszf_NyO0Aw7iaIuI="  # la misma de cliente.py
CARPETA = "logs_recibidos"

fernet = Fernet(CLAVE)

if len(sys.argv) > 1:
    archivos = [sys.argv[1]]
else:
    archivos = sorted(
        os.path.join(CARPETA, f)
        for f in os.listdir(CARPETA)
        if f.endswith(".txt")
    )

for ruta in archivos:
    with open(ruta, "r", encoding="utf-8") as f:
        b64 = f.read().strip()
    try:
        plano = fernet.decrypt(base64.b64decode(b64)).decode("utf-8")
        print(f"\n===== {os.path.basename(ruta)} =====")
        print(plano)
    except Exception as e:
        print(f"[!] No se pudo descifrar {ruta}: {e}")