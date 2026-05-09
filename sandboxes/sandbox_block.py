"""Sandbox isolado para desenvolver e testar o Block.

Coloca um único bloco em posição fixa no centro da câmera. A barra de
espaço alterna `block.active` para validar que `Block.draw()` respeita o
flag (bloco desaparece quando inativo).

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_block
"""

import pygame

from sandboxes._harness import run
from src.entities.block import Block
from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size


def main() -> None:
    block = Block(
        position=Position(0.0, 0.0, -10.0),
        color=Color(0.2, 0.8, 0.3),
        size=Size.uniform(1.0),
    )

    def draw() -> None:
        block.position.apply()
        block.size.apply()
        block.color.apply()
        block.draw()

    def on_key(event) -> None:
        if event.key == pygame.K_SPACE:
            block.active = not block.active

    run(draw, on_key=on_key, title="Sandbox: Block (espaço alterna active)")


if __name__ == "__main__":
    main()
