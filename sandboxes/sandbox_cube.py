"""Sandbox isolado para desenvolver e testar o Cube.

Controles:
  W / S           → cubo tomba para trás / frente  (−Z / +Z)
  A / D           → cubo tomba para esquerda / direita  (−X / +X)
  ↑ / ↓           → aproxima / afasta a câmera do cubo
  ← / →           → orbita a câmera ao redor do cubo
  Q / E           → sobe / desce a câmera
  Mouse btn esq   → arrastar orbita e ajusta altura

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_cube
"""

import pygame
from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f
from OpenGL.GLU import gluLookAt

from sandboxes._harness import run
from src.entities.cube import Cube, CubeState

HOLES = {(2, 0), (2, 1), (-2, -1), (0, -3)}
CAMERA_MIN_HEIGHT = 2.0
CAMERA_MAX_HEIGHT = 14.0
CAMERA_MIN_DISTANCE = 4.0
CAMERA_MAX_DISTANCE = 18.0
CAMERA_ORBIT_STEP = 2.5
CAMERA_DISTANCE_STEP = 0.25
CAMERA_HEIGHT_STEP = 0.18
CAMERA_MOUSE_SENSITIVITY = 0.25
CAMERA_FOLLOW_SMOOTHING = 8.0

CUBE_KEYS = {
    pygame.K_w: (0, -1),
    pygame.K_s: (0, +1),
    pygame.K_a: (-1, 0),
    pygame.K_d: (+1, 0),
}


class SandboxBounds:
    """Validador temporário que simula limites e buracos sem usar o mapa real."""

    def __init__(
        self,
        min_x: int,
        max_x: int,
        min_z: int,
        max_z: int,
        holes: set[tuple[int, int]],
    ) -> None:
        self._min_x = min_x
        self._max_x = max_x
        self._min_z = min_z
        self._max_z = max_z
        self._holes = holes

    def can_move_to(self, grid_x: int, grid_z: int) -> bool:
        """Verifica se a célula está dentro do retângulo visual do sandbox."""
        return (
            self._min_x <= grid_x <= self._max_x
            and self._min_z <= grid_z <= self._max_z
        )

    def get_tile_type(self, grid_x: int, grid_z: int) -> str:
        """Classifica a célula como floor, hole ou empty para testar estados."""
        if (grid_x, grid_z) in self._holes:
            return "hole"
        return "floor" if self.can_move_to(grid_x, grid_z) else "empty"


def _draw_floor() -> None:
    """Desenha o chão em tiles e omite as células marcadas como buraco."""
    glBegin(GL_QUADS)
    for x in range(-10, 10):
        for z in range(-10, 10):
            if (x, z) in HOLES:
                continue

            glColor3f(0.25, 0.25, 0.25)
            glVertex3f(float(x),     0.0, float(z))
            glVertex3f(float(x + 1), 0.0, float(z))
            glVertex3f(float(x + 1), 0.0, float(z + 1))
            glVertex3f(float(x),     0.0, float(z + 1))
    glEnd()


def main() -> None:
    """Monta o sandbox: cubo, validador, câmera orbital e loop de teste."""
    cube = Cube()  # centro em (0, 0.5, 0) — base no plano y=0
    validator = SandboxBounds(
        min_x=-9,
        max_x=9,
        min_z=-9,
        max_z=9,
        holes=HOLES,
    )
    last_frame_ms: list[int | None] = [None]
    last_state: list[CubeState | None] = [None]
    last_respawn_second: list[int | None] = [None]
    camera_yaw: list[float] = [180.0]
    camera_height: list[float] = [7.0]
    camera_distance: list[float] = [9.0]
    camera_eye = pygame.math.Vector3(0.0, 7.0, 9.0)
    camera_target = pygame.math.Vector3(0.0, 0.0, 0.0)

    def _clamp_camera() -> None:
        """Mantém altura e distância da câmera dentro de limites confortáveis."""
        camera_height[0] = max(
            CAMERA_MIN_HEIGHT,
            min(CAMERA_MAX_HEIGHT, camera_height[0]),
        )
        camera_distance[0] = max(
            CAMERA_MIN_DISTANCE,
            min(CAMERA_MAX_DISTANCE, camera_distance[0]),
        )

    def setup_camera() -> None:
        """Aplica a câmera orbital suavizada, sempre olhando para o cubo."""
        gluLookAt(
            camera_eye.x,
            camera_eye.y,
            camera_eye.z,
            camera_target.x,
            camera_target.y,
            camera_target.z,
            0.0,
            1.0,
            0.0,
        )

    def draw() -> None:
        """Desenha o chão e depois o cubo com a transformação atual."""
        _draw_floor()
        cube.apply_transform()
        cube.draw()

    def on_frame() -> None:
        """Atualiza tempo, cubo, logs, input contínuo e suavização da câmera."""
        now_ms = pygame.time.get_ticks()
        if last_frame_ms[0] is None:
            dt = 1.0 / 60.0
        else:
            dt = (now_ms - last_frame_ms[0]) / 1000.0
        last_frame_ms[0] = now_ms

        cube.update(dt)
        if cube.state is not last_state[0]:
            print(f"[Cube] state={cube.state.value} grid={cube.get_grid_position()}")
            last_state[0] = cube.state
            last_respawn_second[0] = None

        if cube.state == CubeState.FADING_OUT:
            remaining = int(cube.get_respawn_remaining() + 0.999)
            if remaining != last_respawn_second[0]:
                print(f"[Cube] respawn em {remaining}s")
                last_respawn_second[0] = remaining

        keys = pygame.key.get_pressed()

        # Cubo — movimento contínuo enquanto W/A/S/D estiver pressionado.
        if not cube.is_moving():
            for key, direction in CUBE_KEYS.items():
                if keys[key]:
                    cube.try_roll(*direction, validator=validator)
                    break

        # Câmera — controles orbitais, sempre ancorados no cubo.
        if keys[pygame.K_LEFT]:
            camera_yaw[0] += CAMERA_ORBIT_STEP
        if keys[pygame.K_RIGHT]:
            camera_yaw[0] -= CAMERA_ORBIT_STEP
        if keys[pygame.K_UP]:
            camera_distance[0] -= CAMERA_DISTANCE_STEP
        if keys[pygame.K_DOWN]:
            camera_distance[0] += CAMERA_DISTANCE_STEP
        if keys[pygame.K_q]:
            camera_height[0] += CAMERA_HEIGHT_STEP
        if keys[pygame.K_e]:
            camera_height[0] -= CAMERA_HEIGHT_STEP
        _clamp_camera()

        yaw = pygame.math.Vector2(0.0, 1.0).rotate(camera_yaw[0])
        desired_target = pygame.math.Vector3(cube.position.x, 0.0, cube.position.z)
        desired_eye = pygame.math.Vector3(
            desired_target.x + yaw.x * camera_distance[0],
            camera_height[0],
            desired_target.z + yaw.y * camera_distance[0],
        )
        blend = min(1.0, CAMERA_FOLLOW_SMOOTHING * dt)
        camera_target.update(camera_target.lerp(desired_target, blend))
        camera_eye.update(camera_eye.lerp(desired_eye, blend))

    def on_mouse_motion(event: pygame.event.Event) -> None:
        """Arrastar com botão esquerdo orbita a câmera e ajusta sua altura."""
        if not pygame.mouse.get_pressed()[0]:
            return

        dx, dy = event.rel
        camera_yaw[0] -= dx * CAMERA_MOUSE_SENSITIVITY
        camera_height[0] -= dy * CAMERA_HEIGHT_STEP
        _clamp_camera()

    run(
        draw,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title="Sandbox: Cube — WASD=cubo | setas+mouse=câmera orbital",
    )


if __name__ == "__main__":
    main()
