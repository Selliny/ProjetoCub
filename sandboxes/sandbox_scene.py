"""Sandbox isolado para desenvolver e testar a Scene completa.

Instancia uma Scene padrão e chama `scene.draw()` no loop. Praticamente
igual ao main.py, mas sem o InputHandler — útil para iterar
rapidamente em mudanças na agregação de Cube + Map sem depender da
entrada de teclado.

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_scene
"""

from sandboxes._harness import run
from src.world.scene import Scene


def main() -> None:
    scene = Scene()

    def draw() -> None:
        scene.draw()

    run(draw, title="Sandbox: Scene")


if __name__ == "__main__":
    main()
