"""Coleção de blocos que formam o terreno do jogo."""

from src.entities.block import Block


class Map:
    def __init__(self, blocks: list[Block] | None = None) -> None:
        self.blocks: list[Block] = blocks if blocks is not None else []

    def add_block(self, block: Block) -> None:
        self.blocks.append(block)

    def draw(self) -> None:
        for block in self.blocks:
            block.draw()
