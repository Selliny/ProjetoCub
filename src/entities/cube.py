"""Entidade jogável principal: cubo grid-based controlado por tombamento."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from OpenGL.GL import (
    GL_BLEND,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_SRC_ALPHA,
    glBegin,
    glBlendFunc,
    glColor4f,
    glDisable,
    glEnable,
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
FADE_DURATION: float = 0.4   # duração do fade out e do fade in
RESPAWN_DELAY: float = 2.0   # segundos parado antes do fade out → teleporte
TILE_SIZE: float = 1.0


class MovementValidator(Protocol):
    def can_move_to(self, grid_x: int, grid_z: int) -> bool:
        """Retorna True se o cubo pode se mover para a célula informada."""
        ...

    def get_tile_type(self, grid_x: int, grid_z: int) -> str:
        """Retorna o tipo da célula para reações do cubo."""
        ...


class CubeState(Enum):
    """Estados da máquina de movimento do cubo."""

    IDLE       = "idle"
    ROLLING    = "rolling"
    FADING_OUT = "fading_out"  # sumindo após sair do caminho
    FADING_IN  = "fading_in"   # reaparecendo no último bloco válido


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
        self._fade_t: float = 0.0
        self._respawn_t: float = 0.0
        self._alpha: float = 1.0         # 1.0 = opaco, 0.0 = invisível
        self._pending_dx: int = 0
        self._pending_dz: int = 0
        self._queued: tuple[int, int, MovementValidator | None] | None = None
        self._validator: MovementValidator | None = None

        # Último bloco válido pisado — destino do fade in após sair do caminho.
        self._last_valid_grid_x: int = self.grid_x
        self._last_valid_grid_z: int = self.grid_z

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
        """Compatibilidade com API antiga: converte eixo em dx/dz."""
        if axis == "z":
            self.try_roll(0, direction)
        elif axis == "x":
            self.try_roll(direction, 0)

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """Avança animações usando delta time do frame."""
        if self.state == CubeState.ROLLING:
            self._roll_t = min(self._roll_t + dt / ROLL_DURATION, 1.0)
            if self._roll_t >= 1.0:
                self._finish_roll()
            return

        if self.state == CubeState.FADING_OUT:
            self._respawn_t += dt
            # Fase 1: espera RESPAWN_DELAY antes de começar a sumir.
            if self._respawn_t < RESPAWN_DELAY:
                return
            # Fase 2: fade out.
            self._fade_t += dt / FADE_DURATION
            self._alpha = max(0.0, 1.0 - self._fade_t)
            if self._fade_t >= 1.0:
                # Teleporta para o último bloco válido e inicia fade in.
                self.grid_x = self._last_valid_grid_x
                self.grid_z = self._last_valid_grid_z
                self._sync_position_from_grid()
                self._total_angle_z = 0.0
                self._total_angle_x = 0.0
                self.state = CubeState.FADING_IN
                self._fade_t = 0.0
                self._alpha = 0.0
            return

        if self.state == CubeState.FADING_IN:
            self._fade_t += dt / FADE_DURATION
            self._alpha = min(1.0, self._fade_t)
            if self._fade_t >= 1.0:
                self._alpha = 1.0
                self.state = CubeState.IDLE
            return

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
        """Reage ao tile final do roll: qualquer coisa fora de 'floor' inicia fade."""
        if tile_type != "floor":
            self._start_fade_out()

    def get_respawn_remaining(self) -> float:
        """Segundos restantes para o fade out começar (apenas durante FADING_OUT)."""
        if self.state != CubeState.FADING_OUT:
            return 0.0
        return max(0.0, RESPAWN_DELAY - self._respawn_t)

    def respawn(self) -> None:
        """Força retorno imediato ao spawn inicial (debug/reset manual)."""
        self.grid_x = self._spawn_grid_x
        self.grid_z = self._spawn_grid_z
        self._last_valid_grid_x = self._spawn_grid_x
        self._last_valid_grid_z = self._spawn_grid_z
        self._sync_position_from_grid()
        self.state = CubeState.IDLE
        self._roll_t = 0.0
        self._fade_t = 0.0
        self._respawn_t = 0.0
        self._alpha = 1.0
        self._pending_dx = 0
        self._pending_dz = 0
        self._queued = None
        self._validator = None
        self._total_angle_z = 0.0
        self._total_angle_x = 0.0

    def apply_transform(self) -> None:
        """Aplica a matriz OpenGL correta para roll, fade ou posição parada."""
        if self.state == CubeState.ROLLING:
            self._apply_roll_transform()
            return

        self._sync_position_from_grid()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        self._apply_accumulated_rotation()
        self._apply_size()

    def draw(self) -> None:
        """Desenha o cubo com 6 faces coloridas. Respeita _alpha para fade."""
        a = self._alpha
        if a < 1.0:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glBegin(GL_QUADS)

        # Frente (+Z) — vermelho
        glColor4f(1.0, 0.0, 0.0, a)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Trás (−Z) — verde
        glColor4f(0.0, 1.0, 0.0, a)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)

        # Cima (+Y) — azul
        glColor4f(0.0, 0.0, 1.0, a)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Baixo (−Y) — amarelo
        glColor4f(1.0, 1.0, 0.0, a)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)

        # Direita (+X) — laranja
        glColor4f(1.0, 0.5, 0.0, a)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)

        # Esquerda (−X) — roxo
        glColor4f(0.5, 0.0, 1.0, a)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5, -0.5)

        glEnd()

        if a < 1.0:
            glDisable(GL_BLEND)

    # ------------------------------------------------------------------
    # Compatibilidade e utilidades
    # ------------------------------------------------------------------

    def move(self, dx: float, dy: float, dz: float) -> None:
        """Move diretamente e recalcula o grid; mantido para compatibilidade."""
        self.position.translate(dx, dy, dz)
        self.grid_x = round(self.position.x / TILE_SIZE)
        self.grid_z = round(self.position.z / TILE_SIZE)

    def scale(self, factor: float) -> None:
        """Escala uniformemente; mantido para testes futuros."""
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
            # Salva o último bloco válido antes de reagir ao tile.
            if tile == "floor":
                self._last_valid_grid_x = self.grid_x
                self._last_valid_grid_z = self.grid_z
            self.on_tile_enter(tile)

        self._validator = None

        # Processa fila apenas se ainda em IDLE (não iniciou fade).
        if self.state != CubeState.IDLE:
            self._queued = None
            return

        if self._queued is not None:
            dx, dz, validator = self._queued
            self._queued = None
            self.try_roll(dx, dz, validator)

    def _start_fade_out(self) -> None:
        """Inicia o ciclo fade out → teleporte → fade in."""
        self.state = CubeState.FADING_OUT
        self._fade_t = 0.0
        self._respawn_t = 0.0
        self._alpha = 1.0
        self._queued = None

    def _sync_position_from_grid(self) -> None:
        """Atualiza Position a partir de grid_x/grid_z para evitar drift de float."""
        self.position.x = float(self.grid_x) * TILE_SIZE
        self.position.y = 0.5 * self.size.sy
        self.position.z = float(self.grid_z) * TILE_SIZE

    def _apply_roll_transform(self) -> None:
        """Interpola o tombamento em torno da aresta inferior."""
        cx = float(self.grid_x) * TILE_SIZE
        cy = 0.5 * self.size.sy
        cz = float(self.grid_z) * TILE_SIZE

        if self._pending_dz != 0:
            pivot_x = 0.0
            pivot_z = 0.5 * TILE_SIZE * self._pending_dz
            angle   = 90.0 * self._roll_t * self._pending_dz
            axis    = (1.0, 0.0, 0.0)
        else:
            pivot_x = 0.5 * TILE_SIZE * self._pending_dx
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


def _run_logic_smoke_tests() -> None:
    """Smoke tests da lógica do cubo sem abrir janela OpenGL."""

    class Bounds:
        def can_move_to(self, grid_x: int, grid_z: int) -> bool:
            return -1 <= grid_x <= 2 and -1 <= grid_z <= 1

        def get_tile_type(self, grid_x: int, grid_z: int) -> str:
            if not self.can_move_to(grid_x, grid_z):
                return "empty"
            return "floor"

    cube = Cube()
    bounds = Bounds()

    # Roll simples
    assert cube.get_grid_position() == (0, 0)
    assert cube.try_roll(1, 0, validator=bounds)
    cube.update(ROLL_DURATION)
    assert cube.get_grid_position() == (1, 0)
    assert cube.state == CubeState.IDLE

    # Último bloco válido atualizado
    assert cube._last_valid_grid_x == 1
    assert cube._last_valid_grid_z == 0

    # Roll enfileirado durante animação
    assert cube.try_roll(0, 1, validator=bounds)
    assert cube.try_roll(-1, 0, validator=bounds)      # enfileira com sucesso
    assert not cube.try_roll(-1, 0, validator=bounds)  # fila cheia — rejeita
    cube.update(ROLL_DURATION)  # termina roll (1,0)→(1,1), inicia queued (-1,0)
    assert cube.state == CubeState.ROLLING
    cube.update(ROLL_DURATION)  # termina queued roll (1,1)→(0,1)
    assert cube.get_grid_position() == (0, 1)
    assert cube.state == CubeState.IDLE
    # Reposiciona para (1,1) para os próximos testes
    cube.grid_x, cube.grid_z = 1, 1
    cube._last_valid_grid_x, cube._last_valid_grid_z = 1, 1
    cube._sync_position_from_grid()

    # Sair do caminho → FADING_OUT após espera
    assert cube.try_roll(0, 1, validator=bounds)  # vai para (1,2) = empty
    cube.update(ROLL_DURATION)
    assert cube.get_grid_position() == (1, 2)
    assert cube.state == CubeState.FADING_OUT

    # Durante FADING_OUT não aceita novo roll
    assert not cube.try_roll(0, -1, validator=bounds)

    # Espera menos que RESPAWN_DELAY → ainda em FADING_OUT
    cube.update(RESPAWN_DELAY - 0.1)
    assert cube.state == CubeState.FADING_OUT

    # Passa do RESPAWN_DELAY em steps pequenos para não pular o fade
    cube.update(0.05)  # chega em RESPAWN_DELAY; _fade_t começa subir
    cube.update(0.05)
    assert cube.state == CubeState.FADING_OUT
    assert cube._alpha < 1.0  # fade visual em andamento

    # Completa fade out → teleporta → FADING_IN no último bloco válido
    cube.update(FADE_DURATION)
    assert cube.state == CubeState.FADING_IN
    assert cube.get_grid_position() == (1, 1)  # último bloco válido

    # Fade in completo → IDLE
    cube.update(FADE_DURATION + 0.01)
    assert cube.state == CubeState.IDLE
    assert cube._alpha == 1.0

    print("cube logic smoke tests ok")


if __name__ == "__main__":
    _run_logic_smoke_tests()
