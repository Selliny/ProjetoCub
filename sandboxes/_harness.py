"""Plumbing comum dos sandboxes.

Inicializa pygame + janela OpenGL com a mesma configuração do main.py
(perspectiva, depth test, fundo azul claro) e roda um loop genérico que
chama uma função de desenho passada pelo sandbox a cada frame.

Uso típico:

    from sandboxes._harness import run

    def draw():
        ...

    def on_key(event):
        ...

    run(draw, on_key=on_key, title="Sandbox: Cube")
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
    glEnable,
    glLoadIdentity,
    glMatrixMode,
    glViewport,
)
from OpenGL.GLU import gluPerspective
from pygame.locals import DOUBLEBUF, OPENGL

DrawFn = Callable[[], None]
KeyFn = Callable[[pygame.event.Event], None]


def run(
    draw_fn: DrawFn,
    *,
    on_key: KeyFn | None = None,
    title: str = "Sandbox",
    clear_color: tuple[float, float, float, float] = (0.2, 0.5, 0.8, 1.0),
    size: tuple[int, int] = (800, 600),
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

        glClearColor(*clear_color)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        draw_fn()

        pygame.display.flip()
        pygame.time.wait(10)
