"""Coleção de blocos que formam o terreno do jogo.

Map armazena blocos num dicionário esparso: a chave é (col, row) e o valor
é um Block (ou PoweredBlock). Células vazias simplesmente não existem no
dicionário — não ocupam memória nem são desenhadas.

Como montar um mapa
---------------------
    Opção 1 — mapa gerado proceduralmente (padrão 32×32):
        map_ = Map.generate()

    Opção 2 — mapa gerado com dimensões e seed personalizados:
        map_ = Map.generate(cols=24, rows=24, seed=42)

    Opção 3 — manualmente, célula a célula:
        map_ = Map()
        map_.add_block(Block(position=Position(0, 0, 0)), col=0, row=0)
        map_.add_block(PoweredBlock(power="speed", position=Position(1, 0, 0)), col=1, row=0)

Como acessar e modificar um bloco já no mapa
----------------------------------------------
    block = map_.get_block(col=5, row=3)   # None se a célula estiver vazia

    if block:
        block.active = False               # torna invisível sem remover do grid
        block.color = Color(1.0, 0.0, 0.0) # muda a cor em tempo real

    # Trocar o tipo (Block → PoweredBlock) na mesma célula:
    if block and not isinstance(block, PoweredBlock):
        map_.add_block(
            PoweredBlock(power="scale", position=block.position, color=block.color),
            col=5, row=3,
        )

    # Editar o poder de um PoweredBlock existente:
    if isinstance(block, PoweredBlock):
        block.power = "color"              # troca o efeito sem recriar o objeto

    # Remover um bloco:
    map_.remove_block(col=5, row=3)

Tipos de célula gerados
------------------------
    0 → vazio   (sem bloco no _grid)
    1 → caminho (Block, cor bege)
    2 → início  (Block, cor verde)  — posição inicial do Cube
    3 → fim     (Block, cor vermelha) — destino do Cube
"""

import random

from src.entities.block import Block
from src.graphics.color import Color
from src.graphics.position import Position

# Cores por tipo de célula — usadas pelo gerador e por add_block() manual.
_CELL_COLORS: dict[int, Color] = {
    1: Color(0.78, 0.59, 0.39),  # caminho — bege
    2: Color(0.20, 0.78, 0.20),  # início  — verde
    3: Color(0.78, 0.20, 0.20),  # fim     — vermelho
}


def _generate_matrix(cols: int, rows: int, rng: random.Random) -> list[list[int]]:
    """Gera uma matriz cols×rows com um caminho aleatório de largura ≥ 2.

    Algoritmo — Random Walk com largura dupla:
    1. Sorteia orientação: Norte→Sul (percorre linhas) ou Leste→Oeste (percorre colunas).
    2. Escolhe posição aleatória de início em uma borda e fim na borda oposta.
    3. Drunk walk do início ao fim:
       - 70% de chance de avançar na direção principal a cada passo.
       - 30% de chance de desviar lateralmente (nunca recua, respeita bordas).
    4. set_cell() preenche sempre duas células paralelas — garante largura ≥ 2.
    5. Segmento reto final conecta o walk ao ponto exato de fim.
    6. Células de início e fim recebem tipos 2 e 3 respectivamente.
    """
    grid: list[list[int]] = [[0] * cols for _ in range(rows)]

    # True = walk percorre eixo Z (Norte→Sul); False = eixo X (Leste→Oeste).
    vertical = rng.choice([True, False])

    if vertical:
        main_len, cross_len = rows, cols
        start_cross = rng.randint(0, cross_len - 2)
        end_cross   = rng.randint(0, cross_len - 2)

        def set_cell(main: int, cross: int, value: int) -> None:
            grid[main][cross]     = value
            grid[main][cross + 1] = value

    else:
        main_len, cross_len = cols, rows
        start_cross = rng.randint(0, cross_len - 2)
        end_cross   = rng.randint(0, cross_len - 2)

        def set_cell(main: int, cross: int, value: int) -> None:  # type: ignore[misc]
            grid[cross][main]     = value
            grid[cross + 1][main] = value

    cross = start_cross
    for main in range(main_len):
        set_cell(main, cross, 1)

        remaining = (main_len - 1) - main
        if remaining == 0:
            break

        # Nos últimos 2 passos não desvia — garante espaço para o segmento de fechamento.
        if remaining > 2 and rng.random() < 0.30:
            direction = rng.choice([-1, 1])
            new_cross = cross + direction
            if 0 <= new_cross <= cross_len - 2:
                cross = new_cross

    # Fecha lateralmente até end_cross na última linha/coluna.
    step = 1 if end_cross > cross else -1
    while cross != end_cross:
        cross += step
        set_cell(main_len - 1, cross, 1)

    # Sobrescreve início e fim com seus tipos.
    set_cell(0,           start_cross, 2)
    set_cell(main_len - 1, end_cross,  3)

    return grid


def _matrix_to_map(matrix: list[list[int]]) -> "Map":
    """Converte uma matriz de inteiros num Map populado com Blocks."""
    m = Map()
    for row_idx, row in enumerate(matrix):
        for col_idx, cell in enumerate(row):
            template = _CELL_COLORS.get(cell)
            if template is None:
                continue
            pos   = Position(x=float(col_idx), y=0.0, z=float(row_idx))
            # Instância nova de Color por bloco — edições isoladas entre células.
            color = Color(template.r, template.g, template.b)
            m.add_block(Block(position=pos, color=color), col=col_idx, row=row_idx)
    return m


class Map:
    DEFAULT_COLS: int = 32
    DEFAULT_ROWS: int = 32

    def __init__(self) -> None:
        # Dicionário esparso: só células ocupadas existem aqui.
        # Chave: (col, row) — inteiros de grade, não coordenadas de mundo.
        self._grid: dict[tuple[int, int], Block] = {}

    def add_block(self, block: Block, col: int, row: int) -> None:
        """Registra um bloco na célula (col, row). Substitui se já existir."""
        self._grid[(col, row)] = block

    def get_block(self, col: int, row: int) -> Block | None:
        # Retorna None para célula vazia — verifique antes de acessar .power ou .active.
        return self._grid.get((col, row))

    def remove_block(self, col: int, row: int) -> None:
        """Remove o bloco da célula (col, row), se houver."""
        self._grid.pop((col, row), None)

    def draw(self) -> None:
        # Delega para cada bloco — blocos com active=False se ignoram sozinhos.
        for block in self._grid.values():
            block.draw()

    @classmethod
    def generate(
        cls,
        cols: int = DEFAULT_COLS,
        rows: int = DEFAULT_ROWS,
        seed: int | None = None,
    ) -> "Map":
        """Gera um mapa procedural com caminho aleatório de largura ≥ 2.

        O início fica em uma borda e o fim na borda oposta. O caminho é
        contínuo — sem fendas — garantindo que o Cube consiga atravessá-lo.

        Args:
            cols: largura do grid em células (padrão: 32).
            rows: altura do grid em células (padrão: 32).
            seed: semente do RNG. None = diferente a cada chamada.
                  Inteiro fixo = mesmo mapa sempre (útil para testes).
        """
        rng = random.Random(seed)
        matrix = _generate_matrix(cols, rows, rng)
        return _matrix_to_map(matrix)
