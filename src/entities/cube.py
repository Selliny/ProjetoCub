"""Entidade jogável principal: cubo grid-based controlado por tombamento."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from OpenGL.GL import (
    GL_QUADS,
    glBegin,
    glColor3f,
    glEnd,
    glRotatef,
    glScalef,
    glTranslatef,
    glVertex3f,
)

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size


ROLL_DURATION: float = 0.25
BLOCKED_DURATION: float = 0.08
FALL_DURATION: float = 0.55
FALL_DISTANCE: float = 3.0
RESPAWN_DELAY: float = 10.0
TILE_SIZE: float = 1.0


class MovementValidator(Protocol):
    def can_move_to(self, grid_x: int, grid_z: int) -> bool:
        """Retorna True se o cubo pode se mover para a célula informada."""
        ...

    def get_tile_type(self, grid_x: int, grid_z: int) -> str:
        """Retorna o tipo da célula para reações futuras do cubo."""
        ...


class CubeState(Enum):
    """Estados de controle da máquina de movimento do cubo."""

    IDLE = "idle"
    ROLLING = "rolling"
    BLOCKED = "blocked"
    FALLING = "falling"


class Cube:
    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
    ) -> None:
        start = position if position is not None else Position(0.0, 0.5, 0.0)
        self.grid_x = round(start.x / TILE_SIZE)
        self.grid_z = round(start.z / TILE_SIZE)
        self._spawn_grid_x = self.grid_x
        self._spawn_grid_z = self.grid_z
        self._spawn_y = start.y
        self.position = Position(
            float(self.grid_x) * TILE_SIZE,
            start.y,
            float(self.grid_z) * TILE_SIZE,
        )
        self.color = color if color is not None else Color(1.0, 0.0, 0.0)
        self.size = size if size is not None else Size.uniform(1.0)

        self.state = CubeState.IDLE
        self._roll_t: float = 0.0
        self._blocked_t: float = 0.0
        self._fall_t: float = 0.0
        self._fall_start_y: float = self.position.y
        self._respawn_t: float = 0.0
        self._pending_dx: int = 0
        self._pending_dz: int = 0
        self._queued: tuple[int, int, MovementValidator | None] | None = None
        self._validator: MovementValidator | None = None

        # Rotação acumulada permanente depois de cada tombamento completo.
        self._total_angle_z: float = 0.0  # rolls no eixo Z giram em X
        self._total_angle_x: float = 0.0  # rolls no eixo X giram em Z

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
        """Mantém compatibilidade com a API antiga convertendo eixo em dx/dz."""
        if axis == "z":
            self.try_roll(0, direction)
        elif axis == "x":
            self.try_roll(direction, 0)

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """Avança roll, queda e respawn usando delta time do frame."""
        if self.state == CubeState.BLOCKED:
            self.update_respawn_timer(dt)
            return

        if self.state == CubeState.FALLING:
            self._fall_t = min(self._fall_t + dt / FALL_DURATION, 1.0)
            self.position.y = self._fall_start_y - FALL_DISTANCE * self._fall_t
            self.update_respawn_timer(dt)
            return

        if self.state != CubeState.ROLLING:
            return

        self._roll_t = min(self._roll_t + dt / ROLL_DURATION, 1.0)
        if self._roll_t >= 1.0:
            self._finish_roll()

    def is_moving(self) -> bool:
        """Retorna True somente enquanto a animação de tombamento está ativa."""
        return self.state == CubeState.ROLLING

    def is_rolling(self) -> bool:
        """Alias temporário para código antigo que ainda chama is_rolling()."""
        return self.is_moving()

    def get_grid_position(self) -> tuple[int, int]:
        """Retorna a posição lógica inteira do cubo no grid."""
        return self.grid_x, self.grid_z

    def get_next_position(self, dx: int, dz: int) -> tuple[int, int]:
        """Calcula a próxima célula sem alterar a posição atual."""
        dx, dz = self._normalize_direction(dx, dz)
        return self.grid_x + dx, self.grid_z + dz

    def on_tile_enter(self, tile_type: str) -> None:
        """Reage ao tile final do roll: buraco cai, não-floor bloqueia."""
        if tile_type == "hole":
            self._start_fall()
        elif tile_type != "floor":
            self._set_blocked()

    def update_respawn_timer(self, dt: float) -> None:
        """Conta o tempo em BLOCKED/FALLING e respawna ao completar 10s."""
        self._respawn_t += dt
        if self._respawn_t >= RESPAWN_DELAY:
            self.respawn()

    def get_respawn_remaining(self) -> float:
        """Informa quantos segundos faltam para o respawn automático."""
        if self.state not in (CubeState.BLOCKED, CubeState.FALLING):
            return 0.0
        return max(0.0, RESPAWN_DELAY - self._respawn_t)

    def respawn(self) -> None:
        """Restaura posição inicial, estado e acumuladores para continuar testando."""
        self.grid_x = self._spawn_grid_x
        self.grid_z = self._spawn_grid_z
        self.position.x = float(self.grid_x) * TILE_SIZE
        self.position.y = self._spawn_y
        self.position.z = float(self.grid_z) * TILE_SIZE
        self.state = CubeState.IDLE
        self._roll_t = 0.0
        self._blocked_t = 0.0
        self._fall_t = 0.0
        self._respawn_t = 0.0
        self._pending_dx = 0
        self._pending_dz = 0
        self._queued = None
        self._validator = None
        self._total_angle_z = 0.0
        self._total_angle_x = 0.0

    def apply_transform(self) -> None:
        """Aplica a matriz OpenGL correta para roll, queda ou posição parada."""
        if self.state == CubeState.ROLLING:
            self._apply_roll_transform()
            return

        if self.state == CubeState.FALLING:
            glTranslatef(self.position.x, self.position.y, self.position.z)
            self._apply_accumulated_rotation()
            self._apply_size()
            return

        self._sync_position_from_grid()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        self._apply_accumulated_rotation()
        self._apply_size()

    def draw(self) -> None:
        """Desenha o cubo unitário centrado na origem com 6 faces coloridas."""
        glBegin(GL_QUADS)

        # Frente (+Z) — vermelho
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Tras (-Z) — verde
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)

        # Cima (+Y) — azul
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Baixo (-Y) — amarelo
        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)

        # Direita (+X) — laranja
        glColor3f(1.0, 0.5, 0.0)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)

        # Esquerda (-X) — roxo
        glColor3f(0.5, 0.0, 1.0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5, -0.5)

        glEnd()

    # ------------------------------------------------------------------
    # Compatibilidade e utilidades
    # ------------------------------------------------------------------

    def move(self, dx: float, dy: float, dz: float) -> None:
        """Move diretamente e recalcula o grid; mantido para compatibilidade."""
        self.position.translate(dx, dy, dz)
        self.grid_x = round(self.position.x / TILE_SIZE)
        self.grid_z = round(self.position.z / TILE_SIZE)

    def scale(self, factor: float) -> None:
        """Escala o cubo uniformemente; mantido para testes futuros."""
        self.size.sx *= factor
        self.size.sy *= factor
        self.size.sz *= factor

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _normalize_direction(self, dx: int, dz: int) -> tuple[int, int]:
        """Converte qualquer entrada em um passo cardinal válido do grid."""
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
        """Guarda apenas 1 próximo movimento enquanto o roll atual termina."""
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
        """Configura direção, validador e estado inicial de uma animação de roll."""
        self._pending_dx = dx
        self._pending_dz = dz
        self._roll_t = 0.0
        self._validator = validator
        self.state = CubeState.ROLLING
        self._sync_position_from_grid()

    def _finish_roll(self) -> None:
        """Finaliza o roll com snap no grid e aplica reação do tile final."""
        self.grid_x += self._pending_dx
        self.grid_z += self._pending_dz

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
            tile = self._validator.get_tile_type(self.grid_x, self.grid_z)
            self.on_tile_enter(tile)

        self._validator = None
        if self.state != CubeState.IDLE:
            self._queued = None
            return

        if self._queued is not None:
            dx, dz, validator = self._queued
            self._queued = None
            self.try_roll(dx, dz, validator)

    def _set_blocked(self) -> None:
        """Coloca o cubo em BLOCKED no tile inválido até o respawn automático."""
        self.state = CubeState.BLOCKED
        self._blocked_t = BLOCKED_DURATION

    def _start_fall(self) -> None:
        """Inicia a queda vertical ao entrar em um tile do tipo hole."""
        self.state = CubeState.FALLING
        self._fall_t = 0.0
        self._fall_start_y = self.position.y
        self._queued = None

    def _sync_position_from_grid(self) -> None:
        """Atualiza Position a partir de grid_x/grid_z para evitar drift de float."""
        self.position.x = float(self.grid_x) * TILE_SIZE
        self.position.y = 0.5 * self.size.sy
        self.position.z = float(self.grid_z) * TILE_SIZE

    def _apply_roll_transform(self) -> None:
        """Desenha o roll interpolado girando em torno da aresta inferior."""
        cx = float(self.grid_x) * TILE_SIZE
        cy = 0.5 * self.size.sy
        cz = float(self.grid_z) * TILE_SIZE

        if self._pending_dz != 0:
            pivot_x = 0.0
            pivot_z = 0.5 * TILE_SIZE * self._pending_dz
            angle = 90.0 * self._roll_t * self._pending_dz
            axis = (1.0, 0.0, 0.0)
        else:
            pivot_x = 0.5 * TILE_SIZE * self._pending_dx
            pivot_z = 0.0
            angle = -90.0 * self._roll_t * self._pending_dx
            axis = (0.0, 0.0, 1.0)

        glTranslatef(cx, cy, cz)
        glTranslatef(pivot_x, -0.5 * self.size.sy, pivot_z)
        glRotatef(angle, *axis)
        glTranslatef(-pivot_x, 0.5 * self.size.sy, -pivot_z)
        self._apply_accumulated_rotation()
        self._apply_size()

    def _apply_accumulated_rotation(self) -> None:
        """Reaplica rotações completas de rolls anteriores."""
        glRotatef(self._total_angle_z, 1.0, 0.0, 0.0)
        glRotatef(self._total_angle_x, 0.0, 0.0, 1.0)

    def _apply_size(self) -> None:
        """Aplica a escala atual do cubo na matriz OpenGL."""
        glScalef(self.size.sx, self.size.sy, self.size.sz)


def _run_logic_smoke_tests() -> None:
    """Smoke tests rápidos para a lógica do cubo, sem abrir janela OpenGL."""

    class Bounds:
        def can_move_to(self, grid_x: int, grid_z: int) -> bool:
            return -1 <= grid_x <= 2 and -1 <= grid_z <= 1

        def get_tile_type(self, grid_x: int, grid_z: int) -> str:
            if (grid_x, grid_z) == (2, 1):
                return "hole"
            return "floor" if self.can_move_to(grid_x, grid_z) else "empty"

    cube = Cube()
    bounds = Bounds()

    assert cube.get_grid_position() == (0, 0)
    assert cube.try_roll(1, 0, validator=bounds)
    assert cube.try_roll(0, 1, validator=bounds)
    assert not cube.try_roll(-1, 0, validator=bounds)

    cube.update(ROLL_DURATION)
    assert cube.get_grid_position() == (1, 0)
    assert cube.state == CubeState.ROLLING

    cube.update(ROLL_DURATION)
    assert cube.get_grid_position() == (1, 1)
    assert cube.state == CubeState.IDLE

    assert cube.try_roll(0, 1, validator=bounds)
    cube.update(ROLL_DURATION)
    assert cube.get_grid_position() == (1, 2)
    assert cube.state == CubeState.BLOCKED
    cube.update(BLOCKED_DURATION)
    assert cube.state == CubeState.BLOCKED
    assert not cube.try_roll(0, -1, validator=bounds)
    cube.update(RESPAWN_DELAY)
    assert cube.state == CubeState.IDLE
    assert cube.get_grid_position() == (0, 0)

    falling_cube = Cube()
    assert falling_cube.try_roll(1, 0, validator=bounds)
    falling_cube.update(ROLL_DURATION)
    assert falling_cube.try_roll(0, 1, validator=bounds)
    falling_cube.update(ROLL_DURATION)
    assert falling_cube.try_roll(1, 0, validator=bounds)
    falling_cube.update(ROLL_DURATION)
    assert falling_cube.get_grid_position() == (2, 1)
    assert falling_cube.state == CubeState.FALLING
    falling_cube.update(RESPAWN_DELAY)
    assert falling_cube.state == CubeState.IDLE
    assert falling_cube.get_grid_position() == (0, 0)

    print("cube logic smoke tests ok")


if __name__ == "__main__":
    _run_logic_smoke_tests()
