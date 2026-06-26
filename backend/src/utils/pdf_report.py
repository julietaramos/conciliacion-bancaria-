import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DARK_BLUE = colors.HexColor("#0d1b4b")
LIGHT_BLUE = colors.HexColor("#e8ecf8")
CAT_COLORS = {
    1: colors.HexColor("#fff3cd"),
    2: colors.HexColor("#d1ecf1"),
    3: colors.HexColor("#f8d7da"),
    4: colors.HexColor("#d4edda"),
}
GREEN_BG = colors.HexColor("#d4edda")
RED_BG = colors.HexColor("#f8d7da")

_styles = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "title", parent=_styles["Heading1"],
    textColor=DARK_BLUE, fontSize=18, spaceAfter=4,
)
STYLE_SUB = ParagraphStyle(
    "sub", parent=_styles["Normal"],
    textColor=colors.grey, fontSize=9, spaceAfter=14,
)
STYLE_SECTION = ParagraphStyle(
    "section", parent=_styles["Heading2"],
    textColor=DARK_BLUE, fontSize=11, spaceBefore=14, spaceAfter=6,
)
STYLE_CELL = ParagraphStyle(
    "cell", parent=_styles["Normal"], fontSize=8, leading=10,
)
STYLE_NOTE = ParagraphStyle(
    "note", parent=_styles["Normal"],
    textColor=colors.HexColor("#155724"),
    backColor=GREEN_BG, fontSize=9, spaceAfter=6,
)


def _header_style(n_cols: int) -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
    ])


def generate_pdf_report(result: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Conciliación Bancaria",
    )

    mayor = result.get("mayor_procesado", [])
    banco = result.get("banco_procesado", [])
    difs = result.get("archivo_diferencias", [])

    story = []

    # ── Header ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Conciliación Bancaria", STYLE_TITLE))
    story.append(Paragraph(f"Generado el {date.today().strftime('%d/%m/%Y')}", STYLE_SUB))

    # ── Stats ───────────────────────────────────────────────────────────────
    conc_m = sum(1 for r in mayor if r.get("conciliado"))
    conc_b = sum(1 for r in banco if r.get("conciliado"))
    pct_m = round(conc_m / len(mayor) * 100) if mayor else 0
    pct_b = round(conc_b / len(banco) * 100) if banco else 0

    stats_data = [
        ["Registros Mayor", "Conciliados Mayor", "Registros Banco", "Conciliados Banco", "Diferencias"],
        [
            str(len(mayor)),
            f"{conc_m}  ({pct_m}%)",
            str(len(banco)),
            f"{conc_b}  ({pct_b}%)",
            str(len(difs)),
        ],
    ]
    stats_t = Table(stats_data, hAlign="LEFT", colWidths=[5 * cm] * 5)
    stats_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BLUE),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_t)

    # ── Differences ─────────────────────────────────────────────────────────
    story.append(Paragraph("Partidas Pendientes — Diferencias", STYLE_SECTION))

    if not difs:
        story.append(Paragraph(
            "Sin diferencias — todos los registros fueron conciliados.",
            STYLE_NOTE,
        ))
    else:
        diff_headers = ["Cat.", "Descripción de Categoría", "Origen", "Fecha", "Detalle", "Referencia", "Monto ($)"]
        diff_rows = [diff_headers]
        for d in difs:
            diff_rows.append([
                str(d["categoria"]),
                d["categoria_label"],
                d["origen"],
                d["fecha"],
                str(d["detalle"])[:70],
                str(d["referencia"]),
                f"{float(d['monto']):,.2f}",
            ])

        col_w = [1 * cm, 7 * cm, 2 * cm, 2.2 * cm, 7 * cm, 2.5 * cm, 2.5 * cm]
        diff_t = Table(diff_rows, colWidths=col_w, hAlign="LEFT", repeatRows=1)

        row_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]
        for i, d in enumerate(difs, start=1):
            bg = CAT_COLORS.get(d["categoria"], colors.white)
            row_styles.append(("BACKGROUND", (0, i), (-1, i), bg))

        diff_t.setStyle(TableStyle(row_styles))
        story.append(diff_t)

    # ── Mayor audit ─────────────────────────────────────────────────────────
    story.append(Paragraph("Mayor Contable — Vista de Auditoría", STYLE_SECTION))
    _append_audit_table(story, mayor)

    # ── Banco audit ─────────────────────────────────────────────────────────
    story.append(Paragraph("Extracto Bancario — Vista de Auditoría", STYLE_SECTION))
    _append_audit_table(story, banco)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def _append_audit_table(story: list, records: list[dict]) -> None:
    if not records:
        story.append(Paragraph("Sin registros.", STYLE_CELL))
        return

    headers = ["Estado", "Fecha", "Detalle", "Referencia", "Tipo", "Monto ($)"]
    rows = [headers]
    for r in records:
        rows.append([
            "Conciliado" if r.get("conciliado") else "Pendiente",
            str(r.get("fecha", "")),
            str(r.get("detalle", ""))[:70],
            str(r.get("referencia", "")),
            str(r.get("tipo", "")),
            f"{float(r.get('monto_abs', 0)):,.2f}",
        ])

    col_w = [2.2 * cm, 2.2 * cm, 9 * cm, 3 * cm, 2 * cm, 2.5 * cm]
    t = Table(rows, colWidths=col_w, hAlign="LEFT", repeatRows=1)

    row_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]
    for i, r in enumerate(records, start=1):
        bg = GREEN_BG if r.get("conciliado") else RED_BG
        row_styles.append(("BACKGROUND", (0, i), (-1, i), bg))

    t.setStyle(TableStyle(row_styles))
    story.append(t)
