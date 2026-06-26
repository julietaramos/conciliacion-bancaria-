import io
import re
import pdfplumber
from pypdf import PdfReader
import pandas as pd

DATE_KEYWORDS = ["fecha", "fec", "date"]
DESC_KEYWORDS = ["concepto", "descripcion", "descripción", "detalle", "detail", "movimiento", "glosa"]
REF_KEYWORDS = ["referencia", "comprobante", "nro op", "nro_op", "operacion", "id", "numero", "nro", "cheque"]
DEBIT_KEYWORDS = ["debito", "débito", "debit", "cargo", "salida", "egreso"]
CREDIT_KEYWORDS = ["credito", "crédito", "credit", "acreditacion", "entrada", "ingreso"]
AMOUNT_KEYWORDS = ["importe", "monto", "amount", "valor", "movimiento"]
DEBE_KEYWORDS = ["debe"]
HABER_KEYWORDS = ["haber"]

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
CHEQUE_REF_RE = re.compile(r"\b(\d{7,12})\b")

# Galicia / Nación: DD/MM/YYYY CONCEPTO IMPORTE DD-MM SALDO
_STRICT_DATE_START = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+)$")
_STRICT_RIGHT = re.compile(r"\s+(-?[\d.,]+)\s+\d{2}-\d{2}\s+-?[\d.,]+\s*$")

# Generic: DD/MM/YYYY CONCEPTO IMPORTE  (last token is the amount)
_LOOSE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s{2,}(-?[\d.,]+)\s*$")

# Alternative: single space before amount at EOL
_LOOSE2 = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+)\s(-?[\d.,]+)\s*$")

SKIP_WORDS = {"SALDO", "ANTERIOR", "INICIAL", "FINAL", "TOTAL"}


def _clean_series(s: pd.Series) -> pd.Series:
    return (
        s.fillna("").astype(str)
        .str.replace(r"[^\d,.\-]", "", regex=True)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .abs()
    )


def _normalize_amount(value) -> float:
    if pd.isna(value):
        return 0.0
    cleaned = re.sub(r"[^\d,.\-]", "", str(value))
    cleaned = cleaned.replace(",", ".")
    try:
        return abs(float(cleaned))
    except ValueError:
        return 0.0


def _parse_signed_amount(raw: str) -> float | None:
    raw = raw.strip()
    cleaned = re.sub(r"[^\d,.\-]", "", raw)
    if not cleaned or cleaned == "-":
        return None
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _match_column(columns: list[str], keywords: list[str]) -> str | None:
    for col in columns:
        col_lower = col.lower().strip()
        for kw in keywords:
            if kw in col_lower:
                return col
    return None


def _detect_delimiter(content: str) -> str:
    sample = content[:2000]
    counts = {";": sample.count(";"), ",": sample.count(","), "\t": sample.count("\t")}
    return max(counts, key=counts.get)


def _parse_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, format="mixed", dayfirst=True, errors="coerce")
    except TypeError:
        return pd.to_datetime(series, dayfirst=True, errors="coerce")


# ---------------------------------------------------------------------------
# PDF parsing — text extraction only (no table fallback to avoid timeouts)
# ---------------------------------------------------------------------------

def _build_record_from_row(fecha_str: str, text: str) -> dict | None:
    """Parse one complete bank row (may be multi-line merged into a single string)."""
    text = text.strip()
    if not text or any(w in text.upper() for w in SKIP_WORDS):
        return None

    # Right-anchored: IMPORTE  DD-MM  SALDO
    right_m = _STRICT_RIGHT.search(text)
    if not right_m:
        return None

    importe_str = right_m.group(1)
    concepto = text[: right_m.start()].strip()

    importe = _parse_signed_amount(importe_str)
    if importe is None or importe == 0:
        return None

    fecha = _parse_dates(pd.Series([fecha_str])).iloc[0]
    if pd.isna(fecha):
        return None

    ref_match = CHEQUE_REF_RE.search(concepto)
    return {
        "fecha": fecha,
        "detalle": concepto,
        "referencia": ref_match.group(1) if ref_match else "",
        "monto_abs": abs(importe),
        "tipo": "debito" if importe < 0 else "credito",
        "conciliado": False,
    }


def _parse_rows_state_machine(lines: list[str]) -> list[dict]:
    """
    Handles multi-line rows (Banco Provincia wraps long concepts across lines).

    Two strategies per row:
    1. Try the date-line content alone (covers: amount is on the first line).
    2. If that fails, prepend continuation lines to the first-line content
       (covers: amount is on a continuation line after a wrapped concept).
    """
    records = []
    current_fecha: str | None = None
    first_line_content = ""
    extra_parts: list[str] = []

    def flush():
        if current_fecha is None:
            return

        # Strategy 1: amount is on the date line itself
        rec = _build_record_from_row(current_fecha, first_line_content)
        if rec:
            records.append(rec)
            return

        # Strategy 2: amount may be on a continuation line
        if extra_parts:
            combined = " ".join([first_line_content] + extra_parts)
            rec = _build_record_from_row(current_fecha, combined)
            if rec:
                records.append(rec)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        date_m = _STRICT_DATE_START.match(line)
        if date_m:
            flush()
            current_fecha = date_m.group(1)
            first_line_content = date_m.group(2).strip()
            extra_parts = []
        elif current_fecha:
            extra_parts.append(line)

    flush()
    return records


def _extract_text_pypdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_text_pdfplumber(file_bytes: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=False)
            if text:
                parts.append(text)
    return "\n".join(parts)


def _parse_pdf_generic(file_bytes: bytes, filename: str) -> pd.DataFrame:
    # Use pypdf (fast). Only fall back to pdfplumber if pypdf got no text at all.
    text = _extract_text_pypdf(file_bytes)
    if not text.strip():
        text = _extract_text_pdfplumber(file_bytes)

    if not text.strip():
        raise ValueError(
            f"No se pudo extraer texto del PDF '{filename}'. "
            "Verificá que sea un PDF digital, no un escaneado."
        )

    records = _parse_rows_state_machine(text.splitlines())

    if not records:
        raise ValueError(
            f"No se encontraron transacciones en '{filename}'. "
            "El PDF se leyó correctamente pero no matchea el formato esperado "
            "(Fecha | Concepto | Importe | DD-MM | Saldo). "
            "Exportá el extracto como CSV desde el home banking."
        )

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_bank_statement(file_bytes: bytes, filename: str) -> pd.DataFrame:
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return _parse_pdf_generic(file_bytes, filename)

    content = file_bytes.decode("latin-1", errors="replace")
    delimiter = _detect_delimiter(content)
    try:
        df = pd.read_csv(io.StringIO(content), sep=delimiter, dtype=str, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
    except Exception:
        raise ValueError(f"No se pudo parsear el archivo bancario: {filename}")

    return _df_from_columns(df, filename)


def parse_mayor(file_bytes: bytes, filename: str) -> pd.DataFrame:
    ext = filename.lower().split(".")[-1]

    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    else:
        content = file_bytes.decode("latin-1", errors="replace")
        delimiter = _detect_delimiter(content)
        df = pd.read_csv(io.StringIO(content), sep=delimiter, dtype=str, skipinitialspace=True)

    df.columns = [c.strip() for c in df.columns]
    cols = list(df.columns)

    date_col = _match_column(cols, DATE_KEYWORDS)
    desc_col = _match_column(cols, DESC_KEYWORDS)
    ref_col = _match_column(cols, REF_KEYWORDS)
    debe_col = _match_column(cols, DEBE_KEYWORDS)
    haber_col = _match_column(cols, HABER_KEYWORDS)
    amount_col = _match_column(cols, AMOUNT_KEYWORDS)

    if date_col is None:
        raise ValueError(
            f"No se encontró columna de fecha en '{filename}'. "
            f"Columnas encontradas: {cols}. "
            "Se espera una columna con nombre que contenga 'Fecha', 'Fec' o 'Date'."
        )

    df["fecha"] = _parse_dates(df[date_col])
    df = df.dropna(subset=["fecha"])

    if df.empty:
        raise ValueError(
            f"No se encontraron fechas válidas en la columna '{date_col}' de '{filename}'."
        )

    df["detalle"] = df[desc_col].fillna("").astype(str).str.strip() if desc_col else ""
    df["referencia"] = df[ref_col].fillna("").astype(str).str.strip() if ref_col else ""

    if debe_col and haber_col:
        debe_vals = _clean_series(df[debe_col])
        haber_vals = _clean_series(df[haber_col])
        df["tipo"] = debe_vals.gt(0).map({True: "ingreso", False: "egreso"})
        df["monto_abs"] = debe_vals.where(debe_vals > 0, haber_vals)
    elif amount_col:
        raw = df[amount_col].fillna("").astype(str)
        df["monto_abs"] = _clean_series(df[amount_col])
        df["tipo"] = (~raw.str.contains("-", regex=False)).map({True: "ingreso", False: "egreso"})
    else:
        raise ValueError(
            f"No se encontraron columnas de monto en '{filename}'. "
            f"Columnas encontradas: {cols}. "
            "Se esperan columnas 'Debe'/'Haber' o 'Importe'/'Monto'."
        )

    df = df[df["monto_abs"] > 0].copy()
    df["conciliado"] = False
    return df[["fecha", "detalle", "referencia", "monto_abs", "tipo", "conciliado"]].reset_index(drop=True)


def _df_from_columns(df: pd.DataFrame, source_label: str) -> pd.DataFrame:
    cols = list(df.columns)

    date_col = _match_column(cols, DATE_KEYWORDS)
    desc_col = _match_column(cols, DESC_KEYWORDS)
    ref_col = _match_column(cols, REF_KEYWORDS)
    debit_col = _match_column(cols, DEBIT_KEYWORDS)
    credit_col = _match_column(cols, CREDIT_KEYWORDS)
    amount_col = _match_column(cols, AMOUNT_KEYWORDS)

    if date_col is None:
        raise ValueError(
            f"No se encontró columna de fecha en '{source_label}'. "
            f"Columnas encontradas: {cols}."
        )

    df["fecha"] = _parse_dates(df[date_col])
    df = df.dropna(subset=["fecha"])

    if df.empty:
        raise ValueError(
            f"No se encontraron fechas válidas en '{source_label}'."
        )

    df["detalle"] = df[desc_col].fillna("").astype(str).str.strip() if desc_col else ""
    df["referencia"] = df[ref_col].fillna("").astype(str).str.strip() if ref_col else ""

    if debit_col and credit_col:
        debit_vals = _clean_series(df[debit_col])
        credit_vals = _clean_series(df[credit_col])
        df["tipo"] = credit_vals.gt(0).map({True: "credito", False: "debito"})
        df["monto_abs"] = credit_vals.where(credit_vals > 0, debit_vals)
    elif amount_col:
        raw = df[amount_col].fillna("").astype(str)
        df["monto_abs"] = _clean_series(df[amount_col])
        df["tipo"] = (~raw.str.contains("-", regex=False)).map({True: "credito", False: "debito"})
    else:
        raise ValueError(
            f"No se encontraron columnas de monto en '{source_label}'. "
            f"Columnas encontradas: {cols}."
        )

    df = df[df["monto_abs"] > 0].copy()
    df["conciliado"] = False
    return df[["fecha", "detalle", "referencia", "monto_abs", "tipo", "conciliado"]].reset_index(drop=True)
