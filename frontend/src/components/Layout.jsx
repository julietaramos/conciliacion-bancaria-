import Sidebar from './Sidebar'

export default function Layout({ page, onNavigate, children }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar page={page} onNavigate={onNavigate} />
      <main style={{
        flex: 1,
        padding: '40px 48px',
        overflowY: 'auto',
        minWidth: 0,
      }}>
        {children}
      </main>
    </div>
  )
}
