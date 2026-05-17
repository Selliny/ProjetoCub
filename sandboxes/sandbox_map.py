"""Sandbox interativo para desenvolver e testar o Map.

Demonstra controle total sobre a composição do mapa em tempo real:
adicionar/remover blocos, trocar tipo (Block / PoweredBlock), mudar cor,
alterar tamanho (Size) e ativar/desativar células individualmente.
O cursor de seleção navega pelo grid e as edições afetam o bloco na célula
selecionada — sem reiniciar o programa.

Controles — câmera:
  ↑ / ↓           → aproxima / afasta a câmera
  ← / →           → orbita a câmera ao redor do centro do mapa
  Q / E           → sobe / desce a câmera
  Mouse btn esq   → arrastar orbita e ajusta altura

Controles — cursor de seleção no grid:
  W / A / S / D   → move cursor (cima / esquerda / baixo / direita)

Controles — edição do bloco na célula selecionada:
  ENTER           → toggle: insere bloco padrão se vazio, remove se ocupado
  P               → alterna tipo: Block comum ↔ PoweredBlock
  1               → cor cinza  (bloco de caminho padrão)
  2               → cor verde  (início)
  3               → cor vermelho (fim)
  4               → cor amarelo ouro (PoweredBlock visual)
  + / =           → aumenta escala XZ do bloco (+0.05)
  - / _           → diminui escala XZ do bloco (−0.05, mín 0.1)
  ESPAÇO          → toggle block.active (bloco some / aparece)
  G               → gera novo mapa procedural 32×32 aleatório

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_map
"""

import pygame
from OpenGL.GL import (
    GL_LINES,
    GL_QUADS,
    glBegin,
    glColor3f,
    glColor4f,
    glEnd,
    glLineWidth,
    glVertex3f,
)
from OpenGL.GLU import gluLookAt

from sandboxes._harness import run
from src.entities.block import Block, PoweredBlock
from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size
from src.world.map import Map

_BLOCK_XZ: float = 1.0
_BLOCK_HEIGHT: float = 0.1

_CORES: dict[int, tuple[Color, str]] = {
    pygame.K_1: (Color(0.78, 0.59, 0.39), "caminho"),
    pygame.K_2: (Color(0.20, 0.78, 0.20), "início"),
    pygame.K_3: (Color(0.78, 0.20, 0.20), "fim"),
    pygame.K_4: (Color(1.00, 0.75, 0.00), "powered"),
}

CAMERA_MIN_HEIGHT = 4.0
CAMERA_MAX_HEIGHT = 50.0
CAMERA_MIN_DISTANCE = 8.0
CAMERA_MAX_DISTANCE = 60.0
CAMERA_ORBIT_STEP = 2.5
CAMERA_DISTANCE_STEP = 0.5
CAMERA_HEIGHT_STEP = 0.3
CAMERA_MOUSE_SENSITIVITY = 0.25
CAMERA_FOLLOW_SMOOTHING = 8.0


def _build_default_map() -> Map:
    return Map.generate()


def _new_block(col: int, row: int) -> Block:
    return Block(
        position=Position(float(col), 0.0, float(row)),
        color=Color(0.78, 0.59, 0.39),
        size=Size(_BLOCK_XZ, _BLOCK_HEIGHT, _BLOCK_XZ),
    )


def _draw_floor(cols: int, rows: int) -> None:
    glBegin(GL_QUADS)
    glColor3f(0.12, 0.12, 0.12)
    glVertex3f(-1.0,       -0.01, -1.0)
    glVertex3f(cols + 1.0, -0.01, -1.0)
    glVertex3f(cols + 1.0, -0.01, rows + 1.0)
    glVertex3f(-1.0,       -0.01, rows + 1.0)
    glEnd()


def _draw_grid_lines(cols: int, rows: int) -> None:
    glLineWidth(1.0)
    glBegin(GL_LINES)
    glColor3f(0.25, 0.25, 0.25)
    for i in range(cols + 1):
        glVertex3f(float(i) - 0.5, 0.0,  -0.5)
        glVertex3f(float(i) - 0.5, 0.0, float(rows) - 0.5)
    for j in range(rows + 1):
        glVertex3f(-0.5,           0.0, float(j) - 0.5)
        glVertex3f(float(cols) - 0.5, 0.0, float(j) - 0.5)
    glEnd()


def _draw_cursor(col: int, row: int) -> None:
    x, z = float(col), float(row)
    glLineWidth(2.5)
    glBegin(GL_LINES)
    glColor4f(1.0, 1.0, 0.0, 1.0)
    corners = [
        (x - 0.5, z - 0.5), (x + 0.5, z - 0.5),
        (x + 0.5, z - 0.5), (x + 0.5, z + 0.5),
        (x + 0.5, z + 0.5), (x - 0.5, z + 0.5),
        (x - 0.5, z + 0.5), (x - 0.5, z - 0.5),
    ]
    for ax, az in corners:
        glVertex3f(ax, 0.01, az)
    glEnd()
    glLineWidth(1.0)


def _print_state(col: int, row: int, block: Block | None) -> None:
    if block is None:
        print(f"[{col:02d},{row:02d}] vazio")
        return
    kind = type(block).__name__
    power = getattr(block, "power", "—")
    c = block.color
    s = block.size
    print(
        f"[{col:02d},{row:02d}] {kind} | active={block.active}"
        f" | is_powered={block.is_powered} | power={power}"
        f" | cor=({c.r:.2f},{c.g:.2f},{c.b:.2f})"
        f" | size=({s.sx:.2f},{s.sy:.2f},{s.sz:.2f})"
    )


def main() -> None:
    map_: Map = _build_default_map()

    cursor: list[int] = [0, 0]

    def _col() -> int: return cursor[0]
    def _row() -> int: return cursor[1]

    def _grid_dims() -> tuple[int, int]:
        if not map_._grid:
            return (Map.DEFAULT_COLS, Map.DEFAULT_ROWS)
        max_col = max(c for c, _ in map_._grid) + 1
        max_row = max(r for _, r in map_._grid) + 1
        return (max_col, max_row)

    last_frame_ms: list[int | None] = [None]
    camera_yaw: list[float] = [180.0]
    camera_height: list[float] = [20.0]
    camera_distance: list[float] = [28.0]

    cols0, rows0 = _grid_dims()
    cx0, cz0 = cols0 / 2.0, rows0 / 2.0
    camera_eye = pygame.math.Vector3(cx0, 20.0, cz0 + 28.0)
    camera_target = pygame.math.Vector3(cx0, 0.0, cz0)

    def _clamp_camera() -> None:
        camera_height[0] = max(CAMERA_MIN_HEIGHT, min(CAMERA_MAX_HEIGHT, camera_height[0]))
        camera_distance[0] = max(CAMERA_MIN_DISTANCE, min(CAMERA_MAX_DISTANCE, camera_distance[0]))

    def setup_camera() -> None:
        gluLookAt(
            camera_eye.x, camera_eye.y, camera_eye.z,
            camera_target.x, camera_target.y, camera_target.z,
            0.0, 1.0, 0.0,
        )

    def draw() -> None:
        cols, rows = _grid_dims()
        _draw_floor(cols, rows)
        _draw_grid_lines(cols, rows)
        _draw_cursor(_col(), _row())
        map_.draw()

    def on_frame() -> None:
        now_ms = pygame.time.get_ticks()
        if last_frame_ms[0] is None:
            dt = 1.0 / 60.0
        else:
            dt = (now_ms - last_frame_ms[0]) / 1000.0
        last_frame_ms[0] = now_ms

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            camera_yaw[0] += CAMERA_ORBIT_STEP
        if keys[pygame.K_RIGHT]:
            camera_yaw[0] -= CAMERA_ORBIT_STEP
        if keys[pygame.K_UP]:
            camera_distance[0] -= CAMERA_DISTANCE_STEP
        if keys[pygame.K_DOWN]:
            camera_distance[0] += CAMERA_DISTANCE_STEP
        if keys[pygame.K_q]:
            camera_height[0] += CAMERA_HEIGHT_STEP
        if keys[pygame.K_e]:
            camera_height[0] -= CAMERA_HEIGHT_STEP
        _clamp_camera()

        cols, rows = _grid_dims()
        yaw = pygame.math.Vector2(0.0, 1.0).rotate(camera_yaw[0])
        desired_target = pygame.math.Vector3(cols / 2.0, 0.0, rows / 2.0)
        desired_eye = pygame.math.Vector3(
            desired_target.x + yaw.x * camera_distance[0],
            camera_height[0],
            desired_target.z + yaw.y * camera_distance[0],
        )
        blend = min(1.0, CAMERA_FOLLOW_SMOOTHING * dt)
        camera_target.update(camera_target.lerp(desired_target, blend))
        camera_eye.update(camera_eye.lerp(desired_eye, blend))

    def on_mouse_motion(event: pygame.event.Event) -> None:
        if not pygame.mouse.get_pressed()[0]:
            return
        dx, dy = event.rel
        camera_yaw[0] -= dx * CAMERA_MOUSE_SENSITIVITY
        camera_height[0] -= dy * CAMERA_HEIGHT_STEP
        _clamp_camera()

    def on_key(event: pygame.event.Event) -> None:  # noqa: C901
        col, row = _col(), _row()
        block = map_.get_block(col, row)

        if event.key == pygame.K_w:
            cursor[1] = max(0, row - 1)
            _print_state(cursor[0], cursor[1], map_.get_block(cursor[0], cursor[1]))
            return
        if event.key == pygame.K_s:
            cols, rows = _grid_dims()
            cursor[1] = min(rows - 1, row + 1)
            _print_state(cursor[0], cursor[1], map_.get_block(cursor[0], cursor[1]))
            return
        if event.key == pygame.K_a:
            cursor[0] = max(0, col - 1)
            _print_state(cursor[0], cursor[1], map_.get_block(cursor[0], cursor[1]))
            return
        if event.key == pygame.K_d:
            cols, rows = _grid_dims()
            cursor[0] = min(cols - 1, col + 1)
            _print_state(cursor[0], cursor[1], map_.get_block(cursor[0], cursor[1]))
            return

        if event.key == pygame.K_RETURN:
            if block is None:
                map_.add_block(_new_block(col, row), col, row)
                print(f"[{col:02d},{row:02d}] bloco inserido")
            else:
                map_.remove_block(col, row)
                print(f"[{col:02d},{row:02d}] bloco removido")
            return

        if block is None:
            return

        if event.key == pygame.K_p:
            if isinstance(block, PoweredBlock):
                replacement: Block = Block(
                    position=block.position,
                    color=block.color,
                    size=block.size,
                    active=block.active,
                )
            else:
                replacement = PoweredBlock(
                    power="scale",
                    position=block.position,
                    color=block.color,
                    size=block.size,
                    active=block.active,
                )
            map_.add_block(replacement, col, row)
            _print_state(col, row, replacement)
            return

        if event.key in _CORES:
            template, nome = _CORES[event.key]
            block.color = Color(template.r, template.g, template.b)
            print(f"[{col:02d},{row:02d}] cor → {nome}")
            return

        if event.key in (pygame.K_PLUS, pygame.K_EQUALS):
            block.size = Size(
                round(block.size.sx + 0.05, 3),
                block.size.sy,
                round(block.size.sz + 0.05, 3),
            )
            _print_state(col, row, block)
            return

        if event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
            new_xz = max(0.1, round(block.size.sx - 0.05, 3))
            block.size = Size(new_xz, block.size.sy, new_xz)
            _print_state(col, row, block)
            return

        if event.key == pygame.K_SPACE:
            block.active = not block.active
            _print_state(col, row, block)
            return

        if event.key == pygame.K_g:
            map_._grid = Map.generate()._grid
            cursor[0], cursor[1] = 0, 0
            print("Novo mapa procedural gerado (32×32).")
            return

    print("=== Sandbox Map ===")
    print("WASD=cursor | ENTER=inserir/remover | P=tipo | 1-4=cor | +/-=escala")
    print("ESPAÇO=active | G=gerar novo mapa(32×32) | setas+mouse=câmera orbital | Q/E=altura")
    _print_state(_col(), _row(), map_.get_block(_col(), _row()))

    run(
        draw,
        on_key=on_key,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title="Sandbox: Map | WASD=cursor | ENTER=±bloco | G=novo mapa | setas+mouse=câmera orbital",
    )


if __name__ == "__main__":
    main()
