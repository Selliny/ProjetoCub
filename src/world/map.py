"""Coleção de blocos que formam o terreno do jogo.

O mapa é estruturado como um grid 16×16. Cada célula é identificada
por (col, row) e armazena um Block (ou subclasse). Células vazias
simplesmente não existem no dicionário — não há bloco lá.
"""

from src.entities.block import Block


class Map:
    COLS: int = 16
    ROWS: int = 16

    def __init__(self) -> None:
        self._grid: dict[tuple[int, int], Block] = {}

    def add_block(self, block: Block, col: int, row: int) -> None:
        """Registra um bloco na célula (col, row) do grid."""
        self._grid[(col, row)] = block

    def get_block(self, col: int, row: int) -> Block | None:
        return self._grid.get((col, row))

    def draw(self) -> None:
        for block in self._grid.values():
            block.draw()
