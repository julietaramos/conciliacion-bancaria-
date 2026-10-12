import { useRef, useState } from 'react'
import { apiFetch } from './api'

export function formatoElegido(inspeccion) {
  return { fila_encabezado: inspeccion.fila_encabezado, columnas: inspeccion.columnas }
}

export default function useInspeccionArchivo(bancoId, tipo) {
  const [archivo, setArchivo]       = useState(null)
  const [inspeccion, setInspeccion] = useState(null)
  const [cargando, setCargando]     = useState(false)
  const [error, setError]           = useState(null)
  const ultimoPedido = useRef(0)

  const inspeccionar = async (file, formato) => {
    const pedido = ++ultimoPedido.current
    setCargando(true); setError(null)

    const fd = new FormData()
    fd.append('banco_id', bancoId)
    fd.append('tipo', tipo)
    fd.append('archivo', file)
    if (formato) fd.append('formato', JSON.stringify(formato))

    try {
      const res = await apiFetch('/api/archivos/inspeccionar', { method: 'POST', body: fd })
      const data = await res.json().catch(() => ({}))
      if (pedido !== ultimoPedido.current) return
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`)
      setInspeccion(data)
    } catch (err) {
      if (pedido !== ultimoPedido.current) return
      setInspeccion(null)
      setError(err.message)
    } finally {
      if (pedido === ultimoPedido.current) setCargando(false)
    }
  }

  const seleccionar = file => {
    setArchivo(file)
    setInspeccion(null)
    if (file) inspeccionar(file)
  }

  const cambiarColumna = (clave, columna) => {
    const columnas = { ...inspeccion.columnas }
    if (columna) columnas[clave] = columna
    else delete columnas[clave]
    inspeccionar(archivo, { fila_encabezado: inspeccion.fila_encabezado, columnas })
  }

  const cambiarFilaEncabezado = fila => inspeccionar(archivo, { fila_encabezado: fila })

  const listo = Boolean(inspeccion) && !cargando && inspeccion.errores.length === 0

  return { archivo, inspeccion, cargando, error, listo, seleccionar, cambiarColumna, cambiarFilaEncabezado }
}
