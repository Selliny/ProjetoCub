"""Entidade jogável principal: cubo grid-based controlado por tombamento."""

from __future__ import annotations

import math
from enum import Enum
from typing import Protocol

from OpenGL.GL import (
    GL_BLEND,
    GL_LINES,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_SRC_ALPHA,
    glBegin,
    glBlendFunc,
    glColor4f,
    glDisable,
    glEnable,
    glEnd,
    glLineWidth,
    glRotatef,
    glScalef,
    glTranslatef,
    glVertex3f,
)

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size


class MovementValidator(Protocol):
    def can_move_to(self, grid_x: int, grid_z: int) -> bool:
        """Retorna True se o cubo pode se mover para a célula informada."""
        ...

    def get_tile_type(self, grid_x: int, grid_z: int) -> str:
        """Retorna o tipo da célula para reações do cubo."""
        ...

    def get_power(self, grid_x: int, grid_z: int) -> str | None:
        """Retorna o poder do bloco na célula, se houver."""
        ...


class CubeState(Enum):
    IDLE      = "idle"
    ROLLING   = "rolling"
    SLIDING   = "sliding"
    FALLING   = "falling"
    FADING_IN = "fading_in"


class Cube:
    # Durações e distâncias das animações (em segundos / unidades).
    ROLL_DURATION: float = 0.25
    FALL_DURATION: float = 0.5
    FALL_DISTANCE: float = 3.0
    FADE_DURATION: float = 0.4
    TILE_SIZE:     float = 1.0

    # Número padrão de vidas com que o cubo começa.
    MAX_LIVES: int = 3

    # Duração dos efeitos temporários
    INVERT_DURATION:     float = 5.0   # segundos de controles invertidos
    ICE_STEPS:           int   = 6     # passos do deslize de gelo
    SLIDE_STEP_DURATION: float = 0.09  # duração de cada passo do deslize (s)

    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
        lives: int = MAX_LIVES,
    ) -> None:
        start = position if position is not None else Position(0.0, 0.5, 0.0)
        self.grid_x = round(start.x / Cube.TILE_SIZE)
        self.grid_z = round(start.z / Cube.TILE_SIZE)
        self._spawn_grid_x = self.grid_x
        self._spawn_grid_z = self.grid_z
        self._spawn_y = start.y
        self.position = Position(
            float(self.grid_x) * Cube.TILE_SIZE,
            start.y,
            float(self.grid_z) * Cube.TILE_SIZE,
        )
        self.color = color if color is not None else Color(1.0, 0.0, 0.0)
        self.size = size if size is not None else Size.uniform(1.0)

        self.lives: int = max(1, lives)
        self.max_lives: int = self.lives

        self.state = CubeState.IDLE
        self.step_size = 1.0
        self._roll_t: float = 0.0
        self._fall_t: float = 0.0
        self._fall_offset_y: float = 0.0
        self._fade_t: float = 0.0
        self._alpha: float = 1.0
        self._pending_dx: int = 0
        self._pending_dz: int = 0
        self._queued: tuple[int, int, MovementValidator | None] | None = None
        self._validator: MovementValidator | None = None

        self._last_valid_grid_x: int = self.grid_x
        self._last_valid_grid_z: int = self.grid_z

        self._total_angle_z: float = 0.0
        self._total_angle_x: float = 0.0

        # Ice slide: estado de deslizamento plano
        self._ice_slide_dx: int = 0
        self._ice_slide_dz: int = 0
        self._slide_dx: int = 0
        self._slide_dz: int = 0
        self._slide_steps: int = 0           # passos restantes
        self._slide_t: float = 0.0           # progresso do passo atual (0→1)
        self._slide_from_x: float = 0.0      # posição XZ de início do passo
        self._slide_from_z: float = 0.0
        self._slide_validator: MovementValidator | None = None

        # Invert: tempo restante de controles invertidos
        self._invert_timer: float = 0.0

        # Estado de vitória
        self._reached_end: bool = False

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @property
    def controls_inverted(self) -> bool:
        return self._invert_timer > 0.0

    @property
    def reached_end(self) -> bool:
        return self._reached_end

    @property
    def active_effects(self) -> list[dict]:
        """Efeitos temporários ativos com tempo/contagem restante para o HUD."""
        out = []
        if self._invert_timer > 0.0:
            out.append({
                "name": "INV",
                "remaining": self._invert_timer,
                "max": 5.0,
                "color": (0.85, 0.0, 0.55, 1.0),
            })
        return out

    def try_roll(
        self,
        dx: int,
        dz: int,
        validator: MovementValidator | None = None,
    ) -> bool:
        """Inicia um roll se estiver livre ou enfileira 1 comando durante o roll."""
        dx, dz = self._normalize_direction(dx, dz)
        if dx == 0 and dz == 0:
            return False

        if self.state == CubeState.ROLLING:
            return self._enqueue_roll(dx, dz, validator)

        if self.state not in (CubeState.IDLE,):
            return False

        # Verificar bloqueios antes de iniciar o roll.
        # Calcula a célula de destino real (grid_x + dx*step_size) para evitar
        # bloqueio antecipado quando o cubo está pequeno (step_size=0.5, offset ±0.25).
        if validator is not None and hasattr(validator, "can_move_to"):
            dest_x = self.grid_x + dx * self.step_size
            dest_z = self.grid_z + dz * self.step_size
            target_x = round(dest_x)
            target_z = round(dest_z)
            cube_scale = self.size.sx
            tile = validator.get_tile_type(target_x, target_z)
            if tile == "floor" and not validator.can_move_to(target_x, target_z, cube_scale):  # type: ignore[call-arg]
                return False

        self._start_roll(dx, dz, validator)
        return True

    def start_roll(self, direction: int, axis: str = "z") -> None:
        """Compatibilidade com API antiga: converte eixo em dx/dz."""
        if axis == "z":
            self.try_roll(0, direction)
        elif axis == "x":
            self.try_roll(direction, 0)

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """Avança animações e timers usando delta time do frame."""

        # Timers de efeito temporário
        if self._invert_timer > 0.0:
            self._invert_timer = max(0.0, self._invert_timer - dt)

        if self.state == CubeState.ROLLING:
            self._roll_t = min(self._roll_t + dt / Cube.ROLL_DURATION, 1.0)
            if self._roll_t >= 1.0:
                self._finish_roll()
            return

        if self.state == CubeState.SLIDING:
            self._slide_t = min(self._slide_t + dt / Cube.SLIDE_STEP_DURATION, 1.0)
            if self._slide_t >= 1.0:
                self._finish_slide_step()
            return

        if self.state == CubeState.FALLING:
            self._fall_t = min(self._fall_t + dt / Cube.FALL_DURATION, 1.0)
            self._fall_offset_y = -Cube.FALL_DISTANCE * self._fall_t
            if self._fall_t >= 1.0:
                self.grid_x = float(self._last_valid_grid_x)
                self.grid_z = float(self._last_valid_grid_z)
                # Re-aplica o offset do cubo encolhido para reaparecer na borda correta
                if self.step_size == 0.5:
                    self.grid_x -= 0.25
                    self.grid_z += 0.25
                self._sync_position_from_grid()
                self._total_angle_z = 0.0
                self._total_angle_x = 0.0
                self._fall_offset_y = 0.0
                self._fade_t = 0.0
                self._alpha = 0.0
                self.state = CubeState.FADING_IN
            return

        if self.state == CubeState.FADING_IN:
            self._fade_t += dt / Cube.FADE_DURATION
            self._alpha = min(1.0, self._fade_t)
            if self._fade_t >= 1.0:
                self._alpha = 1.0
                self._last_valid_grid_x = round(self.grid_x)
                self._last_valid_grid_z = round(self.grid_z)
                self.state = CubeState.IDLE
            return

    @property
    def is_dead(self) -> bool:
        return self.lives <= 0

    def is_moving(self) -> bool:
        return self.state in (CubeState.ROLLING, CubeState.SLIDING)

    def is_rolling(self) -> bool:
        return self.state == CubeState.ROLLING

    def get_grid_position(self) -> tuple[int, int]:
        return self.grid_x, self.grid_z

    def get_next_position(self, dx: int, dz: int) -> tuple[int, int]:
        dx, dz = self._normalize_direction(dx, dz)
        return self.grid_x + dx, self.grid_z + dz

    def on_tile_enter(self, tile_type: str) -> None:
        if tile_type == "end":
            self._reached_end = True
            return
        if tile_type != "floor":
            self._start_fall()

    def respawn(self) -> None:
        self.grid_x = self._spawn_grid_x
        self.grid_z = self._spawn_grid_z
        self._last_valid_grid_x = self._spawn_grid_x
        self._last_valid_grid_z = self._spawn_grid_z
        self._sync_position_from_grid()
        self.state = CubeState.IDLE
        self._roll_t = 0.0
        self._fall_t = 0.0
        self._fall_offset_y = 0.0
        self._fade_t = 0.0
        self._alpha = 1.0
        self._pending_dx = 0
        self._pending_dz = 0
        self._queued = None
        self._validator = None
        self._total_angle_z = 0.0
        self._total_angle_x = 0.0
        self._ice_slide_dx = 0
        self._ice_slide_dz = 0
        self._slide_dx = 0
        self._slide_dz = 0
        self._slide_steps = 0
        self._slide_t = 0.0
        self._slide_validator = None

        self._reached_end = False
    def apply_transform(self) -> None:
        if self.state == CubeState.ROLLING:
            self._apply_roll_transform()
            return

        if self.state == CubeState.SLIDING:
            self._apply_slide_transform()
            return

        self._sync_position_from_grid()
        y_offset = self._fall_offset_y if self.state == CubeState.FALLING else 0.0
        glTranslatef(self.position.x, self.position.y + y_offset, self.position.z)
        self._apply_accumulated_rotation()
        self._apply_size()

    def draw(self) -> None:
        a = self._alpha
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Faces: roxo escuro, topo levemente mais claro
        glBegin(GL_QUADS)
        glColor4f(0.18, 0.0, 0.35, a)
        # frente
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5,  0.5)
        # trás
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5, -0.5)
        # topo
        glColor4f(0.30, 0.0, 0.55, a)
        glVertex3f(-0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5,  0.5)
        # base
        glColor4f(0.10, 0.0, 0.22, a)
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5, -0.5)
        # direita
        glColor4f(0.14, 0.0, 0.28, a)
        glVertex3f( 0.5, -0.5,  0.5); glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5,  0.5)
        # esquerda
        glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5, -0.5)
        glEnd()

        # Outline neon magenta (sem glow)
        glColor4f(1.0, 0.0, 1.0, a)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # topo
        glVertex3f(-0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5, -0.5)
        # base
        glVertex3f(-0.5, -0.5, -0.5); glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5); glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f(-0.5, -0.5, -0.5)
        # pilares
        glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5, -0.5,  0.5); glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f(-0.5,  0.5,  0.5)
        glEnd()
        glLineWidth(1.0)

        if a >= 1.0:
            glDisable(GL_BLEND)

    # ------------------------------------------------------------------
    # Compatibilidade e utilidades
    # ------------------------------------------------------------------

    def move(self, dx: float, dy: float, dz: float) -> None:
        self.position.translate(dx, dy, dz)
        self.grid_x = round(self.position.x / Cube.TILE_SIZE)
        self.grid_z = round(self.position.z / Cube.TILE_SIZE)

    def scale(self, factor: float) -> None:
        self.size.sx *= factor
        self.size.sy *= factor
        self.size.sz *= factor

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _normalize_direction(self, dx: int, dz: int) -> tuple[int, int]:
        dx = 0 if dx == 0 else (1 if dx > 0 else -1)
        dz = 0 if dz == 0 else (1 if dz > 0 else -1)
        if dx != 0 and dz != 0:
            return 0, 0
        return dx, dz

    def _is_walkable(self, tile: str) -> bool:
        return tile in ("floor", "end")

    def _enqueue_roll(self, dx: int, dz: int, validator: MovementValidator | None) -> bool:
        if self._queued is not None:
            return False
        self._queued = (dx, dz, validator)
        return True

    def _start_roll(self, dx: int, dz: int, validator: MovementValidator | None) -> None:
        self._pending_dx = dx
        self._pending_dz = dz
        self._roll_t = 0.0
        self._validator = validator
        self.state = CubeState.ROLLING
        self._sync_position_from_grid()

    def _finish_roll(self) -> None:
        """Finaliza o roll com snap no grid e reage ao tile destino."""
        saved_dx = self._pending_dx
        saved_dz = self._pending_dz

        self.grid_x += saved_dx * self.step_size
        self.grid_z += saved_dz * self.step_size

        if saved_dz != 0:
            self._total_angle_z += 90.0 * saved_dz
        elif saved_dx != 0:
            self._total_angle_x += -90.0 * saved_dx

        self._pending_dx = 0
        self._pending_dz = 0
        self._roll_t = 0.0
        self.state = CubeState.IDLE
        self._sync_position_from_grid()

        validator = self._validator
        if validator is not None:
            map_x = round(self.grid_x)
            map_z = round(self.grid_z)
            tile  = validator.get_tile_type(map_x, map_z)
            power = validator.get_power(map_x, map_z)

            # ── Poderes existentes ─────────────────────────────────────
            if power == "shrink" and self.step_size != 0.5:
                self.step_size = 0.5
                self.size.sx = self.size.sy = self.size.sz = 0.5
                self.grid_x -= 0.25
                self.grid_z += 0.25

            elif power == "grow" and self.step_size == 0.5:
                self.step_size = 1.0
                self.size.sx = self.size.sy = self.size.sz = 1.0
                self.grid_x = round(self.grid_x)
                self.grid_z = round(self.grid_z)
                if hasattr(validator, "consume_power"):
                    validator.consume_power(map_x, map_z)  # type: ignore[union-attr]

            elif power == "heal" and self.lives < self.max_lives:
                self.lives += 1
                if hasattr(validator, "consume_power"):
                    validator.consume_power(map_x, map_z)  # type: ignore[union-attr]

            # ── Novos poderes ──────────────────────────────────────────
            elif power == "ice":
                # Guarda direção — slide será iniciado abaixo após tile_enter
                self._ice_slide_dx = saved_dx
                self._ice_slide_dz = saved_dz

            elif power == "invert":
                # Cancela se já estava invertido (dois negativos = positivo)
                if self._invert_timer > 0.0:
                    self._invert_timer = 0.0
                else:
                    self._invert_timer = Cube.INVERT_DURATION
                if hasattr(validator, "consume_power"):
                    validator.consume_power(map_x, map_z)  # type: ignore[union-attr]

            elif power == "fragile":
                # Avisa o Map para iniciar contagem regressiva de desativação
                if hasattr(validator, "schedule_fragile"):
                    validator.schedule_fragile(map_x, map_z)  # type: ignore[union-attr]

            if self._is_walkable(tile) and power not in ("fragile", "blink"):
                self._last_valid_grid_x = round(self.grid_x)
                self._last_valid_grid_z = round(self.grid_z)
            self.on_tile_enter(tile)

        self._validator = None

        if self.state != CubeState.IDLE:
            self._queued = None
            self._ice_slide_dx = 0
            self._ice_slide_dz = 0
            return

        # Slide de gelo tem prioridade sobre a fila normal
        if self._ice_slide_dx != 0 or self._ice_slide_dz != 0:
            sdx, sdz = self._ice_slide_dx, self._ice_slide_dz
            self._ice_slide_dx = 0
            self._ice_slide_dz = 0
            self._start_ice_slide(sdx, sdz, validator)
            return

        if self._queued is not None:
            dx, dz, validator = self._queued
            self._queued = None
            self.try_roll(dx, dz, validator)

    def _start_ice_slide(self, dx: int, dz: int, validator: MovementValidator | None) -> None:
        """Inicia o deslizamento plano de gelo: ICE_STEPS passos sem rotação."""
        self._slide_dx = dx
        self._slide_dz = dz
        self._slide_steps = Cube.ICE_STEPS
        self._slide_t = 0.0
        self._slide_from_x = float(self.grid_x)
        self._slide_from_z = float(self.grid_z)
        self._slide_validator = validator
        self.state = CubeState.SLIDING

    def _finish_slide_step(self) -> None:
        """Conclui um passo do deslize de gelo e decide se continua ou para."""
        dest_x = round(self._slide_from_x + self._slide_dx)
        dest_z = round(self._slide_from_z + self._slide_dz)

        validator = self._slide_validator

        # Snap para o destino do passo concluído
        self.grid_x = dest_x
        self.grid_z = dest_z
        self._sync_position_from_grid()
        self._slide_steps -= 1

        map_x = round(self.grid_x)
        map_z = round(self.grid_z)
        tile = validator.get_tile_type(map_x, map_z) if validator else "empty"

        if not self._is_walkable(tile):
            # Caiu do mapa durante o slide
            self._slide_steps = 0
            self._slide_validator = None
            self.state = CubeState.IDLE
            self._last_valid_grid_x = round(self._slide_from_x)
            self._last_valid_grid_z = round(self._slide_from_z)
            self._start_fall()
            return

        if tile == "end":
            self._last_valid_grid_x = map_x
            self._last_valid_grid_z = map_z
            self._reached_end = True
            self._slide_steps = 0
            self._slide_validator = None
            self.state = CubeState.IDLE
            return

        # Atualiza last_valid apenas se o tile não for frágil ou blink (evita respawn em tile perigoso)
        power = validator.get_power(map_x, map_z) if validator else None
        if power not in ("fragile", "blink"):
            self._last_valid_grid_x = map_x
            self._last_valid_grid_z = map_z

        # Ativar poderes nos tiles passados durante o slide
        if validator is not None:
            if power == "invert":
                if self._invert_timer > 0.0:
                    self._invert_timer = 0.0
                else:
                    self._invert_timer = Cube.INVERT_DURATION
                if hasattr(validator, "consume_power"):
                    validator.consume_power(map_x, map_z)  # type: ignore[union-attr]
            elif power == "fragile":
                if hasattr(validator, "schedule_fragile"):
                    validator.schedule_fragile(map_x, map_z)  # type: ignore[union-attr]
            elif power == "ice":
                # Chegou em outro bloco de gelo: reinicia o slide com steps cheios
                self._slide_steps = Cube.ICE_STEPS

        if self._slide_steps <= 0:
            # Slide concluído
            self._slide_validator = None
            self.state = CubeState.IDLE
            # Processa fila normal se houver
            if self._queued is not None:
                dx, dz, qv = self._queued
                self._queued = None
                self.try_roll(dx, dz, qv)
            return

        # Verifica se o próximo passo tem chão antes de continuar
        next_x = map_x + self._slide_dx
        next_z = map_z + self._slide_dz
        next_tile = validator.get_tile_type(next_x, next_z) if validator else "empty"
        if not self._is_walkable(next_tile):
            # Para no tile atual — não cai, só encosta na borda
            self._slide_steps = 0
            self._slide_validator = None
            self.state = CubeState.IDLE
            if self._queued is not None:
                dx, dz, qv = self._queued
                self._queued = None
                self.try_roll(dx, dz, qv)
            return

        # Inicia próximo passo
        self._slide_from_x = float(self.grid_x)
        self._slide_from_z = float(self.grid_z)
        self._slide_t = 0.0

    def _apply_slide_transform(self) -> None:
        """Interpolação linear plana durante o slide de gelo (sem rotação)."""
        t = self._slide_t
        x = (self._slide_from_x + self._slide_dx * t) * Cube.TILE_SIZE
        z = (self._slide_from_z + self._slide_dz * t) * Cube.TILE_SIZE
        y = 0.5 * self.size.sy
        glTranslatef(x, y, z)
        self._apply_accumulated_rotation()
        self._apply_size()

    def check_ground(self, validator: "MovementValidator") -> None:
        """Se estiver IDLE sobre tile inativo/void, inicia queda."""
        if self.state != CubeState.IDLE:
            return
        tile = validator.get_tile_type(round(self.grid_x), round(self.grid_z))
        if not self._is_walkable(tile):
            self._start_fall()

    def _start_fall(self) -> None:
        self.lives = max(0, self.lives - 1)
        self.state = CubeState.FALLING
        self._fall_t = 0.0
        self._fall_offset_y = 0.0
        self._queued = None
        self._ice_slide_dx = 0
        self._ice_slide_dz = 0

    def _sync_position_from_grid(self) -> None:
        self.position.x = float(self.grid_x) * Cube.TILE_SIZE
        self.position.y = 0.5 * self.size.sy
        self.position.z = float(self.grid_z) * Cube.TILE_SIZE

    def _apply_roll_transform(self) -> None:
        cx = float(self.grid_x) * Cube.TILE_SIZE
        cy = 0.5 * self.size.sy
        cz = float(self.grid_z) * Cube.TILE_SIZE

        if self._pending_dz != 0:
            pivot_x = 0.0
            pivot_z = 0.5 * Cube.TILE_SIZE * self.step_size * self._pending_dz
            angle   = 90.0 * self._roll_t * self._pending_dz
            axis    = (1.0, 0.0, 0.0)
        else:
            pivot_x = 0.5 * Cube.TILE_SIZE * self.step_size * self._pending_dx
            pivot_z = 0.0
            angle   = -90.0 * self._roll_t * self._pending_dx
            axis    = (0.0, 0.0, 1.0)

        glTranslatef(cx, cy, cz)
        glTranslatef(pivot_x, -0.5 * self.size.sy, pivot_z)
        glRotatef(angle, *axis)
        glTranslatef(-pivot_x, 0.5 * self.size.sy, -pivot_z)
        self._apply_accumulated_rotation()
        self._apply_size()

    def _apply_accumulated_rotation(self) -> None:
        glRotatef(self._total_angle_z, 1.0, 0.0, 0.0)
        glRotatef(self._total_angle_x, 0.0, 0.0, 1.0)

    def _apply_size(self) -> None:
        glScalef(self.size.sx, self.size.sy, self.size.sz)
