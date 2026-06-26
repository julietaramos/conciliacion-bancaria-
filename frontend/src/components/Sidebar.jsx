const NAV = [
  { id: 'home',   icon: '📊', label: 'Inicio' },
  { id: 'bancos', icon: '🏦', label: 'Bancos' },
]

export default function Sidebar({ page, onNavigate }) {
  return (
    <aside style={{
      width: 240,
      minHeight: '100vh',
      background: '#0d1b4b',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ padding: '28px 24px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 10,
            background: '#2563eb',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, flexShrink: 0,
          }}>
            🏦
          </div>
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: 14, lineHeight: 1.2 }}>
              Conciliaciones
            </div>
            <div style={{ color: '#7b9cce', fontSize: 11, marginTop: 1 }}>
              Bancarias
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.08)', margin: '0 16px' }} />

      {/* Nav */}
      <nav style={{ padding: '16px 12px', flex: 1 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#4a6fa5', letterSpacing: '0.08em', padding: '0 12px', marginBottom: 8 }}>
          MENÚ
        </div>
        {NAV.map(item => {
          const active = page === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={active ? '' : 'nav-item'}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                width: '100%',
                padding: '10px 12px',
                borderRadius: 8,
                border: 'none',
                background: active ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: active ? '#fff' : '#94b0d6',
                fontSize: 14,
                fontWeight: active ? 600 : 400,
                textAlign: 'left',
                transition: 'background 0.15s, color 0.15s',
                marginBottom: 2,
                borderLeft: active ? '3px solid #2563eb' : '3px solid transparent',
              }}
            >
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ fontSize: 11, color: '#4a6fa5' }}>v1.0 · Uso interno</div>
      </div>
    </aside>
  )
}
