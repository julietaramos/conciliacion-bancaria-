import { useEffect, useState, useCallback } from 'react'
import BancoList from './BancoList'
import AddBancoModal from './AddBancoModal'
import FileUploader from './FileUploader'
import ReconciliationReview from './ReconciliationReview'
import GestionarAnteriorModal from './GestionarAnteriorModal'

const MAX_BANCOS = parseInt(import.meta.env.VITE_MAX_BANCOS || '0')

export default function BancosPage({ initialBanco, onClearInitial }) {
  const [bancos, setBancos]               = useState([])
  const [loading, setLoading]             = useState(true)
  const [selectedBanco, setSelectedBanco] = useState(initialBanco ?? null)
  const [previewData,   setPreviewData]   = useState(null)      // null | data
  const [showAddModal,  setShowAddModal]  = useState(false)
  const [gestionarBanco, setGestionarBanco] = useState(null)    // banco | null

  useEffect(() => {
    if (initialBanco) { setSelectedBanco(initialBanco); onClearInitial?.() }
  }, [initialBanco])

  const fetchBancos = useCallback(async () => {
    try {
      const res = await fetch('/api/bancos')
      if (res.ok) setBancos(await res.json())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchBancos() }, [fetchBancos])

  async function handleAddBanco(nombre) {
    const res = await fetch('/api/bancos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'No se pudo agregar el banco.')
    }
    setShowAddModal(false)
    await fetchBancos()
  }

  async function handleDeleteBanco(id) {
    if (!window.confirm('¿Eliminás este banco y todas sus conciliaciones?')) return
    await fetch(`/api/bancos/${id}`, { method: 'DELETE' })
    if (selectedBanco?.id === id) { setSelectedBanco(null); setPreviewData(null) }
    await fetchBancos()
  }

  function handleVolver() {
    if (previewData) { setPreviewData(null) }
    else             { setSelectedBanco(null) }
  }

  function handleSuccess() {
    fetchBancos()
    setPreviewData(null)
    setSelectedBanco(null)
  }

  // Determine view
  const view = !selectedBanco ? 'list'
             : !previewData   ? 'upload'
             :                  'review'

  const STEP_LABELS = { list: null, upload: 'Nueva conciliación', review: 'Revisión' }

  return (
    <>
      {/* Breadcrumb — only when inside a banco */}
      {view !== 'list' && (
        <nav style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 24, fontSize: 13 }}>
          <button
            onClick={() => { setSelectedBanco(null); setPreviewData(null) }}
            style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: 600, padding: 0, cursor: 'pointer' }}
          >
            Bancos
          </button>
          <span style={{ color: '#cbd5e1' }}>›</span>
          {view === 'review' ? (
            <>
              <button
                onClick={() => setPreviewData(null)}
                style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: 600, padding: 0, cursor: 'pointer' }}
              >
                {selectedBanco.nombre}
              </button>
              <span style={{ color: '#cbd5e1' }}>›</span>
              <span style={{ color: '#64748b' }}>Revisión</span>
            </>
          ) : (
            <>
              <span style={{ color: '#64748b' }}>{selectedBanco.nombre}</span>
            </>
          )}
        </nav>
      )}

      {view === 'list' && (
        <BancoList
          bancos={bancos}
          loading={loading}
          onSelect={setSelectedBanco}
          onDelete={handleDeleteBanco}
          onAddClick={() => setShowAddModal(true)}
          onGestionar={setGestionarBanco}
          maxBancos={MAX_BANCOS}
        />
      )}

      {view === 'upload' && (
        <FileUploader
          banco={selectedBanco}
          onBack={handleVolver}
          onPreview={setPreviewData}
        />
      )}

      {view === 'review' && (
        <ReconciliationReview
          banco={selectedBanco}
          previewData={previewData}
          onBack={handleVolver}
          onSuccess={handleSuccess}
        />
      )}

      {showAddModal && (
        <AddBancoModal
          onConfirm={handleAddBanco}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {gestionarBanco && (
        <GestionarAnteriorModal
          banco={gestionarBanco}
          onClose={() => setGestionarBanco(null)}
          onDone={fetchBancos}
        />
      )}
    </>
  )
}
