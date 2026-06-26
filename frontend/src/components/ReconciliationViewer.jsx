const CATEGORY_COLORS = {
  1: '#fff3cd',
  2: '#d1ecf1',
  3: '#f8d7da',
  4: '#d4edda',
}

const s = {
  card: {
    background: '#fff',
    borderRadius: 12,
    padding: 24,
    boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: 700,
    color: '#0d1b4b',
    marginBottom: 16,
    paddingBottom: 8,
    borderBottom: '2px solid #e8ecf8',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    background: '#0d1b4b',
    color: '#fff',
    padding: '10px 12px',
    textAlign: 'left',
    fontWeight: 600,
  },
  td: {
    padding: '9px 12px',
    borderBottom: '1px solid #eef0f8',
  },
  btnRow: {
    display: 'flex',
    gap: 12,
    marginBottom: 24,
    flexWrap: 'wrap',
  },
  btn: {
    background: '#1a3c8f',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '10px 20px',
    fontSize: 13,
    fontWeight: 600,
  },
  btnSecondary: {
    background: '#fff',
    color: '#1a3c8f',
    border: '2px solid #1a3c8f',
    borderRadius: 8,
    padding: '10px 20px',
    fontSize: 13,
    fontWeight: 600,
  },
  badge: (conciliado) => ({
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    background: conciliado ? '#d4edda' : '#f8d7da',
    color: conciliado ? '#155724' : '#721c24',
  }),
}

function downloadCSV(data, filename) {
  if (!data.length) return
  const headers = Object.keys(data[0]).join(',')
  const rows = data.map(r => Object.values(r).map(v => `"${v}"`).join(','))
  const csv = [headers, ...rows].join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function SummaryStats({ result }) {
  const total = result.mayor_procesado.length + result.banco_procesado.length
  const conciliadosMayor = result.mayor_procesado.filter(r => r.conciliado).length
  const conciliadosBanco = result.banco_procesado.filter(r => r.conciliado).length
  const diferencias = result.archivo_diferencias.length

  return (
    <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
      {[
        { label: 'Registros Mayor', value: result.mayor_procesado.length, color: '#0d1b4b' },
        { label: 'Registros Banco', value: result.banco_procesado.length, color: '#0d1b4b' },
        { label: 'Conciliados Mayor', value: conciliadosMayor, color: '#155724' },
        { label: 'Conciliados Banco', value: conciliadosBanco, color: '#155724' },
        { label: 'Diferencias', value: diferencias, color: '#c0392b' },
      ].map(stat => (
        <div key={stat.label} style={{
          background: '#fff',
          borderRadius: 10,
          padding: '14px 20px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          minWidth: 140,
          flex: 1,
        }}>
          <div style={{ fontSize: 26, fontWeight: 700, color: stat.color }}>{stat.value}</div>
          <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{stat.label}</div>
        </div>
      ))}
    </div>
  )
}

function DifferencesTable({ data }) {
  if (!data.length) return (
    <div style={{ color: '#155724', background: '#d4edda', padding: '14px 16px', borderRadius: 8 }}>
      Sin diferencias — todos los registros fueron conciliados.
    </div>
  )

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={s.table}>
        <thead>
          <tr>
            {['Cat.', 'Descripción', 'Origen', 'Fecha', 'Detalle', 'Referencia', 'Monto ($)'].map(h => (
              <th key={h} style={s.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((d, i) => (
            <tr key={i} style={{ background: CATEGORY_COLORS[d.categoria] || '#fff' }}>
              <td style={s.td}><strong>{d.categoria}</strong></td>
              <td style={s.td}>{d.categoria_label}</td>
              <td style={s.td}>{d.origen}</td>
              <td style={s.td}>{d.fecha}</td>
              <td style={s.td}>{d.detalle}</td>
              <td style={s.td}>{d.referencia}</td>
              <td style={{ ...s.td, fontWeight: 600 }}>{Number(d.monto).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AuditTable({ data, label }) {
  if (!data.length) return null

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={s.table}>
        <thead>
          <tr>
            {['Estado', 'Fecha', 'Detalle', 'Referencia', 'Tipo', 'Monto ($)'].map(h => (
              <th key={h} style={s.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f7f8ff' }}>
              <td style={s.td}>
                <span style={s.badge(r.conciliado)}>
                  {r.conciliado ? '✓ Conciliado' : '✗ Pendiente'}
                </span>
              </td>
              <td style={s.td}>{r.fecha}</td>
              <td style={s.td}>{r.detalle}</td>
              <td style={s.td}>{r.referencia}</td>
              <td style={s.td}>{r.tipo}</td>
              <td style={{ ...s.td, fontWeight: 600 }}>
                {Number(r.monto_abs).toLocaleString('es-AR', { minimumFractionDigits: 2 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ReconciliationViewer({ result, onReset }) {
  return (
    <div>
      <div style={s.btnRow}>
        <button style={s.btnSecondary} onClick={onReset}>← Nueva conciliación</button>
        <button style={s.btn} onClick={() => downloadCSV(result.archivo_diferencias, 'diferencias.csv')}>
          Descargar Diferencias CSV
        </button>
        <button style={s.btn} onClick={() => downloadCSV(result.mayor_procesado, 'mayor_procesado.csv')}>
          Descargar Mayor CSV
        </button>
        <button style={s.btn} onClick={() => downloadCSV(result.banco_procesado, 'banco_procesado.csv')}>
          Descargar Banco CSV
        </button>
      </div>

      <SummaryStats result={result} />

      <div style={s.card}>
        <div style={s.sectionTitle}>Diferencias — Partidas Pendientes</div>
        <DifferencesTable data={result.archivo_diferencias} />
      </div>

      <div style={s.card}>
        <div style={s.sectionTitle}>Mayor Contable — Vista de Auditoría</div>
        <AuditTable data={result.mayor_procesado} label="Mayor" />
      </div>

      <div style={s.card}>
        <div style={s.sectionTitle}>Extracto Bancario — Vista de Auditoría</div>
        <AuditTable data={result.banco_procesado} label="Banco" />
      </div>
    </div>
  )
}
