"""Orquestrador do jogo.

Mantém o fluxo OpenGL definido pelo padrão do professor (inicialização +
loop com glClearColor / glLoadIdentity / display.flip), porém sem
variáveis globais: estado e desenho são delegados a Scene, Cube e
InputHandler (POO).
"""

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

from src.input.handler import InputHandler
from src.world.scene import Scene


def main() -> None:
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    glViewport(0, 0, 800, 600)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (800 / 600), 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glEnable(GL_DEPTH_TEST)

    scene = Scene()
    input_handler = InputHandler()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            input_handler.handle(event, scene)

        glClearColor(0.2, 0.5, 0.8, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        scene.draw()

        pygame.display.flip()
        pygame.time.wait(10)


if __name__ == "__main__":
    main()
