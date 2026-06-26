import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, date
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from utils.excel_parser import parse_mayor, parse_extracto, parse_conciliacion_anterior
from utils.reconciliation import reconcile
from utils.excel_report import generate_excel_report
from db.database import init_db, get_db
from db.crud import (
    get_bancos, get_banco, create_banco, delete_banco,
    save_conciliacion, get_ultima_conciliacion, get_anterior_data,
    delete_ultima_conciliacion, upsert_anterior_partidas,
)

load_dotenv()

APP_TZ  = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Argentina/Buenos_Aires"))
TIMEOUT = int(os.getenv("RECONCILE_TIMEOUT", "60"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Conciliaciones Bancarias API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def _result_from_state(state: dict) -> dict:
    col1 = [_item_to_internal(x) for x in state.get("col1", [])]
    col2 = [_item_to_internal(x) for x in state.get("col2", [])]
    col3 = [_item_to_internal(x) for x in state.get("col3", [])]
    col4 = [_item_to_internal(x) for x in state.get("col4", [])]

    def _expand_pairs(raw_pairs):
        result = []
        for p in raw_pairs:
            mayor = _item_to_internal(p["mayor"])
            extractos = p.get("extractos") or ([p["extracto"]] if p.get("extracto") else [])
            result.append((mayor, [_item_to_internal(e) for e in extractos]))
        return result

    matched_hd = _expand_pairs(state.get("matched_haber_debito", []))
    matched_dc = _expand_pairs(state.get("matched_debe_credito", []))

    partidas = round(
        sum(x["monto"] for x in col1)
        - sum(x["monto"] for x in col2)
        + sum(x["monto"] for x in col3)
        - sum(x["monto"] for x in col4),
        2,
    )

    saldo_banco    = float(state.get("saldo_banco", 0))
    saldo_contable = float(state.get("saldo_contable", 0))
    diferencia     = round(saldo_banco + partidas - saldo_contable, 2)

    fecha_datos = None
    raw_fd = state.get("fecha_datos")
    if raw_fd:
        try:
            fecha_datos = date.fromisoformat(raw_fd)
        except (ValueError, TypeError):
            pass

    return {
        "col1": col1, "col2": col2, "col3": col3, "col4": col4,
        "matched_haber_debito": matched_hd,
        "matched_debe_credito": matched_dc,
        "saldo_banco":    saldo_banco,
        "saldo_contable": saldo_contable,
        "partidas":       partidas,
        "diferencia":     diferencia,
        "fecha_datos":    fecha_datos,
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
def listar_bancos(db: Session = Depends(get_db)):
    bancos = get_bancos(db)
    return [
        {
            "id":     str(b.id),
            "nombre": b.nombre,
            "ultima_conciliacion": _fmt_conciliacion(get_ultima_conciliacion(db, str(b.id))),
        }
        for b in bancos
    ]


@app.post("/api/bancos", status_code=201)
def agregar_banco(body: BancoIn, db: Session = Depends(get_db)):
    if not body.nombre.strip():
        raise HTTPException(422, "El nombre del banco no puede estar vacío.")
    banco = create_banco(db, body.nombre)
    return {"id": str(banco.id), "nombre": banco.nombre}


@app.delete("/api/bancos/{banco_id}", status_code=204)
def eliminar_banco(banco_id: str, db: Session = Depends(get_db)):
    if not delete_banco(db, banco_id):
        raise HTTPException(404, "Banco no encontrado.")


# ── Conciliación anterior (gestión manual) ────────────────────────────────────

@app.delete("/api/bancos/{banco_id}/anterior", status_code=204)
def eliminar_anterior(banco_id: str, db: Session = Depends(get_db)):
    if not get_banco(db, banco_id):
        raise HTTPException(404, "Banco no encontrado.")
    delete_ultima_conciliacion(db, banco_id)


@app.post("/api/bancos/{banco_id}/anterior")
async def subir_anterior(
    banco_id: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not get_banco(db, banco_id):
        raise HTTPException(404, "Banco no encontrado.")

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
    upsert_anterior_partidas(db, banco_id, partidas)
    return {"ok": True}


# ── Conciliar: preview ────────────────────────────────────────────────────────

@app.post("/api/conciliar/preview")
async def preview_endpoint(
    banco_id: str        = Form(...),
    mayor:    UploadFile = File(...),
    banco:    UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not get_banco(db, banco_id):
        raise HTTPException(404, "Banco no encontrado.")

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
):
    banco_id = body.get("banco_id")
    if not banco_id or not get_banco(db, banco_id):
        raise HTTPException(404, "Banco no encontrado.")

    result      = await asyncio.to_thread(_result_from_state, body)
    excel_bytes = await asyncio.to_thread(generate_excel_report, result)
    await asyncio.to_thread(save_conciliacion, db, result, banco_id, excel_bytes)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=conciliacion.xlsx"},
    )


# ── Descarga última conciliación ──────────────────────────────────────────────

@app.get("/api/bancos/{banco_id}/ultima/excel")
def descargar_ultima(banco_id: str, db: Session = Depends(get_db)):
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
