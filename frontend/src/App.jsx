import { useEffect, useState, useCallback } from 'react'
import Layout from './components/Layout'
import HomePage from './components/HomePage'
import BancosPage from './components/BancosPage'

export default function App() {
  const [page, setPage]       = useState('home')
  const [bancos, setBancos]   = useState([])
  const [pendingBanco, setPendingBanco] = useState(null)

  const fetchBancos = useCallback(async () => {
    try {
      const res = await fetch('/api/bancos')
      if (res.ok) setBancos(await res.json())
    } catch {}
  }, [])

  useEffect(() => { fetchBancos() }, [fetchBancos])

  function handleConciliarFromHome(banco) {
    setPendingBanco(banco)
    setPage('bancos')
  }

  function handleNavigate(newPage) {
    if (newPage !== 'bancos') setPendingBanco(null)
    setPage(newPage)
    fetchBancos()
  }

  return (
    <Layout page={page} onNavigate={handleNavigate}>
      {page === 'home' && (
        <HomePage
          bancos={bancos}
          onConciliar={handleConciliarFromHome}
          onNavigate={handleNavigate}
        />
      )}
      {page === 'bancos' && (
        <BancosPage
          initialBanco={pendingBanco}
          onClearInitial={() => setPendingBanco(null)}
        />
      )}
    </Layout>
  )
}
