"""Sandbox isolado para desenvolver e testar o Cube.

Roda só o cubo em fundo vazio, com o InputHandler ligado para validar
movimentação/rotação/escala via teclado. Não depende de Map, Block ou
Scene — útil para desenvolver `src/entities/cube.py` em paralelo.

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_cube
"""

from types import SimpleNamespace

from OpenGL.GL import glRotatef

from sandboxes._harness import run
from src.entities.cube import Cube
from src.input.handler import InputHandler


def main() -> None:
    cube = Cube()
    handler = InputHandler()
    fake_scene = SimpleNamespace(cube=cube)

    def draw() -> None:
        cube.position.apply()
        glRotatef(cube.angle, 0.0, 1.0, 0.0)
        cube.size.apply()
        cube.color.apply()
        cube.draw()

    def on_key(event) -> None:
        handler.handle(event, fake_scene)

    run(draw, on_key=on_key, title="Sandbox: Cube")


if __name__ == "__main__":
    main()
