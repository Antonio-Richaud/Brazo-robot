import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
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

function lerp(a, b, t) {
  return a + (b - a) * t
}

function activeServoName(servos) {
  let bestName = null
  let bestDiff = 0

  for (const name of SERVO_ORDER) {
    const s = servos?.[name]
    if (!s) continue
    const diff = Math.abs((s.target ?? 0) - (s.current ?? 0))
    if (diff > bestDiff) {
      bestDiff = diff
      bestName = name
    }
  }

  return bestDiff >= 1 ? bestName : null
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

function Gripper({ open = 0.09, topRef, bottomRef, color = '#fca5a5' }) {
  return (
    <group>
      <mesh position={[0.11, 0, 0]}>
        <boxGeometry args={[0.22, 0.12, 0.12]} />
        <meshBasicMaterial wireframe color={color} />
      </mesh>

      <mesh position={[0.06, 0, 0.10]}>
        <boxGeometry args={[0.10, 0.05, 0.05]} />
        <meshBasicMaterial wireframe color="#fb7185" />
      </mesh>

      <mesh ref={topRef} position={[0.26, open, 0]} rotation={[0, 0, degToRad(-16)]}>
        <boxGeometry args={[0.10, 0.24, 0.08]} />
        <meshBasicMaterial wireframe color={color} />
      </mesh>

      <mesh ref={bottomRef} position={[0.26, -open, 0]} rotation={[0, 0, degToRad(16)]}>
        <boxGeometry args={[0.10, 0.24, 0.08]} />
        <meshBasicMaterial wireframe color={color} />
      </mesh>
    </group>
  )
}

function buildRobotPose(servos) {
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

  const upperArmLen = 2.35
  const foreArmLen = 1.65
  const wristLen = 0.06

  const base = degToRad(baseDeg - home.base)
  const hombro = degToRad(62 + (hombroDeg - home.hombro))
  const codo = degToRad(118 + (codoDeg - home.codo) * 1.2)

  const wrist1LiftDelta = Math.max(0, muneca1Deg - home.muneca1)
  const muneca1 = degToRad(150 - wrist1LiftDelta * 1.1)

  const muneca2 = degToRad((muneca2Deg - home.muneca2) * 1.0)

  const garraOpen = 0.05 + ((garraRaw - 20) / 120) * 0.14

  return {
    upperArmLen,
    foreArmLen,
    wristLen,
    base,
    hombro,
    codo,
    muneca1,
    muneca2,
    garraOpen,
  }
}

function RobotArm({ servos, activeName }) {
  const baseYawRef = useRef()
  const shoulderRef = useRef()
  const elbowRef = useRef()
  const wrist1Ref = useRef()
  const wrist2Ref = useRef()
  const fingerTopRef = useRef()
  const fingerBottomRef = useRef()

  const targetPoseRef = useRef(buildRobotPose(servos))
  const visualPoseRef = useRef(buildRobotPose(servos))

  useEffect(() => {
    targetPoseRef.current = buildRobotPose(servos)
  }, [servos])

  useFrame((_, delta) => {
    const target = targetPoseRef.current
    const visual = visualPoseRef.current
    const alpha = 1 - Math.exp(-16 * delta)

    visual.base = lerp(visual.base, target.base, alpha)
    visual.hombro = lerp(visual.hombro, target.hombro, alpha)
    visual.codo = lerp(visual.codo, target.codo, alpha)
    visual.muneca1 = lerp(visual.muneca1, target.muneca1, alpha)
    visual.muneca2 = lerp(visual.muneca2, target.muneca2, alpha)
    visual.garraOpen = lerp(visual.garraOpen, target.garraOpen, alpha)

    if (baseYawRef.current) baseYawRef.current.rotation.y = visual.base
    if (shoulderRef.current) shoulderRef.current.rotation.z = visual.hombro
    if (elbowRef.current) elbowRef.current.rotation.z = visual.codo
    if (wrist1Ref.current) wrist1Ref.current.rotation.z = visual.muneca1
    if (wrist2Ref.current) wrist2Ref.current.rotation.x = visual.muneca2
    if (fingerTopRef.current) fingerTopRef.current.position.y = visual.garraOpen
    if (fingerBottomRef.current) fingerBottomRef.current.position.y = -visual.garraOpen
  })

  const initial = visualPoseRef.current

  const colors = {
    base: activeName === 'base' ? '#22d3ee' : '#38bdf8',
    hombro: activeName === 'hombro' ? '#a78bfa' : '#60a5fa',
    codo: activeName === 'codo' ? '#4ade80' : '#34d399',
    muneca1: activeName === 'muneca1' ? '#fde047' : '#fbbf24',
    muneca2: activeName === 'muneca2' ? '#fb923c' : '#f59e0b',
    garra: activeName === 'garra' ? '#f472b6' : '#fca5a5',
  }

  return (
    <group position={[0, -1.15, 0]}>
      <gridHelper args={[20, 20, '#1d4ed8', '#1f2937']} position={[0, -0.01, 0]} />
      <axesHelper args={[1.5]} position={[0, 0, 0]} />

      <group ref={baseYawRef} rotation={[0, initial.base, 0]}>
        <mesh position={[0, 0.18, 0]}>
          <cylinderGeometry args={[1.0, 1.15, 0.36, 28, 1, true]} />
          <meshBasicMaterial wireframe color={colors.base} />
        </mesh>

        <group position={[0, 0.38, 0]}>
          <Joint size={0.18} color={colors.base} />

          <group ref={shoulderRef} rotation={[0, 0, initial.hombro]}>
            <Segment length={initial.upperArmLen} thickness={0.22} color={colors.hombro} />

            <group position={[initial.upperArmLen, 0, 0]}>
              <Joint size={0.17} color={colors.hombro} />

              <group ref={elbowRef} rotation={[0, 0, initial.codo]}>
                <Segment length={initial.foreArmLen} thickness={0.18} color={colors.codo} />

                <group position={[initial.foreArmLen, 0, 0]}>
                  <Joint size={0.12} color={colors.codo} />

                  <group ref={wrist1Ref} rotation={[0, 0, initial.muneca1]}>
                    <Segment length={initial.wristLen} thickness={0.10} color={colors.muneca1} />

                    <group position={[initial.wristLen, 0, 0]}>
                      <Joint size={0.10} color={colors.muneca2} />

                      <group rotation={[0, 0, degToRad(-58)]}>
                        <group ref={wrist2Ref} rotation={[initial.muneca2, 0, 0]}>
                          <Gripper
                            open={initial.garraOpen}
                            topRef={fingerTopRef}
                            bottomRef={fingerBottomRef}
                            color={colors.garra}
                          />
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
  const consoleRef = useRef(null)

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
      } catch {}
    }

    return () => ws.close()
  }, [])

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = 0
    }
  }, [robot.logs])

  function send(payload) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }

  const logs = useMemo(() => [...(robot.logs ?? [])].slice(-80).reverse(), [robot.logs])
  const activeName = useMemo(() => activeServoName(robot.servos), [robot.servos])

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
            <StatRow label="Activo" value={activeName || 'ninguno'} />
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
              <RobotArm servos={robot.servos} activeName={activeName} />
              <OrbitControls enablePan enableZoom enableRotate />
            </Canvas>
          </section>

          <section className="overflow-hidden rounded-3xl border border-cyan-400/15 bg-slate-950/70 p-4 shadow-2xl shadow-cyan-500/5 backdrop-blur">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Consola</h2>
                <p className="text-sm text-slate-400">Limpia y directa.</p>
              </div>
            </div>
            <div
              ref={consoleRef}
              className="h-[150px] overflow-auto rounded-2xl border border-white/10 bg-black/30 p-3 font-mono text-xs text-emerald-300"
            >
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
              const isActive = activeName === name

              return (
                <div
                  key={name}
                  className={`rounded-2xl border p-3 transition ${
                    isActive
                      ? 'border-cyan-300/40 bg-cyan-400/10 shadow-lg shadow-cyan-500/10'
                      : 'border-white/10 bg-white/5'
                  }`}
                >
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