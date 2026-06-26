import { useState } from 'react'

export default function AddBancoModal({ onConfirm, onClose }) {
  const [nombre, setNombre]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!nombre.trim()) return
    setLoading(true)
    setError(null)
    try {
      await onConfirm(nombre.trim())
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(13,27,75,0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 200, backdropFilter: 'blur(2px)',
      }}
    >
      <div style={{
        background: '#fff', borderRadius: 14, padding: '32px 36px',
        width: '100%', maxWidth: 440,
        boxShadow: '0 20px 60px rgba(13,27,75,0.2)',
      }}>
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: '#0d1b4b' }}>Agregar banco</h2>
          <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
            Ingresá un nombre descriptivo para identificar la cuenta.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label style={{
            display: 'block', fontWeight: 600, fontSize: 13,
            color: '#0d1b4b', marginBottom: 6,
          }}>
            Nombre del banco
          </label>
          <input
            autoFocus
            type="text"
            value={nombre}
            onChange={e => setNombre(e.target.value)}
            placeholder="Ej: Banco Provincia — Cta. Cte."
            style={{
              display: 'block', width: '100%',
              padding: '11px 14px', borderRadius: 8,
              border: '2px solid #e2e8f0',
              fontSize: 14, outline: 'none', marginBottom: 20,
              transition: 'border-color 0.15s',
            }}
            onFocus={e => e.target.style.borderColor = '#2563eb'}
            onBlur={e => e.target.style.borderColor = '#e2e8f0'}
          />

          {error && (
            <p style={{ color: '#dc2626', fontSize: 13, marginBottom: 14 }}>{error}</p>
          )}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: '#f1f5f9', color: '#64748b', border: 'none',
                borderRadius: 8, padding: '10px 20px', fontSize: 14, fontWeight: 600,
              }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!nombre.trim() || loading}
              style={{
                background: nombre.trim() && !loading ? '#2563eb' : '#c7d5f0',
                color: '#fff', border: 'none',
                borderRadius: 8, padding: '10px 24px', fontSize: 14,
                fontWeight: 700,
                cursor: nombre.trim() && !loading ? 'pointer' : 'not-allowed',
              }}
            >
              {loading ? 'Guardando...' : 'Agregar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
