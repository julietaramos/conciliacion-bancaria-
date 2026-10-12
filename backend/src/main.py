import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from utils.excel_parser import parse_mayor, parse_extracto, parse_conciliacion_anterior
from utils.reconciliation import reconcile
from utils.excel_report import generate_excel_report
from auth.service import (
    DURACION_SESION, SESSION_COOKIE, auth_habilitada, cerrar_sesion, iniciar_sesion,
    inicializar_usuario_principal, usuario_de_sesion,
)
from db.database import SessionLocal, init_db, get_db
from db.crud import (
    get_bancos, get_banco, create_banco, delete_banco,
    save_conciliacion, get_ultima_conciliacion, get_anterior_data,
    delete_ultima_conciliacion, upsert_anterior_partidas,
)

load_dotenv()

APP_TZ  = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Argentina/Buenos_Aires"))
TIMEOUT = int(os.getenv("RECONCILE_TIMEOUT", "60"))

# ── Auth (usuarios con datos separados) ─────────────────────────────────────────
# Sin usuarios cargados ni APP_PASSWORD (uso local con iniciar.bat) el gate queda
# desactivado y los datos no tienen dueño, igual que antes de existir usuarios.
SESION_MAX_AGE_SEGUNDOS = int(DURACION_SESION.total_seconds())
RUTAS_PUBLICAS = ("/api/login", "/api/logout", "/api/session")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        inicializar_usuario_principal(db)
    yield


app = FastAPI(title="Conciliaciones Bancarias API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolver_acceso(token: str | None) -> tuple[bool, object]:
    """Devuelve (autorizado, usuario_id) para la cookie de sesión recibida."""
    with SessionLocal() as db:
        if not auth_habilitada(db):
            return True, None
        usuario = usuario_de_sesion(db, token)
        return usuario is not None, usuario.id if usuario else None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api") or path in RUTAS_PUBLICAS:
            return await call_next(request)
        autorizado, usuario_id = await asyncio.to_thread(_resolver_acceso, request.cookies.get(SESSION_COOKIE))
        if not autorizado:
            return JSONResponse({"detail": "No autorizado."}, status_code=401)
        request.state.usuario_id = usuario_id
        return await call_next(request)


app.add_middleware(AuthMiddleware)


def get_usuario_id(request: Request):
    return getattr(request.state, "usuario_id", None)


class LoginIn(BaseModel):
    usuario: str
    password: str


@app.post("/api/login")
def login(body: LoginIn, response: Response, request: Request, db: Session = Depends(get_db)):
    token = iniciar_sesion(db, body.usuario, body.password)
    if not token:
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    response.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite="lax", secure=(request.url.scheme == "https"),
        max_age=SESION_MAX_AGE_SEGUNDOS,
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    cerrar_sesion(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/session")
def session_check(request: Request, db: Session = Depends(get_db)):
    if not auth_habilitada(db):
        return {"authenticated": True, "usuario": None}
    usuario = usuario_de_sesion(db, request.cookies.get(SESSION_COOKIE))
    return {"authenticated": usuario is not None, "usuario": usuario.nombre if usuario else None}


def _banco_del_usuario(db: Session, banco_id: str | None, usuario_id):
    banco = get_banco(db, banco_id, usuario_id) if banco_id else None
    if not banco:
        raise HTTPException(404, "Banco no encontrado.")
    return banco


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_conciliacion(row) -> dict | None:
    if not row:
        return None
    return {
        "fecha_proceso":  row.fecha_proceso.astimezone(APP_TZ).strftime("%d/%m/%Y") if row.fecha_proceso else None,
        "fecha_datos":    row.fecha_datos.strftime("%d/%m/%Y") if row.fecha_datos else None,
        "saldo_banco":    float(row.saldo_banco) if row.saldo_banco is not None else None,
        "saldo_contable": float(row.saldo_contable) if row.saldo_contable is not None else None,
        "diferencia":     float(row.diferencia) if row.diferencia is not None else None,
        "estado":         row.estado,
        "resumen":        row.resumen,
    }


def _serialize_item(item: dict) -> dict:
    fecha = item.get("fecha")
    fecha_str = fecha.isoformat() if fecha is not None and hasattr(fecha, "isoformat") else None
    return {
        "id":           str(uuid.uuid4()),
        "fecha":        fecha_str,
        "descripcion":  item.get("descripcion", ""),
        "monto":        round(float(item.get("monto", 0)), 2),
        "mes_anterior": bool(item.get("mes_anterior", False)),
    }


def _item_to_internal(item: dict) -> dict:
    fecha = None
    raw = item.get("fecha")
    if raw:
        try:
            fecha = datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            pass
    return {
        "fecha":        fecha,
        "descripcion":  item.get("descripcion", ""),
        "monto":        float(item.get("monto", 0)),
        "mes_anterior": bool(item.get("mes_anterior", False)),
    }


def _ajustes_to_internal(raw_ajustes: list) -> list:
    result = []
    for a in raw_ajustes:
        items = [_item_to_internal(it) | {"categoria": it.get("categoria")} for it in a.get("items", [])]
        result.append({
            "monto":  round(float(a.get("monto", 0)), 2),
            "motivo": a.get("motivo") or "",
            "items":  items,
        })
    return result


def _match_to_internal(m: dict) -> dict:
    return {
        "id":   m.get("id"),
        "col1": [_item_to_internal(x) for x in m.get("col1", [])],
        "col2": [_item_to_internal(x) for x in m.get("col2", [])],
        "col3": [_item_to_internal(x) for x in m.get("col3", [])],
        "col4": [_item_to_internal(x) for x in m.get("col4", [])],
    }


def _result_from_state(state: dict) -> dict:
    col1 = [_item_to_internal(x) for x in state.get("col1", [])]
    col2 = [_item_to_internal(x) for x in state.get("col2", [])]
    col3 = [_item_to_internal(x) for x in state.get("col3", [])]
    col4 = [_item_to_internal(x) for x in state.get("col4", [])]
    ajustes = _ajustes_to_internal(state.get("ajustes", []))
    matched = [_match_to_internal(m) for m in state.get("matched", [])]

    partidas = round(
        sum(x["monto"] for x in col1)
        - sum(x["monto"] for x in col2)
        + sum(x["monto"] for x in col3)
        - sum(x["monto"] for x in col4),
        2,
    )

    saldo_banco             = float(state.get("saldo_banco", 0))
    saldo_contable_original = float(state.get("saldo_contable", 0))
    ajustes_total           = round(sum(a["monto"] for a in ajustes), 2)
    saldo_contable          = round(saldo_contable_original + ajustes_total, 2)
    diferencia              = round(saldo_banco + partidas - saldo_contable, 2)

    fecha_datos = None
    raw_fd = state.get("fecha_datos")
    if raw_fd:
        try:
            fecha_datos = date.fromisoformat(raw_fd)
        except (ValueError, TypeError):
            pass

    return {
        "col1": col1, "col2": col2, "col3": col3, "col4": col4,
        "matched":                  matched,
        "ajustes":                 ajustes,
        "saldo_banco":             saldo_banco,
        "saldo_contable":          saldo_contable,
        "saldo_contable_original": saldo_contable_original,
        "partidas":                partidas,
        "diferencia":              diferencia,
        "fecha_datos":             fecha_datos,
    }


async def _parse_archivos(mayor_file: UploadFile, banco_file: UploadFile):
    mayor_bytes = await mayor_file.read()
    banco_bytes = await banco_file.read()

    try:
        mayor_data = await asyncio.wait_for(
            asyncio.to_thread(parse_mayor, mayor_bytes, mayor_file.filename),
            timeout=TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Timeout al procesar el Mayor Contable.")
    except ValueError as e:
        raise HTTPException(422, str(e))

    try:
        extracto_data = await asyncio.wait_for(
            asyncio.to_thread(parse_extracto, banco_bytes, banco_file.filename),
            timeout=TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Timeout al procesar el Extracto Bancario.")
    except ValueError as e:
        raise HTTPException(422, str(e))

    if not mayor_data["items_debe"] and not mayor_data["items_haber"]:
        raise HTTPException(422, "El Mayor Contable no tiene movimientos válidos.")
    if not extracto_data["items_debito"] and not extracto_data["items_credito"]:
        raise HTTPException(422, "El Extracto Bancario no tiene movimientos válidos.")

    return mayor_data, extracto_data


# ── Bancos ────────────────────────────────────────────────────────────────────

class BancoIn(BaseModel):
    nombre: str


@app.get("/api/bancos")
def listar_bancos(db: Session = Depends(get_db), usuario_id=Depends(get_usuario_id)):
    bancos = get_bancos(db, usuario_id)
    return [
        {
            "id":     str(b.id),
            "nombre": b.nombre,
            "ultima_conciliacion": _fmt_conciliacion(get_ultima_conciliacion(db, str(b.id))),
        }
        for b in bancos
    ]


@app.post("/api/bancos", status_code=201)
def agregar_banco(body: BancoIn, db: Session = Depends(get_db), usuario_id=Depends(get_usuario_id)):
    if not body.nombre.strip():
        raise HTTPException(422, "El nombre del banco no puede estar vacío.")
    banco = create_banco(db, body.nombre, usuario_id)
    return {"id": str(banco.id), "nombre": banco.nombre}


@app.delete("/api/bancos/{banco_id}", status_code=204)
def eliminar_banco(banco_id: str, db: Session = Depends(get_db), usuario_id=Depends(get_usuario_id)):
    if not delete_banco(db, banco_id, usuario_id):
        raise HTTPException(404, "Banco no encontrado.")


# ── Conciliación anterior (gestión manual) ────────────────────────────────────

@app.delete("/api/bancos/{banco_id}/anterior", status_code=204)
def eliminar_anterior(banco_id: str, db: Session = Depends(get_db), usuario_id=Depends(get_usuario_id)):
    _banco_del_usuario(db, banco_id, usuario_id)
    delete_ultima_conciliacion(db, banco_id)


@app.post("/api/bancos/{banco_id}/anterior")
async def subir_anterior(
    banco_id: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_id=Depends(get_usuario_id),
):
    _banco_del_usuario(db, banco_id, usuario_id)

    file_bytes = await archivo.read()
    try:
        anterior_data = await asyncio.to_thread(
            parse_conciliacion_anterior, file_bytes, archivo.filename
        )
    except ValueError as e:
        raise HTTPException(422, str(e))

    from db.crud import _serialize_items
    partidas = {
        "col1": _serialize_items(anterior_data["col1"]),
        "col2": _serialize_items(anterior_data["col2"]),
        "col3": _serialize_items(anterior_data["col3"]),
        "col4": _serialize_items(anterior_data["col4"]),
    }
    upsert_anterior_partidas(db, banco_id, partidas, usuario_id)
    return {"ok": True}


# ── Conciliar: preview ────────────────────────────────────────────────────────

@app.post("/api/conciliar/preview")
async def preview_endpoint(
    banco_id: str        = Form(...),
    mayor:    UploadFile = File(...),
    banco:    UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_id=Depends(get_usuario_id),
):
    _banco_del_usuario(db, banco_id, usuario_id)

    mayor_data, extracto_data = await _parse_archivos(mayor, banco)
    anterior_data = await asyncio.to_thread(get_anterior_data, db, banco_id)
    result = await asyncio.to_thread(reconcile, mayor_data, extracto_data, anterior_data)

    return {
        "banco_id":     banco_id,
        "saldo_banco":    result["saldo_banco"],
        "saldo_contable": result["saldo_contable"],
        "partidas":       result["partidas"],
        "diferencia":     result["diferencia"],
        "fecha_datos":    result["fecha_datos"].isoformat() if result["fecha_datos"] else None,
        "col1": [_serialize_item(x) for x in result["col1"]],
        "col2": [_serialize_item(x) for x in result["col2"]],
        "col3": [_serialize_item(x) for x in result["col3"]],
        "col4": [_serialize_item(x) for x in result["col4"]],
        "matched_haber_debito": [
            {"id": str(uuid.uuid4()), "mayor": _serialize_item(m), "extractos": [_serialize_item(e) for e in exts]}
            for m, exts in result["matched_haber_debito"]
        ],
        "matched_debe_credito": [
            {"id": str(uuid.uuid4()), "mayor": _serialize_item(m), "extractos": [_serialize_item(e) for e in exts]}
            for m, exts in result["matched_debe_credito"]
        ],
    }


# ── Conciliar: generar desde estado revisado ──────────────────────────────────

@app.post("/api/conciliar/generar")
async def generar_endpoint(
    body: dict,
    db: Session = Depends(get_db),
    usuario_id=Depends(get_usuario_id),
):
    banco_id = body.get("banco_id")
    _banco_del_usuario(db, banco_id, usuario_id)

    result      = await asyncio.to_thread(_result_from_state, body)
    excel_bytes = await asyncio.to_thread(generate_excel_report, result)
    await asyncio.to_thread(
        save_conciliacion, db, result, banco_id, excel_bytes, estado_editable=body, usuario_id=usuario_id,
    )

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=conciliacion.xlsx"},
    )


# ── Editar última conciliación ──────────────────────────────────────────────────

@app.get("/api/bancos/{banco_id}/ultima/editar")
def obtener_ultima_editable(banco_id: str, db: Session = Depends(get_db), usuario_id=Depends(get_usuario_id)):
    _banco_del_usuario(db, banco_id, usuario_id)
    ultima = get_ultima_conciliacion(db, banco_id)
    if not ultima or not ultima.estado_editable:
        raise HTTPException(404, "No hay una conciliación editable guardada para este banco.")
    return ultima.estado_editable


# ── Descarga última conciliación ──────────────────────────────────────────────

@app.get("/api/bancos/{banco_id}/ultima/excel")
def descargar_ultima(banco_id: str, db: Session = Depends(get_db), usuario_id=Depends(get_usuario_id)):
    _banco_del_usuario(db, banco_id, usuario_id)
    ultima = get_ultima_conciliacion(db, banco_id)
    if not ultima or not ultima.excel_output:
        raise HTTPException(404, "No hay conciliación disponible para descargar.")
    return Response(
        content=bytes(ultima.excel_output),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=conciliacion.xlsx"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Frontend estático (build de producción) ─────────────────────────────────────
# Solo se monta si el build existe (deploy con Docker); en desarrollo local el
# frontend corre aparte con `npm run dev` + proxy de Vite, así que esto no aplica.
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        return FileResponse(_FRONTEND_DIST / "index.html")
