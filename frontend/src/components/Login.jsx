import { useState } from 'react'

export default function Login({ onSuccess }) {
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!password) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (!res.ok) {
        setError('Contraseña incorrecta.')
        setLoading(false)
        return
      }
      onSuccess()
    } catch {
      setError('No se pudo conectar con el servidor.')
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#eef1f8',
    }}>
      <div style={{
        background: '#fff', borderRadius: 14, padding: '36px 40px',
        width: '100%', maxWidth: 380,
        boxShadow: '0 20px 60px rgba(13,27,75,0.15)',
      }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, color: '#0d1b4b', marginBottom: 6 }}>
          Conciliación Bancaria
        </h1>
        <p style={{ fontSize: 13, color: '#64748b', marginBottom: 24 }}>
          Ingresá la contraseña para continuar.
        </p>

        <form onSubmit={handleSubmit}>
          <input
            autoFocus
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Contraseña"
            style={{
              display: 'block', width: '100%',
              padding: '11px 14px', borderRadius: 8,
              border: '2px solid #e2e8f0',
              fontSize: 14, outline: 'none', marginBottom: 16,
              transition: 'border-color 0.15s',
            }}
            onFocus={e => e.target.style.borderColor = '#2563eb'}
            onBlur={e => e.target.style.borderColor = '#e2e8f0'}
          />

          {error && (
            <p style={{ color: '#dc2626', fontSize: 13, marginBottom: 14 }}>{error}</p>
          )}

          <button
            type="submit"
            disabled={!password || loading}
            style={{
              width: '100%',
              background: password && !loading ? '#2563eb' : '#c7d5f0',
              color: '#fff', border: 'none',
              borderRadius: 8, padding: '11px 20px', fontSize: 14,
              fontWeight: 700,
              cursor: password && !loading ? 'pointer' : 'not-allowed',
            }}
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
      </div>
    </div>
  )
}
