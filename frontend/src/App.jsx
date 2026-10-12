import { useEffect, useState, useCallback } from 'react'
import Layout from './components/Layout'
import HomePage from './components/HomePage'
import BancosPage from './components/BancosPage'
import Login from './components/Login'
import { apiFetch, UNAUTHORIZED_EVENT } from './api'

export default function App() {
  const [authState, setAuthState] = useState('checking') // checking | authenticated | unauthenticated
  const [usuario, setUsuario] = useState(null)
  const [page, setPage]       = useState('home')
  const [bancos, setBancos]   = useState([])
  const [pendingBanco, setPendingBanco] = useState(null)

  const fetchBancos = useCallback(async () => {
    try {
      const res = await apiFetch('/api/bancos')
      if (res.ok) setBancos(await res.json())
    } catch {}
  }, [])

  const checkSession = useCallback(() => {
    fetch('/api/session')
      .then(res => res.json())
      .then(data => {
        setUsuario(data.usuario)
        setAuthState(data.authenticated ? 'authenticated' : 'unauthenticated')
      })
      .catch(() => setAuthState('unauthenticated'))
  }, [])

  useEffect(checkSession, [checkSession])

  useEffect(() => {
    const handleUnauthorized = () => setAuthState('unauthenticated')
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
  }, [])

  useEffect(() => {
    if (authState === 'authenticated') fetchBancos()
  }, [authState, fetchBancos])

  function handleConciliarFromHome(banco) {
    setPendingBanco(banco)
    setPage('bancos')
  }

  async function handleLogout() {
    await fetch('/api/logout', { method: 'POST' }).catch(() => {})
    setBancos([])
    setPage('home')
    setUsuario(null)
    setAuthState('unauthenticated')
  }

  function handleNavigate(newPage) {
    if (newPage !== 'bancos') setPendingBanco(null)
    setPage(newPage)
    fetchBancos()
  }

  if (authState === 'checking') return null
  if (authState === 'unauthenticated') {
    return <Login onSuccess={checkSession} />
  }

  return (
    <Layout page={page} onNavigate={handleNavigate} usuario={usuario} onLogout={handleLogout}>
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
