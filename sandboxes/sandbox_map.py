"""Sandbox interativo para desenvolver e testar o Map.

Demonstra controle total sobre a composição do mapa em tempo real:
adicionar/remover blocos, trocar tipo (Block / PoweredBlock), mudar cor,
alterar tamanho (Size) e ativar/desativar células individualmente.
O cursor de seleção navega pelo grid e as edições afetam o bloco na célula
selecionada — sem reiniciar o programa.

Controles — câmera:
  ↑ / ↓           → dolly (avança / recua)
  ← / →           → strafe (desloca lateralmente)
  Mouse btn esq   → arrastar rotaciona câmera (yaw + pitch)
  Scroll          → zoom (glScalef aplicado na cena)
  Q / E           → rotação yaw esquerda / direita
  R / F           → tilt (achatamento vertical)

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
    glScalef,
    glVertex3f,
)

from sandboxes._harness import run
from src.entities.block import Block, PoweredBlock
from src.graphics.camera import Camera
from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size
from src.world.map import Map

# Tamanho padrão de um bloco no grid (XZ=1.0, Y=altura do Block)
_BLOCK_XZ: float = 1.0
_BLOCK_HEIGHT: float = 0.1

# Cores nomeadas para os atalhos de teclado
_CORES: dict[int, tuple[Color, str]] = {
    pygame.K_1: (Color(0.78, 0.59, 0.39), "caminho"),
    pygame.K_2: (Color(0.20, 0.78, 0.20), "início"),
    pygame.K_3: (Color(0.78, 0.20, 0.20), "fim"),
    pygame.K_4: (Color(1.00, 0.75, 0.00), "powered"),
}


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
    """Desenha linhas de grade sobre o chão para referência visual do grid."""
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
    """Destaca a célula selecionada com uma borda amarela no chão."""
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
    camera = Camera(eye_x=15.0, eye_y=28.0, eye_z=40.0, yaw=180.0, pitch=-35.0)

    # Cursor — célula atualmente selecionada no grid
    cursor: list[int] = [0, 0]   # [col, row]

    def _col() -> int: return cursor[0]
    def _row() -> int: return cursor[1]

    def setup_camera() -> None:
        # Zoom: escala uniforme ao redor da origem antes de posicionar a câmera.
        # Tilt: achatamento adicional no eixo Y (efeito perspectiva isométrica).
        glScalef(camera.zoom, camera.zoom * camera.tilt, camera.zoom)
        camera.apply()

    def _grid_dims() -> tuple[int, int]:
        """Retorna (cols, rows) do mapa atual derivado das chaves do _grid."""
        if not map_._grid:
            return (Map.DEFAULT_COLS, Map.DEFAULT_ROWS)
        max_col = max(c for c, _ in map_._grid) + 1
        max_row = max(r for _, r in map_._grid) + 1
        return (max_col, max_row)

    def draw() -> None:
        cols, rows = _grid_dims()
        _draw_floor(cols, rows)
        _draw_grid_lines(cols, rows)
        _draw_cursor(_col(), _row())
        map_.draw()

    def on_frame() -> None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            camera.move_forward(+Camera.MOVE_STEP)
        if keys[pygame.K_DOWN]:
            camera.move_forward(-Camera.MOVE_STEP)
        if keys[pygame.K_LEFT]:
            camera.strafe(+Camera.MOVE_STEP)
        if keys[pygame.K_RIGHT]:
            camera.strafe(-Camera.MOVE_STEP)
        if keys[pygame.K_q]:
            camera.rotate(3.0, 0.0)
        if keys[pygame.K_e]:
            camera.rotate(-3.0, 0.0)
        if keys[pygame.K_r]:
            camera.tilt = min(1.0, camera.tilt + 0.02)
        if keys[pygame.K_f]:
            camera.tilt = max(0.2, camera.tilt - 0.02)

    def on_scroll(event: pygame.event.Event) -> None:
        camera.handle_scroll(event)

    def on_mouse_motion(event: pygame.event.Event) -> None:
        if pygame.mouse.get_pressed()[0]:
            dx, dy = event.rel
            camera.rotate(
                dyaw=dx * Camera.MOUSE_SENSITIVITY,
                dpitch=-dy * Camera.MOUSE_SENSITIVITY,
            )

    def on_key(event: pygame.event.Event) -> None:  # noqa: C901
        col, row = _col(), _row()
        block = map_.get_block(col, row)

        # --- Navegação do cursor (WASD) ---
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

        # --- Edição da célula selecionada ---

        if event.key == pygame.K_RETURN:
            if block is None:
                map_.add_block(_new_block(col, row), col, row)
                print(f"[{col:02d},{row:02d}] bloco inserido")
            else:
                map_.remove_block(col, row)
                print(f"[{col:02d},{row:02d}] bloco removido")
            return

        if block is None:
            return  # restante das ações requer bloco existente

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
    print("ESPAÇO=active | G=gerar novo mapa(32×32) | setas+mouse=câmera | scroll=zoom | R/F=tilt | Q/E=rotação")
    _print_state(_col(), _row(), map_.get_block(_col(), _row()))

    run(
        draw,
        on_key=on_key,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        on_scroll=on_scroll,
        setup_camera=setup_camera,
        title="Sandbox: Map | WASD=cursor | ENTER=±bloco | G=novo mapa | setas+mouse=câmera",
    )


if __name__ == "__main__":
    main()
