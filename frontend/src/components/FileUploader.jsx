import { useState, useRef } from 'react'

function FileField({ label, hint, accept, onChange, file }) {
  const inputRef = useRef()
  return (
    <div style={{ marginBottom: 20 }}>
      <label style={{ display: 'block', fontWeight: 600, fontSize: 13, color: '#0d1b4b', marginBottom: 4 }}>
        {label}
      </label>
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>{hint}</div>
      <div
        onClick={() => inputRef.current.click()}
        style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px', borderRadius: 8, cursor: 'pointer',
          border: file ? '2px solid #2563eb' : '2px dashed #c7d5f0',
          background: file ? '#f0f7ff' : '#f5f7ff',
          transition: 'border-color 0.15s, background 0.15s',
        }}
      >
        <span style={{ fontSize: 18 }}>{file ? '📄' : '📂'}</span>
        <span style={{
          fontSize: 13, flex: 1, minWidth: 0,
          color: file ? '#1d4ed8' : '#94a3b8',
          fontWeight: file ? 600 : 400,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {file ? file.name : 'Hacer clic para seleccionar archivo'}
        </span>
        {file && (
          <span style={{ fontSize: 11, color: '#2563eb', fontWeight: 700, background: '#dbeafe', borderRadius: 4, padding: '2px 7px', flexShrink: 0 }}>
            Cambiar
          </span>
        )}
      </div>
      <input ref={inputRef} type="file" accept={accept} style={{ display: 'none' }} onChange={e => onChange(e.target.files[0] || null)} />
    </div>
  )
}

export default function FileUploader({ banco, onBack, onPreview }) {
  const [mayorFile, setMayorFile] = useState(null)
  const [bancoFile, setBancoFile] = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error,   setError]       = useState(null)

  const canSubmit = mayorFile && bancoFile && !loading

  const handleSubmit = async () => {
    if (!canSubmit) return
    setLoading(true); setError(null)

    const fd = new FormData()
    fd.append('banco_id', banco.id)
    fd.append('mayor',    mayorFile)
    fd.append('banco',    bancoFile)

    try {
      const res = await fetch('/api/conciliar/preview', { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Error ${res.status}`)
      }
      const data = await res.json()
      onPreview(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: '#0d1b4b' }}>{banco.nombre}</h1>
        <p style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>Nueva conciliación bancaria</p>
      </div>

      <div style={{ background: '#fff', borderRadius: 12, padding: '32px 36px', boxShadow: '0 1px 4px rgba(13,27,75,0.08)', maxWidth: 600 }}>
        <FileField
          label="Mayor Contable"
          hint="Excel con columnas: Fecha, Leyenda / Concepto, Debe, Haber"
          accept=".xlsx,.xls,.csv"
          file={mayorFile}
          onChange={f => { setMayorFile(f) }}
        />
        <FileField
          label="Extracto Bancario"
          hint="Excel con columnas: Fecha, Descripción, Débito, Crédito"
          accept=".xlsx,.xls,.csv"
          file={bancoFile}
          onChange={f => { setBancoFile(f) }}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderRadius: 8, background: '#f0f7ff', border: '1px solid #bfdbfe', marginBottom: 24, fontSize: 12, color: '#1d4ed8' }}>
          <span style={{ fontSize: 15, flexShrink: 0 }}>ℹ️</span>
          Las partidas pendientes de la última conciliación se incorporan automáticamente.
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onBack}
            style={{
              flex: '0 0 auto', padding: '14px 20px',
              background: '#f1f5f9', color: '#475569',
              border: '1.5px solid #cbd5e1', borderRadius: 9,
              fontSize: 15, fontWeight: 700, cursor: 'pointer',
            }}
          >
            ← Volver
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="btn-primary"
            style={{
              flex: 1, padding: '14px',
              background: canSubmit ? '#2563eb' : '#c7d5f0',
              color: '#fff', border: 'none', borderRadius: 9,
              fontSize: 15, fontWeight: 700,
              cursor: canSubmit ? 'pointer' : 'not-allowed',
            }}
          >
            {loading ? 'Procesando...' : 'Conciliar →'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: 16, padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, color: '#dc2626', fontSize: 13, whiteSpace: 'pre-wrap' }}>
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
