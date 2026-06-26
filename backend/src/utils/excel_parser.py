import io
import math
import re
import pandas as pd


def _find_col(columns, keywords: list[str]) -> str | None:
    """Return the ORIGINAL column name (first match), using stripped/lowered comparison."""
    for col in columns:
        cl = str(col).lower().strip()
        for kw in keywords:
            if kw in cl:
                return col
    return None


def _to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        v = float(value)
        return abs(v) if math.isfinite(v) else 0.0
    cleaned = re.sub(r"[^\d,.\-]", "", str(value)).replace(",", ".")
    try:
        return abs(float(cleaned))
    except ValueError:
        return 0.0


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value
    try:
        result = pd.to_datetime(value, dayfirst=True, errors="coerce")
        return None if pd.isna(result) else result
    except Exception:
        return None


def parse_mayor(file_bytes: bytes, filename: str) -> dict:
    ext = filename.lower().split(".")[-1]
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=object)
    else:
        content = file_bytes.decode("latin-1", errors="replace")
        df = pd.read_csv(io.StringIO(content), dtype=object, skipinitialspace=True)

    # Keep original column names — do NOT strip globally (avoids duplicate-name collisions)
    cols = list(df.columns)

    fecha_col = _find_col(cols, ["fecha", "fec", "date"])
    desc_col  = _find_col(cols, ["leyenda", "concepto", "descripcion", "descripción", "detalle", "movimiento"])
    debe_col  = _find_col(cols, ["debe"])
    haber_col = _find_col(cols, ["haber"])
    # Prefer a plain "saldo" column; exclude "saldo inicial/anterior" (running balance header)
    saldo_col = None
    for col in cols:
        cl = str(col).lower().strip()
        if "saldo" in cl and "inicial" not in cl and "anterior" not in cl:
            saldo_col = col
            break

    if fecha_col is None or debe_col is None or haber_col is None:
        raise ValueError(
            f"No se encontraron columnas en '{filename}'. "
            f"Se necesitan: Fecha, Debe, Haber. Columnas encontradas: {[str(c) for c in cols]}"
        )

    items_debe  = []
    items_haber = []
    saldo_final = 0.0

    for _, row in df.iterrows():
        fecha = _to_date(row[fecha_col])
        if fecha is None:
            continue

        desc  = str(row[desc_col]).strip() if desc_col is not None and row[desc_col] is not None else ""
        debe  = _to_float(row[debe_col])
        haber = _to_float(row[haber_col])
        saldo = _to_float(row[saldo_col]) if saldo_col is not None and row[saldo_col] is not None else 0.0

        if saldo > 0:
            saldo_final = saldo

        if debe > 0:
            items_debe.append({"fecha": fecha, "descripcion": desc, "monto": debe})
        if haber > 0:
            items_haber.append({"fecha": fecha, "descripcion": desc, "monto": haber})

    return {
        "items_debe":  items_debe,
        "items_haber": items_haber,
        "saldo_final": saldo_final,
    }


def _anterior_item(date_v, desc_v, amt_v) -> dict | None:
    fecha = _to_date(date_v)
    if fecha is None:
        return None
    monto = _to_float(amt_v)
    if monto == 0:
        return None
    return {
        "fecha":        fecha,
        "descripcion":  str(desc_v).strip() if desc_v is not None else "",
        "monto":        monto,
        "mes_anterior": True,
    }


def parse_conciliacion_anterior(file_bytes: bytes, filename: str) -> dict:
    """
    Reads a previously generated conciliacion.xlsx and extracts the 4 pending columns
    so they can be carried over into the current month's matching pool.

    Column layout of the generated Excel (1-indexed):
      Col1 = A(fecha) B(concepto) C(importe)   → extracto DÉBITO pending
      Col2 = D(fecha) E(concepto) F(importe)   → mayor   HABER  pending
      Col3 = H(fecha) I(concepto) J(importe)   → mayor   DEBE   pending
      Col4 = K(fecha) L(concepto) M(importe)   → extracto CRÉDITO pending
    Data starts at row 8 (rows 1-7 are headers).
    Stops before the verification tables section (rows starting with a non-date string).
    """
    ext = filename.lower().split(".")[-1]
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=object)
    else:
        raise ValueError("La conciliación anterior debe ser un archivo .xlsx generado por esta app.")

    col1, col2, col3, col4 = [], [], [], []

    for i, row in df.iterrows():
        if i < 7:  # rows 0-6 are header rows
            continue
        vals = list(row)

        # The verification tables that appear below the main data start with a
        # title string in col A (e.g. "✓ Conciliados: HABER ..."). Detect this
        # by checking whether col A is a non-empty, non-date string, and stop.
        if len(vals) > 0 and vals[0] is not None:
            a_str = str(vals[0]).strip()
            if a_str and a_str.lower() not in ("nan", "none"):
                if _to_date(vals[0]) is None:
                    break

        # Col1: A=0, B=1, C=2
        if len(vals) > 2:
            it = _anterior_item(vals[0], vals[1], vals[2])
            if it:
                col1.append(it)

        # Col2: D=3, E=4, F=5
        if len(vals) > 5:
            it = _anterior_item(vals[3], vals[4], vals[5])
            if it:
                col2.append(it)

        # Col3: H=7, I=8, J=9
        if len(vals) > 9:
            it = _anterior_item(vals[7], vals[8], vals[9])
            if it:
                col3.append(it)

        # Col4: K=10, L=11, M=12
        if len(vals) > 12:
            it = _anterior_item(vals[10], vals[11], vals[12])
            if it:
                col4.append(it)

    return {"col1": col1, "col2": col2, "col3": col3, "col4": col4}


def _to_signed_float(value) -> float | None:
    """Parse a value preserving sign. Returns None if not parseable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v if math.isfinite(v) else None
    cleaned = re.sub(r"[^\d,.\-]", "", str(value)).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_extracto(file_bytes: bytes, filename: str) -> dict:
    ext = filename.lower().split(".")[-1]
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=object)
    else:
        content = file_bytes.decode("latin-1", errors="replace")
        df = pd.read_csv(io.StringIO(content), dtype=object, skipinitialspace=True)

    cols = list(df.columns)

    fecha_col   = _find_col(cols, ["fecha", "fec", "date"])
    desc_col    = _find_col(cols, ["descripcion", "descripción", "concepto", "movimiento"])
    saldo_col   = _find_col(cols, ["saldo"])
    importe_col = _find_col(cols, ["importe", "monto", "amount"])
    debito_col  = _find_col(cols, ["debito", "débito", "debit", "cargo", "egreso", "salida"])
    credito_col = _find_col(cols, ["credito", "crédito", "credit", "acredit", "ingreso", "entrada"])

    if fecha_col is None:
        raise ValueError(
            f"No se encontró columna Fecha en '{filename}'. "
            f"Columnas encontradas: {[str(c) for c in cols]}"
        )

    # Formato nuevo: columna importe única con +/- (positivo=crédito, negativo=débito)
    # Formato viejo: columnas separadas Débito y Crédito
    use_importe = importe_col is not None and debito_col is None and credito_col is None

    if not use_importe and (debito_col is None or credito_col is None):
        raise ValueError(
            f"No se encontraron columnas de importes en '{filename}'. "
            f"Se necesita una columna 'importe' (nuevo formato) o columnas 'Débito'/'Crédito' (formato anterior). "
            f"Columnas encontradas: {[str(c) for c in cols]}"
        )

    items_debito  = []
    items_credito = []
    saldo_final   = 0.0

    for _, row in df.iterrows():
        fecha = _to_date(row[fecha_col])
        if fecha is None:
            continue

        desc  = str(row[desc_col]).strip() if desc_col is not None and row[desc_col] is not None else ""
        saldo_raw = row[saldo_col] if saldo_col is not None and row[saldo_col] is not None else None
        if saldo_raw is not None:
            s = _to_signed_float(saldo_raw)
            if s is not None and s > 0:
                saldo_final = s

        if use_importe:
            raw = row[importe_col]
            if raw is None:
                continue
            valor = _to_signed_float(raw)
            if valor is None or valor == 0:
                continue
            monto = abs(valor)
            if valor < 0:
                items_debito.append({"fecha": fecha, "descripcion": desc, "monto": monto})
            else:
                items_credito.append({"fecha": fecha, "descripcion": desc, "monto": monto})
        else:
            debito  = _to_float(row[debito_col])
            credito = _to_float(row[credito_col])
            if debito > 0:
                items_debito.append({"fecha": fecha, "descripcion": desc, "monto": debito})
            if credito > 0:
                items_credito.append({"fecha": fecha, "descripcion": desc, "monto": credito})

    return {
        "items_debito":  items_debito,
        "items_credito": items_credito,
        "saldo_final":   saldo_final,
    }
