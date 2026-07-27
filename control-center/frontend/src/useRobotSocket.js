import { useCallback, useEffect, useRef, useState } from 'react'
import { DEFAULT_STATE } from './robotModel.js'

const DEFAULT_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname || '127.0.0.1'}:8765`

export function useRobotSocket(url = import.meta.env.VITE_ROBOT_WS_URL || DEFAULT_URL) {
  const socketRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const closedByComponentRef = useRef(false)
  const attemptRef = useRef(0)
  const [socketState, setSocketState] = useState('connecting')
  const [robot, setRobot] = useState(DEFAULT_STATE)
  const [lastMessageAt, setLastMessageAt] = useState(null)

  useEffect(() => {
    closedByComponentRef.current = false

    function connect() {
      setSocketState(attemptRef.current ? 'reconnecting' : 'connecting')
      const socket = new WebSocket(url)
      socketRef.current = socket

      socket.onopen = () => {
        attemptRef.current = 0
        setSocketState('connected')
      }
      socket.onmessage = (event) => {
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
      socket.onerror = () => setSocketState('error')
      socket.onclose = () => {
        if (closedByComponentRef.current) return
        attemptRef.current += 1
        setSocketState('reconnecting')
        const delay = Math.min(5000, 600 * 2 ** Math.min(attemptRef.current, 3))
        reconnectTimerRef.current = window.setTimeout(connect, delay)
      }
    }

    connect()
    return () => {
      closedByComponentRef.current = true
      window.clearTimeout(reconnectTimerRef.current)
      socketRef.current?.close()
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
