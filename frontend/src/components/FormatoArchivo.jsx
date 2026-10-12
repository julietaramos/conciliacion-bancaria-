import { useState } from 'react'

const FILAS_ENCABEZADO_ELEGIBLES = 20
const SIN_COLUMNA = ''

const ORIGENES = {
  guardado:   'Formato guardado de este banco',
  automatico: 'Columnas detectadas automáticamente',
  manual:     'Columnas ajustadas a mano',
}

const ESTADOS = {
  error:       { icono: '✕', texto: 'Hay que corregir el formato', color: '#dc2626', fondo: '#fef2f2', borde: '#fecaca' },
  advertencia: { icono: '⚠', texto: 'Revisá las columnas tomadas', color: '#b45309', fondo: '#fffbeb', borde: '#fde68a' },
  ok:          { icono: '✓', texto: 'Formato reconocido',          color: '#15803d', fondo: '#f0fdf4', borde: '#bbf7d0' },
}

const formatoMonto = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function estadoDe(inspeccion) {
  if (inspeccion.errores.length) return ESTADOS.error
  if (inspeccion.advertencias.length) return ESTADOS.advertencia
  return ESTADOS.ok
}

function mostrarValor(valor, esMonto) {
  if (valor === null || valor === undefined) return ''
  if (esMonto && typeof valor === 'number') return formatoMonto.format(valor)
  return valor
}

function formatearFecha(iso) {
  const [anio, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${anio}`
}

function Mensajes({ items, color }) {
  if (!items.length) return null
  return (
    <ul style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: 12, color }}>
      {items.map(m => <li key={m} style={{ marginBottom: 3 }}>{m}</li>)}
    </ul>
  )
}

function SelectorColumnas({ inspeccion, onCambiarColumna, onCambiarFilaEncabezado, deshabilitado }) {
  const selectStyle = { width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12, background: '#fff' }
  return (
    <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10 }}>
      <label style={{ fontSize: 11, color: '#475569', fontWeight: 600 }}>
        Fila de encabezados
        <select
          value={inspeccion.fila_encabezado}
          disabled={deshabilitado}
          onChange={e => onCambiarFilaEncabezado(Number(e.target.value))}
          style={{ ...selectStyle, marginTop: 4 }}
        >
          {Array.from({ length: FILAS_ENCABEZADO_ELEGIBLES }, (_, i) => (
            <option key={i} value={i}>Fila {i + 1}</option>
          ))}
        </select>
      </label>
      {inspeccion.campos.map(campo => (
        <label key={campo.clave} style={{ fontSize: 11, color: '#475569', fontWeight: 600 }}>
          {campo.nombre}{campo.obligatorio && <span style={{ color: '#dc2626' }}> *</span>}
          <select
            value={inspeccion.columnas[campo.clave] || SIN_COLUMNA}
            disabled={deshabilitado}
            onChange={e => onCambiarColumna(campo.clave, e.target.value)}
            style={{ ...selectStyle, marginTop: 4 }}
          >
            <option value={SIN_COLUMNA}>— ninguna —</option>
            {inspeccion.columnas_disponibles.map(col => <option key={col} value={col}>{col}</option>)}
          </select>
        </label>
      ))}
      <div style={{ gridColumn: '1 / -1', fontSize: 11, color: '#94a3b8' }}>
        Importes: {inspeccion.importes_requeridos}
      </div>
    </div>
  )
}

function Muestra({ inspeccion }) {
  const campos = inspeccion.campos.filter(c => inspeccion.columnas[c.clave])
  if (!inspeccion.muestra.length) return null
  const celda = { padding: '5px 8px', borderBottom: '1px solid #e2e8f0', whiteSpace: 'nowrap' }
  return (
    <div style={{ marginTop: 12, overflowX: 'auto' }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>Así se leyeron las primeras filas</div>
      <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%', background: '#fff' }}>
        <thead>
          <tr>
            {campos.map(c => (
              <th key={c.clave} style={{ ...celda, textAlign: c.es_monto ? 'right' : 'left', color: '#64748b', fontWeight: 600 }}>
                {c.nombre}
                <div style={{ fontWeight: 400, fontSize: 10, color: '#94a3b8' }}>{inspeccion.columnas[c.clave]}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {inspeccion.muestra.map((fila, i) => (
            <tr key={i}>
              {campos.map(c => {
                const valor = fila[c.clave]
                const ilegible = c.es_monto && typeof valor === 'string'
                return (
                  <td key={c.clave} style={{ ...celda, textAlign: c.es_monto ? 'right' : 'left', color: ilegible ? '#dc2626' : '#0f172a', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {c.clave === 'fecha' ? formatearFecha(valor) : mostrarValor(valor, c.es_monto)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FormatoArchivo({ inspeccion, cargando, error, onCambiarColumna, onCambiarFilaEncabezado }) {
  const [ajustando, setAjustando] = useState(false)

  if (error) {
    return (
      <div style={{ marginTop: -10, marginBottom: 20, padding: '10px 14px', borderRadius: 8, background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 12 }}>
        {error}
      </div>
    )
  }
  if (!inspeccion) {
    return cargando ? <div style={{ marginTop: -10, marginBottom: 20, fontSize: 12, color: '#64748b' }}>Leyendo columnas…</div> : null
  }

  const estado = estadoDe(inspeccion)
  const mostrarSelector = ajustando || inspeccion.errores.length > 0
  const { resumen } = inspeccion

  return (
    <div style={{ marginTop: -10, marginBottom: 20, padding: '12px 14px', borderRadius: 8, background: estado.fondo, border: `1px solid ${estado.borde}`, opacity: cargando ? 0.6 : 1 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 800, color: estado.color }}>{estado.icono}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: estado.color }}>{estado.texto}</span>
        <span style={{ fontSize: 11, color: '#64748b' }}>· {ORIGENES[inspeccion.origen]} · encabezados en fila {inspeccion.fila_encabezado + 1}</span>
        <button
          type="button"
          onClick={() => setAjustando(a => !a)}
          disabled={inspeccion.errores.length > 0}
          style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 700, color: '#2563eb', background: '#dbeafe', border: 'none', borderRadius: 4, padding: '3px 8px', cursor: 'pointer' }}
        >
          {mostrarSelector ? 'Ocultar columnas' : 'Ajustar columnas'}
        </button>
      </div>

      {resumen && (
        <div style={{ fontSize: 12, color: '#475569', marginTop: 6 }}>
          {resumen.movimientos} movimientos leídos
          {resumen.filas_ignoradas > 0 && ` · ${resumen.filas_ignoradas} filas sin fecha ignoradas (títulos, totales, etc.)`}
        </div>
      )}

      <Mensajes items={inspeccion.errores} color="#dc2626" />
      <Mensajes items={inspeccion.advertencias} color="#b45309" />

      {mostrarSelector && (
        <SelectorColumnas
          inspeccion={inspeccion}
          deshabilitado={cargando}
          onCambiarColumna={onCambiarColumna}
          onCambiarFilaEncabezado={onCambiarFilaEncabezado}
        />
      )}

      <Muestra inspeccion={inspeccion} />
    </div>
  )
}
