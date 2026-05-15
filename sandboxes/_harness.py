"""Plumbing comum dos sandboxes.

Inicializa pygame + janela OpenGL com a mesma configuração do main.py
(perspectiva, depth test, face culling, fundo azul claro) e roda um loop
genérico que chama as funções passadas pelo sandbox a cada frame.

Uso típico:

    from sandboxes._harness import run

    def draw(): ...
    def on_key(event): ...
    def on_mouse_motion(event): ...
    def setup_camera(): ...

    run(draw, on_key=on_key, on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera, title="Sandbox")
"""

from collections.abc import Callable

import pygame
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_MODELVIEW,
    GL_PROJECTION,
    glClear,
    glClearColor,
    glCullFace,
    glEnable,
    glLoadIdentity,
    glMatrixMode,
    glViewport,
)
from OpenGL.GLU import gluPerspective
from pygame.locals import DOUBLEBUF, OPENGL

DrawFn = Callable[[], None]
KeyFn = Callable[[pygame.event.Event], None]
MouseFn = Callable[[pygame.event.Event], None]


def run(
    draw_fn: DrawFn,
    *,
    on_key: KeyFn | None = None,
    on_mouse_motion: MouseFn | None = None,
    on_scroll: MouseFn | None = None,
    on_frame: DrawFn | None = None,
    setup_camera: DrawFn | None = None,
    title: str = "Sandbox",
    clear_color: tuple[float, float, float, float] = (0.2, 0.5, 0.8, 1.0),
    size: tuple[int, int] = (1920, 1080),
) -> None:
    width, height = size

    pygame.init()
    pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption(title)

    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width / height, 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glEnable(GL_DEPTH_TEST)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if on_key is not None and event.type == pygame.KEYDOWN:
                on_key(event)
            if on_mouse_motion is not None and event.type == pygame.MOUSEMOTION:
                on_mouse_motion(event)
            if on_scroll is not None and event.type == pygame.MOUSEWHEEL:
                on_scroll(event)

        glClearColor(*clear_color)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if on_frame is not None:
            on_frame()

        if setup_camera is not None:
            setup_camera()

        draw_fn()

        pygame.display.flip()
        pygame.time.wait(10)
