"""Bloco do mapa e subclasse PoweredBlock.

Block é um cubo achatado (1×0.2×1) que forma o terreno do jogo.
PoweredBlock herda Block e carrega uma propriedade especial (`power`)
que futuramente afeta o Cube quando ele tombar sobre o bloco.
"""

from OpenGL.GL import (
    GL_QUADS,
    glBegin,
    glColor3f,
    glEnd,
    glPopMatrix,
    glPushMatrix,
    glScalef,
    glTranslatef,
    glVertex3f,
)

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size

# Altura padrão de um bloco (achatado no Y).
_BLOCK_HEIGHT: float = 0.1


class Block:
    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
        active: bool = True,
        is_powered: bool = False,
    ) -> None:
        self.position = position if position is not None else Position()
        self.color = color if color is not None else Color(0.5, 0.5, 0.5)
        self.size = size if size is not None else Size(1.0, _BLOCK_HEIGHT, 1.0)
        self.active = active
        self.is_powered = is_powered

    def draw(self) -> None:
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b

        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)

        glBegin(GL_QUADS)

        # Topo (+Y)
        glColor3f(r, g, b)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Base (−Y) — tom escuro
        glColor3f(r * 0.5, g * 0.5, b * 0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)

        # Frente (+Z) — tom médio
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Trás (−Z)
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)

        # Direita (+X)
        glColor3f(r * 0.6, g * 0.6, b * 0.6)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)

        # Esquerda (−X)
        glColor3f(r * 0.6, g * 0.6, b * 0.6)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5, -0.5)

        glEnd()
        glPopMatrix()


class PoweredBlock(Block):
    """Bloco especial que aplica um efeito ao Cube quando pisado.

    power: identificador do efeito ("scale", "speed", "color", …).
    A lógica de efeito é resolvida por Scene ao detectar colisão.
    """

    def __init__(self, power: str = "scale", **kwargs) -> None:
        super().__init__(is_powered=True, **kwargs)
        self.power = power
