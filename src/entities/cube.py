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
    IDLE        = "idle"
    ROLLING     = "rolling"
    FALLING     = "falling"
    FADING_OUT  = "fading_out"
    FADING_IN   = "fading_in"


class Cube:
    # Durações e distâncias das animações (em segundos / unidades).
    ROLL_DURATION: float = 0.25
    FALL_DURATION: float = 0.5
    FALL_DISTANCE: float = 3.0
    FADE_DURATION: float = 0.4
    TILE_SIZE:     float = 1.0

    # Número padrão de vidas com que o cubo começa.
    MAX_LIVES: int = 3

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

        # Portal: destino do teleporte (definido ao iniciar o fade-out)
        self._portal_target_x: int = 0
        self._portal_target_z: int = 0

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

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

        if self.state != CubeState.IDLE:
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
        """Avança animações usando delta time do frame."""
        if self.state == CubeState.ROLLING:
            self._roll_t = min(self._roll_t + dt / Cube.ROLL_DURATION, 1.0)
            if self._roll_t >= 1.0:
                self._finish_roll()
            return

        if self.state == CubeState.FALLING:
            self._fall_t = min(self._fall_t + dt / Cube.FALL_DURATION, 1.0)
            self._fall_offset_y = -Cube.FALL_DISTANCE * self._fall_t
            if self._fall_t >= 1.0:
                self.grid_x = self._last_valid_grid_x
                self.grid_z = self._last_valid_grid_z
                self._sync_position_from_grid()
                self._total_angle_z = 0.0
                self._total_angle_x = 0.0
                self._fall_offset_y = 0.0
                self._fade_t = 0.0
                self._alpha = 0.0
                self.state = CubeState.FADING_IN
            return

        if self.state == CubeState.FADING_OUT:
            self._fade_t += dt / Cube.FADE_DURATION
            self._alpha = max(0.0, 1.0 - self._fade_t)
            if self._fade_t >= 1.0:
                # Teleporta para o destino do portal, respeitando o offset de canto do cubo pequeno
                self.grid_x = self._portal_target_x - (0.25 if self.step_size == 0.5 else 0)
                self.grid_z = self._portal_target_z + (0.25 if self.step_size == 0.5 else 0)
                self._sync_position_from_grid()
                self._total_angle_z = 0.0
                self._total_angle_x = 0.0
                self._alpha = 0.0
                self._fade_t = 0.0
                # Verifica se o destino é vazio → queda imediata após fade-in
                self._portal_landing_is_void = True
                if self._validator is not None:
                    tile = self._validator.get_tile_type(
                        round(self.grid_x), round(self.grid_z)
                    )
                    self._portal_landing_is_void = (tile != "floor")
                self.state = CubeState.FADING_IN
            return

        if self.state == CubeState.FADING_IN:
            self._fade_t += dt / Cube.FADE_DURATION
            self._alpha = min(1.0, self._fade_t)
            if self._fade_t >= 1.0:
                self._alpha = 1.0
                if getattr(self, "_portal_landing_is_void", False):
                    self._portal_landing_is_void = False
                    self._start_fall()
                else:
                    self._last_valid_grid_x = round(self.grid_x)
                    self._last_valid_grid_z = round(self.grid_z)
                    self.state = CubeState.IDLE
            return

    @property
    def is_dead(self) -> bool:
        """True quando o cubo ficou sem vidas."""
        return self.lives <= 0

    def is_moving(self) -> bool:
        return self.state == CubeState.ROLLING

    def is_rolling(self) -> bool:
        """Alias para compatibilidade com código antigo."""
        return self.is_moving()

    def get_grid_position(self) -> tuple[int, int]:
        return self.grid_x, self.grid_z

    def get_next_position(self, dx: int, dz: int) -> tuple[int, int]:
        dx, dz = self._normalize_direction(dx, dz)
        return self.grid_x + dx, self.grid_z + dz

    def on_tile_enter(self, tile_type: str) -> None:
        """Reage ao tile final do roll: qualquer coisa fora de 'floor' inicia queda."""
        if tile_type != "floor":
            self._start_fall()

    def respawn(self) -> None:
        """Força retorno imediato ao spawn inicial (debug/reset manual)."""
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

    def apply_transform(self) -> None:
        """Aplica a matriz OpenGL correta para roll, queda, fade ou posição parada."""
        if self.state == CubeState.ROLLING:
            self._apply_roll_transform()
            return

        self._sync_position_from_grid()
        y_offset = self._fall_offset_y if self.state == CubeState.FALLING else 0.0
        glTranslatef(self.position.x, self.position.y + y_offset, self.position.z)
        self._apply_accumulated_rotation()
        self._apply_size()

    def draw(self) -> None:
        """Desenha o cubo roxo com bordas pretas. Respeita _alpha para fade."""
        a = self._alpha
        if a < 1.0:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glBegin(GL_QUADS)
        glColor4f(0.5, 0.0, 0.8, a)

        # Frente (+Z)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Trás (−Z)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)

        # Cima (+Y)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Baixo (−Y)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)

        # Direita (+X)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)

        # Esquerda (−X)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5, -0.5)

        glEnd()

        glLineWidth(2.0)
        glBegin(GL_LINES)
        glColor4f(0.0, 0.0, 0.0, a)

        glVertex3f(-0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5, -0.5)

        glVertex3f(-0.5, -0.5, -0.5); glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5); glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f(-0.5, -0.5, -0.5)

        glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5, -0.5,  0.5); glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f(-0.5,  0.5,  0.5)

        glEnd()
        glLineWidth(1.0)

        if a < 1.0:
            glDisable(GL_BLEND)

    # ------------------------------------------------------------------
    # Compatibilidade e utilidades
    # ------------------------------------------------------------------

    def move(self, dx: float, dy: float, dz: float) -> None:
        """Move diretamente e recalcula o grid; mantido para compatibilidade."""
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

    def _enqueue_roll(
        self,
        dx: int,
        dz: int,
        validator: MovementValidator | None,
    ) -> bool:
        if self._queued is not None:
            return False
        self._queued = (dx, dz, validator)
        return True

    def _start_roll(
        self,
        dx: int,
        dz: int,
        validator: MovementValidator | None,
    ) -> None:
        self._pending_dx = dx
        self._pending_dz = dz
        self._roll_t = 0.0
        self._validator = validator
        self.state = CubeState.ROLLING
        self._sync_position_from_grid()

    def _finish_roll(self) -> None:
        """Finaliza o roll com snap no grid e reage ao tile destino."""
        self.grid_x += self._pending_dx * self.step_size
        self.grid_z += self._pending_dz * self.step_size

        if self._pending_dz != 0:
            self._total_angle_z += 90.0 * self._pending_dz
        elif self._pending_dx != 0:
            self._total_angle_x += -90.0 * self._pending_dx

        self._pending_dx = 0
        self._pending_dz = 0
        self._roll_t = 0.0
        self.state = CubeState.IDLE
        self._sync_position_from_grid()

        if self._validator is not None:
            map_x = round(self.grid_x)
            map_z = round(self.grid_z)
            tile  = self._validator.get_tile_type(map_x, map_z)
            power = self._validator.get_power(map_x, map_z)

            if power == "shrink" and self.step_size != 0.5:
                self.step_size = 0.5
                self.size.sx = 0.5
                self.size.sy = 0.5
                self.size.sz = 0.5
                self.grid_x -= 0.25
                self.grid_z += 0.25

            elif power == "grow" and self.step_size == 0.5:
                self.step_size = 1.0
                self.size.sx = 1.0
                self.size.sy = 1.0
                self.size.sz = 1.0
                self.grid_x = round(self.grid_x)
                self.grid_z = round(self.grid_z)
                if hasattr(self._validator, "consume_power"):
                    self._validator.consume_power(map_x, map_z)  # type: ignore[union-attr]

            elif power == "heal" and self.lives < self.max_lives:
                self.lives += 1
                if hasattr(self._validator, "consume_power"):
                    self._validator.consume_power(map_x, map_z)  # type: ignore[union-attr]

            elif power == "portal":
                if hasattr(self._validator, "get_random_position"):
                    tx, tz = self._validator.get_random_position()  # type: ignore[union-attr]
                else:
                    import random as _random
                    tx = round(self.grid_x) + _random.randint(-5, 5)
                    tz = round(self.grid_z) + _random.randint(-5, 5)
                if hasattr(self._validator, "consume_power"):
                    self._validator.consume_power(map_x, map_z)  # type: ignore[union-attr]
                self._start_portal(tx, tz)
                return

            if tile == "floor":
                self._last_valid_grid_x = self.grid_x
                self._last_valid_grid_z = self.grid_z
            self.on_tile_enter(tile)

        self._validator = None

        if self.state != CubeState.IDLE:
            self._queued = None
            return

        if self._queued is not None:
            dx, dz, validator = self._queued
            self._queued = None
            self.try_roll(dx, dz, validator)

    def _start_fall(self) -> None:
        """Inicia animação de queda → teleporte → fade in. Desconta uma vida."""
        self.lives = max(0, self.lives - 1)
        self.state = CubeState.FALLING
        self._fall_t = 0.0
        self._fall_offset_y = 0.0
        self._queued = None

    def _start_portal(self, target_x: int, target_z: int) -> None:
        """Inicia fade-out para teleporte via portal."""
        self._portal_target_x = target_x
        self._portal_target_z = target_z
        self._fade_t = 0.0
        self._alpha = 1.0
        self.state = CubeState.FADING_OUT
        self._queued = None

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

    # ------------------------------------------------------------------
    # Smoke tests (executados com: python -m src.entities.cube)
    # ------------------------------------------------------------------

    @staticmethod
    def _run_smoke_tests() -> None:
        class Bounds:
            def can_move_to(self, grid_x: int, grid_z: int) -> bool:
                return -1 <= grid_x <= 2 and -1 <= grid_z <= 1

            def get_tile_type(self, grid_x: int, grid_z: int) -> str:
                return "floor" if self.can_move_to(grid_x, grid_z) else "empty"

            def get_power(self, grid_x: int, grid_z: int) -> str | None:
                return None

        cube = Cube()
        bounds = Bounds()

        assert cube.get_grid_position() == (0, 0)
        assert cube.try_roll(1, 0, validator=bounds)
        cube.update(Cube.ROLL_DURATION)
        assert cube.get_grid_position() == (1, 0)
        assert cube.state == CubeState.IDLE
        assert cube._last_valid_grid_x == 1
        assert cube._last_valid_grid_z == 0

        assert cube.try_roll(0, 1, validator=bounds)
        assert cube.try_roll(-1, 0, validator=bounds)
        assert not cube.try_roll(-1, 0, validator=bounds)
        cube.update(Cube.ROLL_DURATION)
        assert cube.state == CubeState.ROLLING
        cube.update(Cube.ROLL_DURATION)
        assert cube.get_grid_position() == (0, 1)
        assert cube.state == CubeState.IDLE

        cube.grid_x, cube.grid_z = 1, 1
        cube._last_valid_grid_x, cube._last_valid_grid_z = 1, 1
        cube._sync_position_from_grid()

        assert cube.try_roll(0, 1, validator=bounds)
        cube.update(Cube.ROLL_DURATION)
        assert cube.get_grid_position() == (1, 2)
        assert cube.state == CubeState.FALLING

        assert not cube.try_roll(0, -1, validator=bounds)

        cube.update(Cube.FALL_DURATION)
        assert cube.state == CubeState.FADING_IN
        assert cube.get_grid_position() == (1, 1)
        assert cube._alpha == 0.0

        cube.update(Cube.FADE_DURATION + 0.01)
        assert cube.state == CubeState.IDLE
        assert cube._alpha == 1.0

        print("cube smoke tests ok")


if __name__ == "__main__":
    Cube._run_smoke_tests()
