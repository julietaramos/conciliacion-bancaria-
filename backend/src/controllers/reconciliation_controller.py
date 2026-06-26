import pandas as pd

DATE_WINDOW_DAYS = 5
AMOUNT_TOLERANCE = 0.01

CATEGORY_LABELS = {
    1: "Cat. 1 – Egreso en Mayor / No debitado en banco (ej: cheque diferido)",
    2: "Cat. 2 – Ingreso en Mayor / No acreditado en banco (ej: depósito en clearing)",
    3: "Cat. 3 – Débito bancario / No registrado en empresa (ej: comisión, impuesto)",
    4: "Cat. 4 – Crédito bancario / No registrado en empresa (ej: interés, transferencia)",
}

MAYOR_BANCO_TYPE_MAP = {"ingreso": "credito", "egreso": "debito"}


def reconcile(mayor_df: pd.DataFrame, banco_df: pd.DataFrame) -> dict:
    mayor_df = mayor_df.copy().reset_index(drop=True)
    banco_df = banco_df.copy().reset_index(drop=True)

    _exact_match(mayor_df, banco_df)
    _fuzzy_match(mayor_df, banco_df)

    diferencias = _classify_orphans(mayor_df, banco_df)

    return {
        "archivo_diferencias": diferencias,
        "mayor_procesado": _to_serializable(mayor_df),
        "banco_procesado": _to_serializable(banco_df),
    }


def _exact_match(mayor_df: pd.DataFrame, banco_df: pd.DataFrame) -> None:
    m = mayor_df[~mayor_df["conciliado"]].copy().reset_index(names="_m_idx")
    b = banco_df[~banco_df["conciliado"]].copy().reset_index(names="_b_idx")

    m["_tipo_b"] = m["tipo"].map(MAYOR_BANCO_TYPE_MAP)
    m["_ref"] = m["referencia"].astype(str).str.strip()
    m["_amt"] = m["monto_abs"].round(2)

    b["_ref"] = b["referencia"].astype(str).str.strip()
    b["_amt"] = b["monto_abs"].round(2)

    m_with_ref = m[m["_ref"].ne("") & m["_ref"].ne("nan") & m["_ref"].ne("None")]
    if m_with_ref.empty:
        return

    merged = m_with_ref.merge(
        b,
        left_on=["_tipo_b", "_amt", "_ref"],
        right_on=["tipo", "_amt", "_ref"],
        how="inner",
        suffixes=("_m", "_b"),
    )
    if merged.empty:
        return

    merged = merged.drop_duplicates(subset="_m_idx", keep="first")
    merged = merged.drop_duplicates(subset="_b_idx", keep="first")

    mayor_df.loc[merged["_m_idx"].values, "conciliado"] = True
    banco_df.loc[merged["_b_idx"].values, "conciliado"] = True


def _fuzzy_match(mayor_df: pd.DataFrame, banco_df: pd.DataFrame) -> None:
    m = mayor_df[~mayor_df["conciliado"]].copy().reset_index(names="_m_idx")
    b = banco_df[~banco_df["conciliado"]].copy().reset_index(names="_b_idx")

    if m.empty or b.empty:
        return

    m["_tipo_b"] = m["tipo"].map(MAYOR_BANCO_TYPE_MAP)
    m["_amt"] = m["monto_abs"].round(2)
    b["_amt"] = b["monto_abs"].round(2)

    merged = m.merge(
        b,
        left_on=["_tipo_b", "_amt"],
        right_on=["tipo", "_amt"],
        how="inner",
        suffixes=("_m", "_b"),
    )
    if merged.empty:
        return

    amount_ok = (merged["monto_abs_m"] - merged["monto_abs_b"]).abs() <= AMOUNT_TOLERANCE
    date_diff = (merged["fecha_m"] - merged["fecha_b"]).abs()
    date_ok = date_diff <= pd.Timedelta(days=DATE_WINDOW_DAYS)

    merged = merged[amount_ok & date_ok].copy()
    if merged.empty:
        return

    merged["_date_diff"] = (merged["fecha_m"] - merged["fecha_b"]).abs()
    merged = merged.sort_values("_date_diff")

    matched_m: set[int] = set()
    matched_b: set[int] = set()

    for _, row in merged.iterrows():
        m_idx = int(row["_m_idx"])
        b_idx = int(row["_b_idx"])
        if m_idx not in matched_m and b_idx not in matched_b:
            matched_m.add(m_idx)
            matched_b.add(b_idx)

    mayor_df.loc[list(matched_m), "conciliado"] = True
    banco_df.loc[list(matched_b), "conciliado"] = True


def _classify_orphans(mayor_df: pd.DataFrame, banco_df: pd.DataFrame) -> list[dict]:
    diferencias = []
    mayor_orphans = mayor_df[~mayor_df["conciliado"]]
    banco_orphans = banco_df[~banco_df["conciliado"]]

    for _, row in mayor_orphans[mayor_orphans["tipo"] == "egreso"].iterrows():
        diferencias.append(_build_diff_row(1, row, "Mayor"))
    for _, row in mayor_orphans[mayor_orphans["tipo"] == "ingreso"].iterrows():
        diferencias.append(_build_diff_row(2, row, "Mayor"))
    for _, row in banco_orphans[banco_orphans["tipo"] == "debito"].iterrows():
        diferencias.append(_build_diff_row(3, row, "Banco"))
    for _, row in banco_orphans[banco_orphans["tipo"] == "credito"].iterrows():
        diferencias.append(_build_diff_row(4, row, "Banco"))

    return diferencias


def _build_diff_row(categoria: int, row: pd.Series, origen: str) -> dict:
    return {
        "categoria": categoria,
        "categoria_label": CATEGORY_LABELS[categoria],
        "origen": origen,
        "fecha": str(row["fecha"].date()),
        "detalle": row["detalle"],
        "referencia": row["referencia"],
        "monto": round(row["monto_abs"], 2),
    }


def _to_serializable(df: pd.DataFrame) -> list[dict]:
    records = df.copy()
    records["fecha"] = records["fecha"].apply(lambda x: str(x.date()) if pd.notna(x) else "")
    return records.to_dict(orient="records")
