"""Sandbox integrado: Cube caminhando sobre um Map real gerado proceduralmente.

Controles:
  W / S           → cubo tomba para trás / frente  (−Z / +Z)
  A / D           → cubo tomba para esquerda / direita  (−X / +X)
  G               → gera novo mapa procedural (cubo volta ao início)
  ↑ / ↓           → aproxima / afasta a câmera do cubo
  ← / →           → orbita a câmera ao redor do cubo
  Q / E           → sobe / desce a câmera
  Mouse btn esq   → arrastar orbita e ajusta altura

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_cube
"""

import pygame
from OpenGL.GLU import gluLookAt

from sandboxes._harness import run
from src.entities.cube import Cube, CubeState
from src.graphics.position import Position
from src.world.map import Map

CAMERA_MIN_HEIGHT = 2.0
CAMERA_MAX_HEIGHT = 20.0
CAMERA_MIN_DISTANCE = 4.0
CAMERA_MAX_DISTANCE = 24.0
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


def _make_cube(map_: Map) -> Cube:
    col, row = map_.start
    return Cube(position=Position(float(col), 0.5, float(row)))


def main() -> None:
    map_: list[Map] = [Map.generate()]
    cube: list[Cube] = [_make_cube(map_[0])]

    last_frame_ms: list[int | None] = [None]
    last_state: list[CubeState | None] = [None]
    # yaw=0°: câmera posicionada em +Z relativo ao cubo, olhando para -Z.
    # W move dz=-1 (-Z), que é "para frente" na tela — alinhado com o caminho.
    camera_yaw: list[float] = [0.0]
    camera_height: list[float] = [9.0]
    camera_distance: list[float] = [12.0]

    start_col, start_row = map_[0].start
    camera_eye = pygame.math.Vector3(float(start_col), 9.0, float(start_row) + 12.0)
    camera_target = pygame.math.Vector3(float(start_col), 0.0, float(start_row))

    def _clamp_camera() -> None:
        camera_height[0] = max(CAMERA_MIN_HEIGHT, min(CAMERA_MAX_HEIGHT, camera_height[0]))
        camera_distance[0] = max(CAMERA_MIN_DISTANCE, min(CAMERA_MAX_DISTANCE, camera_distance[0]))

    def setup_camera() -> None:
        gluLookAt(
            camera_eye.x, camera_eye.y, camera_eye.z,
            camera_target.x, camera_target.y, camera_target.z,
            0.0, 1.0, 0.0,
        )

    def draw() -> None:
        map_[0].draw()
        cube[0].apply_transform()
        cube[0].draw()

    def on_key(event: pygame.event.Event) -> None:
        if event.key == pygame.K_g:
            map_[0] = Map.generate()
            cube[0] = _make_cube(map_[0])
            last_state[0] = None
            print(f"[Map] novo mapa gerado — início em {map_[0].start}")

    def on_frame() -> None:
        now_ms = pygame.time.get_ticks()
        if last_frame_ms[0] is None:
            dt = 1.0 / 60.0
        else:
            dt = (now_ms - last_frame_ms[0]) / 1000.0
        last_frame_ms[0] = now_ms

        c = cube[0]
        c.update(dt)

        if c.state is not last_state[0]:
            print(f"[Cube] state={c.state.value} grid={c.get_grid_position()}")
            last_state[0] = c.state

        keys = pygame.key.get_pressed()

        if not c.is_moving():
            for key, direction in CUBE_KEYS.items():
                if keys[key]:
                    c.try_roll(*direction, validator=map_[0])
                    break

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
        desired_target = pygame.math.Vector3(c.position.x, 0.0, c.position.z)
        desired_eye = pygame.math.Vector3(
            desired_target.x + yaw.x * camera_distance[0],
            camera_height[0],
            desired_target.z + yaw.y * camera_distance[0],
        )
        blend = min(1.0, CAMERA_FOLLOW_SMOOTHING * dt)
        camera_target.update(camera_target.lerp(desired_target, blend))
        camera_eye.update(camera_eye.lerp(desired_eye, blend))

    def on_mouse_motion(event: pygame.event.Event) -> None:
        if not pygame.mouse.get_pressed()[0]:
            return
        dx, dy = event.rel
        camera_yaw[0] -= dx * CAMERA_MOUSE_SENSITIVITY
        camera_height[0] -= dy * CAMERA_HEIGHT_STEP
        _clamp_camera()

    print(f"=== Sandbox Cube ===")
    print(f"WASD=mover | G=novo mapa | setas+mouse=câmera orbital")
    print(f"Mapa gerado — início em {map_[0].start}")

    run(
        draw,
        on_key=on_key,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title="Sandbox: Cube+Map — WASD=mover | G=novo mapa | setas+mouse=câmera",
    )


if __name__ == "__main__":
    main()
