import io
import math
import re
import unicodedata
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
        saldo = _to_signed_float(row[saldo_col]) if saldo_col is not None and row[saldo_col] is not None else None

        if saldo is not None:
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


def _normalize(value) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


# Each group's header label maps to its "fecha" (first) column — the group's
# concepto/importe columns are always the next two columns to the right.
# Matched by label text rather than fixed column letters because different
# reconciliation templates (the app's own output vs. externally supplied
# "anterior" files like the accountant's manual model) pad/offset columns
# differently, even though the 4-group layout itself is the same.
_GROUP_LABELS = {
    "col1": "debitos no contabilizados",   # extracto DÉBITO pending
    "col2": "no debitados",                # mayor   HABER  pending
    "col3": "no acreditados",              # mayor   DEBE   pending
    "col4": "creditos no contabilizados",  # extracto CRÉDITO pending
}


def _find_group_columns(df) -> tuple[int, dict]:
    """Scan the top of the sheet for the 4 group header labels.

    Returns (header_row, {col_key: fecha_column_index}), both 0-indexed.
    Raises ValueError if any group's header can't be located.
    """
    n_rows, n_cols = df.shape
    header_row = None
    found = {}

    for r in range(min(n_rows, 15)):
        for c in range(n_cols):
            val = df.iat[r, c]
            if not isinstance(val, str):
                continue
            norm = _normalize(val)
            for key, label in _GROUP_LABELS.items():
                if key not in found and label in norm:
                    found[key] = c
        if len(found) == 4:
            header_row = r
            break

    missing = [key for key in _GROUP_LABELS if key not in found]
    if missing:
        raise ValueError(
            "No se pudieron ubicar las columnas de pendientes en el archivo "
            f"(faltan: {', '.join(missing)}). Verificá que tenga los encabezados "
            "'Débitos no Contabilizados', 'No Debitados', 'No Acreditados' y "
            "'Créditos no Contabilizados'."
        )
    return header_row, found


def parse_conciliacion_anterior(file_bytes: bytes, filename: str) -> dict:
    """
    Reads a previous month's reconciliation (either generated by this app or an
    externally supplied file, e.g. an accountant's manual template) and extracts
    the 4 pending-items groups so they can be carried over into the current
    month's matching pool.

    Each group is a 3-column block (fecha, concepto, importe); its position is
    located by its header label rather than a fixed column, so both this app's
    own output and differently-offset external files parse correctly.
    """
    ext = filename.lower().split(".")[-1]
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=object)
    else:
        raise ValueError("La conciliación anterior debe ser un archivo .xlsx.")

    header_row, group_cols = _find_group_columns(df)
    pendientes = {"col1": [], "col2": [], "col3": [], "col4": []}
    fecha_col_ref = group_cols["col1"]

    # Templates put a text sub-header ("Fecha"/"Concepto"/"Importe") right below
    # the group header row before the actual data starts — skip it by checking
    # whether the first group's importe column already holds a number.
    data_start = header_row + 1
    importe_col = fecha_col_ref + 2
    if data_start < len(df) and importe_col < df.shape[1]:
        if not isinstance(df.iat[data_start, importe_col], (int, float)):
            data_start += 1

    for i, row in df.iterrows():
        if i < data_start:
            continue
        vals = list(row)

        # The verification tables that appear below the main data (in this app's
        # own output) start with a title string in the reference column (e.g.
        # "✓ Conciliados: HABER ..."). Detect this and stop before it.
        ref_val = vals[fecha_col_ref] if fecha_col_ref < len(vals) else None
        if ref_val is not None:
            ref_str = str(ref_val).strip()
            if ref_str and ref_str.lower() not in ("nan", "none") and _to_date(ref_val) is None:
                break

        for key, col in group_cols.items():
            if col + 2 < len(vals):
                it = _anterior_item(vals[col], vals[col + 1], vals[col + 2])
                if it:
                    pendientes[key].append(it)

    return pendientes


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
            if s is not None:
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
