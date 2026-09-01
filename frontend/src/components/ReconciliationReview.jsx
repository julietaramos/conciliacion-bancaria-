import { useState, useMemo } from 'react'

// ── Helpers ───────────────────────────────────────────────────────────────────

const TOLERANCIA_CRUCE = 100

function round2(n) { return Math.round(n * 100) / 100 }

function fmtFecha(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`
  } catch { return '—' }
}

function fmtMonto(m) {
  return `$${Number(m).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function filterByDescripcion(items, query) {
  const q = query.trim().toLowerCase()
  if (!q) return items
  return items.filter(x => (x.descripcion || '').toLowerCase().includes(q))
}

// Normaliza los cruces guardados/entrantes al formato unificado
// { id, col1: [], col2: [], col3: [], col4: [] }.
// Soporta tanto el formato nuevo (previewData.matched) como el formato legado
// que todavía puede venir de una conciliación guardada antes de este cambio,
// o del propio endpoint de preview (matched_haber_debito / matched_debe_credito).
function normalizeMatches(previewData) {
  if (previewData.matched) {
    return previewData.matched.map(m => ({
      id:   m.id ?? crypto.randomUUID(),
      col1: m.col1 ?? [], col2: m.col2 ?? [], col3: m.col3 ?? [], col4: m.col4 ?? [],
    }))
  }

  const fromLegacy = (pairs, mayorCol, extractoCol) => (pairs || []).map(p => {
    const mayores   = p.mayores   ?? (p.mayor   ? [p.mayor]   : [])
    const extractos = p.extractos ?? (p.extracto ? [p.extracto] : [])
    return {
      id: p.id ?? crypto.randomUUID(),
      col1: [], col2: [], col3: [], col4: [],
      [mayorCol]: mayores,
      [extractoCol]: extractos,
    }
  })

  return [
    ...fromLegacy(previewData.matched_haber_debito, 'col2', 'col1'),
    ...fromLegacy(previewData.matched_debe_credito, 'col3', 'col4'),
  ]
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ step, title, description }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <div style={{
          width: 26, height: 26, borderRadius: '50%',
          background: '#0d1b4b', color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, fontWeight: 800, flexShrink: 0,
        }}>{step}</div>
        <h2 style={{ fontSize: 16, fontWeight: 800, color: '#0d1b4b', margin: 0 }}>{title}</h2>
      </div>
      <p style={{ fontSize: 12, color: '#64748b', margin: '0 0 0 36px', lineHeight: 1.5 }}>{description}</p>
    </div>
  )
}

function ItemRow({ item, selected, side, onClick }) {
  const colors = side === 'mayor'
    ? { sel: '#dcfce7', selBorder: '#16a34a' }
    : { sel: '#dbeafe', selBorder: '#2563eb' }

  return (
    <div
      onClick={() => onClick(item.id)}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: 8,
        padding: '8px 10px', borderRadius: 7, marginBottom: 4,
        cursor: 'pointer',
        background: selected ? colors.sel : item.mes_anterior ? '#fff7ed' : '#fff',
        border: `2px solid ${selected ? colors.selBorder : item.mes_anterior ? '#fed7aa' : '#e2e8f0'}`,
        transition: 'all 0.1s',
        userSelect: 'none',
      }}
    >
      <div style={{
        width: 16, height: 16, borderRadius: 3, marginTop: 1,
        border: `2px solid ${selected ? colors.selBorder : '#cbd5e1'}`,
        background: selected ? colors.selBorder : 'transparent',
        flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {selected && <span style={{ color: '#fff', fontSize: 9, fontWeight: 900 }}>✓</span>}
      </div>
      <span style={{ fontSize: 10, color: '#94a3b8', width: 52, flexShrink: 0, marginTop: 1 }}>
        {fmtFecha(item.fecha)}
      </span>
      <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflowWrap: 'break-word', whiteSpace: 'normal', color: '#1e293b', lineHeight: 1.4 }}>
        {item.descripcion || '—'}
      </span>
      <span style={{ fontSize: 13, fontWeight: 800, color: '#0d1b4b', flexShrink: 0, marginLeft: 4 }}>
        {fmtMonto(item.monto)}
      </span>
      {item.mes_anterior && (
        <span style={{ fontSize: 9, background: '#fed7aa', color: '#c2410c', borderRadius: 3, padding: '1px 5px', flexShrink: 0, fontWeight: 700 }}>
          ANT.
        </span>
      )}
    </div>
  )
}

function ColHeader({ side, title, description, count }) {
  const isMayor = side === 'mayor'
  return (
    <div style={{
      padding: '10px 14px 10px',
      borderBottom: `1px solid ${isMayor ? '#dcfce7' : '#dbeafe'}`,
      background: isMayor ? '#f0fdf4' : '#eff6ff',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{
          fontSize: 10, fontWeight: 800, borderRadius: 3, padding: '1px 6px',
          color: isMayor ? '#15803d' : '#1d4ed8',
          background: isMayor ? '#bbf7d0' : '#bfdbfe',
        }}>{isMayor ? 'MAYOR' : 'EXTRACTO'}</span>
        <span style={{
          marginLeft: 'auto', background: '#f1f5f9', borderRadius: 10,
          padding: '1px 7px', fontSize: 11, fontWeight: 700, color: '#64748b',
        }}>{count}</span>
      </div>
      <div style={{ fontSize: 12, fontWeight: 700, color: isMayor ? '#15803d' : '#1d4ed8', marginBottom: 2 }}>
        {title}
      </div>
      <div style={{ fontSize: 10, color: '#64748b', lineHeight: 1.4 }}>{description}</div>
    </div>
  )
}

function EmptyCol({ text }) {
  return (
    <div style={{
      flex: 1, minHeight: 80,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '20px 12px', textAlign: 'center', color: '#94a3b8', fontSize: 12,
      background: '#f8fafc', borderRadius: 7, border: '1px dashed #e2e8f0',
    }}>
      <div style={{ fontSize: 20, marginBottom: 6 }}>✓</div>
      {text}
    </div>
  )
}

function ItemSearchBar({ value, onChange, count, sum, onSelectAll, placeholder = 'Buscar por descripción... (ej: IVA)' }) {
  const selectDisabled = count === 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: '#fafafa', borderBottom: '1px solid #f1f5f9', flexWrap: 'wrap' }}>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{ flex: '1 1 140px', minWidth: 0, padding: '6px 9px', borderRadius: 6, border: '1.5px solid #e2e8f0', fontSize: 12 }}
      />
      <span style={{ fontSize: 11, color: '#64748b', whiteSpace: 'nowrap', flexShrink: 0 }}>
        {count} ítem{count !== 1 ? 's' : ''} · {fmtMonto(sum)}
      </span>
      <button
        onClick={onSelectAll}
        disabled={selectDisabled}
        title="Tildar todos los ítems que coinciden con la búsqueda"
        style={{
          fontSize: 11, fontWeight: 700, padding: '5px 10px', borderRadius: 6, flexShrink: 0,
          border: '1px solid #cbd5e1', whiteSpace: 'nowrap',
          background: selectDisabled ? '#f1f5f9' : '#fff',
          color: selectDisabled ? '#94a3b8' : '#2563eb',
          cursor: selectDisabled ? 'default' : 'pointer',
        }}
      >
        Seleccionar todo lo filtrado
      </button>
    </div>
  )
}

// ── Cruces confirmados (Paso 2) ────────────────────────────────────────────────

const GRUPOS_CRUCE = [
  { key: 'col2', label: 'HABER (Mayor)',       side: 'mayor' },
  { key: 'col3', label: 'DEBE (Mayor)',         side: 'mayor' },
  { key: 'col1', label: 'DÉBITO (Extracto)',   side: 'extracto' },
  { key: 'col4', label: 'CRÉDITO (Extracto)',  side: 'extracto' },
]

function PairCard({ par, onDescruzar }) {
  const grupos = GRUPOS_CRUCE.filter(g => (par[g.key] || []).length > 0)
  return (
    <div style={{
      borderRadius: 8, overflow: 'hidden',
      border: '1px solid #e2e8f0', marginBottom: 6, display: 'flex',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        {grupos.map((g, gi) => par[g.key].map((item, i) => (
          <div key={item.id} style={{
            display: 'flex', alignItems: 'flex-start', gap: 8, padding: '7px 12px',
            background: g.side === 'mayor' ? '#f0fdf4' : '#eff6ff',
            borderTop: (gi > 0 || i > 0) ? `1px solid ${g.side === 'mayor' ? '#dcfce7' : '#dbeafe'}` : undefined,
          }}>
            <span style={{
              fontSize: 10, fontWeight: 800, borderRadius: 3, padding: '1px 5px', flexShrink: 0,
              color: g.side === 'mayor' ? '#15803d' : '#1d4ed8',
              background: g.side === 'mayor' ? '#bbf7d0' : '#bfdbfe',
            }}>
              {g.label}
            </span>
            <span style={{ fontSize: 10, color: '#94a3b8', width: 54, flexShrink: 0, marginTop: 1 }}>{fmtFecha(item.fecha)}</span>
            <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflowWrap: 'break-word', whiteSpace: 'normal', color: '#1e293b', lineHeight: 1.4 }}>{item.descripcion || '—'}</span>
            <span style={{ fontSize: 13, fontWeight: 800, color: g.side === 'mayor' ? '#15803d' : '#1d4ed8', flexShrink: 0 }}>{fmtMonto(item.monto)}</span>
            {item.mes_anterior && <span style={{ fontSize: 9, background: '#fed7aa', color: '#c2410c', borderRadius: 3, padding: '1px 5px', flexShrink: 0, fontWeight: 700 }}>ANT.</span>}
          </div>
        )))}
      </div>
      <button
        onClick={() => onDescruzar(par.id)}
        title="Descruzar"
        style={{ background: '#fff0f0', color: '#dc2626', border: 'none', borderLeft: '1px solid #fecaca', padding: '0 14px', fontSize: 14, fontWeight: 700, cursor: 'pointer', flexShrink: 0 }}
      >✕</button>
    </div>
  )
}

function MatchGroup({ pairs, onDescruzar }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>Cruces confirmados</span>
        <span style={{ background: '#f1f5f9', borderRadius: 10, padding: '1px 8px', fontSize: 11, fontWeight: 700, color: '#64748b' }}>
          {pairs.length} cruce{pairs.length !== 1 ? 's' : ''}
        </span>
      </div>
      {pairs.length === 0
        ? <div style={{ padding: '14px', textAlign: 'center', color: '#94a3b8', fontSize: 12, background: '#f8fafc', borderRadius: 7, border: '1px dashed #e2e8f0' }}>No hay cruces confirmados todavía.</div>
        : pairs.map(par => <PairCard key={par.id} par={par} onDescruzar={onDescruzar} />)
      }
    </div>
  )
}

// ── Completar cruces pendientes (Paso 1) ───────────────────────────────────────
// Dos paneles visuales (como antes), pero comparten UNA sola selección entre
// las 4 columnas: se puede tildar, por ejemplo, un débito + un crédito + un
// haber a la vez. Ambos paneles muestran el mismo estado/total y ejecutan el
// mismo cruce, sin importar en qué panel se apretó "Cruzar".

function PendingPanel({
  colLeftKey, colLeftSide, titleLeft, descLeft, itemsLeft,
  colRightKey, colRightSide, titleRight, descRight, itemsRight,
  sel, onToggle, onSelectAll,
  barBg, barBorder, barMsg, barMsgColor, canCruzar, onCruzar,
}) {
  const [buscarLeft, setBuscarLeft]   = useState('')
  const [buscarRight, setBuscarRight] = useState('')

  const filtradosLeft  = useMemo(() => filterByDescripcion(itemsLeft, buscarLeft),   [itemsLeft, buscarLeft])
  const filtradosRight = useMemo(() => filterByDescripcion(itemsRight, buscarRight), [itemsRight, buscarRight])
  const sumaLeft  = round2(filtradosLeft.reduce((s, x) => s + x.monto, 0))
  const sumaRight = round2(filtradosRight.reduce((s, x) => s + x.monto, 0))

  return (
    <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', overflow: 'hidden', marginBottom: 12 }}>

      <div style={{
        borderBottom: `2px solid ${barBorder}`,
        padding: '10px 14px',
        background: barBg,
        display: 'flex', alignItems: 'center', gap: 12,
        transition: 'all 0.15s',
      }}>
        <span style={{ fontSize: 12, color: barMsgColor, flex: 1, lineHeight: 1.4 }}>{barMsg}</span>
        <button
          onClick={onCruzar}
          disabled={!canCruzar}
          style={{
            background: canCruzar ? '#2563eb' : '#e2e8f0',
            color: canCruzar ? '#fff' : '#94a3b8',
            border: 'none', borderRadius: 8, padding: '8px 18px',
            fontSize: 13, fontWeight: 700,
            cursor: canCruzar ? 'pointer' : 'default', flexShrink: 0,
            transition: 'all 0.15s',
          }}
        >
          ↔ Cruzar
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
        <div style={{ borderRight: '2px solid #f1f5f9' }}>
          <ColHeader side={colLeftSide} title={titleLeft} description={descLeft} count={itemsLeft.length} />
          {itemsLeft.length > 0 && (
            <ItemSearchBar
              value={buscarLeft} onChange={setBuscarLeft}
              count={filtradosLeft.length} sum={sumaLeft}
              onSelectAll={() => onSelectAll(colLeftKey, filtradosLeft.map(x => x.id))}
            />
          )}
          <div style={{ padding: '10px 12px', maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {itemsLeft.length === 0
              ? <EmptyCol text="Sin pendientes en esta columna" />
              : filtradosLeft.length === 0
              ? <EmptyCol text="Sin resultados para la búsqueda" />
              : filtradosLeft.map(item => (
                  <ItemRow key={item.id} item={item} side={colLeftSide}
                    selected={sel[colLeftKey].includes(item.id)}
                    onClick={id => onToggle(colLeftKey, id)}
                  />
                ))
            }
          </div>
        </div>

        <div>
          <ColHeader side={colRightSide} title={titleRight} description={descRight} count={itemsRight.length} />
          {itemsRight.length > 0 && (
            <ItemSearchBar
              value={buscarRight} onChange={setBuscarRight}
              count={filtradosRight.length} sum={sumaRight}
              onSelectAll={() => onSelectAll(colRightKey, filtradosRight.map(x => x.id))}
            />
          )}
          <div style={{ padding: '10px 12px', maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {itemsRight.length === 0
              ? <EmptyCol text="Sin pendientes en esta columna" />
              : filtradosRight.length === 0
              ? <EmptyCol text="Sin resultados para la búsqueda" />
              : filtradosRight.map(item => (
                  <ItemRow key={item.id} item={item} side={colRightSide}
                    selected={sel[colRightKey].includes(item.id)}
                    onClick={id => onToggle(colRightKey, id)}
                  />
                ))
            }
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Ajuste de Saldo Contable (Paso 3) ──────────────────────────────────────────

// Efecto de cada categoría sobre el Saldo Contable cuando el pendiente se
// escribe de baja como error de un mes anterior (no una transacción a cruzar):
// un Débito no Contabilizado / No Acreditado resta, un No Debitado en Extracto /
// Crédito no Contabilizado suma.
const CATEGORIAS_AJUSTE = [
  { key: 'col1', label: 'Débitos no Contabilizados',  sign: -1 },
  { key: 'col2', label: 'No Debitados en Extracto',    sign:  1 },
  { key: 'col3', label: 'No Acreditados',              sign: -1 },
  { key: 'col4', label: 'Créditos no Contabilizados',  sign:  1 },
]

function AjusteItemRow({ item, selected, onClick }) {
  return (
    <div
      onClick={() => onClick(item.id)}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: 8,
        padding: '8px 10px', borderRadius: 7, marginBottom: 4,
        cursor: 'pointer',
        background: selected ? '#ede9fe' : item.mes_anterior ? '#fff7ed' : '#fff',
        border: `2px solid ${selected ? '#7c3aed' : item.mes_anterior ? '#fed7aa' : '#e2e8f0'}`,
        transition: 'all 0.1s',
        userSelect: 'none',
      }}
    >
      <div style={{
        width: 16, height: 16, borderRadius: 3, marginTop: 1,
        border: `2px solid ${selected ? '#7c3aed' : '#cbd5e1'}`,
        background: selected ? '#7c3aed' : 'transparent',
        flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {selected && <span style={{ color: '#fff', fontSize: 9, fontWeight: 900 }}>✓</span>}
      </div>
      <span style={{
        fontSize: 9, fontWeight: 800, borderRadius: 3, padding: '1px 5px', flexShrink: 0,
        color: '#6d28d9', background: '#ede9fe',
      }}>{item.categoriaLabel}</span>
      <span style={{ fontSize: 10, color: '#94a3b8', width: 52, flexShrink: 0, marginTop: 1 }}>
        {fmtFecha(item.fecha)}
      </span>
      <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflowWrap: 'break-word', whiteSpace: 'normal', color: '#1e293b', lineHeight: 1.4 }}>
        {item.descripcion || '—'}
      </span>
      <span style={{
        fontSize: 9, fontWeight: 800, borderRadius: 3, padding: '1px 5px', flexShrink: 0,
        color: item.sign > 0 ? '#15803d' : '#dc2626',
        background: item.sign > 0 ? '#dcfce7' : '#fee2e2',
      }}>
        {item.sign > 0 ? '+' : '−'} saldo
      </span>
      <span style={{ fontSize: 13, fontWeight: 800, color: '#0d1b4b', flexShrink: 0, marginLeft: 4 }}>
        {fmtMonto(item.monto)}
      </span>
    </div>
  )
}

function AjusteCard({ ajuste, onDeshacer }) {
  return (
    <div style={{
      borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 6,
      padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10,
      background: '#faf5ff',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#1e293b' }}>
          {ajuste.motivo || 'Ajuste de saldo contable'}
        </div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
          {fmtMonto(ajuste.monto)} · {ajuste.items.length} ítem{ajuste.items.length !== 1 ? 's' : ''} escrito{ajuste.items.length !== 1 ? 's' : ''} de baja
        </div>
      </div>
      <button
        onClick={() => onDeshacer(ajuste.id)}
        title="Deshacer ajuste"
        style={{ background: '#fff0f0', color: '#dc2626', border: '1px solid #fecaca', borderRadius: 6, padding: '5px 10px', fontSize: 11, fontWeight: 700, cursor: 'pointer', flexShrink: 0 }}
      >Deshacer</button>
    </div>
  )
}

function AjusteSaldoSection({ cols, saldoActual, ajustes, onAplicar, onDeshacer }) {
  const [motivo, setMotivo]   = useState('')
  const [selIds, setSelIds]   = useState([])
  const [buscar, setBuscar]   = useState('')

  const allItems = useMemo(() => CATEGORIAS_AJUSTE.flatMap(cat =>
    cols[cat.key].map(item => ({ ...item, categoria: cat.key, categoriaLabel: cat.label, sign: cat.sign }))
  ), [cols])

  const filtrados     = useMemo(() => filterByDescripcion(allItems, buscar), [allItems, buscar])
  const sumaFiltrados  = round2(filtrados.reduce((s, x) => s + x.monto, 0))

  function toggle(id) {
    setSelIds(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id])
  }

  function seleccionarTodoFiltrado() {
    setSelIds(p => Array.from(new Set([...p, ...filtrados.map(x => x.id)])))
  }

  const selectedItems = allItems.filter(x => selIds.includes(x.id))
  const delta         = round2(selectedItems.reduce((sum, x) => sum + x.sign * x.monto, 0))
  const nuevoSaldo     = round2(saldoActual + delta)
  const canAplicar     = selIds.length > 0

  let barBg = '#fafafa', barBorder = '#f1f5f9', barMsgColor = '#94a3b8'
  let barMsg = 'Tildá los pendientes que corresponden a errores de meses anteriores — el saldo contable se ajusta solo, según cómo tildes.'
  if (canAplicar) {
    barBg = '#f0fdf4'; barBorder = '#16a34a'; barMsgColor = '#15803d'
    barMsg = `Saldo actual: ${fmtMonto(saldoActual)} → Saldo ajustado: ${fmtMonto(nuevoSaldo)} (${delta >= 0 ? '+' : ''}${fmtMonto(delta)}, ${selIds.length} ítem${selIds.length > 1 ? 's' : ''}). Hacé clic en Aplicar ajuste.`
  }

  function handleAplicar() {
    onAplicar(delta, motivo.trim(), selectedItems)
    setMotivo(''); setSelIds([])
  }

  return (
    <>
      {ajustes.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          {ajustes.map(a => <AjusteCard key={a.id} ajuste={a} onDeshacer={onDeshacer} />)}
        </div>
      )}

      <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', overflow: 'hidden' }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #f1f5f9' }}>
          <input
            type="text"
            placeholder="Motivo (ej: corrección asiento duplicado marzo)"
            value={motivo}
            onChange={e => setMotivo(e.target.value)}
            style={{ width: '100%', padding: '8px 10px', borderRadius: 7, border: '1.5px solid #cbd5e1', fontSize: 13, boxSizing: 'border-box' }}
          />
        </div>

        <div style={{
          borderBottom: `2px solid ${barBorder}`, padding: '10px 14px', background: barBg,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <span style={{ fontSize: 12, color: barMsgColor, flex: 1, lineHeight: 1.4 }}>{barMsg}</span>
          <button
            onClick={handleAplicar}
            disabled={!canAplicar}
            style={{
              background: canAplicar ? '#7c3aed' : '#e2e8f0',
              color: canAplicar ? '#fff' : '#94a3b8',
              border: 'none', borderRadius: 8, padding: '8px 18px',
              fontSize: 13, fontWeight: 700,
              cursor: canAplicar ? 'pointer' : 'default', flexShrink: 0,
            }}
          >
            Aplicar ajuste
          </button>
        </div>

        {allItems.length > 0 && (
          <ItemSearchBar
            value={buscar} onChange={setBuscar}
            count={filtrados.length} sum={sumaFiltrados}
            onSelectAll={seleccionarTodoFiltrado}
          />
        )}

        <div style={{ padding: '10px 12px', maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {allItems.length === 0
            ? <EmptyCol text="No hay pendientes para ajustar." />
            : filtrados.length === 0
            ? <EmptyCol text="Sin resultados para la búsqueda" />
            : filtrados.map(item => (
                <AjusteItemRow key={item.id} item={item}
                  selected={selIds.includes(item.id)}
                  onClick={toggle}
                />
              ))
          }
        </div>
      </div>
    </>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReconciliationReview({ banco, previewData, onBack, onSuccess }) {
  const [col1, setCol1] = useState(previewData.col1)   // extracto DÉBITO
  const [col2, setCol2] = useState(previewData.col2)   // mayor HABER
  const [col3, setCol3] = useState(previewData.col3)   // mayor DEBE
  const [col4, setCol4] = useState(previewData.col4)   // extracto CRÉDITO

  const [matched, setMatched] = useState(() => normalizeMatches(previewData))

  // Al editar una conciliación ya guardada, previewData trae los ajustes aplicados;
  // al partir de una preview nueva, arranca vacío.
  const [ajustes, setAjustes] = useState(previewData.ajustes ?? [])  // { id, monto, motivo, items: [{...item, categoria}] }

  // Selección única compartida entre las 4 columnas — se puede tildar cualquier
  // combinación (ej: un débito + un crédito + un haber) y cruzarlos juntos.
  const [sel, setSel] = useState({ col1: [], col2: [], col3: [], col4: [] })

  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [done,    setDone]    = useState(false)

  const partidas = useMemo(() => round2(
    col1.reduce((s, x) => s + x.monto, 0) -
    col2.reduce((s, x) => s + x.monto, 0) +
    col3.reduce((s, x) => s + x.monto, 0) -
    col4.reduce((s, x) => s + x.monto, 0)
  ), [col1, col2, col3, col4])

  const ajustesTotal        = useMemo(() => round2(ajustes.reduce((s, a) => s + a.monto, 0)), [ajustes])
  const saldoContableAjustado = round2(previewData.saldo_contable + ajustesTotal)

  const diferencia = round2(previewData.saldo_banco + partidas - saldoContableAjustado)
  const difOk = Math.abs(diferencia) < TOLERANCIA_CRUCE

  // ── Selección compartida (Paso 1) ────────────────────────────────────────────

  function toggleSel(col, id) {
    setSel(p => ({ ...p, [col]: p[col].includes(id) ? p[col].filter(x => x !== id) : [...p[col], id] }))
  }

  function selectAllSel(col, ids) {
    setSel(p => ({ ...p, [col]: Array.from(new Set([...p[col], ...ids])) }))
  }

  function limpiarSeleccion() {
    setSel({ col1: [], col2: [], col3: [], col4: [] })
  }

  const seleccionados = useMemo(() => ({
    col1: col1.filter(x => sel.col1.includes(x.id)),
    col2: col2.filter(x => sel.col2.includes(x.id)),
    col3: col3.filter(x => sel.col3.includes(x.id)),
    col4: col4.filter(x => sel.col4.includes(x.id)),
  }), [col1, col2, col3, col4, sel])

  const totalSeleccionado = useMemo(() => {
    const suma = arr => arr.reduce((s, x) => s + x.monto, 0)
    return round2(
      suma(seleccionados.col1) + suma(seleccionados.col3) -
      suma(seleccionados.col2) - suma(seleccionados.col4)
    )
  }, [seleccionados])

  const cantidadSeleccionada = sel.col1.length + sel.col2.length + sel.col3.length + sel.col4.length
  const hayAlgoSeleccionado  = cantidadSeleccionada > 0
  const ladoPositivo = seleccionados.col1.length + seleccionados.col3.length   // débito + debe
  const ladoNegativo = seleccionados.col2.length + seleccionados.col4.length   // haber + crédito
  const diferenciaOk = hayAlgoSeleccionado && Math.abs(totalSeleccionado) < TOLERANCIA_CRUCE
  const puedeCruzar  = diferenciaOk && ladoPositivo > 0 && ladoNegativo > 0

  let barBg = '#fafafa', barBorder = '#f1f5f9', barMsgColor = '#94a3b8'
  let barMsg = 'Tildá ítems de cualquiera de las 4 columnas — se suman y restan entre sí hasta que la diferencia quede dentro del margen permitido.'
  if (hayAlgoSeleccionado && !diferenciaOk) {
    barBg = '#fff7ed'; barBorder = '#f59e0b'; barMsgColor = '#b45309'
    barMsg = `Seleccionado: ${cantidadSeleccionada} ítem${cantidadSeleccionada > 1 ? 's' : ''} — Diferencia: ${fmtMonto(totalSeleccionado)} (margen permitido: ${fmtMonto(TOLERANCIA_CRUCE)}).`
  } else if (diferenciaOk && !puedeCruzar) {
    barBg = '#fff7ed'; barBorder = '#fed7aa'; barMsgColor = '#92400e'
    barMsg = `Diferencia dentro del margen (${fmtMonto(totalSeleccionado)}), pero falta seleccionar algo del otro lado (Mayor o Extracto) para poder cruzar.`
  } else if (puedeCruzar) {
    barBg = '#f0fdf4'; barBorder = '#16a34a'; barMsgColor = '#15803d'
    barMsg = `✓ Diferencia: ${fmtMonto(totalSeleccionado)} (dentro del margen de ${fmtMonto(TOLERANCIA_CRUCE)}), ${cantidadSeleccionada} ítems. Hacé clic en Cruzar.`
  }

  function handleCruzar() {
    if (!puedeCruzar) return
    setMatched(p => [...p, {
      id: crypto.randomUUID(),
      col1: seleccionados.col1, col2: seleccionados.col2,
      col3: seleccionados.col3, col4: seleccionados.col4,
    }])
    setCol1(p => p.filter(x => !sel.col1.includes(x.id)))
    setCol2(p => p.filter(x => !sel.col2.includes(x.id)))
    setCol3(p => p.filter(x => !sel.col3.includes(x.id)))
    setCol4(p => p.filter(x => !sel.col4.includes(x.id)))
    limpiarSeleccion()
  }

  function descruzar(matchId) {
    const m = matched.find(x => x.id === matchId)
    if (!m) return
    setMatched(p => p.filter(x => x.id !== matchId))
    setCol1(p => [...p, ...m.col1])
    setCol2(p => [...p, ...m.col2])
    setCol3(p => [...p, ...m.col3])
    setCol4(p => [...p, ...m.col4])
  }

  function aplicarAjuste(monto, motivo, items) {
    const ids = new Set(items.map(x => x.id))
    setCol1(p => p.filter(x => !ids.has(x.id)))
    setCol2(p => p.filter(x => !ids.has(x.id)))
    setCol3(p => p.filter(x => !ids.has(x.id)))
    setCol4(p => p.filter(x => !ids.has(x.id)))
    setAjustes(p => [...p, { id: crypto.randomUUID(), monto, motivo, items }])
  }

  function deshacerAjuste(ajusteId) {
    const ajuste = ajustes.find(a => a.id === ajusteId)
    if (!ajuste) return
    setAjustes(p => p.filter(a => a.id !== ajusteId))
    const porCategoria = { col1: [], col2: [], col3: [], col4: [] }
    ajuste.items.forEach(it => porCategoria[it.categoria].push(it))
    setCol1(p => [...p, ...porCategoria.col1])
    setCol2(p => [...p, ...porCategoria.col2])
    setCol3(p => [...p, ...porCategoria.col3])
    setCol4(p => [...p, ...porCategoria.col4])
  }

  async function handleGenerar(download = true) {
    setLoading(true); setError(null); setDone(false)
    try {
      const res = await fetch('/api/conciliar/generar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          banco_id: previewData.banco_id,
          col1, col2, col3, col4,
          matched,
          ajustes: ajustes.map(a => ({ monto: a.monto, motivo: a.motivo, items: a.items })),
          saldo_banco:    previewData.saldo_banco,
          saldo_contable: previewData.saldo_contable,
          fecha_datos:    previewData.fecha_datos,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Error ${res.status}`)
      }
      const blob = await res.blob()
      if (download) {
        const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                       'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
        const fecha    = previewData.fecha_datos ? new Date(previewData.fecha_datos + 'T12:00:00') : new Date()
        const mes      = MESES[fecha.getMonth()]
        const anio     = fecha.getFullYear()
        const nombre   = banco.nombre.replace(/[^a-zA-Z0-9]/g, '-').replace(/-+/g, '-')
        const filename = `Conciliacion-${nombre}-${mes}-${anio}.xlsx`
        const url = URL.createObjectURL(blob)
        const a   = document.createElement('a')
        a.href = url; a.download = filename; a.click()
        URL.revokeObjectURL(url)
      }
      setDone(download ? 'download' : 'saved')
      onSuccess?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const totalPendientes = col1.length + col2.length + col3.length + col4.length
  const totalCruzados   = matched.length

  return (
    <div style={{ maxWidth: 960 }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24 }}>
        <button
          onClick={onBack}
          style={{
            flexShrink: 0, marginTop: 2,
            background: '#f1f5f9', color: '#475569',
            border: '1.5px solid #cbd5e1', borderRadius: 8,
            padding: '8px 16px', fontSize: 13, fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          ← Volver
        </button>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: '#0d1b4b', margin: 0 }}>{banco.nombre}</h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>
            Revisión de conciliación · {totalCruzados} cruce{totalCruzados !== 1 ? 's' : ''} · {totalPendientes} ítem{totalPendientes !== 1 ? 's' : ''} pendiente{totalPendientes !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* ── Balance summary (fijo arriba al hacer scroll) ── */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: '#eef1f8', paddingTop: 4, paddingBottom: 12, marginBottom: 8,
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          {[
            { label: 'Saldo Banco',    val: fmtMonto(previewData.saldo_banco),    note: 'Saldo final del extracto',      color: '#0d1b4b', bg: '#fff' },
            { label: 'Partidas pend.', val: fmtMonto(partidas),                   note: 'Suma neta de ítems sin cruzar', color: '#0d1b4b', bg: '#fff' },
            {
              label: 'Saldo Contable',
              val:   fmtMonto(saldoContableAjustado),
              note:  ajustes.length > 0 ? `Incluye ${ajustes.length} ajuste${ajustes.length > 1 ? 's' : ''}: ${fmtMonto(ajustesTotal)}` : 'Saldo final del mayor contable',
              color: '#0d1b4b', bg: '#fff',
            },
            {
              label: 'Diferencia',
              val:   fmtMonto(diferencia),
              note:  difOk ? 'La conciliación cuadra ✓' : 'Existe una diferencia pendiente',
              color: difOk ? '#15803d' : '#dc2626',
              bg:    difOk ? '#f0fdf4' : '#fef2f2',
            },
          ].map(({ label, val, note, color, bg }) => (
            <div key={label} style={{ background: bg, borderRadius: 10, padding: '9px 12px', boxShadow: '0 1px 4px rgba(13,27,75,0.07)' }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{label}</div>
              <div style={{ fontSize: 15, fontWeight: 800, color, lineHeight: 1.2 }}>{val}</div>
              <div style={{ fontSize: 9, color: '#94a3b8', marginTop: 2 }}>{note}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Paso 1: Completar cruces pendientes ── */}
      <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', padding: '20px 24px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
          <SectionHeader
            step="1"
            title="Completar cruces pendientes"
            description="Tildá ítems de cualquiera de las 4 columnas (podés combinar, por ejemplo, un débito con un crédito y un haber). Cuando la diferencia entre lo tildado quede dentro del margen permitido, presioná Cruzar."
          />
          <button
            onClick={limpiarSeleccion}
            disabled={!hayAlgoSeleccionado}
            style={{
              flexShrink: 0, marginTop: 2,
              background: hayAlgoSeleccionado ? '#fff' : '#f1f5f9',
              color: hayAlgoSeleccionado ? '#dc2626' : '#94a3b8',
              border: `1.5px solid ${hayAlgoSeleccionado ? '#fecaca' : '#e2e8f0'}`,
              borderRadius: 8, padding: '7px 14px', fontSize: 12, fontWeight: 700,
              cursor: hayAlgoSeleccionado ? 'pointer' : 'default', whiteSpace: 'nowrap',
            }}
          >
            Destildar selección
          </button>
        </div>

        <PendingPanel
          colLeftKey="col2" colLeftSide="mayor"
          titleLeft="No Debitados en Extracto"
          descLeft="En el Mayor como HABER, pero no aparece como débito en el Extracto."
          itemsLeft={col2}
          colRightKey="col1" colRightSide="extracto"
          titleRight="Débitos no Contabilizados"
          descRight="Débito en el Extracto, pero no está en el Mayor contable."
          itemsRight={col1}
          sel={sel} onToggle={toggleSel} onSelectAll={selectAllSel}
          barBg={barBg} barBorder={barBorder} barMsg={barMsg} barMsgColor={barMsgColor}
          canCruzar={puedeCruzar} onCruzar={handleCruzar}
        />

        <PendingPanel
          colLeftKey="col3" colLeftSide="mayor"
          titleLeft="No Acreditados"
          descLeft="En el Mayor como DEBE, pero no aparece como crédito en el Extracto."
          itemsLeft={col3}
          colRightKey="col4" colRightSide="extracto"
          titleRight="Créditos no Contabilizados"
          descRight="Crédito en el Extracto, pero no está en el Mayor contable."
          itemsRight={col4}
          sel={sel} onToggle={toggleSel} onSelectAll={selectAllSel}
          barBg={barBg} barBorder={barBorder} barMsg={barMsg} barMsgColor={barMsgColor}
          canCruzar={puedeCruzar} onCruzar={handleCruzar}
        />
      </div>

      {/* ── Paso 2: Verificar cruces ── */}
      <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', padding: '20px 24px', marginBottom: 20 }}>
        <SectionHeader
          step="2"
          title="Verificar cruces confirmados"
          description="Automáticos y manuales quedan juntos acá. Revisá que sean correctos. Si alguno no corresponde, usá ✕ para deshacerlo — los ítems vuelven a la lista de pendientes."
        />
        <MatchGroup pairs={matched} onDescruzar={descruzar} />
      </div>

      {/* ── Paso 3: Ajuste de saldo contable ── */}
      <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', padding: '20px 24px', marginBottom: 24 }}>
        <SectionHeader
          step="3"
          title="Ajuste de saldo contable"
          description="Si la diferencia viene de un error de un mes anterior (no de una transacción real que cruzar), tildá el o los pendientes que explican ese error — el saldo contable se ajusta solo según la categoría de cada uno, sin necesidad de buscarles pareja del otro lado."
        />
        <AjusteSaldoSection
          cols={{ col1, col2, col3, col4 }}
          saldoActual={saldoContableAjustado}
          ajustes={ajustes}
          onAplicar={aplicarAjuste}
          onDeshacer={deshacerAjuste}
        />
      </div>

      {/* ── Generate ── */}
      <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: '#0d1b4b' }}>
              {difOk ? '✓ La conciliación está balanceada' : `⚠ Diferencia de ${fmtMonto(diferencia)}`}
            </div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 3 }}>
              {totalPendientes > 0
                ? `${totalPendientes} ítem${totalPendientes !== 1 ? 's' : ''} quedarán como partidas pendientes en el Excel.`
                : 'Todos los ítems están cruzados.'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
            <button
              onClick={() => handleGenerar(false)}
              disabled={loading}
              style={{
                background: loading ? '#e2e8f0' : '#f1f5f9',
                color: loading ? '#94a3b8' : '#0d1b4b',
                border: '1.5px solid #cbd5e1', borderRadius: 9,
                padding: '13px 22px', fontSize: 14, fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {loading ? 'Guardando...' : '✓ Confirmar'}
            </button>
            <button
              onClick={() => handleGenerar(true)}
              disabled={loading}
              style={{
                background: loading ? '#c7d5f0' : '#2563eb',
                color: '#fff', border: 'none', borderRadius: 9,
                padding: '13px 22px', fontSize: 14, fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {loading ? 'Generando...' : '↓ Confirmar y Descargar'}
            </button>
          </div>
        </div>

        {done && (
          <div style={{ marginTop: 14, padding: '12px 16px', background: '#dcfce7', border: '1px solid #bbf7d0', borderRadius: 8, color: '#15803d', fontSize: 13, fontWeight: 600 }}>
            {done === 'download' ? '✓ Conciliación guardada y descargada.' : '✓ Conciliación guardada correctamente.'}
          </div>
        )}
        {error && (
          <div style={{ marginTop: 14, padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, color: '#dc2626', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>

    </div>
  )
}
