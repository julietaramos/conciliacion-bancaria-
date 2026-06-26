import { useState, useMemo } from 'react'

// ── Helpers ───────────────────────────────────────────────────────────────────

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

// Normalize pairs from backend (extracto singular) to new format (extractos array)
function normalizePairs(pairs) {
  return (pairs || []).map(p => ({
    ...p,
    extractos: p.extractos ?? (p.extracto ? [p.extracto] : []),
  }))
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

function ItemRow({ item, selected, side, onClick, disabled }) {
  const colors = side === 'mayor'
    ? { sel: '#dcfce7', selBorder: '#16a34a' }
    : { sel: '#dbeafe', selBorder: '#2563eb' }

  return (
    <div
      onClick={() => !disabled && onClick(item.id)}
      style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 10px', borderRadius: 7, marginBottom: 4,
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        background: selected ? colors.sel : item.mes_anterior ? '#fff7ed' : '#fff',
        border: `2px solid ${selected ? colors.selBorder : item.mes_anterior ? '#fed7aa' : '#e2e8f0'}`,
        transition: 'all 0.1s',
        userSelect: 'none',
      }}
    >
      <div style={{
        width: 16, height: 16, borderRadius: side === 'mayor' ? '50%' : 3,
        border: `2px solid ${selected ? colors.selBorder : '#cbd5e1'}`,
        background: selected ? colors.selBorder : 'transparent',
        flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {selected && <span style={{ color: '#fff', fontSize: 9, fontWeight: 900 }}>✓</span>}
      </div>
      <span style={{ fontSize: 10, color: '#94a3b8', width: 52, flexShrink: 0 }}>
        {fmtFecha(item.fecha)}
      </span>
      <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1e293b' }}>
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

function PairCard({ par, onDescruzar }) {
  return (
    <div style={{
      borderRadius: 8, overflow: 'hidden',
      border: '1px solid #e2e8f0', marginBottom: 6, display: 'flex',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Mayor row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', background: '#f0fdf4', borderBottom: `1px solid ${par.extractos.length > 1 ? '#dcfce7' : 'transparent'}` }}>
          <span style={{ fontSize: 10, fontWeight: 800, color: '#15803d', background: '#bbf7d0', borderRadius: 3, padding: '1px 5px', flexShrink: 0 }}>MAYOR</span>
          <span style={{ fontSize: 10, color: '#94a3b8', width: 54, flexShrink: 0 }}>{fmtFecha(par.mayor.fecha)}</span>
          <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1e293b' }}>{par.mayor.descripcion || '—'}</span>
          <span style={{ fontSize: 13, fontWeight: 800, color: '#15803d', flexShrink: 0 }}>{fmtMonto(par.mayor.monto)}</span>
          {par.mayor.mes_anterior && <span style={{ fontSize: 9, background: '#fed7aa', color: '#c2410c', borderRadius: 3, padding: '1px 5px', flexShrink: 0, fontWeight: 700 }}>ANT.</span>}
        </div>
        {/* Extracto rows (1 or more) */}
        {par.extractos.map((ext, i) => (
          <div key={ext.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', background: '#eff6ff', borderTop: i > 0 ? '1px solid #dbeafe' : undefined }}>
            <span style={{ fontSize: 10, fontWeight: 800, color: '#1d4ed8', background: '#bfdbfe', borderRadius: 3, padding: '1px 5px', flexShrink: 0 }}>
              {par.extractos.length > 1 ? `EXT. ${i+1}` : 'EXTRACTO'}
            </span>
            <span style={{ fontSize: 10, color: '#94a3b8', width: 54, flexShrink: 0 }}>{fmtFecha(ext.fecha)}</span>
            <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1e293b' }}>{ext.descripcion || '—'}</span>
            <span style={{ fontSize: 13, fontWeight: 800, color: '#1d4ed8', flexShrink: 0 }}>{fmtMonto(ext.monto)}</span>
            {ext.mes_anterior && <span style={{ fontSize: 9, background: '#fed7aa', color: '#c2410c', borderRadius: 3, padding: '1px 5px', flexShrink: 0, fontWeight: 700 }}>ANT.</span>}
          </div>
        ))}
      </div>
      <button
        onClick={() => onDescruzar(par.id)}
        title="Descruzar"
        style={{ background: '#fff0f0', color: '#dc2626', border: 'none', borderLeft: '1px solid #fecaca', padding: '0 14px', fontSize: 14, fontWeight: 700, cursor: 'pointer', flexShrink: 0 }}
      >✕</button>
    </div>
  )
}

function MatchGroup({ title, pairs, onDescruzar, emptyText }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>{title}</span>
        <span style={{ background: '#f1f5f9', borderRadius: 10, padding: '1px 8px', fontSize: 11, fontWeight: 700, color: '#64748b' }}>
          {pairs.length} par{pairs.length !== 1 ? 'es' : ''}
        </span>
      </div>
      {pairs.length === 0
        ? <div style={{ padding: '14px', textAlign: 'center', color: '#94a3b8', fontSize: 12, background: '#f8fafc', borderRadius: 7, border: '1px dashed #e2e8f0' }}>{emptyText}</div>
        : pairs.map(par => <PairCard key={par.id} par={par} onDescruzar={onDescruzar} />)
      }
    </div>
  )
}

function PendingGroup({
  titleMayor, titleExtracto, descMayor, descExtracto,
  colMayor, colExtracto,
  selMayor, selExtractos,
  onSelMayor, onToggleExtracto,
  onCruzar,
}) {
  const mayorItem  = colMayor.find(x => x.id === selMayor) ?? null
  const covered    = round2(selExtractos.reduce((sum, id) => {
    const item = colExtracto.find(x => x.id === id)
    return sum + (item?.monto ?? 0)
  }, 0))
  const remaining  = mayorItem ? round2(mayorItem.monto - covered) : null
  const balanced   = remaining !== null && Math.abs(remaining) < 0.02
  const canCruzar  = !!mayorItem && selExtractos.length > 0 && balanced

  // Action bar content depending on state
  let barBg      = '#fafafa'
  let barBorder  = '#f1f5f9'
  let barMsg     = 'Paso 1: seleccioná un ítem de la columna verde (Mayor).'
  let barMsgColor = '#94a3b8'

  if (mayorItem && selExtractos.length === 0) {
    barBg = '#fff7ed'; barBorder = '#fed7aa'
    barMsg = `Objetivo: ${fmtMonto(mayorItem.monto)} — ahora seleccioná ítems del Extracto (columna azul) hasta cubrir ese monto.`
    barMsgColor = '#92400e'
  } else if (mayorItem && !balanced) {
    barBg = '#fff7ed'; barBorder = '#f59e0b'
    barMsg = `Objetivo: ${fmtMonto(mayorItem.monto)} — Cubierto: ${fmtMonto(covered)} — Falta: ${fmtMonto(remaining)}`
    barMsgColor = '#b45309'
  } else if (canCruzar) {
    barBg = '#f0fdf4'; barBorder = '#16a34a'
    barMsg = `✓ Monto cubierto: ${fmtMonto(mayorItem.monto)} (${selExtractos.length} ítem${selExtractos.length > 1 ? 's' : ''} del Extracto). Hacé clic en Cruzar.`
    barMsgColor = '#15803d'
  }

  return (
    <div style={{ background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', overflow: 'hidden', marginBottom: 12 }}>

      {/* Action bar — top */}
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

      {/* Columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
        {/* Mayor column */}
        <div style={{ borderRight: '2px solid #f1f5f9' }}>
          <ColHeader side="mayor" title={titleMayor} description={descMayor} count={colMayor.length} />
          <div style={{ padding: '10px 12px', maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {colMayor.length === 0
              ? <EmptyCol text="Sin pendientes en esta columna" />
              : colMayor.map(item => (
                  <ItemRow key={item.id} item={item} side="mayor"
                    selected={selMayor === item.id}
                    onClick={onSelMayor}
                  />
                ))
            }
          </div>
        </div>

        {/* Extracto column */}
        <div>
          <ColHeader side="extracto" title={titleExtracto} description={descExtracto} count={colExtracto.length} />
          <div style={{ padding: '10px 12px', maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {colExtracto.length === 0
              ? <EmptyCol text="Sin pendientes en esta columna" />
              : colExtracto.map(item => (
                  <ItemRow key={item.id} item={item} side="extracto"
                    selected={selExtractos.includes(item.id)}
                    disabled={!selMayor}
                    onClick={onToggleExtracto}
                  />
                ))
            }
            {!selMayor && colExtracto.length > 0 && (
              <div style={{ fontSize: 10, color: '#94a3b8', textAlign: 'center', marginTop: 6, fontStyle: 'italic' }}>
                Seleccioná primero un ítem del Mayor para habilitar esta columna
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReconciliationReview({ banco, previewData, onBack, onSuccess }) {
  const [col1, setCol1] = useState(previewData.col1)   // extracto DÉBITO
  const [col2, setCol2] = useState(previewData.col2)   // mayor HABER
  const [col3, setCol3] = useState(previewData.col3)   // mayor DEBE
  const [col4, setCol4] = useState(previewData.col4)   // extracto CRÉDITO

  const [matchedHD, setMatchedHD] = useState(() => normalizePairs(previewData.matched_haber_debito))
  const [matchedDC, setMatchedDC] = useState(() => normalizePairs(previewData.matched_debe_credito))

  // HABER/DÉBITO selections: 1 Mayor + N Extracto
  const [selHaber,   setSelHaber]   = useState(null)  // col2 id
  const [selDebitos, setSelDebitos] = useState([])    // col1 ids

  // DEBE/CRÉDITO selections: 1 Mayor + N Extracto
  const [selDebe,     setSelDebe]     = useState(null) // col3 id
  const [selCreditos, setSelCreditos] = useState([])   // col4 ids

  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [done,    setDone]    = useState(false)

  const partidas = useMemo(() => round2(
    col1.reduce((s, x) => s + x.monto, 0) -
    col2.reduce((s, x) => s + x.monto, 0) +
    col3.reduce((s, x) => s + x.monto, 0) -
    col4.reduce((s, x) => s + x.monto, 0)
  ), [col1, col2, col3, col4])

  const diferencia = round2(previewData.saldo_banco + partidas - previewData.saldo_contable)
  const difOk = Math.abs(diferencia) < 0.02

  // ── Handlers ──────────────────────────────────────────────────────────────

  function selectHaber(id) {
    const next = selHaber === id ? null : id
    setSelHaber(next)
    setSelDebitos([])  // clear extracto selections when mayor changes
  }

  function toggleDebito(id) {
    if (!selHaber) return
    setSelDebitos(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id])
  }

  function selectDebe(id) {
    const next = selDebe === id ? null : id
    setSelDebe(next)
    setSelCreditos([])
  }

  function toggleCredito(id) {
    if (!selDebe) return
    setSelCreditos(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id])
  }

  function cruzarHD() {
    const mayor = col2.find(x => x.id === selHaber)
    const exts  = col1.filter(x => selDebitos.includes(x.id))
    if (!mayor || exts.length === 0) return
    setMatchedHD(p => [...p, { id: crypto.randomUUID(), mayor, extractos: exts }])
    setCol2(p => p.filter(x => x.id !== selHaber))
    setCol1(p => p.filter(x => !selDebitos.includes(x.id)))
    setSelHaber(null); setSelDebitos([])
  }

  function cruzarDC() {
    const mayor = col3.find(x => x.id === selDebe)
    const exts  = col4.filter(x => selCreditos.includes(x.id))
    if (!mayor || exts.length === 0) return
    setMatchedDC(p => [...p, { id: crypto.randomUUID(), mayor, extractos: exts }])
    setCol3(p => p.filter(x => x.id !== selDebe))
    setCol4(p => p.filter(x => !selCreditos.includes(x.id)))
    setSelDebe(null); setSelCreditos([])
  }

  function descruzarHD(pairId) {
    const par = matchedHD.find(p => p.id === pairId)
    if (!par) return
    setMatchedHD(p => p.filter(x => x.id !== pairId))
    setCol2(p => [...p, par.mayor])
    setCol1(p => [...p, ...par.extractos])
  }

  function descruzarDC(pairId) {
    const par = matchedDC.find(p => p.id === pairId)
    if (!par) return
    setMatchedDC(p => p.filter(x => x.id !== pairId))
    setCol3(p => [...p, par.mayor])
    setCol4(p => [...p, ...par.extractos])
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
          matched_haber_debito: matchedHD,
          matched_debe_credito: matchedDC,
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
  const totalCruzados   = matchedHD.length + matchedDC.length

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
            Revisión de conciliación · {totalCruzados} cruce{totalCruzados !== 1 ? 's' : ''} automático{totalCruzados !== 1 ? 's' : ''} · {totalPendientes} ítem{totalPendientes !== 1 ? 's' : ''} pendiente{totalPendientes !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* ── Balance summary ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 28 }}>
        {[
          { label: 'Saldo Banco',    val: fmtMonto(previewData.saldo_banco),    note: 'Saldo final del extracto',      color: '#0d1b4b', bg: '#fff' },
          { label: 'Partidas pend.', val: fmtMonto(partidas),                   note: 'Suma neta de ítems sin cruzar', color: '#0d1b4b', bg: '#fff' },
          { label: 'Saldo Contable', val: fmtMonto(previewData.saldo_contable), note: 'Saldo final del mayor contable', color: '#0d1b4b', bg: '#fff' },
          {
            label: 'Diferencia',
            val:   fmtMonto(diferencia),
            note:  difOk ? 'La conciliación cuadra ✓' : 'Existe una diferencia pendiente',
            color: difOk ? '#15803d' : '#dc2626',
            bg:    difOk ? '#f0fdf4' : '#fef2f2',
          },
        ].map(({ label, val, note, color, bg }) => (
          <div key={label} style={{ background: bg, borderRadius: 10, padding: '14px 16px', boxShadow: '0 1px 4px rgba(13,27,75,0.07)' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 800, color, lineHeight: 1 }}>{val}</div>
            <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>{note}</div>
          </div>
        ))}
      </div>

      {/* ── Step 1: Verify automatics ── */}
      <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', padding: '20px 24px', marginBottom: 20 }}>
        <SectionHeader
          step="1"
          title="Verificar cruces automáticos"
          description="El sistema cruzó estos ítems por monto y fecha. Revisá que sean correctos. Si alguno no corresponde, usá ✕ para deshacerlo — el ítem vuelve a la lista de pendientes."
        />
        <MatchGroup
          title="HABER (Mayor) ↔ DÉBITO (Extracto)"
          pairs={matchedHD}
          onDescruzar={descruzarHD}
          emptyText="No hay cruces automáticos en esta categoría."
        />
        <MatchGroup
          title="DEBE (Mayor) ↔ CRÉDITO (Extracto)"
          pairs={matchedDC}
          onDescruzar={descruzarDC}
          emptyText="No hay cruces automáticos en esta categoría."
        />
      </div>

      {/* ── Step 2: Manual pending ── */}
      <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(13,27,75,0.07)', padding: '20px 24px', marginBottom: 24 }}>
        <SectionHeader
          step="2"
          title="Completar cruces pendientes"
          description="Seleccioná 1 ítem del Mayor (verde) para fijar el monto objetivo. Luego seleccioná uno o más ítems del Extracto (azul) hasta cubrir ese monto. Cuando cuadre, presioná Cruzar."
        />

        <PendingGroup
          titleMayor="No Debitados en Extracto"
          titleExtracto="Débitos no Contabilizados"
          descMayor="En el Mayor como HABER, pero no aparece como débito en el Extracto."
          descExtracto="Débito en el Extracto, pero no está en el Mayor contable."
          colMayor={col2}
          colExtracto={col1}
          selMayor={selHaber}
          selExtractos={selDebitos}
          onSelMayor={selectHaber}
          onToggleExtracto={toggleDebito}
          onCruzar={cruzarHD}
        />

        <PendingGroup
          titleMayor="No Acreditados"
          titleExtracto="Créditos no Contabilizados"
          descMayor="En el Mayor como DEBE, pero no aparece como crédito en el Extracto."
          descExtracto="Crédito en el Extracto, pero no está en el Mayor contable."
          colMayor={col3}
          colExtracto={col4}
          selMayor={selDebe}
          selExtractos={selCreditos}
          onSelMayor={selectDebe}
          onToggleExtracto={toggleCredito}
          onCruzar={cruzarDC}
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
