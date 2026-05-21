"""Sandbox integrado: Cube caminhando sobre um Map real gerado proceduralmente.

Controles:
  W / S           → cubo tomba para trás / frente  (−Z / +Z)
  A / D           → cubo tomba para esquerda / direita  (−X / +X)
  G               → gera novo mapa procedural (cubo volta ao início)
  ↑ / ↓           → aproxima / afasta a câmera do cubo
  ← / →           → orbita a câmera ao redor do cubo
  Q / E           → sobe / desce a câmera
  Mouse btn esq   → arrastar orbita e ajusta altura

Vidas:
  O cubo começa com 3 vidas. Cada queda desconta 1.
  Blocos rosa (raros) recuperam 1 vida ao ser pisados e viram blocos comuns.
  Ao perder todas as vidas, o mapa é reiniciado automaticamente.

Como rodar (raiz do projeto, venv ativado):

    python -m sandboxes.sandbox_cube
"""

import math

import pygame
from OpenGL.GL import (
    GL_BLEND,
    GL_DEPTH_TEST,
    GL_LINE_LOOP,
    GL_MODELVIEW,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_PROJECTION,
    GL_QUADS,
    GL_RGBA,
    GL_SRC_ALPHA,
    GL_TRIANGLES,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBlendFunc,
    glColor4f,
    glDisable,
    glEnable,
    glEnd,
    glLineWidth,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glRasterPos2f,
    glDrawPixels,
    glVertex2f,
)
from OpenGL.GLU import gluLookAt

from sandboxes._harness import run
from sandboxes.menu import run_menu
from src.entities.cube import Cube, CubeState
from src.graphics.position import Position
from src.world.map import Map

_HUD_HEART_SIZE = 28       # pixels por coração
_HUD_MARGIN = 16           # margem da borda
_HUD_SPACING = 6           # espaço entre corações
_SCREEN_W = 1920
_SCREEN_H = 1080

# Legenda de blocos especiais: (cor RGBA, nome exibido)
_LEGEND_ITEMS: list[tuple[tuple[float, float, float, float], str]] = [
    ((1.0, 0.4, 0.7, 1.0), "Heal"),
    ((0.5, 0.0, 1.0, 1.0), "Shrink"),
    ((0.2, 1.0, 0.2, 1.0), "Grow"),
    ((0.0, 0.1, 0.4, 1.0), "Portal"),
    ((0.55, 0.88, 1.0, 1.0), "Ice"),
    ((0.85, 0.0, 0.55, 1.0), "Invert"),
    ((0.72, 0.72, 0.72, 1.0), "Fragile"),
    ((1.0, 0.45, 0.0, 1.0), "Bounce"),
    ((0.2, 0.45, 0.15, 1.0), "Slow"),
    ((0.85, 0.65, 0.05, 1.0), "Check"),
]

_HUD_LEGEND_BOX    = 20   # lado do quadrado colorido em pixels
_HUD_LEGEND_GAP    = 4    # espaço entre quadrado e texto abaixo
_HUD_LEGEND_STRIDE = 70   # distância horizontal entre itens

_font: pygame.font.Font | None = None  # inicializado uma vez na primeira chamada


def _get_font() -> pygame.font.Font:
    global _font
    if _font is None:
        pygame.font.init()
        _font = pygame.font.SysFont("consolas", 15, bold=False)
    return _font


def _draw_text_pixels(text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    """Renderiza `text` na posição (x, y) de tela usando glDrawPixels.

    A origem (x, y) é canto superior-esquerdo em coordenadas de tela
    (Y cresce para baixo). glDrawPixels usa origem inferior-esquerda em
    coordenadas de janela (Y cresce para cima), então invertemos a surface
    e convertemos Y antes de posicionar o raster.
    """
    font = _get_font()
    surf = font.render(text, True, color)
    surf = pygame.transform.flip(surf, False, True)   # inverte Y para OpenGL
    data = pygame.image.tostring(surf, "RGBA", False)
    w, h = surf.get_size()

    # glRasterPos em coordenadas de janela: y_gl = altura_janela - y_tela - altura_texto
    y_gl = _SCREEN_H - y - h
    glRasterPos2f(x, y_gl)
    glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)


def _draw_legend(top_y: int) -> None:
    """Desenha a legenda de blocos especiais: itens lado a lado, texto abaixo do quadrado."""
    box    = _HUD_LEGEND_BOX
    gap    = _HUD_LEGEND_GAP
    stride = _HUD_LEGEND_STRIDE
    x0     = _HUD_MARGIN

    for idx, (color, label) in enumerate(_LEGEND_ITEMS):
        bx = x0 + idx * stride

        # ── Quadrado colorido (coordenadas OpenGL: Y↑) ───────────────────
        y_top_gl = _SCREEN_H - top_y
        y_bot_gl = _SCREEN_H - top_y - box

        glColor4f(*color)
        glBegin(GL_QUADS)
        glVertex2f(bx,       y_top_gl)
        glVertex2f(bx + box, y_top_gl)
        glVertex2f(bx + box, y_bot_gl)
        glVertex2f(bx,       y_bot_gl)
        glEnd()

        # ── Borda preta ───────────────────────────────────────────────────
        glColor4f(0.0, 0.0, 0.0, 1.0)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(bx,       y_top_gl)
        glVertex2f(bx + box, y_top_gl)
        glVertex2f(bx + box, y_bot_gl)
        glVertex2f(bx,       y_bot_gl)
        glEnd()
        glLineWidth(1.0)

        # ── Texto abaixo do quadrado (coordenadas de tela: Y↓) ───────────
        text_top = top_y + box + gap
        _draw_text_pixels(label, bx, text_top, (230, 230, 230))


def _draw_heart(cx: float, cy: float, size: float, filled: bool) -> None:
    """Desenha um coração simples em coordenadas de tela (origem canto superior-esq)."""
    r = size / 2.0
    # Cor: vermelho vivo (cheio) ou cinza escuro (vazio)
    if filled:
        glColor4f(0.95, 0.15, 0.20, 1.0)
    else:
        glColor4f(0.35, 0.35, 0.35, 0.7)

    # Dois semicírculos no topo (aproximados por triângulos em leque) + triângulo na ponta
    segments = 12

    # Círculo esquerdo: centro em (cx - r*0.5, cy - r*0.25)
    lx, ly = cx - r * 0.5, cy - r * 0.25
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        a0 = math.pi + i * math.pi / segments
        a1 = math.pi + (i + 1) * math.pi / segments
        glVertex2f(lx, ly)
        glVertex2f(lx + math.cos(a0) * r * 0.55, ly + math.sin(a0) * r * 0.55)
        glVertex2f(lx + math.cos(a1) * r * 0.55, ly + math.sin(a1) * r * 0.55)
    glEnd()

    # Círculo direito: centro em (cx + r*0.5, cy - r*0.25)
    rx2, ry2 = cx + r * 0.5, cy - r * 0.25
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        a0 = math.pi + i * math.pi / segments
        a1 = math.pi + (i + 1) * math.pi / segments
        glVertex2f(rx2, ry2)
        glVertex2f(rx2 + math.cos(a0) * r * 0.55, ry2 + math.sin(a0) * r * 0.55)
        glVertex2f(rx2 + math.cos(a1) * r * 0.55, ry2 + math.sin(a1) * r * 0.55)
    glEnd()

    # Corpo do coração: dois trapézios que formam a ponta
    glBegin(GL_QUADS)
    glVertex2f(cx - r,        cy - r * 0.25)
    glVertex2f(cx + r,        cy - r * 0.25)
    glVertex2f(cx + r * 0.6,  cy + r * 0.5)
    glVertex2f(cx - r * 0.6,  cy + r * 0.5)

    glVertex2f(cx - r * 0.6,  cy + r * 0.5)
    glVertex2f(cx + r * 0.6,  cy + r * 0.5)
    glVertex2f(cx,             cy + r)
    glVertex2f(cx,             cy + r)
    glEnd()


def _draw_hud(lives: int, max_lives: int) -> None:
    """Renderiza corações de vidas e legenda de blocos especiais."""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, _SCREEN_W, _SCREEN_H, 0, -1, 1)   # Y cresce para baixo

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Corações
    s = _HUD_HEART_SIZE
    for i in range(max_lives):
        cx = _HUD_MARGIN + s / 2 + i * (s + _HUD_SPACING)
        cy = _HUD_MARGIN + s / 2
        _draw_heart(cx, cy, s, filled=(i < lives))

    # Legenda logo abaixo dos corações
    hearts_bottom = _HUD_MARGIN + s + 10
    _draw_legend(hearts_bottom)

    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)

    # Restaura projeção perspectiva para o próximo frame
    from OpenGL.GLU import gluPerspective
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, _SCREEN_W / _SCREEN_H, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

CAMERA_MIN_HEIGHT = 2.0
CAMERA_MAX_HEIGHT = 20.0
CAMERA_MIN_DISTANCE = 4.0
CAMERA_MAX_DISTANCE = 24.0
CAMERA_ORBIT_STEP = 2.5
CAMERA_DISTANCE_STEP = 0.25
CAMERA_HEIGHT_STEP = 0.18
CAMERA_MOUSE_SENSITIVITY = 0.25
CAMERA_FOLLOW_SMOOTHING = 8.0

CUBE_KEYS = {
    pygame.K_w: (0, -1),
    pygame.K_s: (0, +1),
    pygame.K_a: (-1, 0),
    pygame.K_d: (+1, 0),
}


def _make_cube(map_: Map) -> Cube:
    col, row = map_.start
    return Cube(position=Position(float(col), 0.5, float(row)))


def main() -> None:
    diff = run_menu()
    if diff is None:
        return

    def _new_map() -> Map:
        return Map.generate(
            cols=diff.cols,
            rows=diff.rows,
            challenge_profile=diff.challenge_profile,
            generator=diff.generator,
            n_paths=diff.n_paths,
            arc_noise=diff.arc_noise,
            branch_count=diff.branch_count,
            branch_length=diff.branch_length,
            main_path_bias=diff.main_path_bias,
            loop_regions=diff.loop_regions,
            reward_branches=diff.reward_branches,
            false_branches=diff.false_branches,
            false_branch_length=diff.false_branch_length,
            risk_shortcuts=diff.risk_shortcuts,
            safe_detours=diff.safe_detours,
            dead_end_ratio=diff.dead_end_ratio,
            prob_heal=diff.prob_heal,
            prob_shrink=diff.prob_shrink,
            prob_grow=diff.prob_grow,
            prob_portal=diff.prob_portal,
            prob_ice=diff.prob_ice,
            prob_invert=diff.prob_invert,
            prob_fragile=diff.prob_fragile,
            prob_bounce=diff.prob_bounce,
            prob_slow=diff.prob_slow,
            prob_checkpoint=diff.prob_checkpoint,
        )

    map_: list[Map] = [_new_map()]
    cube: list[Cube] = [_make_cube(map_[0])]

    last_frame_ms: list[int | None] = [None]
    last_state: list[CubeState | None] = [None]
    last_lives: list[int] = [Cube.MAX_LIVES]
    # yaw=0°: câmera posicionada em +Z relativo ao cubo, olhando para -Z.
    # W move dz=-1 (-Z), que é "para frente" na tela — alinhado com o caminho.
    camera_yaw: list[float] = [0.0]
    camera_height: list[float] = [9.0]
    camera_distance: list[float] = [12.0]

    start_col, start_row = map_[0].start
    camera_eye = pygame.math.Vector3(float(start_col), 9.0, float(start_row) + 12.0)
    camera_target = pygame.math.Vector3(float(start_col), 0.0, float(start_row))

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
        map_[0].draw()
        cube[0].apply_transform()
        cube[0].draw()
        _draw_hud(cube[0].lives, cube[0].max_lives)

    def _reset(reason: str) -> None:
        map_[0] = _new_map()
        cube[0] = _make_cube(map_[0])
        last_state[0] = None
        last_lives[0] = cube[0].lives
        print(f"[Map] {reason} — início em {map_[0].start}")
        _print_lives()

    def _print_lives() -> None:
        c = cube[0]
        bar = "♥ " * c.lives + "♡ " * (c.max_lives - c.lives)
        print(f"[Vidas] {bar.strip()}  ({c.lives}/{c.max_lives})")

    def on_key(event: pygame.event.Event) -> None:
        if event.key == pygame.K_g:
            _reset("novo mapa gerado")

    def on_frame() -> None:
        now_ms = pygame.time.get_ticks()
        if last_frame_ms[0] is None:
            dt = 1.0 / 60.0
        else:
            dt = (now_ms - last_frame_ms[0]) / 1000.0
        last_frame_ms[0] = now_ms

        c = cube[0]
        map_[0].update(dt)
        c.update(dt)

        # Exibe mudança de estado.
        if c.state is not last_state[0]:
            print(f"[Cube] state={c.state.value} grid={c.get_grid_position()}")
            last_state[0] = c.state

        # Exibe mudança de vidas (queda ou cura).
        if c.lives != last_lives[0]:
            last_lives[0] = c.lives
            _print_lives()

        # Game over: sem vidas → reinicia mapa automaticamente após a queda.
        if c.is_dead and c.state == CubeState.IDLE:
            _reset("GAME OVER — sem vidas, reiniciando")
            return

        keys = pygame.key.get_pressed()

        if not c.is_moving():
            for key, direction in CUBE_KEYS.items():
                if keys[key]:
                    dx, dz = direction
                    if c.controls_inverted:
                        dx, dz = -dx, -dz
                    c.try_roll(dx, dz, validator=map_[0])
                    break

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

        yaw = pygame.math.Vector2(0.0, 1.0).rotate(camera_yaw[0])
        desired_target = pygame.math.Vector3(c.position.x, 0.0, c.position.z)
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

    print(f"=== Sandbox Cube ===")
    print(f"WASD=mover | G=novo mapa | setas+mouse=câmera orbital")
    print(f"Mapa gerado — início em {map_[0].start}")

    run(
        draw,
        on_key=on_key,
        on_frame=on_frame,
        on_mouse_motion=on_mouse_motion,
        setup_camera=setup_camera,
        title=f"ProjetoCub [{diff.label}] — WASD=mover | G=novo mapa | setas+mouse=câmera",
    )


if __name__ == "__main__":
    main()
