"""Coleção de blocos que formam o terreno do jogo.

Map armazena blocos num dicionário esparso: a chave é (col, row) e o valor
é um Block (ou PoweredBlock). Células vazias simplesmente não existem no
dicionário — não ocupam memória nem são desenhadas.

Gerador — Loop Central (Mapa 4)
---------------------------------
    Implementa o algoritmo descrito em geracao_caminhos_mapa4.md:

    Fase 1 — Geometria fixa: calcula anel (topo/base/esq/dir), corredor de
             entrada (START → bifurcação) e corredor de saída (convergência → END).

    Fase 2 — Arco superior: sobe da bifurcação ao topo, percorre a borda
             superior e desce até a convergência.

    Fase 3 — Arco inferior: desce da bifurcação à base, percorre a borda
             inferior e sobe até a convergência.

    Fase 4 (opcional) — Corredor interno: atravessa o interior do anel em L.

    Fase 5 (opcional) — Atalho central: diagonal interna bif → centro → conv.

    Fase 6 — Ruído nos arcos: desvia tiles 1 célula para o interior com
             probabilidade `ruido_arcos`.

    Conectividade garantida por construção geométrica; sem necessidade de BFS
    de correção. Blocos especiais distribuídos aleatoriamente em _matrix_to_map.
"""

import random
import time
from collections import deque

from src.entities.block import (
    Block,
    BouncePadBlock,
    CheckpointBlock,
    EndBlock,
    FragileBlock,
    GrowBlock,
    HealBlock,
    IceBlock,
    InvertBlock,
    PortalBlock,
    ShrinkBlock,
    SlowBlock,
    StartBlock,
)
from src.graphics.color import Color
from src.graphics.position import Position


def _make_powered(power_name: str, pos: "Position") -> Block:
    """Instancia o PoweredBlock correto pelo nome do poder."""
    if power_name == "heal":
        return HealBlock(position=pos, color=Color(1.0, 0.4, 0.7))
    if power_name == "shrink":
        return ShrinkBlock(position=pos, color=Color(0.5, 0.0, 1.0))
    if power_name == "grow":
        return GrowBlock(position=pos, color=Color(0.2, 1.0, 0.2))
    if power_name == "portal":
        return PortalBlock(position=pos, color=Color(0.0, 0.1, 0.4))
    if power_name == "ice":
        return IceBlock(position=pos)
    if power_name == "invert":
        return InvertBlock(position=pos)
    if power_name == "fragile":
        return FragileBlock(position=pos)
    if power_name == "bounce":
        return BouncePadBlock(position=pos)
    if power_name == "slow":
        return SlowBlock(position=pos)
    if power_name == "checkpoint":
        return CheckpointBlock(position=pos)
    return HealBlock(position=pos, color=Color(1.0, 0.4, 0.7))


class Map:
    DEFAULT_COLS: int = 32
    DEFAULT_ROWS: int = 32

    # Cores por tipo de célula (1=caminho, 2=início, 3=fim).
    CELL_COLORS: dict[int, Color] = {
        1: Color(0.78, 0.59, 0.39),
        2: Color(0.20, 0.78, 0.20),
        3: Color(0.78, 0.20, 0.20),
    }

    # Probabilidades de geração de blocos especiais (por célula de caminho, não acumuladas).
    PROB_HEAL:       float = 0.005
    PROB_SHRINK:     float = 0.020
    PROB_GROW:       float = 0.015
    PROB_PORTAL:     float = 0.010
    PROB_ICE:        float = 0.030
    PROB_INVERT:     float = 0.020
    PROB_FRAGILE:    float = 0.030
    PROB_BOUNCE:     float = 0.018
    PROB_SLOW:       float = 0.015
    PROB_CHECKPOINT: float = 0.012

    # Duração do timer de FragileBlock (segundos após o cubo sair)
    FRAGILE_DELAY: float = 1.5

    # Parâmetros do gerador Loop Central (Mapa 4).
    DEFAULT_N_PATHS:    int   = 2    # 2=arcos, 3=+corredor interno, 4=+atalho central
    DEFAULT_ARC_NOISE:  float = 0.0  # 0.0=arcos retos, >0=ondulação orgânica

    def __init__(self) -> None:
        self._grid: dict[tuple[int, int], Block] = {}
        self.start: tuple[int, int] = (0, 0)
        self.direction: tuple[int, int] = (0, 1)
        # FragileBlock: mapeia (col, row) → tempo absoluto de desativação
        self._fragile_timers: dict[tuple[int, int], float] = {}
        # CheckpointBlock: chave da célula atualmente ativa
        self._active_checkpoint: tuple[int, int] | None = None

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

    def schedule_fragile(self, grid_x: int, grid_z: int) -> None:
        """Agenda a desativação de um FragileBlock após FRAGILE_DELAY segundos."""
        key = (grid_x, grid_z)
        if key not in self._fragile_timers:
            self._fragile_timers[key] = time.monotonic() + Map.FRAGILE_DELAY

    def set_checkpoint(self, grid_x: int, grid_z: int) -> None:
        """Ativa o CheckpointBlock em (grid_x, grid_z) e desativa o anterior."""
        new_key = (grid_x, grid_z)
        if self._active_checkpoint is not None and self._active_checkpoint != new_key:
            old_block = self._grid.get(self._active_checkpoint)
            if isinstance(old_block, CheckpointBlock):
                old_block.is_active_checkpoint = False
        new_block = self._grid.get(new_key)
        if isinstance(new_block, CheckpointBlock):
            new_block.is_active_checkpoint = True
        self._active_checkpoint = new_key

    def update(self, dt: float) -> None:
        """Processa timers de FragileBlocks a cada frame."""
        now = time.monotonic()
        expired = [key for key, t in self._fragile_timers.items() if now >= t]
        for key in expired:
            del self._fragile_timers[key]
            block = self._grid.get(key)
            if block is not None:
                block.active = False

    # ------------------------------------------------------------------
    # Geração procedural
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        cols: int = DEFAULT_COLS,
        rows: int = DEFAULT_ROWS,
        seed: int | None = None,
        n_paths: int = DEFAULT_N_PATHS,
        arc_noise: float = DEFAULT_ARC_NOISE,
        prob_heal: float = PROB_HEAL,
        prob_shrink: float = PROB_SHRINK,
        prob_grow: float = PROB_GROW,
        prob_portal: float = PROB_PORTAL,
        prob_ice: float = PROB_ICE,
        prob_invert: float = PROB_INVERT,
        prob_fragile: float = PROB_FRAGILE,
        prob_bounce: float = PROB_BOUNCE,
        prob_slow: float = PROB_SLOW,
        prob_checkpoint: float = PROB_CHECKPOINT,
    ) -> "Map":
        """Gera um mapa Loop Central (geracao_caminhos_mapa4.md).

        Args:
            cols, rows:   dimensões da grade (inclui bordas).
            seed:         semente do RNG (None = aleatório).
            n_paths:      2=arco sup+inf | 3=+corredor interno | 4=+atalho central.
            arc_noise:    probabilidade de desvio orgânico em cada tile de arco.
            prob_*:       chance individual de cada bloco especial por tile.
        """
        rng = random.Random(seed)
        matrix, start, direction = cls._build_matrix(cols, rows, rng, n_paths, arc_noise)
        return cls._matrix_to_map(
            matrix, start, direction, rng,
            prob_heal, prob_shrink, prob_grow, prob_portal,
            prob_ice, prob_invert, prob_fragile, prob_bounce,
            prob_slow, prob_checkpoint,
        )

    # ------------------------------------------------------------------
    # Métodos privados — geração da matriz Loop Central
    # ------------------------------------------------------------------

    @staticmethod
    def _build_matrix(
        cols: int,
        rows: int,
        rng: random.Random,
        n_paths: int,
        arc_noise: float,
    ) -> tuple[list[list[int]], tuple[int, int], tuple[int, int]]:
        """Loop Central: anel com arco superior e inferior, entrada e saída lineares.

        A grade usa grid[row][col] internamente.
        Retorna (matrix, start_as_col_row, direction) onde start é (col, row).
        Valor 1 = chão, 2 = START, 3 = END.
        """
        CAMINHO = 1
        START   = 2
        END     = 3

        grid: list[list[int]] = [[0] * cols for _ in range(rows)]

        # ── Geometria derivada ────────────────────────────────────────────
        entrada_row = rows // 2 - 1
        entrada_len = max(2, cols // 6)
        saida_row   = entrada_row + 2
        saida_len   = max(2, cols // 7)

        anel = {
            "topo": max(1, rows // 5),
            "base": rows - max(2, rows // 4) - 1,
            "esq":  entrada_len + 1,
            "dir":  cols - max(3, cols // 6) - 1,
        }

        # Garante que o anel tem pelo menos 3 linhas de altura e 3 colunas
        anel["topo"] = min(anel["topo"], entrada_row - 1)
        anel["base"] = max(anel["base"], saida_row + 1)
        anel["topo"] = max(1, anel["topo"])
        anel["base"] = min(rows - 2, anel["base"])
        anel["esq"]  = max(1, anel["esq"])
        anel["dir"]  = min(cols - 2, anel["dir"])

        bif = (entrada_row, anel["esq"])   # (row, col) — ponto de bifurcação
        con = (saida_row,   anel["dir"])   # (row, col) — ponto de convergência

        # ── START e corredor de entrada ───────────────────────────────────
        grid[entrada_row][0] = START
        for c in range(1, anel["esq"] + 1):
            grid[entrada_row][c] = CAMINHO

        # ── Borda do anel ─────────────────────────────────────────────────
        for c in range(anel["esq"], anel["dir"] + 1):
            grid[anel["topo"]][c] = CAMINHO
            grid[anel["base"]][c] = CAMINHO
        for r in range(anel["topo"], anel["base"] + 1):
            grid[r][anel["esq"]] = CAMINHO
            grid[r][anel["dir"]] = CAMINHO

        # ── END e corredor de saída ────────────────────────────────────────
        end_col = min(cols - 1, anel["dir"] + saida_len)
        for c in range(anel["dir"], end_col + 1):
            grid[saida_row][c] = CAMINHO
        grid[saida_row][end_col] = END

        # ── Helper: desvio orgânico ────────────────────────────────────────
        def apply_noise(r: int, c: int) -> tuple[int, int]:
            if arc_noise <= 0 or rng.random() > arc_noise:
                return r, c
            if r == anel["topo"]:
                nr, nc = r + 1, c
            elif r == anel["base"]:
                nr, nc = r - 1, c
            elif c == anel["esq"]:
                nr, nc = r, c + 1
            elif c == anel["dir"]:
                nr, nc = r, c - 1
            else:
                return r, c
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
                return nr, nc
            return r, c

        # ── Arco superior ─────────────────────────────────────────────────
        r_bif, c_bif = bif
        r_con, c_con = con
        # sobe da bifurcação até o topo
        for r in range(r_bif, anel["topo"] - 1, -1):
            grid[r][c_bif] = CAMINHO
        # percorre borda superior
        for c in range(c_bif, c_con + 1):
            nr, nc = apply_noise(anel["topo"], c)
            grid[nr][nc] = CAMINHO
        # desce do topo até a convergência
        for r in range(anel["topo"], r_con + 1):
            grid[r][c_con] = CAMINHO

        # ── Arco inferior ─────────────────────────────────────────────────
        # desce da bifurcação até a base
        for r in range(r_bif, anel["base"] + 1):
            grid[r][c_bif] = CAMINHO
        # percorre borda inferior
        for c in range(c_bif, c_con + 1):
            nr, nc = apply_noise(anel["base"], c)
            grid[nr][nc] = CAMINHO
        # sobe da base até a convergência
        for r in range(anel["base"], r_con - 1, -1):
            grid[r][c_con] = CAMINHO

        # ── Corredor interno (3º caminho) ─────────────────────────────────
        if n_paths >= 3:
            r_meio = (anel["topo"] + anel["base"]) // 2 + rng.randint(-1, 1)
            r_meio = max(anel["topo"] + 1, min(anel["base"] - 1, r_meio))
            passo = 1 if r_meio >= r_bif else -1
            for r in range(r_bif, r_meio + passo, passo):
                grid[r][c_bif] = CAMINHO
            for c in range(c_bif, c_con + 1):
                grid[r_meio][c] = CAMINHO
            passo = 1 if r_con >= r_meio else -1
            for r in range(r_meio, r_con + passo, passo):
                grid[r][c_con] = CAMINHO

        # ── Atalho central (4º caminho) ───────────────────────────────────
        if n_paths >= 4:
            r_c = (anel["topo"] + anel["base"]) // 2
            c_c = (anel["esq"]  + anel["dir"])  // 2
            passo = 1 if r_c >= r_bif else -1
            for r in range(r_bif, r_c + passo, passo):
                grid[r][c_bif] = CAMINHO
            for c in range(c_bif, c_c + 1):
                grid[r_c][c] = CAMINHO
            for c in range(c_c, c_con + 1):
                grid[r_c][c] = CAMINHO
            passo = 1 if r_con >= r_c else -1
            for r in range(r_c, r_con + passo, passo):
                grid[r][c_con] = CAMINHO

        # ── Converte coordenadas para o sistema (col, row) do Map ─────────
        # start retornado como (col, row) para _make_cube
        start_col_row: tuple[int, int] = (0, entrada_row)
        return grid, start_col_row, (1, 0)

    # ------------------------------------------------------------------
    # Conversão matriz → Map com blocos
    # ------------------------------------------------------------------

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
        prob_ice: float,
        prob_invert: float,
        prob_fragile: float,
        prob_bounce: float,
        prob_slow: float,
        prob_checkpoint: float,
    ) -> "Map":
        """Converte a matriz de inteiros num Map populado com Blocks.

        Cada célula de caminho rola um dado uniforme. Os intervalos são
        construídos dinamicamente a partir das probabilidades individuais,
        permitindo que qualquer delas seja 0 sem distorcer as demais.
        """
        m = Map()
        m.start = start
        m.direction = direction

        # Tabela de (nome, prob) para blocos especiais — ordem importa
        _specials = [
            ("heal",       prob_heal),
            ("shrink",     prob_shrink),
            ("grow",       prob_grow),
            ("portal",     prob_portal),
            ("ice",        prob_ice),
            ("invert",     prob_invert),
            ("fragile",    prob_fragile),
            ("bounce",     prob_bounce),
            ("slow",       prob_slow),
            ("checkpoint", prob_checkpoint),
        ]
        # Filtra os que têm prob > 0 e calcula limiar acumulado
        active = [(name, p) for name, p in _specials if p > 0.0]
        thresholds: list[tuple[str, float]] = []
        acc = 0.0
        for name, p in active:
            acc += p
            thresholds.append((name, acc))
        total_special = acc

        for row_idx, row in enumerate(matrix):
            for col_idx, cell in enumerate(row):
                pos = Position(x=float(col_idx), y=0.0, z=float(row_idx))

                if cell == 1:
                    rv = rng.random()
                    block: Block | None = None
                    if rv < total_special and thresholds:
                        for name, threshold in thresholds:
                            if rv < threshold:
                                block = _make_powered(name, pos)
                                break
                    if block is None:
                        c = Map.CELL_COLORS[1]
                        block = Block(position=pos, color=Color(c.r, c.g, c.b))
                elif cell == 2:
                    block = StartBlock(position=pos)
                elif cell == 3:
                    c = Map.CELL_COLORS[3]
                    block = EndBlock(position=pos, color=Color(c.r, c.g, c.b))
                else:
                    continue

                m.add_block(block, col=col_idx, row=row_idx)

        return m
