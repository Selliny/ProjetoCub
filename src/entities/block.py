"""Bloco do mapa e subclasses."""

from __future__ import annotations

import math

from OpenGL.GL import (
    GL_BLEND,
    GL_LESS,
    GL_LEQUAL,
    GL_LINE_LOOP,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TRIANGLES,
    glBegin,
    glBindTexture,
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
    glTexCoord2f,
    glTranslatef,
    glVertex3f,
)

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size
from src.graphics.texture import TextureManager

_TOP_VERTS = [(-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
_UV_STD    = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
_UV_FLIP   = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]


class Block:
    HEIGHT: float = 0.1
    TEXTURE_PATH: str = "assets/textures/grass.png"
    _tex_id: int | None = None

    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
        active: bool = True,
        is_powered: bool = False,
        textured: bool = True,
    ) -> None:
        self.position = position if position is not None else Position()
        self.color = color if color is not None else Color(0.5, 0.5, 0.5)
        self.size = size if size is not None else Size(1.0, Block.HEIGHT, 1.0)
        self.active = active
        self.is_powered = is_powered
        self.textured = textured

    @classmethod
    def _get_tex(cls) -> int:
        if cls._tex_id is None:
            cls._tex_id = TextureManager.load(cls.TEXTURE_PATH)
        return cls._tex_id

    def _draw_top_textured(self) -> None:
        """Textura opaca no topo — mesmo padrão para todos os blocos texturizados."""
        tex = self._get_tex()
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex)
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        for (u, v), (x, y, z) in zip(_UV_STD, _TOP_VERTS):
            glTexCoord2f(u, v)
            glVertex3f(x, y, z)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    def _draw_top_solid(self, r: float, g: float, b: float) -> None:
        glBegin(GL_QUADS)
        glColor3f(r, g, b)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glEnd()

    def _draw_sides(self, r: float, g: float, b: float) -> None:
        glBegin(GL_QUADS)
        glColor3f(r * 0.5, g * 0.5, b * 0.5)
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5, -0.5)
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        glVertex3f(-0.5, -0.5,  0.5); glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5,  0.5)
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        glVertex3f( 0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5, -0.5)
        glColor3f(r * 0.6, g * 0.6, b * 0.6)
        glVertex3f( 0.5, -0.5,  0.5); glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5); glVertex3f( 0.5,  0.5,  0.5)
        glColor3f(r * 0.6, g * 0.6, b * 0.6)
        glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5); glVertex3f(-0.5,  0.5, -0.5)
        glEnd()

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        if self.textured:
            self._draw_top_textured()
        else:
            self._draw_top_solid(r, g, b)
        self._draw_sides(r, g, b)
        glPopMatrix()


class StartBlock(Block):
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", False)
        kwargs.setdefault("color", Color(0.1, 0.45, 0.1))
        super().__init__(**kwargs)


class EndBlock(Block):
    TEXTURE_PATH: str = "assets/textures/lava.jpg"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
        super().__init__(**kwargs)


class PoweredBlock(Block):
    _tex_id: int | None = None

    def __init__(self, power: str = "scale", **kwargs) -> None:
        kwargs.setdefault("textured", False)
        super().__init__(is_powered=True, **kwargs)
        self.power = power

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        if self.textured:
            self._draw_top_textured()
        else:
            self._draw_top_solid(r, g, b)
        self._draw_sides(r, g, b)
        glPopMatrix()


# ── Blocos existentes ──────────────────────────────────────────────────────────

class HealBlock(PoweredBlock):
    """Rosa claro: recupera 1 vida (uso único)."""
    TEXTURE_PATH: str = "assets/textures/heart.png"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
        super().__init__(power="heal", **kwargs)

    def _draw_top_textured(self) -> None:
        self._draw_top_solid(1.0, 1.0, 1.0)
        glDepthFunc(GL_LEQUAL)
        tex = self._get_tex()
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        for (u, v), (x, y, z) in zip(_UV_FLIP, _TOP_VERTS):
            glTexCoord2f(u, v)
            glVertex3f(x, y, z)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_textured()
        self._draw_sides(r, g, b)
        glPopMatrix()


class PortalBlock(PoweredBlock):
    """Azul escuro: teleporta para posição aleatória do mapa."""
    TEXTURE_PATH: str = "assets/textures/portal.png"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
        super().__init__(power="portal", **kwargs)

    def _draw_top_textured(self) -> None:
        self._draw_top_solid(0.0, 0.0, 0.0)
        glDepthFunc(GL_LEQUAL)
        tex = self._get_tex()
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        for (u, v), (x, y, z) in zip(_UV_FLIP, _TOP_VERTS):
            glTexCoord2f(u, v)
            glVertex3f(x, y, z)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_textured()
        self._draw_sides(r, g, b)
        glPopMatrix()


class ShrinkBlock(PoweredBlock):
    """Roxo vivo: diminui o cubo para metade do tamanho."""
    TEXTURE_PATH: str = "assets/textures/shrink.png"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
        super().__init__(power="shrink", **kwargs)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_textured()
        self._draw_sides(r, g, b)
        glPopMatrix()


class GrowBlock(PoweredBlock):
    """Azul céu: restaura o cubo ao tamanho normal."""
    TEXTURE_PATH: str = "assets/textures/expand.webp"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
        super().__init__(power="grow", **kwargs)

    def _draw_top_textured(self) -> None:
        self._draw_top_solid(self.color.r, self.color.g, self.color.b)
        glDepthFunc(GL_LEQUAL)
        tex = self._get_tex()
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        for (u, v), (x, y, z) in zip(_UV_FLIP, _TOP_VERTS):
            glTexCoord2f(u, v)
            glVertex3f(x, y, z)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_textured()
        self._draw_sides(r, g, b)
        glPopMatrix()


# ── Novos blocos especiais ────────────────────────────────────────────────────

class IceBlock(PoweredBlock):
    """Azul gelo: ao sair, o cubo desliza +1 passo automaticamente na mesma direção."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(0.55, 0.88, 1.0))
        super().__init__(power="ice", **kwargs)

    def _draw_top_solid(self, r: float, g: float, b: float) -> None:
        # Topo com gradiente: centro branco, bordas azul gelo
        glBegin(GL_QUADS)
        glColor3f(r, g, b)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glEnd()
        # Cruz branca no centro para sinalizar deslizamento
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 1.0, 1.0, 0.6)
        glBegin(GL_QUADS)
        glVertex3f(-0.08,  0.501, -0.38); glVertex3f( 0.08,  0.501, -0.38)
        glVertex3f( 0.08,  0.501,  0.38); glVertex3f(-0.08,  0.501,  0.38)
        glVertex3f(-0.38,  0.501, -0.08); glVertex3f( 0.38,  0.501, -0.08)
        glVertex3f( 0.38,  0.501,  0.08); glVertex3f(-0.38,  0.501,  0.08)
        glEnd()
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_solid(r, g, b)
        self._draw_sides(r, g, b)
        glPopMatrix()


class InvertBlock(PoweredBlock):
    """Magenta: inverte os controles W↔S / A↔D por 5 segundos."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(0.85, 0.0, 0.55))
        super().__init__(power="invert", **kwargs)

    def _draw_top_solid(self, r: float, g: float, b: float) -> None:
        super()._draw_top_solid(r, g, b)
        # Símbolo de setas opostas no topo
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 1.0, 1.0, 0.75)
        glLineWidth(2.0)
        # Seta esquerda
        glBegin(GL_TRIANGLES)
        glVertex3f(-0.15,  0.501, -0.05)
        glVertex3f(-0.35,  0.501,  0.0)
        glVertex3f(-0.15,  0.501,  0.05)
        glEnd()
        # Seta direita
        glBegin(GL_TRIANGLES)
        glVertex3f( 0.15,  0.501, -0.05)
        glVertex3f( 0.35,  0.501,  0.0)
        glVertex3f( 0.15,  0.501,  0.05)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_solid(r, g, b)
        self._draw_sides(r, g, b)
        glPopMatrix()


class FragileBlock(PoweredBlock):
    """Cinza claro trincado: desaparece 1,5 s após o cubo sair.

    O campo `_deactivate_at` é definido pelo Map quando o cubo sai do bloco
    (em segundos absolutos de jogo). Enquanto próximo de desaparecer, o topo
    pisca rapidamente para avisar o jogador.
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(0.72, 0.72, 0.72))
        super().__init__(power="fragile", **kwargs)
        self._deactivate_at: float | None = None  # tempo absoluto (segundos)
        self._blink_t: float = 0.0               # acumulador para o piscar

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_solid(r, g, b)
        # Linhas de trinca no topo
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.4, 0.4, 0.4, 0.8)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex3f( 0.0,   0.501, -0.35)
        glVertex3f( 0.15,  0.501,  0.0)
        glVertex3f(-0.1,   0.501,  0.1)
        glVertex3f( 0.05,  0.501,  0.35)
        glEnd()
        glBegin(GL_LINE_LOOP)
        glVertex3f(-0.25,  0.501, -0.1)
        glVertex3f(-0.05,  0.501,  0.0)
        glVertex3f(-0.2,   0.501,  0.25)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)
        self._draw_sides(r, g, b)
        glPopMatrix()


class BouncePadBlock(PoweredBlock):
    """Laranja vivo: lança o cubo 2 casas na mesma direção de entrada.

    Se a casa de destino (2 à frente) for vazia mas a intermediária for chão,
    o cubo para na casa intermediária. Se ambas forem vazias, cai normalmente
    a partir da posição de aterrissagem calculada.
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(1.0, 0.45, 0.0))
        super().__init__(power="bounce", **kwargs)

    def _draw_top_solid(self, r: float, g: float, b: float) -> None:
        super()._draw_top_solid(r, g, b)
        # Seta apontando para cima (visão de cima = triângulo)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 1.0, 1.0, 0.85)
        glBegin(GL_TRIANGLES)
        glVertex3f( 0.0,   0.501, -0.30)
        glVertex3f(-0.22,  0.501,  0.18)
        glVertex3f( 0.22,  0.501,  0.18)
        glEnd()
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_solid(r, g, b)
        self._draw_sides(r, g, b)
        glPopMatrix()


class SlowBlock(PoweredBlock):
    """Verde musgo: dobra a duração do roll pelos próximos 3 movimentos."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(0.2, 0.45, 0.15))
        super().__init__(power="slow", **kwargs)

    def _draw_top_solid(self, r: float, g: float, b: float) -> None:
        super()._draw_top_solid(r, g, b)
        # Círculo (polígono) no topo como símbolo de lentidão
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.9, 0.9, 0.5, 0.75)
        segs = 10
        glBegin(GL_LINE_LOOP)
        for i in range(segs):
            a = 2.0 * math.pi * i / segs
            glVertex3f(0.22 * math.cos(a), 0.501, 0.22 * math.sin(a))
        glEnd()
        # Ponteiro do relógio
        glBegin(GL_TRIANGLES)
        glVertex3f( 0.0,  0.501,  0.0)
        glVertex3f( 0.0,  0.501, -0.18)
        glVertex3f( 0.03, 0.501,  0.0)
        glEnd()
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_solid(r, g, b)
        self._draw_sides(r, g, b)
        glPopMatrix()


class CheckpointBlock(PoweredBlock):
    """Dourado: define ponto de retorno após queda (substitui o anterior).

    Ao pisar, salva a posição como novo checkpoint ativo. Após uma queda,
    o cubo respawna aqui em vez de no Start original. O bloco permanece no
    mapa (não é consumido) mas muda de aparência quando ativo.
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", Color(0.85, 0.65, 0.05))
        super().__init__(power="checkpoint", **kwargs)
        self.is_active_checkpoint: bool = False

    def _draw_top_solid(self, r: float, g: float, b: float) -> None:
        # Quando ativo: topo mais brilhante (amarelo claro)
        if self.is_active_checkpoint:
            super()._draw_top_solid(1.0, 0.95, 0.3)
        else:
            super()._draw_top_solid(r, g, b)
        # Bandeirinha no topo (triângulo + haste)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        flag_color = (0.2, 0.8, 0.2, 0.9) if self.is_active_checkpoint else (0.6, 0.6, 0.6, 0.7)
        glColor4f(*flag_color)
        glBegin(GL_TRIANGLES)
        glVertex3f(-0.05,  0.501, -0.3)
        glVertex3f( 0.25,  0.501, -0.15)
        glVertex3f(-0.05,  0.501,  0.0)
        glEnd()
        glColor4f(0.85, 0.85, 0.85, 0.8)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex3f(-0.05, 0.501, -0.3)
        glVertex3f(-0.05, 0.501,  0.3)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glDepthFunc(GL_LESS)

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)
        self._draw_top_solid(r, g, b)
        self._draw_sides(r, g, b)
        glPopMatrix()


