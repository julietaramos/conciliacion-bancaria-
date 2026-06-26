from datetime import datetime

DATE_WINDOW_DAYS = 5

# Each entry: (keyword in mayor desc, keyword in extracto desc)
# When a mayor item matches rule[0] and there are unmatched extracto items matching rule[1],
# they are grouped together as a single matched pair regardless of amount.
_KEYWORD_GROUP_RULES: list[tuple[str, str]] = [
    ("impuesto debito y credito", "impuesto ley 25.413"),
]


def _match_lists(a_items: list[dict], b_items: list[dict]) -> tuple[list, list, list]:
    """
    Match items from a against items from b by monto.

    Phase 1 — 1-to-1: exact monto match, date-proximity tiebreaker.
    Phase 2 — 1-to-many: for still-unmatched a items, find a subset of
               remaining b items whose sum equals a's monto.

    Returns (matched_pairs, unmatched_a, unmatched_b).
    Each matched pair is (a_item, [b_item, ...]).
    """
    available   = list(range(len(b_items)))
    used_b      = set()
    matched     = []        # list of (a_item, [b_items])
    unmatched_a = []

    # ── Phase 1: 1-to-1 ────────────────────────────────────────────────────────
    for a in a_items:
        target = round(a["monto"], 2)
        candidates = [
            i for i in available
            if i not in used_b and round(b_items[i]["monto"], 2) == target
        ]

        if not candidates:
            unmatched_a.append(a)
            continue

        a_date = a.get("fecha")
        if a_date is not None and len(candidates) > 1:
            def date_diff(i):
                b_date = b_items[i].get("fecha")
                if b_date is None:
                    return 9999
                diff = abs((a_date - b_date).days)
                return diff if diff <= DATE_WINDOW_DAYS else 9999
            candidates.sort(key=date_diff)

        best = candidates[0]
        matched.append((a, [b_items[best]]))
        used_b.add(best)

    # ── Phase 2: keyword-based group matching ──────────────────────────────────
    still_unmatched_a = []
    for a in unmatched_a:
        a_desc = a.get("descripcion", "").lower()
        rule_match = next(
            (rule for rule in _KEYWORD_GROUP_RULES if rule[0] in a_desc),
            None,
        )
        if rule_match is None:
            still_unmatched_a.append(a)
            continue

        b_kw = rule_match[1]
        group = [
            i for i in range(len(b_items))
            if i not in used_b and b_kw in b_items[i].get("descripcion", "").lower()
        ]
        if not group:
            still_unmatched_a.append(a)
            continue

        matched.append((a, [b_items[i] for i in group]))
        used_b.update(group)

    unmatched_b = [b_items[i] for i in range(len(b_items)) if i not in used_b]
    return matched, still_unmatched_a, unmatched_b


def reconcile(mayor: dict, extracto: dict, anterior: dict | None = None) -> dict:
    """
    Core reconciliation:
      - Mayor HABER  ↔  Extracto DÉBITO
      - Mayor DEBE   ↔  Extracto CRÉDITO

    Returns a dict with:
      col1  Débitos no Contabilizados       (extracto DÉBITO  unmatched)
      col2  Contabilizados HABER no deb.    (mayor   HABER    unmatched)
      col3  No Acreditados                  (mayor   DEBE     unmatched)
      col4  Créditos no Contabilizados      (extracto CRÉDITO unmatched)
      matched_haber_debito  list of (mayor_item, extracto_item)
      matched_debe_credito  list of (mayor_item, extracto_item)
      saldo_banco / saldo_contable / diferencia
      partidas_pendientes
    """
    haber_pool   = mayor["items_haber"]   + (anterior["col2"] if anterior else [])
    debe_pool    = mayor["items_debe"]    + (anterior["col3"] if anterior else [])
    debito_pool  = extracto["items_debito"]  + (anterior["col1"] if anterior else [])
    credito_pool = extracto["items_credito"] + (anterior["col4"] if anterior else [])

    matched_hd, unmatched_haber, unmatched_debito = _match_lists(haber_pool, debito_pool)
    matched_dc, unmatched_debe, unmatched_credito = _match_lists(debe_pool, credito_pool)

    col1 = unmatched_debito   # extracto DÉBITO  not in mayor HABER
    col2 = unmatched_haber    # mayor HABER       not in extracto DÉBITO
    col3 = unmatched_debe     # mayor DEBE        not in extracto CRÉDITO
    col4 = unmatched_credito  # extracto CRÉDITO  not in mayor DEBE

    partidas = (
        sum(x["monto"] for x in col1)
        - sum(x["monto"] for x in col2)
        + sum(x["monto"] for x in col3)
        - sum(x["monto"] for x in col4)
    )

    saldo_banco    = extracto["saldo_final"]
    saldo_contable = mayor["saldo_final"]
    diferencia     = round((saldo_banco + partidas) - saldo_contable, 2)

    all_extracto = extracto["items_debito"] + extracto["items_credito"]
    fechas = [x["fecha"] for x in all_extracto if x.get("fecha") is not None]
    fecha_datos = max(fechas).date() if fechas else None

    return {
        "col1": col1,
        "col2": col2,
        "col3": col3,
        "col4": col4,
        "matched_haber_debito": matched_hd,
        "matched_debe_credito": matched_dc,
        "saldo_banco":    saldo_banco,
        "saldo_contable": saldo_contable,
        "partidas":       round(partidas, 2),
        "diferencia":     diferencia,
        "fecha_datos":    fecha_datos,
    }
