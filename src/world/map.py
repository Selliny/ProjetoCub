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

from src.entities.block import Block, PoweredBlock
from src.graphics.color import Color
from src.graphics.position import Position

# Cores por tipo de célula — usadas pelo gerador e por add_block() manual.
_CELL_COLORS: dict[int, Color] = {
    1: Color(0.78, 0.59, 0.39),  # caminho — bege
    2: Color(0.20, 0.78, 0.20),  # início  — verde
    3: Color(0.78, 0.20, 0.20),  # fim     — vermelho
}


def _generate_matrix(
    cols: int, rows: int, rng: random.Random
) -> tuple[list[list[int]], tuple[int, int]]:
    """Gera uma matriz cols×rows com um caminho aleatório de largura ≥ 2.

    Algoritmo — Random Walk com largura dupla e bias de centro:
    1. Sorteia orientação: Norte→Sul (percorre linhas) ou Leste→Oeste (percorre colunas).
    2. Início e fim restritos ao intervalo central (margem de 1/4 de cada lado),
       evitando que o caminho fique totalmente de um lado do mapa.
    3. Drunk walk do início ao fim com bias de centro:
       - Quanto mais periférico o caminho, maior a chance de desvio lateral.
       - Desvios são direcionados ao centro (70%) em vez de totalmente aleatórios.
    4. set_cell() preenche sempre duas células paralelas — garante largura ≥ 2.
    5. Segmento reto final conecta o walk ao ponto exato de fim.
    6. Células de início e fim recebem tipos 2 e 3 respectivamente.

    Retorna: (matrix, start_col_row, direction) onde:
      - start_col_row é (col, row) da célula de início
      - direction é (dcol, drow) do passo inicial do caminho (ex: (0,1) = vai para +Z)
    """
    grid: list[list[int]] = [[0] * cols for _ in range(rows)]

    # O caminho sempre percorre o eixo Z (Norte→Sul): row=0 → row=rows-1.
    # Isso garante que W (dz=-1) e S (dz=+1) correspondem ao eixo do caminho,
    # mantendo a câmera e os controles do cubo sempre alinhados.
    main_len, cross_len = rows, cols
    margin = max(1, cross_len // 4)
    start_cross = rng.randint(margin, cross_len - 2 - margin)
    end_cross   = rng.randint(margin, cross_len - 2 - margin)

    def set_cell(main: int, cross: int, value: int) -> None:
        grid[main][cross]     = value
        grid[main][cross + 1] = value

    def get_start_pos(sc: int) -> tuple[int, int]:
        return sc, 0  # (col, row)

    direction = (0, 1)  # caminho avança em +Z (row cresce)

    center = (cross_len - 1) / 2.0
    cross = start_cross
    for main in range(main_len):
        set_cell(main, cross, 1)

        remaining = (main_len - 1) - main
        if remaining == 0:
            break

        # Nos últimos 2 passos não desvia — garante espaço para o segmento de fechamento.
        if remaining <= 2:
            continue

        # Bias de centro: quanto mais periférico, maior a chance de desvio.
        distance_ratio = abs(cross - center) / max(center, 1.0)
        deviate_chance = 0.20 + 0.35 * distance_ratio  # 20% no centro, 55% na borda

        if rng.random() < deviate_chance:
            toward_center = 1 if cross < center else -1
            # 70% em direção ao centro, 30% em direção contrária.
            step = toward_center if rng.random() < 0.70 else -toward_center
            new_cross = cross + step
            if 0 <= new_cross <= cross_len - 2:
                cross = new_cross

    # Fecha lateralmente até end_cross na última linha/coluna.
    step = 1 if end_cross > cross else -1
    while cross != end_cross:
        cross += step
        set_cell(main_len - 1, cross, 1)

    # Sobrescreve início e fim com seus tipos.
    set_cell(0,            start_cross, 2)
    set_cell(main_len - 1, end_cross,   3)

    return grid, get_start_pos(start_cross), direction


def _generate_matrix_forked(
    cols: int, rows: int, rng: random.Random
) -> tuple[list[list[int]], tuple[int, int], tuple[int, int]]:
    """Gera uma matriz com caminho bifurcado (Y-split).

    Estrutura:
      rows 0-1        — tronco de início (tipo 2 = verde)
      row  2          — bifurcação: ramo A (esq) e ramo B (dir) divergem
      rows 3..rows-4  — cada ramo faz seu próprio drunk-walk independente
      row  rows-3     — convergência: ambos os ramos se unem em end_cross
      rows rows-2..rows-1 — tronco de fim (tipo 3 = vermelho)
    """
    grid: list[list[int]] = [[0] * cols for _ in range(rows)]
    center = (cols - 1) / 2.0

    # Margem maior que o single-path para acomodar os dois ramos lado a lado.
    margin = max(4, cols // 4)
    start_cross = rng.randint(margin, cols - 2 - margin)
    end_cross   = rng.randint(margin, cols - 2 - margin)

    def set_row(row: int, col: int, value: int) -> None:
        """Preenche duas células adjacentes (largura ≥ 2), respeitando bordas."""
        col = max(0, min(col, cols - 2))
        grid[row][col]     = value
        grid[row][col + 1] = value

    def fill_lateral(row: int, c_from: int, c_to: int, value: int) -> None:
        """Preenche todas as células entre dois pontos na mesma row."""
        lo = max(0, min(c_from, c_to))
        hi = min(cols - 1, max(c_from, c_to) + 1)
        for c in range(lo, hi + 1):
            grid[row][c] = value

    # Tronco inicial (rows 0 a 2).
    set_row(0, start_cross, 2)
    set_row(1, start_cross, 1)
    set_row(2, start_cross, 1)

    # Posições de bifurcação: garantindo uma distância média entre os ramos A e B.
    dist = max(4, cols // 4)
    cross_a = max(0, start_cross - dist)
    cross_b = min(cols - 2, start_cross + dist)

    # Row 3: preenche lateralmente o tronco até as pontas de cada ramo.
    fill_lateral(3, cross_a, cross_b + 1, 1)

    # Drunk-walk independente para cada ramo entre rows 4 e rows-5.
    final_a, final_b = cross_a, cross_b
    walk_end = rows - 5

    for init_cross, sign, attr in [(cross_a, -1, "a"), (cross_b, +1, "b")]:
        cross = init_cross
        for row in range(4, walk_end + 1):
            set_row(row, cross, 1)
            remaining = walk_end - row
            
            # Nos últimos blocos, força o caminho a se aproximar do destino (end_cross)
            # para evitar uma "parede" reta de convergência.
            dist_to_end = abs(cross - end_cross)
            if remaining <= dist_to_end + 1 and cross != end_cross:
                step = 1 if end_cross > cross else -1
                new_cross = cross + step
                if 0 <= new_cross <= cols - 2:
                    cross = new_cross
                continue

            if remaining <= 1:
                continue

            distance_ratio = abs(cross - center) / max(center, 1.0)
            deviate_chance = 0.20 + 0.35 * distance_ratio
            if rng.random() < deviate_chance:
                # No terço final do mapa, a preferência muda para ir em direção ao end_cross
                if remaining < rows // 3:
                    preferred = 1 if end_cross > cross else -1
                    allow_cross_center = True
                else:
                    preferred = sign
                    allow_cross_center = False
                
                step = preferred if rng.random() < 0.85 else -preferred
                new_cross = cross + step
                
                if not allow_cross_center:
                    # Evitar que os ramos cruzem o centro do mapa cedo demais
                    if attr == "a" and new_cross > center - 1:
                        new_cross = cross
                    elif attr == "b" and new_cross < center + 1:
                        new_cross = cross
                
                if 0 <= new_cross <= cols - 2:
                    cross = new_cross
        if attr == "a":
            final_a = cross
        else:
            final_b = cross

    # Row rows-4: convergência lateral fina (caso algum ainda não tenha chegado perfeitamente)
    conv_row = rows - 4
    fill_lateral(conv_row, min(final_a, end_cross), max(final_a, end_cross) + 1, 1)
    fill_lateral(conv_row, min(final_b, end_cross), max(final_b, end_cross) + 1, 1)

    # Tronco final (rows rows-3 a rows-1).
    set_row(rows - 3, end_cross, 1)
    set_row(rows - 2, end_cross, 1)
    set_row(rows - 1, end_cross, 3)

    return grid, (start_cross, 0), (0, 1)


def _matrix_to_map(
    matrix: list[list[int]],
    start: tuple[int, int],
    direction: tuple[int, int],
    rng: random.Random,
) -> "Map":
    """Converte uma matriz de inteiros num Map populado com Blocks."""
    m = Map()
    m.start = start
    m.direction = direction
    for row_idx, row in enumerate(matrix):
        for col_idx, cell in enumerate(row):
            template = _CELL_COLORS.get(cell)
            if template is None:
                continue
            pos   = Position(x=float(col_idx), y=0.0, z=float(row_idx))
            
            # Se for célula de caminho comum (1), tem 10% de chance de ter o poder shrink
            if cell == 1 and rng.random() < 0.02:
                color = Color(1.0, 0.75, 0.0) # cor amarela p/ blocos especiais
                block = PoweredBlock(power="shrink", position=pos, color=color)
            else:
                color = Color(template.r, template.g, template.b)
                block = Block(position=pos, color=color)
                
            m.add_block(block, col=col_idx, row=row_idx)
    return m


class Map:
    DEFAULT_COLS: int = 32
    DEFAULT_ROWS: int = 32

    def __init__(self) -> None:
        # Dicionário esparso: só células ocupadas existem aqui.
        # Chave: (col, row) — inteiros de grade, não coordenadas de mundo.
        self._grid: dict[tuple[int, int], Block] = {}
        # Posição (col, row) da célula de início — definida por generate().
        self.start: tuple[int, int] = (0, 0)
        # Direção (dcol, drow) do passo inicial do caminho — definida por generate().
        self.direction: tuple[int, int] = (0, 1)

    def add_block(self, block: Block, col: int, row: int) -> None:
        """Registra um bloco na célula (col, row). Substitui se já existir."""
        self._grid[(col, row)] = block

    def get_block(self, col: int, row: int) -> Block | None:
        # Retorna None para célula vazia — verifique antes de acessar .power ou .active.
        return self._grid.get((col, row))

    def remove_block(self, col: int, row: int) -> None:
        """Remove o bloco da célula (col, row), se houver."""
        self._grid.pop((col, row), None)

    def can_move_to(self, grid_x: int, grid_z: int) -> bool:
        """MovementValidator: retorna True se a célula contém um bloco ativo."""
        block = self._grid.get((grid_x, grid_z))
        return block is not None and block.active

    def get_tile_type(self, grid_x: int, grid_z: int) -> str:
        """MovementValidator: classifica a célula para reações do cubo."""
        block = self._grid.get((grid_x, grid_z))
        if block is None or not block.active:
            return "empty"
        return "floor"

    def get_power(self, grid_x: int, grid_z: int) -> str | None:
        """MovementValidator: retorna o nome do poder armazenado na célula, se existir."""
        block = self._grid.get((grid_x, grid_z))
        if block is not None and block.active and block.is_powered:
            return getattr(block, "power", None)
        return None

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
        forked: bool = False,
    ) -> "Map":
        """Gera um mapa procedural com caminho aleatório de largura ≥ 2.

        O início fica em uma borda e o fim na borda oposta. O caminho é
        contínuo — sem fendas — garantindo que o Cube consiga atravessá-lo.
        O atributo map.start indica a célula (col, row) de início do Cube.

        Args:
            cols:   largura do grid em células (padrão: 32).
            rows:   altura do grid em células (padrão: 32).
            seed:   semente do RNG. None = diferente a cada chamada.
            forked: True = caminho bifurcado (Y-split); False = single-path (padrão).
        """
        rng = random.Random(seed)
        fn = _generate_matrix_forked if forked else _generate_matrix
        matrix, start, direction = fn(cols, rows, rng)
        return _matrix_to_map(matrix, start, direction, rng)
