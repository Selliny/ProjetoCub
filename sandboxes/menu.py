"""Tela inicial com seleção de dificuldade — estética de terminal retrô.

Roda em pygame 2D puro (sem OpenGL) e retorna a DifficultyConfig escolhida,
ou None se o jogador fechar a janela.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

_W, _H = 1920, 1080

# Paleta terminal verde-fósforo
_BG       = (  4,  10,   4)   # preto quase puro
_GREEN    = ( 40, 220,  40)   # verde fósforo principal
_GREEN_DIM= ( 20, 100,  20)   # verde escuro para detalhes
_GREEN_HI = (140, 255, 140)   # destaque claro
_AMBER    = (220, 180,  40)   # âmbar para seleção
_SCANLINE = (  0,   0,   0, 80)  # overlay das scanlines

# Cubo 3D: vértices de um cubo unitário centrado na origem
_VERTS = [
    (-1, -1, -1), ( 1, -1, -1), ( 1,  1, -1), (-1,  1, -1),  # face traseira
    (-1, -1,  1), ( 1, -1,  1), ( 1,  1,  1), (-1,  1,  1),  # face frontal
]
_EDGES = [
    (0,1),(1,2),(2,3),(3,0),  # traseira
    (4,5),(5,6),(6,7),(7,4),  # frontal
    (0,4),(1,5),(2,6),(3,7),  # laterais
]
_FACES = [
    (0,1,2,3), (4,5,6,7), (0,1,5,4),
    (2,3,7,6), (0,3,7,4), (1,2,6,5),
]


@dataclass
class DifficultyConfig:
    label: str
    cols: int
    rows: int
    prob_heal: float
    prob_shrink: float
    prob_grow: float
    prob_portal: float


_DIFFICULTIES: list[DifficultyConfig] = [
    DifficultyConfig(
        label="FACIL",
        cols=16, rows=16,
        prob_heal=0.06,
        prob_shrink=0.01,
        prob_grow=0.005,
        prob_portal=0.012,
    ),
    DifficultyConfig(
        label="MEDIO",
        cols=32, rows=32,
        prob_heal=0.005,
        prob_shrink=0.04,
        prob_grow=0.002,
        prob_portal=0.050,
    ),
    DifficultyConfig(
        label="DIFICIL",
        cols=56, rows=56,
        prob_heal=0.001,
        prob_shrink=0.08,
        prob_grow=0.002,
        prob_portal=0.090,
    ),
]


def _project(vx: float, vy: float, vz: float, fov: float, cx: float, cy: float, scale: float) -> tuple[float, float]:
    z = vz + fov
    if z == 0:
        z = 0.001
    sx = cx + (vx / z) * scale
    sy = cy - (vy / z) * scale
    return sx, sy


def _rotate(vx: float, vy: float, vz: float, ax: float, ay: float) -> tuple[float, float, float]:
    # rotação em Y
    cos_y, sin_y = math.cos(ay), math.sin(ay)
    vx2 = vx * cos_y + vz * sin_y
    vz2 = -vx * sin_y + vz * cos_y
    # rotação em X
    cos_x, sin_x = math.cos(ax), math.sin(ax)
    vy2 = vy * cos_x - vz2 * sin_x
    vz3 = vy * sin_x + vz2 * cos_x
    return vx2, vy2, vz3


def _draw_cube(surf: pygame.Surface, angle: float, cx: float, cy: float, size: float) -> None:
    ax = angle * 0.7   # rotação diagonal
    ay = angle

    fov = 5.0
    projected = [_project(*_rotate(vx, vy, vz, ax, ay), fov, cx, cy, size)
                 for vx, vy, vz in _VERTS]

    # faces preenchidas (cor roxa semi-transparente)
    face_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for face in _FACES:
        pts = [projected[i] for i in face]
        # cull back-faces simples pela área com sinal
        ax_ = pts[1][0] - pts[0][0]; ay_ = pts[1][1] - pts[0][1]
        bx_ = pts[2][0] - pts[0][0]; by_ = pts[2][1] - pts[0][1]
        if ax_ * by_ - ay_ * bx_ > 0:
            pygame.draw.polygon(face_surf, (100, 0, 180, 90), pts)
            pygame.draw.polygon(face_surf, (140, 60, 220, 160), pts, 1)
    surf.blit(face_surf, (0, 0))

    # arestas
    for a, b in _EDGES:
        pygame.draw.line(surf, (160, 80, 255), (int(projected[a][0]), int(projected[a][1])),
                         (int(projected[b][0]), int(projected[b][1])), 2)


def _draw_scanlines(surf: pygame.Surface) -> None:
    """Overlay de linhas horizontais para efeito CRT."""
    overlay = pygame.Surface((_W, _H), pygame.SRCALPHA)
    for y in range(0, _H, 3):
        pygame.draw.line(overlay, (0, 0, 0, 55), (0, y), (_W, y))
    surf.blit(overlay, (0, 0))


def _draw_border(surf: pygame.Surface, font_small: pygame.font.Font) -> None:
    """Borda de caracteres ASCII ao redor da tela."""
    pygame.draw.rect(surf, _GREEN_DIM, (8, 8, _W - 16, _H - 16), 1)
    pygame.draw.rect(surf, _GREEN_DIM, (12, 12, _W - 24, _H - 24), 1)
    # cantos decorativos
    for corner_text, pos in [
        ("╔", (16, 16)), ("╗", (_W - 36, 16)),
        ("╚", (16, _H - 36)), ("╝", (_W - 36, _H - 36)),
    ]:
        s = font_small.render(corner_text, True, _GREEN_DIM)
        surf.blit(s, pos)


def run_menu() -> DifficultyConfig | None:
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((_W, _H))
    pygame.display.set_caption("Cub Project!")
    clock = pygame.time.Clock()

    # Fontes mono para efeito terminal
    font_title  = pygame.font.SysFont("couriernew",  96, bold=True)
    font_instr  = pygame.font.SysFont("couriernew",  22)
    font_option = pygame.font.SysFont("couriernew",  48, bold=True)
    font_small  = pygame.font.SysFont("couriernew",  20)
    font_hint   = pygame.font.SysFont("couriernew",  22)

    instructions = [
        "WASD         : mover o cubo",
        "SETAS + MOUSE: controlar a camera",
        "G            : gerar novo mapa",
        "Q / E        : subir / descer camera",
        "",
        "Colete blocos especiais para obter poderes.",
        "Nao caia para nao perder vidas!",
    ]

    option_labels = [f"[ {d.label} ]" for d in _DIFFICULTIES]

    angle = 0.0
    selected_idx = 0
    blink_t = 0.0
    cursor_visible = True

    # Cubo fica no lado direito
    cube_cx = _W * 0.78
    cube_cy = _H * 0.52
    cube_size = 220.0

    while True:
        dt = clock.tick(60) / 1000.0
        angle += dt * 1.1
        blink_t += dt
        if blink_t >= 0.53:
            blink_t = 0.0
            cursor_visible = not cursor_visible

        mx, my = pygame.mouse.get_pos()

        # Calcula rects das opções para hit-test
        option_y_start = _H // 2 + 20
        option_rects: list[pygame.Rect] = []
        for i, label in enumerate(option_labels):
            s = font_option.render(label, True, _GREEN)
            rx = _W // 4 - s.get_width() // 2
            ry = option_y_start + i * 80
            option_rects.append(pygame.Rect(rx - 20, ry - 6, s.get_width() + 40, s.get_height() + 12))
            if option_rects[-1].collidepoint(mx, my):
                selected_idx = i

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
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(option_rects):
                    if r.collidepoint(mx, my):
                        pygame.quit()
                        return _DIFFICULTIES[i]

        # ── render ──────────────────────────────────────────────────────
        screen.fill(_BG)

        # Cubo rotacionando
        _draw_cube(screen, angle, cube_cx, cube_cy, cube_size)

        # Borda decorativa
        _draw_border(screen, font_small)

        # Título
        title_surf = font_title.render("Cub Project!", True, _GREEN_HI)
        screen.blit(title_surf, (_W // 4 - title_surf.get_width() // 2, 60))

        # Linha separadora abaixo do título
        sep_y = 60 + title_surf.get_height() + 10
        pygame.draw.line(screen, _GREEN_DIM, (40, sep_y), (_W // 2 - 40, sep_y), 1)

        # Instruções
        instr_y = sep_y + 24
        screen.blit(font_small.render("> INSTRUCOES:", True, _GREEN_DIM), (60, instr_y))
        instr_y += 28
        for line in instructions:
            s = font_instr.render(line, True, _GREEN_DIM)
            screen.blit(s, (72, instr_y))
            instr_y += 28

        # Separador antes das opções
        pygame.draw.line(screen, _GREEN_DIM, (40, instr_y + 10), (_W // 2 - 40, instr_y + 10), 1)

        # Label de seleção de dificuldade
        diff_label = font_small.render("> SELECIONE A DIFICULDADE:", True, _GREEN_DIM)
        screen.blit(diff_label, (60, instr_y + 22))

        # Opções de dificuldade
        for i, label in enumerate(option_labels):
            is_sel = (i == selected_idx)
            color = _AMBER if is_sel else _GREEN
            text = label
            prefix = "> " if is_sel else "  "
            cursor = ("_" if cursor_visible else " ") if is_sel else ""
            line_text = f"{prefix}{text}{cursor}"
            s = font_option.render(line_text, True, color)
            rx = _W // 4 - s.get_width() // 2
            ry = option_y_start + i * 80
            if is_sel:
                pygame.draw.rect(screen, (30, 25, 5), (rx - 24, ry - 8, s.get_width() + 48, s.get_height() + 16))
                pygame.draw.rect(screen, _AMBER, (rx - 24, ry - 8, s.get_width() + 48, s.get_height() + 16), 1)
            screen.blit(s, (rx, ry))

        # Hint inferior
        hint_text = "ENTER/CLIQUE para confirmar  |  ESC para sair  |  W/S ou SETAS para navegar"
        hint_s = font_hint.render(hint_text, True, _GREEN_DIM)
        screen.blit(hint_s, ((_W - hint_s.get_width()) // 2, _H - 48))

        _draw_scanlines(screen)
        pygame.display.flip()

    pygame.quit()
    return None
