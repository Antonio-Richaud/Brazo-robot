#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <math.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const uint8_t SDA_PIN = 21;
const uint8_t SCL_PIN = 22;
const uint8_t SERVO_FREQ = 50;
const uint8_t SERVO_COUNT = 6;

const uint16_t MOTION_UPDATE_MS = 10;

const float MAX_SPEED_DEG_PER_SEC = 85.0f;
const float MAX_ACCEL_DEG_PER_SEC2 = 260.0f;
const float POSITION_EPS = 0.20f;
const float VELOCITY_EPS = 1.00f;

struct ServoAxis {
  const char* name;
  uint8_t channel;
  int minAngle;
  int maxAngle;
  int minUs;
  int maxUs;
  int home;
  float current;
  float target;
  float velocity;
};

ServoAxis servos[SERVO_COUNT] = {
  {"base",    0, 10, 170, 500, 2500,  90,  90.0f,  90.0f, 0.0f},
  {"hombro",  1, 15, 165, 500, 2500,  50,  50.0f,  50.0f, 0.0f},
  {"codo",    2, 15, 165, 500, 2500, 165, 165.0f, 165.0f, 0.0f},
  {"muneca1", 3, 10, 170, 500, 2500,  10,  10.0f,  10.0f, 0.0f},
  {"muneca2", 4, 10, 170, 500, 2500, 170, 170.0f, 170.0f, 0.0f},
  {"garra",   5, 20, 140, 500, 2500,  40,  40.0f,  40.0f, 0.0f}
};

unsigned long lastMotionUpdate = 0;
String inputLine = "";

enum ChoreoPhase {
  CHOREO_IDLE,
  CHOREO_MOVING,
  CHOREO_HOLDING
};

bool choreoActive = false;
ChoreoPhase choreoPhase = CHOREO_IDLE;
uint8_t choreoStep = 0;
unsigned long choreoPhaseStart = 0;
float choreoStartAngles[SERVO_COUNT];

struct ChoreoPose {
  int angles[SERVO_COUNT];
  unsigned long moveMs;
  unsigned long holdMs;
};

ChoreoPose saludoPoses[] = {
  { {  90,  60,  90,  90, 100,  40 }, 2600, 450 },
  { {  90,  50, 165,  10, 170,  40 }, 2800, 150 }
};

const uint8_t SALUDO_POSE_COUNT = sizeof(saludoPoses) / sizeof(saludoPoses[0]);

float clampFloat(float value, float minValue, float maxValue) {
  if (value < minValue) return minValue;
  if (value > maxValue) return maxValue;
  return value;
}

int clampInt(int value, int minValue, int maxValue) {
  if (value < minValue) return minValue;
  if (value > maxValue) return maxValue;
  return value;
}

int roundToInt(float v) {
  return (int)lroundf(v);
}

uint16_t usToTicks(int microseconds) {
  return (uint16_t)((microseconds * 4096L) / 20000L);
}

int angleToUs(const ServoAxis& s, float angle) {
  angle = clampFloat(angle, s.minAngle, s.maxAngle);
  float ratio = angle / 180.0f;
  float us = s.minUs + ratio * (float)(s.maxUs - s.minUs);
  return (int)lroundf(us);
}

void writeServoAngleFloat(uint8_t index, float angle) {
  angle = clampFloat(angle, servos[index].minAngle, servos[index].maxAngle);
  int us = angleToUs(servos[index], angle);
  uint16_t ticks = usToTicks(us);
  pwm.setPWM(servos[index].channel, 0, ticks);
}

void writeAllServosCurrent() {
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    writeServoAngleFloat(i, servos[i].current);
  }
}

void setServoTarget(uint8_t index, float angle, bool resetVelocity = true) {
  servos[index].target = clampFloat(angle, servos[index].minAngle, servos[index].maxAngle);
  if (resetVelocity) {
    servos[index].velocity = 0.0f;
  }
}

void moveToHome() {
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    setServoTarget(i, servos[i].home, true);
  }
}

void printStatus() {
  Serial.println("---- STATUS ----");
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    Serial.print(i + 1);
    Serial.print(") ");
    Serial.print(servos[i].name);
    Serial.print(" | PCA ch=");
    Serial.print(servos[i].channel);
    Serial.print(" | current=");
    Serial.print(roundToInt(servos[i].current));
    Serial.print(" | target=");
    Serial.print(roundToInt(servos[i].target));
    Serial.print(" | min=");
    Serial.print(servos[i].minAngle);
    Serial.print(" | max=");
    Serial.println(servos[i].maxAngle);
  }
  Serial.println("----------------");
}

void printHelp() {
  Serial.println();
  Serial.println("Comandos disponibles:");
  Serial.println("help                   -> mostrar ayuda");
  Serial.println("status                 -> ver estado");
  Serial.println("home                   -> mover todos a home");
  Serial.println("saludo                 -> ejecutar saludo suave");
  Serial.println("stop                   -> detener coreografia y volver a home");
  Serial.println("s <id> <angulo>        -> mover servo (1..6) a un angulo");
  Serial.println("d <id> <delta>         -> mover servo relativo");
  Serial.println("homev <id> <angulo>    -> cambiar home del servo");
  Serial.println("range <id> <min> <max> -> cambiar limites del servo");
  Serial.println();
  Serial.println("Mapa de servos:");
  Serial.println("1 = base    -> PCA canal 0");
  Serial.println("2 = hombro  -> PCA canal 1");
  Serial.println("3 = codo    -> PCA canal 2");
  Serial.println("4 = muneca1 -> PCA canal 3");
  Serial.println("5 = muneca2 -> PCA canal 4");
  Serial.println("6 = garra   -> PCA canal 5");
  Serial.println();
}

float smootherStep(float t) {
  if (t <= 0.0f) return 0.0f;
  if (t >= 1.0f) return 1.0f;
  return t * t * t * (t * (t * 6.0f - 15.0f) + 10.0f);
}

void beginChoreoMove(uint8_t stepIndex) {
  choreoStep = stepIndex;
  choreoPhase = CHOREO_MOVING;
  choreoPhaseStart = millis();

  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    choreoStartAngles[i] = servos[i].current;
    servos[i].velocity = 0.0f;
  }
}

void startSaludo() {
  choreoActive = true;
  beginChoreoMove(0);
  Serial.println("OK -> saludo iniciado");
}

void stopChoreo() {
  choreoActive = false;
  choreoPhase = CHOREO_IDLE;
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    servos[i].velocity = 0.0f;
  }
  moveToHome();
  Serial.println("OK -> coreografia detenida, regresando a home");
}

void updateChoreo() {
  if (!choreoActive) return;

  unsigned long now = millis();

  if (choreoPhase == CHOREO_MOVING) {
    unsigned long moveMs = saludoPoses[choreoStep].moveMs;
    float t = 1.0f;

    if (moveMs > 0) {
      t = (float)(now - choreoPhaseStart) / (float)moveMs;
      if (t > 1.0f) t = 1.0f;
    }

    float e = smootherStep(t);

    for (uint8_t i = 0; i < SERVO_COUNT; i++) {
      float targetAngle = (float)saludoPoses[choreoStep].angles[i];
      targetAngle = clampFloat(targetAngle, servos[i].minAngle, servos[i].maxAngle);

      servos[i].current = choreoStartAngles[i] + (targetAngle - choreoStartAngles[i]) * e;
      servos[i].target = servos[i].current;
      writeServoAngleFloat(i, servos[i].current);
    }

    if (t >= 1.0f) {
      for (uint8_t i = 0; i < SERVO_COUNT; i++) {
        servos[i].current = clampFloat((float)saludoPoses[choreoStep].angles[i], servos[i].minAngle, servos[i].maxAngle);
        servos[i].target = servos[i].current;
        servos[i].velocity = 0.0f;
      }
      writeAllServosCurrent();
      choreoPhase = CHOREO_HOLDING;
      choreoPhaseStart = now;
    }
    return;
  }

  if (choreoPhase == CHOREO_HOLDING) {
    if (now - choreoPhaseStart >= saludoPoses[choreoStep].holdMs) {
      choreoStep++;

      if (choreoStep >= SALUDO_POSE_COUNT) {
        choreoActive = false;
        choreoPhase = CHOREO_IDLE;
        moveToHome();
        Serial.println("OK -> saludo terminado");
        return;
      }

      beginChoreoMove(choreoStep);
    }
  }
}

void updateSmoothMotion() {
  if (choreoActive) return;

  unsigned long now = millis();
  if (lastMotionUpdate == 0) {
    lastMotionUpdate = now;
    return;
  }

  if (now - lastMotionUpdate < MOTION_UPDATE_MS) return;

  float dt = (float)(now - lastMotionUpdate) / 1000.0f;
  lastMotionUpdate = now;

  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    float error = servos[i].target - servos[i].current;

    if (fabsf(error) < POSITION_EPS && fabsf(servos[i].velocity) < VELOCITY_EPS) {
      servos[i].current = servos[i].target;
      servos[i].velocity = 0.0f;
      writeServoAngleFloat(i, servos[i].current);
      continue;
    }

    float desiredVelocity = error * 4.2f;
    desiredVelocity = clampFloat(desiredVelocity, -MAX_SPEED_DEG_PER_SEC, MAX_SPEED_DEG_PER_SEC);

    float dv = desiredVelocity - servos[i].velocity;
    float maxDv = MAX_ACCEL_DEG_PER_SEC2 * dt;

    if (dv > maxDv) dv = maxDv;
    if (dv < -maxDv) dv = -maxDv;

    servos[i].velocity += dv;

    float nextPos = servos[i].current + servos[i].velocity * dt;

    if ((error > 0.0f && nextPos > servos[i].target) ||
        (error < 0.0f && nextPos < servos[i].target)) {
      nextPos = servos[i].target;
      servos[i].velocity = 0.0f;
    }

    servos[i].current = clampFloat(nextPos, servos[i].minAngle, servos[i].maxAngle);
    writeServoAngleFloat(i, servos[i].current);
  }
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (choreoActive && cmd != "stop" && cmd != "status" && cmd != "help") {
    Serial.println("ERROR: coreografia en progreso, usa 'stop' o espera a que termine");
    return;
  }

  if (cmd == "help") {
    printHelp();
    return;
  }

  if (cmd == "status") {
    printStatus();
    return;
  }

  if (cmd == "home") {
    moveToHome();
    Serial.println("OK -> home");
    return;
  }

  if (cmd == "saludo") {
    if (!choreoActive) {
      startSaludo();
    } else {
      Serial.println("ERROR: ya hay una coreografia en progreso");
    }
    return;
  }

  if (cmd == "stop") {
    stopChoreo();
    return;
  }

  if (cmd.startsWith("s ")) {
    int id, angle;
    if (sscanf(cmd.c_str(), "s %d %d", &id, &angle) == 2) {
      if (id >= 1 && id <= SERVO_COUNT) {
        setServoTarget(id - 1, (float)angle, true);
        Serial.println("OK");
      } else {
        Serial.println("ERROR: id invalido");
      }
    } else {
      Serial.println("ERROR: formato -> s <id> <angulo>");
    }
    return;
  }

  if (cmd.startsWith("d ")) {
    int id, delta;
    if (sscanf(cmd.c_str(), "d %d %d", &id, &delta) == 2) {
      if (id >= 1 && id <= SERVO_COUNT) {
        float t = servos[id - 1].target + (float)delta;
        setServoTarget(id - 1, t, true);
        Serial.println("OK");
      } else {
        Serial.println("ERROR: id invalido");
      }
    } else {
      Serial.println("ERROR: formato -> d <id> <delta>");
    }
    return;
  }

  if (cmd.startsWith("homev ")) {
    int id, angle;
    if (sscanf(cmd.c_str(), "homev %d %d", &id, &angle) == 2) {
      if (id >= 1 && id <= SERVO_COUNT) {
        servos[id - 1].home = clampInt(angle, servos[id - 1].minAngle, servos[id - 1].maxAngle);
        Serial.println("OK");
      } else {
        Serial.println("ERROR: id invalido");
      }
    } else {
      Serial.println("ERROR: formato -> homev <id> <angulo>");
    }
    return;
  }

  if (cmd.startsWith("range ")) {
    int id, minA, maxA;
    if (sscanf(cmd.c_str(), "range %d %d %d", &id, &minA, &maxA) == 3) {
      if (id >= 1 && id <= SERVO_COUNT && minA < maxA) {
        servos[id - 1].minAngle = minA;
        servos[id - 1].maxAngle = maxA;
        servos[id - 1].home = clampInt(servos[id - 1].home, minA, maxA);
        servos[id - 1].current = clampFloat(servos[id - 1].current, minA, maxA);
        servos[id - 1].target = clampFloat(servos[id - 1].target, minA, maxA);
        servos[id - 1].velocity = 0.0f;
        writeServoAngleFloat(id - 1, servos[id - 1].current);
        Serial.println("OK");
      } else {
        Serial.println("ERROR: rango invalido");
      }
    } else {
      Serial.println("ERROR: formato -> range <id> <min> <max>");
    }
    return;
  }

  Serial.println("ERROR: comando no reconocido");
}

void setup() {
  Serial.begin(115200);
  delay(500);

  Wire.begin(SDA_PIN, SCL_PIN);

  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(500);

  writeAllServosCurrent();

  Serial.println("Brazo robot listo.");
  printHelp();
  printStatus();
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputLine.length() > 0) {
        handleCommand(inputLine);
        inputLine = "";
      }
    } else {
      inputLine += c;
    }
  }

  updateSmoothMotion();
  updateChoreo();
}
