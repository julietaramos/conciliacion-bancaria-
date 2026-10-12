import pytest
from fastapi.testclient import TestClient

from auth.passwords import hashear_password, verificar_password
from auth.service import USUARIO_PRINCIPAL_DEFAULT, alta_usuario, cambiar_password, inicializar_usuario_principal
from db.models import Banco, Conciliacion, Sesion, Usuario
from db.usuarios import get_usuario_por_nombre

PASSWORD_A = "clave-de-prueba-a"
PASSWORD_B = "clave-de-prueba-b"


@pytest.fixture()
def base_limpia(db_session, monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    def limpiar():
        for modelo in (Sesion, Conciliacion, Banco, Usuario):
            db_session.query(modelo).delete()
        db_session.commit()

    limpiar()
    yield db_session
    limpiar()


def _cliente_logueado(usuario: str, password: str) -> TestClient:
    from main import app
    cliente = TestClient(app)
    respuesta = cliente.post("/api/login", json={"usuario": usuario, "password": password})
    assert respuesta.status_code == 200
    return cliente


def test_hash_de_password_verifica_solo_la_correcta():
    password_hash = hashear_password(PASSWORD_A)

    assert PASSWORD_A not in password_hash
    assert verificar_password(PASSWORD_A, password_hash)
    assert not verificar_password(PASSWORD_B, password_hash)


def test_sin_usuarios_la_app_queda_abierta_como_antes(base_limpia, client):
    assert client.get("/api/session").json() == {"authenticated": True, "usuario": None}
    assert client.get("/api/bancos").status_code == 200


def test_primer_usuario_se_queda_con_los_datos_existentes(base_limpia, client):
    client.post("/api/bancos", json={"nombre": "Banco previo"})

    alta_usuario(base_limpia, "guillermo", PASSWORD_A)
    alta_usuario(base_limpia, "tester2", PASSWORD_B)

    guillermo = _cliente_logueado("guillermo", PASSWORD_A)
    tester2 = _cliente_logueado("tester2", PASSWORD_B)
    assert [b["nombre"] for b in guillermo.get("/api/bancos").json()] == ["Banco previo"]
    assert tester2.get("/api/bancos").json() == []


def test_cada_usuario_ve_y_toca_solo_sus_bancos(base_limpia):
    alta_usuario(base_limpia, "guillermo", PASSWORD_A)
    alta_usuario(base_limpia, "tester2", PASSWORD_B)
    guillermo = _cliente_logueado("guillermo", PASSWORD_A)
    tester2 = _cliente_logueado("tester2", PASSWORD_B)

    banco_guillermo = guillermo.post("/api/bancos", json={"nombre": "Provincia"}).json()["id"]
    tester2.post("/api/bancos", json={"nombre": "Galicia"})

    assert [b["nombre"] for b in guillermo.get("/api/bancos").json()] == ["Provincia"]
    assert [b["nombre"] for b in tester2.get("/api/bancos").json()] == ["Galicia"]
    assert tester2.get(f"/api/bancos/{banco_guillermo}/ultima/excel").status_code == 404
    assert tester2.get(f"/api/bancos/{banco_guillermo}/ultima/editar").status_code == 404
    assert tester2.delete(f"/api/bancos/{banco_guillermo}").status_code == 404
    assert tester2.post("/api/conciliar/generar", json={"banco_id": banco_guillermo}).status_code == 404
    assert len(guillermo.get("/api/bancos").json()) == 1


def test_con_usuarios_hay_que_loguearse(base_limpia, client):
    alta_usuario(base_limpia, "guillermo", PASSWORD_A)

    assert client.get("/api/session").json() == {"authenticated": False, "usuario": None}
    assert client.get("/api/bancos").status_code == 401
    assert client.post("/api/login", json={"usuario": "guillermo", "password": PASSWORD_B}).status_code == 401
    assert client.post("/api/login", json={"usuario": "otro", "password": PASSWORD_A}).status_code == 401


def test_logout_cierra_la_sesion(base_limpia):
    alta_usuario(base_limpia, "guillermo", PASSWORD_A)
    cliente = _cliente_logueado("guillermo", PASSWORD_A)
    assert cliente.get("/api/session").json() == {"authenticated": True, "usuario": "guillermo"}

    cliente.post("/api/logout")

    assert cliente.get("/api/bancos").status_code == 401


def test_cambiar_password_cierra_sesiones_abiertas(base_limpia):
    usuario = alta_usuario(base_limpia, "guillermo", PASSWORD_A)
    cliente = _cliente_logueado("guillermo", PASSWORD_A)

    cambiar_password(base_limpia, usuario, PASSWORD_B)

    assert cliente.get("/api/bancos").status_code == 401
    _cliente_logueado("guillermo", PASSWORD_B)


def test_app_password_crea_al_usuario_principal_una_sola_vez(base_limpia, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", PASSWORD_A)

    inicializar_usuario_principal(base_limpia)
    inicializar_usuario_principal(base_limpia)

    assert base_limpia.query(Usuario).count() == 1
    assert get_usuario_por_nombre(base_limpia, USUARIO_PRINCIPAL_DEFAULT) is not None
    _cliente_logueado(USUARIO_PRINCIPAL_DEFAULT, PASSWORD_A)
