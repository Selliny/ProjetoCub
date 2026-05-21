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
        if isinstance(block, EndBlock):
            return "end"
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
        prob_portal: float = PROB_PORTAL,
        prob_ice: float = PROB_ICE,
        prob_invert: float = PROB_INVERT,
        prob_fragile: float = PROB_FRAGILE,
        prob_bounce: float = PROB_BOUNCE,
        prob_slow: float = PROB_SLOW,
        prob_checkpoint: float = PROB_CHECKPOINT,
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
        else:
            raise ValueError(f"Gerador de mapa desconhecido: {generator!r}")

        if not cls._has_path(matrix, start):
            raise RuntimeError("Mapa gerado sem caminho válido entre START e END.")

        return cls._matrix_to_map(
            matrix, start, direction, rng,
            prob_heal, prob_shrink, prob_grow, prob_portal,
            prob_ice, prob_invert, prob_fragile, prob_bounce,
            prob_slow, prob_checkpoint, intents, challenge_profile,
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
                choices = ("fragile", "ice", "bounce", "slow")
                for cell in route[1:-1: max(1, len(route) // 4)]:
                    if cell not in (start, end):
                        intents[cell] = rng.choice(choices)
            elif intent == "safe":
                mid = route[len(route) // 2]
                if mid not in (start, end):
                    intents[mid] = "checkpoint" if rng.random() < 0.45 else "heal"
            elif intent == "loop":
                if len(route) > 4:
                    cell = route[len(route) // 2]
                    if cell not in (start, end):
                        intents[cell] = rng.choice(("slow", "ice", "heal"))

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
                    intents[reward] = rng.choice(("grow", "checkpoint", "slow"))

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
                    intents[tail] = rng.choice(("slow", "ice", "grow"))

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
                        intents[(x, z)] = rng.choice(("slow", "ice"))
                    break
                if not moved:
                    break

        grid[sz][sx] = START
        grid[ez][ex] = END
        return grid, start, (1, 0), intents

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
        prob_portal: float,
        prob_ice: float,
        prob_invert: float,
        prob_fragile: float,
        prob_bounce: float,
        prob_slow: float,
        prob_checkpoint: float,
        intents: dict[tuple[int, int], str] | None = None,
        challenge_profile: str = "medium",
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
        distance_from_start, critical_path = Map._path_analysis(matrix, start)
        cols = len(matrix[0]) if matrix else 0
        rows = len(matrix)
        max_distance = max(distance_from_start.values(), default=1)
        profile = challenge_profile if challenge_profile in {"easy", "medium", "hard"} else "medium"

        danger_powers = {"shrink", "portal", "ice", "invert", "fragile", "bounce", "slow"}
        critical_dangers = {"portal", "fragile", "bounce"}
        reward_powers = {"heal", "grow", "checkpoint"}

        def zone_for(col: int, row: int) -> float:
            return distance_from_start.get((col, row), 0) / max_distance

        def intent_allowed(name: str, zone: float, is_critical: bool) -> bool:
            if zone < 0.18 and name in danger_powers:
                return False
            if zone < 0.28 and name in {"portal", "fragile", "bounce", "invert"}:
                return False
            if zone > 0.88 and name in {"portal", "checkpoint"}:
                return False
            if is_critical and name in critical_dangers:
                return False
            return True

        def zone_weight(name: str, base: float, zone: float, is_critical: bool) -> float:
            if base <= 0.0:
                return 0.0
            if not intent_allowed(name, zone, is_critical):
                return 0.0

            if zone < 0.20:
                multipliers = {
                    "easy": {"heal": 0.65, "grow": 0.45, "checkpoint": 0.70},
                    "medium": {"heal": 0.25, "grow": 0.20, "checkpoint": 0.45},
                    "hard": {"heal": 0.08, "grow": 0.08, "checkpoint": 0.20},
                }
                return base * multipliers[profile].get(name, 0.0)

            if zone < 0.45:
                multipliers = {
                    "easy": {
                        "heal": 1.15, "grow": 1.0, "checkpoint": 1.25,
                        "ice": 0.45, "slow": 0.35, "shrink": 0.25,
                        "invert": 0.20, "fragile": 0.20, "bounce": 0.25, "portal": 0.10,
                    },
                    "medium": {
                        "heal": 0.85, "grow": 0.80, "checkpoint": 1.0,
                        "ice": 0.70, "slow": 0.65, "shrink": 0.60,
                        "invert": 0.45, "fragile": 0.45, "bounce": 0.50, "portal": 0.25,
                    },
                    "hard": {
                        "heal": 0.35, "grow": 0.55, "checkpoint": 0.75,
                        "ice": 0.85, "slow": 0.85, "shrink": 0.80,
                        "invert": 0.70, "fragile": 0.75, "bounce": 0.75, "portal": 0.35,
                    },
                }
                return base * multipliers[profile].get(name, 1.0)

            if zone < 0.75:
                multipliers = {
                    "easy": {
                        "heal": 1.0, "grow": 1.0, "checkpoint": 1.0,
                        "ice": 0.70, "slow": 0.65, "shrink": 0.50,
                        "invert": 0.45, "fragile": 0.45, "bounce": 0.55, "portal": 0.25,
                    },
                    "medium": {
                        "heal": 0.65, "grow": 0.85, "checkpoint": 0.90,
                        "ice": 1.0, "slow": 0.95, "shrink": 0.95,
                        "invert": 0.85, "fragile": 0.85, "bounce": 0.85, "portal": 0.55,
                    },
                    "hard": {
                        "heal": 0.25, "grow": 0.65, "checkpoint": 0.55,
                        "ice": 1.25, "slow": 1.20, "shrink": 1.15,
                        "invert": 1.15, "fragile": 1.25, "bounce": 1.10, "portal": 0.65,
                    },
                }
                return base * multipliers[profile].get(name, 1.0)

            multipliers = {
                "easy": {
                    "heal": 0.75, "grow": 0.80, "checkpoint": 0.35,
                    "ice": 0.80, "slow": 0.70, "shrink": 0.60,
                    "invert": 0.50, "fragile": 0.55, "bounce": 0.55, "portal": 0.15,
                },
                "medium": {
                    "heal": 0.45, "grow": 0.70, "checkpoint": 0.25,
                    "ice": 1.15, "slow": 1.05, "shrink": 1.0,
                    "invert": 1.0, "fragile": 1.0, "bounce": 0.95, "portal": 0.30,
                },
                "hard": {
                    "heal": 0.12, "grow": 0.50, "checkpoint": 0.0,
                    "ice": 1.45, "slow": 1.35, "shrink": 1.30,
                    "invert": 1.30, "fragile": 1.55, "bounce": 1.25, "portal": 0.35,
                },
            }
            return base * multipliers[profile].get(name, 1.0)

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
        def choose_special(col: int, row: int) -> str | None:
            zone = zone_for(col, row)
            is_critical = (col, row) in critical_path
            weighted = [
                (name, zone_weight(name, base, zone, is_critical))
                for name, base in _specials
            ]
            weighted = [(name, weight) for name, weight in weighted if weight > 0.0]
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
                    if intent is not None and intent_allowed(intent, zone, is_critical):
                        block = _make_powered(intent, pos)
                    else:
                        special = choose_special(col_idx, row_idx)
                        if special is not None:
                            block = _make_powered(special, pos)
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
