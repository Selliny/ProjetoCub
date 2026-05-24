"""Ponto de entrada do jogo.

Controles:
  W / S           → cubo tomba para frente / trás
  A / D           → cubo tomba para esquerda / direita
  G               → gera novo mapa (mantém dificuldade)
  ↑ / ↓           → aproxima / afasta a câmera
  ← / →           → orbita a câmera ao redor do cubo
  Q / E           → sobe / desce a câmera
  Mouse btn esq   → arrastar orbita e ajusta altura

Como rodar (raiz do projeto, venv ativado):

    python main.py
"""

import math

import pygame
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
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
    glClear,
    glClearColor,
    glColor4f,
    glDisable,
    glDrawPixels,
    glEnable,
    glEnd,
    glLineWidth,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glRasterPos2f,
    glVertex2f,
    glViewport,
)
from OpenGL.GLU import gluLookAt, gluPerspective
from pygame.locals import DOUBLEBUF, FULLSCREEN, OPENGL

from sandboxes.menu import get_next_difficulty, run_end_screen, run_menu
from src.entities.block import Block
from src.entities.cube import Cube, CubeState
from src.graphics.position import Position
from src.world.map import Map

# ── Configuração de tela (resolução nativa detectada em runtime) ───────────────
pygame.init()
_info = pygame.display.Info()
_SCREEN_W = _info.current_w
_SCREEN_H = _info.current_h
pygame.quit()

# ── HUD ───────────────────────────────────────────────────────────────────────
_HUD_HEART_SIZE  = 28
_HUD_MARGIN      = 16
_HUD_SPACING     = 6
_HUD_LEGEND_BOX    = 18
_HUD_LEGEND_GAP    = 3
_HUD_LEGEND_STRIDE = 70

_LEGEND_ITEMS: list[tuple[tuple[float, float, float, float], str]] = [
    ((1.0, 0.3, 0.7, 1.0),    "Curar"),    # HealBlock    — rosa neon
    ((0.7, 0.0, 1.0, 1.0),    "Encolher"), # ShrinkBlock  — roxo neon
    ((0.0, 1.0, 0.4, 1.0),    "Crescer"),  # GrowBlock    — verde neon
    ((0.0, 0.8, 1.0, 1.0),    "Gelo"),     # IceBlock     — ciano neon
    ((1.0, 0.0, 0.8, 1.0),    "Inverter"), # InvertBlock  — magenta neon
    ((0.85, 0.85, 0.85, 1.0), "Fragil"),   # FragileBlock — branco
    ((1.0, 0.8, 0.0, 1.0),    "Blink"),    # BlinkBlock   — amarelo neon
]

_font: pygame.font.Font | None = None


def _get_font() -> pygame.font.Font:
    global _font
    if _font is None:
        pygame.font.init()
        _font = pygame.font.SysFont("consolas", 15, bold=False)
    return _font


def _draw_text_pixels(text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    font = _get_font()
    surf = font.render(text, True, color)
    surf = pygame.transform.flip(surf, False, True)
    data = pygame.image.tostring(surf, "RGBA", False)
    w, h = surf.get_size()
    y_gl = _SCREEN_H - y - h
    glRasterPos2f(x, y_gl)
    glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)


def _draw_legend(top_y: int) -> None:
    box    = _HUD_LEGEND_BOX
    gap    = _HUD_LEGEND_GAP
    stride = _HUD_LEGEND_STRIDE
    x0     = _HUD_MARGIN

    for idx, (color, label) in enumerate(_LEGEND_ITEMS):
        bx = x0 + idx * stride
        y_top_gl = _SCREEN_H - top_y
        y_bot_gl = _SCREEN_H - top_y - box

        glColor4f(*color)
        glBegin(GL_QUADS)
        glVertex2f(bx,       y_top_gl)
        glVertex2f(bx + box, y_top_gl)
        glVertex2f(bx + box, y_bot_gl)
        glVertex2f(bx,       y_bot_gl)
        glEnd()

        glColor4f(0.0, 0.0, 0.0, 1.0)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(bx,       y_top_gl)
        glVertex2f(bx + box, y_top_gl)
        glVertex2f(bx + box, y_bot_gl)
        glVertex2f(bx,       y_bot_gl)
        glEnd()
        glLineWidth(1.0)

        _draw_text_pixels(label, bx, top_y + box + gap, (230, 230, 230))


def _draw_heart(cx: float, cy: float, size: float, filled: bool) -> None:
    r = size / 2.0
    if filled:
        glColor4f(0.95, 0.15, 0.20, 1.0)
    else:
        glColor4f(0.35, 0.35, 0.35, 0.7)

    segments = 12
    lx, ly = cx - r * 0.5, cy - r * 0.25
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        a0 = math.pi + i * math.pi / segments
        a1 = math.pi + (i + 1) * math.pi / segments
        glVertex2f(lx, ly)
        glVertex2f(lx + math.cos(a0) * r * 0.55, ly + math.sin(a0) * r * 0.55)
        glVertex2f(lx + math.cos(a1) * r * 0.55, ly + math.sin(a1) * r * 0.55)
    glEnd()

    rx2, ry2 = cx + r * 0.5, cy - r * 0.25
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        a0 = math.pi + i * math.pi / segments
        a1 = math.pi + (i + 1) * math.pi / segments
        glVertex2f(rx2, ry2)
        glVertex2f(rx2 + math.cos(a0) * r * 0.55, ry2 + math.sin(a0) * r * 0.55)
        glVertex2f(rx2 + math.cos(a1) * r * 0.55, ry2 + math.sin(a1) * r * 0.55)
    glEnd()

    glBegin(GL_QUADS)
    glVertex2f(cx - r,       cy - r * 0.25)
    glVertex2f(cx + r,       cy - r * 0.25)
    glVertex2f(cx + r * 0.6, cy + r * 0.5)
    glVertex2f(cx - r * 0.6, cy + r * 0.5)
    glVertex2f(cx - r * 0.6, cy + r * 0.5)
    glVertex2f(cx + r * 0.6, cy + r * 0.5)
    glVertex2f(cx,            cy + r)
    glVertex2f(cx,            cy + r)
    glEnd()


def _draw_hud(lives: int, max_lives: int, active_effects: list | None = None, elapsed_s: float = 0.0) -> None:
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, _SCREEN_W, _SCREEN_H, 0, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    s = _HUD_HEART_SIZE
    for i in range(max_lives):
        cx = _HUD_MARGIN + s / 2 + i * (s + _HUD_SPACING)
        cy = _HUD_MARGIN + s / 2
        _draw_heart(cx, cy, s, filled=(i < lives))

    _draw_legend(_HUD_MARGIN + s + 10)

    # Barras de efeitos temporários ativos
    if active_effects:
        bar_w = 48
        bar_h = 7
        bar_y = _HUD_MARGIN + s + 6
        for i, eff in enumerate(active_effects):
            bx = _HUD_MARGIN + i * (bar_w + 6)
            frac = max(0.0, min(1.0, eff["remaining"] / eff["max"]))
            # Fundo cinza
            glColor4f(0.25, 0.25, 0.25, 0.85)
            glBegin(GL_QUADS)
            glVertex2f(bx,          bar_y)
            glVertex2f(bx + bar_w,  bar_y)
            glVertex2f(bx + bar_w,  bar_y + bar_h)
            glVertex2f(bx,          bar_y + bar_h)
            glEnd()
            # Preenchimento colorido
            r, g, b, a = eff["color"]
            glColor4f(r, g, b, a)
            glBegin(GL_QUADS)
            glVertex2f(bx,                      bar_y)
            glVertex2f(bx + bar_w * frac,       bar_y)
            glVertex2f(bx + bar_w * frac,       bar_y + bar_h)
            glVertex2f(bx,                      bar_y + bar_h)
            glEnd()
            # Rótulo do efeito
            _draw_text_pixels(eff["name"], int(bx), int(bar_y + bar_h + 2), (220, 220, 220))

    # Timer no canto superior direito
    total_s = int(elapsed_s)
    timer_str = f"{total_s // 3600:02d}:{(total_s % 3600) // 60:02d}:{total_s % 60:02d}"
    tw, th = _get_font().size(timer_str)
    _draw_text_pixels(timer_str, _SCREEN_W - tw - _HUD_MARGIN, _HUD_MARGIN, (0, 220, 220))

    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, _SCREEN_W / _SCREEN_H, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)


# ── Câmera ────────────────────────────────────────────────────────────────────
_CAMERA_MIN_HEIGHT    = 2.0
_CAMERA_MAX_HEIGHT    = 20.0
_CAMERA_MIN_DISTANCE  = 4.0
_CAMERA_MAX_DISTANCE  = 24.0
_CAMERA_ORBIT_STEP    = 2.5
_CAMERA_DISTANCE_STEP = 0.25
_CAMERA_HEIGHT_STEP   = 0.18
_CAMERA_MOUSE_SENS    = 0.25
_CAMERA_SMOOTHING     = 8.0

_CUBE_KEYS = {
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

    # ── Inicialização OpenGL ──────────────────────────────────────────────
    pygame.init()
    pygame.display.set_mode((_SCREEN_W, _SCREEN_H), DOUBLEBUF | OPENGL | FULLSCREEN)
    pygame.display.set_caption(f"Cub Project! [{diff.label}]")
    Block.reset_texture_cache()

    glViewport(0, 0, _SCREEN_W, _SCREEN_H)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, _SCREEN_W / _SCREEN_H, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glEnable(GL_DEPTH_TEST)

    # ── Estado do jogo ────────────────────────────────────────────────────
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
            prob_ice=diff.prob_ice,
            prob_invert=diff.prob_invert,
            prob_fragile=diff.prob_fragile,
            cluster_zones=diff.cluster_zones,
            combo_sequences=diff.combo_sequences,
            corridor_theme_count=diff.corridor_theme_count,
        )

    map_: list[Map] = [_new_map()]
    cube: list[Cube] = [_make_cube(map_[0])]

    elapsed_s: list[float] = [0.0]   # timer global — não para com mortes

    last_frame_ms: list[int | None] = [None]
    last_state: list[CubeState | None] = [None]
    last_lives: list[int] = [Cube.MAX_LIVES]

    camera_yaw: list[float]      = [0.0]
    camera_height: list[float]   = [diff.camera_height_default]
    camera_distance: list[float] = [diff.camera_distance_default]

    start_col, start_row = map_[0].start
    camera_eye    = pygame.math.Vector3(float(start_col), diff.camera_height_default, float(start_row) + diff.camera_distance_default)
    camera_target = pygame.math.Vector3(float(start_col), 0.0, float(start_row))

    def _clamp_camera() -> None:
        camera_height[0]   = max(_CAMERA_MIN_HEIGHT,   min(_CAMERA_MAX_HEIGHT,   camera_height[0]))
        camera_distance[0] = max(_CAMERA_MIN_DISTANCE, min(_CAMERA_MAX_DISTANCE, camera_distance[0]))

    def _reset(reason: str) -> None:
        map_[0]       = _new_map()
        cube[0]       = _make_cube(map_[0])
        last_state[0] = None
        last_lives[0] = cube[0].lives
        print(f"[Map] {reason} — início em {map_[0].start}")
        _print_lives()

    def _print_lives() -> None:
        c = cube[0]
        bar = "♥ " * c.lives + "♡ " * (c.max_lives - c.lives)
        print(f"[Vidas] {bar.strip()}  ({c.lives}/{c.max_lives})")

    print("=== Cub Project! ===")
    print("WASD=mover | G=novo mapa | setas+mouse=câmera orbital")
    print(f"Dificuldade: {diff.label} | Mapa gerado — início em {map_[0].start}")

    # ── Loop principal ────────────────────────────────────────────────────
    while True:
        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_g:
                    _reset("novo mapa gerado")
            if event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[0]:
                    dx, dy = event.rel
                    camera_yaw[0]    -= dx * _CAMERA_MOUSE_SENS
                    camera_height[0] -= dy * _CAMERA_HEIGHT_STEP
                    _clamp_camera()

        # Delta time
        now_ms = pygame.time.get_ticks()
        if last_frame_ms[0] is None:
            dt = 1.0 / 60.0
        else:
            dt = (now_ms - last_frame_ms[0]) / 1000.0
        last_frame_ms[0] = now_ms

        elapsed_s[0] += dt

        # Atualiza mapa (FragileBlock timers) e cubo
        map_[0].update(dt)
        cube[0].check_ground(map_[0])
        c = cube[0]
        c.update(dt)

        if c.state is not last_state[0]:
            print(f"[Cube] state={c.state.value} grid={c.get_grid_position()}")
            last_state[0] = c.state

        if c.lives != last_lives[0]:
            last_lives[0] = c.lives
            _print_lives()

        if c.is_dead and c.state == CubeState.IDLE:
            _reset("GAME OVER — sem vidas, reiniciando")
            continue

        if c.reached_end and c.state == CubeState.IDLE:
            next_diff = get_next_difficulty(diff)
            total_s = int(elapsed_s[0])
            elapsed_fmt = f"{total_s // 3600:02d}:{(total_s % 3600) // 60:02d}:{total_s % 60:02d}"
            advance = run_end_screen(
                c.lives,
                c.max_lives,
                diff.label,
                next_diff.label if next_diff is not None else None,
                elapsed=elapsed_fmt,
            )
            if not advance or next_diff is None:
                pygame.quit()
                return

            diff = next_diff
            pygame.display.set_mode((_SCREEN_W, _SCREEN_H), DOUBLEBUF | OPENGL | FULLSCREEN)
            pygame.display.set_caption(f"Cub Project! [{diff.label}]")
            Block.reset_texture_cache()

            glViewport(0, 0, _SCREEN_W, _SCREEN_H)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45, _SCREEN_W / _SCREEN_H, 0.1, 100.0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glEnable(GL_DEPTH_TEST)

            map_[0] = _new_map()
            cube[0] = _make_cube(map_[0])
            elapsed_s[0] = 0.0
            last_frame_ms[0] = None
            last_state[0] = None
            last_lives[0] = cube[0].lives
            camera_yaw[0] = 0.0
            camera_height[0] = diff.camera_height_default
            camera_distance[0] = diff.camera_distance_default

            start_col, start_row = map_[0].start
            camera_eye = pygame.math.Vector3(float(start_col), diff.camera_height_default, float(start_row) + diff.camera_distance_default)
            camera_target = pygame.math.Vector3(float(start_col), 0.0, float(start_row))

            print(f"Dificuldade: {diff.label} | Mapa gerado — início em {map_[0].start}")
            continue

        # Input de movimento (respeita inversão de controles)
        keys = pygame.key.get_pressed()
        if not c.is_moving():
            for key, direction in _CUBE_KEYS.items():
                if keys[key]:
                    dx, dz = direction
                    if c.controls_inverted:
                        dx, dz = -dx, -dz
                    c.try_roll(dx, dz, validator=map_[0])
                    break

        # Input de câmera
        if keys[pygame.K_LEFT]:
            camera_yaw[0] += _CAMERA_ORBIT_STEP
        if keys[pygame.K_RIGHT]:
            camera_yaw[0] -= _CAMERA_ORBIT_STEP
        if keys[pygame.K_UP]:
            camera_distance[0] -= _CAMERA_DISTANCE_STEP
        if keys[pygame.K_DOWN]:
            camera_distance[0] += _CAMERA_DISTANCE_STEP
        if keys[pygame.K_q]:
            camera_height[0] += _CAMERA_HEIGHT_STEP
        if keys[pygame.K_z]:
            camera_height[0] -= _CAMERA_HEIGHT_STEP
        _clamp_camera()

        # Posição desejada da câmera (suavizada)
        yaw = pygame.math.Vector2(0.0, 1.0).rotate(camera_yaw[0])
        desired_target = pygame.math.Vector3(c.position.x, 0.0, c.position.z)
        desired_eye    = pygame.math.Vector3(
            desired_target.x + yaw.x * camera_distance[0],
            camera_height[0],
            desired_target.z + yaw.y * camera_distance[0],
        )
        blend = min(1.0, _CAMERA_SMOOTHING * dt)
        camera_target.update(camera_target.lerp(desired_target, blend))
        camera_eye.update(camera_eye.lerp(desired_eye, blend))

        # Render
        glClearColor(0.04, 0.04, 0.08, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        gluLookAt(
            camera_eye.x,    camera_eye.y,    camera_eye.z,
            camera_target.x, camera_target.y, camera_target.z,
            0.0, 1.0, 0.0,
        )

        map_[0].draw()
        c.apply_transform()
        c.draw()
        _draw_hud(c.lives, c.max_lives, c.active_effects, elapsed_s[0])

        pygame.display.flip()
        pygame.time.wait(10)


if __name__ == "__main__":
    main()
