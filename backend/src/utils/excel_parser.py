import io
import math
import re
import pandas as pd

from utils.column_mapping import Formato, es_vacio, normalizar


def leer_monto(value) -> float | None:
    if es_vacio(value) or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v if math.isfinite(v) else None
    text = str(value)
    digits = re.sub(r"[^\d,.]", "", text)
    if not re.search(r"\d", digits):
        return None
    try:
        number = float(_normalize_decimal_separator(digits))
    except ValueError:
        return None
    return -number if "-" in text else number


def _normalize_decimal_separator(digits: str) -> str:
    """Accepts both 1.234,56 (AR) and 1,234.56: the last separator present is the decimal one."""
    if "," in digits and "." in digits:
        decimal, thousands = (",", ".") if digits.rfind(",") > digits.rfind(".") else (".", ",")
        return digits.replace(thousands, "").replace(decimal, ".")
    if digits.count(",") > 1 or digits.count(".") > 1:
        return digits.replace(",", "").replace(".", "")
    return digits.replace(",", ".")


def _to_float(value) -> float:
    number = leer_monto(value)
    return abs(number) if number is not None else 0.0


def es_monto_invalido(value) -> bool:
    return not es_vacio(value) and leer_monto(value) is None


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


def fecha_de_movimiento(value):
    """Bare numbers would parse as 1970 timestamps, so they never count as a movement date."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return None
    return _to_date(value)


def filas_con_fecha(formato: Formato):
    columna_fecha = formato.columna("fecha")
    for _, row in formato.datos.iterrows():
        fecha = fecha_de_movimiento(row[columna_fecha])
        if fecha is not None:
            yield fecha, row


def _texto(row, columna: str | None) -> str:
    if columna is None or es_vacio(row[columna]):
        return ""
    return str(row[columna]).strip()


def _exigir_valido(formato: Formato) -> None:
    if formato.es_valido:
        return
    raise ValueError(f"{formato.esquema.nombre}: " + " ".join(formato.errores))


def parse_mayor(formato: Formato) -> dict:
    _exigir_valido(formato)
    col_desc, col_debe, col_haber, col_saldo = (
        formato.columna(c) for c in ("descripcion", "debe", "haber", "saldo")
    )

    items_debe  = []
    items_haber = []
    saldo_final = 0.0

    for fecha, row in filas_con_fecha(formato):
        desc  = _texto(row, col_desc)
        debe  = _to_float(row[col_debe])
        haber = _to_float(row[col_haber])
        saldo = leer_monto(row[col_saldo]) if col_saldo is not None else None

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


def parse_extracto(formato: Formato) -> dict:
    _exigir_valido(formato)
    col_desc, col_saldo = formato.columna("descripcion"), formato.columna("saldo")
    usa_importe_con_signo = formato.modo_importe() == ("importe",)

    items_debito  = []
    items_credito = []
    saldo_final   = 0.0

    for fecha, row in filas_con_fecha(formato):
        desc  = _texto(row, col_desc)
        saldo = leer_monto(row[col_saldo]) if col_saldo is not None else None
        if saldo is not None:
            saldo_final = saldo

        if usa_importe_con_signo:
            valor = leer_monto(row[formato.columna("importe")])
            if not valor:
                continue
            destino = items_debito if valor < 0 else items_credito
            destino.append({"fecha": fecha, "descripcion": desc, "monto": abs(valor)})
            continue

        debito  = _to_float(row[formato.columna("debito")])
        credito = _to_float(row[formato.columna("credito")])
        if debito > 0:
            items_debito.append({"fecha": fecha, "descripcion": desc, "monto": debito})
        if credito > 0:
            items_credito.append({"fecha": fecha, "descripcion": desc, "monto": credito})

    return {
        "items_debito":  items_debito,
        "items_credito": items_credito,
        "saldo_final":   saldo_final,
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
            norm = normalizar(val)
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
