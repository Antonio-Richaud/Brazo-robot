import { useCallback, useEffect, useRef, useState } from 'react'
import { DEFAULT_STATE } from './robotModel.js'

const DEFAULT_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname || '127.0.0.1'}:8765`

export function useRobotSocket(url = import.meta.env.VITE_ROBOT_WS_URL || DEFAULT_URL) {
  const socketRef = useRef(null)
  const [socketState, setSocketState] = useState('connecting')
  const [robot, setRobot] = useState(DEFAULT_STATE)
  const [lastMessageAt, setLastMessageAt] = useState(null)

  useEffect(() => {
    // Estado propio del efecto: un socket antiguo nunca debe reactivar
    // reintentos despues de cambiar la URL o desmontar el componente.
    let disposed = false
    let attempts = 0
    let connectTimer = null
    let retryTimer = null
    let activeSocket = null

    function connect() {
      if (disposed) return

      setSocketState(attempts ? 'reconnecting' : 'connecting')
      const socket = new WebSocket(url)
      activeSocket = socket
      socketRef.current = socket

      socket.onopen = () => {
        // El navegador no permite cancelar limpiamente un handshake CONNECTING.
        // Si el componente se desmonto, cerrar SOLO despues de OPEN.
        if (disposed) {
          socket.close()
          return
        }
        attempts = 0
        setSocketState('connected')
      }

      socket.onmessage = (event) => {
        if (disposed) return
        try {
          const data = JSON.parse(event.data)
          const nextState = data?.type === 'state' ? data.payload : data
          if (nextState?.servos) {
            setRobot(nextState)
            setLastMessageAt(Date.now())
          }
        } catch (error) {
          console.warn('Estado WebSocket invalido', error)
        }
      }

      socket.onerror = () => {
        if (!disposed) setSocketState('error')
      }

      socket.onclose = () => {
        if (socketRef.current === socket) socketRef.current = null
        if (disposed) return

        attempts += 1
        setSocketState('reconnecting')
        const delay = Math.min(5000, 600 * 2 ** Math.min(attempts, 3))
        retryTimer = window.setTimeout(connect, delay)
      }
    }

    // React StrictMode monta/desmonta efectos inmediatamente en desarrollo.
    // Diferir el handshake evita abrir y cerrar un WebSocket CONNECTING
    // durante ese primer ciclo, sin deshabilitar StrictMode.
    connectTimer = window.setTimeout(connect, 0)

    return () => {
      disposed = true
      window.clearTimeout(connectTimer)
      window.clearTimeout(retryTimer)

      if (socketRef.current === activeSocket) socketRef.current = null
      // En CONNECTING, onopen detecta disposed y lo cierra al establecerse.
      // Invocar close() aqui emitiria "closed before connection is established".
      if (activeSocket?.readyState === WebSocket.OPEN) activeSocket.close()
    }
  }, [url])

  const send = useCallback((payload) => {
    const socket = socketRef.current
    if (socket?.readyState !== WebSocket.OPEN) return false
    socket.send(JSON.stringify(payload))
    return true
  }, [])

  return { robot, socketState, lastMessageAt, send }
}
