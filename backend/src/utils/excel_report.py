import io
from datetime import date as dt_date
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

# ── Palette ────────────────────────────────────────────────────────────────────
_DARK_BLUE  = "0D1B4B"
_MED_BLUE   = "1A3C8F"
_LIGHT_BLUE = "C7D0E8"
_YELLOW     = "FFF3CD"
_GREEN      = "D4EDDA"
_RED        = "F8D7DA"
_PURPLE     = "E8D5F5"
_GREY_LIGHT = "F5F5F5"
_WHITE      = "FFFFFF"

_THIN = Side(style="thin", color="AAAAAA")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

_NUM_FMT = '#,##0.00'
_DATE_FMT = 'DD/MM/YYYY'


def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)


def _font(bold=False, color="000000", size=10) -> Font:
    return Font(bold=bold, color=color, size=size, name="Calibri")


def _align(h="left", v="center", wrap=False) -> Alignment:
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


def _set_header_row(ws, row: int, cells: dict, bg: str, fg: str = "FFFFFF", size=10):
    for col, text in cells.items():
        c = ws.cell(row=row, column=col)
        c.value = text
        c.fill = _fill(bg)
        c.font = _font(bold=True, color=fg, size=size)
        c.alignment = _align("center", wrap=True)
        c.border = _BORDER


def _write_data_row(ws, row: int, values: list, bg: str = None):
    for col, val in enumerate(values, start=1):
        c = ws.cell(row=row, column=col, value=val)
        c.border = _BORDER
        if bg:
            c.fill = _fill(bg)
        if isinstance(val, float):
            c.number_format = _NUM_FMT
            c.alignment = _align("right")
        elif hasattr(val, "date") or isinstance(val, dt_date):
            c.number_format = _DATE_FMT
            c.alignment = _align("center")
        else:
            c.alignment = _align("left", wrap=True)


def _fmt_date(item: dict):
    f = item.get("fecha")
    if f is None:
        return None
    if hasattr(f, "to_pydatetime"):
        return f.to_pydatetime()
    return f


# ── Main generator ─────────────────────────────────────────────────────────────

def generate_excel_report(result: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Conciliacion"

    col1 = result["col1"]   # extracto DÉBITO  unmatched
    col2 = result["col2"]   # mayor   HABER    unmatched
    col3 = result["col3"]   # mayor   DEBE     unmatched
    col4 = result["col4"]   # extracto CRÉDITO unmatched
    matched_hd = result["matched_haber_debito"]
    matched_dc = result["matched_debe_credito"]

    # ── Column widths ───────────────────────────────────────────────────────────
    widths = {
        1: 14, 2: 50, 3: 16,          # col group 1
        4: 14, 5: 50, 6: 16,          # col group 2
        7: 3,                          # separator
        8: 14, 9: 50, 10: 16,         # col group 3
        11: 14, 12: 50, 13: 16,       # col group 4
    }
    for col_idx, w in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    # ── Rows 1-5: Summary block ─────────────────────────────────────────────────
    summary = [
        ("Saldo Banco (Final)",        result["saldo_banco"],    "A"),
        ("Partidas Pendientes",         result["partidas"],       "B"),
        ("Saldo Banco + Partidas",      result["saldo_banco"] + result["partidas"], "C = A + B"),
        ("Saldo Contable (Final Mayor)", result["saldo_contable"], "D"),
        ("Diferencia",                  result["diferencia"],     "C - D"),
    ]
    for i, (label, value, ref) in enumerate(summary, start=1):
        ws.cell(row=i, column=6, value=label).font = _font(bold=(i == 5))
        c_val = ws.cell(row=i, column=8, value=value)
        c_val.number_format = _NUM_FMT
        c_val.font = _font(bold=True, color=("C0392B" if i == 5 and abs(value) > 0.01 else "155724"))
        c_val.alignment = _align("right")
        ws.cell(row=i, column=9, value=ref).font = _font(color="888888")

    # ── Row 6: Group headers ────────────────────────────────────────────────────
    sum1 = sum(x["monto"] for x in col1)
    sum2 = sum(x["monto"] for x in col2)
    sum3 = sum(x["monto"] for x in col3)
    sum4 = sum(x["monto"] for x in col4)

    group_headers = {
        1: "Débitos no Contabilizados",
        3: sum1,
        4: "No Debitados en Extracto",
        6: -sum2,
        8: "No Acreditados",
        10: sum3,
        11: "Créditos no Contabilizados",
        13: -sum4,
    }
    _set_header_row(ws, 6, group_headers, _DARK_BLUE)
    ws.cell(row=6, column=3).number_format = _NUM_FMT
    ws.cell(row=6, column=6).number_format = _NUM_FMT
    ws.cell(row=6, column=10).number_format = _NUM_FMT
    ws.cell(row=6, column=13).number_format = _NUM_FMT
    ws.row_dimensions[6].height = 36

    # ── Row 7: Sub-headers ──────────────────────────────────────────────────────
    sub = {1: "Fecha", 2: "Concepto", 3: "Importe",
           4: "Fecha", 5: "Concepto", 6: "Importe",
           8: "Fecha", 9: "Concepto", 10: "Importe",
           11: "Fecha", 12: "Concepto", 13: "Importe"}
    _set_header_row(ws, 7, sub, _MED_BLUE)

    # ── Rows 8+: Data ───────────────────────────────────────────────────────────
    max_rows = max(len(col1), len(col2), len(col3), len(col4), 1)

    def _item(lst, i):
        return lst[i] if i < len(lst) else None

    for i in range(max_rows):
        row = 8 + i

        a = _item(col1, i)
        b = _item(col2, i)
        c = _item(col3, i)
        d = _item(col4, i)

        # If any item in this row comes from the previous month, tint orange
        any_anterior = any(x.get("mes_anterior") for x in [a, b, c, d] if x)
        bg = _ORANGE if any_anterior else (_GREY_LIGHT if i % 2 == 0 else _WHITE)

        row_vals = [
            _fmt_date(a) if a else None, a["descripcion"] if a else None, a["monto"] if a else None,
            _fmt_date(b) if b else None, b["descripcion"] if b else None, b["monto"] if b else None,
            None,
            _fmt_date(c) if c else None, c["descripcion"] if c else None, c["monto"] if c else None,
            _fmt_date(d) if d else None, d["descripcion"] if d else None, d["monto"] if d else None,
        ]
        _write_data_row(ws, row, row_vals, bg)

    # ── Verification tables ─────────────────────────────────────────────────────
    start_row = 8 + max_rows + 3

    start_row = _write_verification_table(
        ws, start_row,
        title="✓ Conciliados: HABER (Mayor) ↔ DÉBITO (Extracto)",
        header_a="MAYOR — Haber", header_b="EXTRACTO — Débito",
        pairs=matched_hd,
        bg_header=_YELLOW,
    )

    start_row += 2

    start_row = _write_verification_table(
        ws, start_row,
        title="✓ Conciliados: DEBE (Mayor) ↔ CRÉDITO (Extracto)",
        header_a="MAYOR — Debe", header_b="EXTRACTO — Crédito",
        pairs=matched_dc,
        bg_header=_GREEN,
    )

    # ── Freeze top rows ─────────────────────────────────────────────────────────
    ws.freeze_panes = "A8"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


_ORANGE = "FFE0B2"  # highlight for previous-month items


def _write_verification_table(
    ws, start_row: int,
    title: str,
    header_a: str, header_b: str,
    pairs: list,
    bg_header: str,
) -> int:
    """Write a pair verification table. Returns the next available row."""

    c = ws.cell(row=start_row, column=1, value=title)
    c.font = _font(bold=True, size=11, color=_DARK_BLUE)
    c.fill = _fill(bg_header)
    c.alignment = _align("left")
    for col in range(2, 14):
        ws.cell(row=start_row, column=col).fill = _fill(bg_header)
    start_row += 1

    headers = {
        1: "Fecha (Mayor)", 2: "Concepto (Mayor)", 3: "Monto",
        4: "Fecha (Extracto)", 5: "Concepto (Extracto)", 6: "Monto",
        7: "Fuente",
    }
    _set_header_row(ws, start_row, headers, _MED_BLUE, size=9)
    start_row += 1

    if not pairs:
        ws.cell(row=start_row, column=1, value="— Sin pares conciliados —").font = _font(color="888888")
        return start_row + 1

    for i, (mayor_item, extracto_items) in enumerate(pairs):
        from_anterior = mayor_item.get("mes_anterior") or any(
            e.get("mes_anterior") for e in extracto_items
        )
        bg     = _ORANGE if from_anterior else (_GREY_LIGHT if i % 2 == 0 else _WHITE)
        fuente = "Mes anterior" if from_anterior else "Mes actual"

        for j, ext in enumerate(extracto_items):
            row_vals = [
                (_fmt_date(mayor_item)       if j == 0 else None),
                (mayor_item["descripcion"]   if j == 0 else None),
                (mayor_item["monto"]         if j == 0 else None),
                _fmt_date(ext),
                ext["descripcion"],
                ext["monto"],
                (fuente                      if j == 0 else None),
            ]
            _write_data_row(ws, start_row, row_vals, bg)
            start_row += 1

    total_monto = sum(e["monto"] for _, exts in pairs for e in exts)
    ws.cell(row=start_row, column=2, value="TOTAL").font = _font(bold=True)
    t = ws.cell(row=start_row, column=3, value=total_monto)
    t.number_format = _NUM_FMT
    t.font = _font(bold=True)
    t.alignment = _align("right")
    t.fill = _fill(bg_header)

    return start_row + 1
