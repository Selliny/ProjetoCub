"""Sandbox isolado para desenvolver e testar o Map.

Exibe um Map com 8 blocos de teste: 6 blocos comuns (cinza) e 2
PoweredBlocks (amarelo ouro). Permite validar geometria, herança e
layout do grid independente do Cube.

Controles:
  ↑ / ↓           → câmera avança / recua (dolly)
  ← / →           → câmera desloca lateralmente (strafe)
  Mouse btn esq   → arrastar rotaciona câmera (yaw + pitch)

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_map
"""

import pygame
from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f

from sandboxes._harness import run
from src.entities.block import Block, PoweredBlock
from src.graphics.camera import Camera
from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size
from src.world.map import Map


def _draw_floor() -> None:
    glBegin(GL_QUADS)
    glColor3f(0.2, 0.2, 0.2)
    glVertex3f(-20.0, -0.1, -20.0)
    glVertex3f( 20.0, -0.1, -20.0)
    glVertex3f( 20.0, -0.1,  20.0)
    glVertex3f(-20.0, -0.1,  20.0)
    glEnd()


def _build_map() -> Map:
    """Monta o Map com 8 blocos de teste.

    Layout no grid (col, row):
      Blocos comuns cinza : (0,0) (1,0) (2,0) (3,0) (0,1) (3,1)
      PoweredBlock amarelo: (4,1) (2,2)
    """
    map_ = Map()
    gray = Color(0.55, 0.55, 0.55)
    gold = Color(1.0, 0.75, 0.0)
    block_size = Size(1.0, 0.2, 1.0)

    common_cells = [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (3, 1)]
    for col, row in common_cells:
        map_.add_block(
            Block(
                position=Position(col * 1.0, 0.0, row * 1.0),
                color=gray,
                size=block_size,
            ),
            col, row,
        )

    powered_cells = [(4, 1), (2, 2)]
    for col, row in powered_cells:
        map_.add_block(
            PoweredBlock(
                power="scale",
                position=Position(col * 1.0, 0.0, row * 1.0),
                color=gold,
                size=block_size,
            ),
            col, row,
        )

    return map_


def main() -> None:
    map_ = _build_map()
    camera = Camera(eye_x=2.0, eye_y=6.0, eye_z=10.0, yaw=190.0, pitch=-30.0)

    def setup_camera() -> None:
        camera.apply()

    def draw() -> None:
        _draw_floor()
        map_.draw()

    def on_frame() -> None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            camera.move_forward(+Camera.MOVE_STEP)
        if keys[pygame.K_DOWN]:
            camera.move_forward(-Camera.MOVE_STEP)
        if keys[pygame.K_LEFT]:
            camera.strafe(+Camera.MOVE_STEP)
        if keys[pygame.K_RIGHT]:
            camera.strafe(-Camera.MOVE_STEP)

    def on_mouse_motion(event: pygame.event.Event) -> None:
        if pygame.mouse.get_pressed()[0]:
            dx, dy = event.rel
            camera.rotate(
                dyaw=dx * Camera.MOUSE_SENSITIVITY,
                dpitch=-dy * Camera.MOUSE_SENSITIVITY,
            )

    run(
        draw,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title="Sandbox: Map — 8 blocos (cinza=comum, ouro=powered) | setas+mouse=câmera",
    )


if __name__ == "__main__":
    main()
