import csv
import io
import math
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

FILAS_BUSQUEDA_ENCABEZADO = 20
CSV_ENCODING = "latin-1"
CSV_DELIMITADORES = ",;\t"
CSV_DELIMITADOR_DEFAULT = ","
FILAS_MUESTRA_DELIMITADOR = 50
EXTENSIONES_EXCEL = ("xlsx", "xls")

ORIGEN_MANUAL = "manual"
ORIGEN_GUARDADO = "guardado"
ORIGEN_AUTOMATICO = "automatico"


@dataclass(frozen=True)
class Campo:
    clave: str
    nombre: str
    palabras: tuple[str, ...]
    excluir: tuple[str, ...] = ()
    es_monto: bool = False

    def acepta(self, encabezado: str) -> bool:
        if any(palabra in encabezado for palabra in self.excluir):
            return False
        return any(palabra in encabezado for palabra in self.palabras)

    def coincide_exacto(self, encabezado: str) -> bool:
        return encabezado in self.palabras


@dataclass(frozen=True)
class Esquema:
    tipo: str
    nombre: str
    campos: tuple[Campo, ...]
    obligatorios: tuple[str, ...]
    modos_importe: tuple[tuple[str, ...], ...]

    def campo(self, clave: str) -> Campo:
        return next(c for c in self.campos if c.clave == clave)

    def describir_modos_importe(self) -> str:
        return " o ".join(
            " + ".join(self.campo(clave).nombre for clave in modo) for modo in self.modos_importe
        )


_FECHA = Campo("fecha", "Fecha", ("fecha", "fec", "date"))

MAYOR = Esquema(
    tipo="mayor",
    nombre="Mayor Contable",
    campos=(
        _FECHA,
        Campo("descripcion", "Descripción", ("leyenda", "concepto", "descripcion", "detalle", "movimiento")),
        Campo("debe", "Debe", ("debe",), es_monto=True),
        Campo("haber", "Haber", ("haber",), es_monto=True),
        Campo("saldo", "Saldo", ("saldo",), excluir=("inicial", "anterior"), es_monto=True),
    ),
    obligatorios=("fecha",),
    modos_importe=(("debe", "haber"),),
)

EXTRACTO = Esquema(
    tipo="extracto",
    nombre="Extracto Bancario",
    campos=(
        _FECHA,
        Campo("descripcion", "Descripción", ("descripcion", "concepto", "movimiento", "detalle")),
        Campo("debito", "Débito", ("debito", "debit", "cargo", "egreso", "salida"), es_monto=True),
        Campo("credito", "Crédito", ("credito", "credit", "acredit", "ingreso", "entrada"), es_monto=True),
        Campo("importe", "Importe (+/-)", ("importe", "monto", "amount"), es_monto=True),
        Campo("saldo", "Saldo", ("saldo",), es_monto=True),
    ),
    obligatorios=("fecha",),
    modos_importe=(("debito", "credito"), ("importe",)),
)

ESQUEMAS = {MAYOR.tipo: MAYOR, EXTRACTO.tipo: EXTRACTO}


@dataclass(frozen=True)
class PedidoFormato:
    fila_encabezado: int | None = None
    columnas: dict[str, str] | None = None
    guardado: dict[str, str] | None = None


@dataclass
class Formato:
    esquema: Esquema
    fila_encabezado: int
    etiquetas: list[str]
    columnas: dict[str, str]
    origen: str
    datos: pd.DataFrame
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def es_valido(self) -> bool:
        return not self.errores

    def columna(self, clave: str) -> str | None:
        return self.columnas.get(clave)

    def modo_importe(self) -> tuple[str, ...] | None:
        return next(
            (modo for modo in self.esquema.modos_importe if all(self.columna(c) for c in modo)),
            None,
        )


def normalizar(texto) -> str:
    descompuesto = unicodedata.normalize("NFKD", str(texto).strip().lower())
    return "".join(ch for ch in descompuesto if not unicodedata.combining(ch))


def es_vacio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return isinstance(valor, str) and not valor.strip()


def leer_formato(tipo: str, file_bytes: bytes, filename: str, pedido: PedidoFormato) -> Formato:
    esquema = ESQUEMAS[tipo]
    cruda = _leer_tabla_cruda(file_bytes, filename)
    if cruda.empty:
        raise ValueError(f"El archivo '{filename}' está vacío.")
    return _resolver_formato(cruda, esquema, pedido)


def _leer_tabla_cruda(file_bytes: bytes, filename: str) -> pd.DataFrame:
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension in EXTENSIONES_EXCEL:
        return pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=object)
    return _leer_csv_crudo(file_bytes.decode(CSV_ENCODING, errors="replace"))


def _leer_csv_crudo(contenido: str) -> pd.DataFrame:
    filas = list(csv.reader(io.StringIO(contenido), delimiter=_detectar_delimitador(contenido)))
    ancho = max((len(f) for f in filas), default=0)
    return pd.DataFrame([f + [None] * (ancho - len(f)) for f in filas], dtype=object)


def _detectar_delimitador(contenido: str) -> str:
    """Picks the delimiter that splits the most lines into the same number of fields,
    so decimal commas inside amounts don't beat the real ';' separator."""
    muestra = contenido.splitlines()[:FILAS_MUESTRA_DELIMITADOR]

    def consistencia(delimitador: str) -> tuple[int, int]:
        anchos = Counter(len(f) for f in csv.reader(muestra, delimiter=delimitador) if len(f) > 1)
        if not anchos:
            return 0, 0
        ancho, lineas = anchos.most_common(1)[0]
        return lineas, ancho

    mejor = max(CSV_DELIMITADORES, key=consistencia)
    return mejor if consistencia(mejor) != (0, 0) else CSV_DELIMITADOR_DEFAULT


def _resolver_formato(cruda: pd.DataFrame, esquema: Esquema, pedido: PedidoFormato) -> Formato:
    if pedido.columnas is not None:
        fila = _fila_pedida_o_buscada(cruda, esquema, pedido.fila_encabezado, pedido.columnas)
        return _armar_formato(cruda, esquema, fila, dict(pedido.columnas), ORIGEN_MANUAL)

    if pedido.fila_encabezado is not None:
        return _formato_automatico(cruda, esquema, pedido.fila_encabezado)

    if pedido.guardado:
        fila = _buscar_fila_con_columnas(cruda, pedido.guardado.values())
        if fila is not None:
            return _armar_formato(cruda, esquema, fila, dict(pedido.guardado), ORIGEN_GUARDADO)
        formato = _formato_automatico(cruda, esquema, _detectar_fila_encabezado(cruda, esquema))
        formato.advertencias.insert(
            0,
            "El archivo no coincide con el formato guardado para este banco; "
            "las columnas se detectaron automáticamente.",
        )
        return formato

    return _formato_automatico(cruda, esquema, _detectar_fila_encabezado(cruda, esquema))


def _fila_pedida_o_buscada(cruda, esquema, fila_pedida, columnas) -> int:
    if fila_pedida is not None:
        return fila_pedida
    fila = _buscar_fila_con_columnas(cruda, columnas.values())
    return fila if fila is not None else _detectar_fila_encabezado(cruda, esquema)


def _formato_automatico(cruda: pd.DataFrame, esquema: Esquema, fila: int) -> Formato:
    etiquetas = _etiquetas_de_fila(cruda, fila)
    columnas, advertencias = _mapear_automatico(etiquetas, esquema)
    formato = _armar_formato(cruda, esquema, fila, columnas, ORIGEN_AUTOMATICO)
    formato.advertencias = advertencias + formato.advertencias
    return formato


def _armar_formato(cruda, esquema, fila, columnas, origen) -> Formato:
    if not 0 <= fila < len(cruda):
        raise ValueError(f"La fila de encabezados {fila + 1} no existe en el archivo.")
    etiquetas = _etiquetas_de_fila(cruda, fila)
    datos = cruda.iloc[fila + 1:].reset_index(drop=True)
    datos.columns = etiquetas
    columnas = {clave: col for clave, col in columnas.items() if col}
    errores, advertencias = _validar_columnas(etiquetas, columnas, esquema)
    return Formato(esquema, fila, etiquetas, columnas, origen, datos, errores, advertencias)


def _etiquetas_de_fila(cruda: pd.DataFrame, fila: int) -> list[str]:
    etiquetas = []
    for indice, valor in enumerate(cruda.iloc[fila]):
        base = f"Columna {indice + 1}" if es_vacio(valor) else str(valor).strip()
        etiqueta, repeticion = base, 2
        while etiqueta in etiquetas:
            etiqueta, repeticion = f"{base} ({repeticion})", repeticion + 1
        etiquetas.append(etiqueta)
    return etiquetas


def _filas_candidatas(cruda: pd.DataFrame) -> range:
    return range(min(len(cruda), FILAS_BUSQUEDA_ENCABEZADO))


def _detectar_fila_encabezado(cruda: pd.DataFrame, esquema: Esquema) -> int:
    def campos_reconocidos(fila: int) -> int:
        encabezados = [normalizar(e) for e in _etiquetas_de_fila(cruda, fila)]
        return sum(any(campo.acepta(e) for e in encabezados) for campo in esquema.campos)

    return max(_filas_candidatas(cruda), key=lambda fila: (campos_reconocidos(fila), -fila), default=0)


def _buscar_fila_con_columnas(cruda: pd.DataFrame, columnas) -> int | None:
    buscadas = set(columnas)
    return next(
        (fila for fila in _filas_candidatas(cruda) if buscadas <= set(_etiquetas_de_fila(cruda, fila))),
        None,
    )


def _mapear_automatico(etiquetas: list[str], esquema: Esquema) -> tuple[dict[str, str], list[str]]:
    columnas: dict[str, str] = {}
    advertencias: list[str] = []
    for campo in esquema.campos:
        candidatas = [e for e in etiquetas if e not in columnas.values() and campo.acepta(normalizar(e))]
        if not candidatas:
            continue
        elegida = next((e for e in candidatas if campo.coincide_exacto(normalizar(e))), candidatas[0])
        columnas[campo.clave] = elegida
        if len(candidatas) > 1:
            advertencias.append(
                f"Hay más de una columna que podría ser {campo.nombre} "
                f"({', '.join(candidatas)}); se tomó '{elegida}'."
            )
    return columnas, advertencias


def _validar_columnas(etiquetas, columnas, esquema) -> tuple[list[str], list[str]]:
    errores = [
        f"La columna '{col}' asignada a {esquema.campo(clave).nombre} no existe en la fila de encabezados."
        for clave, col in columnas.items()
        if col not in etiquetas
    ]
    errores += _errores_columnas_repetidas(columnas, esquema)
    errores += [
        f"Falta asignar la columna {esquema.campo(clave).nombre}."
        for clave in esquema.obligatorios
        if clave not in columnas
    ]

    modos_completos = [modo for modo in esquema.modos_importe if all(c in columnas for c in modo)]
    if not modos_completos:
        errores.append(f"Faltan las columnas de importes: {esquema.describir_modos_importe()}.")

    advertencias = []
    if len(modos_completos) > 1:
        usadas = " + ".join(esquema.campo(c).nombre for c in modos_completos[0])
        ignoradas = ", ".join(esquema.campo(c).nombre for modo in modos_completos[1:] for c in modo)
        advertencias.append(f"Se usan las columnas {usadas}; se ignora {ignoradas}.")
    return errores, advertencias


def _errores_columnas_repetidas(columnas, esquema) -> list[str]:
    campos_por_columna: dict[str, list[str]] = {}
    for clave, col in columnas.items():
        campos_por_columna.setdefault(col, []).append(esquema.campo(clave).nombre)
    return [
        f"La columna '{col}' está asignada a más de un dato ({', '.join(campos)})."
        for col, campos in campos_por_columna.items()
        if len(campos) > 1
    ]
