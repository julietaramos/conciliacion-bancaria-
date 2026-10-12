import hashlib
import hmac
import secrets

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000
BYTES_SAL = 16


def hashear_password(password: str) -> str:
    sal = secrets.token_hex(BYTES_SAL)
    return f"{ALGORITMO}${ITERACIONES}${sal}${_derivar(password, sal, ITERACIONES)}"


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = password_hash.split("$")
    except ValueError:
        return False
    if algoritmo != ALGORITMO:
        return False
    return hmac.compare_digest(_derivar(password, sal, int(iteraciones)), esperado)


def _derivar(password: str, sal: str, iteraciones: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), iteraciones).hex()
