from itertools import islice

from utils.column_mapping import Formato, es_vacio
from utils.excel_parser import (
    es_monto_invalido, fecha_de_movimiento, filas_con_fecha, leer_monto, parse_extracto, parse_mayor,
)

TAMANO_MUESTRA = 5
PARSERS = {"mayor": parse_mayor, "extracto": parse_extracto}


def inspeccionar(formato: Formato) -> dict:
    esquema = formato.esquema
    respuesta = {
        "tipo":                 esquema.tipo,
        "fila_encabezado":      formato.fila_encabezado,
        "columnas_disponibles": formato.etiquetas,
        "columnas":             formato.columnas,
        "origen":               formato.origen,
        "campos": [
            {"clave": c.clave, "nombre": c.nombre, "es_monto": c.es_monto,
             "obligatorio": c.clave in esquema.obligatorios}
            for c in esquema.campos
        ],
        "importes_requeridos": esquema.describir_modos_importe(),
        "errores":      list(formato.errores),
        "advertencias": list(formato.advertencias),
        "resumen":      None,
        "muestra":      [],
    }
    if not formato.es_valido:
        return respuesta

    resumen = _resumir(formato)
    respuesta["resumen"] = resumen
    respuesta["muestra"] = _muestra(formato)
    respuesta["errores"] += _errores_de_contenido(formato, resumen)
    respuesta["advertencias"] += _advertencias_de_contenido(formato, resumen)
    return respuesta


def _resumir(formato: Formato) -> dict:
    datos = PARSERS[formato.esquema.tipo](formato)
    return {
        "movimientos":      sum(len(v) for k, v in datos.items() if k.startswith("items_")),
        "filas_ignoradas":  _contar_filas_sin_fecha(formato),
        "montos_invalidos": _contar_montos_invalidos(formato),
        "saldo_final":      datos["saldo_final"],
    }


def _contar_filas_sin_fecha(formato: Formato) -> int:
    columna_fecha = formato.columna("fecha")
    return sum(
        1 for _, row in formato.datos.iterrows()
        if not all(es_vacio(v) for v in row) and fecha_de_movimiento(row[columna_fecha]) is None
    )


def _columnas_de_monto(formato: Formato) -> list[str]:
    return [formato.columna(c.clave) for c in formato.esquema.campos if c.es_monto and formato.columna(c.clave)]


def _contar_montos_invalidos(formato: Formato) -> int:
    columnas = _columnas_de_monto(formato)
    return sum(
        1 for _, row in filas_con_fecha(formato)
        if any(es_monto_invalido(row[col]) for col in columnas)
    )


def _errores_de_contenido(formato: Formato, resumen: dict) -> list[str]:
    if resumen["movimientos"]:
        return []
    return [
        f"No se encontró ningún movimiento: revisá que '{formato.columna('fecha')}' tenga fechas "
        "y que las columnas de importes tengan montos."
    ]


def _advertencias_de_contenido(formato: Formato, resumen: dict) -> list[str]:
    advertencias = []
    if resumen["montos_invalidos"]:
        advertencias.append(
            f"{resumen['montos_invalidos']} filas tienen importes que no se pudieron leer como número "
            "(se toman como 0). Revisá que las columnas de importes sean las correctas."
        )
    if resumen["filas_ignoradas"] > resumen["movimientos"]:
        advertencias.append(
            f"Se ignoraron {resumen['filas_ignoradas']} filas sin fecha válida, más que los movimientos leídos. "
            f"Revisá que '{formato.columna('fecha')}' sea la columna de fecha."
        )
    return advertencias


def _muestra(formato: Formato) -> list[dict]:
    return [_fila_muestra(formato, fecha, row) for fecha, row in islice(filas_con_fecha(formato), TAMANO_MUESTRA)]


def _fila_muestra(formato: Formato, fecha, row) -> dict:
    fila = {"fecha": fecha.date().isoformat()}
    for campo in formato.esquema.campos:
        columna = formato.columna(campo.clave)
        if campo.clave == "fecha" or columna is None:
            continue
        fila[campo.clave] = _valor_muestra(row[columna], campo.es_monto)
    return fila


def _valor_muestra(valor, es_monto: bool):
    if es_vacio(valor):
        return None
    if es_monto and not es_monto_invalido(valor):
        return leer_monto(valor)
    return str(valor).strip()
