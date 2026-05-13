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
  ↑ / ↓           → câmera avança / recua
  ← / →           → câmera desloca lateralmente
  Mouse btn esq   → arrastar rotaciona câmera (yaw + pitch)

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_block
"""

import pygame
from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f

from sandboxes._harness import run
from src.entities.block import Block, PoweredBlock
from src.graphics.camera import Camera
from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size


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

    # Lista de um elemento para permitir troca por referência dentro dos closures.
    current: list[Block] = [block_common]

    camera = Camera(eye_x=0.0, eye_y=3.0, eye_z=5.0, yaw=180.0, pitch=-30.0)

    def setup_camera() -> None:
        camera.apply()

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
            return  # tecla não mapeada — não imprime estado

        _print_state(current[0])

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

    print("=== Sandbox Block ===")
    print("ESPAÇO=active | P=tipo | 1/2/3=cor | setas+mouse=câmera")
    _print_state(current[0])

    run(
        draw,
        on_key=on_key,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title="Sandbox: Block — ESPAÇO=active | P=tipo | 1/2/3=cor | setas+mouse=câmera",
    )


if __name__ == "__main__":
    main()
