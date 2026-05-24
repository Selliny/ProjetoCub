"""Bloco do mapa e subclasses — estética Neon / Dark Cyberpunk."""

from __future__ import annotations

from OpenGL.GL import (
    GL_BLEND,
    GL_LESS,
    GL_LEQUAL,
    GL_LINE_LOOP,
    GL_LINES,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_SRC_ALPHA,
    GL_TRIANGLES,
    glBegin,
    glBlendFunc,
    glColor3f,
    glColor4f,
    glDepthFunc,
    glDisable,
    glEnable,
    glEnd,
    glLineWidth,
    glPopMatrix,
    glPushMatrix,
    glScalef,
    glTranslatef,
    glVertex3f,
)

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size


def _draw_solid_box(sx: float, sy: float, sz: float, r: float, g: float, b: float) -> None:
    """Desenha caixa sólida com topo levemente mais claro que as laterais."""
    hi = min(r + 0.06, 1.0), min(g + 0.06, 1.0), min(b + 0.06, 1.0)
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    glBegin(GL_QUADS)
    # topo
    glColor3f(*hi)
    glVertex3f(-hx,  hy, -hz); glVertex3f( hx,  hy, -hz)
    glVertex3f( hx,  hy,  hz); glVertex3f(-hx,  hy,  hz)
    # frente / trás (70%)
    glColor3f(r * 0.70, g * 0.70, b * 0.70)
    glVertex3f(-hx, -hy,  hz); glVertex3f( hx, -hy,  hz)
    glVertex3f( hx,  hy,  hz); glVertex3f(-hx,  hy,  hz)
    glVertex3f( hx, -hy, -hz); glVertex3f(-hx, -hy, -hz)
    glVertex3f(-hx,  hy, -hz); glVertex3f( hx,  hy, -hz)
    # lados (60%)
    glColor3f(r * 0.60, g * 0.60, b * 0.60)
    glVertex3f( hx, -hy,  hz); glVertex3f( hx, -hy, -hz)
    glVertex3f( hx,  hy, -hz); glVertex3f( hx,  hy,  hz)
    glVertex3f(-hx, -hy, -hz); glVertex3f(-hx, -hy,  hz)
    glVertex3f(-hx,  hy,  hz); glVertex3f(-hx,  hy, -hz)
    # base (50%)
    glColor3f(r * 0.50, g * 0.50, b * 0.50)
    glVertex3f(-hx, -hy,  hz); glVertex3f( hx, -hy,  hz)
    glVertex3f( hx, -hy, -hz); glVertex3f(-hx, -hy, -hz)
    glEnd()


def _draw_top_outline(
    sx: float, sy: float, sz: float,
    nr: float, ng: float, nb: float,
    glow: bool = True,
) -> None:
    """Borda neon no topo. glow=True repete 3x com halo alpha decrescente."""
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    hy = sy * 0.5 + 0.002
    layers = [(0.0, 0.85)]
    for delta, alpha in layers:
        hx = sx * 0.5 + delta
        hz = sz * 0.5 + delta
        glColor4f(nr, ng, nb, alpha)
        glLineWidth(1.5 if delta == 0.0 else 1.0)
        glBegin(GL_LINE_LOOP)
        glVertex3f(-hx, hy, -hz); glVertex3f( hx, hy, -hz)
        glVertex3f( hx, hy,  hz); glVertex3f(-hx, hy,  hz)
        glEnd()
    glLineWidth(1.0)
    glDisable(GL_BLEND)
    glDepthFunc(GL_LESS)


class Block:
    HEIGHT: float = 0.1

    # Cor base e cor neon do outline para o bloco normal
    _FACE_COLOR = (0.10, 0.10, 0.16)
    _NEON_COLOR = (0.0, 1.0, 1.0)

    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
        active: bool = True,
        is_powered: bool = False,
    ) -> None:
        self.position = position if position is not None else Position()
        self.color = color if color is not None else Color(*Block._FACE_COLOR)
        self.size = size if size is not None else Size(1.0, Block.HEIGHT, 1.0)
        self.active = active
        self.is_powered = is_powered

    @classmethod
    def reset_texture_cache(cls) -> None:
        """Mantido por compatibilidade com main.py; sem texturas para limpar."""
        pass

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        glPopMatrix()


class StartBlock(Block):
    _FACE_COLOR = (0.0, 0.20, 0.05)
    _NEON_COLOR = (0.2, 1.0, 0.3)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*StartBlock._FACE_COLOR))
        super().__init__(**kwargs)


class EndBlock(Block):
    _FACE_COLOR = (0.30, 0.0, 0.0)
    _NEON_COLOR = (1.0, 0.1, 0.1)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*EndBlock._FACE_COLOR))
        super().__init__(**kwargs)

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # X luminoso no topo para indicar destino
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 0.2, 0.2, 0.7)
        glLineWidth(2.0)
        hy = sy * 0.5 + 0.003
        hx = sx * 0.35
        glBegin(GL_LINES)
        glVertex3f(-hx, hy, -hx); glVertex3f( hx, hy,  hx)
        glVertex3f( hx, hy, -hx); glVertex3f(-hx, hy,  hx)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()


class PoweredBlock(Block):
    def __init__(self, power: str = "scale", **kwargs) -> None:
        super().__init__(is_powered=True, **kwargs)
        self.power = power


# ── Blocos especiais ──────────────────────────────────────────────────────────

class HealBlock(PoweredBlock):
    """Rosa: recupera 1 vida (uso único)."""
    _FACE_COLOR = (0.35, 0.0, 0.15)
    _NEON_COLOR = (1.0, 0.3, 0.7)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*HealBlock._FACE_COLOR))
        super().__init__(power="heal", **kwargs)

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # Símbolo + (cruz) no topo
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 0.4, 0.75, 0.8)
        glLineWidth(2.5)
        hy = sy * 0.5 + 0.003
        arm = sx * 0.30
        glBegin(GL_LINES)
        glVertex3f(0.0, hy, -arm); glVertex3f(0.0, hy,  arm)
        glVertex3f(-arm, hy, 0.0); glVertex3f( arm, hy, 0.0)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()


class ShrinkBlock(PoweredBlock):
    """Roxo: diminui o cubo para metade do tamanho."""
    _FACE_COLOR = (0.15, 0.0, 0.30)
    _NEON_COLOR = (0.7, 0.0, 1.0)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*ShrinkBlock._FACE_COLOR))
        super().__init__(power="shrink", **kwargs)

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # Quadrado menor centralizado (símbolo de encolher)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.7, 0.0, 1.0, 0.65)
        glLineWidth(1.5)
        hy = sy * 0.5 + 0.003
        s = sx * 0.22
        glBegin(GL_LINE_LOOP)
        glVertex3f(-s, hy, -s); glVertex3f( s, hy, -s)
        glVertex3f( s, hy,  s); glVertex3f(-s, hy,  s)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()


class GrowBlock(PoweredBlock):
    """Verde: restaura o cubo ao tamanho normal."""
    _FACE_COLOR = (0.0, 0.18, 0.06)
    _NEON_COLOR = (0.0, 1.0, 0.4)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*GrowBlock._FACE_COLOR))
        super().__init__(power="grow", **kwargs)

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # Quadrado maior (símbolo de crescer)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.0, 1.0, 0.4, 0.55)
        glLineWidth(1.5)
        hy = sy * 0.5 + 0.003
        s = sx * 0.40
        glBegin(GL_LINE_LOOP)
        glVertex3f(-s, hy, -s); glVertex3f( s, hy, -s)
        glVertex3f( s, hy,  s); glVertex3f(-s, hy,  s)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()


class IceBlock(PoweredBlock):
    """Ciano escuro: ao sair o cubo desliza +1 passo na mesma direção."""
    _FACE_COLOR = (0.0, 0.12, 0.25)
    _NEON_COLOR = (0.0, 0.8, 1.0)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*IceBlock._FACE_COLOR))
        super().__init__(power="ice", **kwargs)

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # Floco de neve: 6 braços (H, V, 2 diagonais) + galhos nas pontas
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.0, 0.90, 1.0, 0.80)
        glLineWidth(1.5)
        hy = sy * 0.5 + 0.003
        R  = sx * 0.36   # comprimento do braço principal
        D  = R * 0.707   # braço diagonal (R / sqrt(2))
        bg = R * 0.22    # comprimento do galho lateral
        bg45 = bg * 0.707
        glBegin(GL_LINES)
        # braço horizontal
        glVertex3f(-R,  hy, 0.0); glVertex3f( R,  hy, 0.0)
        # braço vertical
        glVertex3f(0.0, hy, -R ); glVertex3f(0.0, hy,  R )
        # diagonais
        glVertex3f(-D,  hy, -D ); glVertex3f( D,  hy,  D )
        glVertex3f( D,  hy, -D ); glVertex3f(-D,  hy,  D )
        # galhos do braço horizontal (em ±R)
        glVertex3f(-R,  hy, 0.0); glVertex3f(-R + bg45, hy, -bg45)
        glVertex3f(-R,  hy, 0.0); glVertex3f(-R + bg45, hy,  bg45)
        glVertex3f( R,  hy, 0.0); glVertex3f( R - bg45, hy, -bg45)
        glVertex3f( R,  hy, 0.0); glVertex3f( R - bg45, hy,  bg45)
        # galhos do braço vertical (em ±R)
        glVertex3f(0.0, hy, -R ); glVertex3f(-bg45, hy, -R + bg45)
        glVertex3f(0.0, hy, -R ); glVertex3f( bg45, hy, -R + bg45)
        glVertex3f(0.0, hy,  R ); glVertex3f(-bg45, hy,  R - bg45)
        glVertex3f(0.0, hy,  R ); glVertex3f( bg45, hy,  R - bg45)
        # galhos das diagonais (em ±D,±D)
        glVertex3f(-D,  hy, -D ); glVertex3f(-D + bg, hy, -D      )
        glVertex3f(-D,  hy, -D ); glVertex3f(-D,      hy, -D + bg )
        glVertex3f( D,  hy,  D ); glVertex3f( D - bg, hy,  D      )
        glVertex3f( D,  hy,  D ); glVertex3f( D,      hy,  D - bg )
        glVertex3f( D,  hy, -D ); glVertex3f( D - bg, hy, -D      )
        glVertex3f( D,  hy, -D ); glVertex3f( D,      hy, -D + bg )
        glVertex3f(-D,  hy,  D ); glVertex3f(-D + bg, hy,  D      )
        glVertex3f(-D,  hy,  D ); glVertex3f(-D,      hy,  D - bg )
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()


class InvertBlock(PoweredBlock):
    """Magenta: inverte os controles W↔S / A↔D por 5 segundos."""
    _FACE_COLOR = (0.25, 0.0, 0.15)
    _NEON_COLOR = (1.0, 0.0, 0.8)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*InvertBlock._FACE_COLOR))
        super().__init__(power="invert", **kwargs)

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # Setas opostas em magenta neon
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 0.1, 0.85, 0.80)
        glLineWidth(1.0)
        hy = sy * 0.5 + 0.003
        glBegin(GL_TRIANGLES)
        glVertex3f(-0.15, hy, -0.05); glVertex3f(-0.35, hy,  0.0); glVertex3f(-0.15, hy,  0.05)
        glVertex3f( 0.15, hy, -0.05); glVertex3f( 0.35, hy,  0.0); glVertex3f( 0.15, hy,  0.05)
        glEnd()
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()


class FragileBlock(PoweredBlock):
    """Cinza trincado: desaparece 0.45 s após o cubo sair, reaparece em 10 s."""
    _FACE_COLOR = (0.12, 0.12, 0.14)
    _NEON_COLOR = (0.85, 0.85, 0.85)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(*FragileBlock._FACE_COLOR))
        super().__init__(power="fragile", **kwargs)
        self._deactivate_at: float | None = None
        self._blink_t: float = 0.0

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # Linhas de trinca em branco-cinza
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.85, 0.85, 0.85, 0.65)
        glLineWidth(1.5)
        hy = sy * 0.5 + 0.003
        glBegin(GL_LINE_LOOP)
        glVertex3f( 0.0,  hy, -0.35); glVertex3f( 0.15, hy,  0.0)
        glVertex3f(-0.10, hy,  0.10); glVertex3f( 0.05, hy,  0.35)
        glEnd()
        glBegin(GL_LINE_LOOP)
        glVertex3f(-0.25, hy, -0.10); glVertex3f(-0.05, hy,  0.0)
        glVertex3f(-0.20, hy,  0.25)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()


class BlinkBlock(PoweredBlock):
    """Laranja escuro: alterna ativo/inativo em ciclo fixo — desafio de timing."""
    _FACE_COLOR = (0.22, 0.10, 0.0)
    _NEON_COLOR = (1.0, 0.8, 0.0)

    CYCLE: float = 8.0  # 4 s ON + 4 s OFF

    def __init__(self, phase_offset: float = 0.0, **kwargs) -> None:
        kwargs.setdefault("color", Color(*BlinkBlock._FACE_COLOR))
        super().__init__(power="blink", **kwargs)
        self.phase_offset = phase_offset
        self._phase_t: float = phase_offset * BlinkBlock.CYCLE

    def toggle_blink(self, dt: float) -> None:
        self._phase_t = (self._phase_t + dt) % BlinkBlock.CYCLE
        self.active = self._phase_t < (BlinkBlock.CYCLE / 2.0)

    def draw(self) -> None:
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        sx, sy, sz = self.size.sx, self.size.sy, self.size.sz
        _draw_solid_box(sx, sy, sz, *self._FACE_COLOR)
        _draw_top_outline(sx, sy, sz, *self._NEON_COLOR, glow=True)
        # Quadrado neon no topo como marcador visual
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 0.85, 0.0, 0.60)
        glLineWidth(1.5)
        hy = sy * 0.5 + 0.003
        s = sx * 0.28
        glBegin(GL_LINE_LOOP)
        glVertex3f(-s, hy, -s); glVertex3f( s, hy, -s)
        glVertex3f( s, hy,  s); glVertex3f(-s, hy,  s)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        glPopMatrix()
