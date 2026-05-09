"""Despacho de eventos de teclado para métodos de Scene/Cube.

Substitui o bloco `if event.key == K_LEFT: ...` procedural do esqueleto
do professor por uma classe que delega para os objetos da cena.
"""

import pygame

from src.world.scene import Scene


class InputHandler:
    def handle(self, event: pygame.event.Event, scene: Scene) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_LEFT:
            pass  # TODO: scene.cube.move(-dx, 0, 0)
        elif event.key == pygame.K_RIGHT:
            pass  # TODO: scene.cube.move(+dx, 0, 0)
        elif event.key == pygame.K_UP:
            pass  # TODO: scene.cube.move(0, +dy, 0)  ou eixo Z, conforme o jogo
        elif event.key == pygame.K_DOWN:
            pass  # TODO: scene.cube.move(0, -dy, 0)
        elif event.key == pygame.K_r:
            pass  # TODO: scene.cube.rotate(d_angle)
