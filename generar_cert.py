# generar_cert.py
"""
Genera un certificado autofirmado (cert.pem) y su clave privada (key.pem)
para usarlos con Flask en HTTPS.
"""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta, timezone
import ipaddress

# 1. Clave privada RSA de 2048 bits
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# 2. Datos del certificado
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "CO"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Valle"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, "Cali"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Proyecto Grado"),
    x509.NameAttribute(NameOID.COMMON_NAME, "192.168.40.14"),
])

# 3. Construir el certificado
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.now(timezone.utc))
    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.ip_address("192.168.40.14")),
            x509.DNSName("localhost"),
        ]),
        critical=False,
    )
    .sign(key, hashes.SHA256())
)

# 4. Guardar clave privada
with open("key.pem", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))

# 5. Guardar certificado
with open("cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("[+] Certificado generado:")
print("    - cert.pem")
print("    - key.pem")
print(f"    - Válido para IP: 192.168.40.14 y localhost")
print(f"    - Expira: {cert.not_valid_after_utc}")