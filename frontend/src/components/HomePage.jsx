function StatCard({ value, label, sub, accent }) {
  return (
    <div className="stat-card" style={{
      background: '#fff',
      borderRadius: 12,
      padding: '24px 28px',
      boxShadow: '0 1px 4px rgba(13,27,75,0.08)',
      borderTop: `3px solid ${accent}`,
      flex: 1,
      minWidth: 160,
    }}>
      <div style={{ fontSize: 32, fontWeight: 800, color: '#0d1b4b', lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#64748b', marginTop: 6 }}>
        {label}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{sub}</div>
      )}
    </div>
  )
}

function RecentBancoRow({ banco, onConciliar }) {
  const ult = banco.ultima_conciliacion
  const estado = ult?.estado
  const badgeStyle = estado === 'balanceada'
    ? { bg: '#dcfce7', color: '#16a34a' }
    : estado === 'con_diferencias'
    ? { bg: '#fff7ed', color: '#ea580c' }
    : { bg: '#f1f5f9', color: '#94a3b8' }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 16,
      padding: '14px 20px',
      borderBottom: '1px solid #f1f5f9',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 8,
        background: '#eef1f8',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18, flexShrink: 0,
      }}>
        🏦
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: '#0d1b4b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {banco.nombre}
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
          {ult ? `Última: ${ult.fecha_proceso}` : 'Sin conciliaciones'}
        </div>
      </div>
      <span style={{
        background: badgeStyle.bg, color: badgeStyle.color,
        borderRadius: 20, padding: '3px 10px', fontSize: 11, fontWeight: 700,
        flexShrink: 0,
      }}>
        {estado === 'balanceada' ? 'Balanceada' : estado === 'con_diferencias' ? 'Con diferencias' : 'Pendiente'}
      </span>
      <button
        onClick={() => onConciliar(banco)}
        style={{
          background: '#2563eb', color: '#fff', border: 'none',
          borderRadius: 7, padding: '7px 16px', fontSize: 12,
          fontWeight: 600, flexShrink: 0,
        }}
      >
        Conciliar
      </button>
    </div>
  )
}

export default function HomePage({ bancos, onConciliar, onNavigate }) {
  const totalBancos    = bancos.length
  const balanceados    = bancos.filter(b => b.ultima_conciliacion?.estado === 'balanceada').length
  const conDiferencias = bancos.filter(b => b.ultima_conciliacion?.estado === 'con_diferencias').length

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#0d1b4b', lineHeight: 1.2 }}>
          Bienvenido
        </h1>
        <p style={{ color: '#64748b', marginTop: 6, fontSize: 15 }}>
          Gestión de conciliaciones bancarias · Resumen de actividad
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 36, flexWrap: 'wrap' }}>
        <StatCard value={totalBancos}    label="Bancos configurados" accent="#2563eb" />
        <StatCard value={balanceados}    label="Balanceados"         accent="#16a34a" />
        <StatCard value={conDiferencias} label="Con diferencias"     accent="#ea580c" />
      </div>

      {/* Recent */}
      <div style={{
        background: '#fff',
        borderRadius: 12,
        boxShadow: '0 1px 4px rgba(13,27,75,0.08)',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '18px 20px',
          borderBottom: '1px solid #f1f5f9',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: '#0d1b4b' }}>Bancos</div>
            <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>Estado de última conciliación</div>
          </div>
          <button
            onClick={() => onNavigate('bancos')}
            style={{
              background: 'none', border: '1px solid #e2e8f0',
              borderRadius: 7, padding: '6px 14px', fontSize: 12,
              fontWeight: 600, color: '#2563eb',
            }}
          >
            Ver todos →
          </button>
        </div>

        {bancos.length === 0 ? (
          <div style={{ padding: '48px 24px', textAlign: 'center', color: '#94a3b8' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>🏦</div>
            <p style={{ fontWeight: 600, color: '#64748b' }}>No hay bancos configurados</p>
            <p style={{ fontSize: 13, marginTop: 4 }}>
              Ir a{' '}
              <button
                onClick={() => onNavigate('bancos')}
                style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: 600, fontSize: 13, textDecoration: 'underline' }}
              >
                Bancos
              </button>
              {' '}para agregar el primero.
            </p>
          </div>
        ) : (
          bancos.map(b => (
            <RecentBancoRow key={b.id} banco={b} onConciliar={onConciliar} />
          ))
        )}
      </div>
    </div>
  )
}
