const ESTADO = {
  balanceada:      { bg: '#dcfce7', color: '#16a34a', label: 'Balanceada',       border: '#16a34a' },
  con_diferencias: { bg: '#fff7ed', color: '#ea580c', label: 'Con diferencias',  border: '#ea580c' },
  default:         { bg: '#f1f5f9', color: '#94a3b8', label: 'Sin conciliación', border: '#e2e8f0' },
}

function BancoCard({ banco, onSelect, onDelete, onGestionar }) {
  const ult = banco.ultima_conciliacion
  const st  = ESTADO[ult?.estado] ?? ESTADO.default

  return (
    <div className="banco-card" style={{
      background: '#fff',
      borderRadius: 12,
      boxShadow: '0 1px 4px rgba(13,27,75,0.07)',
      overflow: 'hidden',
      borderLeft: `4px solid ${st.border}`,
      display: 'flex',
      alignItems: 'center',
      gap: 0,
    }}>
      <div style={{ padding: '20px 20px', display: 'flex', alignItems: 'center', gap: 16, flex: 1, minWidth: 0 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 10,
          background: '#eef1f8',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, flexShrink: 0,
        }}>
          🏦
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: '#0d1b4b', marginBottom: 6 }}>
            {banco.nombre}
          </div>

          {ult ? (
            <div style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{
                  background: st.bg, color: st.color,
                  borderRadius: 20, padding: '3px 12px', fontSize: 12, fontWeight: 700,
                }}>
                  {st.label}
                </span>
                {ult.diferencia != null && (
                  <span style={{
                    fontWeight: 700, fontSize: 13,
                    color: Math.abs(ult.diferencia) < 0.02 ? '#16a34a' : '#ea580c',
                  }}>
                    Dif: ${ult.diferencia.toFixed(2)}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Procesada
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#0d1b4b', marginTop: 2 }}>
                    {ult.fecha_proceso}
                  </div>
                </div>
                {ult.fecha_datos && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Datos hasta
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#0d1b4b', marginTop: 2 }}>
                      {ult.fecha_datos}
                    </div>
                  </div>
                )}
                {ult.resumen && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Partidas pendientes
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#0d1b4b', marginTop: 2 }}>
                      {(ult.resumen.debitos_no_contab ?? 0) + (ult.resumen.haber_no_debitados ?? 0) +
                       (ult.resumen.no_acreditados ?? 0) + (ult.resumen.creditos_no_contab ?? 0)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <span style={{ color: '#94a3b8', fontSize: 12, marginTop: 4, display: 'block' }}>
              Sin conciliaciones aún
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 20px', flexShrink: 0 }}>
        {banco.ultima_conciliacion && (
          <a
            href={`/api/bancos/${banco.id}/ultima/excel`}
            download="conciliacion.xlsx"
            title="Descargar última conciliación"
            className="download-link"
            style={{
              background: '#f8fafc', color: '#2563eb',
              border: '1px solid #e2e8f0',
              borderRadius: 8, padding: '9px 14px', fontSize: 13,
              fontWeight: 600, textDecoration: 'none',
              display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            ⬇ Última
          </a>
        )}
        <button
          onClick={() => onGestionar(banco)}
          title="Ver y gestionar las partidas pendientes del mes anterior"
          className="btn-secondary"
          style={{
            background: '#f8fafc', color: '#475569',
            border: '1px solid #e2e8f0',
            borderRadius: 8, padding: '9px 14px', fontSize: 12, fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          Mes anterior
        </button>
        <button
          onClick={() => onSelect(banco)}
          className="btn-primary"
          style={{
            background: '#2563eb', color: '#fff', border: 'none',
            borderRadius: 8, padding: '9px 20px', fontSize: 13,
            fontWeight: 600,
          }}
        >
          Conciliar
        </button>
        <button
          onClick={() => onDelete(banco.id)}
          title="Eliminar banco"
          className="btn-danger"
          style={{
            background: '#fff0f0', color: '#dc2626',
            border: '1px solid #fecaca',
            borderRadius: 8, padding: '9px 12px', fontSize: 13,
          }}
        >
          ✕
        </button>
      </div>
    </div>
  )
}

export default function BancoList({ bancos, loading, onSelect, onDelete, onAddClick, onGestionar }) {
  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24,
      }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#0d1b4b' }}>Bancos</h1>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>
            {bancos.length === 0
              ? 'Agregá tu primer banco para empezar'
              : `${bancos.length} banco${bancos.length !== 1 ? 's' : ''} configurado${bancos.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <button
          onClick={onAddClick}
          className="btn-primary"
          style={{
            background: '#2563eb', color: '#fff', border: 'none',
            borderRadius: 9, padding: '11px 22px', fontSize: 14,
            fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          <span style={{ fontSize: 16 }}>+</span> Agregar banco
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}>Cargando...</div>
      ) : bancos.length === 0 ? (
        <div style={{
          background: '#fff', borderRadius: 12,
          boxShadow: '0 1px 4px rgba(13,27,75,0.07)',
          padding: '64px 24px', textAlign: 'center',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🏦</div>
          <p style={{ fontWeight: 700, fontSize: 16, color: '#0d1b4b', marginBottom: 8 }}>
            Todavía no hay bancos configurados
          </p>
          <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 24 }}>
            Agregá un banco para empezar a hacer conciliaciones.
          </p>
          <button
            onClick={onAddClick}
            style={{
              background: '#2563eb', color: '#fff', border: 'none',
              borderRadius: 9, padding: '12px 28px', fontSize: 14, fontWeight: 700,
            }}
          >
            + Agregar primer banco
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {bancos.map(b => (
            <BancoCard key={b.id} banco={b} onSelect={onSelect} onDelete={onDelete} onGestionar={onGestionar} />
          ))}
        </div>
      )}
    </div>
  )
}
