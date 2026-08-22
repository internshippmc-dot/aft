import pyotp

ISSUER = "Actually Fair"


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(email: str, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def verify_code(secret: str, code: str) -> bool:
    if not code:
        return False
    # valid_window=1 tolerates one 30s step of clock drift either side.
    return pyotp.totp.TOTP(secret).verify(code.strip(), valid_window=1)
