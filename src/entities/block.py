"""Bloco do mapa e subclasses."""

from __future__ import annotations

from OpenGL.GL import (
    GL_BLEND,
    GL_LESS,
    GL_LEQUAL,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    glBegin,
    glBindTexture,
    glBlendFunc,
    glColor3f,
    glDepthFunc,
    glDisable,
    glEnable,
    glEnd,
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
    TEXTURE_PATH: str = "assets/textures/rock.jpg"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
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


class HealBlock(PoweredBlock):
    TEXTURE_PATH: str = "assets/textures/heart.png"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
        super().__init__(power="heal", **kwargs)

    def _draw_top_textured(self) -> None:
        # Fundo branco + heart.png com alpha blend sobre o mesmo plano (GL_LEQUAL).
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
    """Bloco de portal. Topo: portal.png com alpha blend sobre fundo preto."""

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
    """Topo com shrink.jpg — textura opaca direta, igual ao grass."""

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
    """Topo com expand.png — textura com alpha blend sobre fundo sólido."""

    TEXTURE_PATH: str = "assets/textures/expand.webp"
    _tex_id: int | None = None

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("textured", True)
        super().__init__(power="grow", **kwargs)

    def _draw_top_textured(self) -> None:
        # expand.png tem fundo transparente — renderiza sobre a cor do bloco.
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
