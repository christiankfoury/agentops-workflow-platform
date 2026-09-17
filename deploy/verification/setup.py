"""Generate fresh, ignored, local-only verification secrets; never overwrite them."""

import ipaddress
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / ".local" / "production"


def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def private(value):
    return value.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


def main():
    DEST.mkdir(parents=True, exist_ok=False)
    DEST.chmod(0o700)
    now = datetime.now(UTC)
    ca_key, tls_key = key(), key()
    ca_name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "AgentOps disposable verification")]
    )
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca_name)
        .public_key(tls_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("gateway"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    password = secrets.token_urlsafe(32)
    files = {
        "ca.crt": ca.public_bytes(serialization.Encoding.PEM),
        "tls.crt": certificate.public_bytes(serialization.Encoding.PEM),
        "tls.key": private(tls_key),
        "oidc.key": private(key()),
        "database_password": password.encode(),
        "database_url": f"postgresql://agentops:{password}@db:5432/agentops".encode(),
        "oidc_client_secret": b"",
    }
    for name, value in files.items():
        (DEST / name).write_bytes(value)
        # Parent is private on POSIX; files must be readable by the non-root
        # container UID when Compose uses bind-backed secrets.
        (DEST / name).chmod(0o644)
    (DEST / "compose.env").write_text(
        f"SECRET_DIR={DEST.as_posix()}\nAPP_ORIGIN=https://localhost:8443\n"
        "OIDC_ISSUER=https://localhost:8443/oidc\nOIDC_CLIENT_ID=agentops-verification\n"
        "OIDC_JWKS_URL=https://gateway:8443/oidc/jwks\n"
        "OIDC_AUTHORIZE_URL=https://localhost:8443/oidc/authorize\n"
        "OIDC_TOKEN_URL=https://gateway:8443/oidc/token\n",
        encoding="utf-8",
    )
    print(f"Created ephemeral verification files in {DEST}; valid for seven days")


if __name__ == "__main__":
    main()
