import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { ContactShadows, Grid, Line, OrbitControls, RoundedBox } from '@react-three/drei'
import * as THREE from 'three'
import { buildRobotPose } from './robotModel.js'

const COLORS = {
  graphite: '#172033',
  metal: '#8fa1b8',
  cyan: '#42d7e8',
  amber: '#f6b94a',
  red: '#ff667f',
}

function damp(current, target, delta, speed = 13) {
  return THREE.MathUtils.lerp(current, target, 1 - Math.exp(-speed * delta))
}

function Joint({ active = false, radius = 0.2, rotation = [Math.PI / 2, 0, 0] }) {
  return (
    <group rotation={rotation}>
      <mesh castShadow receiveShadow>
        <cylinderGeometry args={[radius, radius, radius * 1.25, 32]} />
        <meshStandardMaterial
          color={active ? COLORS.cyan : '#34445e'}
          metalness={0.72}
          roughness={0.28}
          emissive={active ? COLORS.cyan : '#000000'}
          emissiveIntensity={active ? 0.28 : 0}
        />
      </mesh>
      <mesh position={[0, radius * 0.66, 0]}>
        <cylinderGeometry args={[radius * 0.46, radius * 0.46, 0.025, 24]} />
        <meshStandardMaterial color={COLORS.amber} metalness={0.5} roughness={0.25} />
      </mesh>
    </group>
  )
}

function Link({ length, thickness = 0.24, active = false }) {
  return (
    <group position={[length / 2, 0, 0]}>
      <RoundedBox args={[length, thickness, thickness * 0.76]} radius={0.075} smoothness={4} castShadow receiveShadow>
        <meshStandardMaterial
          color={active ? '#2a6371' : COLORS.graphite}
          metalness={0.58}
          roughness={0.32}
          emissive={active ? COLORS.cyan : '#000000'}
          emissiveIntensity={active ? 0.12 : 0}
        />
      </RoundedBox>
      <mesh position={[0, 0, thickness * 0.4 + 0.008]}>
        <boxGeometry args={[length * 0.76, thickness * 0.22, 0.018]} />
        <meshStandardMaterial color={COLORS.metal} metalness={0.82} roughness={0.18} />
      </mesh>
    </group>
  )
}

function RealSenseModel({ active = false }) {
  const rayColor = active ? '#45e6ff' : '#486273'
  const origin = [0.25, 0, 0]
  const corners = [
    [1.7, 0.7, 1.05],
    [1.7, 0.7, -1.05],
    [1.7, -0.7, -1.05],
    [1.7, -0.7, 1.05],
  ]
  return (
    <group position={[0.15, 0.2, 0]}>
      <RoundedBox args={[0.52, 0.14, 0.2]} radius={0.035} smoothness={4} castShadow>
        <meshStandardMaterial color="#202a33" metalness={0.65} roughness={0.28} />
      </RoundedBox>
      {[-0.16, 0.16].map((z) => (
        <mesh key={z} position={[0, 0, z * 0.42]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.038, 0.038, 0.025, 24]} />
          <meshStandardMaterial color="#06090d" metalness={0.1} roughness={0.12} />
        </mesh>
      ))}
      <mesh position={[0, 0.073, 0]}>
        <boxGeometry args={[0.36, 0.012, 0.035]} />
        <meshBasicMaterial color={active ? COLORS.cyan : '#325161'} />
      </mesh>
      {corners.map((corner, index) => (
        <Line key={index} points={[origin, corner]} color={rayColor} transparent opacity={active ? 0.22 : 0.07} lineWidth={0.65} />
      ))}
      <Line points={[...corners, corners[0]]} color={rayColor} transparent opacity={active ? 0.25 : 0.08} lineWidth={0.65} />
    </group>
  )
}

function Gripper({ topRef, bottomRef, open, perceptionActive }) {
  return (
    <group>
      <RoundedBox args={[0.34, 0.2, 0.22]} radius={0.05} smoothness={4} position={[0.17, 0, 0]} castShadow>
        <meshStandardMaterial color="#26374b" metalness={0.62} roughness={0.3} />
      </RoundedBox>
      {[1, -1].map((direction) => (
        <group key={direction} ref={direction > 0 ? topRef : bottomRef} position={[0.38, direction * open, 0]}>
          <RoundedBox args={[0.26, 0.075, 0.1]} radius={0.025} smoothness={3} position={[0.1, 0, 0]} castShadow>
            <meshStandardMaterial color={COLORS.red} metalness={0.45} roughness={0.32} />
          </RoundedBox>
        </group>
      ))}
      <RealSenseModel active={perceptionActive} />
    </group>
  )
}

function RobotArm({ servos, activeName, perceptionActive }) {
  const baseRef = useRef()
  const shoulderRef = useRef()
  const elbowRef = useRef()
  const wristPitchRef = useRef()
  const wristRollRef = useRef()
  const topFingerRef = useRef()
  const bottomFingerRef = useRef()
  const [initialPose] = useState(() => buildRobotPose(servos))
  const targetRef = useRef({ ...initialPose })
  const visualRef = useRef({ ...initialPose })

  useEffect(() => {
    targetRef.current = buildRobotPose(servos)
  }, [servos])

  useFrame((_, delta) => {
    const target = targetRef.current
    const visual = visualRef.current
    for (const key of ['base', 'shoulder', 'elbow', 'wristPitch', 'wristRoll', 'gripperOpen']) {
      visual[key] = damp(visual[key], target[key], delta)
    }
    if (baseRef.current) baseRef.current.rotation.y = visual.base
    if (shoulderRef.current) shoulderRef.current.rotation.z = visual.shoulder
    if (elbowRef.current) elbowRef.current.rotation.z = visual.elbow
    if (wristPitchRef.current) wristPitchRef.current.rotation.z = visual.wristPitch
    if (wristRollRef.current) wristRollRef.current.rotation.x = visual.wristRoll
    if (topFingerRef.current) topFingerRef.current.position.y = visual.gripperOpen
    if (bottomFingerRef.current) bottomFingerRef.current.position.y = -visual.gripperOpen
  })

  const upper = 2.25
  const forearm = 1.65
  const wrist = 0.42

  return (
    <group position={[0, 0, 0]}>
      <group ref={baseRef} rotation={[0, initialPose.base, 0]}>
        <mesh position={[0, 0.15, 0]} castShadow receiveShadow>
          <cylinderGeometry args={[0.72, 0.9, 0.3, 42]} />
          <meshStandardMaterial color="#18263a" metalness={0.7} roughness={0.28} />
        </mesh>
        <mesh position={[0, 0.33, 0]} castShadow>
          <cylinderGeometry args={[0.5, 0.61, 0.12, 42]} />
          <meshStandardMaterial color={COLORS.metal} metalness={0.85} roughness={0.18} />
        </mesh>
        <group position={[0, 0.52, 0]}>
          <Joint active={activeName === 'base'} radius={0.24} />
          <group ref={shoulderRef} rotation={[0, 0, initialPose.shoulder]}>
            <Link length={upper} thickness={0.3} active={activeName === 'hombro'} />
            <group position={[upper, 0, 0]}>
              <Joint active={activeName === 'hombro'} radius={0.23} />
              <group ref={elbowRef} rotation={[0, 0, initialPose.elbow]}>
                <Link length={forearm} active={activeName === 'codo'} />
                <group position={[forearm, 0, 0]}>
                  <Joint active={activeName === 'codo'} radius={0.18} />
                  <group ref={wristPitchRef} rotation={[0, 0, initialPose.wristPitch]}>
                    <Link length={wrist} thickness={0.16} active={activeName === 'muneca1'} />
                    <group position={[wrist, 0, 0]}>
                      <Joint active={activeName === 'muneca1'} radius={0.13} />
                      <group ref={wristRollRef} rotation={[initialPose.wristRoll, 0, 0]}>
                        <Gripper
                          topRef={topFingerRef}
                          bottomRef={bottomFingerRef}
                          open={initialPose.gripperOpen}
                          perceptionActive={perceptionActive}
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
  )
}

function PerceptionCloud({ perception }) {
  const geometry = useMemo(() => {
    const next = new THREE.BufferGeometry()
    const flat = (perception?.points ?? []).flatMap((point) => point.slice(0, 3))
    next.setAttribute('position', new THREE.Float32BufferAttribute(flat, 3))
    return next
  }, [perception?.points])

  useEffect(() => () => geometry.dispose(), [geometry])
  if (!perception?.enabled || !perception?.points?.length) return null

  return (
    <group position={perception.coordinate_frame === 'camera' ? [0, 1.7, 2.4] : [0, 0, 0]}>
      <points geometry={geometry}>
        <pointsMaterial color="#58def0" size={0.035} sizeAttenuation transparent opacity={0.66} depthWrite={false} />
      </points>
      {(perception.obstacles ?? []).map((obstacle) => (
        <mesh key={obstacle.id} position={obstacle.center}>
          <boxGeometry args={obstacle.size} />
          <meshBasicMaterial color={COLORS.amber} wireframe transparent opacity={0.8} />
        </mesh>
      ))}
    </group>
  )
}

function Scene({ robot, activeName }) {
  const perceptionActive = robot.perception?.status === 'streaming'
  return (
    <>
      <color attach="background" args={['#070b13']} />
      <fog attach="fog" args={['#070b13', 10, 24]} />
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 7, 5]} intensity={2.4} color="#d9f6ff" castShadow shadow-mapSize={[1024, 1024]} />
      <pointLight position={[-4, 2.5, -2]} intensity={14} distance={9} color="#167b9b" />
      <pointLight position={[3, 1.2, 3]} intensity={9} distance={7} color="#b07025" />

      <Grid
        position={[0, 0.01, 0]}
        args={[18, 18]}
        cellSize={0.3}
        cellThickness={0.45}
        cellColor="#1b3344"
        sectionSize={1.5}
        sectionThickness={0.8}
        sectionColor="#2b6075"
        fadeDistance={13}
        fadeStrength={1.6}
        infiniteGrid
      />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[5.4, 64]} />
        <meshStandardMaterial color="#0a101a" metalness={0.15} roughness={0.92} />
      </mesh>
      {[1.5, 3, 4.5].map((radius) => (
        <mesh key={radius} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.018, 0]}>
          <ringGeometry args={[radius - 0.008, radius + 0.008, 96]} />
          <meshBasicMaterial color="#1a5667" transparent opacity={0.55} />
        </mesh>
      ))}

      <RobotArm servos={robot.servos} activeName={activeName} perceptionActive={perceptionActive} />
      <PerceptionCloud perception={robot.perception} />
      <ContactShadows position={[0, 0.025, 0]} opacity={0.5} scale={12} blur={2.8} far={7} />
      <OrbitControls makeDefault target={[0.6, 1.35, 0]} minDistance={4.5} maxDistance={13} maxPolarAngle={Math.PI / 2.05} />
    </>
  )
}

export function RobotScene({ robot, activeName }) {
  return (
    <Canvas
      camera={{ position: [6.8, 5.2, 7.8], fov: 39, near: 0.1, far: 60 }}
      dpr={[1, 1.7]}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      shadows
    >
      <Scene robot={robot} activeName={activeName} />
    </Canvas>
  )
}
