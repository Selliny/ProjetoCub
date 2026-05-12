"""Câmera livre: entidade de CG com posição + yaw/pitch.

Modelo esférico padrão de câmera 3D:
  - yaw   → rotação horizontal (em torno do eixo Y)
  - pitch → elevação (em torno do eixo X), clampado em ±89°

WASD movem o eye no plano XZ; mouse (drag) rotaciona yaw/pitch.
Nenhuma transformação de escala ou posição de objetos é afetada aqui —
a câmera só configura a MODELVIEW matrix via gluLookAt.
"""

import math

from OpenGL.GLU import gluLookAt


class Camera:
    MOVE_STEP: float = 0.3        # unidades por pressionamento de tecla
    MOUSE_SENSITIVITY: float = 0.3  # graus por pixel de deslocamento do mouse

    def __init__(
        self,
        eye_x: float = 0.0,
        eye_y: float = 4.0,
        eye_z: float = 6.0,
        yaw: float = 180.0,
        pitch: float = -20.0,
    ) -> None:
        self.eye_x = eye_x
        self.eye_y = eye_y
        self.eye_z = eye_z
        self.yaw = yaw      # graus — 180° = olhando para −Z (origem)
        self.pitch = pitch  # graus — negativo = olhando levemente para baixo

    # ------------------------------------------------------------------
    # Movimento
    # ------------------------------------------------------------------

    def move_forward(self, d: float) -> None:
        """Avança/recua na direção horizontal do yaw (sem mudar altura)."""
        rad = math.radians(self.yaw)
        self.eye_x += d * math.sin(rad)
        self.eye_z += d * math.cos(rad)

    def strafe(self, d: float) -> None:
        """Desloca lateralmente, perpendicular ao yaw no plano XZ."""
        rad = math.radians(self.yaw)
        self.eye_x += d * math.cos(rad)
        self.eye_z -= d * math.sin(rad)

    def rotate(self, dyaw: float, dpitch: float) -> None:
        """Rotaciona a câmera. Clamp pitch em ±89° para evitar gimbal flip."""
        self.yaw = (self.yaw + dyaw) % 360.0
        self.pitch = max(-89.0, min(89.0, self.pitch - dpitch))

    # ------------------------------------------------------------------
    # Aplicação OpenGL
    # ------------------------------------------------------------------

    def apply(self) -> None:
        """Aplica gluLookAt na MODELVIEW matrix. Chamar após glLoadIdentity()."""
        yaw_r = math.radians(self.yaw)
        pitch_r = math.radians(self.pitch)

        fx = math.cos(pitch_r) * math.sin(yaw_r)
        fy = math.sin(pitch_r)
        fz = math.cos(pitch_r) * math.cos(yaw_r)

        gluLookAt(
            self.eye_x, self.eye_y, self.eye_z,
            self.eye_x + fx, self.eye_y + fy, self.eye_z + fz,
            0.0, 1.0, 0.0,
        )
