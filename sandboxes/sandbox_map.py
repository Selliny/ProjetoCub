"""Sandbox isolado para desenvolver e testar o Map.

Popula um Map com alguns blocos de exemplo dispostos em grade e chama
`map.draw()` no loop. Permite validar iteração e layout do mapa
independente do desenho real do Block — quando `Block.draw()` ainda
estiver vazio, a tela aparece azul mas o sandbox prova que `Map.draw()`
itera sem erro.

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_map
"""

from OpenGL.GL import glLoadIdentity

from sandboxes._harness import run
from src.entities.block import Block
from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size
from src.world.map import Map


def _grade_de_blocos(linhas: int = 3, colunas: int = 3, espacamento: float = 2.0) -> list[Block]:
    blocos: list[Block] = []
    offset_x = -(colunas - 1) * espacamento / 2
    offset_y = -(linhas - 1) * espacamento / 2
    for i in range(linhas):
        for j in range(colunas):
            blocos.append(
                Block(
                    position=Position(
                        offset_x + j * espacamento,
                        offset_y + i * espacamento,
                        -15.0,
                    ),
                    color=Color(0.4 + 0.1 * j, 0.4 + 0.1 * i, 0.6),
                    size=Size.uniform(0.8),
                )
            )
    return blocos


def main() -> None:
    map_ = Map(blocks=_grade_de_blocos())

    def draw() -> None:
        for block in map_.blocks:
            glLoadIdentity()
            block.position.apply()
            block.size.apply()
            block.color.apply()
            block.draw()

    run(draw, title="Sandbox: Map (grade 3x3 de blocos)")


if __name__ == "__main__":
    main()
