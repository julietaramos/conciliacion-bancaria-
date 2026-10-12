"""Alta de usuarios / cambio de contraseña.

    python crear_usuario.py <usuario>                     crea el usuario
    python crear_usuario.py <usuario> --cambiar-password  le cambia la contraseña

Usa la base de DATABASE_URL (o el SQLite local si no está seteada). La contraseña
se pide por consola, nunca va como argumento. El primer usuario que se crea se
queda con los bancos y conciliaciones cargados antes de que existieran usuarios.
"""
import argparse
import getpass
import sys

from dotenv import load_dotenv

load_dotenv()

from auth.service import alta_usuario, cambiar_password  # noqa: E402 — necesita el .env cargado
from db.database import SessionLocal, init_db  # noqa: E402
from db.usuarios import get_usuario_por_nombre  # noqa: E402

LARGO_MINIMO_PASSWORD = 8


def pedir_password() -> str:
    password = getpass.getpass("Contraseña: ")
    if len(password) < LARGO_MINIMO_PASSWORD:
        sys.exit(f"La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres.")
    if password != getpass.getpass("Repetir contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Alta de usuarios de Conciliaciones Bancarias.")
    parser.add_argument("usuario")
    parser.add_argument("--cambiar-password", action="store_true")
    args = parser.parse_args()
    nombre = args.usuario.strip()

    init_db()
    with SessionLocal() as db:
        existente = get_usuario_por_nombre(db, nombre)
        if args.cambiar_password:
            if not existente:
                sys.exit(f"No existe el usuario '{nombre}'.")
            cambiar_password(db, existente, pedir_password())
            print(f"Contraseña de '{nombre}' actualizada. Sus sesiones abiertas se cerraron.")
            return
        if existente:
            sys.exit(f"El usuario '{nombre}' ya existe. Usá --cambiar-password para cambiarle la contraseña.")
        alta_usuario(db, nombre, pedir_password())
        print(f"Usuario '{nombre}' creado.")


if __name__ == "__main__":
    main()
