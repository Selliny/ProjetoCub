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
    BlinkBlock,
    EndBlock,
    FragileBlock,
    GrowBlock,
    HealBlock,
    IceBlock,
    InvertBlock,
    ShrinkBlock,
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
    if power_name == "ice":
        return IceBlock(position=pos)
    if power_name == "invert":
        return InvertBlock(position=pos)
    if power_name == "fragile":
        return FragileBlock(position=pos)
    if power_name == "blink":
        return BlinkBlock(position=pos)
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
    PROB_HEAL:    float = 0.005
    PROB_SHRINK:  float = 0.020
    PROB_GROW:    float = 0.015
    PROB_ICE:     float = 0.030
    PROB_INVERT:  float = 0.020
    PROB_FRAGILE: float = 0.030

    # Duração do timer de FragileBlock (segundos após o cubo sair)
    FRAGILE_DELAY: float = 0.45
    # Tempo para o FragileBlock reaparecer após ser quebrado
    FRAGILE_RESPAWN_DELAY: float = 10.0

    # Parâmetros do gerador Loop Central (Mapa 4).
    DEFAULT_N_PATHS:    int   = 2    # 2=arcos, 3=+corredor interno, 4=+atalho central
    DEFAULT_ARC_NOISE:  float = 0.0  # 0.0=arcos retos, >0=ondulação orgânica

    def __init__(self) -> None:
        self._grid: dict[tuple[int, int], Block] = {}
        self.start: tuple[int, int] = (0, 0)
        self.direction: tuple[int, int] = (0, 1)
        # FragileBlock: mapeia (col, row) → tempo absoluto de desativação
        self._fragile_timers: dict[tuple[int, int], float] = {}
        # FragileBlock: mapeia (col, row) → tempo absoluto de reaparecimento
        self._fragile_respawn_timers: dict[tuple[int, int], float] = {}

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

    def get_tile_type(self, grid_x: int, grid_z: int) -> str:
        block = self._grid.get((grid_x, grid_z))
        if block is None or not block.active:
            return "empty"
        if isinstance(block, EndBlock):
            return "end"
        return "floor"

    def can_move_to(self, grid_x: int, grid_z: int, cube_scale: float = 1.0) -> bool:
        block = self._grid.get((grid_x, grid_z))
        if block is None or not block.active:
            return False
        return True

    def get_power(self, grid_x: int, grid_z: int) -> str | None:
        block = self._grid.get((grid_x, grid_z))
        if block is not None and block.active and block.is_powered:
            return getattr(block, "power", None)
        return None

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

    def update(self, dt: float) -> None:
        """Processa timers de FragileBlocks e ciclos de BlinkBlocks a cada frame."""
        now = time.monotonic()

        expired = [key for key, t in self._fragile_timers.items() if now >= t]
        for key in expired:
            del self._fragile_timers[key]
            block = self._grid.get(key)
            if block is not None:
                block.active = False
                if key not in self._fragile_respawn_timers:
                    self._fragile_respawn_timers[key] = now + Map.FRAGILE_RESPAWN_DELAY

        respawned = [key for key, t in self._fragile_respawn_timers.items() if now >= t]
        for key in respawned:
            del self._fragile_respawn_timers[key]
            block = self._grid.get(key)
            if block is not None:
                block.active = True

        for block in self._grid.values():
            if isinstance(block, BlinkBlock):
                block.toggle_blink(dt)

    # ------------------------------------------------------------------
    # Geração procedural
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        cols: int = DEFAULT_COLS,
        rows: int = DEFAULT_ROWS,
        seed: int | None = None,
        challenge_profile: str = "medium",
        generator: str = "loop",
        n_paths: int = DEFAULT_N_PATHS,
        arc_noise: float = DEFAULT_ARC_NOISE,
        branch_count: int | None = None,
        branch_length: int | None = None,
        main_path_bias: float = 0.72,
        loop_regions: int = 0,
        reward_branches: int = 0,
        false_branches: int = 0,
        false_branch_length: int | None = None,
        risk_shortcuts: int = 0,
        safe_detours: int = 0,
        dead_end_ratio: float = 0.35,
        prob_heal: float = PROB_HEAL,
        prob_shrink: float = PROB_SHRINK,
        prob_grow: float = PROB_GROW,
        prob_ice: float = PROB_ICE,
        prob_invert: float = PROB_INVERT,
        prob_fragile: float = PROB_FRAGILE,
        # Ignored (kept for backwards-compatible callers):
        prob_wall: float = 0.0,
        prob_portal: float = 0.0,
        prob_bounce: float = 0.0,
        prob_slow: float = 0.0,
        prob_checkpoint: float = 0.0,
        cluster_zones: list | None = None,
        combo_sequences: list | None = None,
        corridor_theme_count: int = 0,
    ) -> "Map":
        """Gera um mapa procedural.

        Args:
            cols, rows:   dimensões da grade (inclui bordas).
            seed:         semente do RNG (None = aleatório).
            challenge_profile: "easy", "medium" ou "hard" para zoneamento.
            generator:    "loop" para Loop Central ou "maze" para Drunkard Walk.
            n_paths:      2=arco sup+inf | 3=+corredor interno | 4=+atalho central.
            arc_noise:    probabilidade de desvio orgânico em cada tile de arco.
            branch_count: quantidade de ramificações extras no labirinto.
            branch_length: comprimento médio das ramificações extras.
            main_path_bias: chance de o walk principal andar em direção ao fim.
            loop_regions: regiões de decisão com rotas alternativas planejadas.
            reward_branches: becos laterais com recompensa.
            false_branches: bifurcações falsas longas que não reconectam.
            false_branch_length: comprimento médio das bifurcações falsas.
            risk_shortcuts: atalhos curtos com intenção de perigo.
            safe_detours: desvios mais longos com intenção de segurança.
            dead_end_ratio: fração das ramificações orgânicas que devem virar becos.
            prob_*:       chance individual de cada bloco especial por tile.
        """
        rng = random.Random(seed)
        intents: dict[tuple[int, int], str] = {}
        forced_intents: set[tuple[int, int]] = set()
        blink_phases: dict[tuple[int, int], float] = {}

        if generator == "maze":
            matrix, start, direction, intents = cls._build_maze_matrix(
                cols=cols,
                rows=rows,
                rng=rng,
                branch_count=branch_count,
                branch_length=branch_length,
                main_path_bias=main_path_bias,
                loop_regions=loop_regions,
                reward_branches=reward_branches,
                false_branches=false_branches,
                false_branch_length=false_branch_length,
                risk_shortcuts=risk_shortcuts,
                safe_detours=safe_detours,
                dead_end_ratio=dead_end_ratio,
            )
        elif generator == "loop":
            matrix, start, direction = cls._build_matrix(cols, rows, rng, n_paths, arc_noise)
        elif generator == "corridor":
            matrix, start, direction, intents, forced_intents, blink_phases = cls._build_corridor_matrix(
                cols=cols, rows=rows, rng=rng,
                n_corridors=branch_count or 3,
                corridor_theme_count=corridor_theme_count,
            )
        else:
            raise ValueError(f"Gerador de mapa desconhecido: {generator!r}")

        if generator != "corridor":
            cls._remove_dead_ends(matrix, start)

        if not cls._has_path(matrix, start):
            raise RuntimeError("Mapa gerado sem caminho válido entre START e END.")

        return cls._matrix_to_map(
            matrix, start, direction, rng,
            prob_heal, prob_shrink, prob_grow,
            prob_ice, prob_invert, prob_fragile,
            intents, challenge_profile,
            cluster_zones=cluster_zones or [],
            combo_sequences=combo_sequences or [],
            forced_intents=forced_intents,
            blink_phases=blink_phases,
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

    @staticmethod
    def _carve_maze_region(
        grid: list[list[int]],
        rng: random.Random,
        x0: int,
        x1: int,
        y0: int,
        y1: int,
        start: tuple[int, int],
        must_reach: list[tuple[int, int]],
        bias: float = 0.55,
    ) -> None:
        """Drunkard Walk confinado em [x0..x1] x [y0..y1].

        Garante que cada tile em `must_reach` e alcancavel a partir de `start`.
        Para cada target, faz biased random walk dentro do retangulo; se nao
        atingir, fallback Manhattan dentro dos limites. Tiles carved viram
        FLOOR (1); celulas fora do retangulo nao sao tocadas.
        """
        FLOOR = 1
        def inside(x: int, z: int) -> bool:
            return x0 <= x <= x1 and y0 <= z <= y1

        sx, sz = start
        if inside(sx, sz):
            grid[sz][sx] = FLOOR

        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for target in must_reach:
            tx, tz = target
            x, z = sx, sz
            max_steps = (x1 - x0 + y1 - y0 + 4) * 6
            for _ in range(max_steps):
                if (x, z) == (tx, tz):
                    break
                preferred: list[tuple[int, int]] = []
                if tx > x:
                    preferred.append((1, 0))
                elif tx < x:
                    preferred.append((-1, 0))
                if tz > z:
                    preferred.append((0, 1))
                elif tz < z:
                    preferred.append((0, -1))
                if preferred and rng.random() < bias:
                    dx, dz = rng.choice(preferred)
                else:
                    dx, dz = rng.choice(directions)
                nx, nz = x + dx, z + dz
                if not inside(nx, nz):
                    continue
                x, z = nx, nz
                grid[z][x] = FLOOR
            # Fallback Manhattan
            while x != tx:
                x += 1 if tx > x else -1
                if inside(x, z):
                    grid[z][x] = FLOOR
            while z != tz:
                z += 1 if tz > z else -1
                if inside(x, z):
                    grid[z][x] = FLOOR

    @staticmethod
    def _build_corridor_matrix(
        cols: int,
        rows: int,
        rng: random.Random,
        n_corridors: int = 3,
        corridor_theme_count: int = 0,
    ) -> tuple[list[list[int]], tuple[int, int], tuple[int, int], dict, set]:
        """Layout hibrido: maze (esquerda) + corredores tematicos (centro) + maze (direita).

        - Zona esquerda (cols 1..entry_col-1): Drunkard Walk de 1 tile conectando
          START a cada entrada de corredor.
        - Zona central (cols entry_col..exit_col): N corredores de largura 2
          que ondulam verticalmente. Isolados entre si por VOID — o jogador deve
          atravessar UM corredor inteiro (sem rota alternativa horizontal).
        - Zona direita (cols exit_col+1..cols-2): Drunkard Walk conectando cada
          saida de corredor ao END.

        corridor_theme_count primeiros corredores recebem tema (ice, fragile,
        bounce, slow, invert). O ultimo tematico vira corredor com ShrinkBlocks
        na entrada.

        Retorna: grid, start, direction, intents, forced_intents, blink_phases
        forced_intents: set de coordenadas cujo intent deve ser honrado sem
        checagem de zone (para garantir identidade tematica no corredor inteiro).
        blink_phases: dict de (col, row) → phase_offset (float 0.0-1.0) para BlinkBlocks.
        """
        START, FLOOR, END = 2, 1, 3
        grid = [[0] * cols for _ in range(rows)]
        intents: dict[tuple[int, int], str] = {}
        forced_intents: set[tuple[int, int]] = set()
        blink_phases: dict[tuple[int, int], float] = {}

        # Limites das zonas
        entry_col = max(4, cols // 5)
        exit_col  = min(cols - 5, cols - 1 - cols // 5)
        if exit_col <= entry_col + 2:
            exit_col = entry_col + 3

        WAVE_PERIOD = 4  # colunas entre possivel mudanca de altitude

        def fill_undulated(row_a_base: int) -> list[tuple[int, int, int]]:
            """Preenche corredor ondulado; retorna lista de (col, row_a, row_b)."""
            col_range = exit_col - entry_col + 1
            row_a = max(1, min(rows - 3, row_a_base))
            filled: list[tuple[int, int, int]] = []
            for i, col in enumerate(range(entry_col, exit_col + 1)):
                row_b = row_a + 1
                if row_b >= rows - 1:
                    break
                grid[row_a][col] = FLOOR
                grid[row_b][col] = FLOOR
                filled.append((col, row_a, row_b))
                # Decidir mudanca de altitude a cada WAVE_PERIOD cols (nao no fim)
                if i > 0 and i % WAVE_PERIOD == 0 and i < col_range - WAVE_PERIOD:
                    shift = rng.choice([-1, 0, 1])
                    if shift != 0:
                        new_row_a = row_a + shift
                        new_row_b = new_row_a + 1
                        if 1 <= new_row_a and new_row_b <= rows - 2:
                            # Tile de sobreposicao para manter face-connectivity
                            overlap = row_b + 1 if shift == 1 else row_a - 1
                            if 1 <= overlap <= rows - 2:
                                grid[overlap][col] = FLOOR
                            row_a = new_row_a
            return filled

        # Corredores tematicos (zona central): calcular base row por espacamento
        spacing = max(3, rows // (n_corridors + 1))
        # corridors_filled: lista de lista de (col, row_a, row_b) por corredor
        corridors_filled: list[list[tuple[int, int, int]]] = []
        for i in range(n_corridors):
            row_a_base = max(1, spacing * (i + 1) - 1)
            if row_a_base + 1 >= rows - 1:
                break
            filled = fill_undulated(row_a_base)
            if filled:
                corridors_filled.append(filled)

        # Para conectores de maze, usar row da primeira e ultima coluna do corredor
        def entry_rows(cf: list[tuple[int, int, int]]) -> tuple[int, int]:
            _, ra, rb = cf[0]
            return ra, rb

        def exit_rows(cf: list[tuple[int, int, int]]) -> tuple[int, int]:
            _, ra, rb = cf[-1]
            return ra, rb

        # START no canto noroeste; END no canto sudeste
        start = (1, 1)
        end   = (cols - 2, rows - 2)

        # Maze esquerdo: conectar START a cada entrada (entry_col-1, row_a/row_b)
        left_targets: list[tuple[int, int]] = []
        for cf in corridors_filled:
            ra, rb = entry_rows(cf)
            left_targets.append((entry_col - 1, ra))
            left_targets.append((entry_col - 1, rb))
        Map._carve_maze_region(
            grid, rng,
            x0=1, x1=entry_col - 1,
            y0=1, y1=rows - 2,
            start=start, must_reach=left_targets,
        )

        # Maze direito: conectar END a cada saida (exit_col+1, row_a/row_b)
        right_targets: list[tuple[int, int]] = []
        for cf in corridors_filled:
            ra, rb = exit_rows(cf)
            right_targets.append((exit_col + 1, ra))
            right_targets.append((exit_col + 1, rb))
        Map._carve_maze_region(
            grid, rng,
            x0=exit_col + 1, x1=cols - 2,
            y0=1, y1=rows - 2,
            start=end, must_reach=right_targets,
        )

        # Temas via intents (primeiros corridor_theme_count corredores)
        themes = ["ice", "fragile", "invert"]
        for i, cf in enumerate(corridors_filled):
            if i >= corridor_theme_count:
                break
            theme = themes[i % len(themes)]
            if theme == "ice":
                # Corredor de gelo: largura 2 (row_a e row_b).
                # 2 blocos de inversão de controles por corredor, em 1/3 e 2/3 do comprimento.
                n = len(cf)
                ice_invert_positions = {max(1, n // 3), max(2, 2 * n // 3)}
                for j, (col, row_a, row_b) in enumerate(cf):
                    tile_intent = "invert" if j in ice_invert_positions else "ice"
                    intents[(col, row_a)] = tile_intent
                    intents[(col, row_b)] = tile_intent
                    forced_intents.add((col, row_a))
                    forced_intents.add((col, row_b))
            elif theme == "fragile":
                # Corredor frágil: 1 bloco de inversão no meio + 70% chance de shrink em n//3.
                n = len(cf)
                fragile_invert_positions = {n // 2}
                shrink_pos = n // 3
                use_shrink = rng.random() < 0.70
                for j, (col, row_a, row_b) in enumerate(cf):
                    if j == shrink_pos and use_shrink:
                        tile_intent = "shrink"
                    elif j in fragile_invert_positions:
                        tile_intent = "invert"
                    else:
                        tile_intent = "fragile"
                    intents[(col, row_a)] = tile_intent
                    intents[(col, row_b)] = tile_intent
                    forced_intents.add((col, row_a))
                    forced_intents.add((col, row_b))
            else:
                for (col, row_a, row_b) in cf:
                    intents[(col, row_a)] = theme
                    intents[(col, row_b)] = theme
                    forced_intents.add((col, row_a))
                    forced_intents.add((col, row_b))

        # Ultimo corredor tematico vira corredor de BlinkBlocks (desafio de timing)
        if corridor_theme_count > 0 and corridors_filled:
            idx = min(corridor_theme_count - 1, len(corridors_filled) - 1)
            cf = corridors_filled[idx]
            # Limpar intents anteriores deste corredor
            for (col, row_a, row_b) in cf:
                intents.pop((col, row_a), None)
                intents.pop((col, row_b), None)
                forced_intents.discard((col, row_a))
                forced_intents.discard((col, row_b))
            # Preencher interior com BlinkBlocks em fases escalonadas.
            # row_a e row_b recebem fases opostas (desfasadas 0.5) — garante que
            # sempre existe pelo menos um tile ativo por coluna.
            # Primeira e última colunas ficam livres (entrada/saída do corredor).
            blink_tiles = cf[1:-1]
            n_blink = len(blink_tiles)
            for j, (col, row_a, row_b) in enumerate(blink_tiles):
                phase_a = (1.0 - j / max(1, n_blink)) % 1.0  # onda da esq→dir (entrada→saída)
                phase_b = (phase_a + 0.5) % 1.0
                intents[(col, row_a)] = "blink"
                intents[(col, row_b)] = "blink"
                forced_intents.add((col, row_a))
                forced_intents.add((col, row_b))
                blink_phases[(col, row_a)] = phase_a
                blink_phases[(col, row_b)] = phase_b
            # Conectores (cf[0] e cf[-1]): 20% de chance de shrink ou invert.
            for (col, row_a, row_b) in (cf[0], cf[-1]):
                if rng.random() < 0.20:
                    power = rng.choice(["shrink", "invert"])
                    intents[(col, row_a)] = power
                    intents[(col, row_b)] = power
                    forced_intents.add((col, row_a))
                    forced_intents.add((col, row_b))

        grid[start[1]][start[0]] = START
        grid[end[1]][end[0]] = END
        return grid, start, (1, 0), intents, forced_intents, blink_phases

    @staticmethod
    def _build_maze_matrix(
        cols: int,
        rows: int,
        rng: random.Random,
        branch_count: int | None,
        branch_length: int | None,
        main_path_bias: float,
        loop_regions: int,
        reward_branches: int,
        false_branches: int,
        false_branch_length: int | None,
        risk_shortcuts: int,
        safe_detours: int,
        dead_end_ratio: float,
    ) -> tuple[
        list[list[int]],
        tuple[int, int],
        tuple[int, int],
        dict[tuple[int, int], str],
    ]:
        """Gera labirinto orgânico por Drunkard Walk dirigido.

        O caminho principal é escavado de START até END com viés para o alvo.
        Depois, walkers secundários criam ramificações e becos sem saída. A
        saída fica em uma célula distante do início, preservando borda segura.
        """
        EMPTY = 0
        FLOOR = 1
        START = 2
        END = 3

        cols = max(8, cols)
        rows = max(8, rows)
        grid: list[list[int]] = [[EMPTY] * cols for _ in range(rows)]
        intents: dict[tuple[int, int], str] = {}

        start = (1, rows // 2)
        end = (cols - 2, rng.randint(1, rows - 2))

        sx, sz = start
        ex, ez = end
        grid[sz][sx] = START
        grid[ez][ex] = END

        def carve(x: int, z: int) -> None:
            if (x, z) == start:
                grid[z][x] = START
            elif (x, z) == end:
                grid[z][x] = END
            else:
                grid[z][x] = FLOOR

        def inside(x: int, z: int) -> bool:
            return 1 <= x < cols - 1 and 1 <= z < rows - 1

        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        main_path: list[tuple[int, int]] = [start]

        def biased_direction(x: int, z: int) -> tuple[int, int]:
            preferred: list[tuple[int, int]] = []
            if ex > x:
                preferred.append((1, 0))
            elif ex < x:
                preferred.append((-1, 0))
            if ez > z:
                preferred.append((0, 1))
            elif ez < z:
                preferred.append((0, -1))

            if preferred and rng.random() < main_path_bias:
                return rng.choice(preferred)
            return rng.choice(directions)

        # Caminho principal: orgânico, mas sempre com fallback Manhattan.
        x, z = start
        max_steps = (cols + rows) * 12
        for _ in range(max_steps):
            if (x, z) == end:
                break
            dx, dz = biased_direction(x, z)
            nx, nz = x + dx, z + dz
            if inside(nx, nz):
                x, z = nx, nz
                carve(x, z)
                main_path.append((x, z))

        while x != ex:
            x += 1 if ex > x else -1
            carve(x, z)
            main_path.append((x, z))
        while z != ez:
            z += 1 if ez > z else -1
            carve(x, z)
            main_path.append((x, z))

        def path_window() -> tuple[int, int]:
            margin = max(3, len(main_path) // 8)
            return margin, max(margin + 1, len(main_path) - margin - 1)

        def choose_segment(min_gap: int) -> tuple[tuple[int, int], tuple[int, int]] | None:
            if len(main_path) < min_gap + 8:
                return None
            lo, hi = path_window()
            if hi - lo < min_gap:
                return None
            a_idx = rng.randint(lo, hi - min_gap)
            b_idx = rng.randint(a_idx + min_gap, hi)
            return main_path[a_idx], main_path[b_idx]

        def is_near_main_path(x: int, z: int) -> bool:
            for px, pz in main_path:
                if abs(px - x) + abs(pz - z) <= 1:
                    return True
            return False

        def mark_route(route: list[tuple[int, int]], intent: str) -> None:
            if not route:
                return
            if intent == "risk":
                choices = ("fragile", "ice", "invert")
                for cell in route[1:-1: max(1, len(route) // 4)]:
                    if cell not in (start, end):
                        intents[cell] = rng.choice(choices)
            elif intent == "safe":
                mid = route[len(route) // 2]
                if mid not in (start, end):
                    intents[mid] = "heal"
            elif intent == "loop":
                if len(route) > 4:
                    cell = route[len(route) // 2]
                    if cell not in (start, end):
                        intents[cell] = rng.choice(("ice", "heal"))

        def carve_to(x: int, z: int, tx: int, tz: int, route: list[tuple[int, int]]) -> tuple[int, int]:
            while (x, z) != (tx, tz):
                can_x = x != tx
                can_z = z != tz
                if can_x and (not can_z or rng.random() < 0.55):
                    x += 1 if tx > x else -1
                elif can_z:
                    z += 1 if tz > z else -1
                if not inside(x, z):
                    break
                carve(x, z)
                route.append((x, z))
            return x, z

        def carve_detour(a: tuple[int, int], b: tuple[int, int], intent: str) -> None:
            ax, az = a
            bx, bz = b
            route = [a]
            span = max(3, abs(ax - bx) + abs(az - bz))
            offset = max(2, min(rows // 3, span // 3))
            if intent == "safe":
                offset += 2
            if rng.random() < 0.5:
                offset = -offset

            if rng.random() < 0.5:
                wz = max(1, min(rows - 2, (az + bz) // 2 + offset))
                x1, z1 = carve_to(ax, az, ax, wz, route)
                x2, z2 = carve_to(x1, z1, bx, wz, route)
                carve_to(x2, z2, bx, bz, route)
            else:
                wx = max(1, min(cols - 2, (ax + bx) // 2 + offset))
                x1, z1 = carve_to(ax, az, wx, az, route)
                x2, z2 = carve_to(x1, z1, wx, bz, route)
                carve_to(x2, z2, bx, bz, route)
            mark_route(route, intent)

        motif_gap = max(6, (cols + rows) // 8)
        for _ in range(loop_regions):
            segment = choose_segment(motif_gap)
            if segment is not None:
                carve_detour(*segment, intent="loop")
        for _ in range(safe_detours):
            segment = choose_segment(motif_gap + 2)
            if segment is not None:
                carve_detour(*segment, intent="safe")
        for _ in range(risk_shortcuts):
            segment = choose_segment(max(4, motif_gap - 2))
            if segment is not None:
                carve_detour(*segment, intent="risk")

        def carve_reward_branch() -> None:
            if len(main_path) < 8:
                return
            lo, hi = path_window()
            x, z = main_path[rng.randint(lo, hi)]
            length = rng.randint(3, max(4, branch_length or 6))
            dx, dz = rng.choice(directions)
            route: list[tuple[int, int]] = []
            for _ in range(length):
                if rng.random() < 0.25:
                    dx, dz = rng.choice(directions)
                nx, nz = x + dx, z + dz
                if not inside(nx, nz):
                    break
                x, z = nx, nz
                carve(x, z)
                route.append((x, z))
            if route:
                reward = route[-1]
                if reward not in (start, end):
                    intents[reward] = rng.choice(("grow", "heal"))

        for _ in range(reward_branches):
            carve_reward_branch()

        def carve_false_branch() -> None:
            if len(main_path) < 10:
                return
            lo, hi = path_window()
            x, z = main_path[rng.randint(lo, hi)]
            max_len = false_branch_length if false_branch_length is not None else max(5, branch_length or 8)
            length = rng.randint(max(4, max_len // 2), max_len)
            dx, dz = rng.choice(directions)
            route: list[tuple[int, int]] = []
            last_dir = (dx, dz)

            for _ in range(length):
                candidates = directions[:]
                rng.shuffle(candidates)
                candidates.insert(0, last_dir)
                moved = False

                for ndx, ndz in candidates:
                    nx, nz = x + ndx, z + ndz
                    if not inside(nx, nz):
                        continue
                    if route and is_near_main_path(nx, nz):
                        continue
                    x, z = nx, nz
                    carve(x, z)
                    route.append((x, z))
                    last_dir = (ndx, ndz)
                    moved = True
                    break

                if not moved:
                    break

            if len(route) >= 3:
                tail = route[-1]
                if tail not in (start, end):
                    intents[tail] = rng.choice(("ice", "grow"))

        for _ in range(false_branches):
            carve_false_branch()

        # Ramificações: criam escolhas falsas e rotas laterais.
        floor_cells = [
            (x, z)
            for z in range(1, rows - 1)
            for x in range(1, cols - 1)
            if grid[z][x] in (FLOOR, START)
        ]
        if branch_count is None:
            branch_count = max(4, (cols * rows) // 70)
        if branch_length is None:
            branch_length = max(4, (cols + rows) // 7)

        for _ in range(branch_count):
            if not floor_cells:
                break
            x, z = rng.choice(floor_cells)
            last_dir: tuple[int, int] | None = None
            steps = rng.randint(max(2, branch_length // 2), branch_length)
            should_dead_end = rng.random() < dead_end_ratio
            for _step in range(steps):
                candidates = directions[:]
                rng.shuffle(candidates)
                if last_dir is not None and rng.random() < 0.55:
                    candidates.insert(0, last_dir)

                moved = False
                for dx, dz in candidates:
                    nx, nz = x + dx, z + dz
                    if not inside(nx, nz):
                        continue
                    x, z = nx, nz
                    carve(x, z)
                    floor_cells.append((x, z))
                    last_dir = (dx, dz)
                    moved = True
                    if should_dead_end and (x, z) not in (start, end) and _step == steps - 1:
                        intents[(x, z)] = "ice"
                    break
                if not moved:
                    break

        grid[sz][sx] = START
        grid[ez][ex] = END
        return grid, start, (1, 0), intents

    @staticmethod
    def _remove_dead_ends(matrix: list[list[int]], start: tuple[int, int]) -> None:
        """Remove iterativamente tiles de chão com apenas 1 vizinho walkable (becos)."""
        if not matrix or not matrix[0]:
            return
        rows = len(matrix)
        cols = len(matrix[0])
        walkable = {1, 2, 3}
        changed = True
        while changed:
            changed = False
            for r in range(rows):
                for c in range(cols):
                    if matrix[r][c] != 1:  # preserva START(2), END(3) e paredes(0)
                        continue
                    neighbors = sum(
                        1 for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= c + dc < cols and 0 <= r + dr < rows
                        and matrix[r + dr][c + dc] in walkable
                    )
                    if neighbors <= 1:
                        matrix[r][c] = 0
                        changed = True

    @staticmethod
    def _has_path(matrix: list[list[int]], start: tuple[int, int]) -> bool:
        """Valida se existe caminho caminhável do START até END."""
        return bool(Map._path_analysis(matrix, start)[1])

    @staticmethod
    def _path_analysis(
        matrix: list[list[int]],
        start: tuple[int, int],
    ) -> tuple[dict[tuple[int, int], int], set[tuple[int, int]]]:
        """Retorna distâncias do START e um caminho crítico START→END."""
        if not matrix or not matrix[0]:
            return {}, set()

        cols = len(matrix[0])
        rows = len(matrix)
        sx, sz = start
        if not (0 <= sx < cols and 0 <= sz < rows):
            return {}, set()

        walkable = {1, 2, 3}
        queue: deque[tuple[int, int]] = deque([(sx, sz)])
        seen = {(sx, sz)}
        distance = {(sx, sz): 0}
        parent: dict[tuple[int, int], tuple[int, int]] = {}
        end: tuple[int, int] | None = None

        while queue:
            x, z = queue.popleft()
            if matrix[z][x] == 3:
                end = (x, z)
                break
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, nz = x + dx, z + dz
                if not (0 <= nx < cols and 0 <= nz < rows):
                    continue
                if (nx, nz) in seen or matrix[nz][nx] not in walkable:
                    continue
                seen.add((nx, nz))
                distance[(nx, nz)] = distance[(x, z)] + 1
                parent[(nx, nz)] = (x, z)
                queue.append((nx, nz))

        critical_path: set[tuple[int, int]] = set()
        if end is not None:
            current = end
            while current != (sx, sz):
                critical_path.add(current)
                current = parent[current]
            critical_path.add((sx, sz))
        return distance, critical_path

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
        prob_ice: float,
        prob_invert: float,
        prob_fragile: float,
        intents: dict[tuple[int, int], str] | None = None,
        challenge_profile: str = "medium",
        cluster_zones: list | None = None,
        combo_sequences: list | None = None,
        forced_intents: set[tuple[int, int]] | None = None,
        blink_phases: dict[tuple[int, int], float] | None = None,
    ) -> "Map":
        """Converte a matriz de inteiros num Map populado com Blocks.

        Cada célula de caminho rola um dado uniforme. Os intervalos são
        construídos dinamicamente a partir das probabilidades individuais,
        permitindo que qualquer delas seja 0 sem distorcer as demais.
        """
        m = Map()
        m.start = start
        m.direction = direction
        intents = intents or {}
        cluster_zones = cluster_zones or []
        combo_sequences = combo_sequences or []
        distance_from_start, critical_path = Map._path_analysis(matrix, start)
        cols = len(matrix[0]) if matrix else 0
        rows = len(matrix)
        max_distance = max(distance_from_start.values(), default=1)
        profile = challenge_profile if challenge_profile in {"easy", "medium", "hard"} else "medium"

        danger_powers = {"shrink", "ice", "invert", "fragile"}
        critical_dangers = {"fragile"}
        reward_powers = {"heal", "grow"}

        def zone_for(col: int, row: int) -> float:
            return distance_from_start.get((col, row), 0) / max_distance

        def intent_allowed(name: str, zone: float, is_critical: bool) -> bool:
            if zone < 0.18 and name in danger_powers:
                return False
            if zone < 0.28 and name in {"fragile", "invert"}:
                return False
            if is_critical and name in critical_dangers:
                return False
            return True

        def _apply_cluster(name: str, zone: float, w: float) -> float:
            for zmin, zmax, cname, mult in cluster_zones:
                if cname == name and zmin <= zone < zmax:
                    return w * mult
            return w

        def zone_weight(name: str, base: float, zone: float, is_critical: bool) -> float:
            if base <= 0.0:
                return 0.0
            if not intent_allowed(name, zone, is_critical):
                return 0.0

            if zone < 0.20:
                multipliers = {
                    "easy": {"heal": 0.65, "grow": 0.45},
                    "medium": {"heal": 0.25, "grow": 0.20},
                    "hard": {"heal": 0.08, "grow": 0.08},
                }
                return _apply_cluster(name, zone, base * multipliers[profile].get(name, 0.0))

            if zone < 0.45:
                multipliers = {
                    "easy": {
                        "heal": 1.15, "grow": 1.0,
                        "ice": 0.45, "shrink": 0.25,
                        "invert": 0.20, "fragile": 0.20,
                    },
                    "medium": {
                        "heal": 0.85, "grow": 0.80,
                        "ice": 0.70, "shrink": 0.60,
                        "invert": 0.45, "fragile": 0.45,
                    },
                    "hard": {
                        "heal": 0.35, "grow": 0.55,
                        "ice": 0.85, "shrink": 0.80,
                        "invert": 0.70, "fragile": 0.75,
                    },
                }
                return _apply_cluster(name, zone, base * multipliers[profile].get(name, 1.0))

            if zone < 0.75:
                multipliers = {
                    "easy": {
                        "heal": 1.0, "grow": 1.0,
                        "ice": 0.70, "shrink": 0.50,
                        "invert": 0.45, "fragile": 0.45,
                    },
                    "medium": {
                        "heal": 0.65, "grow": 0.85,
                        "ice": 1.0, "shrink": 0.95,
                        "invert": 0.85, "fragile": 0.85,
                    },
                    "hard": {
                        "heal": 0.25, "grow": 0.65,
                        "ice": 1.25, "shrink": 1.15,
                        "invert": 1.15, "fragile": 1.25,
                    },
                }
                return _apply_cluster(name, zone, base * multipliers[profile].get(name, 1.0))

            multipliers = {
                "easy": {
                    "heal": 0.75, "grow": 0.80,
                    "ice": 0.80, "shrink": 0.60,
                    "invert": 0.50, "fragile": 0.55,
                },
                "medium": {
                    "heal": 0.45, "grow": 0.70,
                    "ice": 1.15, "shrink": 1.0,
                    "invert": 1.0, "fragile": 1.0,
                },
                "hard": {
                    "heal": 0.12, "grow": 0.50,
                    "ice": 1.45, "shrink": 1.30,
                    "invert": 1.30, "fragile": 1.55,
                },
            }
            return _apply_cluster(name, zone, base * multipliers[profile].get(name, 1.0))

        # Tabela de (nome, prob) para blocos especiais — ordem importa
        _specials = [
            ("heal",       prob_heal),
            ("shrink",     prob_shrink),
            ("grow",       prob_grow),
            ("ice",        prob_ice),
            ("invert",     prob_invert),
            ("fragile",    prob_fragile),
        ]
        # Anti-clustering: controla vizinhança de poderes repetidos
        _recency: dict[tuple[int, int], dict[str, int]] = {}
        _COOLDOWN = 3

        def _apply_recency(col: int, row: int, power_name: str) -> None:
            for nc in range(col - 2, col + 3):
                for nr in range(row - 2, row + 3):
                    _recency.setdefault((nc, nr), {})[power_name] = _COOLDOWN

        def choose_special(col: int, row: int) -> str | None:
            zone = zone_for(col, row)
            is_critical = (col, row) in critical_path
            nbr = _recency.get((col, row), {})
            weighted = []
            for name, base in _specials:
                w = zone_weight(name, base, zone, is_critical)
                if w <= 0.0:
                    continue
                cd = nbr.get(name, 0)
                if cd > 0:
                    w *= (1.0 - 0.7 * cd / _COOLDOWN)
                if w > 0.0:
                    weighted.append((name, w))
            total = sum(weight for _, weight in weighted)
            if total <= 0.0 or rng.random() >= min(total, 0.42):
                return None
            pick = rng.random() * total
            acc = 0.0
            for name, weight in weighted:
                acc += weight
                if pick <= acc:
                    return name
            return weighted[-1][0]

        for row_idx, row in enumerate(matrix):
            for col_idx, cell in enumerate(row):
                pos = Position(x=float(col_idx), y=0.0, z=float(row_idx))

                if cell == 1:
                    block: Block | None = None
                    intent = intents.get((col_idx, row_idx))
                    zone = zone_for(col_idx, row_idx)
                    is_critical = (col_idx, row_idx) in critical_path
                    coord = (col_idx, row_idx)
                    is_forced = forced_intents is not None and coord in forced_intents
                    if intent is not None and (is_forced or intent_allowed(intent, zone, is_critical)):
                        if intent == "blink" and blink_phases:
                            phase = blink_phases.get(coord, 0.0)
                            block = BlinkBlock(phase_offset=phase, position=pos)
                        else:
                            block = _make_powered(intent, pos)
                        _apply_recency(col_idx, row_idx, intent)
                    else:
                        special = choose_special(col_idx, row_idx)
                        if special is not None:
                            block = _make_powered(special, pos)
                            _apply_recency(col_idx, row_idx, special)
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

        # Inserir combo_sequences no caminho crítico
        if combo_sequences and distance_from_start:
            cp_sorted = sorted(critical_path, key=lambda pos: distance_from_start.get(pos, 0))
            for seq in combo_sequences:
                n = len(seq)
                if n == 0:
                    continue
                placed = False
                for i in range(len(cp_sorted) - n):
                    segment = cp_sorted[i:i + n]
                    z_start = zone_for(*segment[0])
                    z_end   = zone_for(*segment[-1])
                    if z_start < 0.28 or z_end > 0.88:
                        continue
                    # Verificar que todos os tiles são floor sem poder existente
                    if all(
                        m._grid.get(p) is not None and not m._grid[p].is_powered
                        for p in segment
                    ):
                        for p, pname in zip(segment, seq):
                            new_pos = Position(x=float(p[0]), y=0.0, z=float(p[1]))
                            m._grid[p] = _make_powered(pname, new_pos)
                        placed = True
                        break

        return m
