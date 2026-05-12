"""Sandbox isolado para desenvolver e testar o Cube.

Controles:
  W / S           → cubo tomba para frente / trás  (+Z / −Z)
  A / D           → cubo tomba para esquerda / direita  (−X / +X)
  ↑ / ↓           → câmera avança / recua (dolly)
  ← / →           → câmera desloca lateralmente (strafe)
  Mouse btn esq   → arrastar rotaciona câmera (yaw + pitch)

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_cube
"""

import pygame
from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f

from sandboxes._harness import run
from src.entities.cube import Cube
from src.graphics.camera import Camera


def _draw_floor() -> None:
    """Chão de referência visual — apenas para o sandbox."""
    glBegin(GL_QUADS)
    glColor3f(0.25, 0.25, 0.25)
    glVertex3f(-10.0, 0.0, -10.0)
    glVertex3f( 10.0, 0.0, -10.0)
    glVertex3f( 10.0, 0.0,  10.0)
    glVertex3f(-10.0, 0.0,  10.0)
    glEnd()


def main() -> None:
    cube = Cube()  # centro em (0, 0.5, 0) — base no plano y=0

    # Câmera começa atrás/acima do cubo: yaw=180° olha para −Z (origem).
    camera = Camera(eye_x=0.0, eye_y=4.0, eye_z=6.0, yaw=180.0, pitch=-20.0)

    def setup_camera() -> None:
        camera.apply()

    def draw() -> None:
        _draw_floor()
        cube.update()
        cube.apply_transform()
        cube.draw()

    def on_key(event: pygame.event.Event) -> None:
        # Cubo — 4 direções de tombamento (por passo, não contínuo)
        if event.key == pygame.K_w:
            cube.start_roll(-1, axis='z')    # trás  (−Z)
        elif event.key == pygame.K_s:
            cube.start_roll(+1, axis='z')    # frente (+Z)
        elif event.key == pygame.K_a:
            cube.start_roll(-1, axis='x')    # esquerda (−X)
        elif event.key == pygame.K_d:
            cube.start_roll(+1, axis='x')    # direita  (+X)

    def on_frame() -> None:
        # Câmera — setas contínuas (consultadas a cada frame)
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
        # Rotaciona câmera apenas enquanto botão esquerdo está pressionado.
        if pygame.mouse.get_pressed()[0]:
            dx, dy = event.rel
            camera.rotate(
                dyaw=dx * Camera.MOUSE_SENSITIVITY,
                dpitch=-dy * Camera.MOUSE_SENSITIVITY,  # dy negado: baixo = olha para cima
            )

    run(
        draw,
        on_key=on_key,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title="Sandbox: Cube — WASD=cubo | setas+mouse=câmera",
    )


if __name__ == "__main__":
    main()
