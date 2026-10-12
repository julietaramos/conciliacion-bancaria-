from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Banco, Conciliacion, Sesion, Usuario


def contar_usuarios(db: Session) -> int:
    return db.query(Usuario).count()


def get_usuario_por_nombre(db: Session, nombre: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.nombre == nombre).first()


def crear_usuario(db: Session, nombre: str, password_hash: str) -> Usuario:
    usuario = Usuario(nombre=nombre, password_hash=password_hash)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_password(db: Session, usuario: Usuario, password_hash: str) -> None:
    usuario.password_hash = password_hash
    db.query(Sesion).filter(Sesion.usuario_id == usuario.id).delete(synchronize_session=False)
    db.commit()


def asignar_datos_sin_usuario(db: Session, usuario_id) -> None:
    for modelo in (Banco, Conciliacion):
        db.query(modelo).filter(modelo.user_id.is_(None)).update(
            {modelo.user_id: usuario_id}, synchronize_session=False,
        )
    db.commit()


def crear_sesion(db: Session, token_hash: str, usuario_id, expira: datetime) -> None:
    db.add(Sesion(token_hash=token_hash, usuario_id=usuario_id, expira=expira))
    db.commit()


def get_sesion(db: Session, token_hash: str) -> Sesion | None:
    return db.query(Sesion).filter(Sesion.token_hash == token_hash).first()


def borrar_sesion(db: Session, token_hash: str) -> None:
    db.query(Sesion).filter(Sesion.token_hash == token_hash).delete(synchronize_session=False)
    db.commit()
