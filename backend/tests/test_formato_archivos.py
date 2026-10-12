import io
import json
from datetime import datetime

import pytest
from openpyxl import Workbook

from utils.column_mapping import ORIGEN_AUTOMATICO, ORIGEN_GUARDADO, ORIGEN_MANUAL, PedidoFormato, leer_formato
from utils.excel_parser import leer_monto, parse_extracto, parse_mayor
from utils.file_inspection import inspeccionar


def _xlsx(filas) -> bytes:
    wb = Workbook()
    ws = wb.active
    for fila in filas:
        ws.append(fila)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


MAYOR_CON_TITULO = _xlsx([
    ["EMPRESA SA - Mayor de la cuenta Banco Provincia"],
    [],
    ["Fecha", "Leyenda", "Debe", "Haber", "Saldo"],
    [datetime(2026, 9, 1), "Saldo anterior", None, None, 1000],
    [datetime(2026, 9, 2), "Cobro cliente", 500, None, 1500],
    [datetime(2026, 9, 3), "Pago proveedor", None, 200, 1300],
    ["Total", None, 500, 200, None],
])

EXTRACTO_FECHA_VALOR = _xlsx([
    ["Fecha valor", "Fecha", "Descripción", "Débito", "Crédito", "Saldo"],
    ["05/09/2026", datetime(2026, 9, 2), "Transferencia", None, 500, 1500],
    ["06/09/2026", datetime(2026, 9, 3), "Pago", 200, None, 1300],
])


def _leer(tipo, contenido, nombre="archivo.xlsx", **pedido):
    return leer_formato(tipo, contenido, nombre, PedidoFormato(**pedido))


def test_detecta_encabezado_debajo_de_filas_de_titulo():
    formato = _leer("mayor", MAYOR_CON_TITULO)

    assert formato.fila_encabezado == 2
    assert formato.columnas == {"fecha": "Fecha", "descripcion": "Leyenda", "debe": "Debe", "haber": "Haber", "saldo": "Saldo"}
    assert formato.origen == ORIGEN_AUTOMATICO
    datos = parse_mayor(formato)
    assert [i["monto"] for i in datos["items_debe"]] == [500]
    assert [i["monto"] for i in datos["items_haber"]] == [200]
    assert datos["saldo_final"] == 1300


def test_prefiere_columna_con_nombre_exacto_y_avisa_ambiguedad():
    formato = _leer("extracto", EXTRACTO_FECHA_VALOR)

    assert formato.columnas["fecha"] == "Fecha"
    assert any("más de una columna que podría ser Fecha" in a for a in formato.advertencias)


def test_reusa_formato_guardado_del_banco():
    guardado = {"fecha": "Fecha valor", "descripcion": "Descripción", "debito": "Débito", "credito": "Crédito"}
    formato = _leer("extracto", EXTRACTO_FECHA_VALOR, guardado=guardado)

    assert formato.origen == ORIGEN_GUARDADO
    assert formato.columnas["fecha"] == "Fecha valor"
    assert parse_extracto(formato)["items_credito"][0]["fecha"] == datetime(2026, 9, 5)


def test_formato_guardado_que_no_coincide_cae_en_deteccion_automatica():
    formato = _leer("extracto", EXTRACTO_FECHA_VALOR, guardado={"fecha": "Fec. Op.", "importe": "Monto"})

    assert formato.origen == ORIGEN_AUTOMATICO
    assert "no coincide con el formato guardado" in formato.advertencias[0]


def test_mapeo_manual_con_errores_de_validacion():
    formato = _leer(
        "mayor", MAYOR_CON_TITULO, fila_encabezado=2,
        columnas={"fecha": "Fecha", "debe": "Debe", "haber": "Debe", "descripcion": "Inexistente"},
    )

    assert formato.origen == ORIGEN_MANUAL
    assert any("'Inexistente'" in e for e in formato.errores)
    assert any("más de un dato" in e for e in formato.errores)
    with pytest.raises(ValueError):
        parse_mayor(formato)


def test_falta_columna_de_importes():
    formato = _leer("mayor", _xlsx([["Fecha", "Concepto", "Debe"], [datetime(2026, 9, 1), "x", 10]]))

    assert any("Faltan las columnas de importes" in e for e in formato.errores)


def test_extracto_csv_con_punto_y_coma_titulo_e_importe_con_signo():
    contenido = (
        "Movimientos de la cuenta\n"
        "Fecha;Concepto;Importe;Saldo\n"
        "01/09/2026;Acreditacion;1.234,56;1.234,56\n"
        "02/09/2026;Debito automatico;-234,56;1.000,00\n"
    ).encode("latin-1")
    datos = parse_extracto(_leer("extracto", contenido, "extracto.csv"))

    assert [i["monto"] for i in datos["items_credito"]] == [1234.56]
    assert [i["monto"] for i in datos["items_debito"]] == [234.56]
    assert datos["saldo_final"] == 1000.0


@pytest.mark.parametrize("texto,esperado", [
    ("1.234,56", 1234.56),
    ("1,234.56", 1234.56),
    ("$ -1.234.567", -1234567.0),
    ("12,5", 12.5),
    ("abc", None),
    ("", None),
])
def test_leer_monto(texto, esperado):
    assert leer_monto(texto) == esperado


def test_inspeccion_avisa_montos_ilegibles_y_arma_muestra():
    contenido = _xlsx([
        ["Fecha", "Leyenda", "Debe", "Haber"],
        [datetime(2026, 9, 1), "Cobro", 100, None],
        [datetime(2026, 9, 2), "Pago", "N/D", 50],
    ])
    resultado = inspeccionar(_leer("mayor", contenido))

    assert resultado["errores"] == []
    assert resultado["resumen"]["movimientos"] == 2
    assert resultado["resumen"]["montos_invalidos"] == 1
    assert resultado["muestra"][0] == {"fecha": "2026-09-01", "descripcion": "Cobro", "debe": 100.0, "haber": None}
    assert resultado["muestra"][1]["debe"] == "N/D"


def test_endpoint_inspeccionar_y_preview_guardan_formato_del_banco(client, db_session):
    banco_id = client.post("/api/bancos", json={"nombre": "Banco Formato"}).json()["id"]

    inspeccion = client.post(
        "/api/archivos/inspeccionar",
        data={"banco_id": banco_id, "tipo": "extracto"},
        files={"archivo": ("extracto.xlsx", EXTRACTO_FECHA_VALOR)},
    ).json()
    assert inspeccion["columnas"]["fecha"] == "Fecha"

    columnas_extracto = inspeccion["columnas"] | {"fecha": "Fecha valor"}
    respuesta = client.post(
        "/api/conciliar/preview",
        data={
            "banco_id": banco_id,
            "formato_extracto": json.dumps({"fila_encabezado": 0, "columnas": columnas_extracto}),
        },
        files={"mayor": ("mayor.xlsx", MAYOR_CON_TITULO), "banco": ("extracto.xlsx", EXTRACTO_FECHA_VALOR)},
    )
    assert respuesta.status_code == 200

    reinspeccion = client.post(
        "/api/archivos/inspeccionar",
        data={"banco_id": banco_id, "tipo": "extracto"},
        files={"archivo": ("extracto.xlsx", EXTRACTO_FECHA_VALOR)},
    ).json()
    assert reinspeccion["origen"] == ORIGEN_GUARDADO
    assert reinspeccion["columnas"]["fecha"] == "Fecha valor"
