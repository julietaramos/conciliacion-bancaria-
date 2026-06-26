import { useState, useRef } from 'react'

function ActionCard({ icon, title, description, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%', textAlign: 'left', background: '#fff',
        border: '2px solid #e2e8f0', borderRadius: 10,
        padding: '16px 18px', cursor: 'pointer', marginBottom: 10,
        display: 'flex', alignItems: 'flex-start', gap: 14,
        transition: 'border-color 0.15s, background 0.15s',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = '#2563eb'; e.currentTarget.style.background = '#f8fafc' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.background = '#fff' }}
    >
      <span style={{ fontSize: 22, flexShrink: 0, lineHeight: 1 }}>{icon}</span>
      <div>
        <div style={{ fontWeight: 700, fontSize: 14, color: '#0d1b4b', marginBottom: 3 }}>{title}</div>
        <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.5 }}>{description}</div>
      </div>
      <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: 16, alignSelf: 'center', flexShrink: 0 }}>›</span>
    </button>
  )
}

export default function GestionarAnteriorModal({ banco, onClose, onDone }) {
  const [view,    setView]    = useState('menu')   // 'menu' | 'borrar' | 'reemplazar'
  const [archivo, setArchivo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [ok,      setOk]      = useState(false)
  const inputRef = useRef()

  const tieneAnterior = !!banco.ultima_conciliacion

  async function handleBorrar() {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`/api/bancos/${banco.id}/anterior`, { method: 'DELETE' })
      if (!res.ok && res.status !== 204) throw new Error('No se pudo eliminar.')
      setOk(true)
      setTimeout(() => { onDone?.(); onClose() }, 1400)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSubir() {
    if (!archivo) return
    setLoading(true); setError(null)
    const fd = new FormData()
    fd.append('archivo', archivo)
    try {
      const res = await fetch(`/api/bancos/${banco.id}/anterior`, { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Error ${res.status}`)
      }
      setOk(true)
      setTimeout(() => { onDone?.(); onClose() }, 1400)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function goBack() { setView('menu'); setError(null); setArchivo(null) }

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(13,27,75,0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 200, backdropFilter: 'blur(2px)',
      }}
    >
      <div style={{
        background: '#fff', borderRadius: 14, width: '100%', maxWidth: 460,
        boxShadow: '0 20px 60px rgba(13,27,75,0.2)', overflow: 'hidden',
      }}>

        {/* Header */}
        <div style={{ padding: '22px 28px 16px', borderBottom: '1px solid #f1f5f9' }}>
          {view !== 'menu' && !ok && (
            <button
              onClick={goBack}
              style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: 13, fontWeight: 600, padding: 0, marginBottom: 10, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
            >
              ← Volver
            </button>
          )}
          <h2 style={{ fontSize: 17, fontWeight: 800, color: '#0d1b4b', margin: 0 }}>
            {view === 'menu'       ? 'Partidas del mes anterior'
             : view === 'borrar'   ? 'Borrar partidas guardadas'
             :                       'Reemplazar con otro Excel'}
          </h2>
          <p style={{ fontSize: 12, color: '#64748b', marginTop: 3 }}>{banco.nombre}</p>
        </div>

        {/* Content */}
        <div style={{ padding: '20px 28px 24px' }}>

          {ok ? (
            <div style={{ padding: '16px', background: '#dcfce7', borderRadius: 8, color: '#15803d', fontWeight: 600, textAlign: 'center', fontSize: 14 }}>
              ✓ Cambio aplicado correctamente.
            </div>

          ) : view === 'menu' ? (
            <>
              <div style={{
                display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '12px 14px', background: '#f0f7ff', border: '1px solid #bfdbfe',
                borderRadius: 8, marginBottom: 18, fontSize: 12, color: '#1e40af', lineHeight: 1.5,
              }}>
                <span style={{ fontSize: 15, flexShrink: 0 }}>ℹ️</span>
                <span>
                  Cuando hacés una conciliación, los ítems que quedan sin cruzar se guardan como <strong>partidas pendientes</strong>. La próxima vez que concilies este banco, esas partidas se incorporan automáticamente.
                  {tieneAnterior
                    ? ' Este banco tiene partidas guardadas del mes anterior.'
                    : ' Este banco no tiene partidas guardadas actualmente.'}
                </span>
              </div>

              <ActionCard
                icon="🗑️"
                title="Borrar partidas guardadas"
                description={tieneAnterior
                  ? 'Elimina las partidas pendientes guardadas. La próxima conciliación comenzará desde cero, sin carry-over.'
                  : 'No hay partidas guardadas para este banco.'}
                onClick={() => setView('borrar')}
              />

              <ActionCard
                icon="📤"
                title="Reemplazar con otro Excel"
                description="Subí un Excel generado por esta app de un mes anterior para usarlo como base. Sus partidas pendientes reemplazarán las actuales."
                onClick={() => setView('reemplazar')}
              />

              <button
                onClick={onClose}
                style={{
                  width: '100%', marginTop: 4, padding: '10px',
                  background: '#f1f5f9', color: '#64748b',
                  border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}
              >
                Cerrar
              </button>
            </>

          ) : view === 'borrar' ? (
            <>
              <div style={{
                padding: '12px 14px', background: '#fef2f2', border: '1px solid #fecaca',
                borderRadius: 8, fontSize: 13, color: '#7f1d1d', marginBottom: 20, lineHeight: 1.5,
              }}>
                {tieneAnterior
                  ? 'Esto eliminará las partidas pendientes guardadas para este banco. La próxima conciliación no tendrá datos del mes anterior.'
                  : 'Este banco no tiene partidas guardadas actualmente. No hay nada que eliminar.'}
              </div>
              {error && <p style={{ color: '#dc2626', fontSize: 13, marginBottom: 12 }}>{error}</p>}
              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button onClick={goBack} style={{ background: '#f1f5f9', color: '#64748b', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                  Cancelar
                </button>
                <button
                  onClick={handleBorrar}
                  disabled={loading || !tieneAnterior}
                  style={{
                    background: loading || !tieneAnterior ? '#fca5a5' : '#dc2626',
                    color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px',
                    fontSize: 13, fontWeight: 700,
                    cursor: loading || !tieneAnterior ? 'not-allowed' : 'pointer',
                  }}
                >
                  {loading ? 'Borrando...' : 'Confirmar y borrar'}
                </button>
              </div>
            </>

          ) : (
            <>
              <p style={{ fontSize: 13, color: '#64748b', marginBottom: 14, lineHeight: 1.5 }}>
                Subí un <strong>.xlsx</strong> generado por esta app de un mes anterior. Sus partidas pendientes reemplazarán la base actual de <strong>{banco.nombre}</strong>.
              </p>
              <div
                onClick={() => inputRef.current.click()}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '12px 14px', borderRadius: 8, cursor: 'pointer', marginBottom: 20,
                  border: archivo ? '2px solid #2563eb' : '2px dashed #c7d5f0',
                  background: archivo ? '#f0f7ff' : '#f5f7ff',
                }}
              >
                <span style={{ fontSize: 20 }}>{archivo ? '📄' : '📂'}</span>
                <span style={{ fontSize: 13, flex: 1, color: archivo ? '#1d4ed8' : '#94a3b8', fontWeight: archivo ? 600 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {archivo ? archivo.name : 'Hacer clic para seleccionar .xlsx'}
                </span>
                <input ref={inputRef} type="file" accept=".xlsx" style={{ display: 'none' }} onChange={e => setArchivo(e.target.files[0] || null)} />
              </div>
              {error && <p style={{ color: '#dc2626', fontSize: 13, marginBottom: 12 }}>{error}</p>}
              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button onClick={goBack} style={{ background: '#f1f5f9', color: '#64748b', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                  Cancelar
                </button>
                <button
                  onClick={handleSubir}
                  disabled={!archivo || loading}
                  className="btn-primary"
                  style={{
                    background: archivo && !loading ? '#2563eb' : '#c7d5f0',
                    color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px',
                    fontSize: 13, fontWeight: 700,
                    cursor: archivo && !loading ? 'pointer' : 'not-allowed',
                  }}
                >
                  {loading ? 'Subiendo...' : 'Aplicar'}
                </button>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  )
}
