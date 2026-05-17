"""Sandbox isolado para desenvolver e testar Block e PoweredBlock.

Permite testar interativamente: geometria visual, flag active, troca entre
Block comum e PoweredBlock, e mudança de cor em tempo real. O estado atual
do bloco é impresso no console a cada mudança de tecla.

Controles:
  ESPAÇO          → alterna block.active (bloco some/aparece)
  P               → alterna entre Block comum e PoweredBlock
  1               → cor cinza (Block padrão)
  2               → cor amarelo ouro (PoweredBlock visual)
  3               → cor vermelha
  ↑ / ↓           → aproxima / afasta a câmera
  ← / →           → orbita a câmera ao redor do bloco
  Q / E           → sobe / desce a câmera
  Mouse btn esq   → arrastar orbita e ajusta altura

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_block
"""

import pygame
from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f
from OpenGL.GLU import gluLookAt

from sandboxes._harness import run
from src.entities.block import Block, PoweredBlock
from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size

CAMERA_MIN_HEIGHT = 1.0
CAMERA_MAX_HEIGHT = 10.0
CAMERA_MIN_DISTANCE = 2.0
CAMERA_MAX_DISTANCE = 12.0
CAMERA_ORBIT_STEP = 2.5
CAMERA_DISTANCE_STEP = 0.25
CAMERA_HEIGHT_STEP = 0.18
CAMERA_MOUSE_SENSITIVITY = 0.25
CAMERA_FOLLOW_SMOOTHING = 8.0


def _draw_floor() -> None:
    glBegin(GL_QUADS)
    glColor3f(0.2, 0.2, 0.2)
    glVertex3f(-10.0, -0.01, -10.0)
    glVertex3f( 10.0, -0.01, -10.0)
    glVertex3f( 10.0, -0.01,  10.0)
    glVertex3f(-10.0, -0.01,  10.0)
    glEnd()


def _print_state(block: Block) -> None:
    kind = type(block).__name__
    power = getattr(block, "power", "—")
    print(
        f"[Block] tipo={kind} | active={block.active} "
        f"| is_powered={block.is_powered} | power={power} "
        f"| cor=({block.color.r:.2f}, {block.color.g:.2f}, {block.color.b:.2f})"
    )


def main() -> None:
    block_size = Size(1.0, 0.1, 1.0)
    origin = Position(0.0, 0.0, 0.0)

    block_common = Block(
        position=origin,
        color=Color(0.55, 0.55, 0.55),
        size=block_size,
    )
    block_powered = PoweredBlock(
        power="scale",
        position=origin,
        color=Color(1.0, 0.75, 0.0),
        size=block_size,
    )

    current: list[Block] = [block_common]

    last_frame_ms: list[int | None] = [None]
    camera_yaw: list[float] = [180.0]
    camera_height: list[float] = [4.0]
    camera_distance: list[float] = [6.0]
    camera_eye = pygame.math.Vector3(0.0, 4.0, 6.0)
    camera_target = pygame.math.Vector3(0.0, 0.0, 0.0)

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
        _draw_floor()
        current[0].draw()

    def on_key(event: pygame.event.Event) -> None:
        if event.key == pygame.K_SPACE:
            current[0].active = not current[0].active

        elif event.key == pygame.K_p:
            current[0] = (
                block_powered if current[0] is block_common else block_common
            )

        elif event.key == pygame.K_1:
            current[0].color = Color(0.55, 0.55, 0.55)

        elif event.key == pygame.K_2:
            current[0].color = Color(1.0, 0.75, 0.0)

        elif event.key == pygame.K_3:
            current[0].color = Color(0.9, 0.2, 0.2)

        else:
            return

        _print_state(current[0])

    def on_frame() -> None:
        now_ms = pygame.time.get_ticks()
        if last_frame_ms[0] is None:
            dt = 1.0 / 60.0
        else:
            dt = (now_ms - last_frame_ms[0]) / 1000.0
        last_frame_ms[0] = now_ms

        keys = pygame.key.get_pressed()
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
        desired_target = pygame.math.Vector3(0.0, 0.0, 0.0)
        desired_eye = pygame.math.Vector3(
            yaw.x * camera_distance[0],
            camera_height[0],
            yaw.y * camera_distance[0],
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

    print("=== Sandbox Block ===")
    print("ESPAÇO=active | P=tipo | 1/2/3=cor | setas+mouse=câmera orbital")
    _print_state(current[0])

    run(
        draw,
        on_key=on_key,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title="Sandbox: Block — ESPAÇO=active | P=tipo | 1/2/3=cor | setas+mouse=câmera orbital",
    )


if __name__ == "__main__":
    main()
