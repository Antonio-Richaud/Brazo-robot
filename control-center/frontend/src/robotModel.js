export const SERVO_ORDER = ['base', 'hombro', 'codo', 'muneca1', 'muneca2', 'garra']

export const SERVO_LABELS = {
  base: 'Base',
  hombro: 'Hombro',
  codo: 'Codo',
  muneca1: 'Muñeca vertical',
  muneca2: 'Giro de muñeca',
  garra: 'Garra',
}

export const HOME = {
  base: 90,
  hombro: 50,
  codo: 165,
  muneca1: 10,
  muneca2: 170,
  garra: 40,
}

export const DEFAULT_STATE = {
  protocol_version: 2,
  connected: false,
  port: null,
  runtime_mode: 'simulation',
  mode: 'manual',
  joystick_connected: false,
  servos: Object.fromEntries(
    SERVO_ORDER.map((name, index) => [
      name,
      {
        id: index + 1,
        current: HOME[name],
        target: HOME[name],
        min: name === 'garra' ? 20 : name === 'hombro' || name === 'codo' ? 15 : 10,
        max: name === 'garra' ? 140 : name === 'hombro' || name === 'codo' ? 165 : 170,
        pca_channel: index,
        measured: false,
      },
    ]),
  ),
  joystick: { axis0: 0, axis1: 0, hat: [0, 0], buttons: Array(8).fill(0) },
  perception: {
    enabled: false,
    source: 'off',
    status: 'inactive',
    model: 'Intel RealSense D435i',
    serial: '926522071007',
    coordinate_frame: 'robot_base',
    calibrated: false,
    fps: 0,
    point_count: 0,
    closest_distance_m: null,
    points: [],
    obstacles: [],
  },
  health: { uptime_s: 0, last_error: null },
  logs: [],
}

export function degToRad(degrees) {
  return (degrees * Math.PI) / 180
}

export function activeServoName(servos) {
  let result = null
  let largestDifference = 0
  for (const name of SERVO_ORDER) {
    const servo = servos?.[name]
    if (!servo) continue
    const difference = Math.abs((servo.target ?? 0) - (servo.current ?? 0))
    if (difference > largestDifference) {
      result = name
      largestDifference = difference
    }
  }
  return largestDifference >= 1 ? result : null
}

export function buildRobotPose(servos) {
  const value = (name) => servos?.[name]?.current ?? HOME[name]
  const gripper = value('garra')
  return {
    base: degToRad(value('base') - HOME.base),
    shoulder: degToRad(58 + value('hombro') - HOME.hombro),
    elbow: degToRad(116 + (value('codo') - HOME.codo) * 1.15),
    wristPitch: degToRad(148 - Math.max(0, value('muneca1') - HOME.muneca1) * 1.05),
    wristRoll: degToRad(value('muneca2') - HOME.muneca2),
    gripperOpen: 0.055 + ((gripper - 20) / 120) * 0.14,
  }
}
