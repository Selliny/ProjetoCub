"""Tela inicial com seleção de dificuldade — renderizada em OpenGL (neon cyberpunk).

Roda na mesma janela OpenGL do jogo e retorna a DifficultyConfig escolhida,
ou None se o jogador fechar a janela.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame
from pygame.locals import DOUBLEBUF, FULLSCREEN, OPENGL
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_LINE_LOOP,
    GL_LINES,
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
    glPopMatrix,
    glPushMatrix,
    glRasterPos2f,
    glRotatef,
    glScalef,
    glTranslatef,
    glVertex2f,
    glVertex3f,
    glViewport,
)
from OpenGL.GLU import gluPerspective

pygame.init()
_info = pygame.display.Info()
_W, _H = _info.current_w, _info.current_h
pygame.quit()

# Paleta neon / dark cyberpunk (compatível com verde fósforo do terminal)
_BG       = (0.04, 0.04, 0.08, 1.0)
_GREEN    = (0.16, 0.86, 0.16, 1.0)
_GREEN_DIM= (0.08, 0.39, 0.08, 1.0)
_GREEN_HI = (0.55, 1.00, 0.55, 1.0)
_AMBER    = (0.86, 0.71, 0.16, 1.0)
_CYAN     = (0.00, 1.00, 1.00, 1.0)


@dataclass
class DifficultyConfig:
    label: str
    challenge_profile: str
    generator: str
    cols: int
    rows: int
    n_paths: int
    arc_noise: float
    branch_count: int
    branch_length: int
    main_path_bias: float
    loop_regions: int
    reward_branches: int
    false_branches: int
    false_branch_length: int
    risk_shortcuts: int
    safe_detours: int
    dead_end_ratio: float
    prob_heal: float
    prob_shrink: float
    prob_grow: float
    prob_ice: float
    prob_invert: float
    prob_fragile: float
    camera_distance_default: float = 12.0
    camera_height_default: float = 9.0
    cluster_zones: list = field(default_factory=list)
    combo_sequences: list = field(default_factory=list)
    corridor_theme_count: int = 0


_DIFFICULTIES: list[DifficultyConfig] = [
    DifficultyConfig(
        label="FACIL",
        challenge_profile="easy",
        generator="corridor",
        cols=48, rows=22,
        n_paths=4,
        arc_noise=0.10,
        branch_count=2,
        branch_length=8,
        main_path_bias=0.72,
        loop_regions=4,
        reward_branches=3,
        false_branches=0,
        false_branch_length=5,
        risk_shortcuts=1,
        safe_detours=3,
        dead_end_ratio=0.0,
        prob_heal=0.035,
        prob_shrink=0.006,
        prob_grow=0.006,
        prob_ice=0.012,
        prob_invert=0.004,
        prob_fragile=0.008,
        camera_distance_default=14.0,
        camera_height_default=10.0,
        cluster_zones=[],
        combo_sequences=[],
        corridor_theme_count=2,
    ),
    DifficultyConfig(
        label="MEDIO",
        challenge_profile="medium",
        generator="corridor",
        cols=52, rows=28,
        n_paths=3,
        arc_noise=0.20,
        branch_count=3,
        branch_length=11,
        main_path_bias=0.62,
        loop_regions=5,
        reward_branches=3,
        false_branches=0,
        false_branch_length=11,
        risk_shortcuts=2,
        safe_detours=1,
        dead_end_ratio=0.0,
        prob_heal=0.005,
        prob_shrink=0.020,
        prob_grow=0.006,
        prob_ice=0.018,
        prob_invert=0.014,
        prob_fragile=0.018,
        camera_distance_default=10.0,
        camera_height_default=7.0,
        cluster_zones=[(0.40, 0.65, "ice", 1.8)],
        combo_sequences=[["ice", "fragile"]],
        corridor_theme_count=3,
    ),
    DifficultyConfig(
        label="DIFICIL",
        challenge_profile="hard",
        generator="corridor",
        cols=60, rows=32,
        n_paths=2,
        arc_noise=0.30,
        branch_count=3,
        branch_length=16,
        main_path_bias=0.55,
        loop_regions=6,
        reward_branches=2,
        false_branches=0,
        false_branch_length=14,
        risk_shortcuts=3,
        safe_detours=0,
        dead_end_ratio=0.0,
        prob_heal=0.004,
        prob_shrink=0.018,
        prob_grow=0.010,
        prob_ice=0.028,
        prob_invert=0.025,
        prob_fragile=0.035,
        camera_distance_default=8.0,
        camera_height_default=5.0,
        cluster_zones=[
            (0.55, 0.75, "ice",     2.5),
            (0.75, 0.90, "fragile", 2.0),
            (0.30, 0.50, "bounce",  1.8),
        ],
        combo_sequences=[
            ["ice", "fragile"],
            ["invert", "fragile"],
        ],
        corridor_theme_count=3,
    ),
]


# ── Helpers de renderização OpenGL 2D ────────────────────────────────────────

def _set_2d() -> None:
    """Muda para projeção ortográfica 2D (Y cresce para baixo)."""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, _W, _H, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


def _set_3d() -> None:
    """Restaura projeção perspectiva 3D."""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, _W / _H, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glEnable(GL_DEPTH_TEST)


def _gl_rect(x: float, y: float, w: float, h: float, r: float, g: float, b: float, a: float) -> None:
    glColor4f(r, g, b, a)
    glBegin(GL_QUADS)
    glVertex2f(x,     y    )
    glVertex2f(x + w, y    )
    glVertex2f(x + w, y + h)
    glVertex2f(x,     y + h)
    glEnd()


def _gl_rect_outline(x: float, y: float, w: float, h: float, r: float, g: float, b: float, a: float, lw: float = 1.0) -> None:
    glColor4f(r, g, b, a)
    glLineWidth(lw)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x,     y    )
    glVertex2f(x + w, y    )
    glVertex2f(x + w, y + h)
    glVertex2f(x,     y + h)
    glEnd()
    glLineWidth(1.0)


def _gl_line(x1: float, y1: float, x2: float, y2: float, r: float, g: float, b: float, a: float, lw: float = 1.0) -> None:
    glColor4f(r, g, b, a)
    glLineWidth(lw)
    glBegin(GL_LINES)
    glVertex2f(x1, y1); glVertex2f(x2, y2)
    glEnd()
    glLineWidth(1.0)


def _gl_text(font: pygame.font.Font, text: str, x: float, y: float, r: float, g: float, b: float) -> None:
    """Renderiza texto. y=0 é o topo da tela (glOrtho com Y crescendo para baixo).

    glDrawPixels ancora no canto inferior-esquerdo e sobe. Como nosso ortho tem Y↓,
    o 'inferior' no espaço de projeção é y+h (maior valor de Y). Além disso,
    glDrawPixels lê pixels da base para o topo, enquanto pygame armazena de cima
    para baixo — então usamos flip vertical para corrigir.
    """
    surf = font.render(text, True, (int(r * 255), int(g * 255), int(b * 255)))
    surf = pygame.transform.flip(surf, False, True)
    data = pygame.image.tostring(surf, "RGBA", False)
    w, h = surf.get_size()
    glRasterPos2f(int(x), int(y) + h)
    glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)


def _gl_scanlines() -> None:
    """Overlay de scanlines CRT (linhas horizontais semitransparentes)."""
    glColor4f(0.0, 0.0, 0.0, 0.12)
    glBegin(GL_LINES)
    y = 0.0
    while y < _H:
        glVertex2f(0, y); glVertex2f(_W, y)
        y += 3.0
    glEnd()


def _gl_border() -> None:
    """Borda dupla neon no perímetro da tela."""
    _gl_rect_outline(8, 8, _W - 16, _H - 16, *_GREEN_DIM, lw=1.0)
    _gl_rect_outline(13, 13, _W - 26, _H - 26, *_GREEN_DIM, lw=1.0)


# ── Cubo 3D animado (renderizado via OpenGL real) ────────────────────────────

_CUBE_FACES = [
    # (normal_brighness, v0..v3)  — cada face tem cor levemente diferente
    (1.00, [(-1,-1,-1),( 1,-1,-1),( 1, 1,-1),(-1, 1,-1)]),  # trás
    (0.85, [(-1,-1, 1),( 1,-1, 1),( 1, 1, 1),(-1, 1, 1)]),  # frente
    (1.10, [(-1, 1,-1),( 1, 1,-1),( 1, 1, 1),(-1, 1, 1)]),  # topo
    (0.60, [(-1,-1,-1),( 1,-1,-1),( 1,-1, 1),(-1,-1, 1)]),  # base
    (0.75, [( 1,-1,-1),( 1,-1, 1),( 1, 1, 1),( 1, 1,-1)]),  # direita
    (0.70, [(-1,-1, 1),(-1,-1,-1),(-1, 1,-1),(-1, 1, 1)]),  # esquerda
]

_CUBE_EDGES = [
    (0,1),(1,2),(2,3),(3,0),
    (4,5),(5,6),(6,7),(7,4),
    (0,4),(1,5),(2,6),(3,7),
]

_CUBE_VERTS_RAW = [
    (-1,-1,-1),( 1,-1,-1),( 1, 1,-1),(-1, 1,-1),
    (-1,-1, 1),( 1,-1, 1),( 1, 1, 1),(-1, 1, 1),
]


def _draw_3d_cube(angle: float, cx: float, cy: float, scale: float) -> None:
    """Desenha cubo 3D real no ponto (cx, cy) da viewport usando OpenGL 3D."""
    _set_3d()
    glLoadIdentity()
    glTranslatef(cx, cy, -8.0)
    glScalef(scale, scale, scale)
    glRotatef(angle * 50.0, 0.3, 1.0, 0.1)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Faces roxo escuro
    glBegin(GL_QUADS)
    for brightness, verts in _CUBE_FACES:
        b = min(brightness, 1.3)
        glColor4f(0.18 * b, 0.0, 0.35 * b, 0.85)
        for vx, vy, vz in verts:
            glVertex3f(vx, vy, vz)
    glEnd()

    # Outline magenta neon + glow
    for delta, alpha, lw in ((0.0, 1.0, 2.0), (0.04, 0.35, 1.5), (0.09, 0.12, 1.0)):
        s = 1.0 + delta
        glColor4f(1.0, 0.0, 1.0, alpha)
        glLineWidth(lw)
        glBegin(GL_LINES)
        for i, j in _CUBE_EDGES:
            vx, vy, vz = _CUBE_VERTS_RAW[i]
            glVertex3f(vx * s, vy * s, vz * s)
            vx, vy, vz = _CUBE_VERTS_RAW[j]
            glVertex3f(vx * s, vy * s, vz * s)
        glEnd()
    glLineWidth(1.0)

    glDisable(GL_BLEND)


# ── Loop do menu ──────────────────────────────────────────────────────────────

_DIFF_DESCRIPTIONS = [
    "Poucos obstaculos e mais espaco para errar",
    "Equilibrio entre risco e recompensa",
    "Gelo, fragil e inversao combinados",
]


def run_menu() -> DifficultyConfig | None:
    pygame.init()
    pygame.font.init()

    pygame.display.set_mode((_W, _H), DOUBLEBUF | OPENGL | FULLSCREEN)
    pygame.display.set_caption("Cub Project!")
    glViewport(0, 0, _W, _H)
    clock = pygame.time.Clock()

    font_title  = pygame.font.SysFont("couriernew", 72, bold=True)
    font_option = pygame.font.SysFont("couriernew", 30, bold=True)
    font_desc   = pygame.font.SysFont("couriernew", 17)
    font_label  = pygame.font.SysFont("couriernew", 16)
    font_credit = pygame.font.SysFont("couriernew", 22)

    _CREDIT_LINES = [
        ("cyan", "Projeto Cub  ·  Eng. da Computacao"),
        ("hi",   "Prof. Bruno Aguilar da Cunha"),
        ("dim",  ""),
        ("dim",  "Leonardo Canalez  ·  Lucas Madureira Santiago"),
        ("dim",  "Nicolas Ferrari  ·  Rafael Santos  ·  Selliny Sampaio"),
    ]

    # Zonas de layout (frações da altura da tela)
    TITLE_Y     = int(_H * 0.04)
    CREDIT_Y    = int(_H * 0.15)
    CREDIT_STEP = int(_H * 0.055)
    SEP1_Y      = int(_H * 0.40)
    OPTIONS_TOP = int(_H * 0.45)
    OPT_SPACING = int(_H * 0.14)

    # Cubo 3D: menor e mais alto
    CUBE_CX = 1.8
    CUBE_CY = 1.2
    CUBE_SC = 0.7

    option_labels = [f"[ {d.label} ]" for d in _DIFFICULTIES]
    block_h = font_option.get_height() + 4 + font_desc.get_height()

    angle = 0.0
    selected_idx = 0
    blink_t = 0.0
    cursor_visible = True

    while True:
        dt = clock.tick(60) / 1000.0
        angle += dt
        blink_t += dt
        if blink_t >= 0.53:
            blink_t = 0.0
            cursor_visible = not cursor_visible

        option_rects: list[pygame.Rect] = []
        for i in range(len(_DIFFICULTIES)):
            ry = OPTIONS_TOP + i * OPT_SPACING
            option_rects.append(pygame.Rect(50, ry - 4, _W // 2, block_h + 8))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return None
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_idx = (selected_idx - 1) % len(_DIFFICULTIES)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_idx = (selected_idx + 1) % len(_DIFFICULTIES)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    pygame.quit()
                    return _DIFFICULTIES[selected_idx]
            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                for i, r in enumerate(option_rects):
                    if r.collidepoint(mx, my):
                        selected_idx = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, r in enumerate(option_rects):
                    if r.collidepoint(mx, my):
                        pygame.quit()
                        return _DIFFICULTIES[i]

        # ── render 3D ────────────────────────────────────────────────────
        glClearColor(*_BG)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        _draw_3d_cube(angle, CUBE_CX, CUBE_CY, CUBE_SC)

        # ── render 2D ────────────────────────────────────────────────────
        _set_2d()
        _gl_border()

        # Zona topo: título
        _gl_text(font_title, "Cub Project!", 60, TITLE_Y, *_GREEN_HI[:3])

        # Bloco de créditos do projeto (topo esquerdo, abaixo do título)
        cy = CREDIT_Y
        for color_key, line in _CREDIT_LINES:
            if not line:
                cy += CREDIT_STEP // 2
                continue
            if color_key == "cyan":
                _gl_text(font_credit, line, 60, cy, *_CYAN[:3])
            elif color_key == "hi":
                _gl_text(font_credit, line, 60, cy, *_GREEN_HI[:3])
            else:
                _gl_text(font_credit, line, 60, cy, 0.75, 0.75, 0.75)
            cy += CREDIT_STEP

        # Separador 1 (cyan neon)
        _gl_line(40, SEP1_Y, _W - 40, SEP1_Y, *_CYAN[:3], 0.35, lw=1.0)

        # Label de seleção
        _gl_text(font_label, "> SELECIONE A DIFICULDADE:", 60, SEP1_Y + 8, *_GREEN_DIM[:3])

        # Zona opções
        for i, (label, desc) in enumerate(zip(option_labels, _DIFF_DESCRIPTIONS)):
            is_sel = (i == selected_idx)
            ry = OPTIONS_TOP + i * OPT_SPACING

            if is_sel:
                _gl_rect(50, ry - 6, _W // 2 - 60, block_h + 12, 0.10, 0.08, 0.01, 0.92)
                _gl_rect_outline(50, ry - 6, _W // 2 - 60, block_h + 12, *_AMBER[:3], 0.9, lw=1.5)
                _gl_rect_outline(47, ry - 9, _W // 2 - 54, block_h + 18, *_AMBER[:3], 0.20, lw=1.0)

            prefix_text = "> " if is_sel else "  "
            cr, cg, cb, _ = _AMBER if is_sel else _GREEN
            cursor = ("_" if cursor_visible else " ") if is_sel else ""
            name_text = f"{prefix_text}{label}{cursor}"
            _gl_text(font_option, name_text, 60, ry, cr, cg, cb)

            _gl_text(font_desc, f"   {desc}", 60, ry + font_option.get_height() + 4, 0.85, 0.85, 0.85)

        _gl_scanlines()
        pygame.display.flip()

    pygame.quit()
    return None


def get_next_difficulty(current: DifficultyConfig) -> DifficultyConfig | None:
    try:
        idx = _DIFFICULTIES.index(current)
    except ValueError:
        return None
    next_idx = idx + 1
    if next_idx >= len(_DIFFICULTIES):
        return None
    return _DIFFICULTIES[next_idx]


def run_end_screen(
    lives: int,
    max_lives: int,
    label: str | None = None,
    next_label: str | None = None,
    elapsed: str = "00:00:00",
) -> bool:
    """Mostra a tela final em OpenGL. Retorna True quando SPACE pede o próximo nível."""
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((_W, _H), DOUBLEBUF | OPENGL | FULLSCREEN)
    pygame.display.set_caption("Cub Project! - Fim")
    glViewport(0, 0, _W, _H)
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("couriernew", 88, bold=True)
    font_mid   = pygame.font.SysFont("couriernew", 32, bold=True)
    font_text  = pygame.font.SysFont("couriernew", 24)
    font_small = pygame.font.SysFont("couriernew", 20)
    font_hint  = pygame.font.SysFont("couriernew", 22)

    angle = 0.0
    blink_t = 0.0
    cursor_visible = True

    cube_3d_cx = 2.2
    cube_3d_cy = 0.6
    cube_scale  = 1.1

    while True:
        dt = clock.tick(60) / 1000.0
        angle += dt
        blink_t += dt
        if blink_t >= 0.53:
            blink_t = 0.0
            cursor_visible = not cursor_visible

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    return False
                if event.key == pygame.K_SPACE and next_label is not None:
                    return True

        # ── render 3D ────────────────────────────────────────────────────
        glClearColor(*_BG)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        _draw_3d_cube(angle, cube_3d_cx, cube_3d_cy, cube_scale)

        # ── render 2D ────────────────────────────────────────────────────
        _set_2d()

        _gl_border()

        title_text = "PARABENS!"
        tw = font_title.size(title_text)[0]
        _gl_text(font_title, title_text, _W // 4 - tw // 2, 70, *_GREEN_HI[:3])

        sep_y = 70 + font_title.get_height() + 10
        _gl_line(40, sep_y, _W // 2 - 40, sep_y, *_GREEN_DIM[:3], 0.7)

        msg = "VOCE CHEGOU AO FIM DO CAMINHO"
        mw = font_mid.size(msg)[0]
        _gl_text(font_mid, msg, _W // 4 - mw // 2, sep_y + 30, *_GREEN[:3])

        lives_text = f"VIDAS FINAIS: {lives}/{max_lives}"
        lw2 = font_text.size(lives_text)[0]
        _gl_text(font_text, lives_text, _W // 4 - lw2 // 2, sep_y + 90, 0.85, 0.85, 0.85)

        if label is not None:
            diff_text = f"DIFICULDADE: {label}"
            dw = font_text.size(diff_text)[0]
            _gl_text(font_text, diff_text, _W // 4 - dw // 2, sep_y + 130, 0.85, 0.85, 0.85)

        time_label = f"TEMPO: {elapsed}"
        tw2 = font_mid.size(time_label)[0]
        _gl_text(font_mid, time_label, _W // 4 - tw2 // 2, sep_y + 185, *_CYAN[:3])

        if next_label is None:
            prompt = "> ENTER PARA SAIR" + ("_" if cursor_visible else " ")
        else:
            prompt = f"> ENTER PARA SAIR  |  SPACE PARA {next_label}" + ("_" if cursor_visible else " ")
        pw = font_text.size(prompt)[0]
        _gl_text(font_text, prompt, _W // 4 - pw // 2, _H - 120, *_AMBER[:3])

        if next_label is None:
            hint_text = "ESC/ENTER para sair"
        else:
            hint_text = f"ESC/ENTER para sair  |  SPACE para nivel {next_label}"
        hw = font_hint.size(hint_text)[0]
        _gl_text(font_hint, hint_text, (_W - hw) // 2, _H - 48, *_GREEN_DIM[:3])

        _gl_scanlines()

        pygame.display.flip()

    return False
