import { useState } from 'react'

const ICON_SIZE = 18
const TOGGLE_WIDTH = 40

const toggleStyle = {
  position: 'absolute', top: 0, right: 0, bottom: 0,
  width: TOGGLE_WIDTH,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'none', border: 'none', padding: 0,
  color: '#64748b', cursor: 'pointer',
}

function EyeIcon({ crossed }) {
  return (
    <svg width={ICON_SIZE} height={ICON_SIZE} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
      {crossed && <line x1="3" y1="3" x2="21" y2="21" />}
    </svg>
  )
}

export default function PasswordInput({ style, wrapperStyle, ...inputProps }) {
  const [visible, setVisible] = useState(false)

  return (
    <div style={{ position: 'relative', ...wrapperStyle }}>
      <input
        {...inputProps}
        type={visible ? 'text' : 'password'}
        style={{ ...style, paddingRight: TOGGLE_WIDTH }}
      />
      <button
        type="button"
        onClick={() => setVisible(v => !v)}
        aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        title={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        style={toggleStyle}
      >
        <EyeIcon crossed={visible} />
      </button>
    </div>
  )
}
