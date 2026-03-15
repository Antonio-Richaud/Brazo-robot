import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'

const DEFAULT_STATE = {
  connected: false,
  port: null,
  mode: 'manual',
  joystick_connected: false,
  servos: {
    base: { id: 1, current: 90, target: 90, min: 10, max: 170, pca_channel: 0 },
    hombro: { id: 2, current: 50, target: 50, min: 15, max: 165, pca_channel: 1 },
    codo: { id: 3, current: 165, target: 165, min: 15, max: 165, pca_channel: 2 },
    muneca1: { id: 4, current: 10, target: 10, min: 10, max: 170, pca_channel: 3 },
    muneca2: { id: 5, current: 170, target: 170, min: 10, max: 170, pca_channel: 4 },
    garra: { id: 6, current: 40, target: 40, min: 20, max: 140, pca_channel: 5 },
  },
  joystick: {
    axis0: 0,
    axis1: 0,
    hat: [0, 0],
    buttons: [0, 0, 0, 0, 0, 0, 0, 0],
  },
  logs: [],
}

const SERVO_ORDER = ['base', 'hombro', 'codo', 'muneca1', 'muneca2', 'garra']
const SERVO_LABELS = {
  base: 'Base',
  hombro: 'Hombro',
  codo: 'Codo',
  muneca1: 'Muñeca 1',
  muneca2: 'Muñeca 2',
  garra: 'Garra',
}

function degToRad(deg) {
  return (deg * Math.PI) / 180
}

function servoCurrent(servos, name, fallback) {
  return servos?.[name]?.current ?? fallback
}

function pretty(n) {
  return typeof n === 'number' ? n.toFixed(2) : '0.00'
}

function Joint({ size = 0.18, color = '#67e8f9' }) {
  return (
    <mesh>
      <sphereGeometry args={[size, 16, 16]} />
      <meshBasicMaterial wireframe color={color} />
    </mesh>
  )
}

function Segment({ length, thickness = 0.18, color = '#93c5fd' }) {
  return (
    <mesh position={[length / 2, 0, 0]}>
      <boxGeometry args={[length, thickness, thickness]} />
      <meshBasicMaterial wireframe color={color} />
    </mesh>
  )
}

function Gripper({ open = 0.09 }) {
  return (
    <group>
      {/* cuerpo central */}
      <mesh position={[0.11, 0, 0]}>
        <boxGeometry args={[0.22, 0.12, 0.12]} />
        <meshBasicMaterial wireframe color="#fca5a5" />
      </mesh>

      {/* marcador asimétrico para que se note el roll de muñeca 2 */}
      <mesh position={[0.06, 0, 0.10]}>
        <boxGeometry args={[0.10, 0.05, 0.05]} />
        <meshBasicMaterial wireframe color="#fb7185" />
      </mesh>

      {/* dedo superior */}
      <mesh position={[0.26, open, 0]} rotation={[0, 0, degToRad(-16)]}>
        <boxGeometry args={[0.10, 0.24, 0.08]} />
        <meshBasicMaterial wireframe color="#fca5a5" />
      </mesh>

      {/* dedo inferior */}
      <mesh position={[0.26, -open, 0]} rotation={[0, 0, degToRad(16)]}>
        <boxGeometry args={[0.10, 0.24, 0.08]} />
        <meshBasicMaterial wireframe color="#fca5a5" />
      </mesh>
    </group>
  )
}

function RobotArm({ servos }) {
  const home = {
    base: 90,
    hombro: 50,
    codo: 165,
    muneca1: 10,
    muneca2: 170,
    garra: 40,
  }

  const baseDeg = servoCurrent(servos, 'base', home.base)
  const hombroDeg = servoCurrent(servos, 'hombro', home.hombro)
  const codoDeg = servoCurrent(servos, 'codo', home.codo)
  const muneca1Deg = servoCurrent(servos, 'muneca1', home.muneca1)
  const muneca2Deg = servoCurrent(servos, 'muneca2', home.muneca2)
  const garraRaw = servoCurrent(servos, 'garra', home.garra)

  // Longitudes visuales
  const upperArmLen = 2.35   // brazo un poco más corto
  const foreArmLen = 1.65    // antebrazo como ya te gustó
  const wristLen = 0.06

  // Base y brazo principal
  const base = degToRad(baseDeg - home.base)
  const hombro = degToRad(62 + (hombroDeg - home.hombro))
  const codo = degToRad(118 + (codoDeg - home.codo) * 1.20)

  // Muñeca 1
  // Home visual = límite inferior
  // Desde ahí solo debe subir
  const wrist1LiftDelta = Math.max(0, muneca1Deg - home.muneca1)
  const muneca1 = degToRad(150 - wrist1LiftDelta * 1.10)

  // Muñeca 2
  // Roll de la garra sobre su propio eje
  const muneca2 = degToRad((muneca2Deg - home.muneca2) * 1.0)

  const garraOpen = 0.05 + ((garraRaw - 20) / 120) * 0.14

  return (
    <group position={[0, -1.15, 0]}>
      <gridHelper args={[20, 20, '#1d4ed8', '#1f2937']} position={[0, -0.01, 0]} />
      <axesHelper args={[1.5]} position={[0, 0, 0]} />

      <mesh position={[0, 0.18, 0]} rotation={[0, base, 0]}>
        <cylinderGeometry args={[1.0, 1.15, 0.36, 28, 1, true]} />
        <meshBasicMaterial wireframe color="#38bdf8" />
      </mesh>

      <group position={[0, 0.38, 0]} rotation={[0, base, 0]}>
        <Joint size={0.18} color="#67e8f9" />

        <group rotation={[0, 0, hombro]}>
          <Segment length={upperArmLen} thickness={0.22} color="#60a5fa" />

          <group position={[upperArmLen, 0, 0]}>
            <Joint size={0.17} color="#a5f3fc" />

            <group rotation={[0, 0, codo]}>
              <Segment length={foreArmLen} thickness={0.18} color="#34d399" />

              <group position={[foreArmLen, 0, 0]}>
                <Joint size={0.12} color="#fde68a" />

                <group rotation={[0, 0, muneca1]}>
                  <Segment length={wristLen} thickness={0.10} color="#fbbf24" />

                  <group position={[wristLen, 0, 0]}>
                    <Joint size={0.10} color="#f59e0b" />

                    <group rotation={[0, 0, degToRad(-58)]}>
                      <group rotation={[muneca2, 0, 0]}>
                        <Gripper open={garraOpen} />
                      </group>
                    </group>
                  </group>
                </group>
              </group>
            </group>
          </group>
        </group>
      </group>
    </group>
  )
}

function StatRow({ label, value }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2">
      <span className="text-sm text-slate-300">{label}</span>
      <span className="font-mono text-sm text-cyan-300">{value}</span>
    </div>
  )
}

export default function App() {
  const wsRef = useRef(null)
  const [socketState, setSocketState] = useState('connecting')
  const [robot, setRobot] = useState(DEFAULT_STATE)

  useEffect(() => {
    const ws = new WebSocket('ws://127.0.0.1:8765')
    wsRef.current = ws

    ws.onopen = () => setSocketState('connected')
    ws.onclose = () => setSocketState('disconnected')
    ws.onerror = () => setSocketState('error')
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setRobot(data)
      } catch {
        // ignore
      }
    }

    return () => ws.close()
  }, [])

  function send(payload) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }

  const logs = useMemo(() => [...(robot.logs ?? [])].slice(-80).reverse(), [robot.logs])

  return (
    <div className="h-screen overflow-hidden bg-[radial-gradient(circle_at_top,#0f172a,#060816_55%)] text-slate-100">
      <div className="grid h-full grid-cols-[320px_1fr_360px] gap-3 p-3">
        <aside className="flex flex-col gap-3 rounded-3xl border border-cyan-400/15 bg-slate-950/70 p-4 shadow-2xl shadow-cyan-500/5 backdrop-blur">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-cyan-400/70">Robot IA</p>
            <h1 className="mt-2 text-2xl font-semibold">Control Center</h1>
            <p className="mt-1 text-sm text-slate-400">Fase 1 · estación de control local</p>
          </div>

          <div className="grid gap-2">
            <StatRow label="WebSocket UI" value={socketState} />
            <StatRow label="Serial" value={robot.connected ? 'Conectado' : 'Desconectado'} />
            <StatRow label="Puerto" value={robot.port || '-'} />
            <StatRow label="Modo" value={robot.mode} />
            <StatRow label="Joystick" value={robot.joystick_connected ? 'Detectado' : 'No detectado'} />
          </div>

          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => send({ action: 'home' })}
              className="rounded-2xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-sm font-medium transition hover:bg-cyan-400/20"
            >
              Home
            </button>
            <button
              onClick={() => send({ action: 'saludo' })}
              className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-sm font-medium transition hover:bg-emerald-400/20"
            >
              Saludo
            </button>
            <button
              onClick={() => send({ action: 'stop' })}
              className="rounded-2xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm font-medium transition hover:bg-rose-400/20"
            >
              Stop
            </button>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
            <p className="mb-3 text-sm font-medium text-slate-200">Joystick</p>
            <div className="grid gap-2">
              <StatRow label="Axis 0" value={pretty(robot.joystick?.axis0)} />
              <StatRow label="Axis 1" value={pretty(robot.joystick?.axis1)} />
              <StatRow
                label="Hat"
                value={`${robot.joystick?.hat?.[0] ?? 0}, ${robot.joystick?.hat?.[1] ?? 0}`}
              />
              <div className="rounded-lg border border-white/10 bg-slate-900/70 p-2">
                <p className="mb-2 text-xs uppercase tracking-wider text-slate-400">Botones</p>
                <div className="grid grid-cols-4 gap-2">
                  {(robot.joystick?.buttons ?? []).map((b, i) => (
                    <div
                      key={i}
                      className={`rounded-lg border px-2 py-1 text-center font-mono text-xs ${
                        b
                          ? 'border-cyan-300/50 bg-cyan-400/20 text-cyan-200'
                          : 'border-white/10 bg-white/5 text-slate-400'
                      }`}
                    >
                      {i}:{b}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </aside>

        <main className="grid grid-rows-[1fr_220px] gap-3">
          <section className="rounded-3xl border border-cyan-400/15 bg-slate-950/65 shadow-2xl shadow-cyan-500/5 backdrop-blur">
            <Canvas camera={{ position: [6, 5, 8], fov: 42 }}>
              <color attach="background" args={['#050816']} />
              <ambientLight intensity={1} />
              <RobotArm servos={robot.servos} />
              <OrbitControls enablePan enableZoom enableRotate />
            </Canvas>
          </section>

          <section className="overflow-hidden rounded-3xl border border-cyan-400/15 bg-slate-950/70 p-4 shadow-2xl shadow-cyan-500/5 backdrop-blur">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Consola</h2>
                <p className="text-sm text-slate-400">Lo mismo que ves en backend, pero sin olor a terminal.</p>
              </div>
            </div>
            <div className="h-[150px] overflow-auto rounded-2xl border border-white/10 bg-black/30 p-3 font-mono text-xs text-emerald-300">
              {logs.length === 0 ? (
                <div className="text-slate-500">Sin logs todavía.</div>
              ) : (
                logs.map((line, idx) => (
                  <div key={idx} className="mb-1 whitespace-pre-wrap">
                    {line}
                  </div>
                ))
              )}
            </div>
          </section>
        </main>

        <aside className="flex flex-col gap-3 rounded-3xl border border-cyan-400/15 bg-slate-950/70 p-4 shadow-2xl shadow-cyan-500/5 backdrop-blur">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-cyan-400/70">Telemetría</p>
            <h2 className="mt-2 text-xl font-semibold">Servos</h2>
          </div>

          <div className="grid gap-3 overflow-auto">
            {SERVO_ORDER.map((name) => {
              const servo = robot.servos?.[name]
              if (!servo) return null

              return (
                <div key={name} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{SERVO_LABELS[name]}</p>
                      <p className="text-xs text-slate-400">
                        ID {servo.id} · PCA {servo.pca_channel ?? '-'}
                      </p>
                    </div>
                    <div className="text-right font-mono text-xs text-slate-300">
                      <div>cur: {servo.current}</div>
                      <div>tar: {servo.target}</div>
                    </div>
                  </div>

                  <input
                    type="range"
                    min={servo.min ?? 0}
                    max={servo.max ?? 180}
                    value={servo.target ?? servo.current ?? 0}
                    onChange={(e) =>
                      send({
                        action: 'set_servo',
                        servo_id: servo.id,
                        angle: Number(e.target.value),
                      })
                    }
                    className="w-full accent-cyan-400"
                  />

                  <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                    <span>min {servo.min ?? '-'}</span>
                    <span>max {servo.max ?? '-'}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </aside>
      </div>
    </div>
  )
}