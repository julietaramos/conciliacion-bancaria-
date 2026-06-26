from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Banco, Conciliacion


def get_bancos(db: Session) -> list[Banco]:
    return db.query(Banco).order_by(Banco.created_at).all()


def get_banco(db: Session, banco_id: str) -> Banco | None:
    return db.query(Banco).filter(Banco.id == banco_id).first()


def create_banco(db: Session, nombre: str) -> Banco:
    banco = Banco(nombre=nombre.strip())
    db.add(banco)
    db.commit()
    db.refresh(banco)
    return banco


def delete_banco(db: Session, banco_id: str) -> bool:
    banco = db.query(Banco).filter(Banco.id == banco_id).first()
    if not banco:
        return False
    db.delete(banco)
    db.commit()
    return True


def _serialize_items(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        s = dict(item)
        if s.get("fecha") is not None and hasattr(s["fecha"], "isoformat"):
            s["fecha"] = s["fecha"].isoformat()
        result.append(s)
    return result


def _deserialize_items(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        d = dict(item)
        if d.get("fecha") is not None:
            try:
                d["fecha"] = datetime.fromisoformat(d["fecha"])
            except (ValueError, TypeError):
                d["fecha"] = None
        d["mes_anterior"] = True
        result.append(d)
    return result


def save_conciliacion(db: Session, result: dict, banco_id: str | None = None, excel_bytes: bytes | None = None) -> Conciliacion:
    estado = "balanceada" if abs(result.get("diferencia") or 0) < 0.02 else "con_diferencias"

    row = Conciliacion(
        banco_id   = banco_id,
        fecha_datos    = result.get("fecha_datos"),
        saldo_banco    = result.get("saldo_banco"),
        saldo_contable = result.get("saldo_contable"),
        diferencia     = result.get("diferencia"),
        estado         = estado,
        resumen        = {
            "debitos_no_contab":    len(result.get("col1", [])),
            "haber_no_debitados":   len(result.get("col2", [])),
            "no_acreditados":       len(result.get("col3", [])),
            "creditos_no_contab":   len(result.get("col4", [])),
            "matched_haber_debito": len(result.get("matched_haber_debito", [])),
            "matched_debe_credito": len(result.get("matched_debe_credito", [])),
        },
        excel_output        = excel_bytes,
        partidas_pendientes = {
            "col1": _serialize_items(result.get("col1", [])),
            "col2": _serialize_items(result.get("col2", [])),
            "col3": _serialize_items(result.get("col3", [])),
            "col4": _serialize_items(result.get("col4", [])),
        },
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if banco_id:
        db.query(Conciliacion).filter(
            Conciliacion.banco_id == banco_id,
            Conciliacion.id != row.id,
        ).delete(synchronize_session=False)
        db.commit()

    return row


def get_ultima_conciliacion(db: Session, banco_id: str) -> Conciliacion | None:
    return (
        db.query(Conciliacion)
        .filter(Conciliacion.banco_id == banco_id)
        .order_by(Conciliacion.fecha_proceso.desc())
        .first()
    )


def delete_ultima_conciliacion(db: Session, banco_id: str) -> bool:
    ultima = get_ultima_conciliacion(db, banco_id)
    if not ultima:
        return False
    db.delete(ultima)
    db.commit()
    return True


def upsert_anterior_partidas(db: Session, banco_id: str, partidas: dict) -> Conciliacion:
    ultima = get_ultima_conciliacion(db, banco_id)
    if ultima:
        ultima.partidas_pendientes = partidas
        db.commit()
        db.refresh(ultima)
        return ultima
    row = Conciliacion(banco_id=banco_id, estado="manual", partidas_pendientes=partidas)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_anterior_data(db: Session, banco_id: str) -> dict | None:
    ultima = get_ultima_conciliacion(db, banco_id)
    if not ultima or not ultima.partidas_pendientes:
        return None
    pp = ultima.partidas_pendientes
    return {
        "col1": _deserialize_items(pp.get("col1", [])),
        "col2": _deserialize_items(pp.get("col2", [])),
        "col3": _deserialize_items(pp.get("col3", [])),
        "col4": _deserialize_items(pp.get("col4", [])),
    }
