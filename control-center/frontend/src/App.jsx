import { lazy, Suspense, useMemo } from 'react'
import { SERVO_LABELS, SERVO_ORDER, activeServoName } from './robotModel.js'
import { useRobotSocket } from './useRobotSocket.js'

const RobotScene = lazy(() =>
  import('./RobotScene.jsx').then((module) => ({ default: module.RobotScene })),
)

function formatNumber(value, digits = 1) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : '—'
}

function StatusDot({ state }) {
  return <span className={`status-dot status-dot--${state}`} aria-hidden="true" />
}

function Metric({ label, value, tone = 'neutral' }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={`tone-${tone}`}>{value}</strong>
    </div>
  )
}

function ActionButton({ children, tone, disabled, onClick, title }) {
  return (
    <button className={`action action--${tone}`} disabled={disabled} onClick={onClick} title={title}>
      {children}
    </button>
  )
}

function ServoControl({ name, servo, disabled, active, send }) {
  const percentage = ((servo.target - servo.min) / (servo.max - servo.min)) * 100
  return (
    <article className={`servo ${active ? 'servo--active' : ''}`}>
      <div className="servo__head">
        <div>
          <span className="servo__name">{SERVO_LABELS[name]}</span>
          <span className="servo__meta">ID {servo.id} · PCA {servo.pca_channel}</span>
        </div>
        <div className="servo__reading">
          <strong>{servo.current}°</strong>
          <span>objetivo {servo.target}°</span>
        </div>
      </div>
      <input
        type="range"
        min={servo.min}
        max={servo.max}
        value={servo.target}
        disabled={disabled}
        onChange={(event) => send({ action: 'set_servo', servo_id: servo.id, angle: Number(event.target.value) })}
        style={{ '--progress': `${percentage}%` }}
        aria-label={`Mover ${SERVO_LABELS[name]}`}
      />
      <div className="servo__limits"><span>{servo.min}°</span><span>{servo.max}°</span></div>
    </article>
  )
}

function App() {
  const { robot, socketState, lastMessageAt, send } = useRobotSocket()
  const activeName = useMemo(() => activeServoName(robot.servos), [robot.servos])
  const logs = useMemo(() => [...(robot.logs ?? [])].slice(-80).reverse(), [robot.logs])
  const socketConnected = socketState === 'connected'
  const manual = robot.mode === 'manual'
  const perception = robot.perception ?? {}
  const controlsDisabled = !socketConnected || !manual
  const lastMessageTime = lastMessageAt
    ? new Date(lastMessageAt).toLocaleTimeString('es-MX', { hour12: false })
    : '—'

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand__mark"><span /></div>
          <div>
            <p>ROBOT IA · LAB</p>
            <h1>Arm Control Center</h1>
          </div>
        </div>
        <div className="topbar__status">
          <span className="eyebrow">ENLACE LOCAL</span>
          <div><StatusDot state={socketConnected ? 'online' : 'warning'} /><strong>{socketState}</strong></div>
        </div>
        <div className="topbar__clock">
          <span className="eyebrow">ÚLTIMO ESTADO</span>
          <strong>{lastMessageTime}</strong>
        </div>
      </header>

      <div className="workspace">
        <aside className="panel panel--controls">
          <section className="panel-section">
            <div className="section-title"><span>01</span><h2>Sistema</h2></div>
            <div className="metrics-grid">
              <Metric label="Runtime" value={robot.runtime_mode} tone="cyan" />
              <Metric label="ESP32" value={robot.connected ? 'conectado' : 'sin enlace'} tone={robot.connected ? 'green' : 'amber'} />
              <Metric label="Puerto" value={robot.port || '—'} />
              <Metric label="Modo" value={robot.mode} tone={manual ? 'cyan' : 'amber'} />
              <Metric label="Joystick" value={robot.joystick_connected ? 'detectado' : 'ausente'} />
              <Metric label="Activo" value={activeName ? SERVO_LABELS[activeName] : 'estable'} />
            </div>
          </section>

          <section className="panel-section">
            <div className="section-title"><span>02</span><h2>Acciones</h2></div>
            <div className="action-grid">
              <ActionButton tone="cyan" disabled={!socketConnected} onClick={() => send({ action: 'home' })}>Home</ActionButton>
              <ActionButton tone="green" disabled={!socketConnected || !manual} onClick={() => send({ action: 'saludo' })}>Saludo</ActionButton>
              <ActionButton tone="violet" disabled={!socketConnected || !manual} onClick={() => send({ action: 'rutina' })}>Rutina</ActionButton>
              <ActionButton
                tone="amber"
                disabled={!socketConnected}
                onClick={() => send({ action: 'stop' })}
                title="Cancela la secuencia y ordena volver a Home; no es un paro eléctrico."
              >Cancelar / Home</ActionButton>
            </div>
            <p className="safety-note"><span>!</span> “Cancelar” todavía mueve el brazo hacia Home. No sustituye un corte físico de potencia.</p>
          </section>

          <section className="panel-section perception-card">
            <div className="section-title"><span>03</span><h2>Percepción</h2></div>
            <div className="sensor-name">
              <div className="sensor-icon"><i /><i /></div>
              <div><strong>{perception.model || 'Intel RealSense D435i'}</strong><span>S/N {perception.serial || '926522071007'}</span></div>
              <StatusDot state={perception.status === 'streaming' ? 'online' : perception.status === 'error' ? 'error' : 'idle'} />
            </div>
            <div className="sensor-stats">
              <Metric label="Fuente" value={perception.source || 'off'} />
              <Metric label="Estado" value={perception.status || 'inactive'} />
              <Metric label="Nube" value={`${perception.point_count || 0} pts`} />
              <Metric label="Frecuencia" value={`${formatNumber(perception.fps)} Hz`} />
              <Metric label="Objeto cercano" value={perception.closest_distance_m ? `${formatNumber(perception.closest_distance_m, 2)} m` : '—'} />
              <Metric label="Calibración" value={perception.calibrated ? 'válida' : 'pendiente'} tone={perception.calibrated ? 'green' : 'amber'} />
            </div>
          </section>

          <section className="panel-section joystick-card">
            <div className="section-title"><span>04</span><h2>Joystick</h2></div>
            <div className="axis-row">
              <div><span>X</span><div className="axis-track"><i style={{ left: `${50 + (robot.joystick?.axis0 || 0) * 46}%` }} /></div></div>
              <div><span>Y</span><div className="axis-track"><i style={{ left: `${50 + (robot.joystick?.axis1 || 0) * 46}%` }} /></div></div>
            </div>
            <div className="button-map">
              {(robot.joystick?.buttons ?? []).map((pressed, index) => <span key={index} className={pressed ? 'pressed' : ''}>{index}</span>)}
            </div>
          </section>
        </aside>

        <main className="main-stage">
          <section className="scene-card">
            <div className="scene-overlay scene-overlay--left">
              <span className="eyebrow">DIGITAL TWIN</span>
              <strong>Modelo cinemático · 6 GDL</strong>
            </div>
            <div className="scene-overlay scene-overlay--right">
              <span className={`mode-pill mode-pill--${robot.mode}`}>{robot.mode}</span>
              <span className="frame-pill">{perception.coordinate_frame || 'robot_base'}</span>
            </div>
            <Suspense fallback={<div className="scene-loading"><span />Preparando gemelo digital…</div>}>
              <RobotScene robot={robot} activeName={activeName} />
            </Suspense>
            <div className="scene-help">Arrastra para orbitar · rueda para acercar</div>
          </section>

          <section className="console-card">
            <div className="console-head">
              <div><span className="eyebrow">EVENT STREAM</span><h2>Consola</h2></div>
              <span>{logs.length} eventos</span>
            </div>
            <div className="console-log">
              {logs.length ? logs.map((line, index) => <p key={`${line}-${index}`}>{line}</p>) : <p className="muted">Esperando eventos del backend…</p>}
            </div>
          </section>
        </main>

        <aside className="panel panel--servos">
          <div className="servo-panel-head">
            <div><span className="eyebrow">TELEMETRÍA ESTIMADA</span><h2>Articulaciones</h2></div>
            <span className="servo-count">06</span>
          </div>
          <p className="estimate-note">Los ángulos son estimados por software; los servos actuales no entregan retroalimentación física.</p>
          <div className="servo-list">
            {SERVO_ORDER.map((name) => {
              const servo = robot.servos?.[name]
              return servo ? <ServoControl key={name} name={name} servo={servo} disabled={controlsDisabled} active={activeName === name} send={send} /> : null
            })}
          </div>
          {robot.health?.last_error && <div className="error-card"><strong>Error activo</strong><span>{robot.health.last_error}</span></div>}
        </aside>
      </div>
    </div>
  )
}

export default App
