import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from auth.passwords import hashear_password, verificar_password
from db import usuarios as repo
from db.models import Usuario

SESSION_COOKIE = "cb_session"
DURACION_SESION = timedelta(days=30)
BYTES_TOKEN = 32
USUARIO_PRINCIPAL_DEFAULT = "guillermo"


def password_legacy() -> str | None:
    """APP_PASSWORD: la contraseña compartida previa a los usuarios. Mantiene el
    gate de login activo y crea al usuario principal en el primer arranque."""
    return os.getenv("APP_PASSWORD")


def auth_habilitada(db: Session) -> bool:
    return bool(password_legacy()) or repo.contar_usuarios(db) > 0


def alta_usuario(db: Session, nombre: str, password: str) -> Usuario:
    """El primer usuario que se crea se queda con los bancos y conciliaciones
    cargados antes de que existieran usuarios."""
    es_primer_usuario = repo.contar_usuarios(db) == 0
    usuario = repo.crear_usuario(db, nombre, hashear_password(password))
    if es_primer_usuario:
        repo.asignar_datos_sin_usuario(db, usuario.id)
    return usuario


def cambiar_password(db: Session, usuario: Usuario, password: str) -> None:
    repo.actualizar_password(db, usuario, hashear_password(password))


def inicializar_usuario_principal(db: Session) -> None:
    password = password_legacy()
    if not password or repo.contar_usuarios(db) > 0:
        return
    nombre = os.getenv("APP_USUARIO_PRINCIPAL", USUARIO_PRINCIPAL_DEFAULT)
    alta_usuario(db, nombre, password)


def iniciar_sesion(db: Session, nombre: str, password: str) -> str | None:
    usuario = repo.get_usuario_por_nombre(db, nombre.strip())
    if not usuario or not verificar_password(password, usuario.password_hash):
        return None
    token = secrets.token_urlsafe(BYTES_TOKEN)
    repo.crear_sesion(db, _hash_token(token), usuario.id, datetime.now(timezone.utc) + DURACION_SESION)
    return token


def usuario_de_sesion(db: Session, token: str | None) -> Usuario | None:
    if not token:
        return None
    sesion = repo.get_sesion(db, _hash_token(token))
    if not sesion or _expirada(sesion.expira):
        return None
    return sesion.usuario


def cerrar_sesion(db: Session, token: str | None) -> None:
    if token:
        repo.borrar_sesion(db, _hash_token(token))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _expirada(expira: datetime) -> bool:
    if expira.tzinfo is None:  # SQLite devuelve datetimes naive
        expira = expira.replace(tzinfo=timezone.utc)
    return expira <= datetime.now(timezone.utc)
