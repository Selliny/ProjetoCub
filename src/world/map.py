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

Gerador (drunk grid)
---------------------
    Produz uma rede de corredores verticais tortuosos (drunk-walk)
    conectados por passagens horizontais de espessura dupla. Cada corredor
    desvia lateralmente ±1 célula por row com probabilidade 35%, e cada
    curva recebe um "joelho" de preenchimento que elimina becos. O jogador
    tem múltiplas rotas reais do início ao fim, com interseções orgânicas
    — sem nenhuma saída cega além do bloco de início (row=0) e fim
    (row=rows-1).
"""

import random

from src.entities.block import Block, EndBlock, GrowBlock, HealBlock, PortalBlock, ShrinkBlock, StartBlock
from src.graphics.color import Color
from src.graphics.position import Position


class Map:
    DEFAULT_COLS: int = 32
    DEFAULT_ROWS: int = 32

    # Cores por tipo de célula (0=vazio, 1=caminho, 2=início, 3=fim).
    CELL_COLORS: dict[int, Color] = {
        1: Color(0.78, 0.59, 0.39),
        2: Color(0.20, 0.78, 0.20),
        3: Color(0.78, 0.20, 0.20),
    }

    # Probabilidades acumuladas de geração de blocos especiais (por célula de caminho).
    PROB_HEAL:   float = 0.005   # ~0.5%  — rosa,  recupera 1 vida (uso único)
    PROB_SHRINK: float = 0.025   # ~2.0%  — roxo,  diminui o cubo
    PROB_GROW:   float = 0.040   # ~1.5%  — azul,  aumenta o cubo (menor que shrink)
    PROB_PORTAL: float = 0.050   # ~2.0%  — azul escuro, teleporta aleatoriamente

    # Parâmetros do gerador drunk-grid.
    LANE_GAP:       int   = 2     # células vazias mínimas entre corredores
    DEVIATE_CHANCE: float = 0.35  # chance de desvio lateral por row
    CROSS_DENSITY:  float = 0.75  # chance de ponte entre corredores vizinhos por banda

    def __init__(self) -> None:
        self._grid: dict[tuple[int, int], Block] = {}
        self.start: tuple[int, int] = (0, 0)
        self.direction: tuple[int, int] = (0, 1)

    # ------------------------------------------------------------------
    # API pública — manipulação do grid
    # ------------------------------------------------------------------

    def add_block(self, block: Block, col: int, row: int) -> None:
        """Registra um bloco na célula (col, row). Substitui se já existir."""
        self._grid[(col, row)] = block

    def get_block(self, col: int, row: int) -> Block | None:
        return self._grid.get((col, row))

    def remove_block(self, col: int, row: int) -> None:
        self._grid.pop((col, row), None)

    def draw(self) -> None:
        for block in self._grid.values():
            block.draw()

    # ------------------------------------------------------------------
    # MovementValidator (protocolo duck-typed usado pelo Cube)
    # ------------------------------------------------------------------

    def can_move_to(self, grid_x: int, grid_z: int) -> bool:
        block = self._grid.get((grid_x, grid_z))
        return block is not None and block.active

    def get_tile_type(self, grid_x: int, grid_z: int) -> str:
        block = self._grid.get((grid_x, grid_z))
        if block is None or not block.active:
            return "empty"
        return "floor"

    def get_power(self, grid_x: int, grid_z: int) -> str | None:
        block = self._grid.get((grid_x, grid_z))
        if block is not None and block.active and block.is_powered:
            return getattr(block, "power", None)
        return None

    def get_random_position(self) -> tuple[int, int]:
        """Retorna uma posição aleatória do grid (pode ser vazia — o cubo cai)."""
        import random
        keys = list(self._grid.keys())
        col, row = random.choice(keys)
        return col, row

    def consume_power(self, grid_x: int, grid_z: int) -> None:
        """Converte o PoweredBlock na célula em Block comum, consumindo o poder."""
        block = self._grid.get((grid_x, grid_z))
        if block is None or not block.is_powered:
            return
        self._grid[(grid_x, grid_z)] = Block(
            position=block.position,
            color=Map.CELL_COLORS[1],
            size=block.size,
            active=block.active,
        )

    # ------------------------------------------------------------------
    # Geração procedural
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        cols: int = DEFAULT_COLS,
        rows: int = DEFAULT_ROWS,
        seed: int | None = None,
        gap: int = LANE_GAP,
        deviate_chance: float = DEVIATE_CHANCE,
        cross_density: float = CROSS_DENSITY,
        prob_heal: float = PROB_HEAL,
        prob_shrink: float = PROB_SHRINK,
        prob_grow: float = PROB_GROW,
        prob_portal: float = PROB_PORTAL,
    ) -> "Map":
        """Gera um mapa procedural com corredores tortuosos (drunk grid).

        Todos os parâmetros têm padrões definidos como constantes de classe,
        mas podem ser sobrescritos individualmente pelos sandboxes.
        A largura de cada corredor (1 ou 2 células) é sorteada individualmente
        pelo gerador — não é mais um parâmetro global.

        Args:
            cols:           largura do grid em células.
            rows:           altura do grid em células.
            seed:           semente do RNG (None = aleatório a cada chamada).
            gap:            células vazias mínimas entre corredores.
            deviate_chance: probabilidade de desvio lateral por row.
            cross_density:  probabilidade de ponte entre corredores vizinhos por banda.
            prob_heal:      chance acumulada de bloco de cura (rosa).
            prob_shrink:    chance acumulada de bloco de diminuição (roxo).
            prob_grow:      chance acumulada de bloco de crescimento (azul).
        """
        rng = random.Random(seed)
        matrix, start, direction = cls._build_matrix(
            cols, rows, rng, gap, deviate_chance, cross_density
        )
        return cls._matrix_to_map(matrix, start, direction, rng, prob_heal, prob_shrink, prob_grow, prob_portal)

    # ------------------------------------------------------------------
    # Métodos privados — geração da matriz e conversão para Map
    # ------------------------------------------------------------------

    @staticmethod
    def _build_matrix(
        cols: int,
        rows: int,
        rng: random.Random,
        gap: int,
        deviate_chance: float,
        cross_density: float,
    ) -> tuple[list[list[int]], tuple[int, int], tuple[int, int]]:
        """Drunk-grid: corredores verticais tortuosos conectados por pontes horizontais.

        Cada corredor tem largura 1 ou 2 sorteada individualmente.
        Retorna (matrix, start_pos, direction).
        """
        grid: list[list[int]] = [[0] * cols for _ in range(rows)]

        # ── 1. Posições base e larguras dos corredores ────────────────────
        # Usa stride máximo (2 + gap) para reservar espaço suficiente para
        # qualquer largura sorteada. As larguras reais são definidas depois.
        max_lane_w = 2
        stride = max_lane_w + gap

        lane_bases: list[int] = []
        c = gap
        while c + max_lane_w <= cols - gap:
            lane_bases.append(c)
            c += stride

        if not lane_bases:
            lane_bases = [gap, gap + max(1, cols // 2)]

        n_lanes = len(lane_bases)

        # Cada corredor sorteia largura 1 ou 2 independentemente.
        lane_widths: list[int] = [rng.choice([1, 2]) for _ in range(n_lanes)]

        # ── 2. Drunk-walk de cada corredor ────────────────────────────────
        lane_paths: list[list[int]] = []

        for li, base in enumerate(lane_bases):
            w = lane_widths[li]

            # Limites que preservam o gap em relação aos vizinhos,
            # levando em conta a largura real de cada corredor vizinho.
            if li > 0:
                lo = lane_bases[li - 1] + lane_widths[li - 1] + gap
            else:
                lo = 0
            if li < n_lanes - 1:
                hi = lane_bases[li + 1] - w - gap
            else:
                hi = cols - w

            col_cur = base
            path: list[int] = []

            for r in range(rows):
                path.append(col_cur)

                for lc in range(w):
                    cc = col_cur + lc
                    if 0 <= cc < cols:
                        grid[r][cc] = 1

                if r == rows - 1:
                    break

                if rng.random() < deviate_chance:
                    step = rng.choice([-1, 1])
                    new_col = col_cur + step
                    if lo <= new_col and new_col + w - 1 <= hi:
                        # Joelho de curva: célula de transição em r+1 para que
                        # os dois segmentos compartilhem ao menos 1 célula.
                        knee_col = col_cur if step == 1 else new_col + w - 1
                        if 0 <= r + 1 < rows and 0 <= knee_col < cols:
                            grid[r + 1][knee_col] = 1
                        col_cur = new_col

            lane_paths.append(path)

        # ── 3. Pontes horizontais em bandas ───────────────────────────────
        # Mais bandas = mais oportunidades de ponte ao longo da altura.
        # A espessura de cada ponte usa a menor largura dos dois corredores ligados.
        n_bands = max(5, rows // max(1, stride))
        band_size = max(1, rows // n_bands)

        def paint_bridge(r: int, c_left: int, c_right: int, thickness: int) -> None:
            lo_c, hi_c = min(c_left, c_right), max(c_left, c_right)
            for br in range(thickness):
                target_row = r + br
                if 0 < target_row < rows - 1:
                    for cc in range(lo_c, hi_c + 1):
                        if 0 <= cc < cols:
                            grid[target_row][cc] = 1

        for band in range(n_bands):
            row_lo = band * band_size + 1
            row_hi = min((band + 1) * band_size - 1, rows - 2)
            if row_lo >= row_hi:
                continue
            for i in range(n_lanes - 1):
                if rng.random() > cross_density:
                    continue
                br = rng.randint(row_lo, row_hi)
                right_edge = lane_paths[i][br] + lane_widths[i] - 1
                left_edge  = lane_paths[i + 1][br]
                thickness  = min(lane_widths[i], lane_widths[i + 1])
                paint_bridge(br, right_edge, left_edge, thickness)

        # ── 4. Garantia de conectividade ──────────────────────────────────
        # Força ao menos uma ponte no meio para cada par de vizinhos sem nenhuma.
        for i in range(n_lanes - 1):
            mid = rows // 2
            right_edge = lane_paths[i][mid] + lane_widths[i] - 1
            left_edge  = lane_paths[i + 1][mid]
            gap_col = right_edge + 1
            has_bridge = (
                0 <= gap_col < cols
                and any(grid[r][gap_col] == 1 for r in range(1, rows - 1))
            )
            if not has_bridge:
                thickness = min(lane_widths[i], lane_widths[i + 1])
                paint_bridge(mid, right_edge, left_edge, thickness)

        # ── 5. Início e fim em cantos opostos ─────────────────────────────
        if rng.random() < 0.5:
            start_li, end_li = 0, n_lanes - 1
        else:
            start_li, end_li = n_lanes - 1, 0

        start_col = lane_paths[start_li][0]
        end_col   = lane_paths[end_li][rows - 1]

        for lc in range(lane_widths[start_li]):
            if start_col + lc < cols:
                grid[0][start_col + lc] = 2
        for lc in range(lane_widths[end_li]):
            if end_col + lc < cols:
                grid[rows - 1][end_col + lc] = 3

        # ── 6. Remoção iterativa de becos ─────────────────────────────────
        # Células protegidas: início (row 0) e fim (row rows-1) e seus vizinhos
        # imediatos na direção do percurso — nunca podem ser removidos.
        protected: set[tuple[int, int]] = set()
        for c in range(cols):
            if grid[0][c] > 0:
                protected.add((0, c))
                if grid[1][c] > 0:
                    protected.add((1, c))
            if grid[rows - 1][c] > 0:
                protected.add((rows - 1, c))
                if grid[rows - 2][c] > 0:
                    protected.add((rows - 2, c))

        def degree(r: int, c: int) -> int:
            return sum(
                1
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if 0 <= r + dr < rows and 0 <= c + dc < cols and grid[r + dr][c + dc] > 0
            )

        changed = True
        while changed:
            changed = False
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] != 1:
                        continue
                    if (r, c) in protected:
                        continue
                    if degree(r, c) <= 1:
                        grid[r][c] = 0
                        changed = True

        return grid, (start_col, 0), (0, 1)

    @staticmethod
    def _matrix_to_map(
        matrix: list[list[int]],
        start: tuple[int, int],
        direction: tuple[int, int],
        rng: random.Random,
        prob_heal: float,
        prob_shrink: float,
        prob_grow: float,
        prob_portal: float,
    ) -> "Map":
        """Converte uma matriz de inteiros num Map populado com Blocks."""
        m = Map()
        m.start = start
        m.direction = direction

        for row_idx, row in enumerate(matrix):
            for col_idx, cell in enumerate(row):
                template = Map.CELL_COLORS.get(cell)
                if template is None:
                    continue

                pos = Position(x=float(col_idx), y=0.0, z=float(row_idx))

                if cell == 1:
                    rv = rng.random()
                    if rv < prob_heal:
                        block: Block = HealBlock(
                            position=pos,
                            color=Color(1.0, 0.4, 0.7),
                        )
                    elif rv < prob_shrink:
                        block = ShrinkBlock(
                            position=pos,
                            color=Color(0.5, 0.0, 1.0),
                        )
                    elif rv < prob_grow:
                        block = GrowBlock(
                            position=pos,
                            color=Color(0.2, 1.0, 0.2),
                        )
                    elif rv < prob_portal:
                        block = PortalBlock(
                            position=pos,
                            color=Color(0.0, 0.1, 0.4),
                        )
                    else:
                        block = Block(position=pos, color=Color(template.r, template.g, template.b))
                elif cell == 2:
                    block = StartBlock(position=pos, color=Color(template.r, template.g, template.b))
                else:
                    block = EndBlock(position=pos, color=Color(template.r, template.g, template.b))

                m.add_block(block, col=col_idx, row=row_idx)

        return m
